"""Launch tokens, the identity provider, the authorizer table and the server configuration of
the notebook image's Jupyter extension (no server is started here)."""

import base64
import hashlib
import hmac
import json
import os
import site
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from traitlets.config import Config

from fione_notebook.auth import (
    LAUNCH_PARAM,
    FioneAuthorizer,
    FioneIdentityProvider,
    FioneUser,
    hide_terminals_unless_admin,
    verify_launch_token,
)
from fione_notebook.config import configure

pytestmark = pytest.mark.notebook

KEY = bytes(range(32))
NOW = 1_800_000_000.0
JTI = "0123456789abcdef"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign(key: bytes, claims: dict, *, version: str = "v1", payload: str | None = None) -> str:
    """A launch token in the documented format: v1.<b64url(json)>.<b64url(HMAC-SHA256)>."""
    if payload is None:
        payload = _b64(json.dumps(claims).encode())
    signature = hmac.new(key, f"{version}.{payload}".encode(), hashlib.sha256).digest()
    return f"{version}.{payload}.{_b64(signature)}"


def claims(**changes) -> dict:
    """Valid claims for owner 7; a change to None drops that claim."""
    base = {"sub": "7", "name": "alice", "role": "editor", "exp": int(NOW) + 60, "jti": JTI}
    base.update(changes)
    return {name: value for name, value in base.items() if value is not None}


def _flip_signature_byte(token: str) -> str:
    head, signature = token.rsplit(".", 1)
    raw = bytearray(base64.urlsafe_b64decode(signature + "="))
    raw[5] ^= 0x01
    return f"{head}.{_b64(bytes(raw))}"


def test_launch_param_name():
    assert LAUNCH_PARAM == "launch"


def test_accepts_a_fresh_token_for_the_owner():
    got = verify_launch_token(KEY, sign(KEY, claims()), owner="7", now=NOW)
    assert got == claims()


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(sign(KEY, claims(exp=int(NOW) - 1)), id="expired-by-1s"),
        pytest.param(sign(KEY, claims(exp=int(NOW))), id="expires-now"),
        pytest.param(sign(KEY, claims(exp=int(NOW) + 301)), id="lives-over-300s"),
        pytest.param(_flip_signature_byte(sign(KEY, claims())), id="flipped-signature-byte"),
        pytest.param(sign(bytes(32), claims()), id="other-key"),
        pytest.param(sign(KEY, claims(sub="8")), id="other-user"),
        pytest.param(sign(KEY, claims(jti=None)), id="no-jti"),
        pytest.param(sign(KEY, claims(jti="short")), id="short-jti"),
        pytest.param(sign(KEY, claims(), version="v2"), id="v2-prefix"),
        pytest.param(sign(KEY, claims()) + ".x", id="three-dots"),
        pytest.param(sign(KEY, {}, payload=_b64(b"not json")), id="non-json-payload"),
        pytest.param(sign(KEY, {}, payload=_b64(b"[1, 2]")), id="json-not-an-object"),
        pytest.param(sign(KEY, {}, payload="e30*"), id="bad-base64"),
        pytest.param(sign(KEY, claims(exp="soon")), id="exp-not-an-int"),
        pytest.param(sign(KEY, claims(exp=True)), id="exp-a-bool"),
        pytest.param(sign(KEY, claims(sub=7)), id="sub-not-a-string"),
        pytest.param(sign(KEY, claims(role="owner")), id="unknown-role"),
        pytest.param(sign(KEY, claims(name=None)), id="no-name"),
        pytest.param("", id="empty"),
        pytest.param("v1.\udc80.\udc80", id="lone-surrogates"),
        pytest.param(sign(KEY, claims()) + "\u00e9", id="non-ascii"),
    ],
)
def test_rejects(token):
    assert verify_launch_token(KEY, token, owner="7", now=NOW) is None


def test_accepts_a_token_living_300s():
    token = sign(KEY, claims(exp=int(NOW) + 300))
    assert verify_launch_token(KEY, token, owner="7", now=NOW) is not None


def test_signature_padding_variants_are_rejected():
    token = sign(KEY, claims())
    assert verify_launch_token(KEY, token + "=", owner="7", now=NOW) is None


# --- identity provider and authorizer --------------------------------------------------------


def _provider(owner: str = "7", expires: int | None = None) -> FioneIdentityProvider:
    if expires is None:
        expires = int(time.time()) + 3600
    return FioneIdentityProvider(owner=owner, key=KEY, expires=expires)


