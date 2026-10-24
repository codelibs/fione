import codecs
import csv
import io
import itertools
import logging
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from fione.projects import service
from fione.projects.service import Dataset, DatasetType
from fione.storage import Storage

log = logging.getLogger(__name__)

_SAMPLE_SIZE = 1 << 20
_COPY_CHUNK = 1 << 20
_BLOCK_SIZE = 1 << 20
_ROW_GROUP_ROWS = 128 * 1024
_EXPORT_BATCH_ROWS = 50_000
_DELIMITERS = ",;\t|"
_SNIFF_ROWS = 20
_MAX_EXACT_FLOAT_INT = 2**53  # integers up to this magnitude survive a float64 round trip


class IngestError(Exception):
    """The upload is not a CSV Fione can read; the message is meant for the user."""


def _spool(stream: BinaryIO, path: Path, max_bytes: int) -> int:
    """Copy the upload to disk in chunks so it can be re-read; refuse more than ``max_bytes``."""
    total = 0
    with path.open("wb") as out:
        while chunk := stream.read(_COPY_CHUNK):
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("too large")
            out.write(chunk)
    return total


def _decode(sample: bytes, encoding: str, final: bool) -> str | None:
    # Incremental, so a multibyte character cut at the end of a partial sample is not an error.
    try:
        return codecs.getincrementaldecoder(encoding)().decode(sample, final)
    except UnicodeDecodeError:
        return None


def _detect_encoding(sample: bytes, final: bool) -> tuple[str, str]:
    """Return ``(encoding, decoded sample)``: UTF-8, else Shift_JIS family, else EUC-JP."""
    text = _decode(sample, "utf-8-sig", final)
    if text is not None:
        return ("utf-8-sig" if sample.startswith(codecs.BOM_UTF8) else "utf-8"), text
    candidates = [
        (encoding, text)
        for encoding in ("cp932", "euc_jp")
        if (text := _decode(sample, encoding, final)) is not None
    ]
    if not candidates:
        raise IngestError(
            "could not detect the text encoding (expected UTF-8, Shift_JIS or EUC-JP)"
        )
    # EUC-JP kana often decode as valid cp932, but as half-width katakana noise; prefer the
    # reading with fewer of those (ties go to cp932).
    return min(candidates, key=lambda c: sum("｡" <= ch <= "ﾟ" for ch in c[1]))


def _detect_delimiter(text: str) -> str:
    """Pick the delimiter that splits the leading rows into the most, consistent, fields."""
    best, best_score = ",", (False, 1)
    for delimiter in _DELIMITERS:
        try:
            rows = list(
                itertools.islice(csv.reader(io.StringIO(text), delimiter=delimiter), _SNIFF_ROWS)
            )
        except csv.Error:
            continue
        widths = {len(row) for row in rows if row}
        if max(widths, default=0) < 2:
            continue
        score = (len(widths) == 1, max(widths))
        if score > best_score:
            best, best_score = delimiter, score
    return best


def _inspect(path: Path) -> tuple[str, str]:
    """Return ``(encoding, delimiter)`` from a leading sample of the file."""
    with path.open("rb") as f:
        sample = f.read(_SAMPLE_SIZE)
        final = len(sample) < _SAMPLE_SIZE
    encoding, text = _detect_encoding(sample, final)
    if not text.strip():
        raise IngestError("empty file")
    if not final and "\n" in text:
        text = text[: text.rindex("\n") + 1]  # drop the line cut by the sample boundary
    return encoding, _detect_delimiter(text)


def _unique_names(raw: list[str]) -> list[str]:
    names: list[str] = []
    used: set[str] = set()
    for position, name in enumerate(raw, start=1):
        name = name.strip() or f"column_{position}"
        candidate, suffix = name, 2
        while candidate in used:
            candidate, suffix = f"{name}_{suffix}", suffix + 1
        used.add(candidate)
        names.append(candidate)
    return names


def _open_csv(
    path: Path, encoding: str, delimiter: str, block_size: int, column_types: dict[str, pa.DataType]
) -> pacsv.CSVStreamingReader:
    return pacsv.open_csv(
        path,
        read_options=pacsv.ReadOptions(encoding=encoding, block_size=block_size),
        parse_options=pacsv.ParseOptions(delimiter=delimiter),
        convert_options=pacsv.ConvertOptions(
            strings_can_be_null=True,
            column_types=column_types,
        ),
    )


def _write_parquet(
    reader: pacsv.CSVStreamingReader, names: list[str], out: Path
) -> tuple[int, pa.Schema]:
    for name, field in zip(names, reader.schema, strict=True):
        if pa.types.is_binary(field.type):  # pyarrow infers binary for invalid UTF-8
            raise IngestError(f"column {name!r} contains text that is not valid UTF-8")
    schema = pa.schema(
        [(name, field.type) for name, field in zip(names, reader.schema, strict=True)]
    )
    rows = 0
    pending: list[pa.RecordBatch] = []
    pending_rows = 0
    with pq.ParquetWriter(out, schema) as writer:
        for batch in reader:
            rows += batch.num_rows
            pending.append(batch.rename_columns(names))
            pending_rows += batch.num_rows
            if pending_rows >= _ROW_GROUP_ROWS:
                writer.write_table(pa.Table.from_batches(pending, schema))
                pending, pending_rows = [], 0
        if pending:
            writer.write_table(pa.Table.from_batches(pending, schema))
    return rows, schema


