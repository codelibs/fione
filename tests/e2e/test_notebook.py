"""The embedded notebook end to end: an administrator allows an editor notebooks on the users
page; the editor starts one from the notebook page, which frames JupyterLab signed in through
the launch token (a cross-port, same-site navigation), and runs fione-sdk in a cell. Cells
reach nothing but the gateway's relay, with a token capped at editor and revoked on Stop.

JupyterLab saves its layout and settings through APIs the gateway keeps read-only, so those
failed loads (and only those) are expected in the console.
"""

import re
import subprocess
import time

import httpx
import pytest
from playwright.sync_api import expect

from e2e_helpers import sign_in

pytestmark = pytest.mark.e2e

PASSWORD = "e2e-notebook-password-1"  # test-only
START_TIMEOUT_MS = 120_000
CELL_TIMEOUT_MS = 90_000
END = "--end--"  # the last line every cell prints
RUN_ATTEMPTS = 3  # a run JupyterLab drops is retried, at most twice per cell
QUEUED = re.compile(r"\[(\*|\d+)\]")  # a cell's prompt once its run is sent


@pytest.fixture(scope="module")
def users(stack, admin) -> dict[str, int]:
    """Editors for these tests, by name: their ids. Only ``nb-runner`` and ``nb-other`` may
    run notebooks; the first test allows ``nb-editor`` on the users page."""
    ids = {}
    with admin.api(stack) as api:
        for name in ("nb-editor", "nb-runner", "nb-other", "nb-outsider"):
            r = api.post(
                "/api/v1/users", json={"username": name, "password": PASSWORD, "role": "editor"}
            )
            assert r.status_code == 201, r.text
            ids[name] = r.json()["id"]
        for name in ("nb-runner", "nb-other"):
            r = api.patch(f"/api/v1/users/{ids[name]}", json={"notebook": "run"})
            assert r.status_code == 200, r.text
    return ids


def expect_refused_writes(stack, console, uid: int) -> None:
    for api in ("settings", "workspaces"):
        console.expect_error_prefix(f"{stack.notebook_base}/user/{uid}/lab/api/{api}/")


def open_notebook(page, stack, console, uid: int):
    """On the notebook page: start the notebook unless it runs; the frame, signed in."""
    expect_refused_writes(stack, console, uid)
    page.goto("/notebook")
    start = page.locator("form[action='/notebook/start'] button[type=submit]")
    if start.count():
        start.click()
    return signed_in_frame(page)


def signed_in_frame(page):
    """The notebook page's frame once JupyterLab shows its launcher in it: the launch token
    signed the browser in (the page reloads by itself when a starting notebook runs)."""
    page.wait_for_selector("iframe.notebook-frame", timeout=START_TIMEOUT_MS)
    frame = page.frame_locator("iframe.notebook-frame")
    frame.locator(".jp-LauncherCard[data-category='Notebook']").first.wait_for(
        timeout=START_TIMEOUT_MS
    )
    return frame


def edit_first_cell(notebook) -> None:
    """Put the first cell in edit mode with the keyboard focus in its editor."""
    notebook.locator(".jp-Cell").first.locator(".cm-content").click()
    # JupyterLab's own selector for the cell being edited (edit mode is the notebook's class).
    editing = notebook.locator(".jp-mod-editMode .jp-Cell.jp-mod-active")
    expect(editing).to_have_count(1)
    expect(editing).to_have_attribute("data-windowed-list-index", "0")
    expect(editing.locator(".cm-content")).to_be_focused()


def run_cell(frame, page, code: str, record_property) -> str:
    """Run ``code`` in a new notebook's first cell; the cell's output, which ends with
    ``END``. Any error output (a traceback) or JupyterLab dialog fails the test. How many
    runs it took is recorded (``cell_runs``)."""
    frame.locator(".jp-LauncherCard[data-category='Notebook']").first.click()
    notebook = frame.locator(".jp-NotebookPanel:not(.lm-mod-hidden)")
    notebook.locator(".jp-Notebook-ExecutionIndicator[data-status='idle']").wait_for(
        timeout=CELL_TIMEOUT_MS
    )
    cell = notebook.locator(".jp-Cell").first
    edit_first_cell(notebook)
    page.keyboard.insert_text(code)
    # In a just-created notebook JupyterLab sometimes drops a run without a message, even with
    # the kernel shown idle (the prompt stays "[ ]"): run the cell again, at most twice.
    sent = False
    for runs in range(1, RUN_ATTEMPTS + 1):
        if runs > 1:
            edit_first_cell(notebook)  # Shift+Enter moved on to a new cell
        page.keyboard.press("Shift+Enter")
        try:
            expect(cell.locator(".jp-InputPrompt")).to_have_text(QUEUED, timeout=5_000)
        except AssertionError:
            continue
        sent = True
        break
    record_property("cell_runs", runs)
    print(f"cell runs: {runs}")
    assert sent, f"JupyterLab dropped the cell's run {RUN_ATTEMPTS} times"
    outputs = cell.locator(".jp-OutputArea-output")
    outputs.get_by_text(re.compile(rf"{END}|Error")).first.wait_for(timeout=CELL_TIMEOUT_MS)
    text = "\n".join(outputs.all_inner_texts())
    assert END in text, text
    assert frame.locator(".jp-Dialog").count() == 0, frame.locator(".jp-Dialog").inner_text()
    return text


