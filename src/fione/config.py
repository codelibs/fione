import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    # REST API
    runner_enabled: bool = True
    cookie_secure: bool = False
    session_max_age_secs: int = 7 * 24 * 3600
    login_max_failures: int = 5
    login_window_secs: int = 15 * 60
    # Trust X-Forwarded-For/-Host: only behind a reverse proxy that sets them.
    trust_proxy: bool = False
    max_upload_bytes: int = 2**30
    # First-admin setup token; when unset, one is generated into <data_dir>/setup-token.
    setup_token: str | None = None

    @model_validator(mode="after")
    def _derive_defaults(self) -> "Settings":
        if not self.storage_url:
            self.storage_url = (self.data_dir / "objects").as_uri()
        if self.secret_key_path is None:
            self.secret_key_path = self.data_dir / "secret.key"
        return self


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