def test_cookie_round_trip_keeps_name_and_role():
    idp = _provider()
    user = FioneUser(username="7", name="alice", role="admin")
    assert json.loads(idp.user_to_cookie(user)) == {
        "username": "7",
        "name": "alice",
        "role": "admin",
    }
    back = idp.user_from_cookie(idp.user_to_cookie(user))
    assert (back.username, back.name, back.role) == ("7", "alice", "admin")


@pytest.mark.parametrize(
    "cookie",
    [
        json.dumps({"username": "8", "name": "bob", "role": "admin"}),
        json.dumps({"username": "7", "name": "alice", "role": "root"}),
        json.dumps({"username": "7", "role": "editor"}),
        json.dumps(["7"]),
        "not json",
    ],
)
def test_user_from_cookie_refuses_anything_but_the_owner(cookie):
    assert _provider().user_from_cookie(cookie) is None


def test_user_from_cookie_refuses_a_cookie_after_the_container_expiry():
    cookie = json.dumps({"username": "7", "name": "alice", "role": "editor"})
    assert _provider(expires=int(time.time()) - 1).user_from_cookie(cookie) is None
    assert _provider().user_from_cookie(cookie) is not None


def test_identity_provider_never_token_authenticates():
    idp = _provider()
    assert idp.token == ""
    handler = SimpleNamespace(
        request=SimpleNamespace(headers={"Authorization": "token x"}),
        get_argument=lambda *a, **k: "x",
    )
    assert idp.get_user_token(handler) is None


@pytest.mark.parametrize(("owner", "key"), [("", KEY), ("7", b""), ("7", KEY[:31])])
def test_validate_security_exits_without_owner_or_key(owner, key):
    idp = FioneIdentityProvider(owner=owner, key=key)
    app = SimpleNamespace(ip="127.0.0.1", log=SimpleNamespace(warning=print))
    with pytest.raises(SystemExit):
        idp.validate_security(app)


RESOURCES = [
    "api",
    "config",
    "contents",
    "csp",
    "events",
    "kernels",
    "kernelspecs",
    "lsp",
    "nbconvert",
    "server",
    "sessions",
    "terminals",
]
SIGNED_IN = {
    *[
        (r, "read")
        for r in ("contents", "kernelspecs", "sessions", "kernels", "config", "api", "events")
    ],
    *[(r, "write") for r in ("contents", "sessions", "kernels", "config", "events")],
    *[(r, "execute") for r in ("kernels", "events", "lsp")],
    ("lsp", "read"),
    ("nbconvert", "read"),
}
ADMIN = SIGNED_IN | {
    ("terminals", "read"),
    ("terminals", "write"),
    ("terminals", "execute"),
    ("server", "write"),
}


def _granted(user) -> set[tuple[str, str]]:
    authorizer = FioneAuthorizer(identity_provider=_provider())
    return {
        (resource, action)
        for resource in RESOURCES
        for action in ("read", "write", "execute")
        if authorizer.is_authorized(None, user, action, resource)
    }


@pytest.mark.parametrize(
    ("user", "expected"),
    [
        (FioneUser(username="7", name="a", role="viewer"), SIGNED_IN),
        (FioneUser(username="7", name="a", role="editor"), SIGNED_IN),
        (FioneUser(username="7", name="a", role="admin"), ADMIN),
        (FioneUser(username="8", name="b", role="admin"), set()),
        (FioneUser(username="7", name="a", role="root"), set()),
        (None, set()),
    ],
    ids=["viewer", "editor", "admin", "other-user", "unknown-role", "anonymous"],
)
def test_authorizer_grants_exactly_the_table(user, expected):
    assert _granted(user) == expected


@pytest.mark.parametrize(
    ("user", "available"),
    [
        (FioneUser(username="7", name="a", role="viewer"), False),
        (FioneUser(username="7", name="a", role="editor"), False),
        (FioneUser(username="7", name="a", role="admin"), True),
        (None, False),
    ],
    ids=["viewer", "editor", "admin", "anonymous"],
)
def test_only_admins_are_shown_terminals(user, available):
    page_config = {"terminalsAvailable": True, "baseUrl": "/user/7/"}
    shown = hide_terminals_unless_admin(SimpleNamespace(current_user=user), page_config)
    assert shown == {"terminalsAvailable": available, "baseUrl": "/user/7/"}
    assert hide_terminals_unless_admin(object(), page_config)["terminalsAvailable"] is False
    assert page_config == {"terminalsAvailable": True, "baseUrl": "/user/7/"}  # a copy changed


# --- configure ----------------------------------------------------------------------------


