"""The module model and the checks every module result goes through.

A module is a function from a frame (and parameters, and optionally a second frame or a trained
state) to a frame (and, for ``train`` modules, a state). The state is plain JSON, never a
serialized Python object, so loading one cannot run code.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from fione.projects.ingest import unique_names

MODULE_ID = re.compile(r"[a-z][a-z0-9_]{0,39}")
KINDS = ("frame", "train", "predict")
# The most cells (rows times columns) a module may return: a memory ceiling (about 400 MB of
# float64), checked before a result is built where its size can be estimated.
MAX_OUTPUT_CELLS = 50_000_000
# A predict module only accepts a state made by its train module.
TRAIN_FOR = {"kmeans_predict": "kmeans_train", "lowrank_predict": "lowrank_train"}
_PATH = re.compile(r"/(?:[^\s/:'\"]+/)+[^\s:'\"]*")


class ModuleError(ValueError):
    """A problem with the data or parameters given to a module; the message is for the user."""


@dataclass(frozen=True)
class ModuleContext:
    other: pd.DataFrame | None = None  # the second dataset, for modules with other_dataset_id
    state: dict | None = None  # the trained state, for modules with module_model_id


@dataclass(frozen=True)
class ModuleOutput:
    df: pd.DataFrame
    state: dict | None = None


@dataclass(frozen=True)
class Module:
    id: str
    name: str
    kind: Literal["frame", "train", "predict"]
    params: dict  # flat JSON schema, see fione.schema
    run: Callable[[pd.DataFrame, dict, ModuleContext], ModuleOutput]


_BUILTIN: dict[str, Module] = {}


def register(module: Module) -> Module:
    if module.id in _BUILTIN:
        raise ValueError(f"module {module.id!r} is already registered")
    _BUILTIN[module.id] = module
    return module


def _load_builtins() -> None:
    from fione.modules import frame_ops, unsupervised  # noqa: F401  (they register on import)


def builtin_modules() -> list[Module]:
    """The built-in modules: the frame operations, then the others, each by id."""
    _load_builtins()
    return sorted(_BUILTIN.values(), key=lambda m: (m.kind != "frame", m.id))


def get_builtin(module_id: str) -> Module | None:
    _load_builtins()
    return _BUILTIN.get(module_id)


def check_module_id(module_id) -> str:
    """``module_id`` if it is a safe module id, else ``ValueError``."""
    if not isinstance(module_id, str) or not MODULE_ID.fullmatch(module_id):
        raise ValueError("a module id is 1-40 characters: a-z, 0-9 and _, starting with a letter")
    return module_id


def redact(text: str) -> str:
    """``text`` without absolute file paths, which must not reach job messages."""
    return _PATH.sub("<path>", text)


def check_cells(rows: int, columns: int) -> None:
    """``ModuleError`` if a result of ``rows`` x ``columns`` would be over the cell cap."""
    cells = rows * columns
    if cells > MAX_OUTPUT_CELLS:
        raise ModuleError(
            f"the result has {cells} cells; at most {MAX_OUTPUT_CELLS} cells are allowed"
        )


def validate_output(df) -> pd.DataFrame:
    """The module's result, checked and with its column names normalized like an import's."""
    if not isinstance(df, pd.DataFrame):
        raise ModuleError(f"the module must return a DataFrame, not {type(df).__name__}")
    names = list(df.columns)
    if not names:
        raise ModuleError("the result has no columns")
    if not all(isinstance(n, str) for n in names):
        raise ModuleError("column names must be text")
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ModuleError(f"duplicate column names: {duplicates}")
    check_cells(len(df), len(names))
    return df.set_axis(unique_names(names), axis=1)


def normalize_result(value) -> ModuleOutput:
    """The ``ModuleOutput`` for what an uploaded ``run`` returned: a frame or (frame, state)."""
    if isinstance(value, ModuleOutput):
        return value
    if isinstance(value, tuple) and len(value) == 2:
        return ModuleOutput(value[0], value[1])
    return ModuleOutput(value)


def require_column(df: pd.DataFrame, name: str) -> str:
    if name not in df.columns:
        raise ModuleError(f"unknown column '{name}'")
    return name


def pick_columns(df: pd.DataFrame, names: list[str]) -> list[str]:
    """``names`` (all the columns of ``df`` if empty), which must all exist."""
    if not names:
        return [str(c) for c in df.columns]
    unknown = [n for n in names if n not in df.columns]
    if unknown:
        raise ModuleError(f"unknown columns: {unknown}")
    return list(names)


def numeric_matrix(df: pd.DataFrame, names: list[str]) -> tuple[list[str], np.ndarray]:
    """The chosen columns as a float matrix with NaN for gaps. Integer and float columns are
    numeric; booleans, text and dates are not and are named in the error."""
    columns = pick_columns(df, names)
    if not columns:
        raise ModuleError("the dataset has no columns")
    bad = [
        c
        for c in columns
        if not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c])
    ]
    if bad:
        raise ModuleError(
            f"columns are not numeric: {bad}; leave them out with the 'columns' parameter"
        )
    matrix = df[columns].to_numpy(dtype=float, na_value=np.nan)
    if np.isinf(matrix).any():
        raise ModuleError("columns contain values that are not finite")
    return columns, matrix
