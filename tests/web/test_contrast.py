"""WCAG AA contrast of the design tokens, in the light and the dark theme: 4.5:1 for text,
3:1 for input borders, the focus ring and coloured controls against their surroundings."""

import re
from pathlib import Path

import pytest

import fione.web

TOKENS = Path(fione.web.__file__).parent / "static" / "css" / "tokens.css"

PAIRS = [
    *[(fg, bg, 4.5) for fg in ("text", "text-muted") for bg in ("bg", "surface", "surface-2")],
    ("link", "bg", 4.5),
    ("link", "surface", 4.5),
    ("on-primary", "primary", 4.5),
    ("on-primary", "primary-hover", 4.5),
    ("on-danger", "danger", 4.5),
    ("on-danger", "danger-hover", 4.5),
    ("info-text", "info-subtle", 4.5),
    ("info-text", "surface-2", 4.5),
    ("success-text", "success-subtle", 4.5),
    ("warning-text", "warning-subtle", 4.5),
    ("danger-text", "danger-subtle", 4.5),
    ("danger-text", "surface", 4.5),
    ("neutral-text", "neutral-subtle", 4.5),
    *[("border-strong", bg, 3.0) for bg in ("bg", "surface", "surface-2")],
    *[("focus", bg, 3.0) for bg in ("bg", "surface", "surface-2")],
    ("primary", "surface", 3.0),
    ("danger", "surface", 3.0),
]


def tokens() -> dict[str, tuple[str, str]]:
    css = TOKENS.read_text(encoding="utf-8")
    pairs = r"--color-([\w-]+): light-dark\((#[0-9a-f]{6}), (#[0-9a-f]{6})\)"
    found = {name: (light, dark) for name, light, dark in re.findall(pairs, css)}
    for name, ref in re.findall(r"--color-([\w-]+): var\(--color-([\w-]+)\);", css):
        found[name] = found[ref]
    return found


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("theme", [0, 1], ids=["light", "dark"])
@pytest.mark.parametrize("fg,bg,minimum", PAIRS)
def test_contrast(fg, bg, minimum, theme):
    colours = tokens()
    ratio = contrast(colours[fg][theme], colours[bg][theme])
    assert ratio >= minimum, f"--color-{fg} on --color-{bg}: {ratio:.2f}"
