from typing import BinaryIO, Protocol

RESERVED_SEGMENT = ".tmp"


class Storage(Protocol):
    """Flat key -> bytes object store.

    Keys are ``/``-separated relative paths such as ``projects/1/data.csv``; see
    ``validate_key``. A missing key raises ``KeyError`` from ``get``, ``open_read``
    and ``size``; ``delete`` of a missing key is a no-op.

    ``open_read`` returns a seekable, buffered binary file (``seek``/``tell``/``read``) on
    every backend, so readers such as Parquet that seek to the footer work everywhere.
    The caller closes it.

    ``list`` takes a plain *string* prefix (``"a/s"`` matches ``"a/sub/1"``). ``delete_prefix``
    is stricter: the prefix must end with ``/`` so that ``projects/1/`` never deletes
    ``projects/10/...``.
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

    Rejected: empty keys, backslashes, NUL, any empty, ``.`` or ``..`` path segment
    (which covers a leading or trailing ``/`` and ``//``), and a first segment equal to
    ``.tmp`` in any letter case (reserved for in-flight local writes).
    """
    if not key:
        raise ValueError("storage key is empty")
    if "\\" in key or "\x00" in key:
        raise ValueError(f"invalid character in storage key: {key!r}")
    if any(seg in ("", ".", "..") for seg in key.split("/")):
        raise ValueError(f"invalid path segment in storage key: {key!r}")
    if key.split("/", 1)[0].lower() == RESERVED_SEGMENT:
        raise ValueError(f"{RESERVED_SEGMENT!r} is a reserved storage key segment: {key!r}")


def validate_prefix(prefix: str) -> None:
    """Like ``validate_key`` but allows the empty prefix and one trailing ``/``."""
    if prefix:
        validate_key(prefix.removesuffix("/"))


def validate_delete_prefix(prefix: str) -> None:
    """Like ``validate_prefix`` but the prefix must be a non-empty ``/``-terminated directory."""
    if not prefix.endswith("/"):
        raise ValueError(f"delete_prefix requires a prefix ending with '/': {prefix!r}")
    validate_prefix(prefix)
