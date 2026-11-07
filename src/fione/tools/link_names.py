"""Whether the names of two columns of two tables may name the same key.

A person who joins tables looks at the names first: the same name, the id of a table named for
it (``customers.id`` and ``orders.customer_id``), then names that differ in a word or two
(``cust_id`` and ``customer_id``). The values decide afterwards; these rules only say which
pairs of columns are worth comparing.
"""

import difflib
import re

SAME_NAME = "same_name"
TABLE_ID = "table_id"
SIMILAR_NAME = "similar_name"
VALUES = "values"  # no name relates the columns; their values do

# ``id`` is a key anywhere in a name (SK_ID_CURR); the others only as the last word, so that
# ``order_number`` is a key and ``number_of_items`` is not
_ID_WORD = "id"
_LAST_ID_WORDS = frozenset({"nbr", "number", "no", "key", "code", "uid", "ref"})
_SIMILAR_RATIO = 0.75
_MIN_ABBREVIATION = 3


def _words(name: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [w for w in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if w]


def _singular(word: str) -> str:
    if word.endswith("ies"):
        return word[:-3] + "y"
    return word[:-1] if word.endswith("s") and not word.endswith("ss") else word


def is_id_like(column: str) -> bool:
    """The name has the word id, or ends in a word such as key, number or code."""
    words = _words(column)
    return _ID_WORD in words or bool(words) and words[-1] in _LAST_ID_WORDS


def _stem(column: str) -> list[str]:
    """The words of the name less the id words and plurals: ``SK_ID_CURR`` gives sk, curr."""
    words = _words(column)
    if words and words[-1] in _LAST_ID_WORDS:
        words = words[:-1]
    return [w for w in map(_singular, words) if w != _ID_WORD]


def related(table_a: str, column_a: str, table_b: str, column_b: str) -> str | None:
    """How the two columns are related by name, or None. Only id-like columns are compared:
    the other names are too common (``MONTHS_BALANCE``, ``CNT_INSTALMENT``) to say anything."""
    if column_a.lower() == column_b.lower():
        return SAME_NAME
    if not (is_id_like(column_a) and is_id_like(column_b)):
        return None
    stem_a, stem_b = _stem(column_a), _stem(column_b)
    for bare, other, table in ((stem_a, stem_b, table_a), (stem_b, stem_a, table_b)):
        if not bare and other and other == [_singular(w) for w in _words(_table_name(table))]:
            return TABLE_ID  # ``id`` of a table and ``<table>_id`` elsewhere
    if not (stem_a and stem_b):
        return None
    if set(stem_a) <= set(stem_b) or set(stem_b) <= set(stem_a):
        return SIMILAR_NAME
    joined_a, joined_b = "".join(stem_a), "".join(stem_b)
    short, long = sorted((joined_a, joined_b), key=len)
    if len(short) >= _MIN_ABBREVIATION and long.startswith(short):
        return SIMILAR_NAME  # an abbreviation: cust and customer
    ratio = difflib.SequenceMatcher(None, joined_a, joined_b).ratio()
    return SIMILAR_NAME if ratio >= _SIMILAR_RATIO else None


def _table_name(name: str) -> str:
    return re.sub(r"\.\w{1,5}$", "", name)  # a file extension is not a word of the name