def as_one_line(code: str) -> str:
    """``code`` as one ``exec`` line: the editor's auto-indent cannot change it."""
    return f"exec({code!r})"


def close_lab(page) -> None:
    """Take JupyterLab out of the page. Leaving the page with it would abort its requests,
    which JupyterLab logs as errors, and stopping the container under it fails them (502)."""
    page.locator("iframe.notebook-frame").evaluate_all("frames => frames.forEach(f => f.remove())")


def stop(page) -> None:
    """Stop the notebook from its page."""
    if not page.url.endswith("/notebook"):
        page.goto("/notebook")
    close_lab(page)
    page.click("form[action='/notebook/stop'] button[type=submit]")
    page.wait_for_selector("form[action='/notebook/start']")


def test_a_permitted_user_runs_the_sdk_in_jupyterlab(
    stack, admin, users, new_page, console, record_property
):
    page = new_page()
    sign_in(page, admin.username, admin.password)
    page.goto("/admin/users")
    row = page.locator("tr", has=page.locator("th", has_text="nb-editor"))
    row.get_by_role("button", name="Allow").click()
    page.wait_for_url(re.compile(r"/admin/users\?done=notebook"))

    editor = new_page()
    sign_in(editor, "nb-editor", PASSWORD)
    editor.fill("#project-name", "Notebook e2e")  # the editor's one project
    editor.click("#new-project button[type=submit]")
    editor.locator(".project-card__link:text-is('Notebook e2e')").wait_for()
    expect_refused_writes(stack, console, users["nb-editor"])
    editor.click("nav a[href='/notebook']")
    editor.wait_for_url("**/notebook")
    editor.click("form[action='/notebook/start'] button[type=submit]")
    editor.wait_for_selector("#notebook-status[hx-trigger]")  # starting, polled
    frame = signed_in_frame(editor)
    try:
        code = 'import fione_sdk; print("projects", len(fione_sdk.Client().projects()))'
        assert "projects 1" in run_cell(frame, editor, f'{code}; print("{END}")', record_property)
        editor.screenshot(path=str(stack.artifacts / "notebook-running.png"))
    finally:
        stop(editor)


def test_without_permission_there_is_no_link_and_403(stack, users, new_page, console):
    page = new_page()
    sign_in(page, "nb-outsider", PASSWORD)
    assert page.locator("nav a[href='/notebook']").count() == 0
    console.expect_error(stack.base + "/notebook")
    assert page.goto("/notebook").status == 403
    csrf = page.get_attribute("meta[name=csrf-token]", "content")
    r = page.request.post("/notebook/start", form={"csrf_token": csrf}, max_redirects=0)
    assert r.status == 403


ESCAPE = """
import errno, os, socket, urllib.error, urllib.request

def connect(host, port):
    try:
        socket.create_connection((host, port), timeout=5).close()
        return "connects"
    except OSError:
        return "fails"

def resolve(name):
    try:
        socket.getaddrinfo(name, 80)
        return "resolves"
    except OSError:
        return "unresolved"

def probe(host, port):
    # "refused" still means that the host answered: only a service listening there is missing.
    try:
        socket.create_connection((host, port), timeout=5).close()
        return "connects"
    except socket.timeout:
        return "timeout"
    except OSError as e:
        return {errno.ECONNREFUSED: "refused"}.get(e.errno, "unreachable")

def host_address():
    # The default gateway, or (an internal network has no default route) the first address
    # of eth0's subnet, which Docker gives the bridge on the host.
    rows = [line.split() for line in open("/proc/net/route").read().splitlines()[1:]]
    for row in rows:
        if row[1] == "00000000" and row[2] != "00000000":
            return socket.inet_ntoa(bytes.fromhex(row[2])[::-1])
    for row in rows:
        if row[0] == "eth0" and row[2] == "00000000":
            network = int.from_bytes(bytes.fromhex(row[1])[::-1], "big")
            return socket.inet_ntoa((network + 1).to_bytes(4, "big"))

def status(url, token=None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    try:
        request = urllib.request.Request(url, headers=headers)
        return urllib.request.urlopen(request, timeout=10).status
    except urllib.error.HTTPError as e:
        return e.code

token = os.environ["FIONE_TOKEN"]
relay = "http://notebook-gateway:8081/api/v1"
print("pypi.org:443", connect("pypi.org", 443))
print("1.1.1.1:443", connect("1.1.1.1", 443))
print("fione", resolve("fione"))
print("seaweedfs", resolve("seaweedfs"))
print("auth/me", status(relay + "/auth/me", token))
print("tokens", status(relay + "/tokens", token))
print("projects without token", status(relay + "/projects"))
print("projects", status(relay + "/projects", token))
print("other contents", status("http://notebook-gateway:8080/user/%s/api/contents" % OTHER))
host = host_address()
print("host:22", probe(host, 22))
print("host:80", probe(host, 80))
print("END")
"""


