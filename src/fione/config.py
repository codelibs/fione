import os
import re
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SETUP_TOKEN_LENGTH = 16
MIN_LAUNCHER_SECRET_LENGTH = 32  # as the launcher requires
_LAUNCHER_SECRET = re.compile(r"[\x21-\x7e]+")  # visible ASCII: it travels in an HTTP header
# scheme://host[:port] with dot-separated labels: what the launcher accepts as Fione's origin.
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_ORIGIN = re.compile(
    rf"(?P<scheme>https?)://(?P<host>{_LABEL}(?:\.{_LABEL})*)(?::(?P<port>[0-9]{{1,5}}))?"
)
_DEFAULT_PORTS = {"http": 80, "https": 443}
_NOTEBOOK_FIELDS = (
    "public_url",
    "notebook_url",
    "notebook_launcher_url",
    "notebook_launcher_secret",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FIONE_")

    data_dir: Path = Path("/data")
    # Defaults below are derived from data_dir when left unset.
    storage_url: str = ""
    secret_key_path: Path | None = None
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    max_concurrent_train_jobs: int = 1
    max_concurrent_short_jobs: int = 4
    image_tag: str = "dev"
    serving_image: str = "ghcr.io/codelibs/fione-serving"
    # Queue an explain job (importance and partial dependence) after each training.
    explain_after_training: bool = True
    # REST API
    runner_enabled: bool = True
    cookie_secure: bool = False
    session_max_age_secs: int = 7 * 24 * 3600
    login_max_failures: int = Field(5, ge=1)  # per (client address, username) and window
    login_window_secs: int = 15 * 60
    # Per client address and window, whatever the usernames. Users sharing an address (NAT, or
    # a proxy while trust_proxy is off) share this budget: one client's wrong attempts can
    # block login for all of them. Behind a reverse proxy, set trust_proxy.
    login_max_failures_per_ip: int = Field(50, ge=1)
    # Trust X-Forwarded-For/-Host (the last value, the one the nearest proxy added): only behind
    # a reverse proxy that sets them; otherwise clients could choose their own address.
    trust_proxy: bool = False
    max_upload_bytes: int = 2**30
    # First-admin setup token; when unset, one is generated into <data_dir>/setup-token.
    setup_token: str | None = None
    # Notebooks (off unless notebook_url is set): Fione's origin as browsers reach it (behind
    # a TLS proxy Fione cannot know its scheme), the notebook gateway's origin, and the
    # launcher that starts the per-user containers.
    public_url: str | None = None
    notebook_url: str | None = None
    notebook_launcher_url: str | None = None
    notebook_launcher_secret: str | None = None
    notebook_max_lifetime_secs: int = Field(43200, ge=600, le=604800)  # the launcher's bound

    @model_validator(mode="after")
    def _derive_defaults(self) -> "Settings":
        if not self.setup_token:
            self.setup_token = None
        elif len(self.setup_token) < MIN_SETUP_TOKEN_LENGTH:
            raise ValueError(
                f"FIONE_SETUP_TOKEN must be at least {MIN_SETUP_TOKEN_LENGTH} characters"
            )
        if not self.storage_url:
            self.storage_url = (self.data_dir / "objects").as_uri()
        if self.secret_key_path is None:
            self.secret_key_path = self.data_dir / "secret.key"
        self._check_notebooks()
        return self

    def _check_notebooks(self) -> None:
        """Empty values are unset; with ``notebook_url`` set, every notebook value is required,
        both origins are bare (kept in their normal form) and they differ."""
        for name in _NOTEBOOK_FIELDS:
            if not getattr(self, name):
                setattr(self, name, None)
        if self.notebook_url is None:
            return
        for name in _NOTEBOOK_FIELDS:
            if getattr(self, name) is None:
                raise ValueError(f"FIONE_{name.upper()} is required with FIONE_NOTEBOOK_URL")
        for name in ("public_url", "notebook_url"):
            setattr(self, name, _normal_origin(name, getattr(self, name)))
        if self.public_url == self.notebook_url:
            raise ValueError("FIONE_NOTEBOOK_URL must not be Fione's own origin")
        if not self.notebook_launcher_url.startswith(("http://", "https://")):
            raise ValueError("FIONE_NOTEBOOK_LAUNCHER_URL must be an http(s) URL")
        secret = self.notebook_launcher_secret
        if len(secret) < MIN_LAUNCHER_SECRET_LENGTH or not _LAUNCHER_SECRET.fullmatch(secret):
            raise ValueError(
                f"FIONE_NOTEBOOK_LAUNCHER_SECRET must be at least {MIN_LAUNCHER_SECRET_LENGTH}"
                " visible ASCII characters"
            )

    @property
    def notebooks_enabled(self) -> bool:
        return self.notebook_url is not None


def _normal_origin(name: str, value: str) -> str:
    """``value`` as browsers compare origins: the host in lower case, no default port."""
    match = _ORIGIN.fullmatch(value)
    if match is None or (match["port"] and int(match["port"]) > 65535):
        raise ValueError(f"FIONE_{name.upper()} must be scheme://host[:port], no path")
    scheme, host = match["scheme"], match["host"].lower()
    port = int(match["port"]) if match["port"] else _DEFAULT_PORTS[scheme]
    return f"{scheme}://{host}" + ("" if port == _DEFAULT_PORTS[scheme] else f":{port}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


SECRET_LENGTH = 32


def load_secret(settings: Settings) -> bytes:
    """Return the server secret, creating a random 32-byte key file (mode 0600) if missing.

    The key file is published atomically (see ``create_private_file``). An existing file of
    any other length is rejected, never regenerated.
    """
    path = settings.secret_key_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        _create_secret(path)
    data = path.read_bytes()
    if len(data) != SECRET_LENGTH:
        raise RuntimeError("secret key file is corrupt")
    return data


def _create_secret(path: Path) -> None:
    create_private_file(path, os.urandom(SECRET_LENGTH))


def create_private_file(path: Path, data: bytes) -> bool:
    """Publish ``data`` at ``path`` (mode 0600) unless the file exists; True if this call did.

    The data goes to a private temp file first and is published with ``os.link``, so the
    file is never visible empty or partial, even across processes or crashes.
    """
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            return False  # another process published first; its file is read by the caller
        return True
    finally:
        tmp.unlink(missing_ok=True)
