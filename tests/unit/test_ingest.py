import io
import itertools
import sqlite3

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from fione import db
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.projects import ingest, service
from fione.projects.ingest import IngestError
from fione.projects.service import DatasetType, ProjectNotFound
from fione.storage import LocalStorage

CSV = "id,name,score\n1,alice,1.5\n2,bob,2.5\n3,carol,\n"


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "fione.db")
    db.migrate(c)
    yield c
    c.close()


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "storage")


@pytest.fixture
def project(conn):
    owner = auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)
    return service.create_project(conn, owner, "demo")


def load(conn, storage, project, data: bytes, **kw):
    ds = ingest.ingest_csv(
        storage, conn, project.id, "data.csv", DatasetType.TRAIN, io.BytesIO(data), **kw
    )
    return ds, ingest.read_dataset(storage, ds)


def test_ingest_basic_roundtrip(conn, storage, project):
    ds, df = load(conn, storage, project, CSV.encode())
    assert ds.key == f"projects/{project.id}/datasets/{ds.id}/data.parquet"
    assert (ds.n_rows, ds.n_cols) == (3, 3) == df.shape
    assert ds.schema == [("id", "int64"), ("name", "string"), ("score", "double")]
    assert ds.type == DatasetType.TRAIN and ds.project_id == project.id and ds.name == "data.csv"
    assert list(df.columns) == ["id", "name", "score"]
    assert df["id"].tolist() == [1, 2, 3]
    assert df["score"].isna().tolist() == [False, False, True]
    assert storage.list("projects/") == [ds.key]
    assert service.get_dataset(conn, ds.id) == ds
    assert service.list_datasets(conn, project.id) == [ds]
    with storage.open_read(ds.key) as f:
        metadata = pq.ParquetFile(f).metadata
    assert metadata.num_rows == ds.n_rows and metadata.num_columns == ds.n_cols


def test_read_dataset_selects_columns(conn, storage, project):
    ds, _ = load(conn, storage, project, CSV.encode())
    df = ingest.read_dataset(storage, ds, ["score", "id"])
    assert list(df.columns) == ["score", "id"]


def test_utf8_bom_is_stripped(conn, storage, project):
    _, df = load(conn, storage, project, b"\xef\xbb\xbf" + CSV.encode())
    assert list(df.columns) == ["id", "name", "score"]


def test_cp932_japanese(conn, storage, project):
    text = "名前,売上\n田中,100\n佐藤,200\nヴィ,300\n"
    ds, df = load(conn, storage, project, text.encode("cp932"))
    assert list(df.columns) == ["名前", "売上"]
    assert df["名前"].tolist() == ["田中", "佐藤", "ヴィ"]
    assert ds.schema[1] == ("売上", "int64")


def test_euc_jp_japanese(conn, storage, project):
    text = "なまえ,てんすう\nたなか,10\nさとう,20\nすずき,30\n"
    _, df = load(conn, storage, project, text.encode("euc_jp"))
    assert list(df.columns) == ["なまえ", "てんすう"]
    assert df["なまえ"].tolist() == ["たなか", "さとう", "すずき"]


def test_multibyte_char_cut_at_sample_boundary(conn, storage, project, monkeypatch):
    monkeypatch.setattr(ingest, "_SAMPLE_SIZE", 8)
    # Every sample size 8 cuts "名前" (3-byte chars) and cp932 pairs mid-character.
    for enc in ("utf-8", "cp932"):
        text = "名前,売上\n" + "田中,1\n" * 20
        _, df = load(conn, storage, project, text.encode(enc))
        assert list(df.columns) == ["名前", "売上"]
        assert len(df) == 20


@pytest.mark.parametrize("delim", [";", "\t", "|"])
def test_delimiters_give_same_frame(conn, storage, project, delim):
    _, expected = load(conn, storage, project, CSV.encode())
    _, df = load(conn, storage, project, CSV.replace(",", delim).encode())
    pd.testing.assert_frame_equal(df, expected)


