import tomllib
from pathlib import Path

import fione_sdk

from fione.version import __version__


def test_sdk_version_matches_fione():
    assert fione_sdk.__version__ == __version__
    pyproject = Path(__file__).resolve().parents[2] / "sdk" / "pyproject.toml"
    assert tomllib.loads(pyproject.read_text())["project"]["version"] == __version__
