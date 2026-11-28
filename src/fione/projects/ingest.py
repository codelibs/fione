import codecs
import csv
import io
import itertools
import json
import logging
import re
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import BinaryIO

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from fione.projects import service
from fione.projects.service import Dataset, DatasetType
from fione.schema import clean_text
from fione.storage import Storage

log = logging.getLogger(__name__)

_SAMPLE_SIZE = 1 << 20
_COPY_CHUNK = 1 << 20
_BLOCK_SIZE = 1 << 20
_ROW_GROUP_ROWS = 128 * 1024
# A row group holds at most this many cells: the rows of a table of thousands of columns would
# otherwise fill gigabytes (128k rows of 10,000 columns) before the first group is written.
_ROW_GROUP_CELLS = 16 * 1024 * 1024
_MIN_GROUP_ROWS = 1024
_EXPORT_BATCH_ROWS = 50_000
_PAGE_BATCH_ROWS = 8192  # read_dataset_rows
_DELIMITERS = ",;\t|"
_SNIFF_ROWS = 20
_MAX_EXACT_FLOAT_INT = 2**53  # integers up to this magnitude survive a float64 round trip
# A JSON array is read whole: json.load held about 5.6 times the file (1 GB for a 179 MB array),
# so a larger one is refused with a pointer to JSON Lines, which is read a line at a time.
JSON_ARRAY_MAX_BYTES = 200 * 2**20
_JSON_ROWS = 50_000  # rows of a JSON upload written at a time


class IngestError(Exception):
    """The upload is not a CSV or JSON Fione can read; the message is meant for the user."""


_PARSE_ERROR = re.compile(r"Expected (\d+) columns?, got (\d+)")


def ingest_error_message(error: IngestError) -> str:
    """The one-line refusal for a CSV Fione cannot read. The parser's own text quotes the
    offending row, which is data, so only the two field counts are kept."""
    message = str(error)
    if not message.startswith("could not parse the CSV"):
        return clean_text(message, 200)
    found = _PARSE_ERROR.search(message)
    detail = f": a row has {found[2]} fields, the header {found[1]}" if found else ""
    return f"could not parse the CSV{detail}"


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


def unique_names(raw: list[str]) -> list[str]:
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
    group_rows = _group_rows(len(names))
    with pq.ParquetWriter(out, schema) as writer:
        for batch in reader:
            rows += batch.num_rows
            pending.append(batch.rename_columns(names))
            pending_rows += batch.num_rows
            if pending_rows >= group_rows:
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
    except pa.ArrowInvalid:  # more digits than an int64 holds
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


# 1,234 and 1,234,567.8 (no leading zero), or plain digits without leading zeros
THOUSANDS_NUMBER = r"^-?([1-9][0-9]{0,2}(,[0-9]{3})+|0|[1-9][0-9]*)(\.[0-9]+)?$"
# a number the reader reads (a sign, a point at either end, an exponent), without a leading zero
_PLAIN_NUMBER = r"^[+-]?((0|[1-9][0-9]*)(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$"
_FLOAT_MARK = r"[.eE]"
_SMALL_INTEGER = r"^(-?[1-9][0-9]{0,14}|0)$"  # at most 15 digits: a float64 holds it exactly
# what the CSV reader reads as missing; after trimming blanks, a cell like this is missing too
_NULL_TEXTS = pa.array(pacsv.ConvertOptions().null_values)


