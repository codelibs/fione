import io
import itertools
import json
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


def test_a_western_file_that_no_other_encoding_reads_is_read_as_windows_1252(
    conn, storage, project
):
    text = "city,note\nZürich,café crème\nSão Paulo,“quoted” – 5 €\nKraków,naïve\n"
    _, df = load(conn, storage, project, text.encode("cp1252"))
    assert df["city"].tolist() == ["Zürich", "São Paulo", "Kraków"]
    assert df["note"].tolist() == ["café crème", "“quoted” – 5 €", "naïve"]


def test_a_binary_file_is_not_taken_for_windows_1252(conn, storage, project):
    # the bytes no other encoding reads (0x80), but with the control characters of a binary file
    metadata = b"\x00\x05\x16\x07\x00\x02\x00\x00Mac OS X        \x00\x02\x80\xe9\x00"
    with pytest.raises(IngestError, match="encoding"):
        load(conn, storage, project, metadata * 10)


def test_a_japanese_file_is_still_read_as_japanese(conn, storage, project):
    # cp1252 reads these bytes too: it is the last choice, after Shift_JIS and EUC-JP
    for encoding in ("cp932", "euc_jp"):
        _, df = load(conn, storage, project, "名前,値\n山田,1\n".encode(encoding))
        assert df["名前"].tolist() == ["山田"]


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


def _texts_of_several_lines(rows: int) -> bytes:
    return b"id,text,score\n" + b"".join(
        b'%d,"line one of %d\nline two, with a comma\r\nline three",%d\n' % (i, i, i % 7)
        for i in range(rows)
    )


def test_cells_with_line_breaks_are_read_over_many_blocks(conn, storage, project):
    ds, df = load(conn, storage, project, _texts_of_several_lines(2_000), block_size=4096)
    assert ds.n_rows == 2_000 and list(df.columns) == ["id", "text", "score"]
    assert df["text"][1_999] == "line one of 1999\nline two, with a comma\r\nline three"
    assert df["score"].tolist() == [i % 7 for i in range(2_000)]


def test_a_first_line_break_past_the_sample_is_read_too(conn, storage, project, monkeypatch):
    plain = b"".join(b'%d,"one line",%d\n' % (i, i % 7) for i in range(2_000))
    data = b"id,text,score\n" + plain + _texts_of_several_lines(2_000).split(b"\n", 1)[1]
    monkeypatch.setattr(ingest, "_SAMPLE_SIZE", 4096)  # the sample holds plain rows only
    ds, df = load(conn, storage, project, data, block_size=4096)
    assert ds.n_rows == 4_000 and df["text"][3_999].endswith("line three")


def test_a_file_without_line_breaks_in_cells_is_read_the_fast_way(
    conn, storage, project, monkeypatch
):
    asked = []
    real = ingest._open_csv
    monkeypatch.setattr(ingest, "_open_csv", lambda *a: asked.append(a[-1]) or real(*a))
    load(conn, storage, project, b'id,text\n1,"a, b"\n2,c\n')
    assert asked and not any(asked)


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
    monkeypatch.setattr(ingest, "_PAGE_BATCH_ROWS", 7)  # pages across read batches too
    assert ingest.read_dataset_rows(storage, dataset, 95, 10)["n"].tolist() == list(range(95, 105))
    assert ingest.read_dataset_rows(storage, dataset, 0, 30)["n"].tolist() == list(range(30))
    assert ingest.read_dataset_rows(storage, dataset, 343, 10)["s"].tolist() == [
        f"v{i}" for i in range(343, 350)
    ]


