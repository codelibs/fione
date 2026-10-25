"""Explanations of a model: its training diagnostics, its stored explanation (the explain
job's), and per-row contributions and partial dependence computed on request.

A model id is resolved, then authorized on the model's own project (404 without read
access); a dataset must belong to that project too. Reading is enough for every route here:
an explanation changes nothing (recomputing the stored one is ``POST .../jobs/explain``).

Contributions and partial dependence load the model in this process through ``LiveModels``:
one request at a time (503 ``busy`` with ``Retry-After`` after the wait), and never a model
this install did not sign (409 ``untrusted``; the explain job explains those). The routes
are sync, so they run in the threadpool.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pandas as pd
import pyarrow as pa
from fastapi import APIRouter, Request

from fione.api.deps import Conn, CurrentUser
from fione.api.errors import ApiError, not_found
from fione.api.routes_models import _model
from fione.api.schemas import (
    ContributionsIn,
    IdPath,
    PartialDependenceIn,
    contributions_out,
    diagnostics_out,
    explanation_out,
    partial_dependence_out,
)
from fione.engine import explain
from fione.engine.artifact import UntrustedArtifactError
from fione.engine.model import TrainedModel
from fione.jobs.store import JobStatus
from fione.models import explanations
from fione.models.live import Busy, Untrusted
from fione.models.service import ModelRecord
from fione.modules.registry import redact
from fione.predict.batch import PredictInputError, check_inputs
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import Dataset

router = APIRouter(tags=["explanations"])

RETRY_AFTER_SECS = 5
ACTIVE = (JobStatus.QUEUED, JobStatus.RUNNING)


@router.get("/models/{model_id}/diagnostics")
def diagnostics(model_id: IdPath, user: CurrentUser, conn: Conn) -> dict:
    """The model's training-time diagnostics (confusion matrix, per-class metrics, ROC/PR,
    calibration or residuals), or ``null`` for a model trained before they existed."""
    return diagnostics_out(_model(conn, user, model_id, "read"))


@router.get("/models/{model_id}/explanations")
def stored_explanation(model_id: IdPath, user: CurrentUser, conn: Conn) -> dict:
    """The explain job's global importance and partial dependence curves. ``status`` is
    ``done`` when one is stored and no newer explain job is queued or running, otherwise the
    latest explain job's status, or ``none``. A stored explanation is returned even while a
    newer job runs."""
    record = _model(conn, user, model_id, "read")
    stored = explanations.get_explanation(conn, record.id)
    job = explanations.latest_explain_job(conn, record.id)
    active = job is not None and job.status in ACTIVE
    if stored is not None and not active:
        status = "done"
    else:
        status = job.status.value if job is not None else "none"
    return explanation_out(record.id, status, job, stored)


@contextmanager
def _explaining() -> Iterator[None]:
    """The errors of an explanation request as API errors; messages without file paths."""
    try:
        yield
    except Untrusted:
        message = (
            "this model was imported without this install's signature;"
            " only the explain job can explain it"
        )
        raise ApiError(409, "untrusted", message) from None
    except Busy:
        message = "another explanation is being computed; try again shortly"
        headers = {"Retry-After": str(RETRY_AFTER_SECS)}
        raise ApiError(503, "busy", message, headers) from None
    except UntrustedArtifactError:
        raise ApiError(409, "conflict", "the model file failed verification") from None
    except ValueError as e:  # PredictInputError, ConfigError and the engine's limits
        if isinstance(e, pa.ArrowException | UnicodeError):
            raise
        raise ApiError(422, "invalid", redact(str(e))) from e


def _dataset(conn, record: ModelRecord, dataset_id: int | None) -> Dataset:
    """``dataset_id``, else the model's training data, checked to be of the model's project
    and to have the model's columns."""
    chosen = record.dataset_id if dataset_id is None else dataset_id
    if chosen is None:
        raise ApiError(422, "invalid", "choose a dataset")
    dataset = projects.get_dataset(conn, chosen)  # DatasetNotFound -> 404
    if dataset.project_id != record.project_id:
        raise not_found("dataset not found")
    present = {column for column, _ in dataset.schema}
    missing = [c for c in explanations.model_columns(record) if c not in present]
    if missing:
        raise ApiError(422, "invalid", f"the dataset lacks the model's columns: {missing}")
    return dataset


def _read(read, *args) -> pd.DataFrame:
    try:
        return read(*args)
    except KeyError:  # storage: the object is gone (its message would name the key)
        raise not_found("dataset not found") from None


def _instances(model: TrainedModel, instances: list[dict]) -> pd.DataFrame:
    """The model's columns of ``instances`` (other keys are ignored, as in Fione Serving)."""
    for i, row in enumerate(instances):
        missing = [c for c in model.columns if c not in row]
        if missing:
            raise PredictInputError(f"instance {i}: missing columns: {missing}")
    return pd.DataFrame({c: [row[c] for row in instances] for c in model.columns})


@router.post("/models/{model_id}/contributions")
def contributions(
    model_id: IdPath, body: ContributionsIn, user: CurrentUser, conn: Conn, request: Request
) -> dict:
    """Each row's contributions per input column, with the bias they add up from to the
    prediction: for the binary positive class, the predicted class (multiclass, unless
    ``class_index`` is given), or the value (regression). Rows are up to 100 ``instances``,
    or ``limit`` rows of ``dataset_id`` from ``offset`` (``row`` numbers them from 0 or
    ``offset``). The values are approximate (combined over the ensemble), but always add up."""
    record = _model(conn, user, model_id, "read")
    live = request.app.state.live_models
    with _explaining():
        live.check(record)
        dataset = None if body.instances is not None else _dataset(conn, record, body.dataset_id)
        with live.use(record) as model:
            if dataset is None:
                frame = _instances(model, body.instances)
            else:
                columns = explanations.model_columns(record)
                frame = _read(
                    ingest.read_dataset_rows,
                    request.app.state.storage,
                    dataset,
                    body.offset,
                    body.limit,
                    columns,
                )
            check_inputs(model, frame)
            c = explain.contributions(model, frame)
        slots = c.slots(body.class_index)
    first = 0 if dataset is None else body.offset
    return contributions_out(record.id, c, slots, first, multiclass=len(c.outputs) > 1)


@router.post("/models/{model_id}/partial-dependence")
def partial_dependence(
    model_id: IdPath, body: PartialDependenceIn, user: CurrentUser, conn: Conn, request: Request
) -> dict:
    """How the model's average output changes as ``column`` varies over a grid of up to
    ``grid`` points, over ``rows`` background rows of ``dataset_id`` (else of the training
    data), with ``ice`` single-row curves for ``outputs[ice_output]``."""
    record = _model(conn, user, model_id, "read")
    live = request.app.state.live_models
    with _explaining():
        live.check(record)
        dataset = _dataset(conn, record, body.dataset_id)
        columns = explanations.model_columns(record)
        with live.use(record) as model:
            background = _read(
                ingest.read_dataset_spread, request.app.state.storage, dataset, body.rows, columns
            )
            check_inputs(model, background)
            curve = explain.partial_dependence(
                model,
                background,
                body.column,
                grid_size=body.grid,
                max_rows=body.rows,
                ice_rows=body.ice,
                class_index=body.class_index,
            )
    return partial_dependence_out(curve)
