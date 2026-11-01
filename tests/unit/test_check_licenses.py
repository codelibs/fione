import check_licenses
import pytest
from check_licenses import classify


@pytest.mark.parametrize(
    "expr",
    [
        "Apache-2.0",
        "MIT License",
        "MIT",
        "BSD-3-Clause",
        "BSD License",
        "Apache Software License",
        "Apache 2.0",
        "ISC",
        "PSF-2.0",
        "Python Software Foundation License",
        "Apache-2.0 OR BSD-2-Clause",
        "MIT AND PSF-2.0",
        "(MIT OR Apache-2.0)",
        "Apache-2.0 OR GPL-2.0",
        "MIT OR Apache-2.0",
    ],
)
def test_allowed(expr):
    assert classify(expr) == "allowed"


@pytest.mark.parametrize(
    "expr",
    [
        "GPL-3.0",
        "GPLv3",
        "LGPL-2.1",
        "LGPL-3.0-or-later",
        "AGPL-3.0",
        "GNU General Public License v3 (GPLv3)",
        "GNU Lesser General Public License v2 (LGPLv2)",
        "CC-BY-NC-4.0",
        "Non-Commercial Use Only",
        "GPL-2.0 OR LGPL-2.1",
        "MIT AND GPL-3.0",
        "gpl-2.0 or mit",
        "GPLv2 or later",
        "GPL v3 or later",
        "GNU General Public License v2 or later",
    ],
)
def test_forbidden(expr):
    assert classify(expr) == "forbidden"


@pytest.mark.parametrize(
    "expr",
    [
        "MPL-2.0",
        "Mozilla Public License 2.0 (MPL 2.0)",
        "MPL-2.0 OR GPL-2.0",
        "MIT AND MPL-2.0",
        "Proprietary",
        "Some Custom License",
        "",
    ],
)
def test_review(expr):
    assert classify(expr) == "review"


class FakeMetadata(dict):
    def get_all(self, key, default=None):
        return self.get(key, default)


class FakeDist:
    def __init__(self, name, **fields):
        self.metadata = FakeMetadata(Name=name, **fields)
        self.version = "1.0"


def test_package_license_prefers_expression():
    dist = FakeDist("a", **{"License-Expression": "MIT", "License": "GPL-3.0"})
    assert check_licenses.package_license(dist) == "allowed"


def test_package_license_uses_license_field_and_classifiers():
    dist = FakeDist("a", License="MIT", Classifier=["License :: OSI Approved :: BSD License"])
    assert check_licenses.package_license(dist) == "allowed"


def test_package_license_forbidden_classifier_wins():
    dist = FakeDist(
        "a",
        License="MIT",
        Classifier=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        ],
    )
    assert check_licenses.package_license(dist) == "forbidden"


@pytest.mark.parametrize("field", [None, "UNKNOWN", "", "Permission is hereby granted\nfree of"])
def test_package_license_without_usable_metadata_is_review(field):
    fields = {} if field is None else {"License": field}
    assert check_licenses.package_license(FakeDist("a", **fields)) == "review"


def test_main_exit_code(monkeypatch, capsys):
    dists = [FakeDist("ok", License="MIT"), FakeDist("bad", License="GPL-3.0")]
    monkeypatch.setattr(check_licenses, "installed_distributions", lambda: dists)
    assert check_licenses.main() == 1
    out = capsys.readouterr().out
    assert "bad" in out and "forbidden" in out


def test_main_review_does_not_fail(monkeypatch, capsys):
    dists = [FakeDist("ok", License="MIT"), FakeDist("odd", License="MPL-2.0")]
    monkeypatch.setattr(check_licenses, "installed_distributions", lambda: dists)
    assert check_licenses.main() == 0
    assert "review" in capsys.readouterr().out


def test_exception_overrides_forbidden(monkeypatch, capsys):
    dists = [FakeDist("Bad_Pkg", License="GPL-3.0")]
    monkeypatch.setattr(check_licenses, "installed_distributions", lambda: dists)
    monkeypatch.setattr(check_licenses, "EXCEPTIONS", {"bad-pkg": "dev-only tool, not shipped"})
    assert check_licenses.main() == 0
    assert "dev-only tool, not shipped" in capsys.readouterr().out


def test_tqdm_is_allowed_by_exception(monkeypatch, capsys):
    dists = [FakeDist("tqdm", **{"License-Expression": "MPL-2.0 AND MIT"})]
    monkeypatch.setattr(check_licenses, "installed_distributions", lambda: dists)
    assert check_licenses.main() == 0
    out = capsys.readouterr().out
    assert out.startswith("allowed") and "weak file-level copyleft" in out


def test_certifi_is_an_exception(monkeypatch, capsys):
    dists = [FakeDist("certifi", **{"License-Expression": "MPL-2.0"})]
    monkeypatch.setattr(check_licenses, "installed_distributions", lambda: dists)
    assert check_licenses.main() == 0
    out = capsys.readouterr().out
    assert out.startswith("allowed") and "(exception: MPL-2.0" in out
