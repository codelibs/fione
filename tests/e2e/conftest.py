"""The end-to-end suite: a real Compose stack (docker/compose.yaml + compose.e2e.yaml, the
public test values of docker/e2e.env) and a real browser (Playwright, Chromium).

    uv run pytest tests/e2e -m e2e

One stack per session, under a unique project name on free host ports, always removed with
its volumes at the end (also on failure or Ctrl-C). Set ``FIONE_IMAGE_TAG`` to use images
built beforehand (``docker compose ... --profile serving build``); otherwise both images are
built. ``FIONE_E2E=0`` skips the suite; so does a missing Docker. On failure the Compose
logs are printed, and they, a Playwright trace and a screenshot of the failing page are
saved under ``FIONE_E2E_ARTIFACTS`` (default ``test-results/e2e``).
"""

import atexit
import os
import secrets
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest

from e2e_helpers import sign_in, upload

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / "docker" / "e2e.env"
ADMIN, PASSWORD = "e2e-admin", "e2e-admin-password-1"  # test-only, inside a throwaway stack
UP_TIMEOUT_SECS = 600  # building both images from scratch included
# Console messages a page may log without failing a test: resource loads the tests cause on
# purpose (a 403 or 404 page). CSP violations ("Refused to ...") and script errors fail.
IGNORED_CONSOLE = ("Failed to load resource",)


def _env_value(name: str) -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1]
    raise KeyError(name)


SETUP_TOKEN = _env_value("FIONE_SETUP_TOKEN")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class Stack:
    project: str
    port: int
    image_tag: str
    env: dict
    artifacts: Path
    down_done: bool = field(default=False)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def serving_image(self) -> str:
        return f"ghcr.io/codelibs/fione-serving:{self.image_tag}"

    def compose(self, *args: str, check: bool = True, timeout: float = 120, **kw):
        command = [
            "docker",
            "compose",
            "-p",
            self.project,
            "--env-file",
            str(ENV_FILE),
            "-f",
            "docker/compose.yaml",
            "-f",
            "docker/compose.e2e.yaml",
            *args,
        ]
        return subprocess.run(
            command,
            cwd=ROOT,
            env=self.env,
            check=check,
            timeout=timeout,
            capture_output=True,
            text=True,
            **kw,
        )

    def processes(self) -> list[str]:
        """The command lines running in the fione container, but ``ps`` itself."""
        out = self.compose("exec", "-T", "fione", "ps", "-eo", "args", "--no-headers").stdout
        return [line.strip() for line in out.splitlines() if line.strip() and "ps -eo" not in line]

    def wait_healthy(self, seconds: float = 120) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{self.base}/api/v1/health", timeout=3).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(1)
        raise TimeoutError("the fione container did not become healthy")

    def logs(self) -> str:
        return self.compose("logs", "--no-color", "--tail", "300", check=False).stdout

    def down(self) -> None:
        if not self.down_done:
            self.down_done = True
            self.compose("--profile", "serving", "down", "-v", "--remove-orphans", check=False)


def _docker_ready() -> str | None:
    """None when Docker can be used, else why not."""
    if os.environ.get("FIONE_E2E") == "0":
        return "FIONE_E2E=0"
    if shutil.which("docker") is None:
        return "docker is not installed"
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=30)
    except (subprocess.SubprocessError, OSError):
        return "the Docker daemon is not reachable"
    return None


@pytest.fixture(scope="session")
def stack(request):
    reason = _docker_ready()
    if reason:
        pytest.skip(f"e2e needs Docker: {reason}")
    prebuilt = os.environ.get("FIONE_IMAGE_TAG")
    artifacts = Path(os.environ.get("FIONE_E2E_ARTIFACTS", ROOT / "test-results" / "e2e"))
    artifacts.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    env = os.environ | {"FIONE_PORT": str(port), "FIONE_SERVING_PORT": str(_free_port())}
    stack = Stack(
        project=f"fione-e2e-{secrets.token_hex(3)}",
        port=port,
        image_tag=prebuilt or _env_value("FIONE_IMAGE_TAG"),
        env=env,
        artifacts=artifacts,
    )
    atexit.register(stack.down)  # also after Ctrl-C, when fixtures may not finalize
    try:
        if not prebuilt:
            stack.compose("--profile", "serving", "build", timeout=UP_TIMEOUT_SECS)
        up = ["up", "-d", "--wait", "--wait-timeout", "180"]
        stack.compose(*up, *([] if not prebuilt else ["--no-build"]), timeout=UP_TIMEOUT_SECS)
        yield stack
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"docker compose failed:\n{e.stdout}\n{e.stderr}") from None
    finally:
        if request.session.testsfailed:
            logs = stack.logs()
            (artifacts / "compose.log").write_text(logs)
            capture = request.config.pluginmanager.get_plugin("capturemanager")
            with capture.global_and_fixture_disabled():
                print(f"\n--- docker compose logs ({stack.project}) ---\n{logs}")
        stack.down()


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    report = yield
    setattr(item, f"report_{report.when}", report)
    return report


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