def _ints_fit_float64(text: pa.Array) -> bool:
    """True if every integer-looking value in the text column is exactly representable."""
    ints = pc.filter(text, pc.match_substring_regex(text, r"^[+-]?[0-9]+$"))
    try:
        bounds = pc.min_max(ints.cast(pa.int64())).as_py()
    except pa.ArrowInvalid:  # beyond int64
        return False
    if bounds["min"] is None:
        return True
    return -_MAX_EXACT_FLOAT_INT <= bounds["min"] and bounds["max"] <= _MAX_EXACT_FLOAT_INT


def _widen_columns(
    path: Path, encoding: str, delimiter: str, block_size: int, inferred: pa.Schema
) -> dict[str, pa.DataType]:
    """The wider type for each column whose inferred type some later value does not fit.

    Re-reads every column as text and tries the cast to the type inferred from the first
    block, so the whole file is never held in memory. An integer column that only fails
    on non-integers becomes float64; anything else that fails becomes string.
    """
    as_text = {name: pa.string() for name in inferred.names}
    fails: set[str] = set()
    float_fails: set[str] = set()
    with _open_csv(path, encoding, delimiter, block_size, as_text) as reader:
        for batch in reader:
            for index, field in enumerate(inferred):
                if pa.types.is_string(field.type):
                    continue
                column = batch.column(index)
                if field.name not in fails:
                    try:
                        column.cast(field.type)
                    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
                        fails.add(field.name)
                if not pa.types.is_integer(field.type) or field.name in float_fails:
                    continue
                # Checked on every batch, not just failing ones: widening must be lossless.
                if not _ints_fit_float64(column):
                    float_fails.add(field.name)
                elif field.name in fails:
                    try:
                        column.cast(pa.float64())
                    except pa.ArrowInvalid:
                        float_fails.add(field.name)
    int_columns = {field.name for field in inferred if pa.types.is_integer(field.type)}
    return {
        name: pa.float64() if name in int_columns and name not in float_fails else pa.string()
        for name in fails
    }


def _convert(
    path: Path, out: Path, encoding: str, delimiter: str, block_size: int
) -> tuple[int, pa.Schema]:
    """CSV to Parquet in one streaming pass; columns that hit a type mismatch are widened.

    pyarrow infers types from the first block, so a later value that does not fit makes
    the pass fail. Those columns are found and the pass is retried with them widened
    (integer to float64 when lossless, then string); each retry changes at least one column's type.
    """
    forced: dict[str, pa.DataType] = {}
    while True:
        inferred = None
        try:
            with _open_csv(path, encoding, delimiter, block_size, forced) as reader:
                inferred = reader.schema
                return _write_parquet(reader, _unique_names(inferred.names), out)
        except pa.ArrowInvalid:
            if inferred is None:
                raise
            widened = _widen_columns(path, encoding, delimiter, block_size, inferred)
            if all(forced.get(name) == dtype for name, dtype in widened.items()):
                raise
            forced |= widened


def ingest_csv(
    storage: Storage,
    conn: sqlite3.Connection,
    project_id: str,
    name: str,
    type: DatasetType,
    stream: BinaryIO,
    *,
    max_bytes: int = 2**30,
    tmp_dir: Path | None = None,
    block_size: int = _BLOCK_SIZE,
) -> Dataset:
    """Convert an uploaded CSV to Parquet in storage and record it as a dataset.

    The upload is streamed to a scratch file (under ``tmp_dir``, default the system temp
    dir), then converted block by block, so memory stays bounded by ``block_size``. Raises
    ``ValueError("too large")`` past ``max_bytes`` and ``IngestError`` for unreadable CSV.
    Nothing is left in storage or the database unless the dataset is fully recorded.
    """
    service.require_project(conn, project_id)
    with tempfile.TemporaryDirectory(dir=tmp_dir) as work:
        raw, parquet = Path(work) / "upload.csv", Path(work) / "data.parquet"
        _spool(stream, raw, max_bytes)
        encoding, delimiter = _inspect(raw)
        try:
            n_rows, schema = _convert(raw, parquet, encoding, delimiter, block_size)
        except (pa.ArrowInvalid, UnicodeDecodeError) as e:
            raise IngestError(f"could not parse the CSV: {e}") from e
        if n_rows == 0:
            raise IngestError("no data rows")
        return _register(storage, conn, project_id, name, type, parquet, n_rows, schema)


def _register(
    storage: Storage,
    conn: sqlite3.Connection,
    project_id: str,
    name: str,
    type: DatasetType,
    parquet: Path,
    n_rows: int,
    schema: pa.Schema,
) -> Dataset:
    """Store the Parquet file, then record the dataset; the object is removed if that fails."""
    dataset_id = service.reserve_dataset_id(conn)
    key = f"projects/{project_id}/datasets/{dataset_id}/data.parquet"
    with parquet.open("rb") as f:
        storage.put(key, f)
    try:
        return service.add_dataset(
            conn,
            project_id,
            name,
            type,
            n_rows,
            len(schema),
            [(field.name, str(field.type)) for field in schema],
            key,
            dataset_id,
        )
    except BaseException:
        try:
            storage.delete(key)
        except Exception:
            # Never mask the original error (a JobAbort must stay a JobAbort).
            log.exception("could not remove the object %s", key)
        raise


