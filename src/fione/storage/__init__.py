from pathlib import Path
from urllib.parse import unquote, urlparse

from fione.config import Settings
from fione.storage.base import Storage
from fione.storage.local import LocalStorage
from fione.storage.s3 import S3Storage

__all__ = ["LocalStorage", "S3Storage", "Storage", "open_storage"]


def open_storage(settings: Settings) -> Storage:
    """Pick the backend from the ``storage_url`` scheme.

    ``file:///abs/dir`` -> ``LocalStorage``. ``s3://bucket[/key/prefix]`` -> ``S3Storage``
    using the endpoint, credentials and region from ``settings``; the bucket must
    already exist (see ``S3Storage.ensure_bucket``).
    """
    url = urlparse(settings.storage_url)
    if url.scheme == "file":
        if url.netloc:
            raise ValueError(
                f"file storage_url must be file:///absolute/path: {settings.storage_url}"
            )
        return LocalStorage(Path(unquote(url.path)))
    if url.scheme == "s3":
        if not url.netloc:
            raise ValueError(f"s3 storage_url needs a bucket: {settings.storage_url}")
        return S3Storage(
            bucket=url.netloc,
            key_prefix=unquote(url.path),
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
        )
    raise ValueError(f"unsupported storage_url: {settings.storage_url}")