def _group_rows(columns: int) -> int:
    """The rows of one row group of a table of ``columns`` columns: a wide table gets fewer."""
    return min(_ROW_GROUP_ROWS, max(_MIN_GROUP_ROWS, _ROW_GROUP_CELLS // max(columns, 1)))


def _trimmed(values: pa.Array) -> tuple[pa.Array, pa.Array]:
    """``values`` (text, no nulls) without surrounding blanks, and which of them are then empty
    or a marker the reader reads as missing (``NA``, ``null``...)."""
    trimmed = pc.utf8_trim_whitespace(values)
    return trimmed, pc.is_in(trimmed, value_set=_NULL_TEXTS)


def _is_number(numbers: pa.Array, thousands: bool) -> bool:
    """Whether every one of ``numbers`` (trimmed text) is a number: ``_PLAIN_NUMBER``, or with
    ``thousands`` also ``THOUSANDS_NUMBER``."""
    found = pc.match_substring_regex(numbers, _PLAIN_NUMBER)
    if thousands:
        found = pc.or_(found, pc.match_substring_regex(numbers, THOUSANDS_NUMBER))
    return pc.all(found).as_py()


def _integers(numbers: pa.Array) -> pa.Array:
    """The whole numbers among ``numbers`` (trimmed text), as text without a plus sign or
    thousands separators."""
    whole = pc.filter(numbers, pc.invert(pc.match_substring_regex(numbers, _FLOAT_MARK)))
    return pc.replace_substring_regex(pc.replace_substring(whole, ",", ""), r"^\+", "")


def blank_padded_numbers(levels: pd.Series) -> pd.Series:
    """The values of ``levels`` (the values a model learned for a text column) that have blanks
    around them, the numbers first, when all of them are numbers or missing markers once
    trimmed, one is a number, and none is beyond what an upload reads as a number (see
    ``_number_columns``): the column an upload now reads as numbers. Empty when the levels are
    anything else."""
    text = levels[levels.map(lambda value: isinstance(value, str))]
    trimmed = text.str.strip()
    padded = text[text != trimmed]
    markers = trimmed.isin(_NULL_TEXTS.to_pylist())
    numbers = trimmed[~markers]
    none = padded.iloc[:0]
    if not len(padded) or not len(numbers) or len(text) != len(levels):
        return none
    if not (numbers.str.fullmatch(_PLAIN_NUMBER) | numbers.str.fullmatch(THOUSANDS_NUMBER)).all():
        return none
    fraction = numbers.str.contains(_FLOAT_MARK).any()
    whole = numbers[~numbers.str.contains(_FLOAT_MARK)].str.replace(",", "").str.lstrip("+")
    limit = _MAX_EXACT_FLOAT_INT if fraction else 2**63 - 1
    if any(abs(int(value)) > limit for value in whole):
        return none
    is_marker = markers[padded.index]
    return pd.concat([padded[~is_marker], padded[is_marker]])  # a number first, to show


def _scan_number_column(file: pq.ParquetFile, name: str, thousands: bool) -> pa.DataType | None:
    """The number type (int64, or float64 when a value has a fraction or an exponent) the text
    column ``name`` reads as, or None for a column that stays text (see ``_number_columns``)."""
    marked = number = fraction = False
    wide = False  # a whole number beyond what a float64 holds exactly
    for batch in file.iter_batches(batch_size=_ROW_GROUP_ROWS, columns=[name]):
        values = pc.drop_null(batch.column(0))
        if not len(values):
            continue
        trimmed, missing = _trimmed(values)
        numbers = pc.filter(trimmed, pc.invert(missing))
        marked = marked or pc.any(pc.not_equal(values, trimmed)).as_py()
        if len(numbers) and pc.all(pc.match_substring_regex(numbers, _SMALL_INTEGER)).as_py():
            number = True  # the usual column: whole numbers a float64 holds exactly
        elif len(numbers):
            if not _is_number(numbers, thousands):
                return None
            number = True
            marked = marked or thousands and pc.any(pc.match_substring(numbers, ",")).as_py()
            fraction = fraction or pc.any(pc.match_substring_regex(numbers, _FLOAT_MARK)).as_py()
            whole = _integers(numbers)
            try:
                bounds = pc.min_max(whole.cast(pa.int64())).as_py()
            except pa.ArrowInvalid:  # more digits than an int64 holds
                return None
            if bounds["min"] is not None and not (
                -_MAX_EXACT_FLOAT_INT <= bounds["min"] and bounds["max"] <= _MAX_EXACT_FLOAT_INT
            ):
                wide = True
    if not (marked and number) or (fraction and wide):
        return None
    return pa.float64() if fraction else pa.int64()


def _number_columns(parquet: Path, schema: pa.Schema, thousands: bool) -> dict[str, pa.DataType]:
    """The text columns of ``parquet`` whose values, trimmed of surrounding blanks, are all
    numbers (or missing: empty, ``NA``, ``null``...), with the number type each reads as: int64,
    or float64 when a value has a fraction or an exponent. At least one value must show a
    thousands separator (``16,853``, ``1,234,567.5``, in a comma-delimited file only: elsewhere a
    comma may be a decimal one) or blanks around it (``' 35'``, ``'12 '``), and one must be a
    number, so ``0,123`` and other text stay text, as do numbers with a leading zero, whole
    numbers beyond int64, and whole numbers beyond what a float64 holds exactly in a column with
    fractions. The columns are scanned one at a time, so a table of many text columns is not read
    in full for the few that stay candidates."""
    found = {}
    with pq.ParquetFile(parquet) as file:
        for field in schema:
            if pa.types.is_string(field.type):
                dtype = _scan_number_column(file, field.name, thousands)
                if dtype is not None:
                    found[field.name] = dtype
    return found


def _to_number(column: pa.ChunkedArray | pa.Array, dtype: pa.DataType) -> pa.Array:
    """The text ``column`` as numbers: blanks trimmed, thousands separators dropped, and empty
    cells and missing markers as missing."""
    trimmed, missing = _trimmed(pc.fill_null(column, ""))
    cleaned = pc.replace_substring(trimmed, ",", "")
    if pa.types.is_integer(dtype):
        cleaned = pc.replace_substring_regex(cleaned, r"^\+", "")
    return pc.if_else(missing, pa.scalar(None, pa.string()), cleaned).cast(dtype)


def _read_numbers(parquet: Path, schema: pa.Schema, thousands: bool) -> pa.Schema:
    """Rewrite ``parquet`` with the text columns that hold numbers (see ``_number_columns``) as
    numbers; returns the schema of the result (``schema`` itself when there are none)."""
    found = _number_columns(parquet, schema, thousands)
    if not found:
        return schema
    typed = pa.schema([(f.name, found.get(f.name, f.type)) for f in schema])
    out = parquet.with_suffix(".numbers")
    try:
        with pq.ParquetFile(parquet) as file, pq.ParquetWriter(out, typed) as writer:
            for batch in file.iter_batches(batch_size=_group_rows(len(schema))):
                columns = [
                    _to_number(batch.column(i), found[f.name])
                    if f.name in found
                    else batch.column(i)
                    for i, f in enumerate(schema)
                ]
                writer.write_table(pa.Table.from_arrays(columns, schema=typed))
        out.replace(parquet)
    finally:
        out.unlink(missing_ok=True)
    return typed


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
                return _write_parquet(reader, unique_names(inferred.names), out)
        except pa.ArrowInvalid:
            if inferred is None:
                raise
            widened = _widen_columns(path, encoding, delimiter, block_size, inferred)
            if all(forced.get(name) == dtype for name, dtype in widened.items()):
                raise
            forced |= widened


def _json_form(path: Path) -> str | None:
    """``"array"`` for a JSON array of objects or lists (``[`` then ``{`` or ``[``), ``"lines"``
    for JSON Lines (``{`` and a first line that parses), else None (a CSV). Judged on a leading
    sample, so a CSV whose first cell starts with a bracket stays a CSV."""
    with path.open("rb") as f:
        sample = f.read(_SAMPLE_SIZE)
    text = _decode(sample, "utf-8-sig", len(sample) < _SAMPLE_SIZE)
    if text is None:
        return None
    text = text.lstrip()
    if text.startswith("["):
        return "array" if text[1:].lstrip()[:1] in ("{", "[") else None
    if text.startswith("{"):
        first = text.split("\n", 1)[0]
        try:
            return "lines" if isinstance(json.loads(first), dict) else None
        except ValueError:
            return None
    return None


def _json_records(path: Path, form: str) -> Iterator[dict]:
    """The objects of a JSON array or of JSON Lines (blank lines skipped)."""
    if form == "array":
        if path.stat().st_size > JSON_ARRAY_MAX_BYTES:
            raise IngestError(
                f"the JSON array is over {JSON_ARRAY_MAX_BYTES // 2**20} MB; save it as JSON Lines "
                "(one object per line) or as CSV"
            )
        try:
            with path.open(encoding="utf-8-sig") as f:
                records = json.load(f)
        except (ValueError, RecursionError) as e:
            raise IngestError(f"could not parse the JSON: {_json_error(e)}") from None
        for record in records:
            if not isinstance(record, dict):
                raise IngestError(
                    "could not parse the JSON: the array holds a value that is no object"
                )
            yield record
        return
    with path.open(encoding="utf-8-sig") as f:
        for number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except (ValueError, RecursionError) as e:
                raise IngestError(
                    f"could not parse the JSON: line {number}: {_json_error(e)}"
                ) from None
            if not isinstance(record, dict):
                raise IngestError(f"could not parse the JSON: line {number} is no object")
            yield record


def _json_error(error: Exception) -> str:
    # the decoder's message names a position, never the text (which is data)
    if isinstance(error, RecursionError):
        return "nested too deeply"
    return getattr(error, "msg", "not JSON")


def _json_kind(value) -> str | None:
    if value is None or value == "":  # an empty string is missing, as an empty CSV cell
        return None
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int" if -(2**63) <= value < 2**63 else "text"
    if isinstance(value, float):
        return "float"
    return "text"  # a string, a list or an object


def _json_types(kinds: set[str]) -> pa.DataType:
    """The column type for the kinds of value it holds: numbers stay numbers, true/false a
    bool, anything else (strings, lists, objects, a mix) text."""
    if kinds <= {"int"} and kinds:
        return pa.int64()
    if kinds <= {"int", "float"} and kinds:
        return pa.float64()
    if kinds == {"bool"}:
        return pa.bool_()
    return pa.string()


def _json_cell(value, dtype: pa.DataType):
    if value is None or value == "":
        return None
    if not pa.types.is_string(dtype):
        return value
    if isinstance(value, str):
        return value
    # a list or an object as its compact JSON text (a list of numbers reads as one); a number or
    # true/false among text as its JSON text
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _convert_json(path: Path, out: Path, form: str) -> tuple[int, pa.Schema]:
    """JSON (an array of objects, or JSON Lines) to Parquet: a column for each top-level key, in
    the order first seen. Read twice, once for the keys and their types and once to write, so
    JSON Lines is never held whole."""
    kinds: dict[str, set[str]] = {}
    for record in _json_records(path, form):
        for key, value in record.items():
            found = kinds.setdefault(key, set())
            if (kind := _json_kind(value)) is not None:
                found.add(kind)
    keys = list(kinds)
    names = unique_names(keys)
    schema = pa.schema(
        [(name, _json_types(kinds[key])) for name, key in zip(names, keys, strict=True)]
    )
    rows = 0
    with pq.ParquetWriter(out, schema) as writer:
        chunk: list[dict] = []
        for record in itertools.chain(_json_records(path, form), [None]):
            if record is not None:
                chunk.append(record)
            if chunk and (record is None or len(chunk) >= _JSON_ROWS):
                columns = [
                    pa.array([_json_cell(r.get(key), f.type) for r in chunk], type=f.type)
                    for key, f in zip(keys, schema, strict=True)
                ]
                writer.write_table(pa.Table.from_arrays(columns, schema=schema))
                rows += len(chunk)
                chunk = []
    return rows, schema


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
    """Convert an uploaded CSV, JSON array of objects or JSON Lines file to Parquet in storage
    and record it as a dataset (see ``_json_form`` for how JSON is told from CSV).

    The upload is streamed to a scratch file (under ``tmp_dir``, default the system temp
    dir), then converted block by block, so memory stays bounded by ``block_size``. Raises
    ``ValueError("too large")`` past ``max_bytes`` and ``IngestError`` for unreadable CSV.
    Nothing is left in storage or the database unless the dataset is fully recorded.
    """
    service.require_project(conn, project_id)
    with tempfile.TemporaryDirectory(dir=tmp_dir) as work:
        raw, parquet = Path(work) / "upload.csv", Path(work) / "data.parquet"
        _spool(stream, raw, max_bytes)
        if (form := _json_form(raw)) is not None:
            n_rows, schema = _convert_json(raw, parquet, form)
            if n_rows == 0 or not len(schema):
                raise IngestError("no data rows")
            return _register(storage, conn, project_id, name, type, parquet, n_rows, schema)
        encoding, delimiter = _inspect(raw)
        try:
            n_rows, schema = _convert(raw, parquet, encoding, delimiter, block_size)
            # in a comma-delimited file 12,500 is 12500; elsewhere a comma may be a decimal one
            schema = _read_numbers(parquet, schema, delimiter == ",")
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


def _runs(rng: np.random.Generator, rows: int, take: int, run: int) -> np.ndarray:
    """``take`` of ``rows`` positions, in order: runs of ``run`` neighbours, one in each of
    equal stretches of the rows (all of them over a stretch of the rows when ``take`` is more
    than half), so rows that sit together stay together."""
    if 2 * take > rows:
        return np.sort(rng.choice(rows, take, replace=False))
    runs = -(-take // run)
    edges = np.arange(runs + 1)
    stretch = edges * rows // runs  # the stretch of each run
    done = edges * take // runs  # the rows taken before each run
    length = np.diff(done)
    start = stretch[:-1] + rng.integers(0, np.diff(stretch) - length + 1)
    return np.repeat(start - done[:-1], length) + np.arange(take)


def read_dataset_runs(
    storage: Storage,
    dataset: Dataset,
    max_rows: int = 200_000,
    columns: list[str] | None = None,
    *,
    seed: int = 0,
    run: int = 100,
) -> pd.DataFrame:
    """About ``max_rows`` rows of the whole dataset (all of them if it is smaller), in file
    order, drawn with ``seed`` as runs of ``run`` neighbouring rows spread over the whole file.
    A file sorted by time or by group shows all of its periods, not just its first, and rows
    that sit together (the rows of one id) are still together. The file is read in batches of
    ``_ROW_GROUP_ROWS`` rows, each keeping its share of the sample, so memory is bounded by one
    batch and the sample whatever the row groups hold, but the requested ``columns`` of the whole
    file are read."""
    rng = np.random.default_rng(seed)
    with storage.open_read(dataset.key) as f:
        parquet = pq.ParquetFile(f)
        meta = parquet.metadata
        if meta.num_rows <= max_rows:
            return parquet.read(columns=columns).to_pandas()
        parts, seen, kept = [], 0, 0
        for batch in parquet.iter_batches(_ROW_GROUP_ROWS, columns=columns, use_threads=False):
            rows = batch.num_rows
            seen += rows
            take = round(max_rows * seen / meta.num_rows) - kept
            if take <= 0:
                continue
            table = pa.Table.from_batches([batch])
            if take < rows:
                table = table.take(_runs(rng, rows, take, run))
            parts.append(table)
            kept += take
    return pa.concat_tables(parts).to_pandas()


def dataset_row_count_and_empty_columns(
    storage: Storage, dataset: Dataset, columns: list[str]
) -> tuple[int, dict[str, bool | None]]:
    """(the rows of the dataset, and for each of ``columns`` whether it holds no value in any row:
    True or False, or None when the file cannot say). The answer comes from the file's metadata,
    which counts the missing values of every row group exactly, so no data is read. A column of
    type null (all empty in a CSV) is empty; a column of numbers with no minimum or maximum in a
    row group may hold NaN that is not counted as missing, so it is left to the caller (None)."""
    with storage.open_read(dataset.key) as f:
        parquet = pq.ParquetFile(f)
        meta, schema = parquet.metadata, parquet.schema_arrow
        leaves = {name: j for j, name in enumerate(meta.schema.names)}
        found: dict[str, bool | None] = {}
        for name in columns:
            if name not in schema.names:
                continue
            kind = schema.field(name).type
            if pa.types.is_null(kind):
                found[name] = True
                continue
            j = leaves.get(name)
            if j is None or meta.num_row_groups == 0:
                found[name] = None
                continue
            missing = 0
            for g in range(meta.num_row_groups):
                group = meta.row_group(g)
                stats = group.column(j).statistics
                if stats is None or not stats.has_null_count:
                    missing = -1
                    break
                if (
                    pa.types.is_floating(kind)
                    and not stats.has_min_max
                    and stats.null_count < group.num_rows
                ):
                    missing = -1  # NaN is not counted as missing: the file cannot say
                    break
                missing += stats.null_count
            found[name] = None if missing < 0 else missing == meta.num_rows
        return meta.num_rows, found


def _head(parquet: pq.ParquetFile, group: int, rows: int, columns) -> list[pa.RecordBatch]:
    """The first ``rows`` rows of the row group, decoding no more of it than that needs."""
    batches = parquet.iter_batches(rows, row_groups=[group], columns=columns, use_threads=False)
    return list(itertools.islice(batches, 1))


def read_dataset_spread(
    storage: Storage,
    dataset: Dataset,
    rows: int,
    columns: list[str] | None = None,
    *,
    seed: int = 0,
    max_groups: int = 8,
    per_group: int | None = None,
) -> pd.DataFrame:
    """``rows`` rows drawn with ``seed`` from at most ``max_groups`` evenly spaced row groups
    (all of their rows if there are fewer), in file order: a sample of the whole file, never
    just its head, that is the same every time.

    Without ``per_group``, memory is bounded by the groups, not by ``rows``: up to
    ``max_groups`` whole groups of ``columns`` are read before sampling. A CSV upload's groups
    hold 131,072 rows (so about 1M rows at most); a dataset written from frames (predictions,
    module output) has one group per frame, which can be larger. With ``per_group``, only the
    first ``per_group`` rows of each of those groups are read, whatever their size.
    """
    with storage.open_read(dataset.key) as f:
        parquet = pq.ParquetFile(f)
        count = parquet.metadata.num_row_groups
        groups = np.unique(np.round(np.linspace(0, count - 1, min(count, max_groups))))
        groups = groups.astype(int).tolist()
        if per_group is None:
            table = parquet.read_row_groups(groups, columns=columns) if count else None
        else:
            heads = [b for g in groups for b in _head(parquet, g, per_group, columns)]
            table = pa.Table.from_batches(heads) if heads else None
        if table is None:  # no rows
            table = parquet.schema_arrow.empty_table()
            return (table.select(columns) if columns is not None else table).to_pandas()
    if table.num_rows > rows:
        picked = np.random.default_rng(seed).choice(table.num_rows, rows, replace=False)
        table = table.take(np.sort(picked))
    return table.to_pandas()


def read_dataset_rows(
    storage: Storage,
    dataset: Dataset,
    offset: int,
    limit: int,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Rows ``offset`` to ``offset + limit`` (fewer at the end), reading only the row groups
    that hold them, so a page deep in a large file costs no more than the first one. They are
    read in batches of ``_PAGE_BATCH_ROWS``, so memory is bounded by the page, not the groups."""
    with storage.open_read(dataset.key) as f:
        parquet = pq.ParquetFile(f)
        meta = parquet.metadata
        groups, start, first_row = [], 0, None
        for index in range(meta.num_row_groups):
            rows = meta.row_group(index).num_rows
            if start + rows > offset and start < offset + limit:
                groups.append(index)
                first_row = start if first_row is None else first_row
            start += rows
        if not groups:  # past the end: no rows, the columns all the same
            table = parquet.schema_arrow.empty_table()
            return (table.select(columns) if columns is not None else table).to_pandas()
        skip, batches, wanted = offset - first_row, [], limit
        batches_of = parquet.iter_batches(
            _PAGE_BATCH_ROWS, row_groups=groups, columns=columns, use_threads=False
        )
        for batch in batches_of:
            if skip >= len(batch):
                skip -= len(batch)
                continue
            batches.append(batch.slice(skip, wanted))
            wanted -= len(batches[-1])
            skip = 0
            if wanted <= 0:
                break
    return pa.Table.from_batches(batches).to_pandas()


def export_csv(storage: Storage, dataset: Dataset) -> Iterator[bytes]:
    """The dataset as UTF-8 CSV with a header, yielded in batches of rows."""
    with storage.open_read(dataset.key) as f:
        batches = pq.ParquetFile(f).iter_batches(batch_size=_EXPORT_BATCH_ROWS)
        for number, batch in enumerate(batches):
            out = io.BytesIO()
            pacsv.write_csv(batch, out, pacsv.WriteOptions(include_header=number == 0))
            yield out.getvalue()
