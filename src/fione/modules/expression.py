"""A small, safe language for a column computed from other columns.

The text is parsed with ``ast`` and only the node types and functions listed here are evaluated,
by this module's own code over numpy arrays. Nothing is passed to ``eval`` or ``exec``, there is
no attribute access, subscript or user-defined name, and every number is a float, so no
expression can run code or compute a huge integer. Every value is a float64 array (or one
float); an infinite value, such as a division by zero or ``log(0)``, is empty (NaN). A pattern
with ``*`` is matched by plain string comparison, never by a regular expression.
"""

import ast
import unicodedata

import numpy as np
import pandas as pd

from fione.modules import registry
from fione.modules.registry import ModuleError, check_cells

MAX_LENGTH = 1000
MAX_DEPTH = 100
MAX_OPERANDS = 10_000  # the columns and values the row functions of one expression read

_BINARY = {
    ast.Add: np.add,
    ast.Sub: np.subtract,
    ast.Mult: np.multiply,
    ast.Div: np.divide,
    ast.Pow: np.power,
}
_COMPARE = {
    ast.Eq: np.equal,
    ast.NotEq: np.not_equal,
    ast.Lt: np.less,
    ast.LtE: np.less_equal,
    ast.Gt: np.greater,
    ast.GtE: np.greater_equal,
}
_UNARY_FUNCTIONS = {
    "abs": np.abs,
    "sqrt": np.sqrt,
    "log": np.log,
    "log1p": np.log1p,
    "exp": np.exp,
}
_TWO_FUNCTIONS = {"min2": np.minimum, "max2": np.maximum}
_ROW_FUNCTIONS = ("rowsum", "rowmean", "rowcount")
FUNCTIONS = (
    *_UNARY_FUNCTIONS,
    *_TWO_FUNCTIONS,
    *_ROW_FUNCTIONS,
    "col",
    "where",
    "isnull",
    "clip",
)


def _glob(pattern: str):
    """A function telling whether a name matches ``pattern``, in which ``*`` stands for any
    characters (also none) and every other character for itself."""
    first, *rest = pattern.split("*")
    if not rest:
        return lambda name: name == pattern
    last = rest.pop()

    def matches(name: str) -> bool:
        if len(name) < len(first) + len(last) or not name.startswith(first):
            return False
        if not name.endswith(last):
            return False
        at, end = len(first), len(name) - len(last)
        for part in rest:  # the parts between the stars, in order and apart
            found = name.find(part, at, end)
            if found < 0:
                return False
            at = found + len(part)
        return True

    return matches


def _truth(values):
    """Whether each value is true: not 0 and not empty."""
    return (values != 0) & ~np.isnan(values)


def _flag(condition):
    return np.where(condition, 1.0, 0.0)


