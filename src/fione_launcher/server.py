"""The launcher's HTTP API and the lifecycle of its notebook containers.

Every route but ``/health`` needs ``X-Fione-Launcher-Secret``. A request is validated in full
before any Docker call. Nothing logs a request body, the token or the keys: the access log has
the request line only, and errors log their class or Docker's status."""

import hmac
import json
import logging
import os
import re
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fione_launcher.config import LauncherConfig
from fione_launcher.docker import DockerAPI, DockerError
from fione_launcher.spec import (
    InvalidRequest,
    StartRequest,
    container_body,
    container_name,
    valid_uid,
    volume_name,
)

log = logging.getLogger("fione_launcher")

SECRET_HEADER = "X-Fione-Launcher-Secret"
_MAX_BODY = 4096
_REAP_INTERVAL = 60.0
_PREFIX = "/notebooks/"
_DIGITS = re.compile(r"[0-9]{1,12}")  # ASCII: str.isdigit() takes other digits too


class Refused(Exception):
    """An answer other than success: ``status`` and the JSON error ``code``."""

    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status = status
        self.code = code


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict:
    data = dict(pairs)
    if len(data) != len(pairs):
        raise InvalidRequest("duplicate field")
    return data


def _state(info: dict | None) -> str:
    if info is None:
        return "absent"
    state = info.get("State") or {}
    status = state.get("Status")
    if status == "running":
        healthy = (state.get("Health") or {}).get("Status") == "healthy"
        return "running" if healthy else "starting"
    if status in ("created", "restarting"):
        return "starting"
    return "absent"  # exited, dead or being removed: AutoRemove takes it away


def _expired(labels: dict, now: float) -> bool:
    expires = labels.get("fione.expires", "")
    return not _DIGITS.fullmatch(expires) or int(expires) <= now  # unreadable: expired


class Launcher:
    """Starts, reports and removes the notebook containers of one Compose project."""

    def __init__(self, cfg: LauncherConfig, docker, *, project: str, network: str):
        self.cfg = cfg
        self.docker = docker
        self.project = project
        self.network = network
        self._lock = threading.Lock()  # a start (limit check to start) is one step
        self._closed = False

    @classmethod
    def start_up(cls, cfg: LauncherConfig, docker) -> "Launcher":
        """The launcher of this container's Compose project, after removing that project's
        notebooks left from an earlier run; exits when the project or network is missing."""
        labels = (docker.inspect_self().get("Config") or {}).get("Labels") or {}
        project = labels.get("com.docker.compose.project")
        if not project:
            raise SystemExit(
                "fione_launcher: no com.docker.compose.project label on this container"
            )
        try:
            network = docker.find_network(project, "notebooks")
        except LookupError:
            raise SystemExit(
                f"fione_launcher: no single internal network `notebooks` in project {project}"
            ) from None
        launcher = cls(cfg, docker, project=project, network=network)
        launcher.remove_all()
        return launcher

    def _ours(self, info: dict | None, uid: str) -> dict | None:
        labels = ((info or {}).get("Config") or {}).get("Labels") or {}
        expected = {"fione.notebook": "1", "fione.project": self.project, "fione.uid": uid}
        if any(labels.get(k) != v for k, v in expected.items()):
            return None
        return info

    def state(self, uid: str) -> str:
        return _state(self._ours(self.docker.inspect(container_name(self.project, uid)), uid))

    def ensure(self, uid: str, req: StartRequest) -> str:
        name = container_name(self.project, uid)
        with self._lock:
            if self._closed:
                raise Refused(503, "closing")
            if self.docker.inspect(name) is not None:
                raise Refused(409, "exists")
            if len(self.docker.list_notebooks(self.project)) >= self.cfg.max_running:
                raise Refused(409, "limit")
            self.docker.create_volume(
                volume_name(self.project, uid), {"fione.project": self.project, "fione.uid": uid}
            )
            body = container_body(
                self.cfg, project=self.project, network=self.network, uid=uid, req=req
            )
            try:
                container_id = self.docker.create(name, body)
            except DockerError as e:
                if e.status == 404:
                    raise Refused(503, "image_missing") from None
                if e.status == 409:
                    raise Refused(409, "exists") from None
                raise
            try:
                self.docker.start(container_id)
            except Exception:
                self.docker.remove(container_id)
                raise
        return "starting"

    def stop(self, uid: str) -> None:
        info = self._ours(self.docker.inspect(container_name(self.project, uid)), uid)
        if info is not None:
            self.docker.remove(info["Id"])  # the volume stays

    def remove_all(self) -> None:
        for container in self.docker.list_notebooks(self.project):
            self.docker.remove(container["Id"])

    def reap(self, now: float) -> None:
        for container in self.docker.list_notebooks(self.project):
            labels = container.get("Labels") or {}
            if _expired(labels, now):
                log.info("removing an expired notebook (uid %s)", labels.get("fione.uid"))
                self.docker.remove(container["Id"])

    def close(self) -> None:
        """Refuse new starts and remove every notebook of the project."""
        with self._lock:
            self._closed = True
        self.remove_all()


