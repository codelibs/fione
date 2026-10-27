"""Jupyter Server settings of the notebook image. Its ``jupyter_server_config.py`` calls
``configure(c, os.environ)`` with the values the launcher passes to the container."""

import os
import re
import site
import time
from collections.abc import Mapping
from datetime import UTC, datetime

from fione_notebook.auth import (
    FioneAuthorizer,
    FioneIdentityProvider,
    hide_terminals_unless_admin,
)

_DIGITS = re.compile(r"[0-9]+")
_USER_ID = re.compile(r"[1-9][0-9]{0,17}")  # as Fione writes it: no sign, no leading zero
_HEX_32_BYTES = re.compile(r"[0-9a-fA-F]{64}")
# scheme://host[:port] and nothing else: it goes verbatim into the CSP header.
_ORIGIN = re.compile(
    r"https?://(?:[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*|\[[0-9A-Fa-f:.]+\])(?::[0-9]{1,5})?"
)
# The plan's one lifetime: a container, its token and its cookie live at most this long.
_MAX_LIFETIME = 604800
# Read once here and then unset, so kernels and terminals do not inherit them and `!env` output
# saved in a notebook does not hold them. Hygiene, not a boundary: /proc/<ppid>/environ (the
# same uid) still holds them, and they only reach the owner's own container anyway.
_SECRETS = ("FIONE_NB_KEY", "FIONE_NB_COOKIE_SECRET")


def _exit(message: str) -> SystemExit:
    return SystemExit(f"fione_notebook: {message}")


def _value(env: Mapping[str, str], name: str, pattern: re.Pattern) -> str:
    value = env.get(name, "")
    if not pattern.fullmatch(value):
        raise _exit(f"{name} is missing or malformed")  # never echo the value: it may be secret
    return value


def _read_only_tree(top: str) -> bool:
    """Whether nothing in the tree at ``top`` is writable to this process or a symlink (which
    could lead out of it). Links are not followed; an unreadable directory fails too."""

    def fail(error: OSError) -> None:
        raise error

    try:
        if os.path.islink(top):
            return False
        for dirpath, dirnames, filenames in os.walk(top, onerror=fail):
            if os.access(dirpath, os.W_OK):
                return False
            for name in dirnames + filenames:
                path = os.path.join(dirpath, name)
                if os.path.islink(path) or os.access(path, os.W_OK):
                    return False
    except OSError:
        return False
    return True


def _check_nothing_user_writable_is_searched(env: Mapping[str, str]) -> None:
    """Every user's Jupyter shares one browser origin, so anything a user could get served (a
    lab extension's static file, say) would run as every other user's JupyterLab. Jupyter
    serves and loads files from its config and data dirs, so those must be read-only to this
    process, and nothing may add user-writable dirs to the search path."""
    for name in ("JUPYTER_CONFIG_DIR", "JUPYTER_DATA_DIR"):
        path = env.get(name, "")
        if not path or not os.path.isdir(path) or not _read_only_tree(path):
            raise _exit(f"{name} must be a directory tree this user cannot write to")
    for name in ("JUPYTER_PATH", "JUPYTER_CONFIG_PATH"):
        if name in env:
            raise _exit(f"{name} must not be set")
    if site.ENABLE_USER_SITE:
        # jupyter_core then also searches ~/.local/share/jupyter and ~/.local/etc/jupyter.
        raise _exit("the Python user site must be off (PYTHONNOUSERSITE=1 or a virtualenv)")


def configure(c, env: Mapping[str, str]) -> None:
    """Configure the server for the container's owner, or exit when a value is malformed."""
    owner = _value(env, "FIONE_NB_OWNER", _USER_ID)
    key = _value(env, "FIONE_NB_KEY", _HEX_32_BYTES)
    cookie_secret = _value(env, "FIONE_NB_COOKIE_SECRET", _HEX_32_BYTES)
    origin = _value(env, "FIONE_NB_ORIGIN", _ORIGIN)
    expires = int(_value(env, "FIONE_NB_EXPIRES", _DIGITS))
    life = expires - time.time()
    if not 0 < life <= _MAX_LIFETIME:
        raise _exit(f"FIONE_NB_EXPIRES must be within {_MAX_LIFETIME} s from now")
    _check_nothing_user_writable_is_searched(env)
    base_url = f"/user/{owner}/"

    c.ServerApp.identity_provider_class = FioneIdentityProvider
    c.ServerApp.authorizer_class = FioneAuthorizer
    c.FioneIdentityProvider.owner = owner
    c.FioneIdentityProvider.key = bytes.fromhex(key)
    c.FioneIdentityProvider.expires = expires  # the server refuses cookies from then on
    c.ServerApp.ip = "0.0.0.0"
    c.ServerApp.port = 8888
    c.ServerApp.base_url = base_url
    c.ServerApp.root_dir = "/home/nb/work"
    c.ServerApp.allow_unauthenticated_access = False
    c.ServerApp.allow_remote_access = True  # the Host is the gateway's public name
    c.ServerApp.open_browser = False
    c.ServerApp.cookie_secret = bytes.fromhex(cookie_secret)
    c.ServerApp.extra_log_scrub_param_keys = ["launch"]
    c.ServerApp.tornado_settings = {
        "headers": {
            "Content-Security-Policy": (
                f"frame-ancestors 'self' {origin}; report-uri {base_url}api/security/csp-report"
            ),
        },
        "page_config_hook": hide_terminals_unless_admin,
    }
    # The browser drops the cookie when the container ends, whenever the sign-in was.
    c.IdentityProvider.cookie_options = {
        "samesite": "Lax",
        "expires": datetime.fromtimestamp(expires, UTC),
    }
    c.IdentityProvider.get_secure_cookie_kwargs = {"max_age_days": life / 86400}
    if origin.startswith("https://"):
        # The gateway talks plain http to the container, so tornado would not mark it Secure.
        c.IdentityProvider.secure_cookie = True
    c.MappingKernelManager.cull_idle_timeout = 1800
    c.MappingKernelManager.cull_interval = 300
    c.ServerApp.shutdown_no_activity_timeout = 3600
    # Admins only, by the authorizer; JupyterLab shows them to admins only (page_config_hook).
    c.ServerApp.terminals_enabled = True
    # Notebook trust signatures are kept in memory, as the data dir is read-only: outputs of
    # notebooks saved before a container restart show as untrusted until they are run again.
    c.NotebookNotary.db_file = ":memory:"
    c.NotebookNotary.secret = os.urandom(32)
    for name in _SECRETS:
        os.environ.pop(name, None)
