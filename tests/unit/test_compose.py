"""docker/compose.yaml keeps the notebook topology: who shares which network, who holds the
Docker socket, what is published, and that the notebook services stay in their profile."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker" / "compose.yaml").read_text())
SERVICES = COMPOSE["services"]
GATEWAY_CONF = (ROOT / "docker" / "notebook-gateway.conf").read_text()
NOTEBOOK_SERVICES = {"notebook-gateway", "notebook-launcher", "notebook-image"}


def _networks(service: dict) -> set[str]:
    networks = service.get("networks", [])
    return set(networks if isinstance(networks, list) else networks.keys())


def _values(node) -> list[str]:
    if isinstance(node, dict):
        return [v for key, value in node.items() for v in (str(key), *_values(value))]
    if isinstance(node, list):
        return [v for value in node for v in _values(value)]
    return [str(node)]


def test_network_membership():
    assert _networks(SERVICES["fione"]) == {"backend", "gateway", "launcher"}
    assert _networks(SERVICES["notebook-gateway"]) == {"gateway", "notebooks"}
    assert _networks(SERVICES["notebook-launcher"]) == {"launcher"}
    image = SERVICES["notebook-image"]
    assert image["network_mode"] == "none" and not _networks(image)
    members = {name for name, s in SERVICES.items() if "notebooks" in _networks(s)}
    assert members == {"notebook-gateway"}
    networks = COMPOSE["networks"]
    assert networks["notebooks"]["internal"] is True
    assert networks["launcher"]["internal"] is True
    assert not (networks["gateway"] or {}).get("internal")


def test_only_the_launcher_mounts_the_socket():
    mounting = {
        name
        for name, service in SERVICES.items()
        if any("docker.sock" in volume for volume in _values(service.get("volumes", [])))
    }
    assert mounting == {"notebook-launcher"}


def test_launcher_publishes_nothing_and_gateway_binds_localhost():
    launcher = SERVICES["notebook-launcher"]
    assert "ports" not in launcher and "expose" not in launcher
    assert "hostname" not in launcher  # it finds its own container by the default hostname
    assert launcher["cap_drop"] == ["ALL"]
    assert launcher["security_opt"] == ["no-new-privileges:true"]
    assert launcher["read_only"] is True
    gateway = SERVICES["notebook-gateway"]
    assert gateway["ports"] == ["127.0.0.1:${FIONE_NOTEBOOK_PORT:-8888}:8080"]
    assert gateway["cap_drop"] == ["ALL"] and gateway["read_only"] is True
    assert gateway["security_opt"] == ["no-new-privileges:true"]
    assert "./notebook-gateway.conf:/etc/nginx/conf.d/default.conf:ro" in gateway["volumes"]
    assert re.fullmatch(r"nginxinc/nginx-unprivileged:\d+\.\d+\.\d+-alpine", gateway["image"])


def test_notebook_services_are_in_the_profile():
    for name, service in SERVICES.items():
        if name in NOTEBOOK_SERVICES:
            assert service["profiles"] == ["notebook"], name
        else:
            assert "notebook" not in service.get("profiles", []), name
    assert SERVICES["notebook-image"]["scale"] == 0
    launcher_env = SERVICES["notebook-launcher"]["environment"]
    assert launcher_env["FIONE_NOTEBOOK_IMAGE"] == SERVICES["notebook-image"]["image"]
    # Set in docker/.env like the other notebook values; the launcher's own default otherwise.
    assert launcher_env["FIONE_NOTEBOOK_MAX_RUNNING"] == "${FIONE_NOTEBOOK_MAX_RUNNING:-4}"


def test_no_required_interpolation_in_profile_services():
    # Compose interpolates every service, profile or not: a `:?` would stop the default stack.
    for name in NOTEBOOK_SERVICES:
        for value in _values(SERVICES[name]):
            assert ":?" not in value, (name, value)
    fione_env = SERVICES["fione"]["environment"]
    for key in ("FIONE_PUBLIC_URL", "FIONE_NOTEBOOK_URL", "FIONE_NOTEBOOK_LAUNCHER_SECRET"):
        assert fione_env[key] == f"${{{key}:-}}"
    assert fione_env["FIONE_NOTEBOOK_MAX_LIFETIME_SECS"] == (
        "${FIONE_NOTEBOOK_MAX_LIFETIME_SECS:-43200}"
    )
    assert fione_env["FIONE_NOTEBOOK_LAUNCHER_URL"] == "http://notebook-launcher:8000"


def test_gateway_conf_has_no_query_in_logs():
    formats = [line for line in GATEWAY_CONF.splitlines() if line.startswith("log_format")]
    assert formats
    for line in formats:
        for variable in ("$request ", '$request"', "$request'", "$args", "$request_uri"):
            assert variable not in line, line
        assert "$http_referer" not in line
    # Every server logs with that format, never the image's default (which has $request).
    servers = GATEWAY_CONF.count("\nserver {")
    assert GATEWAY_CONF.count("access_log /dev/stdout fione_gateway;") == servers == 2


def test_both_gateway_servers_proxy_with_http_1_1():
    # The public server for WebSockets, the relay for streamed (unbuffered, chunked) uploads.
    relay = GATEWAY_CONF[GATEWAY_CONF.index("listen 8081;") :]
    public = GATEWAY_CONF[GATEWAY_CONF.index("listen 8080;") : GATEWAY_CONF.index("listen 8081;")]
    assert "proxy_http_version 1.1;" in public
    location = relay[relay.index("location /api/v1/ {") :]
    location = location[: location.index("\n    }")]
    assert "proxy_http_version 1.1;" in location and "proxy_request_buffering off;" in location
