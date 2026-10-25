"""Explanations of a model: its training diagnostics, its stored explanation (the explain
job's), and per-row contributions and partial dependence computed on request.

A model id is resolved, then authorized on the model's own project (404 without read
access); a dataset must belong to that project too. Reading is enough for every route here:
an explanation changes nothing (recomputing the stored one is ``POST .../jobs/explain``).

Contributions and partial dependence load the model in this process through ``LiveModels``:
one request at a time, a few more waiting (503 ``busy`` with ``Retry-After`` beyond them or
after the wait). The explain job (``POST .../jobs/explain``, write access) explains what is
refused here: a model this install did not sign (409 ``untrusted``), a model whose artifact
is over the loaded-model budget of 512 MiB (409 ``too_large``), and more rows than a wide
model allows at a time (422). Partial dependence on a wide model averages over fewer
background rows (``n_rows`` says how many). The routes are sync, so they run in the
threadpool.
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
    MAX_CONTRIBUTION_ROWS,
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
from fione.models.live import Busy, TooLarge, Untrusted
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
    except TooLarge:
        message = "this model is too large to explain here; use the explain job"
        raise ApiError(409, "too_large", message) from None
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


def _read(read, *args, **kwargs) -> pd.DataFrame:
    try:
        return read(*args, **kwargs)
    except KeyError:  # storage: the object is gone (its message would name the key)
        raise not_found("dataset not found") from None


def _instances(model: TrainedModel, instances: list[dict]) -> pd.DataFrame:
    """The model's columns of ``instances`` (other keys are ignored, as in Fione Serving).
    A numeric column takes no ``true``/``false``."""
    numeric = set(model.prep.numeric_columns)
    for i, row in enumerate(instances):
        missing = [c for c in model.columns if c not in row]
        if missing:
            raise PredictInputError(f"instance {i}: missing columns: {missing}")
        flags = [c for c in model.columns if c in numeric and isinstance(row[c], bool)]
        if flags:
            raise PredictInputError(f"instance {i}: numbers expected, not true or false: {flags}")
    return pd.DataFrame({c: [row[c] for row in instances] for c in model.columns})


def _check_request(model: TrainedModel, rows: int, class_index: int | None) -> None:
    """Refuse, before any work, more rows than the model's width allows here, and a
    ``class_index`` the model has no output for."""
    allowed = explain.contribution_rows(model, MAX_CONTRIBUTION_ROWS)
    if rows > allowed:
        if allowed == 0:
            message = "this model is too wide to explain here; use the explain job"
        else:
            message = (
                f"this model is explained at most {allowed} rows at a time here;"
                " the explain job covers more"
            )
        raise ApiError(422, "invalid", message)
    outputs = len(explain.explained_outputs(model))
    if class_index is not None and class_index >= outputs:
        raise ApiError(422, "invalid", f"class_index must be an integer in 0..{outputs - 1}")


@router.post("/models/{model_id}/contributions")
def contributions(
    model_id: IdPath, body: ContributionsIn, user: CurrentUser, conn: Conn, request: Request
) -> dict:
    """Each row's contributions per input column, with the bias they add up from to the
    prediction: for the binary positive class, the predicted class (multiclass, unless
    ``class_index`` is given), or the value (regression). Rows are up to 100 ``instances``,
    or ``limit`` rows of ``dataset_id`` from ``offset`` (``row`` numbers them from 0 or
    ``offset``); a model with many classes x columns allows fewer (422). The values are
    approximate (combined over the ensemble), but always add up. Instances' values are
    scalars; numeric columns take numbers, not ``true``/``false``."""
    record = _model(conn, user, model_id, "read")
    live = request.app.state.live_models
    with _explaining():
        live.check(record)
        dataset = None if body.instances is not None else _dataset(conn, record, body.dataset_id)
        with live.use(record) as model:
            asked = body.limit if body.instances is None else len(body.instances)
            _check_request(model, asked, body.class_index)
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
    data; fewer for a wide model), with ``ice`` single-row curves for ``outputs[ice_output]``.
    The background is read from the first rows of up to 8 row groups spread over the file."""
    record = _model(conn, user, model_id, "read")
    live = request.app.state.live_models
    with _explaining():
        live.check(record)
        dataset = _dataset(conn, record, body.dataset_id)
        columns = explanations.model_columns(record)
        with live.use(record) as model:
            rows = explain.pd_rows(model, body.rows, body.grid)  # a wide model gets fewer
            background = _read(
                ingest.read_dataset_spread,
                request.app.state.storage,
                dataset,
                rows,
                columns,
                per_group=rows,  # the head of each spread row group, not the whole groups
            )
            check_inputs(model, background)
            curve = explain.partial_dependence(
                model,
                background,
                body.column,
                grid_size=body.grid,
                max_rows=rows,
                ice_rows=body.ice,
                class_index=body.class_index,
            )
    return partial_dependence_out(curve)
