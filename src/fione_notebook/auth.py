"""Sign-in and authorization for a per-user notebook container.

Fione opens ``<base_url>login?launch=<token>``. The launch token is
``v1.<b64url(json claims)>.<b64url(HMAC-SHA256(key, "v1." + payload))>``, signed with a key
Fione derives for this container only, and it is good for one sign-in within its short life.
The login cookie then names the owner and their Fione role. Only the owner is ever authorized.

The sign-in must come from a same-site page (``Sec-Fetch-Site``), that is from Fione. A launch
token is a bearer credential for its owner's container, and its owner can take one from their
own notebook page without using it. Were a cross-site navigation accepted, an attacker could
sign a victim's browser into the attacker's container, whose trusted notebook output would
then run as script on the notebook origin that every user's JupyterLab shares, and reach the
victim's own JupyterLab from there.
"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from jupyter_server.auth.authorizer import Authorizer
from jupyter_server.auth.decorator import allow_unauthenticated
from jupyter_server.auth.identity import IdentityProvider, User
from jupyter_server.base.handlers import JupyterHandler
from tornado import web
from traitlets import Bytes, Dict, Int, Unicode, default

LAUNCH_PARAM = "launch"
ROLES = frozenset({"admin", "editor", "viewer"})
KEY_BYTES = 32
_VERSION = "v1"
_MIN_JTI = 16
_MAX_LIFE = 300  # seconds: Fione issues 60 s tokens; anything longer is an issuer bug
_SAME_SITE = frozenset({"same-site", "same-origin"})


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(text: str) -> bytes:
    return base64.b64decode(text + "=" * (-len(text) % 4), altchars=b"-_", validate=True)


def verify_launch_token(
    key: bytes, token: str, *, owner: str, now: float | None = None
) -> dict | None:
    """The claims of a launch token signed with ``key`` for ``owner`` that has not expired;
    None for anything else. It never raises on a malformed token."""
    parts = token.split(".")
    if not token.isascii() or len(parts) != 3 or parts[0] != _VERSION or not owner:
        return None
    _, payload, signature = parts
    expected = hmac.new(key, f"{_VERSION}.{payload}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64encode(expected).encode(), signature.encode()):
        return None
    try:
        claims = json.loads(_b64decode(payload))
    except ValueError:  # bad base64, UTF-8 or JSON
        return None
    if not isinstance(claims, dict):
        return None
    sub, name, role, exp, jti = (claims.get(k) for k in ("sub", "name", "role", "exp", "jti"))
    if not (
        isinstance(sub, str)
        and isinstance(name, str)
        and isinstance(role, str)
        and role in ROLES
        and isinstance(exp, int)
        and not isinstance(exp, bool)
        and isinstance(jti, str)
        and len(jti) >= _MIN_JTI
    ):
        return None
    now = time.time() if now is None else now
    if exp <= now or exp - now > _MAX_LIFE or sub != owner:
        return None
    return claims


@dataclass
class FioneUser(User):
    """A signed-in Fione user; ``role`` is their Fione role."""

    role: str = ""


def _safe_next(target: str, base_url: str) -> str:
    """``target`` when it is a plain path under ``base_url``, otherwise the lab."""
    decoded = unquote(target)
    parts = urlsplit(target)
    if (
        parts.scheme
        or parts.netloc
        or not target.startswith(base_url)
        or "\\" in decoded
        or any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in decoded)
        or {".", ".."} & set(unquote(parts.path).split("/"))
    ):
        return base_url + "lab"
    return target


class FioneLoginHandler(JupyterHandler):
    """``GET <base_url>login?launch=<token>&next=<path>``: a launch token from Fione becomes the
    login cookie, then the browser goes on to ``next`` (a path under the base URL) or the lab."""

    async def prepare(self, **kwargs):
        # jupyter_server's access log line names request.uri. Its scrubbing knows `launch=` but
        # not a percent-encoded spelling of the key, so the query is not logged at all.
        if self.request.query:
            self.request.uri = self.request.path + "?[hidden]"
        return await super().prepare(**kwargs)

    @allow_unauthenticated
    def get(self) -> None:
        # Bare 403s throughout: tornado would log a message with the request URI, launch token
        # included. Both checks come before redemption, so a refused token is not used up.
        if self.request.headers.get("Sec-Fetch-Site") not in _SAME_SITE:
            raise web.HTTPError(403)  # see the module docstring; browsers always send it
        if any("%" in part.partition("=")[0] for part in self.request.query.split("&")):
            raise web.HTTPError(403)  # Fione never encodes a key
        idp = self.identity_provider
        claims = idp.redeem(self.get_argument(LAUNCH_PARAM, ""))
        if claims is None:
            raise web.HTTPError(403)
        user = FioneUser(username=claims["sub"], name=claims["name"], role=claims["role"])
        idp.set_login_cookie(self, user)
        self.redirect(_safe_next(self.get_argument("next", ""), self.base_url))

    def log_exception(self, typ, value, tb) -> None:
        # Tornado's version names the request URI, which holds the launch token. The access
        # log line (jupyter_server's log_request) is written anyway, without the query.
        if not isinstance(value, web.HTTPError):
            self.log.error(
                "Uncaught exception in %s %s",
                self.request.method,
                self.request.path,
                exc_info=(typ, value, tb),
            )


class FioneIdentityProvider(IdentityProvider):
    """Users come only from the login cookie set by ``FioneLoginHandler``: there is no Jupyter
    token, and no request is ever token-authenticated (which would skip the XSRF and Origin
    checks)."""

    owner = Unicode(config=True, help="The Fione user id that owns this container.")
    key = Bytes(config=True, help="The per-container key launch tokens are signed with.")
    expires = Int(config=True, help="When the container ends (epoch seconds); cookies too.")
    _used_jti = Dict()  # jti -> exp of redeemed launch tokens

    @default("token")
    def _token_default(self) -> str:
        return ""

    @default("login_handler_class")
    def _login_handler_class_default(self) -> type:
        return FioneLoginHandler

    def redeem(self, token: str, now: float | None = None) -> dict | None:
        """The claims of a valid launch token not redeemed before, which it then marks as
        redeemed; None otherwise. A container is one process, so memory is enough."""
        now = time.time() if now is None else now
        self._used_jti = {jti: exp for jti, exp in self._used_jti.items() if exp > now}
        claims = verify_launch_token(self.key, token, owner=self.owner, now=now) if token else None
        if claims is None or claims["jti"] in self._used_jti:
            return None
        self._used_jti[claims["jti"]] = claims["exp"]
        return claims

    def get_user_token(self, handler) -> None:
        return None

    def user_to_cookie(self, user: User) -> str:
        role = user.role if isinstance(user, FioneUser) else ""
        return json.dumps({"username": user.username, "name": user.name, "role": role})

    def user_from_cookie(self, cookie_value: str) -> FioneUser | None:
        try:
            data = json.loads(cookie_value)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        username, name, role = data.get("username"), data.get("name"), data.get("role")
        if (
            not self.owner
            or time.time() >= self.expires
            or username != self.owner
            or not isinstance(name, str)
            or not isinstance(role, str)
            or role not in ROLES
        ):
            return None
        return FioneUser(username=username, name=name, role=role)

    def validate_security(self, app, ssl_options=None) -> None:
        if not self.owner or len(self.key) != KEY_BYTES:
            raise SystemExit("fione_notebook: the owner and a 32-byte launch key are required")
        super().validate_security(app, ssl_options)


# (resource, action) pairs granted to the owner; anything else is denied.
_READ = ("contents", "kernelspecs", "sessions", "kernels", "config", "api", "events")
_WRITE = ("contents", "sessions", "kernels", "config", "events")
_EXECUTE = ("kernels", "events", "lsp")
_SIGNED_IN = frozenset(
    [(resource, "read") for resource in _READ]
    + [(resource, "write") for resource in _WRITE]
    + [(resource, "execute") for resource in _EXECUTE]
    + [("lsp", "read"), ("nbconvert", "read")]
)
# Terminals give nothing a kernel does not; they stay an admin convenience.
_ADMIN = _SIGNED_IN | {
    ("terminals", "read"),
    ("terminals", "write"),
    ("terminals", "execute"),
    ("server", "write"),
}


def hide_terminals_unless_admin(handler, page_config: dict) -> dict:
    """JupyterLab's ``page_config_hook``: a user the authorizer refuses terminals (anyone but
    an admin, or no user at all) gets ``terminalsAvailable: false``, so JupyterLab neither
    offers terminals nor polls their list (a 403 each time)."""
    user = getattr(handler, "current_user", None)
    if isinstance(user, FioneUser) and user.role == "admin":
        return page_config
    return {**page_config, "terminalsAvailable": False}


class FioneAuthorizer(Authorizer):
    """The owner only, and only the pairs above. A viewer granted notebooks runs code too:
    their boundary is their read-only Fione token, not Jupyter.

    JupyterLab's settings, workspaces, extensions, build, plugins, news and update handlers
    are only @web.authenticated, so they never ask this authorizer: every role of the owner
    reaches them. Their writes fail on the read-only config and data dirs and the root-owned
    environment of the notebook image, and the notebook gateway refuses settings and
    workspace writes."""

    def is_authorized(self, handler, user, action, resource) -> bool:
        owner = self.identity_provider.owner
        if not isinstance(user, FioneUser) or not owner or user.username != owner:
            return False
        if user.role == "admin":
            return (resource, action) in _ADMIN
        return user.role in ROLES and (resource, action) in _SIGNED_IN
