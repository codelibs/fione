"""The web UI: server-rendered pages (Jinja2, autoescaped) over the same services as the API.

Pages authenticate with the session cookie only and send anonymous visitors to
``/login?next=<path>``. Sign-in and first-admin setup are done by the page's script against
the JSON API; the UI's own unsafe endpoints check the session's CSRF token (``X-CSRF-Token``,
which HTMX sends from ``hx-headers`` on ``<body>``, or a ``csrf_token`` form field).
"""

import sqlite3
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote, urlencode, urlsplit

from fastapi import APIRouter, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from fione import i18n
from fione.api.deps import Auth, Conn, cookie_auth, effective_access, request_host
from fione.api.security import SESSION_COOKIE, origin_matches, tokens_equal
from fione.auth import service as auth_service
from fione.auth.passwords import MIN_PASSWORD_LENGTH
from fione.auth.roles import Role
from fione.projects import service as projects
from fione.version import __version__

WEB_DIR = Path(__file__).parent
STATIC_PREFIX = "/static"
LANG_COOKIE_MAX_AGE = 365 * 24 * 3600
MAX_NEXT_LENGTH = 2048
# Percent-decoding rounds a ``next`` value is checked through (a proxy or app that decodes
# once more must not turn it into ``//host``).
NEXT_DECODE_ROUNDS = 3

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(
    env=Environment(
        loader=FileSystemLoader(WEB_DIR / "templates"),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
)


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
    also after percent-decoding it (``/%2F%2Fhost``, double-encoded too)."""
    if not value or len(value) > MAX_NEXT_LENGTH:
        return "/"
    decoded = value
    for _ in range(NEXT_DECODE_ROUNDS):
        if not _same_site_path(decoded):
            return "/"
        decoded = unquote(decoded)
    return value


def language(request: Request) -> str:
    return i18n.resolve_language(
        request.cookies.get(i18n.LANG_COOKIE), request.headers.get("accept-language")
    )


def _here(request: Request) -> str:
    query = request.url.query
    return request.url.path + (f"?{query}" if query else "")


def _static(path: str) -> str:
    return f"{STATIC_PREFIX}/{path}?v={__version__}"


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
            **context,  # may override ``here``: where the language switch returns to
        },
        status_code=status,
    )


def _to_login(request: Request) -> RedirectResponse:
    return RedirectResponse("/login?" + urlencode({"next": _here(request)}), 303)


def _action_auth(request: Request, conn: sqlite3.Connection, token: str | None = None) -> Auth:
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
        _action_auth(request, conn, csrf_token)
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
        return _to_login(request)
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
    auth = _action_auth(request, conn)
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
        return _to_login(request)
    return render(request, "_design.html", auth)


async def _ui_error(request: Request, exc: UiError) -> Response:
    message = i18n.t(exc.key, language(request))
    if request.headers.get("hx-request"):
        response: Response = PlainTextResponse(message, status_code=exc.status)
        if exc.status == 401:
            current = urlsplit(request.headers.get("hx-current-url", ""))
            back = safe_next(current.path + (f"?{current.query}" if current.query else ""))
            response.headers["HX-Redirect"] = "/login?" + urlencode({"next": back})
        return response
    # here="/": the language switch must not return to a POST-only path.
    return render(request, "error.html", status=exc.status, message=message, here="/")


def install(app: FastAPI) -> None:
    """Serve the UI's pages at ``/`` and its assets under ``/static``."""
    app.mount(STATIC_PREFIX, StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(router)
    app.add_exception_handler(UiError, _ui_error)
