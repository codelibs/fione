"""The ``export_models`` job: every model of a project in one zip of per-model export zips."""

import logging
import tempfile
import zipfile
from contextlib import closing
from typing import BinaryIO

from fione.engine.events import Event
from fione.jobs.handlers import JobContext, JobUserError, register_handler
from fione.models import service as models_service
from fione.models.transfer import export_model

log = logging.getLogger(__name__)


def _build(ctx: JobContext, records: list[models_service.ModelRecord], out: BinaryIO) -> bool:
    """Write the outer zip to ``out``; False if the job was cancelled before it was complete."""
    total = len(records)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as outer:
        for done, record in enumerate(records, start=1):
            if ctx.should_stop():
                return False
            info = zipfile.ZipInfo(f"model-{record.id}.zip", date_time=(1980, 1, 1, 0, 0, 0))
            try:
                with outer.open(info, "w", force_zip64=True) as member:
                    with closing(export_model(ctx.storage, record)) as chunks:
                        for chunk in chunks:
                            member.write(chunk)
            except models_service.ModelNotFound as e:
                raise JobUserError(
                    f"model {record.id} ({record.name}): its files are missing"
                ) from e
            message = f"exported {done} of {total} models"
            ctx.emit(
                Event(
                    "notice",
                    data={"message": message, "models_done": done, "models_total": total},
                )
            )
    return True


@register_handler("export_models")
def export_models(ctx: JobContext) -> None:
    """Store ``projects/<id>/exports/<job id>.zip``; a cancelled run leaves no object.

    The zip is built in a temp file and stored only after a forced stop check; a cancel landing
    during the store, or a failure after it, deletes the object again. Old exports are not
    cleaned up here: ``delete_project`` removes them with the project.
    """
    project_id = ctx.job.project_id
    records = models_service.list_models(ctx.conn, project_id)
    if not records:
        raise JobUserError("this project has no models")
    key = f"projects/{project_id}/exports/{ctx.job.id}.zip"
    with tempfile.TemporaryFile(prefix="fione-export-") as out:
        if not _build(ctx, records, out):
            return
        size = out.tell()
        out.seek(0)
        if ctx.should_stop(force=True):
            return
        try:
            ctx.storage.put(key, out)
            if ctx.should_stop(force=True):  # cancelled while storing: take it back out
                ctx.storage.delete(key)
                return
            ctx.set_result({"key": key, "n_models": len(records), "bytes": size})
            ctx.emit(Event("finished", data={"key": key, "n_models": len(records)}))
        except BaseException:
            try:
                ctx.storage.delete(key)
            except Exception:
                # Never mask the original error (a JobAbort must stay a JobAbort).
                log.exception("could not remove %s", key)
            raise