def test_numbers_with_thousands_separators_are_numbers(conn, storage, project):
    data = (
        'a,b,c,d,e,f\n"1,234","1,234.5","0,123","1,23","12,345",x\n'
        '"16,853",7,"0,456","1,234","1,234,567",y\n,"2,000.25","0,789","5,000",,z\n'
    )
    ds, df = load(conn, storage, project, data.encode())
    assert dict(ds.schema) == {
        "a": "int64",
        "b": "double",
        "c": "string",
        "d": "string",
        "e": "int64",
        "f": "string",
    }
    assert df["a"].tolist()[:2] == [1234, 16853] and df["a"].isna().tolist() == [False, False, True]
    assert df["b"].tolist() == [1234.5, 7.0, 2000.25]
    assert df["e"].tolist()[:2] == [12345, 1234567]
    assert df["c"].tolist() == ["0,123", "0,456", "0,789"]  # a decimal comma stays text


def test_thousands_separators_are_read_only_in_a_comma_delimited_file(conn, storage, project):
    ds, df = load(conn, storage, project, b'a;b\n"12,500";1\n"3,750";2\n')
    assert dict(ds.schema)["a"] == "string" and df["a"].tolist() == ["12,500", "3,750"]


def test_thousands_separated_whole_numbers_beyond_int64_stay_text(conn, storage, project):
    ds, df = load(conn, storage, project, b'a\n"99,999,999,999,999,999,999"\n"1,000"\n')
    assert dict(ds.schema)["a"] == "string"


@pytest.mark.parametrize(
    ("values", "dtype", "numbers"),
    [
        (['"-1,234"', '"1,234.50"', '"2,000"'], "double", [-1234.0, 1234.5, 2000.0]),
        (['"+2,000"', '"1,000"'], "string", None),  # a plus sign is not read
        (['"1,200"', "950", "NA"], "int64", [1200, 950, None]),  # one separator is enough
        (['"1,200"', "NA", '"3,000"'], "int64", [1200, None, 3000]),
        (['"1,234"', "7", '"0.5"'], "double", [1234.0, 7.0, 0.5]),
        (['"123,456"', '"234,567"'], "int64", [123456, 234567]),  # an identifier reads as a number
        (['"(1,234)"', '"1,000"'], "string", None),
        (['"$1,234"', '"1,000"'], "string", None),
        (['"1,234 "', '"1,000"'], "int64", [1234, 1000]),  # blanks around a number are trimmed
        (['"12,34"', '"1,000"'], "string", None),
        (['"1,23,456"', '"1,000"'], "string", None),  # Indian grouping
        (['"1,2"', '"1,5"'], "string", None),  # a decimal comma
        (['"1,5"', '"1,000"'], "string", None),
        (['"0,123"', '"1,000"'], "string", None),
        (['"007"', '"1,000"'], "string", None),  # a code with a leading zero
        (['"1,000,00"', '"1,000"'], "string", None),
        (["950", "1200"], "int64", [950, 1200]),  # plain numbers were numbers already
    ],
)
def test_thousands_separator_cases(conn, storage, project, values, dtype, numbers):
    data = "a\n" + "\n".join(values) + "\n"
    ds, df = load(conn, storage, project, data.encode())
    assert dict(ds.schema)["a"] == dtype
    if numbers is not None:
        assert [None if pd.isna(v) else v for v in df["a"].tolist()] == numbers
    else:
        assert df["a"].tolist() == [v.strip('"') if v else None for v in values]


@pytest.mark.parametrize("delimiter", [b"\t", b"|"])
def test_thousands_separators_stay_text_in_other_delimited_files(conn, storage, project, delimiter):
    data = (
        b"a"
        + delimiter
        + b"b\n"
        + b'"12,500"'
        + delimiter
        + b"1\n"
        + b'"3,750"'
        + delimiter
        + b"2\n"
    )
    ds, _ = load(conn, storage, project, data)
    assert dict(ds.schema)["a"] == "string"


def test_thousands_separated_numbers_in_a_frame_batch_are_untouched(conn, storage, project):
    ds = ingest.ingest_batches(
        storage,
        conn,
        project.id,
        "frame",
        DatasetType.TRAIN,
        [pd.DataFrame({"a": ["1,234", "5,000"]})],
    )
    assert dict(ds.schema)["a"] == "string"