def test_quoted_delimiter_does_not_confuse_detection(conn, storage, project):
    data = 'a,b\n"x;y;z",1\n"p;q;r",2\n'
    _, df = load(conn, storage, project, data.encode())
    assert list(df.columns) == ["a", "b"]
    assert df["a"].tolist() == ["x;y;z", "p;q;r"]


def test_blank_and_duplicate_headers(conn, storage, project):
    _, df = load(conn, storage, project, b"a,,a,a, ,b\n1,2,3,4,5,6\n")
    assert list(df.columns) == ["a", "column_2", "a_2", "a_3", "column_5", "b"]


def test_header_only_and_empty(conn, storage, project):
    with pytest.raises(IngestError, match="no data rows"):
        load(conn, storage, project, b"a,b,c\n")
    with pytest.raises(IngestError, match="empty file"):
        load(conn, storage, project, b"")
    with pytest.raises(IngestError, match="empty file"):
        load(conn, storage, project, b"\xef\xbb\xbf \n")
    assert storage.list("") == []
    assert service.list_datasets(conn, project.id) == []


def test_mixed_int_str_column_is_string_even_in_later_block(conn, storage, project):
    rows = [f"{i},{i * 2}" for i in range(2000)] + ["x,5", "2001,6"]
    data = ("a,b\n" + "\n".join(rows) + "\n").encode()
    ds, df = load(conn, storage, project, data, block_size=4096)
    assert ds.schema == [("a", "string"), ("b", "int64")]
    assert len(df) == 2002
    assert df["a"].iloc[0] == "0" and df["a"].iloc[2000] == "x"
    assert df["b"].dtype.kind == "i"


def test_null_then_value_in_later_block_becomes_string(conn, storage, project):
    rows = ["," + str(i) for i in range(2000)] + ["hello,1"]
    data = ("a,b\n" + "\n".join(rows) + "\n").encode()
    ds, df = load(conn, storage, project, data, block_size=4096)
    assert ds.schema[0] == ("a", "string")
    assert df["a"].iloc[-1] == "hello"


def test_ragged_rows_raise_ingest_error(conn, storage, project):
    with pytest.raises(IngestError):
        load(conn, storage, project, b"a,b,c\n1,2,3\n4,5\n")
    assert storage.list("") == []
    assert service.list_datasets(conn, project.id) == []


def test_undecodable_sample_raises_ingest_error(conn, storage, project):
    with pytest.raises(IngestError, match="encoding"):
        load(conn, storage, project, b"a,b\n1,2\n" + b"\x81\x20,3\n")


def test_undecodable_bytes_after_sample_raise_ingest_error(conn, storage, project, monkeypatch):
    monkeypatch.setattr(ingest, "_SAMPLE_SIZE", 16)
    with pytest.raises(IngestError, match="UTF-8"):
        load(conn, storage, project, b"a,b\n" + b"1,2\n" * 20 + b"\x81\x20,3\n")
    assert storage.list("") == []


def test_too_large_leaves_nothing(conn, storage, project, tmp_path):
    tmp = tmp_path / "scratch"
    tmp.mkdir()
    data = b"a,b\n" + b"1,2\n" * 1000
    with pytest.raises(ValueError, match="too large"):
        load(conn, storage, project, data, max_bytes=1000, tmp_dir=tmp)
    assert storage.list("") == []
    assert conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == 0
    assert list(tmp.iterdir()) == []


def test_exactly_max_bytes_is_accepted(conn, storage, project):
    ds, _ = load(conn, storage, project, CSV.encode(), max_bytes=len(CSV))
    assert ds.n_rows == 3


def test_streaming_reads_in_chunks(conn, storage, project):
    class Chunky(io.RawIOBase):
        def __init__(self, data):
            self.buf = io.BytesIO(data)
            self.max_read = 0

        def readable(self):
            return True

        def readinto(self, b):
            self.max_read = max(self.max_read, len(b))
            return self.buf.readinto(b)

    stream = Chunky(CSV.encode() * 1)
    ingest.ingest_csv(storage, conn, project.id, "x", DatasetType.TRAIN, stream)
    assert stream.max_read <= 8 * 2**20


