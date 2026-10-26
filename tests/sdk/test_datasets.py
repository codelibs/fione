import pandas as pd
import pytest
from fione_sdk import FioneError


@pytest.fixture
def dataset(sdk):
    frame = pd.DataFrame({"a/b": [1.0, 2.0, 3.0], "c": ["x", "y", "x"]})
    project = sdk.create_project("p")
    return project["id"], sdk.upload(project["id"], frame, "frame", type="test")


def test_lists_and_gets_datasets(sdk, dataset):
    pid, ds = dataset
    assert [d["id"] for d in sdk.datasets(pid)] == [ds["id"]]
    assert sdk.dataset(pid, ds["id"])["type"] == "test"
    assert [p["id"] for p in sdk.projects()] == [pid]
    assert sdk.project(pid)["name"] == "p"


def test_preview_and_profile(sdk, dataset):
    pid, ds = dataset
    preview = sdk.preview(pid, ds["id"], rows=2)
    assert preview["columns"] == ["a/b", "c"] and len(preview["rows"]) == 2
    assert sdk.profile(pid, ds["id"])["columns"]


def test_column_name_with_slash_is_quoted(sdk, dataset):
    pid, ds = dataset
    assert sdk.column_profile(pid, ds["id"], "a/b")["name"] == "a/b"


def test_delete_dataset(sdk, dataset):
    pid, ds = dataset
    assert sdk.delete_dataset(pid, ds["id"]) is None
    with pytest.raises(FioneError) as err:
        sdk.dataset(pid, ds["id"])
    assert err.value.status == 404
