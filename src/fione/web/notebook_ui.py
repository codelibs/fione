"""The notebook page: start, stop and a signed-in JupyterLab frame.

Only on installs with notebooks (404 otherwise), for signed-in users (the session cookie,
never a token) who may use notebooks (403 otherwise). A starting notebook's status is polled;
once it runs, the page is reloaded and frames the notebook gateway with a fresh launch token,
which is minted nowhere else. Launcher failures are shown by their code's message, never the
launcher's own text.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from fione import i18n
from fione.api.deps import Auth, Conn
from fione.auth import service as auth_service
from fione.notebooks import service as notebooks
from fione.notebooks.launcher import LauncherError
from fione.web.access import SmallForm, form_auth, signed_in
from fione.web.easyml import STOP_POLLING
from fione.web.views import UiError, language, render

router = APIRouter(include_in_schema=False)
log = logging.getLogger(__name__)

POLL_SECS = 2
ERROR_KEYS = {"limit": "notebook.limit", "image_missing": "notebook.image_missing"}
ERROR_STATUS = {"limit": 409}  # others: 503


def _enabled(request: Request) -> None:
    if not request.app.state.settings.notebooks_enabled:
        raise UiError(404, "error.not_found")


def _allowed(conn, auth: Auth) -> Auth:
    if not auth_service.can_use_notebook(conn, auth.user):
        raise UiError(403, "notebook.forbidden")
    return auth


def _page_auth(request: Request, conn) -> Auth:
    _enabled(request)
    return _allowed(conn, signed_in(request, conn))


def _post_auth(request: Request, conn, form) -> Auth:
    _enabled(request)
    return _allowed(conn, form_auth(request, conn, form))


def _failed(e: LauncherError) -> str:
    """The message key of a launcher failure, which is logged by its code only."""
    log.warning("the notebook launcher failed: %s", e.code)
    return ERROR_KEYS.get(e.code, "notebook.unavailable")


def _page(
    request: Request, auth: Auth, state, *, status: int = 200, error=None, frame=None
) -> Response:
    return render(
        request,
        "notebook.html",
        auth,
        status=status,
        nav="notebook",
        here="/notebook",
        state=state,
        error=error,
        frame=frame,
        poll_secs=POLL_SECS,
    )


@router.get("/notebook")
def notebook(request: Request, conn: Conn) -> Response:
    auth = _page_auth(request, conn)
    app = request.app.state
    try:
        state = notebooks.state(conn, app.notebook_launcher, auth.user)
    except LauncherError as e:
        return _page(request, auth, None, status=503, error=_failed(e))
    frame = None
    if state == "running":
        try:
            frame = notebooks.launch_url(conn, app.settings, app.secret, auth.user)
        except notebooks.NotebookNotRunning:  # ended since the state was read
            state = "absent"
        else:
            request.state.csp_frame_src = app.settings.notebook_url  # this response only
    return _page(request, auth, state, frame=frame)


@router.get("/notebook/status")
def notebook_status(request: Request, conn: Conn) -> Response:
    """The polled status of a starting notebook. Once it is anything else, HTMX reloads the
    page (which frames a running one); a refusal or failure is a final fragment (286)."""
    polling = bool(request.headers.get("hx-request"))
    try:
        auth = _page_auth(request, conn)
        state = notebooks.state(conn, request.app.state.notebook_launcher, auth.user)
    except UiError as e:
        if not polling or e.status == 401:  # 401: HTMX is sent to the login page
            raise
        return _stopped(request, e.key)
    except LauncherError as e:
        key = _failed(e)
        if not polling:
            raise UiError(503, key) from None
        return _stopped(request, key)
    # No ``auth``: the fragment has no header, so no navigation to look up every poll.
    response = render(request, "_notebook_status.html", state=state, poll_secs=POLL_SECS)
    if polling and state != "starting":
        response.headers["HX-Refresh"] = "true"
    return response


def _stopped(request: Request, key: str) -> Response:
    message = i18n.t(key, language(request))
    return render(request, "_notebook_status.html", status=STOP_POLLING, message=message)


@router.post("/notebook/start")
def start(request: Request, conn: Conn, form: SmallForm) -> Response:
    auth = _post_auth(request, conn, form)
    app = request.app.state
    try:
        notebooks.start(conn, app.notebook_launcher, app.settings, app.secret, auth.user)
    except notebooks.NotebookNotAllowed:  # revoked since the check above
        raise UiError(403, "notebook.forbidden") from None
    except LauncherError as e:
        status = ERROR_STATUS.get(e.code, 503)
        return _page(request, auth, "absent", status=status, error=_failed(e))
    return RedirectResponse("/notebook", 303)


@router.post("/notebook/stop")
def stop(request: Request, conn: Conn, form: SmallForm) -> Response:
    auth = _post_auth(request, conn, form)
    try:
        notebooks.stop(conn, request.app.state.notebook_launcher, auth.user.id)
    except LauncherError as e:
        return _page(request, auth, None, status=503, error=_failed(e))
    return RedirectResponse("/notebook", 303)
