import contextlib
import io
import os
import secrets
from collections.abc import Iterator
from typing import Any, Literal
from urllib.parse import quote

import httpx
import pandas as pd

from fione_sdk.errors import FioneError
from fione_sdk.jobs import TERMINAL, Job

API = "/api/v1"


class _Body(io.RawIOBase):
    """A binary file object over a streamed response body, for ``pd.read_csv``."""

    def __init__(self, chunks: Iterator[bytes]):
        self._chunks = chunks
        self._rest = b""

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        while not self._rest:
            try:
                self._rest = next(self._chunks)
            except StopIteration:
                return 0
        n = min(len(buffer), len(self._rest))
        buffer[:n] = self._rest[:n]
        self._rest = self._rest[n:]
        return n


def _error(response: httpx.Response) -> FioneError:
    if response.is_redirect:
        where = response.headers.get("location", "somewhere else")
        return FioneError(
            response.status_code, "http", f"redirected to {where}; check that FIONE_URL is right"
        )
    try:
        body = response.json()
        return FioneError(response.status_code, str(body["code"]), str(body["error"]))
    except (ValueError, KeyError, TypeError):
        return FioneError(
            response.status_code, "http", response.text[:200] or response.reason_phrase
        )


def _segment(name: str) -> str:
    """``name`` as one URL path segment (``quote`` leaves dots, which a URL normalizes away)."""
    return name.replace(".", "%2E") if name in {".", ".."} else quote(name, safe="")


