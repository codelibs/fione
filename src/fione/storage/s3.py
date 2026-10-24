import io
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from fione.storage.base import validate_delete_prefix, validate_key, validate_prefix

_NOT_FOUND = {"404", "NoSuchKey", "NotFound"}
_DELETE_BATCH = 1000  # S3 DeleteObjects limit
_READ_BUFFER = 4 * 1024 * 1024


class S3Storage:
    """``Storage`` on an S3-compatible bucket (SeaweedFS, AWS S3, Ceph, ...).

    Uses path-style addressing. Streams are uploaded with boto3's managed transfer,
    which switches to multipart above 8 MiB. ``key_prefix`` namespaces every key inside
    the bucket (``s3://bucket/key_prefix``).

    The bucket must already exist: this class never creates one implicitly.
    ``ensure_bucket`` creates it idempotently, for one-time setup and tests only.
    """

    def __init__(
        self,
        bucket: str,
        key_prefix: str = "",
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.key_prefix = key_prefix.strip("/")
        self._prefix = f"{self.key_prefix}/" if self.key_prefix else ""
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(
                s3={"addressing_style": "path"},
                # Third-party S3 servers do not all accept the default CRC32 trailers.
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    def ensure_bucket(self) -> None:
        """Create the bucket if it does not exist yet (no-op when it already does)."""
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            if _code(e) not in _NOT_FOUND:
                raise
            self._client.create_bucket(Bucket=self.bucket)

    def _key(self, key: str) -> str:
        validate_key(key)
        return self._prefix + key

    def put(self, key: str, data: bytes | BinaryIO) -> None:
        full = self._key(key)
        if isinstance(data, bytes):
            self._client.put_object(Bucket=self.bucket, Key=full, Body=data)
        else:
            self._client.upload_fileobj(data, self.bucket, full)

    def open_read(self, key: str) -> BinaryIO:
        """Seekable file: ranged GETs behind a buffer, so Parquet-style readers can seek."""
        raw = _RangeReader(self._client, self.bucket, self._key(key), self.size(key))
        return io.BufferedReader(raw, buffer_size=_READ_BUFFER)

    def get(self, key: str) -> bytes:
        try:
            body = self._client.get_object(Bucket=self.bucket, Key=self._key(key))["Body"]
        except ClientError as e:
            raise _key_error(e, key) from None
        with body:
            return body.read()

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=self._key(key))
        except ClientError as e:
            if _code(e) in _NOT_FOUND:
                return False
            raise
        return True

    def size(self, key: str) -> int:
        try:
            head = self._client.head_object(Bucket=self.bucket, Key=self._key(key))
        except ClientError as e:
            raise _key_error(e, key) from None
        return head["ContentLength"]

    def list(self, prefix: str) -> list[str]:
        validate_prefix(prefix)
        paginator = self._client.get_paginator("list_objects_v2")
        keys = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self._prefix + prefix):
            keys.extend(obj["Key"].removeprefix(self._prefix) for obj in page.get("Contents", []))
        return sorted(keys)

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=self._key(key))

    def delete_prefix(self, prefix: str) -> None:
        validate_delete_prefix(prefix)
        keys = self.list(prefix)
        for i in range(0, len(keys), _DELETE_BATCH):
            objects = [{"Key": self._prefix + k} for k in keys[i : i + _DELETE_BATCH]]
            result = self._client.delete_objects(
                Bucket=self.bucket, Delete={"Objects": objects, "Quiet": True}
            )
            if result.get("Errors"):
                raise OSError(f"failed to delete objects: {result['Errors']}")


class _RangeReader(io.RawIOBase):
    """Read-only, seekable view of one object using ``GetObject`` with a ``Range`` header."""

    def __init__(self, client, bucket: str, key: str, size: int):
        self._client = client
        self._bucket = bucket
        self._key = key
        self._size = size
        self._pos = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self._size}.get(whence)
        if base is None:
            raise ValueError(f"invalid whence: {whence}")
        if base + offset < 0:
            raise ValueError("negative seek position")
        self._pos = base + offset
        return self._pos

    def _fetch(self, end: int) -> bytes:
        """Bytes from the current position up to and including ``end``."""
        resp = self._client.get_object(
            Bucket=self._bucket, Key=self._key, Range=f"bytes={self._pos}-{end}"
        )
        with resp["Body"] as body:
            data = body.read()
        self._pos += len(data)
        return data

    def readinto(self, b) -> int:
        want = min(len(b), self._size - self._pos)
        if want <= 0:
            return 0
        data = self._fetch(self._pos + want - 1)
        b[: len(data)] = data
        return len(data)

    def readall(self) -> bytes:
        if self._pos >= self._size:
            return b""
        return self._fetch(self._size - 1)


def _code(e: ClientError) -> str:
    return str(e.response.get("Error", {}).get("Code", ""))


def _key_error(e: ClientError, key: str) -> Exception:
    return KeyError(key) if _code(e) in _NOT_FOUND else e
