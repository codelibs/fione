"""The notebook image (docker/Dockerfile.notebook): pinned versions, licences, the SDK, and the
rule that nothing Jupyter serves or loads is writable by the user. One build per module; the
server itself is started once with the launcher's container settings and a real sign-in."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.docker

ROOT = Path(__file__).resolve().parents[2]
IMAGE = f"fione-notebook:test-{os.getpid()}"  # removed again at the end
OWNER = "7"
BASE = f"/user/{OWNER}/"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture(scope="module", autouse=True)
def image():
    build = subprocess.run(
        ["docker", "build", "-f", "docker/Dockerfile.notebook", "-t", IMAGE, "."],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    assert build.returncode == 0, build.stderr[-5000:]
    yield
    subprocess.run(["docker", "image", "rm", IMAGE], capture_output=True)


def _name() -> str:
    return f"fione-nb-test-{uuid.uuid4().hex[:12]}"


def run(
    *command: str, options: tuple[str, ...] = (), timeout: float = 300
) -> subprocess.CompletedProcess:
    """Run a command in a new container of the image (as its own user unless options say)."""
    name = _name()
    try:
        return subprocess.run(
            ["docker", "run", "--rm", "--name", name, *options, IMAGE, *command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def test_runs_as_uid_1000():
    assert run("id", "-u").stdout.strip() == "1000"
    assert run("id", "-g").stdout.strip() == "1000"


def test_pinned_versions():
    out = run("jupyter", "--version").stdout
    assert re.search(r"^jupyter_server\s*:\s*2\.21\.1$", out, re.M), out
    assert re.search(r"^jupyterlab\s*:\s*4\.6\.4$", out, re.M), out
    tornado = run("python", "-c", "import tornado; print(tornado.version)").stdout.strip()
    assert re.fullmatch(r"6\.5\.[0-9]+", tornado), tornado


def test_licence_check_passes_in_the_image():
    result = run(
        "python",
        "/scripts/check_licenses.py",
        options=("-v", f"{ROOT / 'scripts'}:/scripts:ro"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "allowed   bundle elkjs: EPL-2.0  (exception: " in result.stdout
    assert "allowed   bundle @fortawesome/fontawesome-free: (CC-BY-4.0" in result.stdout


def test_sdk_importable():
    result = run("python", "-c", "import fione_sdk; print(fione_sdk.__version__)")
    assert result.stdout.strip() == "20.0.0", result.stderr


def test_announcements_disabled():
    result = run("jupyter", "labextension", "list")
    out = ANSI.sub("", result.stdout + result.stderr)
    assert re.search(
        r"^Disabled extensions:\n\s+@jupyterlab/apputils-extension:announcements$", out, re.M
    ), out


def test_jupyter_dirs_are_not_writable_by_nb():
    script = """
for dir in "$JUPYTER_CONFIG_DIR" "$JUPYTER_DATA_DIR" /app/.venv/share/jupyter \
           /app/.venv/etc/jupyter /etc/jupyter /app/src/fione_notebook; do
    touch "$dir/x" 2>/dev/null && echo "writable: $dir"
