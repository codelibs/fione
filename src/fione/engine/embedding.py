"""Vectors of texts from a pretrained language model, for the ``TextEmbedding`` family.

A *backend* turns texts into vectors (the mean of one hidden layer of a language model over a
text's tokens). Fione's core does not load a model: it asks a backend by name (``BACKENDS``) and
keeps every vector in an on-disk cache keyed by the backend's fingerprint and the text, so a
text is embedded once, whoever asks and however often. The torch backend lives in
``fione.embedding_torch`` and is imported only when it is asked for; another backend (a server,
MLX) is one more entry of ``BACKENDS``.

Two environment variables say where things are, so that a trained model holds only the
fingerprint of what it read, never a path:

* ``FIONE_EMBEDDING_CACHE_DIR``: the cache. Unset, vectors are kept in memory for the process.
  ``extract`` fills the cache where a GPU is, and a fit or a prediction elsewhere reads it.
* ``FIONE_EMBEDDING_MODEL_DIR``: the model's directory, read by the torch backend; with several
  models, a directory that holds one subdirectory per model, named by the model's label.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from fione.engine.config import ConfigError

CACHE_ENV = "FIONE_EMBEDDING_CACHE_DIR"
MODEL_ENV = "FIONE_EMBEDDING_MODEL_DIR"
CHUNK = 2048  # texts asked of a backend at a time; each chunk is written to the cache at once
MAX_LENGTH = 8192


class EmbeddingUnavailable(ConfigError):
    """The vectors of some texts are neither in the cache nor computable by the backend."""


@dataclass(frozen=True)
class EmbeddingSpec:
    """What is embedded: the backend, a name for the model, the layer (a fraction of the depth,
    0.75: the layer three quarters of the way up) and the longest text read (in tokens). The
    vector of a text is the mean over its tokens of that layer's hidden states."""

    backend: str
    model: str
    layer: float = 0.75
    max_length: int = 384

    @property
    def fingerprint(self) -> str:
        return f"{self.backend}|{self.model}|layer={self.layer:g}|mean|len={self.max_length}"

    def validate(self) -> EmbeddingSpec:
        if self.backend not in BACKENDS:
            raise ConfigError(f"embedding_backend must be one of {sorted(BACKENDS)}")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ConfigError("embedding_model must name the model (a label, not a path)")
        layer = self.layer
        if not isinstance(layer, int | float) or isinstance(layer, bool) or not 0 < layer <= 1:
            raise ConfigError(f"embedding_layer must be above 0 and at most 1, got {layer!r}")
        length = self.max_length
        if not isinstance(length, int) or isinstance(length, bool) or not 1 <= length <= MAX_LENGTH:
            raise ConfigError(f"embedding_max_length must be a whole number from 1 to {MAX_LENGTH}")
        return self


