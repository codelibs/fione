import os
import secrets
import shutil
from pathlib import Path
from typing import BinaryIO

from fione.storage.base import (
    RESERVED_SEGMENT,
    validate_delete_prefix,
    validate_key,
    validate_prefix,
)


class LocalStorage:
    """``Storage`` on a local directory.

    Writes are atomic: temp file, fsync, ``os.replace``, directory fsync. Directories left
    empty by a delete are removed.

    A key and a prefix of another key cannot coexist here (``a`` and ``a/b``), because
    a path cannot be both a file and a directory; S3 allows it.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        validate_key(key)
        return self.root / key

    def put(self, key: str, data: bytes | BinaryIO) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_dir = self.root / RESERVED_SEGMENT
        tmp_dir.mkdir(exist_ok=True)
        tmp = tmp_dir / secrets.token_hex(16)
        # Mode 0o666 lets the process umask decide, so other uids on a shared volume can read.
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        try:
            with os.fdopen(fd, "wb") as f:
                if isinstance(data, bytes):
                    f.write(data)
                else:
                    shutil.copyfileobj(data, f)
                f.flush()
                os.fsync(f.fileno())
            try:
                os.replace(tmp, path)
            except FileNotFoundError:
                # A concurrent delete pruned the (then empty) parent directory.
                path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(tmp, path)
            _fsync_dir(path.parent)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    def open_read(self, key: str) -> BinaryIO:
        try:
            return open(self._path(key), "rb")
        except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
            raise KeyError(key) from None

    def get(self, key: str) -> bytes:
        with self.open_read(key) as f:
            return f.read()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def size(self, key: str) -> int:
        path = self._path(key)
        if not path.is_file():
            raise KeyError(key)
        return path.stat().st_size

    def list(self, prefix: str) -> list[str]:
        validate_prefix(prefix)
        # Only walk the directory the prefix points into, then filter by the full prefix.
        start = self.root / prefix.rpartition("/")[0]
        keys = []
        for dirpath, dirnames, filenames in os.walk(start):
            if Path(dirpath) == self.root:
                dirnames[:] = [d for d in dirnames if d != RESERVED_SEGMENT]
            for name in filenames:
                key = (Path(dirpath) / name).relative_to(self.root).as_posix()
                if key.startswith(prefix):
                    keys.append(key)
        return sorted(keys)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():  # a directory (a prefix of other keys) is not an object
            path.unlink(missing_ok=True)
            self._prune(path.parent)

    def delete_prefix(self, prefix: str) -> None:
        validate_delete_prefix(prefix)
        for key in self.list(prefix):
            self.delete(key)

    def _prune(self, directory: Path) -> None:
        """Remove now-empty directories up to, not including, the root."""
        while directory != self.root:
            try:
                directory.rmdir()
            except OSError:  # not empty (or already gone)
                return
            directory = directory.parent


def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