class Client:
    """A client of the Fione API. ``url`` and ``token`` default to the environment variables
    ``FIONE_URL`` and ``FIONE_TOKEN``.

    ``http`` is an ``httpx.Client`` to send through instead of one of its own. With it,
    ``url`` and ``timeout`` are ignored (it has its own base URL and timeout) and the token
    goes to wherever that client points. Redirects are never followed. Any response that is
    not a 2xx, or whose body is not what the call needs, raises ``FioneError``; transport
    errors (``httpx.ConnectError``, timeouts) propagate as they are."""

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        *,
        http: httpx.Client | None = None,
        timeout: float = 60.0,
    ):
        token = token or os.environ.get("FIONE_TOKEN")
        if not token:
            raise FioneError(0, "config", "set FIONE_TOKEN or pass token=")
        url = url or os.environ.get("FIONE_URL")
        if http is None:
            if not url:
                raise FioneError(0, "config", "set FIONE_URL or pass url=")
            http = httpx.Client(base_url=url, timeout=timeout)
        self.http = http
        self._headers = {"Authorization": f"Bearer {token}"}

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = self.http.request(
            method, API + path, headers=self._headers, follow_redirects=False, **kwargs
        )
        if not response.is_success:
            raise _error(response)
        return response

    def _json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._request(method, path, **kwargs)
        try:
            return response.json()
        except ValueError:
            raise FioneError(response.status_code, "http", "response is not JSON") from None

    def projects(self) -> list[dict]:
        return self._json("GET", "/projects")

    def project(self, project_id: str) -> dict:
        return self._json("GET", f"/projects/{project_id}")

    def create_project(self, name: str) -> dict:
        return self._json("POST", "/projects", json={"name": name})

    def datasets(self, project_id: str) -> list[dict]:
        return self._json("GET", f"/projects/{project_id}/datasets")

    def dataset(self, project_id: str, dataset_id: int) -> dict:
        return self._json("GET", f"/projects/{project_id}/datasets/{dataset_id}")

    def upload(
        self,
        project_id: str,
        df: pd.DataFrame,
        name: str,
        type: Literal["train", "test", "predict"] = "train",
    ) -> dict:
        return self._json(
            "POST",
            f"/projects/{project_id}/datasets",
            data={"name": name, "type": type},
            files={"file": (f"{name}.csv", df.to_csv(index=False).encode(), "text/csv")},
        )

    def read(self, project_id: str, dataset_id: int) -> pd.DataFrame:
        path = f"{API}/projects/{project_id}/datasets/{dataset_id}/download"
        with self.http.stream(
            "GET", path, headers=self._headers, follow_redirects=False
        ) as response:
            if not response.is_success:
                response.read()
                raise _error(response)
            return pd.read_csv(io.BufferedReader(_Body(response.iter_bytes())))

    def preview(self, project_id: str, dataset_id: int, **params: Any) -> dict:
        return self._json(
            "GET", f"/projects/{project_id}/datasets/{dataset_id}/preview", params=params
        )

    def profile(self, project_id: str, dataset_id: int) -> dict:
        return self._json("GET", f"/projects/{project_id}/datasets/{dataset_id}/profile")

    def column_profile(self, project_id: str, dataset_id: int, column: str) -> dict:
        return self._json(
            "GET",
            f"/projects/{project_id}/datasets/{dataset_id}/columns/{_segment(column)}",
        )

    def delete_dataset(self, project_id: str, dataset_id: int) -> None:
        self._request("DELETE", f"/projects/{project_id}/datasets/{dataset_id}")

    def train(
        self, project_id: str, dataset_id: int, target: str, *, name: str | None = None, **config
    ) -> Job:
        """Queue AutoML training on a ``train`` dataset; ``config`` holds the other training
        options (``max_runtime_secs``, ``max_models``, ``nfolds``...). Returns the job:
        ``job.wait()`` blocks until it is done, then ``job.result["model_id"]`` is the model."""
        body: dict[str, Any] = {"dataset_id": dataset_id, "config": {"target": target, **config}}
        if name is not None:
            body["name"] = name
        return Job(self, self._json("POST", f"/projects/{project_id}/jobs/automl", json=body))

    def job(self, job_id: int) -> Job:
        return Job(self, self._json("GET", f"/jobs/{job_id}"))

    def models(self, project_id: str) -> pd.DataFrame:
        """The project's models, one row each."""
        return pd.DataFrame(self._json("GET", f"/projects/{project_id}/models"))

    def model(self, model_id: int) -> dict:
        return self._json("GET", f"/models/{model_id}")

    def leaderboard(self, model_id: int) -> pd.DataFrame:
        """The models AutoML tried for this model, best first."""
        return pd.DataFrame(self.model(model_id).get("leaderboard") or [])

    def predict(
        self,
        project_id: str,
        model_id: int,
        df: pd.DataFrame,
        *,
        include_columns: list[str] | None = None,
        timeout: float | None = None,
    ) -> pd.DataFrame:
        """Predict the rows of ``df`` with the model on the server and return them, in order,
        with a ``predict`` column. ``df`` is uploaded as a temporary ``predict`` dataset that
        is removed afterwards; the result dataset stays in the project. ``include_columns``
        names the input columns to copy to the result. After ``timeout`` seconds the job is
        cancelled and ``TimeoutError`` raised."""
        uploaded = self.upload(project_id, df, f"sdk_predict_{secrets.token_hex(4)}", "predict")
        job = None
        try:
            job = Job(
                self,
                self._json(
                    "POST",
                    f"/projects/{project_id}/jobs/batch-predict",
                    json={
                        "model_id": model_id,
                        "dataset_id": uploaded["id"],
                        "include_columns": include_columns,
                    },
                ),
            )
            job.wait(timeout=timeout)
            dataset_id = (job.result or {}).get("dataset_id")
            if not isinstance(dataset_id, int):
                raise FioneError(200, "http", "unexpected response: the job has no result dataset")
            result = self.read(project_id, dataset_id)
        except BaseException:
            # Do not let a failed clean-up hide why the prediction failed.
            with contextlib.suppress(FioneError, httpx.HTTPError):
                if job is not None and job.status not in TERMINAL:
                    job.cancel()
            with contextlib.suppress(FioneError, httpx.HTTPError):
                self.delete_dataset(project_id, uploaded["id"])
            raise
        self.delete_dataset(project_id, uploaded["id"])
        return result

    def modules(self) -> list[dict]:
        """The modules the server can run: built-in operations such as ``sort`` and ``filter``
        and the ones an administrator uploaded, each with its parameter schema."""
        return self._json("GET", "/modules")

    def run_module(
        self,
        project_id: str,
        module_id: str,
        dataset_id: int,
        params: dict | None = None,
        *,
        name: str | None = None,
    ) -> Job:
        """Queue a module over a dataset. It runs on the server, not in this process. When
        the job is done, ``job.result["dataset_id"]`` is the dataset it made."""
        body: dict[str, Any] = {
            "module_id": module_id,
            "dataset_id": dataset_id,
            "params": params or {},
        }
        if name is not None:
            body["name"] = name
        return Job(self, self._json("POST", f"/projects/{project_id}/jobs/module", json=body))
