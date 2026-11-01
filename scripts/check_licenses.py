"""Check the licenses of installed Python dependencies (stdlib only).

Policy (design spec 4.6): Apache-2.0, MIT, BSD, ISC and PSF are allowed;
GPL/LGPL/AGPL and non-commercial licenses are forbidden; anything else
(MPL, custom or unrecognised strings) needs a manual review.

Exit code is 1 if any installed package is forbidden and not in EXCEPTIONS.
"""

import re
import sys
from importlib import metadata
from typing import Literal

Verdict = Literal["allowed", "forbidden", "review"]

# Package (normalized name) -> reason why its verdict is overridden to "allowed".
EXCEPTIONS: dict[str, str] = {
    # MPL-2.0 AND MIT, a transitive dependency of optuna.
    "tqdm": "weak file-level copyleft; unmodified library use is compatible with Apache-2.0",
    "certifi": "MPL-2.0 CA bundle, unmodified, via httpx",
}

_ALLOWED = re.compile(r"\b(apache|mit|bsd|0bsd|isc|psf|python software foundation)\b")
_FORBIDDEN = re.compile(
    r"(?<![a-z])[al]?gpl|general public license|non-?commercial|(?<![a-z])cc-by-nc"
)
# SPDX operators are uppercase; lowercase "or later" etc. is free text.
_TOKEN = re.compile(r"\s+(AND|OR)\s+|([()])")
_SEVERITY = {"allowed": 0, "review": 1, "forbidden": 2}


def _term(text: str) -> Verdict:
    text = text.lower()
    if _FORBIDDEN.search(text):
        return "forbidden"
    if _ALLOWED.search(text):
        return "allowed"
    return "review"


def _both(verdicts: list[Verdict]) -> Verdict:
    """AND: the worst verdict wins."""
    return max(verdicts, key=_SEVERITY.__getitem__)


def _either(verdicts: list[Verdict]) -> Verdict:
    """OR: the best verdict wins (any permitted alternative is enough)."""
    return min(verdicts, key=_SEVERITY.__getitem__)


class _Parser:
    """SPDX-like expressions: terms joined by AND / OR, with parentheses."""

    def __init__(self, expr: str):
        parts = [p.strip() for p in _TOKEN.split(expr) if p and p.strip()]
        self.tokens = parts
        self.pos = 0

    def _peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self) -> str:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def parse(self) -> Verdict:
        verdict = self._or()
        if self._peek() is not None:
            raise ValueError(f"unexpected token: {self._peek()}")
        return verdict

    def _or(self) -> Verdict:
        verdicts = [self._and()]
        while self._peek() == "OR":
            self._next()
            verdicts.append(self._and())
        return _either(verdicts)

    def _and(self) -> Verdict:
        verdicts = [self._atom()]
        while self._peek() == "AND":
            self._next()
            verdicts.append(self._atom())
        return _both(verdicts)

    def _atom(self) -> Verdict:
        if self._peek() is None:
            raise ValueError("unexpected end of expression")
        token = self._next()
        if token == "(":
            verdict = self._or()
            if self._peek() != ")":
                raise ValueError("missing ')'")
            self._next()
            return verdict
        if token in (")", "AND", "OR"):
            raise ValueError(f"unexpected token: {token}")
        return _term(token)


def classify(license_expr: str) -> Verdict:
    """Classify a license string. Unknown or malformed input is never "allowed"."""
    expr = license_expr.strip()
    if not expr:
        return "review"
    if not re.search(r"\s(AND|OR)\s", expr):
        # Free text such as "GNU ... License v3 (GPLv3)": parentheses are not grouping.
        return _term(expr)
    try:
        return _Parser(expr).parse()
    except ValueError:
        return "forbidden" if _FORBIDDEN.search(expr.lower()) else "review"


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _license_strings(dist: metadata.Distribution) -> list[str]:
    meta = dist.metadata
    expression = (meta.get("License-Expression") or "").strip()
    if expression:
        return [expression]
    strings = []
    field = (meta.get("License") or "").strip()
    # Some packages put the whole license text in this field; only short values are names.
    if field and field.upper() != "UNKNOWN" and "\n" not in field and len(field) <= 200:
        strings.append(field)
    for classifier in meta.get_all("Classifier") or []:
        if classifier.startswith("License ::"):
            strings.append(classifier.rsplit("::", 1)[-1].strip())
    return strings


def package_license(dist: metadata.Distribution) -> Verdict:
    """Verdict for one package; when several sources disagree the worst one wins."""
    verdicts = [classify(s) for s in _license_strings(dist)]
    return _both(verdicts) if verdicts else "review"


def installed_distributions() -> list[metadata.Distribution]:
    unique = {}
    for dist in metadata.distributions():
        unique.setdefault(_normalize(dist.metadata["Name"]), dist)
    return sorted(unique.values(), key=lambda d: _normalize(d.metadata["Name"]))


def main() -> int:
    failed = False
    dists = installed_distributions()
    for dist in dists:
        name = dist.metadata["Name"]
        verdict = package_license(dist)
        note = ""
        reason = EXCEPTIONS.get(_normalize(name))
        if reason is not None and verdict != "allowed":
            note = f"  (exception: {reason})"
            verdict = "allowed"
        elif verdict == "forbidden":
            failed = True
        licenses = "; ".join(_license_strings(dist)) or "-"
        print(f"{verdict:<9} {name} {dist.version}: {licenses}{note}")
    if failed:
        print("Forbidden licenses found; replace the dependency or add an EXCEPTIONS entry.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
