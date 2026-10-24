"""UI strings in English and Japanese, and the choice of language for a request.

Catalogs are flat JSON objects (``en.json``, ``ja.json``) of plain text: templates escape
them, so they hold no HTML. ``t`` never raises: a key missing in Japanese falls back to
English, a key missing everywhere is shown as itself, and a translation whose placeholders
do not match the given variables is shown unformatted.
"""

import json
from functools import cache
from importlib import resources

LANGUAGES = ("en", "ja")
DEFAULT_LANGUAGE = "en"
LANG_COOKIE = "fione_lang"


@cache
def catalog(lang: str) -> dict[str, str]:
    text = resources.files(__package__).joinpath(f"{lang}.json").read_text(encoding="utf-8")
    return json.loads(text)


def t(key: str, lang: str, **vars: object) -> str:
    text = catalog(lang).get(key) if lang in LANGUAGES else None
    if text is None:
        text = catalog(DEFAULT_LANGUAGE).get(key, key)
    if not vars:
        return text
    try:
        return text.format(**vars)
    except (KeyError, IndexError, ValueError):
        return text


def _quality(params: list[str]) -> float:
    for param in params:
        name, _, value = param.partition("=")
        if name.strip().lower() == "q":
            try:
                q = float(value)
            except ValueError:
                return 0.0
            return q if 0.0 <= q <= 1.0 else 0.0
    return 1.0


def parse_accept_language(header: str | None) -> str | None:
    """The supported language the ``Accept-Language`` header prefers most (``ja-JP``
    counts as ``ja``; ``q=0`` and malformed q-values exclude a range), else None."""
    best, best_q = None, 0.0
    for item in (header or "").split(",")[:32]:
        tag, *params = item.split(";")
        primary = tag.strip().lower().split("-")[0]
        if primary not in LANGUAGES:
            continue
        q = _quality(params)
        if q > best_q:  # ties keep the earlier range, as the header lists them
            best, best_q = primary, q
    return best


def resolve_language(cookie: str | None, accept_language: str | None) -> str:
    """The ``fione_lang`` cookie if it names a supported language, then the header."""
    if cookie in LANGUAGES:
        return cookie
    return parse_accept_language(accept_language) or DEFAULT_LANGUAGE
