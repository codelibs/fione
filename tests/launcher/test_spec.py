"""The launcher's configuration and the fixed container spec it creates notebooks with."""

import time

import pytest

from fione_launcher.config import LauncherConfig
from fione_launcher.spec import InvalidRequest, StartRequest, container_body, valid_uid
from launcher_helpers import IMAGE, SECRET, make_config, start_request


def test_container_body_is_exactly_the_fixed_spec():
    expires = int(time.time()) + 3600
    req = StartRequest.parse(start_request(expires_at=expires), now=time.time())
    body = container_body(
        make_config(), project="fione", network="fione_notebooks", uid="7", req=req
    )
    expected_host_config = {
        "NanoCpus": 2_000_000_000,
        "Memory": 4294967296,
        "MemorySwap": 4294967296,
        "PidsLimit": 512,
        "CapDrop": ["ALL"],
        "SecurityOpt": ["no-new-privileges:true"],
        "AutoRemove": True,
        "Init": True,
        "NetworkMode": "fione_notebooks",
        "Mounts": [
            {"Type": "volume", "Source": "fione-nb-home-7", "Target": "/home/nb/work"},
        ],
    }
    assert body == {
        "Image": IMAGE,
        "User": "1000:1000",
        "Env": [
            "FIONE_NB_OWNER=7",
            f"FIONE_NB_KEY={'a' * 64}",
            f"FIONE_NB_COOKIE_SECRET={'b' * 64}",
            "FIONE_NB_ORIGIN=http://127.0.0.1:8080",
            f"FIONE_NB_EXPIRES={expires}",
            "FIONE_URL=http://notebook-gateway:8081",
            f"FIONE_TOKEN=fione_{'T' * 40}",
        ],
        "Labels": {
            "fione.notebook": "1",
            "fione.project": "fione",
            "fione.uid": "7",
            "fione.expires": str(expires),
        },
        "HostConfig": expected_host_config,
        "NetworkingConfig": {"EndpointsConfig": {"fione_notebooks": {"Aliases": ["nb-7"]}}},
    }
    assert set(body["HostConfig"]) == set(expected_host_config)
    for key in ("Binds", "Privileged", "PortBindings", "CapAdd", "Devices", "PublishAllPorts"):
        assert key not in body["HostConfig"] and key not in body


def test_container_body_takes_the_image_from_the_configuration():
    req = StartRequest.parse(start_request(), now=time.time())
    cfg = make_config(FIONE_NOTEBOOK_IMAGE="registry.example/nb:1")
    body = container_body(cfg, project="p", network="p_notebooks", uid="9", req=req)
    assert body["Image"] == "registry.example/nb:1"


def test_start_request_repr_holds_no_secrets():
    req = StartRequest.parse(start_request(), now=time.time())
    text = repr(req)
    assert "a" * 64 not in text and "b" * 64 not in text and "T" * 40 not in text


@pytest.mark.parametrize("value", ["1", "7", "123456789012345678"])
def test_valid_uid(value):
    assert valid_uid(value)


@pytest.mark.parametrize("value", ["", "0", "07", "1a", "-1", "1\n", "1234567890123456789"])
def test_invalid_uid(value):
    assert not valid_uid(value)


@pytest.mark.parametrize(
    "changes",
    [
        {"expires_at": True},
        {"expires_at": float(int(time.time()) + 60)},
        {"expires_at": str(int(time.time()) + 60)},
        {"token": 1},
        {"launch_key": None},
    ],
    ids=["bool", "float", "string", "token-not-str", "missing-key"],
)
def test_start_request_types(changes):
    with pytest.raises(InvalidRequest):
        StartRequest.parse(start_request(**changes), now=time.time())


def test_start_request_must_be_an_object():
    with pytest.raises(InvalidRequest):
        StartRequest.parse([start_request()], now=time.time())


def test_start_request_expiry_bounds():
    now = 1_800_000_000
    assert StartRequest.parse(start_request(expires_at=now + 604800), now=now)
    for expires in (now, now + 604801):
        with pytest.raises(InvalidRequest):
            StartRequest.parse(start_request(expires_at=expires), now=now)


def test_config_defaults():
    cfg = LauncherConfig.from_env({"FIONE_LAUNCHER_SECRET": SECRET, "FIONE_NOTEBOOK_IMAGE": IMAGE})
    assert cfg.secret == SECRET
    assert cfg.image == IMAGE
    assert cfg.api_url == "http://notebook-gateway:8081"
    assert cfg.max_running == 4
    assert cfg.socket_path == "/var/run/docker.sock"
    assert cfg.port == 8000
    assert SECRET not in repr(cfg)


def test_config_values():
    cfg = make_config(
        FIONE_NOTEBOOK_API_URL="https://nb.example:8443", FIONE_NOTEBOOK_MAX_RUNNING="9"
    )
    assert cfg.api_url == "https://nb.example:8443"
    assert cfg.max_running == 9


@pytest.mark.parametrize(
    ("changes", "name"),
    [
        ({"FIONE_LAUNCHER_SECRET": None}, "FIONE_LAUNCHER_SECRET"),
        ({"FIONE_LAUNCHER_SECRET": "x" * 31}, "FIONE_LAUNCHER_SECRET"),
        ({"FIONE_NOTEBOOK_IMAGE": None}, "FIONE_NOTEBOOK_IMAGE"),
        ({"FIONE_NOTEBOOK_IMAGE": "a b"}, "FIONE_NOTEBOOK_IMAGE"),
        ({"FIONE_NOTEBOOK_MAX_RUNNING": "0"}, "FIONE_NOTEBOOK_MAX_RUNNING"),
        ({"FIONE_NOTEBOOK_MAX_RUNNING": "four"}, "FIONE_NOTEBOOK_MAX_RUNNING"),
        ({"FIONE_NOTEBOOK_API_URL": "http://gw:8081\nX=1"}, "FIONE_NOTEBOOK_API_URL"),
    ],
)
def test_config_errors_exit(changes, name):
    env = {"FIONE_LAUNCHER_SECRET": SECRET, "FIONE_NOTEBOOK_IMAGE": IMAGE}
    env.update(changes)
    env = {k: v for k, v in env.items() if v is not None}
    with pytest.raises(SystemExit) as raised:
        LauncherConfig.from_env(env)
    message = str(raised.value.code)
    assert message.startswith(f"fione_launcher: {name}")
    assert "x" * 31 not in message
