"""Datasets of a project: upload, metadata, download, preview and profiles (EDA).

Every dataset id is checked against the project in the path: a dataset of another project
is a 404, whatever the caller may see elsewhere.
"""

import datetime
import math
from dataclasses import asdict
from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Query, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from fione.api.deps import Conn, ProjectContext, project_access
from fione.api.downloads import attachment, content_disposition
from fione.api.errors import ApiError, not_found, service_errors
from fione.api.schemas import IdPath, dataset_out
from fione.data.profile import profile_dataset
from fione.engine.events import jsonable
from fione.projects import service
from fione.projects.ingest import export_csv, ingest_csv, read_dataset_sample
from fione.projects.service import Dataset, DatasetNotFound, DatasetType

router = APIRouter(prefix="/projects/{project_id}/datasets", tags=["datasets"])

MAX_PREVIEW_ROWS = 200
# Profiles describe the first rows of a dataset, so a request costs bounded time and memory.
PROFILE_SAMPLE_ROWS = 100_000
_MAX_NAME_LEN = 100

Reader = Annotated[ProjectContext, Depends(project_access("read"))]
Writer = Annotated[ProjectContext, Depends(project_access("write"))]

_UPLOAD_SCHEMA = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["name", "type", "file"],
                    "properties": {
                        "name": {"type": "string", "maxLength": _MAX_NAME_LEN},
                        "type": {"type": "string", "enum": [t.value for t in DatasetType]},
                        "file": {"type": "string", "format": "binary"},
                    },
                }
            }
        },
    }
}


def _dataset(conn, ctx: ProjectContext, dataset_id: int) -> Dataset:
    try:
        dataset = service.get_dataset(conn, dataset_id)
    except DatasetNotFound:
        raise not_found("dataset not found") from None
    if dataset.project_id != ctx.project.id:
        raise not_found("dataset not found")
    return dataset


@router.get("")
def list_datasets(ctx: Reader, conn: Conn) -> list[dict]:
    return [dataset_out(d) for d in service.list_datasets(conn, ctx.project.id)]


def _form_text(form, field: str) -> str:
    value = form.get(field)
    if not isinstance(value, str):
        raise ApiError(422, "invalid", f"{field}: a text field is required")
    return value.strip()


@router.post("", status_code=201, openapi_extra=_UPLOAD_SCHEMA)
async def upload_dataset(ctx: Writer, request: Request, conn: Conn) -> dict:
    """Upload a CSV (multipart fields ``name``, ``type`` = train|test|predict, ``file``).

    The form is parsed only after authorization (no body parameters are declared, so FastAPI
    does not read the body first); the file is streamed through ingest, which converts it to
    Parquet. Over ``max_upload_bytes`` -> 413 with nothing stored.
    """
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise ApiError(415, "unsupported_media_type", "Content-Type must be multipart/form-data")
    form = await request.form(max_files=1, max_fields=2)
    try:
        name = _form_text(form, "name")
        if not 1 <= len(name) <= _MAX_NAME_LEN:
            raise ApiError(422, "invalid", f"name must be 1-{_MAX_NAME_LEN} characters")
        type_ = _form_text(form, "type")
        if type_ not in {t.value for t in DatasetType}:
            raise ApiError(422, "invalid", "type must be train, test or predict")
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise ApiError(422, "invalid", "file: a file field is required")
        settings = request.app.state.settings
        storage = request.app.state.storage

        def ingest() -> Dataset:
            try:
                return ingest_csv(
                    storage,
                    conn,
                    ctx.project.id,
                    name,
                    DatasetType(type_),
                    upload.file,
                    max_bytes=settings.max_upload_bytes,
                )
            except ValueError as e:
                if str(e) == "too large":  # ingest's size refusal
                    raise ApiError(
                        413, "too_large", f"the file exceeds {settings.max_upload_bytes} bytes"
                    ) from e
                raise

        dataset = await run_in_threadpool(ingest)
    finally:
        await form.close()
    return dataset_out(dataset, schema=True)


@router.get("/{dataset_id}")
def get_dataset(dataset_id: IdPath, ctx: Reader, conn: Conn) -> dict:
    return dataset_out(_dataset(conn, ctx, dataset_id), schema=True)


@router.get("/{dataset_id}/download")
def download_dataset(dataset_id: IdPath, ctx: Reader, conn: Conn, request: Request):
    """The dataset as UTF-8 CSV, streamed."""
    dataset = _dataset(conn, ctx, dataset_id)
    return attachment(
        export_csv(request.app.state.storage, dataset),
        "text/csv; charset=utf-8",
        content_disposition(dataset.name),
    )


def _cell(value):
    """A JSON value: missing values as null, dates and times as ISO 8601 strings."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, datetime.date | datetime.time):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


@router.get("/{dataset_id}/preview")
def preview_dataset(
    dataset_id: IdPath,
    ctx: Reader,
    conn: Conn,
    request: Request,
    rows: int = Query(50, ge=1, le=MAX_PREVIEW_ROWS),
) -> dict:
    """The first ``rows`` rows (at most 200) as ``{"columns": [...], "rows": [[...]]}``."""
    dataset = _dataset(conn, ctx, dataset_id)
    frame = read_dataset_sample(request.app.state.storage, dataset, max_rows=rows)
    return {
        "columns": list(frame.columns),
        "rows": [
            [_cell(v) for v in row]
            for row in frame.astype(object).itertuples(index=False, name=None)
        ],
    }


@router.get("/{dataset_id}/profile")
def profile(
    dataset_id: IdPath,
    ctx: Reader,
    conn: Conn,
    request: Request,
    target: str | None = Query(None, max_length=1000),
) -> dict:
    """Profile (EDA) of the first 100,000 rows: kinds, statistics, histograms, correlations
    and, with ``target``, leak suspects. For the UI, so ``top_values`` (raw cell values)
    are included, unlike the LLM-facing tools. ``n_rows`` is the whole dataset's row count,
    ``sample_rows`` the number profiled."""
    dataset = _dataset(conn, ctx, dataset_id)
    frame = read_dataset_sample(request.app.state.storage, dataset, max_rows=PROFILE_SAMPLE_ROWS)
    with service_errors():
        result = profile_dataset(frame, target)
    return jsonable({**asdict(result), "n_rows": dataset.n_rows, "sample_rows": len(frame)})


@router.get("/{dataset_id}/columns/{column:path}")
def column_profile(
    dataset_id: IdPath, column: str, ctx: Reader, conn: Conn, request: Request
) -> dict:
    """One column's profile with its histogram, from the same sample as ``/profile``."""
    dataset = _dataset(conn, ctx, dataset_id)
    if column not in {name for name, _ in dataset.schema}:
        raise not_found("column not found")
    frame = read_dataset_sample(
        request.app.state.storage, dataset, max_rows=PROFILE_SAMPLE_ROWS, columns=[column]
    )
    return jsonable(asdict(profile_dataset(frame).columns[0]))


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: IdPath, ctx: Writer, conn: Conn, request: Request) -> None:
    dataset = _dataset(conn, ctx, dataset_id)
    service.delete_dataset(conn, request.app.state.storage, dataset.id)