class _Evaluator:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.rows = len(df)
        self.columns: dict[str, np.ndarray] = {}
        self.infinite = np.zeros(self.rows, dtype=bool)  # rows where a step came out infinite
        self.operands = 0  # the columns and values a row function reads, over the expression
        self.labels: list[tuple[str, object]] | None = None  # (text, label) of each column
        self.same_text: dict[str, list] | None = None  # NFKC text -> the labels that have it

    def finite(self, values):
        """``values`` with an infinite value made empty."""
        infinite = np.isinf(values)
        self.infinite |= infinite
        return np.where(infinite, np.nan, values)

    def column(self, name: str, keep: bool = True) -> np.ndarray:
        """The column as floats (an infinite value is empty); kept for a later use if ``keep``."""
        if name in self.columns:
            return self.columns[name]
        if name not in self.df.columns:
            raise ModuleError(f"unknown column '{name}'")
        series = self.df[name]
        if not (
            pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series)
        ) or pd.api.types.is_complex_dtype(series):
            raise ModuleError(f"column '{name}' is not numeric")
        values = series.to_numpy(dtype="float64", na_value=np.nan)
        values = np.where(np.isinf(values), np.nan, values)
        if keep:
            self.columns[name] = values
        return values

    def pattern(self, pattern: str) -> list:
        """The labels of the columns whose name matches ``pattern``."""
        if self.labels is None:
            self.labels = [(str(c), c) for c in self.df.columns]
        matches = _glob(pattern)
        found = [label for text, label in self.labels if matches(text)]
        if not found:
            raise ModuleError(f"no column matches '{pattern}'")
        return found

    def evaluate(self, node, depth=0):
        if depth > MAX_DEPTH:
            raise ModuleError("the expression is nested too deeply")
        depth += 1
        if isinstance(node, ast.Constant):
            return self.number(node)
        if isinstance(node, ast.Name):
            return self.name(node.id)
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = self.evaluate(node.left, depth), self.evaluate(node.right, depth)
            return self.finite(_BINARY[type(node.op)](left, right))
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitAnd, ast.BitOr)):
            left = _truth(self.evaluate(node.left, depth))
            right = _truth(self.evaluate(node.right, depth))
            return _flag(left & right if isinstance(node.op, ast.BitAnd) else left | right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = self.evaluate(node.operand, depth)
            return np.negative(value) if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
            return _flag(~_truth(self.evaluate(node.operand, depth)))
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or type(node.ops[0]) not in _COMPARE:
                raise ModuleError(
                    "compare two values at a time with == != < <= > >=, and put each"
                    " comparison in parentheses before joining it with & or |"
                )
            left = self.evaluate(node.left, depth)
            right = self.evaluate(node.comparators[0], depth)
            return _flag(_COMPARE[type(node.ops[0])](left, right))
        if isinstance(node, ast.Call):
            return self.call(node, depth)
        raise ModuleError(f"not allowed in an expression: {_describe(node)}")

    def number(self, node: ast.Constant):
        value = node.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ModuleError(
                "only numbers can be written in an expression; write a column name with"
                ' spaces or symbols as col("name")'
            )
        try:
            number = float(value)
        except OverflowError:
            number = np.inf
        if not np.isfinite(number):
            raise ModuleError("the number is too large")
        return np.float64(number)

    def name(self, name: str):
        if name in self.df.columns:
            return self.column(name)
        # Python reads a name as NFKC (a full-width digit is a digit): so does a column's name
        if self.same_text is None:
            self.same_text = {}
            for c in self.df.columns:
                self.same_text.setdefault(unicodedata.normalize("NFKC", str(c)), []).append(c)
        same = self.same_text.get(name, [])
        if len(same) == 1:
            return self.column(same[0])
        if name == "nan":
            return np.float64("nan")
        raise ModuleError(
            f"unknown column '{name}'; write a column name with spaces or symbols as"
            f' col("{name}")'
        )

    def call(self, node: ast.Call, depth: int):
        if not isinstance(node.func, ast.Name):
            raise ModuleError(f"not allowed in an expression: {_describe(node.func)}")
        name = node.func.id
        if name not in FUNCTIONS:
            raise ModuleError(f"unknown function '{name}'; use one of: {', '.join(FUNCTIONS)}")
        if node.keywords:
            raise ModuleError(f"{name}() takes no named arguments")
        args = node.args
        if name == "col":
            return self.column(self.text(name, args))
        if name in _ROW_FUNCTIONS:
            return self.row_function(name, args, depth)
        count = {"where": 3, "clip": 3, "isnull": 1}.get(name, 2 if name in _TWO_FUNCTIONS else 1)
        if len(args) != count:
            raise ModuleError(f"{name}() takes {count} argument{'s' * (count != 1)}")
        values = [self.evaluate(arg, depth) for arg in args]
        if name in _UNARY_FUNCTIONS:
            return self.finite(_UNARY_FUNCTIONS[name](values[0]))
        if name in _TWO_FUNCTIONS:
            return _TWO_FUNCTIONS[name](*values)
        if name == "isnull":
            return _flag(np.isnan(values[0]))
        if name == "where":
            return np.where(_truth(values[0]), values[1], values[2])
        return self.finite(np.clip(values[0], values[1], values[2]))

    @staticmethod
    def text(function: str, args: list) -> str:
        if len(args) != 1 or not (
            isinstance(args[0], ast.Constant) and isinstance(args[0].value, str)
        ):
            raise ModuleError(f'{function}() takes one name in quotes, such as {function}("a b")')
        return args[0].value

    def row_function(self, name: str, args: list, depth: int):
        """The sum, mean or count of the values that are not empty in each row, over the columns
        matching the patterns (text in quotes, with ``*``) and the values of the other arguments.
        What it reads is counted before any is read, and a column of a pattern is not kept."""
        if not args:
            raise ModuleError(f"{name}() needs at least one argument")
        sources: list = []  # a column's label, or the node of a value to compute
        read: set = set()  # the columns of the patterns, each once however many patterns match it
        patterns: set[str] = set()
        for arg in args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value in patterns:
                    continue
                patterns.add(arg.value)
                sources += [c for c in self.pattern(arg.value) if c not in read and not read.add(c)]
            else:
                sources.append(arg)
            if self.operands + len(sources) > MAX_OPERANDS:  # before the next pattern is expanded
                raise ModuleError(
                    f"the expression reads more than {MAX_OPERANDS} columns and values"
                )
        self.operands += len(sources)
        try:
            check_cells(self.rows, self.operands)
        except ModuleError:
            raise ModuleError(
                f"the expression reads {self.operands} columns and values on each of {self.rows}"
                f" rows; at most {registry.MAX_OUTPUT_CELLS} are allowed"
            ) from None
        total, found = np.zeros(self.rows), np.zeros(self.rows)
        for source in sources:
            value = (
                self.column(source, keep=False)
                if not isinstance(source, ast.AST)
                else self.evaluate(source, depth)
            )
            present = ~np.isnan(value)
            total = total + np.where(present, value, 0.0)
            found = found + present
        if name == "rowcount":
            return found
        return self.finite(total if name == "rowsum" else np.divide(total, found))


def _live(node, depth: int = 0) -> int:
    """The most arrays of one value per row alive at once while ``node`` is evaluated, which
    runs the left operand and the arguments first and holds their results: it grows with how far
    the expression nests on the right, not with its length. The tree is also checked for depth
    here, before anything is computed."""
    if depth > MAX_DEPTH:
        raise ModuleError("the expression is nested too deeply")
    if isinstance(node, ast.BinOp):
        return max(_live(node.left, depth + 1), 1 + _live(node.right, depth + 1), 3)
    if isinstance(node, ast.Compare):
        return max(
            _live(node.left, depth + 1), *(1 + _live(c, depth + 1) for c in node.comparators), 3
        )
    if isinstance(node, ast.UnaryOp):
        return max(_live(node.operand, depth + 1), 2)
    if isinstance(node, ast.Call):
        arguments = [a for a in node.args if not isinstance(a, ast.Constant)]
        rows = isinstance(node.func, ast.Name) and node.func.id in _ROW_FUNCTIONS
        held = 2 if rows else 0  # the sum and the count of a row function; else earlier results
        lives = [(held if rows else i) + _live(a, depth + 1) for i, a in enumerate(arguments)]
        return max([*lives, held + 2, 0 if rows else len(arguments) + 1])
    return 1


def _describe(node) -> str:
    kinds = {
        "BinOp": "this operator (use + - * / ** & |)",
        "Attribute": "attribute access",
        "Call": "calling the result of a call",
        "Subscript": "subscript",
        "Lambda": "lambda",
        "ListComp": "comprehension",
        "SetComp": "comprehension",
        "DictComp": "comprehension",
        "GeneratorExp": "comprehension",
        "IfExp": "if/else (use where)",
        "BoolOp": "and/or (use & and |)",
        "JoinedStr": "formatted text",
        "Starred": "*",
        "NamedExpr": "assignment",
    }
    return kinds.get(type(node).__name__, type(node).__name__)


def evaluate(text: str, df: pd.DataFrame) -> tuple[np.ndarray, int]:
    """The expression ``text`` over the columns of ``df``: one float64 value per row, and the
    number of rows made empty by an infinite result (a division by zero, an overflow)."""
    if len(text) > MAX_LENGTH:
        raise ModuleError(f"the expression is longer than {MAX_LENGTH} characters")
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError as error:
        raise ModuleError(
            f"cannot read the expression: {error.msg} (write a column name that is not a plain"
            ' word, such as "class" or "1st", as col("class"))'
        ) from None
    except (ValueError, RecursionError, MemoryError):
        raise ModuleError("cannot read the expression") from None
    try:
        live = _live(tree.body)
        check_cells(len(df), len(df.columns) + 1 + live)
    except RecursionError:
        raise ModuleError("the expression is nested too deeply") from None
    except ModuleError as error:
        if "cells" not in str(error):
            raise
        raise ModuleError(
            f"the expression holds {live} columns of {len(df)} values at once; at most"
            f" {registry.MAX_OUTPUT_CELLS} cells are allowed with the dataset"
        ) from None
    evaluator = _Evaluator(df)
    try:
        with np.errstate(all="ignore"):
            result = evaluator.evaluate(tree.body)
    except RecursionError:
        raise ModuleError("the expression is nested too deeply") from None
    values = np.array(np.broadcast_to(np.asarray(result, dtype="float64"), (len(df),)))
    return values, int((evaluator.infinite & np.isnan(values)).sum())