def test_thousands_separators_are_found_across_batches(conn, storage, project, monkeypatch):
    monkeypatch.setattr(ingest, "_ROW_GROUP_ROWS", 3)
    rows = [
        ("1", "5", "9", "NA"),
        ("2", "6", "8", "NA"),
        ("3", "7", "7", "NA"),
        ("4", "8", "6", "NA"),
        ("5", "9", "5", "1"),
        ("6", "10", "4", "NA"),
        ("7", "11", "3", "NA"),
        ("8", "12", "2", "2"),
        ("9", "13", "1", "NA"),
        ('"1,000"', '"99,999,999,999,999,999,999"', '"1,200"', '"4,500"'),
    ]
    data = "a,b,c,d\n" + "\n".join(",".join(r) for r in rows) + "\n"
    ds, df = load(conn, storage, project, data.encode())
    assert dict(ds.schema) == {"a": "int64", "b": "string", "c": "int64", "d": "int64"}
    assert df["a"].tolist() == [1, 2, 3, 4, 5, 6, 7, 8, 9, 1000]  # a separator in the last batch
    assert df["c"].tolist() == [9, 8, 7, 6, 5, 4, 3, 2, 1, 1200]
    assert df["b"].iloc[-1] == "99,999,999,999,999,999,999"  # an overflow in the last batch
    assert df["d"].isna().sum() == 7 and df["d"].iloc[-1] == 4500  # nulls kept


def test_thousands_separated_column_with_empty_cells(conn, storage, project):
    ds, df = load(conn, storage, project, b'a,b\n"1,200",1\n,2\n950,3\n"",4\n')
    assert dict(ds.schema)["a"] == "int64"
    assert [None if pd.isna(v) else v for v in df["a"].tolist()] == [1200, None, 950, None]


def test_a_wide_table_is_written_in_row_groups_of_fewer_rows(conn, storage, project, monkeypatch):
    # a group holds up to _ROW_GROUP_CELLS cells, so a table of many columns is cut sooner
    monkeypatch.setattr(ingest, "_ROW_GROUP_CELLS", 4 * 1500)
    monkeypatch.setattr(ingest, "_MIN_GROUP_ROWS", 100)
    frame = pd.DataFrame({f"c{i}": range(6000) for i in range(4)})
    data = frame.to_csv(index=False).encode()
    ds, df = load(conn, storage, project, data, block_size=4096)  # small batches from the reader
    with storage.open_read(ds.key) as f:
        meta = pq.ParquetFile(f).metadata
    sizes = [meta.row_group(i).num_rows for i in range(meta.num_row_groups)]
    assert len(sizes) >= 3 and max(sizes) < 2500 and sum(sizes) == 6000  # a batch may overshoot
    assert df.equals(frame)
    # a narrow table keeps the usual group
    monkeypatch.setattr(ingest, "_ROW_GROUP_CELLS", 10**9)
    ds, _ = load(conn, storage, project, frame.to_csv(index=False).encode())
    with storage.open_read(ds.key) as f:
        assert pq.ParquetFile(f).metadata.num_row_groups == 1


def _text(values, delimiter=","):
    return ("a" + delimiter + "b\n" + "".join(f'"{v}"{delimiter}1\n' for v in values)).encode()