def run_reaper(launcher: Launcher, stop: threading.Event, interval: float = _REAP_INTERVAL):
    while not stop.wait(interval):
        try:
            launcher.reap(time.time())
        except Exception as e:  # keep reaping; Docker may be back next time
            log.error("reaping failed: %s", _describe(e))


def _describe(e: Exception) -> str:
    return str(e) if isinstance(e, DockerError) else type(e).__name__


class _Handler(BaseHTTPRequestHandler):
    server_version = "fione-launcher"
    sys_version = ""
    timeout = 10  # a slow client cannot hold a thread for long
    launcher: Launcher  # set by make_server

    def log_message(self, format, *args):  # noqa: A002 (the base class's name)
        log.info("%s %s", self.address_string(), format % args)

    def _send(self, status: int, data: dict | None) -> None:
        payload = b"" if data is None else json.dumps(data).encode()
        self.send_response(status)
        if data is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _authorized(self) -> bool:
        given = self.headers.get(SECRET_HEADER, "").encode("utf-8", "surrogateescape")
        return hmac.compare_digest(given, self.launcher.cfg.secret.encode())

    def _body(self) -> object:
        length = self.headers.get("Content-Length", "")
        if not _DIGITS.fullmatch(length) or not 0 < int(length) <= _MAX_BODY:
            raise InvalidRequest("length")
        try:
            return json.loads(self.rfile.read(int(length)), object_pairs_hook=_no_duplicates)
        except ValueError as e:  # JSONDecodeError and UnicodeDecodeError too
            raise InvalidRequest("json") from e

    def _handle(self, method: str) -> None:
        if method == "GET" and self.path == "/health":
            return self._send(200, {})
        if not self._authorized():
            return self._send(401, {"error": "unauthorized"})
        if not self.path.startswith(_PREFIX):
            return self._send(404, {"error": "not_found"})
        if method not in ("GET", "PUT", "DELETE"):
            return self._send(405, {"error": "method_not_allowed"})
        uid = self.path[len(_PREFIX) :]
        try:
            if not valid_uid(uid):
                raise InvalidRequest("uid")
            if method == "PUT":
                req = StartRequest.parse(self._body(), now=time.time())
                return self._send(200, {"state": self.launcher.ensure(uid, req)})
            if method == "GET":
                return self._send(200, {"state": self.launcher.state(uid)})
            self.launcher.stop(uid)
            return self._send(204, None)
        except InvalidRequest:
            return self._send(422, {"error": "invalid"})
        except Refused as e:
            return self._send(e.status, {"error": e.code})
        except Exception as e:
            log.error("%s /notebooks/%s failed: %s", method, uid, _describe(e))
            return self._send(500, {"error": "internal"})

    def do_GET(self):  # noqa: N802
        self._handle("GET")

    def do_PUT(self):  # noqa: N802
        self._handle("PUT")

    def do_DELETE(self):  # noqa: N802
        self._handle("DELETE")

    def do_POST(self):  # noqa: N802
        self._handle("POST")

    def do_PATCH(self):  # noqa: N802
        self._handle("PATCH")


def make_server(launcher: Launcher, host: str, port: int) -> ThreadingHTTPServer:
    handler = type("Handler", (_Handler,), {"launcher": launcher})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def main(env=os.environ) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cfg = LauncherConfig.from_env(env)
    docker = DockerAPI(cfg.socket_path)
    try:
        launcher = Launcher.start_up(cfg, docker)
    except (OSError, DockerError) as e:
        raise SystemExit(f"fione_launcher: cannot use the Docker socket: {_describe(e)}") from None
    server = make_server(launcher, "0.0.0.0", cfg.port)  # noqa: S104 (inside its network)
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=run_reaper, args=(launcher, stop), daemon=True).start()
    log.info("listening on port %d for project %s", cfg.port, launcher.project)
    stop.wait()
    log.info("stopping: removing this project's notebooks")
    server.shutdown()
    launcher.close()
    return 0
