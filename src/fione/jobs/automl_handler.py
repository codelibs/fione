"""The ``automl`` job: train on a dataset, save the model artifact, record it in ``models``."""

import time
import uuid
from datetime import datetime

from fione.config import load_secret
from fione.engine.artifact import save_model
from fione.engine.automl import AutoML
from fione.engine.config import ConfigError, NoModelError, TrainConfig
from fione.jobs.handlers import JobContext, JobUserError, register_handler
from fione.models import service as models_service
from fione.projects import service as projects
from fione.projects.ingest import IngestError, read_dataset

# Raised for what the user can fix; JobAbort and everything else keep their own handling.
USER_ERRORS = (ConfigError, NoModelError, IngestError)


@register_handler("automl")
def automl(ctx: JobContext) -> None:
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
    if model.stop_reason == "cancelled" or ctx.should_stop():
        return

    prefix = f"projects/{project_id}/models/{uuid.uuid4().hex}/"
    save_model(
        model, ctx.storage, prefix, load_secret(ctx.settings), image_tag=ctx.settings.image_tag
    )
    try:
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
        ctx.storage.delete_prefix(prefix)
        raise
    result = {
        "model_id": record.id,
        "stop_reason": record.stop_reason,
        "best_model": record.best_model,
        "metrics": record.metrics,
        "elapsed": elapsed,
    }
    if record.stop_reason == "error":
        result["degraded"] = True
    ctx.set_result(result)
