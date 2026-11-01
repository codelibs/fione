"""The web UI: server-rendered pages (Jinja2, autoescaped) over the same services as the API.

Pages authenticate with the session cookie only and send anonymous visitors to
``/login?next=<path>``. Sign-in and first-admin setup are done by the page's script against
the JSON API; the UI's own unsafe endpoints check the session's CSRF token (``X-CSRF-Token``,
which HTMX sends from ``hx-headers`` on ``<body>``, or a ``csrf_token`` form field).
"""

import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote, urlencode, urlsplit

from fastapi import APIRouter, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from starlette.exceptions import HTTPException as StarletteHTTPException

from fione import db, i18n
from fione.api.deps import Auth, Conn, cookie_auth, effective_access, request_host
from fione.api.security import SESSION_COOKIE, origin_matches, tokens_equal
from fione.auth import service as auth_service
from fione.auth.passwords import MIN_PASSWORD_LENGTH
from fione.auth.roles import Role
from fione.projects import service as projects
from fione.version import __version__
from fione.web.cache import LruCache
from fione.web.headers import ui_headers

WEB_DIR = Path(__file__).parent
STATIC_PREFIX = "/static"
LANG_COOKIE_MAX_AGE = 365 * 24 * 3600
MODE_COOKIE = "fione_mode"
MODES = ("simple", "detailed")
MAX_NEXT_LENGTH = 2048
# Percent-decoding rounds a ``next`` value is checked through (a proxy or app that decodes
# once more must not turn it into ``//host``).
NEXT_DECODE_ROUNDS = 3
PROFILE_CACHE_SIZE = 16  # column profiles of datasets (the analysis page)
BASELINE_CACHE_SIZE = 1024  # rating baselines of training targets (a few numbers each)
LEAK_CACHE_SIZE = 256  # leak check and task per (dataset, target): a few column names each
SIZE_CACHE_SIZE = 4096  # stored size of each dataset (a HEAD request on S3)

log = logging.getLogger(__name__)
router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(
    env=Environment(
        loader=FileSystemLoader(WEB_DIR / "templates"),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
)


def _when(value) -> datetime | None:
    """A database time as UTC: Unix seconds, or SQLite's ``YYYY-MM-DD HH:MM:SS`` (UTC)."""
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _utc(value) -> str:
    when = _when(value)
    return when.strftime("%Y-%m-%d %H:%M") if when else ""


def _iso(value) -> str:
    when = _when(value)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ") if when else ""


def _cellnum(value) -> str:
    """A number in a data preview: floats to 6 significant digits (downloads keep them all)."""
    if not isinstance(value, float):
        return str(value)
    text = f"{value:.6g}"
    return text if any(c in text for c in ".eni") else text + ".0"  # 3.0 stays a float


templates.env.filters.update(utc=_utc, iso=_iso, cellnum=_cellnum)


class UiError(Exception):
    """A refused UI request: shown as a short translated message (the ``key``)."""

    def __init__(self, status: int, key: str):
        super().__init__(key)
        self.status = status
        self.key = key


def _same_site_path(value: str) -> bool:
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return False
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in value):
        return False
    parts = urlsplit(value)
    return not (parts.scheme or parts.netloc)


def safe_next(value: str | None) -> str:
    """``value`` if it is a path on this site, else ``/``: one leading slash, no backslash
        or control character (browsers read ``/\\host`` and ``/<tab>/host`` as ``//host``),
        also after each of ``NEXT_DECODE_ROUNDS`` percent-decodings (``/%2F%2Fhost``, and double
    or triple encoded); the original string is returned."""
    if not value or len(value) > MAX_NEXT_LENGTH:
        return "/"
    decoded = value
    for _ in range(NEXT_DECODE_ROUNDS):
        if not _same_site_path(decoded):
            return "/"
        decoded = unquote(decoded)
    return value if _same_site_path(decoded) else "/"


def language(request: Request) -> str:
    return i18n.resolve_language(
        request.cookies.get(i18n.LANG_COOKIE), request.headers.get("accept-language")
    )


def _here(request: Request) -> str:
    query = request.url.query
    return request.url.path + (f"?{query}" if query else "")


def _static(path: str) -> str:
    return f"{STATIC_PREFIX}/{path}?v={__version__}"


def ui_mode(request: Request) -> str:
    """``simple`` (the default) or ``detailed``: what the screens show, never what is allowed."""
    return "detailed" if request.cookies.get(MODE_COOKIE) == "detailed" else "simple"


