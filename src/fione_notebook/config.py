"""Jupyter Server settings of the notebook image. Its ``jupyter_server_config.py`` calls
``configure(c, os.environ)`` with the values the launcher passes to the container."""

import os
import re
import site
import time
from collections.abc import Mapping

from fione_notebook.auth import FioneAuthorizer, FioneIdentityProvider

_DIGITS = re.compile(r"[0-9]+")
_HEX_32_BYTES = re.compile(r"[0-9a-fA-F]{64}")
# scheme://host[:port] and nothing else: it goes verbatim into the CSP header.
_ORIGIN = re.compile(
    r"https?://(?:[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*|\[[0-9A-Fa-f:.]+\])(?::[0-9]{1,5})?"
)
# Read once here; kernels and terminals, which inherit the server's environment, do not need them.
_SECRETS = ("FIONE_NB_KEY", "FIONE_NB_COOKIE_SECRET")


def _exit(message: str) -> SystemExit:
    return SystemExit(f"fione_notebook: {message}")


def _value(env: Mapping[str, str], name: str, pattern: re.Pattern) -> str:
    value = env.get(name, "")
    if not pattern.fullmatch(value):
        raise _exit(f"{name} is missing or malformed")  # never echo the value: it may be secret
    return value


def _check_nothing_user_writable_is_searched(env: Mapping[str, str]) -> None:
    """Every user's Jupyter shares one browser origin, so anything a user could get served (a
    lab extension's static file, say) would run as every other user's JupyterLab. Jupyter
    serves and loads files from its config and data dirs, so those must be read-only to this
    process, and nothing may add user-writable dirs to the search path."""
    for name in ("JUPYTER_CONFIG_DIR", "JUPYTER_DATA_DIR"):
        path = env.get(name, "")
        if not path or not os.path.isdir(path) or os.access(path, os.W_OK):
            raise _exit(f"{name} must be a directory this user cannot write to")
    for name in ("JUPYTER_PATH", "JUPYTER_CONFIG_PATH"):
        if name in env:
            raise _exit(f"{name} must not be set")
    if site.ENABLE_USER_SITE:
        # jupyter_core then also searches ~/.local/share/jupyter and ~/.local/etc/jupyter.
        raise _exit("the Python user site must be off (PYTHONNOUSERSITE=1 or a virtualenv)")


def configure(c, env: Mapping[str, str]) -> None:
    """Configure the server for the container's owner, or exit when a value is malformed."""
    owner = _value(env, "FIONE_NB_OWNER", _DIGITS)
    key = _value(env, "FIONE_NB_KEY", _HEX_32_BYTES)
    cookie_secret = _value(env, "FIONE_NB_COOKIE_SECRET", _HEX_32_BYTES)
    origin = _value(env, "FIONE_NB_ORIGIN", _ORIGIN)
    expires = int(_value(env, "FIONE_NB_EXPIRES", _DIGITS))
    _check_nothing_user_writable_is_searched(env)
    base_url = f"/user/{owner}/"
    cookie_days = max(expires - time.time(), 0) / 86400

    c.ServerApp.identity_provider_class = FioneIdentityProvider
    c.ServerApp.authorizer_class = FioneAuthorizer
    c.FioneIdentityProvider.owner = owner
    c.FioneIdentityProvider.key = bytes.fromhex(key)
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
    }
    c.IdentityProvider.cookie_options = {"samesite": "Lax", "expires_days": cookie_days}
    c.IdentityProvider.get_secure_cookie_kwargs = {"max_age_days": cookie_days}
    c.MappingKernelManager.cull_idle_timeout = 1800
    c.MappingKernelManager.cull_interval = 300
    c.ServerApp.shutdown_no_activity_timeout = 3600
    c.ServerApp.terminals_enabled = True  # admins only, by the authorizer
    # Notebook trust signatures are kept in memory, as the data dir is read-only: outputs of
    # notebooks saved before a container restart show as untrusted until they are run again.
    c.NotebookNotary.db_file = ":memory:"
    c.NotebookNotary.secret = os.urandom(32)
    for name in _SECRETS:
        os.environ.pop(name, None)
