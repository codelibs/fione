"""Test helpers of the notebook launcher (tests/launcher): a fake Docker API, valid
requests and an HTTP client."""

import http.client
import json
import time

from fione_launcher.config import LauncherConfig
from fione_launcher.docker import DockerError

PROJECT = "p"
NETWORK = "p_notebooks"
IMAGE = "fione-notebook:test"
SECRET = "s" * 40


class FakeDocker:
    """In-memory stand-in for ``DockerAPI`` with the same methods. ``calls`` records every
    call; ``containers`` maps a name to its inspect-like state."""

    def __init__(self, *, project: str = PROJECT, images: tuple[str, ...] = (IMAGE,)):
        self.calls: list[tuple] = []
        self.containers: dict[str, dict] = {}
        self.volumes: dict[str, dict] = {}
        self.images = set(images)
        self.self_labels = {"com.docker.compose.project": project}
        self.networks = [
            {
                "Name": f"{project}_notebooks",
                "Internal": True,
                "Labels": {
                    "com.docker.compose.project": project,
                    "com.docker.compose.network": "notebooks",
                },
            }
        ]
        self._ids = 0

    def add(self, name: str, labels: dict, status: str = "running", health: str | None = None):
        """A container that is already there (not recorded as a call)."""
        self._ids += 1
        state = {"Status": status}
        if health is not None:
            state["Health"] = {"Status": health}
        self.containers[name] = {"Id": f"id{self._ids}", "Labels": labels, "State": state}
        return self.containers[name]["Id"]

    def _by_id(self, container_id: str) -> str | None:
        return next((n for n, c in self.containers.items() if c["Id"] == container_id), None)

    def request(self, method, path, body=None):
        self.calls.append(("request", method, path, body))
        raise AssertionError("the launcher uses the helpers only")

    def inspect_self(self):
        self.calls.append(("inspect_self",))
        return {"Config": {"Labels": self.self_labels}}

    def find_network(self, project, name):
        self.calls.append(("find_network", project, name))
        found = [
            n
            for n in self.networks
            if n["Labels"].get("com.docker.compose.project") == project
            and n["Labels"].get("com.docker.compose.network") == name
        ]
        if len(found) != 1 or not found[0]["Internal"]:
            raise LookupError(name)
        return found[0]["Name"]

    def list_notebooks(self, project):
        self.calls.append(("list_notebooks", project))
        return [
            {
                "Id": c["Id"],
                "Names": [f"/{n}"],
                "Labels": c["Labels"],
                "State": c["State"]["Status"],
            }
            for n, c in self.containers.items()
            if c["Labels"].get("fione.notebook") == "1"
            and c["Labels"].get("fione.project") == project
        ]

    def inspect(self, name):
        self.calls.append(("inspect", name))
        c = self.containers.get(name)
        if c is None:
            return None
        return {"Id": c["Id"], "Config": {"Labels": c["Labels"]}, "State": c["State"]}

    def create_volume(self, name, labels):
        self.calls.append(("create_volume", name, labels))
        self.volumes.setdefault(name, labels)

    def inspect_volume(self, name):
        self.calls.append(("inspect_volume", name))
        labels = self.volumes.get(name)
        return None if labels is None else {"Name": name, "Labels": labels}

    def remove_volume(self, name):
        self.calls.append(("remove_volume", name))
        self.volumes.pop(name, None)

    def create(self, name, body):
        self.calls.append(("create", name, body))
        if body["Image"] not in self.images:
            raise DockerError(
                404, "POST /containers/create: 404", f"No such image: {body['Image']}"
            )
        if name in self.containers:
            raise DockerError(409, "POST /containers/create: 409", "Conflict. The name is in use")
        return self.add(name, body["Labels"], status="created")

    def start(self, container_id):
        self.calls.append(("start", container_id))
        self.containers[self._by_id(container_id)]["State"] = {
            "Status": "running",
            "Health": {"Status": "starting"},
        }

    def remove(self, container_id):
        self.calls.append(("remove", container_id))
        name = self._by_id(container_id)
        if name is not None:
            del self.containers[name]

    def names(self) -> set[str]:
        return set(self.containers)


def make_config(**changes) -> LauncherConfig:
    env = {"FIONE_LAUNCHER_SECRET": SECRET, "FIONE_NOTEBOOK_IMAGE": IMAGE}
    env.update(changes)
    return LauncherConfig.from_env(env)


def labels(project: str, uid: str, expires: int | str | None = None) -> dict:
    expires = int(time.time()) + 3600 if expires is None else expires
    return {
        "fione.notebook": "1",
        "fione.project": project,
        "fione.uid": uid,
        "fione.expires": str(expires),
    }


def start_request(**changes) -> dict:
    """A valid PUT body; a change to None drops that field."""
    body = {
        "launch_key": "a" * 64,
        "cookie_secret": "b" * 64,
        "token": "fione_" + "T" * 40,
        "fione_origin": "http://127.0.0.1:8080",
        "expires_at": int(time.time()) + 3600,
    }
    body.update(changes)
    return {k: v for k, v in body.items() if v is not None}


class Api:
    """A client of the launcher's HTTP API on 127.0.0.1."""

    def __init__(self, port: int):
        self.port = port

    def call(self, method, path, body=None, *, secret=SECRET, raw: bytes | None = None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {}
        if secret is not None:
            headers["X-Fione-Launcher-Secret"] = secret
        data = raw if raw is not None else None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        try:
            conn.request(method, path, body=data, headers=headers)
            response = conn.getresponse()
            payload = response.read()
            return response.status, json.loads(payload) if payload else None
        finally:
            conn.close()