@pytest.fixture
def jupyter_dirs(tmp_path):
    """Read-only config and data dirs, as root-owned dirs in the image are to the server."""
    config_dir, data_dir = tmp_path / "config", tmp_path / "data"
    for d in (config_dir, data_dir):
        d.mkdir()
        d.chmod(0o555)
    yield config_dir, data_dir
    for d in (config_dir, data_dir):
        d.chmod(0o755)
        for sub in d.iterdir():
            if sub.is_dir() and not sub.is_symlink():
                sub.chmod(0o755)


@pytest.fixture
def env(jupyter_dirs):
    config_dir, data_dir = jupyter_dirs
    return {
        "FIONE_NB_OWNER": "7",
        "FIONE_NB_KEY": "ab" * 32,
        "FIONE_NB_COOKIE_SECRET": "cd" * 32,
        "FIONE_NB_ORIGIN": "http://127.0.0.1:18080",
        "FIONE_NB_EXPIRES": str(int(time.time()) + 43200),
        "JUPYTER_CONFIG_DIR": str(config_dir),
        "JUPYTER_DATA_DIR": str(data_dir),
    }


def test_configure_sets_the_security_traits(env):
    c = Config()
    configure(c, env)
    app = c.ServerApp
    assert app.identity_provider_class is FioneIdentityProvider
    assert app.authorizer_class is FioneAuthorizer
    assert (app.ip, app.port, app.base_url, app.root_dir) == (
        "0.0.0.0",
        8888,
        "/user/7/",
        "/home/nb/work",
    )
    assert app.allow_unauthenticated_access is False
    assert app.allow_remote_access is True
    assert app.open_browser is False
    assert app.cookie_secret == bytes.fromhex("cd" * 32)
    assert app.extra_log_scrub_param_keys == ["launch"]
    assert app.tornado_settings["headers"]["Content-Security-Policy"] == (
        "frame-ancestors 'self' http://127.0.0.1:18080; report-uri /user/7/api/security/csp-report"
    )
    assert app.terminals_enabled is True
    assert app.tornado_settings["page_config_hook"] is hide_terminals_unless_admin
    assert app.shutdown_no_activity_timeout == 3600
    assert c.MappingKernelManager.cull_idle_timeout == 1800
    assert c.MappingKernelManager.cull_interval == 300
    assert c.NotebookNotary.db_file == ":memory:"
    assert len(c.NotebookNotary.secret) == 32
    assert c.FioneIdentityProvider.owner == "7"
    assert c.FioneIdentityProvider.key == bytes.fromhex("ab" * 32)
    expires = int(env["FIONE_NB_EXPIRES"])
    assert c.FioneIdentityProvider.expires == expires
    # The browser cookie ends with the container, wherever in its life the sign-in happens.
    assert c.IdentityProvider.cookie_options == {
        "samesite": "Lax",
        "expires": datetime.fromtimestamp(expires, UTC),
    }
    max_age = c.IdentityProvider.get_secure_cookie_kwargs["max_age_days"]
    assert max_age == pytest.approx(0.5, abs=0.001)
    assert "secure_cookie" not in c.IdentityProvider  # http: tornado's per-request default


def test_configure_marks_the_cookie_secure_behind_https(env):
    c = Config()
    configure(c, {**env, "FIONE_NB_ORIGIN": "https://fione.example"})
    assert c.IdentityProvider.secure_cookie is True


@pytest.mark.parametrize(
    ("offset", "accepted"),
    [(-1, False), (0, False), (1, True), (604800, True), (604801, False), (10**30, False)],
)
def test_configure_bounds_the_container_expiry(env, offset, accepted):
    env["FIONE_NB_EXPIRES"] = str(int(time.time()) + offset)
    if accepted:
        configure(Config(), env)
    else:
        with pytest.raises(SystemExit):
            configure(Config(), env)