def render(
    request: Request, template: str, auth: Auth | None = None, *, status: int = 200, **context
) -> HTMLResponse:
    lang = language(request)

    def t(key: str, **vars: object) -> str:
        return i18n.t(key, lang, **vars)

    return templates.TemplateResponse(
        request,
        template,
        {
            "lang": lang,
            "t": t,
            "user": auth.user if auth else None,
            "csrf": auth.session.csrf if auth and auth.session else None,
            "here": _here(request),
            "static": _static,
            "version": __version__,
            "mode": ui_mode(request),
            # The assistant's place in a project's navigation and entry links: configured or not.
            "assistant_link": request.app.state.settings.llm_base_url is not None,
            **context,  # may override ``here``: where the language switch returns to
        },
        status_code=status,
    )


def to_login(request: Request) -> RedirectResponse:
    return RedirectResponse("/login?" + urlencode({"next": _here(request)}), 303)


def action_auth(request: Request, conn: sqlite3.Connection, token: str | None = None) -> Auth:
    """The session of an unsafe UI request, whose CSRF token must match."""
    auth = cookie_auth(request, conn)
    if auth is None:
        raise UiError(401, "error.session")
    given = token if token is not None else request.headers.get("x-csrf-token")
    if not tokens_equal(auth.session.csrf, given):
        raise UiError(403, "error.csrf")
    return auth


@router.get("/login")
def login_page(request: Request, conn: Conn, next: str = "/") -> Response:
    if auth_service.needs_first_admin(conn):
        return RedirectResponse("/first-admin", 303)
    target = safe_next(next)
    if cookie_auth(request, conn) is not None:
        return RedirectResponse(target, 303)
    # The language switch returns here with ``next`` only, never echoing other query fields.
    here = "/login" + ("?" + urlencode({"next": target}) if target != "/" else "")
    return render(request, "login.html", next=target, here=here)


@router.get("/first-admin")
def first_admin_page(request: Request, conn: Conn) -> Response:
    if not auth_service.needs_first_admin(conn):
        return RedirectResponse("/login", 303)
    return render(
        request, "first_admin.html", min_password=MIN_PASSWORD_LENGTH, here="/first-admin"
    )


