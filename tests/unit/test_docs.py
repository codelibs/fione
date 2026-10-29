"""The user documentation stays true to the code: every setting is documented (and nothing
else), every relative link resolves, and nothing private leaks into a public page."""

import re
from pathlib import Path

import pytest

from fione.config import Settings

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DOC = ROOT / "docs" / "configuration.md"
PAGES = sorted([ROOT / "README.md", *(ROOT / "docs").glob("*.md")])
NAME = re.compile(r"FIONE_[A-Z0-9_]*[A-Z0-9]")


def _section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}\n")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def _table_names(section: str) -> set[str]:
    return set(re.findall(r"^\| `(FIONE_[A-Z0-9_]+)`", section, re.M))


def _names_in(path: Path, pattern: str) -> set[str]:
    return set(re.findall(pattern, path.read_text()))


def test_docs_list_every_setting_and_only_those():
    settings = {f"FIONE_{name.upper()}" for name in Settings.model_fields}
    documented = _table_names(_section(CONFIG_DOC.read_text(), "Fione settings"))
    assert documented == settings


def test_docs_list_every_compose_and_serving_variable():
    text = CONFIG_DOC.read_text()
    compose = _names_in(ROOT / "docker" / "compose.yaml", r"\$\{(FIONE_[A-Z0-9_]+)")
    compose |= _names_in(ROOT / "docker" / ".env.example", r"(?m)^#? ?(FIONE_[A-Z0-9_]+)=")
    assert _table_names(_section(text, "Compose variables (`docker/.env`)")) == compose
    serving = set()
    for source in (ROOT / "src" / "fione_serving").glob("*.py"):
        serving |= _names_in(source, r"\"(FIONE_[A-Z0-9_]+)\"")
    assert _table_names(_section(text, "Fione Serving")) == serving


def test_docs_name_no_setting_that_does_not_exist():
    known = {f"FIONE_{name.upper()}" for name in Settings.model_fields}
    known |= _names_in(ROOT / "docker" / "compose.yaml", r"\$\{(FIONE_[A-Z0-9_]+)")
    known |= _names_in(ROOT / "docker" / ".env.example", r"(FIONE_[A-Z0-9_]+)=")
    for source in [
        *(ROOT / "src" / "fione_serving").glob("*.py"),
        *(ROOT / "src" / "fione" / "jobs").glob("*.py"),
    ]:
        known |= _names_in(source, r"\"(FIONE_[A-Z0-9_]+)\"")
    for page in PAGES:
        unknown = set(NAME.findall(page.read_text())) - known
        assert not unknown, (page.name, unknown)


def _slug(heading: str) -> str:
    """GitHub's anchor of a heading."""
    text = re.sub(r"[`*_]", "", heading.strip().lower())
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def _anchors(page: Path) -> set[str]:
    text = re.sub(r"```.*?```", "", page.read_text(), flags=re.S)
    return {_slug(h) for h in re.findall(r"^#{1,6} (.+)$", text, re.M)}


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_docs_links_resolve(page):
    text = re.sub(r"```.*?```", "", page.read_text(), flags=re.S)
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"[a-z]+:", target):
            continue  # http(s), mailto
        path, _, anchor = target.partition("#")
        assert "superpowers" not in path, (page.name, target)
        resolved = (page.parent / path).resolve() if path else page
        assert resolved.exists(), (page.name, target)
        if anchor and resolved.suffix == ".md":
            assert anchor in _anchors(resolved), (page.name, target)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_docs_hold_nothing_private(page):
    text = page.read_text()
    for pattern in (r"/Users/", r"/home/\w", r"claude-\d", r"\.superpowers", r"claude\.ai"):
        assert not re.search(pattern, text), (page.name, pattern)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", text), page.name  # no e-mail address
    assert not re.search(r"!\[[^\]]*\]\([^)]*\.(png|jpe?g|gif|webp)\)", text), page.name