def test_configure_unsets_the_secrets_as_hygiene_not_a_boundary(env, monkeypatch):
    # Kernels then do not inherit them, so `!env` output saved in a notebook does not hold
    # them; /proc/<server pid>/environ (same uid) still does.
    monkeypatch.setenv("FIONE_NB_KEY", env["FIONE_NB_KEY"])
    monkeypatch.setenv("FIONE_NB_COOKIE_SECRET", env["FIONE_NB_COOKIE_SECRET"])
    configure(Config(), dict(os.environ) | env)
    assert "FIONE_NB_KEY" not in os.environ
    assert "FIONE_NB_COOKIE_SECRET" not in os.environ


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"FIONE_NB_OWNER": "7a"}, id="non-digit-owner"),
        pytest.param({"FIONE_NB_OWNER": "٧"}, id="non-ascii-digit-owner"),
        pytest.param({"FIONE_NB_OWNER": "7\n"}, id="owner-with-newline"),
        pytest.param({"FIONE_NB_OWNER": "007"}, id="owner-with-leading-zeros"),
        pytest.param({"FIONE_NB_OWNER": "0"}, id="owner-zero"),
        pytest.param({"FIONE_NB_OWNER": "1" * 19}, id="owner-too-long"),
        pytest.param({"FIONE_NB_OWNER": None}, id="no-owner"),
        pytest.param({"FIONE_NB_KEY": "a" * 63}, id="63-hex-key"),
        pytest.param({"FIONE_NB_KEY": "g" * 64}, id="non-hex-key"),
        pytest.param({"FIONE_NB_KEY": None}, id="no-key"),
        pytest.param({"FIONE_NB_COOKIE_SECRET": "cd" * 16}, id="short-cookie-secret"),
        pytest.param({"FIONE_NB_ORIGIN": "http://fione.example/path"}, id="origin-with-path"),
        pytest.param({"FIONE_NB_ORIGIN": "http://fione.example/"}, id="origin-with-slash"),
        pytest.param({"FIONE_NB_ORIGIN": "http://a; script-src *"}, id="origin-injection"),
        pytest.param({"FIONE_NB_ORIGIN": "ftp://fione.example"}, id="origin-scheme"),
        pytest.param({"FIONE_NB_ORIGIN": "http://u@fione.example"}, id="origin-userinfo"),
        pytest.param({"FIONE_NB_EXPIRES": "soon"}, id="non-digit-expires"),
        pytest.param({"JUPYTER_CONFIG_DIR": None}, id="no-config-dir"),
        pytest.param({"JUPYTER_DATA_DIR": None}, id="no-data-dir"),
        pytest.param({"JUPYTER_DATA_DIR": "/nonexistent/fione-nb"}, id="missing-data-dir"),
        pytest.param({"JUPYTER_PATH": "/opt/jupyter"}, id="jupyter-path-set"),
        pytest.param({"JUPYTER_CONFIG_PATH": "/opt/jupyter"}, id="jupyter-config-path-set"),
    ],
)
def test_configure_refuses_malformed_env(env, changes):
    for name, value in changes.items():
        if value is None:
            env.pop(name)
        else:
            env[name] = value
    with pytest.raises(SystemExit):
        configure(Config(), env)


@pytest.mark.parametrize("which", ["JUPYTER_CONFIG_DIR", "JUPYTER_DATA_DIR"])
def test_configure_refuses_a_writable_jupyter_dir(env, which):
    os.chmod(env[which], 0o755)
    with pytest.raises(SystemExit):
        configure(Config(), env)


@pytest.mark.parametrize("which", ["JUPYTER_CONFIG_DIR", "JUPYTER_DATA_DIR"])
@pytest.mark.parametrize("what", ["writable-subdir", "symlink", "writable-file"])
def test_configure_refuses_anything_writable_inside_a_jupyter_dir(env, which, what, tmp_path):
    top = Path(env[which])
    top.chmod(0o755)
    sub = top / "labextensions"
    sub.mkdir()
    if what == "writable-subdir":
        (sub / "evil").mkdir()  # writable, under a read-only parent
    elif what == "symlink":
        (sub / "evil").symlink_to(tmp_path)
    else:
        (sub / "page_config.json").write_text("{}")
    sub.chmod(0o555)
    top.chmod(0o555)
    with pytest.raises(SystemExit):
        configure(Config(), env)
    sub.chmod(0o755)
    for child in sub.iterdir():
        if child.is_dir() and not child.is_symlink():
            child.chmod(0o755)


def test_configure_accepts_a_read_only_tree(env):
    top = Path(env["JUPYTER_DATA_DIR"])
    top.chmod(0o755)
    sub = top / "labextensions" / "ok" / "static"
    sub.mkdir(parents=True)
    (sub / "x.js").write_text("")
    (sub / "x.js").chmod(0o444)
    for d in (sub, sub.parent, sub.parent.parent, top):
        d.chmod(0o555)
    configure(Config(), env)
    for d in (top, sub.parent.parent, sub.parent, sub):
        d.chmod(0o755)


def test_configure_refuses_the_python_user_site(env, monkeypatch):
    # With the user site on, ~/.local/share/jupyter and ~/.local/etc/jupyter are searched
    # next to JUPYTER_DATA_DIR and JUPYTER_CONFIG_DIR, so the user could get files served.
    monkeypatch.setattr(site, "ENABLE_USER_SITE", True)
    with pytest.raises(SystemExit):
        configure(Config(), env)
