"""The account page: who one is, one's password and one's API tokens, with the API's rules.

The password change goes through the API's own path (``change_own_password``: the login
throttle, the same policy) and re-issues the session cookie, since every session is bound to
the password. A new token's secret is shown once: the creating post redirects to the account
page, which takes the secret from a short-lived server-side handoff keyed by the user and
the session (never the URL, a cookie or the log), so a reload or a second tab shows nothing.
"""

import math
import threading
import time
from collections import OrderedDict

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from fione.api.deps import Auth, Conn, request_host
from fione.api.errors import ApiError
from fione.api.routes_auth import change_own_password, start_session
from fione.api.schemas import MAX_PASSWORD_LENGTH
from fione.auth import service as auth_service
from fione.auth.passwords import MIN_PASSWORD_LENGTH
from fione.auth.roles import Role
from fione.web.access import SmallForm, field, form_auth, parse_id, signed_in
from fione.web.views import UiError, render

router = APIRouter(include_in_schema=False)

TOKENS_PER_PAGE = 20
MAX_TOKEN_NAME = 100  # as the API's token name
HANDOFF_SECS = 120  # how long a new token's secret waits for its one page view
HANDOFF_SIZE = 256
DONE = ("password", "revoked")  # ?done=: the confirmation shown after a change


class SecretHandoff:
    """At most ``size`` secrets, each for ``ttl`` seconds, taken (and so removed) by the one
    page view that shows it. In memory, per process: the app runs as one worker."""

    def __init__(self, size: int = HANDOFF_SIZE, ttl: float = HANDOFF_SECS):
        self._size, self._ttl = size, ttl
        self._items: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def put(self, key, value) -> None:
        with self._lock:
            self._items[key] = (time.monotonic() + self._ttl, value)
            self._items.move_to_end(key)
            while len(self._items) > self._size:
                self._items.popitem(last=False)

    def take(self, key):
        with self._lock:
            expires, value = self._items.pop(key, (0.0, None))
        return value if expires > time.monotonic() else None


def _handoff(request: Request) -> SecretHandoff:
    return request.app.state.ui_token_handoff


def _key(auth: Auth) -> tuple[int, str]:
    return auth.user.id, auth.session.csrf


def _page_number(value: str | None, pages: int) -> int:
    if value is None or not value.isascii() or not value.isdigit() or len(value) > 12:
        return 1
    return min(pages, max(1, int(value)))


def _view(
    request: Request,
    conn,
    auth: Auth,
    *,
    status: int = 200,
    errors: dict | None = None,
    created: dict | None = None,
    token_name: str = "",
    retry: str | None = None,
) -> Response:
    total = auth_service.count_tokens(conn, auth.user.id)
    pages = max(1, math.ceil(total / TOKENS_PER_PAGE))
    number = _page_number(request.query_params.get("page"), pages)
    tokens = auth_service.page_tokens(
        conn, auth.user.id, limit=TOKENS_PER_PAGE, offset=(number - 1) * TOKENS_PER_PAGE
    )
    done = request.query_params.get("done")
    response = render(
        request,
        "account.html",
        auth,
        status=status,
        nav="account",
        roles=[r.value for r in Role],
        tokens=tokens,
        total=total,
        page_number=number,
        pages=pages,
        created=created,
        errors=errors or {},
        token_name=token_name,
        done=done if done in DONE and status == 200 else None,
        min_password=MIN_PASSWORD_LENGTH,
        max_password=MAX_PASSWORD_LENGTH,
        max_token_name=MAX_TOKEN_NAME,
        api_base=f"{request.url.scheme}://{request_host(request) or 'localhost'}",
        here="/account",
    )
    if retry:
        response.headers["Retry-After"] = retry
    return response


@router.get("/account")
def account(request: Request, conn: Conn) -> Response:
    auth = signed_in(request, conn)
    created = _handoff(request).take(_key(auth))
    return _view(request, conn, auth, created=created)


def _password_errors(current: str, new: str, confirm: str) -> dict:
    """The API's limits (checked before the throttle counts an attempt) and the repeat."""
    errors = {}
    if not current or len(current) > MAX_PASSWORD_LENGTH:
        errors["current"] = "account.error.current_wrong" if current else "account.error.current"
    if not MIN_PASSWORD_LENGTH <= len(new) <= MAX_PASSWORD_LENGTH:
        errors["new"] = "account.error.new_length"
    elif new != confirm:
        errors["confirm"] = "account.error.confirm"
    return errors


@router.post("/account/password")
def change_password(request: Request, conn: Conn, form: SmallForm) -> Response:
    auth = form_auth(request, conn, form)
    current = field(form, "current_password")
    new = field(form, "new_password")
    errors = _password_errors(current, new, field(form, "confirm_password"))
    if errors:
        return _view(request, conn, auth, status=422, errors=errors)
    try:
        change_own_password(request, conn, auth.user, current, new)
    except ApiError as e:
        key = {429: "error.throttled", 403: "account.error.current_wrong"}.get(
            e.status, "account.error.new_length"
        )
        retry = (e.headers or {}).get("Retry-After")
        name = "form" if e.status == 429 else ("current" if e.status == 403 else "new")
        return _view(request, conn, auth, status=e.status, errors={name: key}, retry=retry)
    response = RedirectResponse("/account?done=password", 303)
    start_session(request, response, conn, auth.user)  # the old session ended with it
    return response


@router.post("/account/tokens")
def create_token(request: Request, conn: Conn, form: SmallForm) -> Response:
    auth = form_auth(request, conn, form)
    name = field(form, "name").strip()
    if not 1 <= len(name) <= MAX_TOKEN_NAME:
        errors = {"token": "account.error.token_name"}
        return _view(request, conn, auth, status=422, errors=errors, token_name=name[:200])
    record, secret = auth_service.create_token(conn, auth.user.id, name)
    _handoff(request).put(_key(auth), {"id": record.id, "name": record.name, "secret": secret})
    return RedirectResponse("/account", 303)


@router.post("/account/tokens/{tid}/revoke")
def revoke_token(request: Request, conn: Conn, tid: str, form: SmallForm) -> Response:
    """One's own tokens only: any other id is not found, also for administrators (the API
    lets them revoke anyone's; this page is about one's own)."""
    auth = form_auth(request, conn, form)
    record = auth_service.get_token(conn, parse_id(tid))
    if record is None or record.user_id != auth.user.id:
        raise UiError(404, "error.not_found")
    auth_service.revoke_token(conn, record.id)
    return RedirectResponse("/account?done=revoked", 303)
