import httpx
import numpy as np
import pandas as pd
import pytest
from fione_sdk import Client, FioneError

from api_helpers import add_user, bearer
from fione.auth.roles import Role


def _token_of(api, user_id) -> str:
    return bearer(api, user_id)["Authorization"].removeprefix("Bearer ")


FRAME = pd.DataFrame({"数値": [1.5, np.nan, 3.0], "name": ["a", "b", "c"], "n": [1, 2, 3]})


def test_upload_then_read_round_trips_a_frame(sdk):
    project = sdk.create_project("p")
    dataset = sdk.upload(project["id"], FRAME, "frame")
    assert dataset["name"] == "frame" and dataset["type"] == "train"
    pd.testing.assert_frame_equal(sdk.read(project["id"], dataset["id"]), FRAME, check_dtype=False)


def test_errors_carry_status_and_code(api, sdk):
    with pytest.raises(FioneError) as missing:
        sdk.project("missing")
    assert missing.value.status == 404
    assert missing.value.code and missing.value.message

    project = sdk.create_project("shared")
    viewer = add_user(api, "viewer", Role.VIEWER)
    sdk._request(
        "POST", f"/projects/{project['id']}/share", json={"username": "viewer", "access": "viewer"}
    )
    reader = Client(token=_token_of(api, viewer.id), http=api)
    with pytest.raises(FioneError) as denied:
        reader.upload(project["id"], FRAME, "nope")
    assert denied.value.status == 403


def test_env_configures_the_client(api, monkeypatch):
    token = _token_of(api, add_user(api, "envuser").id)
    monkeypatch.setenv("FIONE_TOKEN", token)
    monkeypatch.delenv("FIONE_URL", raising=False)
    assert Client(http=api).projects() == []

    monkeypatch.delenv("FIONE_TOKEN")
    with pytest.raises(FioneError) as err:
        Client(http=api)
    assert err.value.code == "config"


def test_url_is_required_without_http(monkeypatch):
    monkeypatch.delenv("FIONE_URL", raising=False)
    with pytest.raises(FioneError) as err:
        Client(token="t")
    assert err.value.code == "config"


def test_url_and_timeout_come_from_the_environment_and_arguments(monkeypatch):
    monkeypatch.setenv("FIONE_URL", "http://fione.test")
    monkeypatch.setenv("FIONE_TOKEN", "t")
    own = Client()
    assert str(own.http.base_url) == "http://fione.test"
    assert own.http.timeout == httpx.Timeout(60.0)
    assert Client(url="http://other.test", timeout=5).http.timeout == httpx.Timeout(5.0)