# Each case has a cell the reader cannot read as a number (a marker or a cell of blanks), so it
# reads the column as text: the cases are for the numbers read from that text.
@pytest.mark.parametrize(
    ("values", "dtype", "numbers"),
    [
        ([" 35", " NA", "7"], "int64", [35, None, 7]),
        (["35 ", " NA", " 12 "], "int64", [35, None, 12]),
        ([" 35", "N/A ", "null", " NaN", " #N/A"], "int64", [35, None, None, None, None]),
        ([" 35", "   ", "7"], "int64", [35, None, 7]),  # a cell of blanks is missing
        ([" -3.5", " NA", "7"], "double", [-3.5, None, 7.0]),
        ([" 1.2e-05", " 0.5", " NA"], "double", [1.2e-05, 0.5, None]),
        (["1.5E+10", " NA"], "double", [1.5e10, None]),
        (["+5", " NA", "6"], "int64", [5, None, 6]),
        ([" .5", " NA"], "double", [0.5, None]),
        (["5.", " NA"], "double", [5.0, None]),
        ([" 12345678901234567", " NA", "1"], "int64", [12345678901234567, None, 1]),
        ([" 35", " NA", "1,200"], "int64", [35, None, 1200]),  # with thousands separators
        ([" 35", "abc", " NA"], "string", None),  # a word among the numbers
        ([" 35", "None", " NA"], "string", None),  # the reader does not read None as missing
        ([" NA", "word", "other"], "string", None),  # a marker among words
        ([" 007", "35", " NA"], "string", None),  # a leading zero is a code
        ([" 1e", "35", " NA"], "string", None),
        ([" NA", " NA"], "string", None),  # no number at all
        ([" 99999999999999999999", "35", " NA"], "string", None),  # beyond int64
        ([" 12345678901234567", " 0.5", " NA"], "string", None),  # a float64 would round it
        ([" 0.5", " 99999999999999999999", " NA"], "string", None),
    ],
)
def test_numbers_written_with_surrounding_blanks_are_numbers(
    conn, storage, project, values, dtype, numbers
):
    ds, df = load(conn, storage, project, _text(values))
    assert dict(ds.schema)["a"] == dtype
    if numbers is not None:
        kept = ingest.read_dataset(storage, ds, nullable_dtypes=True)["a"]  # integers stay exact
        assert [None if pd.isna(v) else v for v in kept.tolist()] == numbers
    else:
        assert df["a"].tolist() == values


def test_blanks_around_numbers_are_trimmed_whatever_the_delimiter(conn, storage, project):
    ds, df = load(conn, storage, project, _text([" 35", " NA", "7"], delimiter=";"))
    assert dict(ds.schema)["a"] == "int64" and df["a"].isna().tolist() == [False, True, False]
    ds, df = load(conn, storage, project, _text([" 1,200", " NA", "7"], delimiter=";"))
    assert dict(ds.schema)["a"] == "string"  # a comma may be a decimal one there


def test_the_type_of_a_number_column_is_decided_across_batches(conn, storage, project, monkeypatch):
    monkeypatch.setattr(ingest, "_ROW_GROUP_ROWS", 3)
    big = "12345678901234567"  # a whole number a float64 would round
    first = lambda cell: [cell, *["1"] * 19]  # noqa: E731  (the reader's first block: plain)
    early = list(
        zip(
            first("1"), first("1"), first("1"), first("1"), first("1"),
            first(big), first("0.5"), first(big),
            strict=True,
        )
    )  # fmt: skip
    late = [(" NA", '" 0.5"', '"x"', '" 99999999999999999999"', "7", '" 0.5"', f'" {big}"', " NA")]
    late += [('" 2"', '" 0.25"', '" NA"', '" 5"', '" NA"', '" NA"', '" NA"', '" 3"')]
    data = "a,b,c,d,e,f,g,h\n" + "\n".join(",".join(r) for r in early + late) + "\n"
    ds, df = load(conn, storage, project, data.encode(), block_size=128)
    assert dict(ds.schema) == {
        "a": "int64",  # a marker with blanks in the last batch
        "b": "double",  # a fraction in the last batch
        "c": "string",  # a word in the last batch
        "d": "string",  # a number beyond int64 in the last batch
        "e": "int64",
        "f": "string",  # a whole number a float64 rounds early, a fraction late
        "g": "string",  # a fraction early, such a whole number late
        "h": "int64",  # the same whole number early, no fraction: exact
    }
    assert df["a"].isna().tolist()[-2:] == [True, False] and df["a"].iloc[-1] == 2
    assert df["b"].tolist()[-2:] == [0.5, 0.25]
    assert df["e"].isna().tolist()[-2:] == [False, True] and df["e"].iloc[-2] == 7
    exact = ingest.read_dataset(storage, ds, nullable_dtypes=True)["h"]
    assert exact.iloc[0] == int(big) and exact.iloc[-2] is pd.NA


