import os
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
    image_tag: str = "dev"

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


def load_secret(settings: Settings) -> bytes:
    """Return the server secret, creating a random 32-byte key file (mode 0600) if missing."""
    path = settings.secret_key_path
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        return load_secret(settings)
    except FileExistsError:
        return path.read_bytes()
    with os.fdopen(fd, "wb") as f:
        key = os.urandom(32)
        f.write(key)
    return key
