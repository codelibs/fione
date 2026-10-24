from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from fione.storage.base import validate_key, validate_prefix

_NOT_FOUND = {"404", "NoSuchKey", "NotFound"}
_DELETE_BATCH = 1000  # S3 DeleteObjects limit


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
        try:
            return self._client.get_object(Bucket=self.bucket, Key=self._key(key))["Body"]
        except ClientError as e:
            raise _key_error(e, key) from None

    def get(self, key: str) -> bytes:
        with self.open_read(key) as f:
            return f.read()

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
        validate_prefix(prefix)
        if not prefix:
            raise ValueError("delete_prefix requires a non-empty prefix")
        keys = self.list(prefix)
        for i in range(0, len(keys), _DELETE_BATCH):
            objects = [{"Key": self._prefix + k} for k in keys[i : i + _DELETE_BATCH]]
            result = self._client.delete_objects(
                Bucket=self.bucket, Delete={"Objects": objects, "Quiet": True}
            )
            if result.get("Errors"):
                raise OSError(f"failed to delete objects: {result['Errors']}")


def _code(e: ClientError) -> str:
    return str(e.response.get("Error", {}).get("Code", ""))


def _key_error(e: ClientError, key: str) -> Exception:
    return KeyError(key) if _code(e) in _NOT_FOUND else e
