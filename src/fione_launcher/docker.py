"""A minimal Docker Engine API client over the Unix socket (stdlib ``http.client``). It uses the
daemon's default API version and never pulls an image."""

import http.client
import json
import socket
from typing import Any
from urllib.parse import quote, urlencode

_TIMEOUT = 30.0


class DockerError(Exception):
    """Docker answered with an error status. The message names the call and the status only."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float):
        super().__init__("localhost", timeout=timeout)
        self._socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect(self._socket_path)
        except OSError:
            sock.close()
            raise
        self.sock = sock


def _labels_filter(labels: dict[str, str]) -> str:
    return json.dumps({"label": [f"{k}={v}" for k, v in labels.items()]})


class DockerAPI:
    def __init__(self, socket_path: str, timeout: float = _TIMEOUT):
        self._socket_path = socket_path
        self._timeout = timeout

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
        """``(status, decoded JSON body or None)``; any status, errors included."""
        conn = _UnixConnection(self._socket_path, self._timeout)
        try:
            headers = {}
            data = None
            if body is not None:
                data = json.dumps(body).encode()
                headers["Content-Type"] = "application/json"
            conn.request(method, path, body=data, headers=headers)
            response = conn.getresponse()
            payload = response.read()
            status = response.status
            if "json" in response.getheader("Content-Type", "") and payload:
                return status, json.loads(payload)
            return status, None
        finally:
            conn.close()

    def _call(self, method: str, path: str, body: dict | None = None, ok=(200,)) -> Any:
        status, data = self.request(method, path, body)
        if status not in ok:
            raise DockerError(status, f"{method} {path.split('?')[0]}: {status}")
        return data

    def inspect_self(self) -> dict:
        """This container, found by its host name (Docker's default: the short id)."""
        return self._call("GET", f"/containers/{quote(socket.gethostname(), safe='')}/json")

    def find_network(self, project: str, name: str) -> str:
        """The name of Compose network ``name`` of ``project``; ``LookupError`` unless there is
        exactly one and it is internal (no egress)."""
        labels = {"com.docker.compose.project": project, "com.docker.compose.network": name}
        found = self._call("GET", "/networks?" + urlencode({"filters": _labels_filter(labels)}))
        if len(found) != 1 or found[0].get("Internal") is not True:
            raise LookupError(name)
        return found[0]["Name"]

    def list_notebooks(self, project: str) -> list[dict]:
        """Every notebook container of ``project``, whatever its state."""
        labels = {"fione.notebook": "1", "fione.project": project}
        query = urlencode({"all": "true", "filters": _labels_filter(labels)})
        return self._call("GET", f"/containers/json?{query}")

    def inspect(self, name: str) -> dict | None:
        """The container ``name``, or None when there is none."""
        status, data = self.request("GET", f"/containers/{quote(name, safe='')}/json")
        if status == 404:
            return None
        if status != 200:
            raise DockerError(status, f"GET /containers/{{name}}/json: {status}")
        return data

    def create_volume(self, name: str, labels: dict[str, str]) -> None:
        """Create the named volume, or keep it as it is when it exists."""
        self._call("POST", "/volumes/create", {"Name": name, "Labels": labels}, ok=(200, 201))

    def create(self, name: str, body: dict) -> str:
        """The id of a new container (never pulls: a missing image is a 404 ``DockerError``)."""
        query = urlencode({"name": name})
        return self._call("POST", f"/containers/create?{query}", body, ok=(201,))["Id"]

    def start(self, container_id: str) -> None:
        self._call("POST", f"/containers/{quote(container_id, safe='')}/start", ok=(204, 304))

    def remove(self, container_id: str) -> None:
        """Remove the container, running or not; gone already, or being removed, is fine."""
        path = f"/containers/{quote(container_id, safe='')}?force=true"
        self._call("DELETE", path, ok=(204, 404, 409))
