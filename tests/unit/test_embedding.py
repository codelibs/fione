"""Vectors of texts from a backend, kept in a cache that is read before the backend is asked."""

import numpy as np
import pytest

from fione.engine import embedding
from fione.engine.config import ConfigError, TrainConfig
from fione.engine.embedding import (
    CACHE_ENV,
    EmbeddingSpec,
    EmbeddingUnavailable,
    embed_texts,
    extract,
    missing,
)

DIM = 16


class FakeBackend:
    """A vector per text from its character trigrams: equal texts, equal vectors."""

    calls: list[int] = []

    def __init__(self, spec):
        self.spec = spec

    def embed(self, texts):
        FakeBackend.calls.append(len(texts))
        out = np.zeros((len(texts), DIM), dtype=np.float32)
        for row, text in enumerate(texts):
            for at in range(len(text) - 2):
                out[row, hash(text[at : at + 3]) % DIM] += 1
        return out / np.maximum(1, np.linalg.norm(out, axis=1, keepdims=True))


@pytest.fixture(autouse=True)
def fake_backend(monkeypatch, tmp_path):
    FakeBackend.calls = []
    embedding.forget()
    monkeypatch.setitem(embedding.BACKENDS, "fake", FakeBackend)
    monkeypatch.setenv(CACHE_ENV, str(tmp_path / "cache"))
    yield
    embedding.forget()


SPEC = EmbeddingSpec("fake", "toy", 0.5, 64)


def test_the_fingerprint_names_everything_that_changes_a_vector():
    other = [
        EmbeddingSpec("fake", "toy", 0.75, 64),
        EmbeddingSpec("fake", "toy", 0.5, 128),
        EmbeddingSpec("fake", "other", 0.5, 64),
    ]
    assert len({SPEC.fingerprint, *(s.fingerprint for s in other)}) == 4


def test_a_text_is_embedded_once_whoever_asks(tmp_path):
    texts = ["alpha beta", "gamma delta", "alpha beta"]
    first = embed_texts(SPEC, texts)
    assert first.shape == (3, DIM) and first.dtype == np.float32
    assert np.allclose(first[0], first[2]) and FakeBackend.calls == [2]  # a repeat is one text
    embed_texts(SPEC, ["gamma delta", "alpha beta"])
    assert FakeBackend.calls == [2]  # the cache answered
    assert missing(SPEC, ["alpha beta", "new text"]) == 1
    embedding.forget()  # another process: the vectors are on disk
    again = embed_texts(SPEC, texts)
    assert FakeBackend.calls == [2] and np.allclose(again, first, atol=1e-3)


def test_the_cache_is_per_fingerprint(tmp_path):
    embed_texts(SPEC, ["alpha beta"])
    embed_texts(EmbeddingSpec("fake", "toy", 0.9, 64), ["alpha beta"])
    assert FakeBackend.calls == [1, 1]
    root = tmp_path / "cache"
    assert len(list(root.iterdir())) == 2


def test_a_cache_of_another_setting_is_refused(tmp_path):
    embed_texts(SPEC, ["alpha beta"])
    folder = next((tmp_path / "cache").iterdir())
    (folder / "meta.json").write_text('{"fingerprint": "other"}')
    embedding.forget()
    with pytest.raises(EmbeddingUnavailable, match="another model"):
        embed_texts(SPEC, ["alpha beta"])


def test_without_a_backend_or_vectors_the_message_says_so():
    with pytest.raises(EmbeddingUnavailable, match="cannot run here"):
        embed_texts(EmbeddingSpec("torch_lm", "toy"), ["alpha beta"])  # no model directory
    with pytest.raises(EmbeddingUnavailable, match="unknown embedding backend"):
        embed_texts(EmbeddingSpec("nothing", "toy"), ["alpha beta"])


def test_a_read_only_cache_still_serves_what_it_holds():
    embed_texts(SPEC, ["alpha beta"])
    embedding.forget()
    embedding.open_cache(SPEC).writable = False  # e.g. a dataset mounted read-only
    embed_texts(SPEC, ["alpha beta", "fresh text"])  # the new vector stays in memory
    assert FakeBackend.calls == [1, 1]
    embed_texts(SPEC, ["fresh text"])
    assert FakeBackend.calls == [1, 1]


def test_extract_fills_the_cache_in_chunks_and_a_rerun_embeds_nothing(monkeypatch):
    monkeypatch.setattr(embedding, "CHUNK", 3)
    texts = [f"text number {i}" for i in range(8)]
    seen = []
    assert extract(SPEC, texts, lambda done, total: seen.append((done, total))) == 8
    assert FakeBackend.calls == [3, 3, 2] and seen[-1] == (8, 8)
    embedding.forget()
    assert extract(SPEC, texts) == 0 and FakeBackend.calls == [3, 3, 2]


def test_extract_needs_a_cache_directory(monkeypatch):
    monkeypatch.delenv(CACHE_ENV)
    with pytest.raises(ConfigError, match=CACHE_ENV):
        extract(SPEC, ["alpha beta"])


def test_the_settings_are_checked():
    ok = TrainConfig(target="y", embedding_backend="fake", embedding_model="toy")
    assert ok.embedding == SPEC.__class__("fake", "toy", 0.75, 384) and ok.validate()
    assert TrainConfig(target="y").embedding is None
    for bad in (
        {"embedding_backend": "nothing", "embedding_model": "toy"},
        {"embedding_backend": "fake", "embedding_model": " "},
        {"embedding_backend": "fake", "embedding_model": "toy", "embedding_layer": 0},
        {"embedding_backend": "fake", "embedding_model": "toy", "embedding_layer": 1.5},
        {"embedding_backend": "fake", "embedding_model": "toy", "embedding_max_length": 0},
    ):
        with pytest.raises(ConfigError):
            TrainConfig(target="y", **bad).validate()


def test_only_one_backend_stays_in_memory_and_the_one_let_go_is_closed():
    closed = []

    class Closing(FakeBackend):
        def close(self):
            closed.append(self.spec.model)

    embedding.BACKENDS["fake"] = Closing
    first, second = EmbeddingSpec("fake", "one", 0.5, 64), EmbeddingSpec("fake", "two", 0.5, 64)
    embed_texts(first, ["alpha beta"])
    embed_texts(first, ["gamma delta"])  # the same backend again: nothing is closed
    assert closed == []
    embed_texts(second, ["alpha beta"])
    assert closed == ["one"]


def test_one_loaded_model_serves_every_layer_asked_of_it():
    built, closed = [], []

    class Shared(FakeBackend):
        def __init__(self, spec):
            super().__init__(spec)
            built.append(spec.model)

        def view(self, spec):
            other = FakeBackend(spec)
            other.view = self.view
            other.close = lambda: closed.append(spec.layer)
            return other

        def close(self):
            closed.append(self.spec.layer)

    embedding.BACKENDS["fake"] = Shared
    low, high = EmbeddingSpec("fake", "big", 0.5, 64), EmbeddingSpec("fake", "big", 0.9, 64)
    embed_texts(low, ["alpha beta"])
    embed_texts(high, ["alpha beta"])
    assert built == ["big"]  # the second layer reuses the loaded model
    embed_texts(EmbeddingSpec("fake", "small", 0.5, 64), ["alpha beta"])
    assert built == ["big", "small"] and sorted(closed) == [0.5, 0.9]
