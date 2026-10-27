"""The client of the notebook launcher, the service that starts, reports and removes the
per-user containers (``fione_launcher``). Fione never holds the Docker socket itself.

Every failure is a ``LauncherError`` whose ``code`` the UI translates; the launcher's own
text never reaches an exception, a log or a page. The request body holds the notebook token
and the container's key, so requests go straight to the configured URL: no proxy from the
environment and no redirect is followed.
"""

import http.client
import json
import urllib.error
import urllib.request
from typing import Literal, Protocol, get_args

NotebookState = Literal["absent", "starting", "running"]
LauncherErrorCode = Literal["unreachable", "limit", "exists", "image_missing", "refused"]

SECRET_HEADER = "X-Fione-Launcher-Secret"
_STATES = frozenset(get_args(NotebookState))
# The launcher's JSON error codes that keep their meaning here; any other is by status.
_CODES = {(409, "exists"), (409, "limit"), (503, "image_missing")}


class LauncherError(Exception):
    """``code``: unreachable (down, timed out or failing), limit (too many notebooks run),
    exists (the container is already there), image_missing, refused (a request the launcher
    did not accept: a wrong secret or value). The message is Fione's own, never the
    launcher's."""

    def __init__(self, code: LauncherErrorCode, message: str | None = None):
        super().__init__(message or code)
        self.code = code


class Launcher(Protocol):
    def ensure(self, user_id: int, body: dict) -> NotebookState: ...

    def status(self, user_id: int) -> NotebookState: ...

    def stop(self, user_id: int) -> None: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # the 3xx is raised as an HTTPError: refused


class HttpLauncher:
    def __init__(self, url: str, secret: str, timeout: float = 10.0):
        self.url = url.rstrip("/")
        self.secret = secret
        self.timeout = timeout
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)

    def _call(self, method: str, user_id: int, body: dict | None = None) -> dict | None:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            f"{self.url}/notebooks/{int(user_id)}", data=data, method=method
        )
        request.add_header(SECRET_HEADER, self.secret)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as e:  # before URLError, its base class
            try:
                code = _error_code(e)
            finally:
                e.close()
            raise LauncherError(code, f"the launcher answered {e.code}") from None
        # URLError, timeouts, refused connections, malformed answers, bad URLs
        except (OSError, http.client.HTTPException, ValueError):
            raise LauncherError("unreachable", "the launcher could not be reached") from None
        if not payload:
            return None
        try:
            answer = json.loads(payload)
        except ValueError:
            raise LauncherError("unreachable", "the launcher's answer is not JSON") from None
        return answer if isinstance(answer, dict) else {}

    def _state(self, answer: dict | None) -> NotebookState:
        state = (answer or {}).get("state")
        if state not in _STATES:
            raise LauncherError("unreachable", "the launcher's answer has no state")
        return state

    def ensure(self, user_id: int, body: dict) -> NotebookState:
        return self._state(self._call("PUT", user_id, body))

    def status(self, user_id: int) -> NotebookState:
        return self._state(self._call("GET", user_id))

    def stop(self, user_id: int) -> None:
        self._call("DELETE", user_id)


def _error_code(error: urllib.error.HTTPError) -> LauncherErrorCode:
    try:
        code = json.loads(error.read()).get("error")
    except (OSError, ValueError, AttributeError):
        code = None
    if (error.code, code) in _CODES:
        return code
    return "unreachable" if error.code >= 500 else "refused"
