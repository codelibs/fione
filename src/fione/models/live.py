"""Models loaded in the web process, for small synchronous explanation requests.

Contributions of a few rows and one partial dependence curve run here (everything larger
runs in jobs). They cost far more than a prediction, so one request at a time computes:
the others wait for the slot up to ``wait_secs`` and then get ``Busy``. At most
``max_models`` models and ``max_bytes`` of artifact bytes stay loaded, least recently used
dropped first. Loaded models predict on ``explain.THREADS`` threads, not on the threads
they were trained with.

Only models this install signed are loaded: loading a pickle runs its code, and a viewer
can ask for an explanation. Imports not vouched for (``trusted=0``) raise ``Untrusted``
before anything is read; the explain job, which needs write access, explains them.
"""

import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager

from fione.engine import explain
from fione.engine.artifact import MODEL_FILE, UntrustedArtifactError
from fione.engine.model import TrainedModel
from fione.models import service
from fione.models.service import ModelNotFound, ModelRecord
from fione.storage import Storage


class Busy(Exception):
    """Another explanation request kept the slot for the whole wait."""


class Untrusted(Exception):
    """The model is an import this install did not sign (``trusted=0``)."""


class LiveModels:
    def __init__(
        self,
        storage: Storage,
        secret: bytes,
        *,
        max_models: int = 2,
        max_bytes: int = 512 << 20,
        wait_secs: float = 15.0,
    ):
        self.storage = storage
        self.secret = secret
        self.max_models = max_models
        self.max_bytes = max_bytes
        self.wait_secs = wait_secs
        self.slot = threading.BoundedSemaphore(1)
        # (id, storage prefix) -> (model, artifact bytes); only changed while holding the slot
        self._models: OrderedDict[tuple[int, str], tuple[TrainedModel, int]] = OrderedDict()

    @contextmanager
    def use(self, record: ModelRecord) -> Iterator[TrainedModel]:
        """The record's model, with the slot held until the block ends.

        ``Untrusted`` for a ``trusted=0`` record, ``Busy`` when the slot stays taken for
        ``wait_secs``, ``ModelNotFound`` when its files are gone, ``UntrustedArtifactError``
        when they fail verification.
        """
        self.check(record)
        if not self.slot.acquire(timeout=self.wait_secs):
            raise Busy("another explanation is being computed")
        try:
            yield self._get(record)
        finally:
            self.slot.release()

    @staticmethod
    def check(record: ModelRecord) -> None:
        """``Untrusted`` unless this process may load the record's model."""
        if not record.trusted:
            raise Untrusted(f"model {record.id} is an import this install did not sign")

    def _get(self, record: ModelRecord) -> TrainedModel:
        key = (record.id, record.storage_prefix)
        if key in self._models:
            self._models.move_to_end(key)
            return self._models[key][0]
        try:
            size = self.storage.size(record.storage_prefix + MODEL_FILE)
        except KeyError:
            raise ModelNotFound(record.id) from None
        keep = size <= self.max_bytes
        if keep:  # make room first, so the old ones are not held while this one loads
            self._evict(self.max_models - 1, self.max_bytes - size)
        try:
            model = service.load_trained(self.storage, record, self.secret)
        except UntrustedArtifactError as e:
            if isinstance(e.__cause__, KeyError):  # the files went away meanwhile
                raise ModelNotFound(record.id) from None
            raise
        explain.cap_threads(model, explain.THREADS)
        if keep:
            self._models[key] = (model, size)
        return model

    def _evict(self, models: int, size: int) -> None:
        """Drop the least recently used until at most ``models`` of at most ``size`` bytes
        are left."""
        while self._models and (
            len(self._models) > models or sum(s for _, s in self._models.values()) > size
        ):
            self._models.popitem(last=False)

    def __len__(self) -> int:
        return len(self._models)
