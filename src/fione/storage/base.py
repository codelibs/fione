from typing import BinaryIO, Protocol


class Storage(Protocol):
    """Flat key -> bytes object store.

    Keys are ``/``-separated relative paths such as ``projects/1/data.csv``; see
    ``validate_key``. A missing key raises ``KeyError`` from ``get``, ``open_read``
    and ``size``; ``delete`` of a missing key is a no-op. ``list`` and
    ``delete_prefix`` take a plain *string* prefix (``"a/s"`` matches ``"a/sub/1"``), so
    pass a trailing ``/`` to match whole path segments.
    """

    def put(self, key: str, data: bytes | BinaryIO) -> None: ...

    def get(self, key: str) -> bytes: ...

    def open_read(self, key: str) -> BinaryIO: ...

    def exists(self, key: str) -> bool: ...

    def list(self, prefix: str) -> list[str]: ...

    def delete(self, key: str) -> None: ...

    def delete_prefix(self, prefix: str) -> None: ...

    def size(self, key: str) -> int: ...


def validate_key(key: str) -> None:
    """Raise ``ValueError`` unless ``key`` is a safe relative path.

    Rejected: empty keys, backslashes, NUL, and any empty, ``.`` or ``..`` path segment
    (which covers a leading or trailing ``/`` and ``//``).
    """
    if not key:
        raise ValueError("storage key is empty")
    if "\\" in key or "\x00" in key:
        raise ValueError(f"invalid character in storage key: {key!r}")
    if any(seg in ("", ".", "..") for seg in key.split("/")):
        raise ValueError(f"invalid path segment in storage key: {key!r}")


def validate_prefix(prefix: str) -> None:
    """Like ``validate_key`` but allows the empty prefix and one trailing ``/``."""
    if prefix:
        validate_key(prefix.removesuffix("/"))