def test_cells_cannot_escape(stack, users, new_page, console, record_property):
    other = new_page()  # another user's notebook, running: Jupyter answers for it
    sign_in(other, "nb-other", PASSWORD)
    open_notebook(other, stack, console, users["nb-other"])
    page = new_page()
    sign_in(page, "nb-runner", PASSWORD)
    try:
        frame = open_notebook(page, stack, console, users["nb-runner"])
        code = ESCAPE.replace("OTHER", str(users["nb-other"])).replace('"END"', repr(END))
        lines = run_cell(frame, page, as_one_line(code), record_property).splitlines()
        assert lines[:9] == [
            "pypi.org:443 fails",
            "1.1.1.1:443 fails",
            "fione unresolved",
            "seaweedfs unresolved",
            "auth/me 403",
            "tokens 403",
            "projects without token 401",
            "projects 200",
            "other contents 403",
        ], lines
        # The host through the `notebooks` bridge address: no service there may answer. The
        # host itself may (refused): see known-limitations.md.
        host = dict(line.split(" ", 1) for line in lines[9:11])
        record_property("host_bridge", host)
        assert set(host) == {"host:22", "host:80"} and "connects" not in host.values(), lines
    finally:
        try:
            stop(page)
        finally:
            stop(other)


ADMIN_CAP = """
import io, fione_sdk
client = fione_sdk.Client()
print("modules", len(client.modules()) > 0)
try:
    module = ("m.py", io.BytesIO(b"x = 1"), "text/x-python")
    client._json("POST", "/modules", files={"file": module})
    print("upload allowed")
except fione_sdk.FioneError as e:
    print("upload", e.status, e.code)
print("END")
"""


def test_admin_notebook_is_capped(stack, admin, new_page, console, record_property):
    page = new_page()
    sign_in(page, admin.username, admin.password)
    uid = page.request.get("/api/v1/auth/me").json()["user"]["id"]
    try:
        frame = open_notebook(page, stack, console, uid)
        output = run_cell(
            frame, page, as_one_line(ADMIN_CAP.replace('"END"', repr(END))), record_property
        )
        assert output.splitlines()[:2] == ["modules True", "upload 403 token_scope"]
    finally:
        stop(page)


def test_stop_removes_the_container_and_revokes_the_token(
    stack, users, new_page, console, record_property
):
    page = new_page()
    sign_in(page, "nb-runner", PASSWORD)
    frame = open_notebook(page, stack, console, users["nb-runner"])
    code = f'import os; print("token", os.environ["FIONE_TOKEN"]); print("{END}")'
    token = run_cell(frame, page, code, record_property).splitlines()[0].removeprefix("token ")
    url = f"{stack.base}/api/v1/projects"
    headers = {"Authorization": f"Bearer {token}"}
    assert httpx.get(url, headers=headers).status_code == 200
    stop(page)
    labels = [f"label=fione.project={stack.project}", f"label=fione.uid={users['nb-runner']}"]
    command = ["docker", "ps", "-a", "-q", "--filter", labels[0], "--filter", labels[1]]
    deadline = time.monotonic() + 30
    while subprocess.run(command, capture_output=True, text=True).stdout.strip():
        assert time.monotonic() < deadline, "the notebook container is still there"
        time.sleep(1)
    assert httpx.get(url, headers=headers).status_code == 401


def test_notebook_page_csp(stack, users, new_page, console):
    page = new_page()
    sign_in(page, "nb-runner", PASSWORD)
    try:
        open_notebook(page, stack, console, users["nb-runner"])
        close_lab(page)
        lab = re.compile(rf"{re.escape(stack.notebook_base)}/user/\d+/lab(\?|$)")
        with page.expect_response(lab) as framed:
            response = page.goto("/notebook")
        signed_in_frame(page)
        csp = response.headers["content-security-policy"]
        assert f"frame-src {stack.notebook_base}" in csp
        assert "frame-ancestors 'none'" in csp
        jupyter_csp = framed.value.headers["content-security-policy"]
        assert f"frame-ancestors 'self' {stack.base}" in jupyter_csp
    finally:
        stop(page)
