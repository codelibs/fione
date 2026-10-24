import re

from fione.version import __version__


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+(\.dev\d+)?", __version__)
