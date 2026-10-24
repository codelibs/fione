import io
import os
import uuid

import pytest

from fione.config import Settings
from fione.storage import LocalStorage, S3Storage, open_storage

S3_ENV = "FIONE_TEST_S3_ENDPOINT"


def _s3_storage() -> S3Storage:
    if not os.environ.get(S3_ENV):
        pytest.skip(f"{S3_ENV} is not set")
    # A unique key prefix isolates each test inside the shared test bucket.
    storage = S3Storage(
        bucket=os.environ["FIONE_TEST_S3_BUCKET"],
        key_prefix=f"fione-test-{uuid.uuid4().hex}",
        endpoint=os.environ[S3_ENV],
        access_key=os.environ["FIONE_TEST_S3_ACCESS_KEY"],
        secret_key=os.environ["FIONE_TEST_S3_SECRET_KEY"],
    )
    storage.ensure_bucket()
    return storage


@pytest.fixture(params=["local", pytest.param("s3", marks=pytest.mark.s3)])
def storage(request, tmp_path):
    if request.param == "local":
        yield LocalStorage(tmp_path / "objects")
        return
    s = _s3_storage()
    yield s
    # key_prefix is unique to this test, so this only removes its own objects.
    for key in s.list(""):
        s.delete(key)


def test_put_get_round_trip(storage):
    storage.put("a/b.txt", b"hello")
    assert storage.get("a/b.txt") == b"hello"


def test_put_overwrites(storage):
    storage.put("k", b"one")
    storage.put("k", b"two")
    assert storage.get("k") == b"two"


def test_put_stream(storage):
    storage.put("s", io.BytesIO(b"streamed"))
    assert storage.get("s") == b"streamed"


def test_put_large_stream_multipart(storage):
    data = os.urandom(1024) * (20 * 1024)  # 20 MiB, above boto3's multipart threshold
    storage.put("big", io.BytesIO(data))
    assert storage.size("big") == len(data)
    assert storage.get("big") == data


def test_open_read(storage):
    storage.put("o", b"abcdef")
    with storage.open_read("o") as f:
        assert f.read(3) == b"abc"
        assert f.read() == b"def"


def test_exists_and_size(storage):
    storage.put("x/y", b"12345")
    assert storage.exists("x/y")
    assert not storage.exists("x/z")
    assert not storage.exists("x")
    assert storage.size("x/y") == 5


def test_list_returns_only_keys_under_prefix_sorted(storage):
    for key in ("a/2", "a/1", "a/sub/3", "ab/4", "b/5"):
        storage.put(key, b"")
    assert storage.list("a/") == ["a/1", "a/2", "a/sub/3"]
    assert storage.list("a/s") == ["a/sub/3"]  # plain string prefix
    assert storage.list("") == ["a/1", "a/2", "a/sub/3", "ab/4", "b/5"]
    assert storage.list("zzz/") == []


def test_delete(storage):
    storage.put("d", b"x")
    storage.delete("d")
    assert not storage.exists("d")


def test_delete_missing_is_noop(storage):
    storage.delete("never/existed")


def test_delete_prefix_removes_nested_keys_only(storage):
    for key in ("p/1", "p/q/2", "p/q/r/3", "pp/4", "other"):
        storage.put(key, b"")
    storage.delete_prefix("p/")
    assert storage.list("") == ["other", "pp/4"]


def test_delete_prefix_rejects_empty_prefix(storage):
    storage.put("keep", b"x")
    with pytest.raises(ValueError):
        storage.delete_prefix("")
    assert storage.exists("keep")


def test_missing_key_raises_key_error(storage):
    with pytest.raises(KeyError):
        storage.get("nope")
    with pytest.raises(KeyError):
        storage.open_read("nope")
    with pytest.raises(KeyError):
        storage.size("nope")


BAD_KEYS = ["", "/abs", "../x", "a/../b", "a/..", "a//b", "a/", "./a", "a/./b", "a\\b", "a\x00b"]