def test_a_rewritten_wide_table_keeps_its_row_groups_small(conn, storage, project, monkeypatch):
    monkeypatch.setattr(ingest, "_ROW_GROUP_CELLS", 4 * 1500)
    monkeypatch.setattr(ingest, "_MIN_GROUP_ROWS", 100)
    frame = pd.DataFrame({f"c{i}": [str(v) for v in range(6000)] for i in range(4)})
    frame.loc[5999, "c0"] = " NA"  # the only cell the reader cannot read: it widens c0 to text
    ds, df = load(conn, storage, project, frame.to_csv(index=False).encode(), block_size=4096)
    assert dict(ds.schema)["c0"] == "int64"
    with storage.open_read(ds.key) as f:
        meta = pq.ParquetFile(f).metadata
    sizes = [meta.row_group(i).num_rows for i in range(meta.num_row_groups)]
    assert len(sizes) >= 3 and max(sizes) <= 1500 and sum(sizes) == 6000


@pytest.mark.parametrize(
    ("levels", "shown"),
    [
        ([" NA", "7", " 12"], [" 12", " NA"]),  # a number first
        ([" 12", "7", "1,200"], [" 12"]),
        ([" NA", "7"], [" NA"]),
        (["7", "12"], []),  # no blanks
        ([" 12", "abc"], []),  # a word
        ([" NA", " NA"], []),  # no number
        ([" 12", "99999999999999999999"], []),  # beyond int64, as an upload keeps it text
        ([" 12", "0.5", "12345678901234567"], []),  # a float64 would round it
        ([" 12", "12345678901234567"], [" 12"]),
    ],
)
def test_levels_with_blanks_around_numbers_are_the_ones_an_upload_reads_as_numbers(levels, shown):
    found = ingest.blank_padded_numbers(pd.Series(levels, dtype=object))
    assert found.tolist() == shown


def test_json_lines_become_a_column_per_key(conn, storage, project):
    lines = [
        '{"id": 1, "emb": [[1, 2], [3, 4]], "tag": "a", "ok": true, "x": 1}',
        "",
        '{"id": 2, "emb": [[5, 6]], "ok": false, "x": 2.5, "late": {"k": "v"}}',
        '{"id": 3, "tag": 7, "ok": null, "x": null}',
    ]
    ds, df = load(conn, storage, project, "\n".join(lines).encode())
    assert ds.schema == [
        ("id", "int64"),
        ("emb", "string"),
        ("tag", "string"),
        ("ok", "bool"),
        ("x", "double"),
        ("late", "string"),
    ]
    assert df["emb"].tolist()[:2] == ["[[1,2],[3,4]]", "[[5,6]]"]  # compact JSON: a list reads it
    assert df["tag"].tolist()[0] == "a" and df["tag"].tolist()[2] == "7"  # numbers among text
    assert df["late"].isna().tolist() == [True, False, True] and df.loc[1, "late"] == '{"k":"v"}'
    assert df["emb"].isna().tolist() == [False, False, True]


def test_a_json_array_of_objects_is_read_like_json_lines(conn, storage, project):
    records = [{"a": i, "b": f"t{i}", "c": [i, i + 1]} for i in range(5)]
    array = json.dumps(records, indent=2).encode()
    lines = "\n".join(json.dumps(r) for r in records).encode()
    a, from_array = load(conn, storage, project, b"\xef\xbb\xbf  " + array)  # a BOM and blanks
    b, from_lines = load(conn, storage, project, lines)
    assert a.schema == b.schema == [("a", "int64"), ("b", "string"), ("c", "string")]
    pd.testing.assert_frame_equal(from_array, from_lines)