class Console:
    """The console errors pages log; CSP violations land here."""

    def __init__(self):
        self.errors: list[str] = []

    def watch(self, page) -> None:
        def on_console(message):
            if message.type == "error" and not message.text.startswith(IGNORED_CONSOLE):
                self.errors.append(f"{page.url}: {message.text}")

        page.on("console", on_console)
        page.on("pageerror", lambda error: self.errors.append(f"{page.url}: {error}"))


@pytest.fixture
def console():
    return Console()


@pytest.fixture
def new_page(request, browser, stack, console):
    """``new_page()``: a page in a fresh browser context (its own cookies), English, desktop.
    The console must stay free of errors; a failing test leaves a trace and a screenshot."""
    contexts = []

    def make():
        context = browser.new_context(
            base_url=stack.base,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            accept_downloads=True,
        )
        context.tracing.start(screenshots=True, snapshots=True)
        contexts.append(context)
        page = context.new_page()
        console.watch(page)
        return page

    yield make
    failed = (
        getattr(request.node, "report_call", None) is not None and request.node.report_call.failed
    )
    for index, context in enumerate(contexts):
        name = f"{request.node.name}-{index}"
        if failed:
            for page in context.pages:
                page.screenshot(path=str(stack.artifacts / f"{name}.png"), full_page=True)
            context.tracing.stop(path=str(stack.artifacts / f"{name}-trace.zip"))
        else:
            context.tracing.stop()
        context.close()
    assert console.errors == [], "console errors (CSP violations, script errors)"


@dataclass
class Admin:
    username: str
    password: str
    token: str

    def api(self, stack: Stack) -> httpx.Client:
        headers = {"Authorization": f"Bearer {self.token}"}
        return httpx.Client(base_url=stack.base, headers=headers, timeout=60)


@pytest.fixture(scope="session")
def admin(stack, browser) -> Admin:
    """The first administrator, created through the first-admin page with the setup token,
    and an API token of theirs for setup and assertions."""
    context = browser.new_context(base_url=stack.base)
    page = context.new_page()
    console = Console()
    console.watch(page)
    page.goto("/")
    page.wait_for_url("**/first-admin")
    page.fill("#setup-token", SETUP_TOKEN)
    page.fill("#setup-username", ADMIN)
    page.fill("#setup-password", PASSWORD)
    page.fill("#setup-password2", PASSWORD)
    page.click("form[data-json-form] button[type=submit]")
    page.wait_for_url(f"{stack.base}/")
    csrf = page.get_attribute("meta[name=csrf-token]", "content")
    r = page.request.post("/api/v1/tokens", data={"name": "e2e"}, headers={"X-CSRF-Token": csrf})
    assert r.ok, r.text()
    token = r.json()["token"]
    context.close()
    assert console.errors == []
    return Admin(ADMIN, PASSWORD, token)


@pytest.fixture(scope="session")
def data(tmp_path_factory) -> dict[str, Path]:
    """Iris (scikit-learn's copy, BSD) as the CSV files the flows upload."""
    from sklearn.datasets import load_iris

    directory = tmp_path_factory.mktemp("e2e-data")
    frame = load_iris(as_frame=True).frame
    frame["species"] = frame.pop("target").map({0: "setosa", 1: "versicolor", 2: "virginica"})
    files = {"iris": directory / "iris.csv", "new": directory / "new.csv"}
    frame.to_csv(files["iris"], index=False)
    frame.drop(columns=["species"]).iloc[[0, 60, 120]].to_csv(files["new"], index=False)
    return files


@dataclass
class Trained:
    project: str  # /projects/<id>
    job: str  # /projects/<id>/jobs/<id>
    summary: str  # /projects/<id>/models/<id>/summary

    @property
    def model(self) -> str:
        return self.summary.removesuffix("/summary")


@pytest.fixture(scope="session")
def trained(stack, browser, admin, data) -> Trained:
    """The EasyML wizard by browser, once per session: a project, iris uploaded, the
    analysis defaults (species, classification), the 1-minute preset, Run, the live
    progress until it moves on to the summary. Later tests reuse the model."""
    context = browser.new_context(base_url=stack.base, viewport={"width": 1280, "height": 800})
    page = context.new_page()
    console = Console()
    console.watch(page)
    sign_in(page, admin.username, admin.password)
    page.fill("#project-name", "Iris e2e")
    page.click("#new-project button[type=submit]")
    page.click(".project-card__link:text-is('Iris e2e')")
    page.wait_for_url("**/projects/*")
    project = page.url.removeprefix(stack.base)
    page.goto(project + "/upload")
    upload(page, data["iris"])
    page.wait_for_url("**/analyze")
    assert page.locator("#target-select").input_value() == "species"
    assert page.locator("#task-classification").is_checked()
    page.check("#runtime-1")
    page.click("#run-button")
    page.wait_for_url("**/jobs/*")
    job = page.url.removeprefix(stack.base)
    page.wait_for_url("**/summary", timeout=180_000)  # the progress page moves on by itself
    summary = page.url.removeprefix(stack.base)
    context.close()
    assert console.errors == []
    return Trained(project, job, summary)
