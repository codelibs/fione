import pandas as pd
import pytest
from fione_sdk import FioneError


@pytest.fixture(params=["full", "notebook"])
def fione(request):
    """A client with a full token and one with a notebook token: both reach every call."""
    return request.getfixturevalue("sdk" if request.param == "full" else "notebook_sdk")


@pytest.fixture
def dataset(fione):
    frame = pd.DataFrame({"a/b": [1.0, 2.0, 3.0], "c": ["x", "y", "x"]})
    project = fione.create_project("p")
    return project["id"], fione.upload(project["id"], frame, "frame", type="test")


def test_lists_and_gets_datasets(fione, dataset):
    pid, ds = dataset
    assert [d["id"] for d in fione.datasets(pid)] == [ds["id"]]
    assert fione.dataset(pid, ds["id"])["type"] == "test"
    assert [p["id"] for p in fione.projects()] == [pid]
    assert fione.project(pid)["name"] == "p"


def test_preview_and_profile(fione, dataset):
    pid, ds = dataset
    preview = fione.preview(pid, ds["id"], rows=2)
    assert preview["columns"] == ["a/b", "c"] and len(preview["rows"]) == 2
    assert fione.profile(pid, ds["id"])["columns"]


def test_column_name_with_slash_is_quoted(fione, dataset):
    pid, ds = dataset
    assert fione.column_profile(pid, ds["id"], "a/b")["name"] == "a/b"


def test_delete_dataset(fione, dataset):
    pid, ds = dataset
    assert fione.delete_dataset(pid, ds["id"]) is None
    with pytest.raises(FioneError) as err:
        fione.dataset(pid, ds["id"])
    assert err.value.status == 404