def test_a_json_array_over_the_cap_points_to_json_lines(conn, storage, project, monkeypatch):
    monkeypatch.setattr(ingest, "JSON_ARRAY_MAX_BYTES", 10)
    with pytest.raises(IngestError, match="JSON Lines"):
        load(conn, storage, project, b'[{"a": 1}, {"a": 2}]')
    assert storage.list("projects/") == []


@pytest.mark.parametrize(
    "data",
    [b"[a],b\n1,2\n", b"{a},b\n1,2\n", b"[1 2],x\n3,4\n"],
)
def test_a_csv_whose_first_cell_starts_with_a_bracket_stays_a_csv(conn, storage, project, data):
    ds, df = load(conn, storage, project, data)
    assert ds.n_cols == 2 and len(df) == 1


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        (b'{"a": 1}\n{"a": 2,\n', "could not parse the JSON: line 2 column 9: Expecting"),
        (b'{"a": 1}\n[1, 2]\n', "line 2 is no object"),
        (b'[{"a": 1}, 3]', "no object"),
        (b'[{"a": 1}, {"a": 2]', "could not parse the JSON: line 1 column 19: Expecting"),
        (b'[{"a": 1},\n {"a": 2}]oops', "could not parse the JSON: line 2 column 11: Extra data"),
        (b'{"a": 1}\r\n{"a": 2,\r\n', "could not parse the JSON: line 2 column 9"),  # CRLF
        (b'{"a": 1}\n\n{"a": x}\n', "could not parse the JSON: line 3 column 7"),  # blank line
        (b'{"a": 1}\n{"a": "\xff"}\n', "the JSON is not valid UTF-8"),
        (b'[{"a": 1}, {"a": "\xff"}]', "the JSON is not valid UTF-8"),
        (b'{"a": 1}\n{"a": ' + b"[" * 100_000 + b"\n", "line 2: nested too deeply"),
        (b'{"a": ' + b"[" * 100_000 + b"\n", "line 1: nested too deeply"),  # the sniffed line
        (b'[{"a": ' + b"[" * 100_000 + b"]", "nested too deeply"),
    ],
)
def test_broken_json_is_refused_without_quoting_it(conn, storage, project, data, fragment):
    with pytest.raises(IngestError, match=fragment) as caught:
        load(conn, storage, project, data)
    assert '"a"' not in str(caught.value)
    assert storage.list("projects/") == []


@pytest.mark.parametrize("form", ["lines", "array"])
def test_json_that_stops_being_utf8_past_the_sample_is_refused(conn, storage, project, form):
    rows = [b'{"a": %d}' % i for i in range(120_000)]  # over the 1 MiB sample
    rows.append(b'{"a": "\xff"}')
    data = b"\n".join(rows) + b"\n" if form == "lines" else b"[" + b",".join(rows) + b"]"
    with pytest.raises(IngestError, match="the JSON is not valid UTF-8"):
        load(conn, storage, project, data)
    assert storage.list("projects/") == []


def test_an_empty_json_string_is_missing_as_an_empty_csv_cell(conn, storage, project):
    lines = ['{"n": 1, "t": "a"}', '{"n": "", "t": ""}', '{"n": 2.5, "t": "b"}']
    ds, df = load(conn, storage, project, "\n".join(lines).encode())
    assert dict(ds.schema) == {"n": "double", "t": "string"}
    assert df["n"].isna().tolist() == [False, True, False]
    assert df["t"].isna().tolist() == [False, True, False]


def test_an_empty_cell_is_missing_alike_in_csv_and_json(conn, storage, project):
    _, csv_df = load(conn, storage, project, b"n,t\n1,a\n,\n2.5,b\n")
    _, json_df = load(
        conn, storage, project, b'{"n":1,"t":"a"}\n{"n":"","t":""}\n{"n":2.5,"t":"b"}'
    )
    assert csv_df.isna().equals(json_df.isna())
    assert csv_df.dtypes.tolist() == json_df.dtypes.tolist()