class EmbeddingBackend(Protocol):
    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Vectors of ``texts``, one row each, in order: shape (len(texts), dim)."""


# name -> a backend factory, or "module:attribute" of one (imported when first used)
BACKENDS: dict[str, Callable[[EmbeddingSpec], EmbeddingBackend] | str] = {
    "torch_lm": "fione.embedding_torch:TorchLMBackend",
}
_live: dict[str, EmbeddingBackend] = {}  # a backend is built once per process and spec
_live_specs: dict[str, tuple[EmbeddingSpec, EmbeddingBackend]] = {}


def make_backend(spec: EmbeddingSpec) -> EmbeddingBackend:
    key = spec.fingerprint
    if key in _live:
        return _live[key]
    for live_spec, backend in _live_specs.values():
        if (live_spec.backend, live_spec.model, live_spec.max_length) == (
            spec.backend,
            spec.model,
            spec.max_length,
        ) and hasattr(backend, "view"):  # the same model, read at another layer
            _live[key] = backend.view(spec)
            _live_specs[key] = (spec, _live[key])
            return _live[key]
    release()  # one model in memory at a time: two large models rarely fit together
    factory = BACKENDS.get(spec.backend)
    if factory is None:
        raise EmbeddingUnavailable(f"unknown embedding backend {spec.backend!r}")
    try:
        if isinstance(factory, str):
            module, _, attribute = factory.partition(":")
            factory = getattr(importlib.import_module(module), attribute)
        _live[key] = factory(spec)
        _live_specs[key] = (spec, _live[key])
    except EmbeddingUnavailable:
        raise
    except Exception as e:  # a missing library or model: say what it was, not a traceback
        raise EmbeddingUnavailable(
            f"the embedding backend {spec.backend!r} cannot run here: {type(e).__name__}: {e}"
        ) from e
    return _live[key]


def text_keys(texts: Sequence[str]) -> np.ndarray:
    """A 64-bit key per text (its content, so equal texts share a vector)."""
    return np.fromiter(
        (
            int.from_bytes(hashlib.blake2b(t.encode(), digest_size=8).digest(), "little")
            for t in texts
        ),
        dtype=np.uint64,
        count=len(texts),
    )


class EmbeddingCache:
    """The vectors of one fingerprint: shards of (keys, float16 vectors) in a directory, or only
    in memory when ``root`` is None. A shard is written once and never changed."""

    def __init__(self, root: Path | None, fingerprint: str):
        self.fingerprint = fingerprint
        self.dir = None
        if root is not None:
            tag = hashlib.blake2b(fingerprint.encode(), digest_size=8).hexdigest()
            self.dir = Path(root) / tag
        self._keys = np.empty(0, dtype=np.uint64)  # all keys, sorted
        self._where = np.empty((0, 2), dtype=np.int64)  # per sorted key: (shard, row)
        self._shards: list[np.ndarray] = []
        self.writable = True
        self.dim = 0
        if self.dir is not None and (self.dir / "meta.json").exists():
            meta = json.loads((self.dir / "meta.json").read_text())
            if meta.get("fingerprint") != fingerprint:
                raise EmbeddingUnavailable(
                    "the embedding cache belongs to another model or setting"
                )
            for keys_file in sorted(self.dir.glob("shard-*.keys.npy")):
                vectors = np.load(str(keys_file).replace(".keys.", ".vec."), mmap_mode="r")
                self._add_shard(np.load(keys_file), vectors)

    def __len__(self) -> int:
        return len(self._keys)

    def _add_shard(self, keys: np.ndarray, vectors: np.ndarray) -> None:
        shard = len(self._shards)
        self._shards.append(vectors)
        self.dim = vectors.shape[1]
        where = np.stack([np.full(len(keys), shard), np.arange(len(keys))], axis=1)
        keys_all = np.concatenate([self._keys, keys])
        where_all = np.concatenate([self._where, where])
        order = np.argsort(keys_all, kind="stable")
        self._keys, self._where = keys_all[order], where_all[order]

    def find(self, keys: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """``(found, where)``: whether each key has a vector, and its (shard, row) if so."""
        if len(self._keys) == 0:
            return np.zeros(len(keys), dtype=bool), np.zeros((len(keys), 2), dtype=np.int64)
        at = np.minimum(np.searchsorted(self._keys, keys), len(self._keys) - 1)
        found = self._keys[at] == keys
        return found, self._where[at]

    def gather(self, where: np.ndarray) -> np.ndarray:
        out = np.empty((len(where), self.dim), dtype=np.float32)
        for shard in np.unique(where[:, 0]):
            rows = np.flatnonzero(where[:, 0] == shard)
            out[rows] = self._shards[shard][where[rows, 1]]
        return out

    def add(self, keys: np.ndarray, vectors: np.ndarray) -> None:
        vectors = np.asarray(vectors, dtype=np.float16)
        if self.dim and vectors.shape[1] != self.dim:
            raise EmbeddingUnavailable("the backend's vectors changed width: a different model")
        if self.dir is not None and self.writable:
            try:
                self.dir.mkdir(parents=True, exist_ok=True)
                meta = self.dir / "meta.json"
                if not meta.exists():
                    meta.write_text(json.dumps({"fingerprint": self.fingerprint}))
                stem = self.dir / f"shard-{uuid.uuid4().hex}"  # unique: writers never collide
                np.save(f"{stem}.vec.npy", vectors)
                np.save(f"{stem}.keys.npy", keys)  # the keys last: a shard without them is unseen
            except OSError:
                self.writable = False  # a read-only cache: keep the vectors in memory only
        self._add_shard(keys, vectors)


_caches: dict[tuple[str, str], EmbeddingCache] = {}


def open_cache(spec: EmbeddingSpec) -> EmbeddingCache:
    root = os.environ.get(CACHE_ENV) or ""
    key = (root, spec.fingerprint)
    if key not in _caches:
        _caches[key] = EmbeddingCache(Path(root) if root else None, spec.fingerprint)
    return _caches[key]


def release() -> None:
    """Let go of the backends in memory (each frees what it holds, if it can)."""
    for backend in _live.values():
        getattr(backend, "close", lambda: None)()
    _live.clear()
    _live_specs.clear()


def forget() -> None:
    """Drop the backends and the caches held in memory (tests; a long process that is done)."""
    release()
    _caches.clear()


def missing(spec: EmbeddingSpec, texts: Sequence[str]) -> int:
    """How many distinct texts of ``texts`` have no vector yet."""
    keys = np.unique(text_keys(texts))
    return int((~open_cache(spec).find(keys)[0]).sum())


def embed_texts(
    spec: EmbeddingSpec, texts: Sequence[str], progress: Callable[[int, int], None] | None = None
) -> np.ndarray:
    """Float32 vectors of ``texts`` (one row each): from the cache, and from the backend for the
    texts the cache lacks (those are added to the cache, chunk by chunk). ``progress(done,
    total)`` reports the texts the backend has embedded."""
    cache = open_cache(spec)
    keys = text_keys(texts)
    found, _ = cache.find(keys)
    if not found.all():
        todo_keys, first = np.unique(keys[~found], return_index=True)
        todo = [texts[i] for i in np.flatnonzero(~found)[first]]
        backend = make_backend(spec)
        for start in range(0, len(todo), CHUNK):
            part = np.asarray(backend.embed(todo[start : start + CHUNK]), dtype=np.float32)
            if part.ndim != 2 or len(part) != len(todo[start : start + CHUNK]):
                raise EmbeddingUnavailable("the backend returned the wrong number of vectors")
            with np.errstate(over="ignore"):
                narrow = part.astype(np.float16)
            if not np.isfinite(narrow).all():  # the cache is permanent
                raise EmbeddingUnavailable("the backend returned vectors that are not finite")
            cache.add(todo_keys[start : start + CHUNK], part)
            if progress is not None:
                progress(min(start + CHUNK, len(todo)), len(todo))
    return cache.gather(cache.find(keys)[1])


def extract(
    spec: EmbeddingSpec, texts: Sequence[str], progress: Callable[[int, int], None] | None = None
) -> int:
    """Fill the cache (``FIONE_EMBEDDING_CACHE_DIR``) with the vectors of ``texts``, where the
    model can run; returns how many texts were embedded now. A run that stops can be repeated:
    what is in the cache is not embedded again."""
    if not os.environ.get(CACHE_ENV):
        raise ConfigError(f"set {CACHE_ENV} to the directory that is to hold the vectors")
    spec.validate()
    before = len(open_cache(spec))
    embed_texts(spec, list(texts), progress)
    return len(open_cache(spec)) - before
