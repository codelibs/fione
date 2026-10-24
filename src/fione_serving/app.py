"""The prediction API: ``/invocations``, ``/model``, ``/ping``.

``/invocations`` keeps v1's contract. Each instance is answered on its own and in order, so a
row that cannot be predicted becomes ``{"exception": ...}`` and never fails the request. Rows
are checked in bulk (missing columns, text in numeric columns) and the valid ones are predicted
in a single batch; only if that batch call itself raises is each row predicted separately, to
find the one that fails.
"""

import json
import logging
import os
import threading
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from fione.engine.config import ConfigError
from fione.engine.events import jsonable
from fione.predict.batch import unreadable_numbers
from fione_serving.loader import LoadedModel, load

log = logging.getLogger(__name__)

DEFAULT_MAX_BODY = 10 << 20
DEFAULT_MAX_INSTANCES = 10_000
MAX_DOMAIN = 1000  # categories listed per feature by /model
_SHOWN_CHARS = 50  # of a value echoed back in a row's error


class Rejected(Exception):
    """A request refused as a whole, with its HTTP status."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value < 1:
        raise ValueError(f"{name} must be a whole number of at least 1, got {raw!r}")
    return value


def _refuse_constant(name: str):
    raise ValueError(f"{name} is not valid JSON")


def _exception(message: str) -> dict:
    return {"exception": message}


def _shown(value) -> str:
    text = repr(value)
    return text if len(text) <= _SHOWN_CHARS else text[: _SHOWN_CHARS - 3] + "..."


class Predictor:
    """The loaded model, its ``/model`` description and row-by-row prediction."""

    def __init__(self, loaded: LoadedModel):
        self.model = loaded.model
        self.manifest = loaded.manifest
        self.columns = list(self.model.columns)
        self.classes = (
            jsonable(list(self.model.classes_)) if self.model.classes_ is not None else None
        )
        self.description = self._describe()
        self._lock = threading.Lock()  # one prediction at a time: the libraries use all cores

    def _domain(self, column: str) -> list | None:
        prep = self.model.prep
        values = prep.categories.get(column)
        if values is None and column in prep.frequencies:
            values = list(prep.frequencies[column])
        return values if values is not None and len(values) <= MAX_DOMAIN else None

    def _describe(self) -> dict:
        n_classes = len(self.classes) if self.classes is not None else 1
        category = (
            "Regression"
            if self.classes is None
            else "Binomial"
            if n_classes == 2
            else "Multinomial"
        )
        return {
            "names": [*self.columns, self.model.target],
            "domains": [*(self._domain(c) for c in self.columns), self.classes],
            "responseColumn": self.model.target,
            "category": category,
            "nclasses": n_classes,
            "nfeatures": len(self.columns),
            "uuid": self.manifest.files["model.joblib"][:32],
            "instance": {c: "?" for c in self.columns},
            "engine": "fione",
            "fioneVersion": self.manifest.fione_version,
        }

    def predict(self, instances: list) -> list[dict]:
        """One result per instance, in order: a prediction or ``{"exception": message}``."""
        results: list[dict | None] = [None] * len(instances)
        positions: list[int] = []
        rows: list[dict] = []
        for i, row in enumerate(instances):
            if not isinstance(row, dict):
                results[i] = _exception("each instance must be a JSON object")
                continue
            missing = [c for c in self.columns if c not in row]
            if missing:
                results[i] = _exception(f"missing columns: {missing}")
                continue
            positions.append(i)
            rows.append(row)
        if rows:
            frame = pd.DataFrame({c: [row[c] for row in rows] for c in self.columns})
            self._predict_valid(frame, positions, results)
        return results  # every slot is filled by now

    def _predict_valid(self, frame: pd.DataFrame, positions: list[int], results: list) -> None:
        problems: dict[int, list[str]] = {}
        for column in self.model.prep.numeric_columns:
            values = frame[column]
            for at in np.flatnonzero(unreadable_numbers(values).to_numpy()):
                text = f"column {column!r} must hold a number, but got {_shown(values.iloc[at])}"
                problems.setdefault(int(at), []).append(text)
        for at, messages in problems.items():
            results[positions[at]] = _exception("; ".join(messages))
        keep = [at for at in range(len(frame)) if at not in problems]
        if not keep:
            return
        frame = frame.iloc[keep].reset_index(drop=True)
        slots = [positions[at] for at in keep]
        try:
            outputs = self._predict_frame(frame)
        except Exception:
            log.warning("batch prediction failed, predicting row by row", exc_info=True)
            outputs = [self._predict_one(frame.iloc[[at]]) for at in range(len(frame))]
        for slot, output in zip(slots, outputs, strict=True):
            results[slot] = output

    def _predict_one(self, row: pd.DataFrame) -> dict:
        try:
            return self._predict_frame(row)[0]
        except ConfigError as e:
            return _exception(str(e))
        except Exception as e:
            log.warning("a row could not be predicted: %s", type(e).__name__)
            return _exception(f"prediction failed ({type(e).__name__})")

    def _predict_frame(self, frame: pd.DataFrame) -> list[dict]:
        with self._lock:
            if self.classes is None:
                values = self.model.predict(frame).to_numpy()
                return [{"value": jsonable(float(v))} for v in values]
            proba = self.model.predict_proba(frame).to_numpy()
        best = proba.argmax(axis=1)
        return [
            {
                "label": self.classes[b],
                "index": int(b),
                "class_probabilities": jsonable(p.tolist()),
            }
            for b, p in zip(best, proba, strict=True)
        ]


async def _read_body(request: Request, limit: int) -> bytes:
    """The request body, refused as soon as it is known to be over ``limit`` bytes.

    The Content-Length header is only a first, cheap check: the bytes are counted as they
    arrive, because the header may be absent (chunked) or wrong.
    """
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise Rejected(413, f"the request body is larger than {limit} bytes")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise Rejected(413, f"the request body is larger than {limit} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def _instances(body: bytes, limit: int) -> list:
    try:
        payload = json.loads(body, parse_constant=_refuse_constant)
    except (ValueError, RecursionError):
        raise Rejected(400, "the request body is not valid JSON") from None
    if not isinstance(payload, dict):
        raise Rejected(400, 'the request body must be a JSON object like {"instances": [...]}')
    instances = payload.get("instances")
    if not isinstance(instances, list):
        raise Rejected(400, '"instances" must be a list of objects')
    if len(instances) > limit:
        raise Rejected(413, f"too many instances: at most {limit} per request")
    return instances


def create_app(model_dir: Path | None = None, *, image_tag: str | None = None) -> FastAPI:
    """The app for the model in ``model_dir`` (default ``$FIONE_MODEL_DIR``, else ``/model``).

    ``image_tag`` (default ``$FIONE_IMAGE_TAG``, else ``dev``) is the running image's tag.
    Raises ``ModelLoadError`` if the model cannot be served. Limits come from
    ``FIONE_SERVING_MAX_BODY`` (bytes) and ``FIONE_SERVING_MAX_INSTANCES``, read here.
    """
    model_dir = Path(model_dir or os.environ.get("FIONE_MODEL_DIR") or "/model")
    image_tag = image_tag or os.environ.get("FIONE_IMAGE_TAG") or "dev"
    max_body = _env_int("FIONE_SERVING_MAX_BODY", DEFAULT_MAX_BODY)
    max_instances = _env_int("FIONE_SERVING_MAX_INSTANCES", DEFAULT_MAX_INSTANCES)
    loaded = load(model_dir, image_tag)
    predictor = Predictor(loaded)

    app = FastAPI(title="Fione Serving", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.loaded = loaded

    @app.exception_handler(Rejected)
    async def _rejected(request: Request, e: Rejected) -> JSONResponse:
        return JSONResponse({"error": e.message}, status_code=e.status)

    @app.get("/")
    @app.get("/ping")
    async def ping() -> Response:
        return Response()

    @app.get("/model")
    async def model() -> JSONResponse:
        return JSONResponse(predictor.description)

    @app.post("/invocations")
    async def invocations(request: Request) -> JSONResponse:
        instances = _instances(await _read_body(request, max_body), max_instances)
        predictions = await run_in_threadpool(predictor.predict, instances)
        return JSONResponse({"predictions": predictions})

    return app
