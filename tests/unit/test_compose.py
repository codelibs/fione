"""docker/compose.yaml keeps its topology: who shares which network, that nothing mounts the
Docker socket, and that Ollama stays private and optional."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker" / "compose.yaml").read_text())
SERVICES = COMPOSE["services"]
E2E = yaml.safe_load((ROOT / "docker" / "compose.e2e.yaml").read_text())
ENV_EXAMPLE = (ROOT / "docker" / ".env.example").read_text()


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
    assert _networks(SERVICES["fione"]) == {"backend", "llm"}
    assert _networks(SERVICES["ollama"]) == {"llm"}  # not on backend, with the storage
    members = {name for name, s in SERVICES.items() if "llm" in _networks(s)}
    assert members == {"fione", "ollama"}
    assert not (COMPOSE["networks"]["llm"] or {}).get("internal")  # Ollama downloads models


def test_nothing_mounts_the_docker_socket():
    mounting = {
        name
        for name, service in SERVICES.items()
        if any("docker.sock" in volume for volume in _values(service.get("volumes", [])))
    }
    assert mounting == set()


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
