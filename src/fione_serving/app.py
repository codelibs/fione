"""The prediction API: ``/invocations``, ``/model``, ``/ping``.

``/invocations`` keeps v1's contract. Each instance is answered on its own and in order, so a
row that cannot be predicted becomes ``{"exception": ...}`` and never fails the request. Rows
are checked in bulk (missing columns, text in numeric columns) and the valid ones are predicted
in a single batch; only if that batch call itself raises is each row predicted separately, to
find the one that fails.

With ``"contributions": true`` each predicted row also gets its contributions, computed in the
same call as its prediction. Such requests have their own instance cap and a cap on how many
run at once (503 beyond it); without the key, or with ``false``, nothing changes.
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

from fione.engine import explain
from fione.engine.config import ConfigError
from fione.engine.events import jsonable
from fione.predict.batch import encodable, unreadable_numbers
from fione_serving.loader import LoadedModel, load

log = logging.getLogger(__name__)

DEFAULT_MAX_BODY = 10 << 20
DEFAULT_MAX_INSTANCES = 10_000
DEFAULT_MAX_CONTRIBUTION_INSTANCES = 100  # as the Fione API; plain predictions wait on them
DEFAULT_MAX_CONTRIBUTION_REQUESTS = 2  # contribution requests in flight; more get 503
MAX_DOMAIN = 1000  # categories listed per feature by /model
_SHOWN_CHARS = 50  # of a value echoed back in a row's error


class Rejected(Exception):
    """A request refused as a whole, with its HTTP status."""

    def __init__(self, status: int, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers


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
        self._lock = threading.Lock()  # one prediction at a time: the libraries use several cores

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

    def predict(self, instances: list, *, contributions: bool = False) -> list[dict]:
        """One result per instance, in order: a prediction or ``{"exception": message}``.

        With ``contributions``, each prediction also has ``"contributions"``: ``{"bias": b,
        "columns": {column: value}}`` for the output it explains (the positive class's
        probability, the predicted class's, or the value), in ``model.columns`` order.
        """
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
            broken = [c for c in self.columns if isinstance(row[c], str) and not encodable(row[c])]
            if broken:  # pandas cannot hold such text, so the row leaves the batch here
                results[i] = _exception(f"invalid text in column {_shown(broken[0])}")
                continue
            positions.append(i)
            rows.append(row)
        if rows:
            frame = pd.DataFrame({c: [row[c] for row in rows] for c in self.columns})
            self._predict_valid(frame, positions, results, contributions)
        return results  # every slot is filled by now

    def _predict_valid(
        self, frame: pd.DataFrame, positions: list[int], results: list, contributions: bool
    ) -> None:
        problems: dict[int, list[str]] = {}
        for column in self.model.prep.numeric_columns:
            values = frame[column]
            for at in np.flatnonzero(unreadable_numbers(values).to_numpy()):
                text = (
                    f"column {_shown(column)} must hold a number, but got {_shown(values.iloc[at])}"
                )
                problems.setdefault(int(at), []).append(text)
        for at, messages in problems.items():
            results[positions[at]] = _exception("; ".join(messages))
        keep = [at for at in range(len(frame)) if at not in problems]
        if not keep:
            return
        frame = frame.iloc[keep].reset_index(drop=True)
        slots = [positions[at] for at in keep]
        outputs = self._predict_split(frame, contributions, top=True)
        for slot, output in zip(slots, outputs, strict=True):
            results[slot] = output

    def _predict_split(
        self, frame: pd.DataFrame, contributions: bool, *, top: bool = False
    ) -> list[dict]:
        """Predict ``frame`` in one call; if that raises, bisect to find the rows that fail.

        k failing rows among n cost O(k log n) calls (a linear row-by-row fallback would let
        one bad row make the server predict every row of the request one at a time).
        """
        try:
            return self._predict_frame(frame, contributions)
        except Exception as e:
            if top:
                log.warning("batch prediction failed, isolating the failing rows", exc_info=True)
            if len(frame) == 1:
                return [self._failure(e)]
            middle = len(frame) // 2
            return self._predict_split(frame.iloc[:middle], contributions) + self._predict_split(
                frame.iloc[middle:], contributions
            )

    @staticmethod
    def _failure(e: Exception) -> dict:
        if isinstance(e, ConfigError):
            return _exception(str(e))
        log.debug("a row could not be predicted: %s", type(e).__name__)
        return _exception(f"prediction failed ({type(e).__name__})")

    def _predict_frame(self, frame: pd.DataFrame, contributions: bool = False) -> list[dict]:
        with self._lock:
            if self.classes is None:
                output = self.model.predict(frame).to_numpy()
            else:
                output = self.model.predict_proba(frame).to_numpy()
            explained = explain.contributions(self.model, frame) if contributions else None
        if self.classes is None:
            rows = [{"value": jsonable(float(v))} for v in output]
            best = np.zeros(len(rows), dtype=int)
        else:
            best = output.argmax(axis=1)
            rows = [
                {
                    "label": self.classes[b],
                    "index": int(b),
                    "class_probabilities": jsonable(p.tolist()),
                }
                for b, p in zip(best, output, strict=True)
            ]
        if explained is not None:
            # One output (binary: the positive class; regression) or one per class, where the
            # row explains the class it predicts: its index, not the contributions' own argmax.
            outputs = best if len(explained.outputs) > 1 else np.zeros(len(rows), dtype=int)
            for at, (row, output) in enumerate(zip(rows, outputs, strict=True)):
                values = jsonable(explained.values[at, output].tolist())
                row["contributions"] = {
                    "bias": jsonable(float(explained.bias[at, output])),
                    "columns": dict(zip(self.columns, values, strict=True)),
                }
        return rows


async def _read_body(request: Request, limit: int) -> bytes:
    """The request body, refused as soon as it is known to be over ``limit`` bytes.

    The Content-Length header is only a first, cheap check: the bytes are counted as they
    arrive, because the header may be absent (chunked) or wrong.
    """
    declared = request.headers.get("content-length", "")
    if declared.isascii() and declared.isdigit() and int(declared) > limit:
        raise Rejected(413, f"the request body is larger than {limit} bytes")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise Rejected(413, f"the request body is larger than {limit} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def _request(body: bytes, max_instances: int, max_contribution_instances: int) -> tuple[list, bool]:
    """The request's instances, and whether it asks for their contributions."""
    try:
        payload = json.loads(body, parse_constant=_refuse_constant)
    except (ValueError, RecursionError):
        raise Rejected(400, "the request body is not valid JSON") from None
    if not isinstance(payload, dict):
        raise Rejected(400, 'the request body must be a JSON object like {"instances": [...]}')
    instances = payload.get("instances")
    if not isinstance(instances, list):
        raise Rejected(400, '"instances" must be a list of objects')
    if len(instances) > max_instances:
        raise Rejected(413, f"too many instances: at most {max_instances} per request")
    contributions = payload.get("contributions")
    if contributions is None:  # absent, or null as typed clients send an unset field
        contributions = False
    if not isinstance(contributions, bool):
        raise Rejected(400, '"contributions" must be true or false')
    if contributions and len(instances) > max_contribution_instances:
        raise Rejected(
            413,
            f"too many instances with contributions: at most {max_contribution_instances} "
            "per request",
        )
    return instances, contributions


def _check_width(predictor: Predictor, n_instances: int) -> None:
    """Refuse contributions whose arrays (rows x classes x features) would pass the cap."""
    allowed = explain.contribution_rows(predictor.model, n_instances)
    if allowed >= n_instances:
        return
    if allowed == 0:
        raise Rejected(422, "this model has too many classes and features for contributions")
    raise Rejected(
        422, f"with contributions, this model takes at most {allowed} instances per request"
    )


def _explained(predictor: Predictor, instances: list) -> JSONResponse:
    # Built here, in the threadpool: a response of contributions can be large to render.
    return JSONResponse({"predictions": predictor.predict(instances, contributions=True)})


def create_app(model_dir: Path | None = None, *, image_tag: str | None = None) -> FastAPI:
    """The app for the model in ``model_dir`` (default ``$FIONE_MODEL_DIR``, else ``/model``).

    ``image_tag`` (default ``$FIONE_IMAGE_TAG``, else ``dev``) is the running image's tag.
    Raises ``ModelLoadError`` if the model cannot be served. Limits come from
    ``FIONE_SERVING_MAX_BODY`` (bytes), ``FIONE_SERVING_MAX_INSTANCES``,
    ``FIONE_SERVING_MAX_CONTRIBUTION_INSTANCES`` and ``FIONE_SERVING_MAX_CONTRIBUTION_REQUESTS``
    (in flight), read here.
    """
    model_dir = Path(model_dir or os.environ.get("FIONE_MODEL_DIR") or "/model")
    image_tag = image_tag or os.environ.get("FIONE_IMAGE_TAG") or "dev"
    max_body = _env_int("FIONE_SERVING_MAX_BODY", DEFAULT_MAX_BODY)
    max_instances = _env_int("FIONE_SERVING_MAX_INSTANCES", DEFAULT_MAX_INSTANCES)
    max_contribution_instances = _env_int(
        "FIONE_SERVING_MAX_CONTRIBUTION_INSTANCES", DEFAULT_MAX_CONTRIBUTION_INSTANCES
    )
    max_contribution_requests = _env_int(
        "FIONE_SERVING_MAX_CONTRIBUTION_REQUESTS", DEFAULT_MAX_CONTRIBUTION_REQUESTS
    )
    loaded = load(model_dir, image_tag)
    predictor = Predictor(loaded)

    app = FastAPI(title="Fione Serving", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.loaded = loaded
    app.state.contribution_requests = threading.BoundedSemaphore(max_contribution_requests)

    @app.exception_handler(Rejected)
    async def _rejected(request: Request, e: Rejected) -> JSONResponse:
        return JSONResponse({"error": e.message}, status_code=e.status, headers=e.headers)

    @app.get("/")
    @app.get("/ping")
    async def ping() -> Response:
        return Response()

    @app.get("/model")
    async def model() -> JSONResponse:
        return JSONResponse(predictor.description)

    @app.post("/invocations")
    async def invocations(request: Request) -> JSONResponse:
        body = await _read_body(request, max_body)
        instances, contributions = _request(body, max_instances, max_contribution_instances)
        if not contributions:
            predictions = await run_in_threadpool(predictor.predict, instances)
            return JSONResponse({"predictions": predictions})
        _check_width(predictor, len(instances))
        slots = app.state.contribution_requests
        if not slots.acquire(blocking=False):  # never wait: a flood gets 503s at once
            raise Rejected(
                503, "too many contribution requests at once; retry shortly", {"Retry-After": "1"}
            )
        try:  # the threadpool call returns only when the thread is done, even if cancelled
            return await run_in_threadpool(_explained, predictor, instances)
        finally:
            slots.release()

    return app