def _frame_schema(frame: pd.DataFrame, fallback_types: dict[str, pa.DataType]) -> pa.Schema:
    """The frame's Arrow schema; a column holding only missing values takes its fallback type."""
    fields = []
    for field in pa.Schema.from_pandas(frame, preserve_index=False):
        dtype = (
            fallback_types.get(field.name, field.type)
            if pa.types.is_null(field.type)
            else field.type
        )
        fields.append(pa.field(field.name, pa.string() if dtype == pa.large_string() else dtype))
    return pa.schema(fields)


def ingest_batches(
    storage: Storage,
    conn: sqlite3.Connection,
    project_id: str,
    name: str,
    type: DatasetType,
    batches: Iterable[pd.DataFrame],
    *,
    fallback_types: dict[str, pa.DataType] | None = None,
    tmp_dir: Path | None = None,
) -> Dataset:
    """Record frames, written one at a time to a Parquet file, as a dataset.

    The column types are inferred from the first frame; a column with only missing values there
    takes its type from ``fallback_types`` (a later frame may hold values for it). Raises
    ``IngestError`` when there are no rows. Whatever ``batches`` raises propagates; nothing is
    left in storage or the database unless the dataset is fully recorded.
    """
    service.require_project(conn, project_id)
    with tempfile.TemporaryDirectory(dir=tmp_dir) as work:
        parquet = Path(work) / "data.parquet"
        n_rows = 0
        schema = writer = None
        try:
            for frame in batches:
                if writer is None:
                    schema = _frame_schema(frame, fallback_types or {})
                    writer = pq.ParquetWriter(parquet, schema)
                writer.write_table(pa.Table.from_pandas(frame, schema=schema, preserve_index=False))
                n_rows += len(frame)
        finally:
            if writer is not None:
                writer.close()
        if n_rows == 0:
            raise IngestError("no data rows")
        return _register(storage, conn, project_id, name, type, parquet, n_rows, schema)


def read_schema(storage: Storage, dataset: Dataset) -> pa.Schema:
    with storage.open_read(dataset.key) as f:
        return pq.ParquetFile(f).schema_arrow


_NULLABLE = {
    **{
        getattr(pa, name)(): dtype
        for name, dtype in [
            ("int8", pd.Int8Dtype()),
            ("int16", pd.Int16Dtype()),
            ("int32", pd.Int32Dtype()),
            ("int64", pd.Int64Dtype()),
            ("uint8", pd.UInt8Dtype()),
            ("uint16", pd.UInt16Dtype()),
            ("uint32", pd.UInt32Dtype()),
            ("uint64", pd.UInt64Dtype()),
        ]
    },
    pa.bool_(): pd.BooleanDtype(),
}


def read_dataset(
    storage: Storage,
    dataset: Dataset,
    columns: list[str] | None = None,
    *,
    nullable_dtypes: bool = False,
) -> pd.DataFrame:
    """The dataset as a frame. Integer and boolean columns become pandas nullable dtypes when
    ``nullable_dtypes`` is set, so that gaps neither turn integers into floats (losing digits
    above 2**53) nor booleans into objects."""
    with storage.open_read(dataset.key) as f:
        table = pq.ParquetFile(f).read(columns=columns)
    return table.to_pandas(types_mapper=_NULLABLE.get if nullable_dtypes else None)


def read_dataset_sample(
    storage: Storage,
    dataset: Dataset,
    max_rows: int = 200_000,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """The first ``max_rows`` rows of the dataset (all of them if it is smaller), read from the
    start of the file without loading the rest: deterministic, and bounded by ``max_rows``."""
    batches: list[pa.RecordBatch] = []
    rows = 0
    with storage.open_read(dataset.key) as f:
        batch_rows = min(max_rows, _EXPORT_BATCH_ROWS)
        for batch in pq.ParquetFile(f).iter_batches(batch_size=batch_rows, columns=columns):
            batches.append(batch)
            rows += batch.num_rows
            if rows >= max_rows:
                break
    if not batches:  # a file without rows: the full read is empty too
        return read_dataset(storage, dataset, columns)
    return pa.Table.from_batches(batches).slice(0, max_rows).to_pandas()


def export_csv(storage: Storage, dataset: Dataset) -> Iterator[bytes]:
    """The dataset as UTF-8 CSV with a header, yielded in batches of rows."""
    with storage.open_read(dataset.key) as f:
        batches = pq.ParquetFile(f).iter_batches(batch_size=_EXPORT_BATCH_ROWS)
        for number, batch in enumerate(batches):
            out = io.BytesIO()
            pacsv.write_csv(batch, out, pacsv.WriteOptions(include_header=number == 0))
            yield out.getvalue()
