"""The ``automl`` job: train on a dataset, save the model artifact, record it in ``models``."""

import dataclasses
import logging
import time
import uuid
from datetime import datetime

from fione.config import load_secret
from fione.engine.artifact import save_model
from fione.engine.automl import AutoML
from fione.engine.config import ConfigError, NoModelError, TrainConfig
from fione.jobs import store
from fione.jobs.handlers import JobContext, JobUserError, register_handler
from fione.models import service as models_service
from fione.projects import service as projects
from fione.projects.ingest import IngestError, read_dataset

log = logging.getLogger(__name__)

# Raised for what the user can fix; JobAbort and everything else keep their own handling.
USER_ERRORS = (ConfigError, NoModelError, IngestError)


def _queue_explain(ctx: JobContext, model_id: int) -> int | None:
    """Queue the explain job of the new model on its training data, when the settings ask for
    it; its id, or None. A failure is logged, never raised: the model is trained."""
    if not ctx.settings.explain_after_training:
        return None
    try:
        payload = {"model_id": model_id, "dataset_id": None}
        return store.enqueue(ctx.conn, "explain", ctx.job.project_id, ctx.job.owner_id, payload).id
    except Exception:
        log.exception("could not queue the explain job of model %s", model_id)
        return None


@register_handler("automl")
def automl(ctx: JobContext) -> None:
    """Train, save and record a model; a cancelled run leaves no row and no objects.

    Cancellation is read forced (not from the 0.5 s cache) before saving and again after the
    row is inserted, the second time undoing the row and objects, so the worker's own forced
    read at the end can only differ if a cancel lands in the microseconds between the two. A
    SIGKILL during ``save_model`` can leave unreferenced objects under the project prefix;
    ``delete_project`` removes them.

    The explain job (``FIONE_EXPLAIN_AFTER_TRAINING``) is queued only once the last cancel check
    has passed, so a cancelled run never leaves one for a deleted model.

    The diagnostics go to the row only: the artifact is saved without them, so the serving
    bundle (the artifact as stored) carries none of the class labels or target values in them.
    """
    payload = ctx.job.payload
    project_id = ctx.job.project_id
    try:
        dataset = projects.get_dataset(ctx.conn, payload["dataset_id"])
        if dataset.project_id != project_id:
            raise projects.DatasetNotFound(dataset.id)
    except projects.DatasetNotFound as e:
        raise JobUserError("the dataset no longer exists") from e
    start = time.monotonic()
    try:
        config = TrainConfig.from_dict(payload["config"])
        frame = read_dataset(ctx.storage, dataset)
        model = AutoML(config, emit=ctx.emit, should_stop=ctx.should_stop).fit(frame)
    except USER_ERRORS as e:
        raise JobUserError(str(e)) from e
    elapsed = time.monotonic() - start
    # A cancelled run is discarded whole: the worker records the job as CANCELLED.
    if model.stop_reason == "cancelled" or ctx.should_stop(force=True):
        return

    prefix = f"projects/{project_id}/models/{uuid.uuid4().hex}/"
    try:
        save_model(
            dataclasses.replace(model, diagnostics=None),
            ctx.storage,
            prefix,
            load_secret(ctx.settings),
            image_tag=ctx.settings.image_tag,
        )
        record = models_service.add_model(
            ctx.conn,
            project_id=project_id,
            dataset_id=dataset.id,
            job_id=ctx.job.id,
            name=payload.get("name") or f"{config.target} model {datetime.now():%Y-%m-%d %H:%M}",
            model=model,
            storage_prefix=prefix,
        )
    except BaseException:
        try:
            ctx.storage.delete_prefix(prefix)
        except Exception:
            # Never mask the original error (a JobAbort must stay a JobAbort).
            log.exception("could not remove the objects under %s", prefix)
        raise
    if ctx.should_stop(force=True):  # cancelled while saving: take the model back out
        models_service.delete_model(ctx.conn, ctx.storage, record.id)
        return
    result = {
        "model_id": record.id,
        "stop_reason": record.stop_reason,
        "best_model": record.best_model,
        "metrics": record.metrics,
        "elapsed": elapsed,
        "explain_job_id": _queue_explain(ctx, record.id),
    }
    if record.stop_reason == "error":
        result["degraded"] = True
    ctx.set_result(result)