@router.post("/logout")
def logout(request: Request, conn: Conn, csrf_token: Annotated[str, Form()] = "") -> Response:
    try:
        action_auth(request, conn, csrf_token)
    except UiError as e:
        if e.status != 401:
            raise
    response = RedirectResponse("/login", 303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.post("/ui/lang")
def set_language(
    request: Request,
    lang: Annotated[str, Form()] = "",
    next: Annotated[str, Form()] = "/",
) -> Response:
    """Remember the chosen language in the ``fione_lang`` cookie (no account needed)."""
    if not origin_matches(request.headers.get("origin"), request_host(request)):
        raise UiError(403, "error.forbidden")
    if lang not in i18n.LANGUAGES:
        raise UiError(400, "error.generic")
    response = RedirectResponse(safe_next(next), 303)
    response.set_cookie(
        i18n.LANG_COOKIE,
        lang,
        max_age=LANG_COOKIE_MAX_AGE,
        path="/",
        secure=request.app.state.settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/ui/mode")
def set_mode(
    request: Request,
    conn: Conn,
    csrf_token: Annotated[str, Form()] = "",
    mode: Annotated[str, Form()] = "",
    next: Annotated[str, Form()] = "/",
) -> Response:
    """Remember the simple or detailed view in the ``fione_mode`` cookie. Only what the screens
    show changes; every route works the same in both. Another value changes nothing."""
    action_auth(request, conn, csrf_token)
    response = RedirectResponse(safe_next(next), 303)
    if mode in MODES:
        response.set_cookie(
            MODE_COOKIE,
            mode,
            max_age=LANG_COOKIE_MAX_AGE,
            path="/",
            secure=request.app.state.settings.cookie_secure,
            httponly=True,
            samesite="lax",
        )
    return response


def _project_rows(conn: sqlite3.Connection, auth: Auth) -> list[dict]:
    owners = {u.id: u.username for u in auth_service.list_users(conn)}
    return [
        {
            "project": p,
            "access": effective_access(conn, auth.user, p.id),
            "owner": owners.get(p.owner_id),
            "own": p.owner_id == auth.user.id,
            # SQLite's CURRENT_TIMESTAMP is UTC ("YYYY-MM-DD HH:MM:SS"); shown as such.
            "created": p.created_at[:10],
            "iso": p.created_at.replace(" ", "T") + "Z",
        }
        for p in projects.list_projects(conn, auth.user, newest_first=True)
    ]


@router.get("/")
def home(request: Request, conn: Conn) -> Response:
    auth = cookie_auth(request, conn)
    if auth is None:
        return to_login(request)
    return render(
        request,
        "home.html",
        auth,
        rows=_project_rows(conn, auth),
        can_create=auth.user.role != Role.VIEWER,
        nav="projects",
    )


@router.post("/ui/projects")
def create_project(request: Request, conn: Conn, name: Annotated[str, Form()] = "") -> Response:
    """HTMX: create a project; returns the form (cleared, or with an error) and, out of
    band, the refreshed project list and a toast."""
    auth = action_auth(request, conn)
    if auth.user.role == Role.VIEWER:
        raise UiError(403, "error.forbidden")
    try:
        project = projects.create_project(conn, auth.user, name)
    except ValueError:
        return render(
            request, "_project_form.html", auth, status=422, name=name, error="home.error.name"
        )
    return render(
        request,
        "_project_created.html",
        auth,
        rows=_project_rows(conn, auth),
        can_create=True,
        created=project.name,
    )


@router.get("/_design")
def design(request: Request, conn: Conn) -> Response:
    auth = cookie_auth(request, conn)
    if auth is None:
        return to_login(request)
    return render(request, "_design.html", auth)


def _signed_in(request: Request) -> Auth | None:
    """The session of an error page's visitor, so the page keeps their header; None if there
    is none or it cannot be read (the error may be the database itself)."""
    try:
        with closing(db.connect(request.app.state.db_path)) as conn:
            return cookie_auth(request, conn)
    except Exception:
        return None


def error_page(request: Request, status: int, key: str) -> HTMLResponse:
    """The friendly error page: the translated message ``key`` and a way back home."""
    # here="/": the language switch must not return to a POST-only path.
    return render(
        request,
        "error.html",
        _signed_in(request),
        status=status,
        message=i18n.t(key, language(request)),
        hint=KEY_HINTS.get(key, ERROR_HINTS.get(status)),
        here="/",
    )


async def _ui_error(request: Request, exc: UiError) -> Response:
    if request.headers.get("hx-request"):
        message = i18n.t(exc.key, language(request))
        response: Response = PlainTextResponse(message, status_code=exc.status)
        if exc.status == 401:
            current = urlsplit(request.headers.get("hx-current-url", ""))
            back = safe_next(current.path + (f"?{current.query}" if current.query else ""))
            response.headers["HX-Redirect"] = "/login?" + urlencode({"next": back})
        return response
    if exc.status == 401 and request.method == "GET":
        return to_login(request)
    return error_page(request, exc.status, exc.key)


# Status -> message of the error page for errors raised outside the UI's own checks.
HTTP_ERROR_KEYS = {404: "error.not_found", 405: "error.method", 413: "error.too_large"}
ERROR_HINTS = {404: "error.not_found_hint", 403: "error.forbidden_hint"}
KEY_HINTS = {"error.admin_only": "error.admin_only_hint"}


def wants_html(request: Request) -> bool:
    """A browser asking for a page outside the API: errors become the HTML error page."""
    path = request.url.path
    api = path == "/api" or path.startswith("/api/")
    return not api and "text/html" in request.headers.get("accept", "")


def install(app: FastAPI) -> None:
    """Serve the UI's pages at ``/`` and its assets under ``/static``, and show errors of
    browser requests outside the API (unknown paths, oversized uploads) as HTML pages."""
    from fione.web import (  # they import this module
        account_ui,
        admin_ui,
        assistant_ui,
        automl,
        easyml,
        models_ui,
        modules_ui,
        sharing_ui,
    )

    app.mount(STATIC_PREFIX, StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(router)
    app.include_router(easyml.router)
    app.include_router(automl.router)
    app.include_router(models_ui.router)
    app.include_router(modules_ui.router)
    app.include_router(account_ui.router)
    app.include_router(admin_ui.router)
    app.include_router(sharing_ui.router)
    app.include_router(assistant_ui.router)
    app.add_exception_handler(UiError, _ui_error)
    api_http_error = app.exception_handlers[StarletteHTTPException]

    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        if wants_html(request):
            return error_page(
                request, exc.status_code, HTTP_ERROR_KEYS.get(exc.status_code, "error.generic")
            )
        return await api_http_error(request, exc)

    app.add_exception_handler(StarletteHTTPException, http_error)
    api_internal_error = app.exception_handlers[Exception]

    async def internal_error(request: Request, exc: Exception) -> Response:
        if wants_html(request):
            log.error("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
            # Served by Starlette's ServerErrorMiddleware, outside UIHeaders: set them here.
            response = error_page(request, 500, "error.generic")
            ui_headers(response.headers)
            return response
        return await api_internal_error(request, exc)

    app.add_exception_handler(Exception, internal_error)
    # Derived from immutable datasets (their ids are never reused), so kept across requests.
    app.state.ui_profiles = LruCache(PROFILE_CACHE_SIZE)
    app.state.ui_baselines = LruCache(BASELINE_CACHE_SIZE)
    app.state.ui_leaks = LruCache(LEAK_CACHE_SIZE)
    app.state.ui_sizes = LruCache(SIZE_CACHE_SIZE)
    app.state.ui_token_handoff = account_ui.SecretHandoff()  # new tokens' one-time view
