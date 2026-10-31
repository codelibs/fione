"""docker/compose.yaml keeps the notebook topology: who shares which network, who holds the
Docker socket, what is published, and that the notebook services stay in their profile."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker" / "compose.yaml").read_text())
SERVICES = COMPOSE["services"]
E2E = yaml.safe_load((ROOT / "docker" / "compose.e2e.yaml").read_text())
ENV_EXAMPLE = (ROOT / "docker" / ".env.example").read_text()
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
    assert _networks(SERVICES["fione"]) == {"backend", "gateway", "launcher", "llm"}
    assert _networks(SERVICES["ollama"]) == {"llm"}  # not on backend, with the storage
    members = {name for name, s in SERVICES.items() if "llm" in _networks(s)}
    assert members == {"fione", "ollama"}
    assert not (COMPOSE["networks"]["llm"] or {}).get("internal")  # Ollama downloads models
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


def test_gateway_relay_never_forwards_mcp():
    # /mcp is served on Fione's own port only: the relay forwards /api/v1/ and answers 404 to
    # everything else, and the public server does not mention it either.
    assert "/mcp" not in GATEWAY_CONF
    relay = GATEWAY_CONF[GATEWAY_CONF.index("listen 8081;") :]
    catch_all = relay[relay.index("location / {") :]
    assert "return 404;" in catch_all[: catch_all.index("}")]


def test_ollama_is_pinned_private_and_optional():
    ollama = SERVICES["ollama"]
    assert re.fullmatch(r"ollama/ollama:\d+\.\d+\.\d+", ollama["image"])
    assert "ports" not in ollama and "expose" not in ollama
    assert ollama["profiles"] == ["ollama"]
    assert ollama["environment"]["OLLAMA_CONTEXT_LENGTH"] == "16384"
    assert "ollama" not in (SERVICES["fione"].get("depends_on") or {})


def test_fione_reaches_the_host():
    assert "host.docker.internal:host-gateway" in SERVICES["fione"]["extra_hosts"]


def test_compose_defaults_to_the_host_ollama():
    env = SERVICES["fione"]["environment"]
    assert (
        env["FIONE_LLM_BASE_URL"] == "${FIONE_LLM_BASE_URL:-http://host.docker.internal:11434/v1}"
    )
    assert env["FIONE_LLM_PROVIDER"] == "${FIONE_LLM_PROVIDER:-ollama}"
    assert env["FIONE_LLM_MODEL"] == "${FIONE_LLM_MODEL:-gemma4:12b-mlx}"
    assert env["FIONE_LLM_AUTO_PULL"] == "${FIONE_LLM_AUTO_PULL:-false}"
    assert env["FIONE_MCP_ENABLED"] == "${FIONE_MCP_ENABLED:-false}"


def test_env_example_offers_the_ollama_profile():
    block = [
        "# COMPOSE_PROFILES=ollama",
        "# FIONE_LLM_BASE_URL=http://ollama:11434/v1",
        "# FIONE_LLM_MODEL=gemma4:12b",
        "# FIONE_LLM_AUTO_PULL=true",
    ]
    lines = ENV_EXAMPLE.splitlines()
    for line in block:  # commented out: the default is the host's Ollama
        assert line in lines
    assert "# FIONE_LLM_API_KEY=" in lines and "# FIONE_MCP_ENABLED=true" in lines
    assert not [line for line in lines if re.match(r"(COMPOSE_PROFILES|FIONE_LLM|FIONE_MCP)", line)]


def test_e2e_uses_the_fake_llm():
    fake = E2E["services"]["fake-llm"]
    assert "ports" not in fake and "expose" not in fake
    assert fake["volumes"] == ["../tests/fake_llm.py:/fake/fake_llm.py:ro"]
    assert _networks(fake) == {"llm"}
    assert re.fullmatch(r"python:\d+\.\d+\.\d+-slim-trixie", fake["image"])
    env = E2E["services"]["fione"]["environment"]
    assert env["FIONE_LLM_BASE_URL"] == "http://fake-llm:11434/v1"
    assert env["FIONE_LLM_AUTO_PULL"] == "true" and env["FIONE_MCP_ENABLED"] == "true"
    assert E2E["services"]["fione"]["depends_on"]["fake-llm"]["condition"] == "service_healthy"
    # for the tests only: the real defaults stay off
    real = SERVICES["fione"]["environment"]
    assert real["FIONE_LLM_AUTO_PULL"].endswith(":-false}")
    assert real["FIONE_MCP_ENABLED"].endswith(":-false}")
    assert "COMPOSE_PROFILES" not in (ROOT / "docker" / "e2e.env").read_text()
