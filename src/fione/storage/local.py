import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO

from fione.storage.base import validate_key, validate_prefix

# Top-level directory under the root that holds in-flight writes. Keys may not use it.
_TMP_DIR = ".tmp"


class LocalStorage:
    """``Storage`` on a local directory. Writes are atomic: temp file, fsync, ``os.replace``.

    A key and a prefix of another key cannot coexist here (``a`` and ``a/b``), because
    a path cannot be both a file and a directory; S3 allows it.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        validate_key(key)
        if key.split("/", 1)[0] == _TMP_DIR:
            raise ValueError(f"{_TMP_DIR!r} is a reserved storage key segment: {key!r}")
        return self.root / key

    def put(self, key: str, data: bytes | BinaryIO) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_dir = self.root / _TMP_DIR
        tmp_dir.mkdir(exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=tmp_dir)
        try:
            with os.fdopen(fd, "wb") as f:
                if isinstance(data, bytes):
                    f.write(data)
                else:
                    shutil.copyfileobj(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
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
                dirnames[:] = [d for d in dirnames if d != _TMP_DIR]
            for name in filenames:
                key = (Path(dirpath) / name).relative_to(self.root).as_posix()
                if key.startswith(prefix):
                    keys.append(key)
        return sorted(keys)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():  # a directory (a prefix of other keys) is not an object
            path.unlink(missing_ok=True)

    def delete_prefix(self, prefix: str) -> None:
        validate_prefix(prefix)
        if not prefix:
            raise ValueError("delete_prefix requires a non-empty prefix")
        for key in self.list(prefix):
            self.delete(key)