def test_tmp_dir_is_cleaned_after_success_and_failure(conn, storage, project, tmp_path):
    tmp = tmp_path / "scratch"
    tmp.mkdir()
    load(conn, storage, project, CSV.encode(), tmp_dir=tmp)
    with pytest.raises(IngestError):
        load(conn, storage, project, b"a,b,c\n1,2,3\n4,5\n", tmp_dir=tmp)
    assert list(tmp.iterdir()) == []


def test_insert_failure_removes_stored_object(conn, storage, project, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(service, "add_dataset", boom)
    with pytest.raises(RuntimeError):
        load(conn, storage, project, CSV.encode())
    assert storage.list("") == []


def test_project_deleted_during_ingest_removes_object(conn, storage, project, monkeypatch):
    real_put = storage.put

    def put_then_drop_project(key, data):
        real_put(key, data)
        conn.execute("DELETE FROM projects WHERE id = ?", (project.id,))

    monkeypatch.setattr(storage, "put", put_then_drop_project)
    with pytest.raises(sqlite3.IntegrityError):
        load(conn, storage, project, CSV.encode())
    assert storage.list("") == []


def test_missing_project(conn, storage):
    with pytest.raises(ProjectNotFound):
        ingest.ingest_csv(storage, conn, "nope", "x", DatasetType.TRAIN, io.BytesIO(CSV.encode()))
    assert storage.list("") == []


def test_dataset_ids_are_not_reused(conn, storage, project):
    a, _ = load(conn, storage, project, CSV.encode())
    service.delete_dataset(conn, storage, a.id)
    b, _ = load(conn, storage, project, CSV.encode())
    assert b.id != a.id
    assert not storage.exists(a.key)


def test_export_csv_reingests_to_same_frame(conn, storage, project):
    text = '名前,売上,備考\n田中,1.5,"a,b"\n佐藤,,"line\nbreak"\n鈴木,3.5,x\n'
    ds, df = load(conn, storage, project, text.encode("cp932"))
    chunks = list(ingest.export_csv(storage, ds))
    out = b"".join(chunks)
    assert out.decode("utf-8").splitlines()[0].replace('"', "") == "名前,売上,備考"
    ds2, df2 = load(conn, storage, project, out)
    pd.testing.assert_frame_equal(df, df2)
    assert ds2.schema == ds.schema


def test_export_csv_is_streamed_in_batches(conn, storage, project, monkeypatch):
    monkeypatch.setattr(ingest, "_EXPORT_BATCH_ROWS", 100)
    data = "a,b\n" + "".join(f"{i},{i}\n" for i in range(450))
    ds, df = load(conn, storage, project, data.encode())
    chunks = list(itertools.islice(ingest.export_csv(storage, ds), 100))
    assert len(chunks) == 5
    _, df2 = load(conn, storage, project, b"".join(chunks))
    pd.testing.assert_frame_equal(df, df2)


def test_invalid_utf8_in_later_block_raises_ingest_error(conn, storage, project):
    data = b"a,b\n" + b"abc,2\n" * 2000 + b"\x81\x20,3\n"
    with pytest.raises(IngestError):
        load(conn, storage, project, data, block_size=4096)
    assert storage.list("") == []


def test_int_then_float_in_later_block_is_double(conn, storage, project):
    rows = [f"{i},{i}" for i in range(3000)] + ["1.5,x", "2.5,y"]
    data = ("a,b\n" + "\n".join(rows) + "\n").encode()
    ds, df = load(conn, storage, project, data, block_size=4096)
    assert ds.schema == [("a", "double"), ("b", "string")]
    assert df["a"].dtype.kind == "f"
    assert df["a"].iloc[0] == 0.0 and df["a"].iloc[3000] == 1.5 and df["a"].iloc[3001] == 2.5


def test_int_float_and_int_text_columns_in_one_file(conn, storage, project):
    rows = [f"{i},{i},{i}" for i in range(3000)] + ["1.5,x,7"]
    data = ("f,t,i\n" + "\n".join(rows) + "\n").encode()
    ds, df = load(conn, storage, project, data, block_size=4096)
    assert ds.schema == [("f", "double"), ("t", "string"), ("i", "int64")]
    assert df["f"].iloc[-1] == 1.5 and df["t"].iloc[-1] == "x" and df["t"].iloc[0] == "0"
    with storage.open_read(ds.key) as f:
        parquet_schema = pq.ParquetFile(f).schema_arrow
    assert [(f.name, str(f.type)) for f in parquet_schema] == ds.schema


def test_int_then_float_and_text_is_string(conn, storage, project):
    rows = [str(i) for i in range(3000)] + ["1.5", "abc"]
    ds, df = load(
        conn, storage, project, ("a\n" + "\n".join(rows) + "\n").encode(), block_size=4096
    )
    assert ds.schema == [("a", "string")]
    assert df["a"].iloc[3000] == "1.5" and df["a"].iloc[3001] == "abc"


def _int_then_float(conn, storage, project, values):
    rows = [str(v) for v in values] + ["1.5"]
    return load(conn, storage, project, ("a\n" + "\n".join(rows) + "\n").encode(), block_size=4096)


def test_big_ints_then_float_stay_exact_strings(conn, storage, project):
    ds, df = _int_then_float(conn, storage, project, [9007199254740993] * 3000)
    assert ds.schema == [("a", "string")]
    assert df["a"].iloc[0] == "9007199254740993" and df["a"].iloc[-1] == "1.5"


def test_distinct_64bit_ids_then_float_are_preserved(conn, storage, project):
    ids = [2**62 + i for i in range(3000)]
    ds, df = _int_then_float(conn, storage, project, ids)
    assert ds.schema == [("a", "string")]
    assert df["a"].iloc[:3000].tolist() == [str(i) for i in ids]


def test_big_int_only_in_early_block_still_blocks_widening(conn, storage, project):
    ds, df = _int_then_float(conn, storage, project, [2**60] + list(range(3000)))
    assert ds.schema == [("a", "string")]
    assert df["a"].iloc[0] == str(2**60)


def test_ints_at_float_limit_then_float_are_double(conn, storage, project):
    ds, df = _int_then_float(conn, storage, project, [2**53, -(2**53)] + [5] * 3000)
    assert ds.schema == [("a", "double")]
    assert df["a"].iloc[0] == 2.0**53 and df["a"].iloc[1] == -(2.0**53) and df["a"].iloc[-1] == 1.5


# --- ingest_batches: a dataset made from frames ---------------------------------


def _frames():
    yield pd.DataFrame({"a": [1, 2], "b": ["x", "ä"], "c": [0.5, None]})
    yield pd.DataFrame({"a": [3], "b": ["日本"], "c": [1.5]})


def store_batches(conn, storage, project, batches, **kw):
    return ingest.ingest_batches(
        storage, conn, project.id, "pred", DatasetType.PREDICT, batches, **kw
    )


def test_ingest_batches_records_the_dataset_and_reads_back(conn, storage, project):
    ds = store_batches(conn, storage, project, _frames())
    assert (ds.type, ds.name, ds.n_rows, ds.n_cols) == (DatasetType.PREDICT, "pred", 3, 3)
    assert ds.schema == [("a", "int64"), ("b", "string"), ("c", "double")]
    assert ds.key == f"projects/{project.id}/datasets/{ds.id}/data.parquet"
    assert service.get_dataset(conn, ds.id) == ds
    expected = pd.concat(_frames(), ignore_index=True)
    pd.testing.assert_frame_equal(ingest.read_dataset(storage, ds), expected)


def test_ingest_batches_types_a_column_missing_in_the_first_frame_from_the_fallback(
    conn, storage, project
):
    first = pd.DataFrame({"a": [None, None], "b": [1, 2]}, dtype=object).astype({"b": "int64"})
    batches = [first, pd.DataFrame({"a": ["x", "y"], "b": [3, 4]})]
    types = {"a": pa.string(), "b": pa.int32()}
    ds = store_batches(conn, storage, project, batches, fallback_types=types)
    assert ds.schema == [("a", "string"), ("b", "int64")]
    values = ingest.read_dataset(storage, ds)["a"]
    assert values.isna().tolist() == [True, True, False, False]
    assert values.iloc[2:].tolist() == ["x", "y"]


def test_ingest_batches_refuses_no_rows(conn, storage, project):
    with pytest.raises(IngestError, match="no data rows"):
        store_batches(conn, storage, project, [pd.DataFrame({"a": []})])
    with pytest.raises(IngestError, match="no data rows"):
        store_batches(conn, storage, project, [])
    assert storage.list("") == [] and service.list_datasets(conn, project.id) == []


def test_ingest_batches_leaves_nothing_when_the_batches_fail(conn, storage, project, tmp_path):
    tmp = tmp_path / "scratch"
    tmp.mkdir()

    def broken():
        yield pd.DataFrame({"a": [1]})
        raise RuntimeError("source failed")

    with pytest.raises(RuntimeError, match="source failed"):
        store_batches(conn, storage, project, broken(), tmp_dir=tmp)
    assert storage.list("") == [] and list(tmp.iterdir()) == []
    assert service.list_datasets(conn, project.id) == []


def test_ingest_batches_removes_the_object_when_the_insert_fails(
    conn, storage, project, monkeypatch, tmp_path
):
    tmp = tmp_path / "scratch"
    tmp.mkdir()

    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(service, "add_dataset", boom)
    with pytest.raises(RuntimeError, match="db down"):
        store_batches(conn, storage, project, _frames(), tmp_dir=tmp)
    assert storage.list("") == [] and list(tmp.iterdir()) == []


def test_a_failing_cleanup_never_masks_the_insert_error(conn, storage, project, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")

    def cannot_delete(key):
        raise OSError("storage down")

    monkeypatch.setattr(service, "add_dataset", boom)
    monkeypatch.setattr(storage, "delete", cannot_delete)
    with pytest.raises(RuntimeError, match="db down"):
        store_batches(conn, storage, project, _frames())


def test_ingest_batches_missing_project(conn, storage):
    with pytest.raises(ProjectNotFound):
        ingest.ingest_batches(storage, conn, "nope", "x", DatasetType.PREDICT, _frames())
    assert storage.list("") == []


def test_tmp_dir_is_cleaned_after_ingest_batches(conn, storage, project, tmp_path):
    tmp = tmp_path / "scratch"
    tmp.mkdir()
    store_batches(conn, storage, project, _frames(), tmp_dir=tmp)
    assert list(tmp.iterdir()) == []


def test_read_dataset_keeps_integers_and_booleans_exact_only_on_request(conn, storage, project):
    frame = pd.DataFrame(
        {
            "id": pd.array([2**60 + 1, None], dtype="Int64"),
            "ok": pd.array([True, None], dtype="boolean"),
        }
    )
    ds = store_batches(conn, storage, project, [frame])
    plain = ingest.read_dataset(storage, ds)
    assert plain["id"].dtype == "float64" and plain["ok"].dtype == object
    exact = ingest.read_dataset(storage, ds, nullable_dtypes=True)
    assert exact["id"].dtype == "Int64" and exact["id"].tolist()[0] == 2**60 + 1
    assert exact["ok"].dtype == "boolean"


def test_read_dataset_rows_reads_a_page_from_the_row_groups_that_hold_it(
    conn, storage, project, monkeypatch
):
    monkeypatch.setattr(ingest, "_ROW_GROUP_ROWS", 100)  # several row groups
    data = "n,s\n" + "".join(f"{i},v{i}\n" for i in range(350))
    dataset, _ = load(conn, storage, project, data.encode(), block_size=256)
    with storage.open_read(dataset.key) as f:
        assert pq.ParquetFile(f).metadata.num_row_groups == 4
    page = ingest.read_dataset_rows(storage, dataset, 95, 10)
    assert page["n"].tolist() == list(range(95, 105))  # across a row-group boundary
    assert ingest.read_dataset_rows(storage, dataset, 345, 10)["n"].tolist() == list(
        range(345, 350)
    )
    assert ingest.read_dataset_rows(storage, dataset, 0, 3, ["s"]).columns.tolist() == ["s"]
    past = ingest.read_dataset_rows(storage, dataset, 400, 10)
    assert past.empty and past.columns.tolist() == ["n", "s"]