done
touch /home/nb/work/x /tmp/x && echo "work and tmp: ok"
find /app /etc /usr -writable 2>/dev/null
find /etc/jupyter-fione /usr/local/share/jupyter-fione -type l
"""
    result = run("sh", "-c", script)
    assert result.stdout.strip() == "work and tmp: ok", result.stdout + result.stderr


def test_jupyter_environment():
    env = json.loads(
        subprocess.run(
            ["docker", "image", "inspect", "-f", "{{json .Config.Env}}", IMAGE],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    values = dict(item.split("=", 1) for item in env)
    assert values["JUPYTER_CONFIG_DIR"] == "/etc/jupyter-fione"
    assert values["JUPYTER_DATA_DIR"] == "/usr/local/share/jupyter-fione"
    assert values["JUPYTER_RUNTIME_DIR"] == "/tmp/jupyter-runtime"
    assert values["PYTHONNOUSERSITE"] == "1"
    assert "JUPYTER_PATH" not in values and "JUPYTER_CONFIG_PATH" not in values
    out = run("python", "-c", "import site, sys; print(site.ENABLE_USER_SITE, sys.prefix)")
    assert out.stdout.split() == ["False", "/app/.venv"]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign(key: bytes, claims: dict) -> str:
    """A launch token as Fione signs it (see fione_notebook.auth)."""
    payload = _b64(json.dumps(claims).encode())
    signature = hmac.new(key, f"v1.{payload}".encode(), hashlib.sha256).digest()
    return f"v1.{payload}.{_b64(signature)}"


def _docker(*args: str) -> str:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=True, timeout=60
    ).stdout


def _wait(condition, timeout: float, what: str):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = condition()
        if value:
            return value
        time.sleep(1)
    raise AssertionError(f"timed out waiting for {what}")


def _up(url: str) -> bool:
    try:
        httpx.get(url, timeout=3)
    except httpx.TransportError:
        return False
    return True


# The container settings the launcher uses (see the plan's fixed container spec).
LAUNCHER_SETTINGS = (
    "--user",
    "1000:1000",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
    "--init",
    "--cpus",
    "2",
    "--memory",
    "4g",
    "--memory-swap",
    "4g",
    "--pids-limit",
    "512",
)


def _settings(key: bytes, **changes: str | None) -> list[str]:
    """`-e` options with valid FIONE_NB_* values, plus changes (None drops a value)."""
    env = {
        "FIONE_NB_OWNER": OWNER,
        "FIONE_NB_KEY": key.hex(),
        "FIONE_NB_COOKIE_SECRET": secrets.token_hex(32),
        "FIONE_NB_ORIGIN": "http://127.0.0.1:18080",
        "FIONE_NB_EXPIRES": str(int(time.time()) + 3600),
    }
    env.update(changes)
    options = []
    for name, value in env.items():
        if value is not None:
            options += ["-e", f"{name}={value}"]
    return options


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"FIONE_NB_OWNER": None}, "fione_notebook: FIONE_NB_OWNER is missing or malformed"),
        ({"JUPYTER_PATH": "/tmp"}, "fione_notebook: JUPYTER_PATH must not be set"),
        # int() raises ValueError, which traitlets would log and then start a stock server.
        ({"FIONE_NB_EXPIRES": "9" * 5000}, "fione_notebook: configuration failed (ValueError)"),
    ],
    ids=["owner-missing", "jupyter-path-set", "other-error"],
)
def test_server_refuses_to_start(changes, message):
    result = run(options=(*LAUNCHER_SETTINGS, *_settings(b"k" * 32, **changes)), timeout=90)
    assert result.returncode != 0
    out = result.stdout + result.stderr
    assert message in out, out
    assert "9" * 100 not in out  # the value is never echoed


def test_server_starts_with_the_launcher_settings_and_signs_in():
    """The extension's start-up checks accept the image, with the container settings the
    launcher uses; a launch token signs the owner in; a notebook can be saved although the
    data dir is read-only; a file the user plants as a lab extension is not served; and the
    health check reports the server as up."""
    name = _name()
    key = secrets.token_bytes(32)
    try:
        _docker(
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            *LAUNCHER_SETTINGS,
            "--health-interval",
            "1s",
            "--health-start-period",
            "60s",
            "-p",
            "127.0.0.1::8888",
            *_settings(key),
            IMAGE,
        )
        port = _docker("port", name, "8888/tcp").splitlines()[0].rsplit(":", 1)[1]
        url = f"http://127.0.0.1:{port}{BASE}"
        _wait(lambda: _up(f"{url}login"), 90, "the server")
        c = httpx.Client(
            base_url=url,
            timeout=30,
            follow_redirects=False,
            headers={"Sec-Fetch-Site": "same-site", "Referer": "http://127.0.0.1:18080/"},
        )

        assert c.get("lab").status_code == 302  # anonymous: to the login page
        claims = {
            "sub": OWNER,
            "name": "user7",
            "role": "editor",
            "exp": int(time.time()) + 60,
            "jti": uuid.uuid4().hex,
        }
        token = sign(key, claims)
        r = c.get("login", params={"launch": token, "next": f"{BASE}lab"})
        assert r.status_code == 302 and r.headers["location"] == f"{BASE}lab", r.text
        assert c.get("lab").status_code == 200

        notebook = {
            "type": "notebook",
            "content": {"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5},
        }
        r = c.put(
            "api/contents/a.ipynb", json=notebook, headers={"X-XSRFToken": c.cookies["_xsrf"]}
        )
        assert r.status_code == 201, r.text

        _docker(
            "exec",
            name,
            "sh",
            "-c",
            "mkdir -p ~/.local/share/jupyter/labextensions/evil/static"
            " && echo '<script>alert(1)</script>' > ~/.local/share/jupyter/labextensions/evil/"
            "static/x.html",
        )
        assert c.get("lab/extensions/evil/static/x.html").status_code == 404
        real = _docker(
            "exec",
            name,
            "sh",
            "-c",
            "ls /app/.venv/share/jupyter/labextensions/jupyterlab_pygments/static | head -1",
        ).strip()
        assert c.get(f"lab/extensions/jupyterlab_pygments/static/{real}").status_code == 200

        _wait(
            lambda: _docker("inspect", "-f", "{{.State.Health.Status}}", name).strip() == "healthy",
            60,
            "a healthy status",
        )
        logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True).stderr
        assert "fione_notebook:" not in logs
        assert token.split(".")[1] not in logs and token.split(".")[2] not in logs
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
