"""The `ollama` Compose profile is switched on by COMPOSE_PROFILES in an env file, and by
nothing else: `docker compose config` lists the service only then."""

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.docker

ROOT = Path(__file__).resolve().parents[2]
S3 = "FIONE_S3_ACCESS_KEY=profileAccessKey0\nFIONE_S3_SECRET_KEY=profileSecretKey0123456789\n"


def services(tmp_path, extra: str) -> set[str]:
    env_file = tmp_path / "profile.env"
    env_file.write_text(S3 + extra)
    command = [
        "docker", "compose", "--env-file", str(env_file),
        "-f", str(ROOT / "docker" / "compose.yaml"), "config", "--services",
    ]  # fmt: skip
    env = {k: v for k, v in os.environ.items() if k != "COMPOSE_PROFILES"}  # only the file
    done = subprocess.run(command, capture_output=True, text=True, check=True, env=env)
    return set(done.stdout.split())


def test_ollama_runs_only_with_its_profile(tmp_path):
    assert "ollama" in services(tmp_path, "COMPOSE_PROFILES=ollama\n")
    assert "ollama" not in services(tmp_path, "")
