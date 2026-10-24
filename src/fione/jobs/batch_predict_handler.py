"""The ``batch_predict`` job: run a dataset through a model into a new ``predict`` dataset."""

import logging
import time
from collections.abc import Iterator

import pandas as pd

from fione.config import load_secret
from fione.engine.artifact import UntrustedArtifactError
from fione.engine.config import ConfigError
from fione.engine.events import Event
from fione.jobs.handlers import JobContext, JobUserError, register_handler
from fione.models import service as models_service
from fione.predict.batch import CHUNK_ROWS, PredictInputError, included_columns, predict_chunks
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import DatasetType

log = logging.getLogger(__name__)

# Raised for what the user can fix; JobAbort and everything else keep their own handling.
USER_ERRORS = (PredictInputError, ConfigError, ingest.IngestError)


class _Cancelled(Exception):
    """Internal: the job was cancelled while the predictions were being written."""


def _watched(ctx: JobContext, chunks: Iterator[pd.DataFrame], total: int) -> Iterator[pd.DataFrame]:
    """The chunks, with a stop check before each and a progress event after each.

    The last check is read forced, right before the caller stores the result, so a cancel is
    seen up to there and only one landing during the store itself needs the later undo.
    """
    done = 0
    while True:
        if ctx.should_stop():
            raise _Cancelled
        chunk = next(chunks, None)
        if chunk is None:
            break
        yield chunk
        done += len(chunk)
        message = f"predicted {done} of {total} rows"
        ctx.emit(Event("notice", data={"message": message, "rows_done": done, "rows_total": total}))
    if ctx.should_stop(force=True):
        raise _Cancelled


@register_handler("batch_predict")
def batch_predict(ctx: JobContext) -> None:
    """Predict, store the result as a ``predict`` dataset and record it.

    A cancelled run leaves no dataset row and no objects: the stop flag is read forced right
    before the result is stored and again after the row is inserted, the second time undoing
    the row and the object. A SIGKILL during the store can leave an unreferenced object under
    the project prefix; ``delete_project`` removes it.
    """
    payload = ctx.job.payload
    project_id = ctx.job.project_id
    try:
        record = models_service.get_model(ctx.conn, payload["model_id"])
        if record.project_id != project_id:
            raise models_service.ModelNotFound(record.id)
    except models_service.ModelNotFound as e:
        raise JobUserError("the model no longer exists") from e
    try:
        dataset = projects.get_dataset(ctx.conn, payload["dataset_id"])
        if dataset.project_id != project_id:
            raise projects.DatasetNotFound(dataset.id)
    except projects.DatasetNotFound as e:
        raise JobUserError("the dataset no longer exists") from e
    start = time.monotonic()
    try:
        model = models_service.load_trained(ctx.storage, record, load_secret(ctx.settings))
    except UntrustedArtifactError as e:
        raise JobUserError("the model file failed verification") from e
    try:
        frame = ingest.read_dataset(ctx.storage, dataset, nullable_dtypes=True)
        chunks = predict_chunks(model, frame, payload.get("include_columns"), chunk_rows=CHUNK_ROWS)
        # A column that is empty in the first chunk still needs the type its source has.
        source = ingest.read_schema(ctx.storage, dataset)
        kept = included_columns(model, list(frame.columns), payload.get("include_columns"))
        fallback = {out: source.field(column).type for out, column in kept.items()}
        ctx.emit(
            Event(
                "started",
                data={"model_id": record.id, "dataset_id": dataset.id, "n_rows": len(frame)},
            )
        )
        created = ingest.ingest_batches(
            ctx.storage,
            ctx.conn,
            project_id,
            payload.get("name") or f"predict_{dataset.name}",
            DatasetType.PREDICT,
            _watched(ctx, chunks, len(frame)),
            fallback_types=fallback,
        )
    except _Cancelled:  # nothing was stored: the worker records the job as CANCELLED
        return
    except USER_ERRORS as e:
        raise JobUserError(str(e)) from e
    try:
        if ctx.should_stop(force=True):  # cancelled while storing: take the dataset back out
            projects.delete_dataset(ctx.conn, ctx.storage, created.id)
            return
        ctx.set_result(
            {
                "dataset_id": created.id,
                "n_rows": created.n_rows,
                "elapsed": time.monotonic() - start,
            }
        )
        ctx.emit(Event("finished", data={"dataset_id": created.id, "n_rows": created.n_rows}))
    except BaseException:
        try:
            projects.delete_dataset(ctx.conn, ctx.storage, created.id)
        except Exception:
            # Never mask the original error (a JobAbort must stay a JobAbort).
            log.exception("could not remove dataset %s", created.id)
        raise