@pytest.mark.parametrize("key", BAD_KEYS)
def test_invalid_keys_rejected(storage, key):
    with pytest.raises(ValueError):
        storage.put(key, b"x")
    with pytest.raises(ValueError):
        storage.get(key)
    with pytest.raises(ValueError):
        storage.open_read(key)
    with pytest.raises(ValueError):
        storage.exists(key)
    with pytest.raises(ValueError):
        storage.size(key)
    with pytest.raises(ValueError):
        storage.delete(key)


@pytest.mark.parametrize("prefix", ["/abs", "../x", "a/../b", "a//", "a\\b", "a\x00"])
def test_invalid_prefixes_rejected(storage, prefix):
    with pytest.raises(ValueError):
        storage.list(prefix)
    with pytest.raises(ValueError):
        storage.delete_prefix(prefix)


# -- local backend specifics ---------------------------------------------------


class _FailingStream(io.RawIOBase):
    def __init__(self):
        self._sent = False

    def readable(self):
        return True

    def readinto(self, b):
        if self._sent:
            raise OSError("boom")
        self._sent = True
        b[:4] = b"part"
        return 4


def test_local_failed_put_leaves_no_partial_object(tmp_path):
    s = LocalStorage(tmp_path / "objects")
    s.put("k", b"old")
    with pytest.raises(OSError):
        s.put("k", _FailingStream())
    with pytest.raises(OSError):
        s.put("new", _FailingStream())
    assert s.get("k") == b"old"
    assert s.list("") == ["k"]
    assert not any((tmp_path / "objects" / ".tmp").iterdir())


def test_local_reserved_tmp_segment_rejected(tmp_path):
    s = LocalStorage(tmp_path / "objects")
    with pytest.raises(ValueError):
        s.put(".tmp/x", b"x")


def test_local_stays_under_root(tmp_path):
    s = LocalStorage(tmp_path / "objects")
    s.put("a", b"x")
    assert (tmp_path / "objects" / "a").read_bytes() == b"x"
    assert not (tmp_path / "a").exists()


def test_local_get_on_directory_key_raises_key_error(tmp_path):
    s = LocalStorage(tmp_path / "objects")
    s.put("dir/file", b"x")
    with pytest.raises(KeyError):
        s.get("dir")
    with pytest.raises(KeyError):
        s.get("dir/file/deeper")


def test_local_delete_on_directory_key_is_noop(tmp_path):
    s = LocalStorage(tmp_path / "objects")
    s.put("dir/file", b"x")
    s.delete("dir")
    assert s.get("dir/file") == b"x"


# -- open_storage ----------------------------------------------------------------


def test_open_storage_file_url(tmp_path):
    s = open_storage(Settings(data_dir=tmp_path, storage_url=(tmp_path / "o").as_uri()))
    assert isinstance(s, LocalStorage)
    s.put("k", b"v")
    assert (tmp_path / "o" / "k").read_bytes() == b"v"


def test_open_storage_default_url_is_under_data_dir(tmp_path):
    s = open_storage(Settings(data_dir=tmp_path))
    assert isinstance(s, LocalStorage)
    s.put("k", b"v")
    assert (tmp_path / "objects" / "k").read_bytes() == b"v"


def test_open_storage_s3_url(tmp_path):
    s = open_storage(
        Settings(
            data_dir=tmp_path,
            storage_url="s3://my-bucket/some/prefix",
            s3_endpoint="http://localhost:1",
            s3_access_key="k",
            s3_secret_key="s",
        )
    )
    assert isinstance(s, S3Storage)
    assert s.bucket == "my-bucket"
    assert s.key_prefix == "some/prefix"


@pytest.mark.parametrize(
    "url", ["ftp://host/x", "/plain/path", "file://host/x", "s3://", "s3:///prefix-only"]
)
def test_open_storage_rejects_bad_urls(tmp_path, url):
    with pytest.raises(ValueError):
        open_storage(Settings(data_dir=tmp_path, storage_url=url))
