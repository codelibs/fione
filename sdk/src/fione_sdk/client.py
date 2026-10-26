import io
import os
from collections.abc import Iterator
from typing import Any, Literal
from urllib.parse import quote

import httpx
import pandas as pd

from fione_sdk.errors import FioneError

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
