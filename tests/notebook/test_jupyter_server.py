"""A real Jupyter server with the fione_notebook extension, on 127.0.0.1: launch-token sign-in,
owner-only authorization, XSRF and Origin checks, kernels, terminals, CSP and log scrubbing.

One server per module (starting JupyterLab takes seconds); it, its kernels and its terminals
are stopped in teardown, also when a test fails."""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from email.utils import formatdate
from pathlib import Path

import httpx
import pytest
from tornado.httpclient import HTTPClientError, HTTPRequest
from tornado.websocket import websocket_connect

pytestmark = pytest.mark.notebook

SRC = Path(__file__).resolve().parents[2] / "src"
OWNER = "7"
BASE = f"/user/{OWNER}/"
FIONE_ORIGIN = "http://127.0.0.1:18080"
CSP = f"frame-ancestors 'self' {FIONE_ORIGIN}; report-uri {BASE}api/security/csp-report"
CONFIG_FILE = """\
import os

from fione_notebook.config import configure

c = get_config()  # noqa: F821
configure(c, os.environ)
c.ServerApp.root_dir = os.environ["NB_TEST_ROOT"]
"""
START_TIMEOUT = 60
EXIT_TIMEOUT = 20


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign(key: bytes, claims: dict) -> str:
    payload = _b64(json.dumps(claims).encode())
    signature = hmac.new(key, f"v1.{payload}".encode(), hashlib.sha256).digest()
    return f"v1.{payload}.{_b64(signature)}"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class Server:
    origin: str  # http://127.0.0.1:<port>
    url: str  # <origin>/user/7/
    ws_url: str
    key: bytes
    root: Path  # the contents root
    home: Path
    data_dir: Path
    log: Path
    expires: int  # FIONE_NB_EXPIRES
    tokens: list[str] = field(default_factory=list)

    def token(self, *, sub: str = OWNER, role: str = "editor", exp_in: int = 60) -> str:
        claims = {
            "sub": sub,
            "name": f"user{sub}",
            "role": role,
            "exp": int(time.time()) + exp_in,
            "jti": uuid.uuid4().hex,
        }
        token = sign(self.key, claims)
        self.tokens.append(token)
        return token

    def client(
        self, fetch_site: str | None = "same-site", referer: str | None = FIONE_ORIGIN + "/"
    ) -> httpx.Client:
        """A client sending the Sec-Fetch-Site and Referer a browser sends when Fione's page
        (``Referrer-Policy: origin``), on a sibling origin of the same site, opens the
        notebook."""
        headers = {"Sec-Fetch-Site": fetch_site} if fetch_site else {}
        if referer is not None:
            headers["Referer"] = referer
        return httpx.Client(base_url=self.url, follow_redirects=False, timeout=30, headers=headers)

    def login(self, role: str = "editor") -> httpx.Client:
        """A signed-in client that also holds the _xsrf cookie."""
        c = self.client()
        r = c.get("login", params={"launch": self.token(role=role), "next": f"{BASE}lab"})
        assert r.status_code == 302, r.text
        assert c.get("lab").status_code == 200
        return c


def _xsrf(c: httpx.Client) -> dict[str, str]:
    return {"X-XSRFToken": c.cookies["_xsrf"]}


def _cookie_header(c: httpx.Client) -> str:
    return "; ".join(f"{name}={value}" for name, value in c.cookies.items())


def _jupyter_env(**changes: str | None) -> dict[str, str]:
    """The test process' environment without any Jupyter or Fione setting, plus changes."""
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("JUPYTER", "FIONE_", "IPYTHON"))
    }
    env["PYTHONPATH"] = str(SRC)
    env["SHELL"] = "/bin/sh"  # terminals: no interactive first-run setup of the user's shell
    for name, value in changes.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _start(env: dict[str, str], port: int, cwd: Path, log: Path) -> subprocess.Popen:
    # The command line beats the config file: listen on loopback only, on this port only.
    # -P keeps the (user-writable) working directory off the server's sys.path, as the image's
    # `jupyter lab` console script does.
    command = [
        sys.executable,
        "-P",
        "-m",
        "jupyterlab",
        "--no-browser",
        "--ServerApp.ip=127.0.0.1",
        f"--ServerApp.port={port}",
        "--ServerApp.port_retries=0",
    ]
    with open(log, "wb") as out:
        return subprocess.Popen(
            command,
            env=env,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # its own process group, killed as a whole in teardown
        )


def _descendants(pid: int) -> dict[int, str]:
    """PID -> command line of every live descendant of pid."""
    out = subprocess.run(
        ["ps", "-A", "-o", "pid=,ppid=,args="], capture_output=True, text=True, check=True
    ).stdout
    children: dict[int, list[tuple[int, str]]] = {}
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 2:
            children.setdefault(int(parts[1]), []).append(
                (int(parts[0]), parts[2] if len(parts) > 2 else "")
            )
    found: dict[int, str] = {}
    todo = [pid]
    while todo:
        for child, args in children.get(todo.pop(), []):
            if child not in found:
                found[child] = args
                todo.append(child)
    return found


def _still_running(pid: int, args: str) -> bool:
    out = subprocess.run(["ps", "-o", "args=", "-p", str(pid)], capture_output=True, text=True)
    return out.returncode == 0 and out.stdout.strip() == args.strip()


def _stop(proc: subprocess.Popen) -> None:
    """Stop the server and everything it started: kernels and terminal shells run in sessions
    of their own, so they are found as descendants first and killed by exact PID."""
    started = _descendants(proc.pid) if proc.poll() is None else {}
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)  # the server shuts its kernels and terminals down
        try:
            proc.wait(15)
        except subprocess.TimeoutExpired:
            # Not reaped yet, so the process group is still the server's own.
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(10)
    for pid, args in started.items():
        if _still_running(pid, args):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def _wait_until_listening(proc: subprocess.Popen, url: str, log: Path) -> bool:
    """True once the server answers, False if it exited first."""
    deadline = time.monotonic() + START_TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        try:
            httpx.get(url + "api/status", timeout=2)
            return True
        except httpx.TransportError:
            time.sleep(0.25)
    pytest.fail(f"Jupyter did not start in {START_TIMEOUT} s:\n{log.read_text()}")


def _launch(env: dict[str, str], cwd: Path, log: Path) -> tuple[subprocess.Popen, int]:
    """A listening server and its port. A port can be taken between _free_port and the
    server's bind; then it is tried once more on another port."""
    for attempt in range(2):
        port = _free_port()
        proc = _start(env, port, cwd, log)
        try:
            if _wait_until_listening(proc, f"http://127.0.0.1:{port}{BASE}", log):
                return proc, port
        except BaseException:
            _stop(proc)
            raise
        if attempt or "is not available" not in log.read_text():
            break
    pytest.fail(f"Jupyter exited with {proc.returncode}:\n{log.read_text()}")


def _layout(root: Path) -> dict[str, Path]:
    dirs = {name: root / name for name in ("home", "runtime", "config", "data", "work")}
    for d in dirs.values():
        d.mkdir()
    (dirs["config"] / "jupyter_server_config.py").write_text(CONFIG_FILE)
    (dirs["config"] / "jupyter_server_config.py").chmod(0o444)  # nothing writable in there
    return dirs


def _server_env(dirs: dict[str, Path], key: bytes, **changes: str | None) -> dict[str, str]:
    values = {
        "HOME": str(dirs["home"]),
        "JUPYTER_RUNTIME_DIR": str(dirs["runtime"]),
        "JUPYTER_CONFIG_DIR": str(dirs["config"]),
        "JUPYTER_DATA_DIR": str(dirs["data"]),
        "NB_TEST_ROOT": str(dirs["work"]),
        "FIONE_NB_OWNER": OWNER,
        "FIONE_NB_KEY": key.hex(),
        "FIONE_NB_COOKIE_SECRET": os.urandom(32).hex(),
        "FIONE_NB_ORIGIN": FIONE_ORIGIN,
        "FIONE_NB_EXPIRES": str(int(time.time()) + 43200),
    }
    return _jupyter_env(**(values | changes))


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    root = tmp_path_factory.mktemp("jupyter")
    dirs = _layout(root)
    for name in ("config", "data"):
        dirs[name].chmod(0o555)
    key = os.urandom(32)
    log = root / "server.log"
    env = _server_env(dirs, key)
    proc, port = _launch(env, dirs["work"], log)
    try:
        url = f"http://127.0.0.1:{port}{BASE}"
        yield Server(
            origin=f"http://127.0.0.1:{port}",
            url=url,
            ws_url=f"ws://127.0.0.1:{port}{BASE}",
            key=key,
            root=dirs["work"],
            home=dirs["home"],
            data_dir=dirs["data"],
            log=log,
            expires=int(env["FIONE_NB_EXPIRES"]),
        )
    finally:
        _stop(proc)
        for name in ("config", "data"):
            dirs[name].chmod(0o755)


def _ws_request(url: str, cookies: str | None = None, origin: str | None = None) -> HTTPRequest:
    headers = {}
    if cookies:
        headers["Cookie"] = cookies
    if origin:
        headers["Origin"] = origin
    return HTTPRequest(url, headers=headers, connect_timeout=10, request_timeout=30)


async def _execute(request: HTTPRequest, code: str) -> str:
    """Run code over a kernel's channels WebSocket; return its stdout."""
    ws = await websocket_connect(request)
    try:
        msg_id = uuid.uuid4().hex
        await ws.write_message(
            json.dumps(
                {
                    "header": {
                        "msg_id": msg_id,
                        "msg_type": "execute_request",
                        "username": OWNER,
                        "session": uuid.uuid4().hex,
                        "version": "5.3",
                    },
                    "parent_header": {},
                    "metadata": {},
                    "channel": "shell",
                    "content": {
                        "code": code,
                        "silent": False,
                        "store_history": False,
                        "user_expressions": {},
                        "allow_stdin": False,
                    },
                }
            )
        )
        out = []
        while True:
            raw = await asyncio.wait_for(ws.read_message(), 60)
            assert raw is not None, "the kernel WebSocket closed"
            msg = json.loads(raw)
            if msg.get("parent_header", {}).get("msg_id") != msg_id:
                continue
            if msg["msg_type"] == "stream":
                out.append(msg["content"]["text"])
            elif msg["msg_type"] == "error":
                pytest.fail("\n".join(msg["content"]["traceback"]))
            elif msg["msg_type"] == "status" and msg["content"]["execution_state"] == "idle":
                return "".join(out)
    finally:
        ws.close()


def _ws_status(request: HTTPRequest) -> int:
    """The status a WebSocket handshake gets: 101 when it opens."""

    async def attempt() -> int:
        try:
            ws = await websocket_connect(request)
        except HTTPClientError as e:
            return e.code
        ws.close()
        return 101

    return asyncio.run(attempt())


@pytest.fixture(scope="module")
def kernel(server):
    """An editor's signed-in client and a running kernel's channels URL."""
    c = server.login("editor")
    r = c.post("api/kernels", json={"name": "python3"}, headers=_xsrf(c))
    assert r.status_code == 201, r.text
    kernel_id = r.json()["id"]
    yield c, f"{server.ws_url}api/kernels/{kernel_id}/channels"
    c.delete(f"api/kernels/{kernel_id}", headers=_xsrf(c))


@pytest.fixture(scope="module")
def terminal(server):
    """An admin's signed-in client, the terminal creation response and its WebSocket URL."""
    c = server.login("admin")
    r = c.post("api/terminals", headers=_xsrf(c))
    name = r.json()["name"] if r.status_code == 200 else "1"
    yield c, r, f"{server.ws_url}terminals/websocket/{name}"
    if r.status_code == 200:
        c.delete(f"api/terminals/{name}", headers=_xsrf(c))


def test_anonymous_lab_redirects_to_login(server):
    r = server.client().get("lab")
    assert r.status_code == 302
    assert r.headers["location"].startswith(f"{BASE}login")


@pytest.mark.parametrize("path", ["api/status", "api/contents", "api/kernels", "api/me"])
def test_anonymous_api_and_status_are_403(server, path):
    assert server.client().get(path).status_code == 403


def test_login_refuses_bad_tokens(server):
    anon = server.client()
    assert anon.get("login").status_code == 403
    assert anon.get("login", params={"launch": ""}).status_code == 403
    assert anon.get("login", params={"launch": server.token(exp_in=-1)}).status_code == 403
    tampered = server.token()
    tampered = tampered[:-4] + ("AAAA" if not tampered.endswith("AAAA") else "BBBB")
    assert anon.get("login", params={"launch": tampered}).status_code == 403
    assert anon.get("login", params={"launch": server.token(sub="8")}).status_code == 403
    assert anon.get("login", params={"launch": sign(os.urandom(32), {})}).status_code == 403
    once = server.token()
    assert server.client().get("login", params={"launch": once}).status_code == 302
    reused = server.client()
    r = reused.get("login", params={"launch": once})
    assert r.status_code == 403
    assert once not in r.text
    assert not [name for name in reused.cookies if name.startswith("username-")]


def test_login_sets_an_httponly_lax_cookie_on_the_base_url(server):
    token = server.token()
    c = server.client()
    r = c.get("login", params={"launch": token, "next": f"{BASE}lab"})
    assert r.status_code == 302
    assert r.headers["location"] == f"{BASE}lab"
    login_cookies = [h for h in r.headers.get_list("set-cookie") if h.startswith("username-")]
    assert len(login_cookies) == 1
    cookie = login_cookies[0]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert f"Path={BASE}" in cookie
    # It ends with the container, not some time after the sign-in.
    assert f"expires={formatdate(server.expires, usegmt=True)}".lower() in cookie.lower()
    assert token not in r.text
    assert c.get("lab").status_code == 200
    assert c.get("api/contents").status_code == 200


@pytest.mark.parametrize("fetch_site", ["cross-site", "none", None, "same-site, cross-site"])
def test_login_needs_a_same_site_navigation(server, fetch_site):
    # Otherwise any site could sign a victim's browser into the attacker's own container,
    # whose trusted notebook output would then run on the shared notebook origin.
    token = server.token()
    r = server.client(fetch_site).get("login", params={"launch": token})
    assert r.status_code == 403
    assert not [h for h in r.headers.get_list("set-cookie") if h.startswith("username-")]
    # Refused before redemption: the same token still signs in from Fione's page.
    assert server.client().get("login", params={"launch": token}).status_code == 302


@pytest.mark.parametrize(
    "referer",
    [
        None,
        "null",
        "",
        "http://127.0.0.1:18081/",  # another page of the same site
        "http://127.0.0.1:18080.evil.example/",
        "http://user@127.0.0.1:18080/",
        "http://127.0.0.1:18080",  # no path: not what a browser sends
        "http://[::1",  # malformed
        "https://127.0.0.1:18080/",
    ],
)
def test_login_needs_fiones_referer(server, referer):
    # A same-site page that is not Fione could otherwise sign a victim into the attacker's
    # container just as a cross-site one could (see the module docstring of the extension).
    token = server.token()
    r = server.client(referer=referer).get("login", params={"launch": token})
    assert r.status_code == 403 and r.text == server.client().get("login").text
    assert not [h for h in r.headers.get_list("set-cookie") if h.startswith("username-")]
    assert server.client().get("login", params={"launch": token}).status_code == 302


def test_login_refuses_a_second_referer(server):
    token = server.token()
    c = server.client(referer=None)
    headers = [("Referer", f"{FIONE_ORIGIN}/"), ("Referer", "http://127.0.0.1:18081/")]
    r = c.get("login", params={"launch": token}, headers=httpx.Headers(headers))
    assert r.status_code == 403
    assert server.client().get("login", params={"launch": token}).status_code == 302


def test_login_accepts_a_full_referer_from_fione(server):
    c = server.client(referer=f"{FIONE_ORIGIN}/notebook")
    assert c.get("login", params={"launch": server.token()}).status_code == 302


def test_login_accepts_a_same_origin_navigation(server):
    r = server.client("same-origin").get("login", params={"launch": server.token()})
    assert r.status_code == 302


def test_login_refuses_a_percent_encoded_launch_key(server):
    token = server.token()
    assert server.client().get(f"login?%6Caunch={token}").status_code == 403
    assert server.client().get("login", params={"launch": token}).status_code == 302


def test_login_without_next_goes_to_lab(server):
    r = server.client().get("login", params={"launch": server.token()})
    assert (r.status_code, r.headers["location"]) == (302, f"{BASE}lab")


@pytest.mark.parametrize(
    "next_url",
    [
        "https://evil.example/",
        "/other/",
        "//evil.example/user/7/lab",
        f"https://evil.example{BASE}lab",
        f"{BASE}../8/lab",
        f"{BASE}%2e%2e/8/lab",
        f"{BASE}lab\\..\\..\\8",
        "/user/77/lab",
    ],
)
def test_next_outside_the_base_url_goes_to_lab(server, next_url):
    r = server.client().get("login", params={"launch": server.token(), "next": next_url})
    assert (r.status_code, r.headers["location"]) == (302, f"{BASE}lab")


def test_next_under_the_base_url_is_kept(server):
    target = f"{BASE}lab/tree/a.ipynb"
    r = server.client().get("login", params={"launch": server.token(), "next": target})
    assert (r.status_code, r.headers["location"]) == (302, target)


def test_token_param_and_header_are_ignored(server):
    anon = server.client()
    assert anon.get("api/contents", params={"token": "x"}).status_code == 403
    assert anon.get("api/contents", headers={"Authorization": "token x"}).status_code == 403
    launch = server.token()
    assert anon.get("api/contents", params={"token": launch}).status_code == 403
    assert anon.get("api/contents", headers={"Authorization": f"token {launch}"}).status_code == 403
    assert anon.get("api/contents", headers={"Authorization": "bearer x"}).status_code == 403
    # A signed-in cookie request is never token-authenticated, so a token does not let it skip
    # the XSRF check.
    c = server.login()
    for kwargs in ({"params": {"token": "x"}}, {"headers": {"Authorization": "token x"}}):
        r = c.post("api/contents", json={"type": "notebook"}, **kwargs)
        assert r.status_code == 403


def test_cookie_post_needs_xsrf(server):
    c = server.login()
    assert c.post("api/contents", json={"type": "notebook"}).status_code == 403
    bad = {"X-XSRFToken": "2|00000000|" + "0" * 32 + "|1"}
    assert c.post("api/contents", json={"type": "notebook"}, headers=bad).status_code == 403
    assert c.post("api/contents", json={"type": "notebook"}, headers=_xsrf(c)).status_code == 201


def test_kernel_runs_code(kernel):
    c, url = kernel
    request = _ws_request(url, cookies=_cookie_header(c))
    assert asyncio.run(_execute(request, "print(6*7)")) == "42\n"
    # Kernels do not inherit the launch key or cookie secret: hygiene, not a boundary, as
    # /proc/<ppid>/environ (same uid) still holds them.
    code = "import os; print(sorted(n for n in os.environ if n.startswith('FIONE_NB_')))"
    visible = "['FIONE_NB_EXPIRES', 'FIONE_NB_ORIGIN', 'FIONE_NB_OWNER']\n"
    assert asyncio.run(_execute(request, code)) == visible


def test_foreign_origin_websocket_is_refused(server, kernel):
    c, url = kernel
    cookies = _cookie_header(c)
    assert _ws_status(_ws_request(url, cookies=cookies, origin="http://evil.example")) == 403
    assert _ws_status(_ws_request(url, cookies=cookies, origin=FIONE_ORIGIN)) == 403
    assert _ws_status(_ws_request(url)) == 403
    assert _ws_status(_ws_request(url, cookies=cookies, origin=server.origin)) == 101


def test_editor_cannot_use_terminals_or_shutdown(server, terminal):
    c = server.login("editor")
    assert c.post("api/terminals", headers=_xsrf(c)).status_code == 403
    assert c.get("api/terminals").status_code == 403
    assert c.post("api/shutdown", headers=_xsrf(c)).status_code == 403
    viewer = server.login("viewer")
    assert viewer.post("api/terminals", headers=_xsrf(viewer)).status_code == 403
    _, created, ws_url = terminal
    assert created.status_code == 200
    assert _ws_status(_ws_request(ws_url)) == 403
    assert _ws_status(_ws_request(ws_url, cookies=_cookie_header(c))) == 403


def _page_config(c: httpx.Client) -> dict:
    found = re.search(
        r'<script id="jupyter-config-data" type="application/json">(.*?)</script>',
        c.get("lab").text,
        re.S,
    )
    assert found, "no page config in the lab page"
    return json.loads(found.group(1))


def test_only_admins_are_shown_terminals(server):
    assert _page_config(server.login("editor"))["terminalsAvailable"] is False
    assert _page_config(server.login("viewer"))["terminalsAvailable"] is False
    assert _page_config(server.login("admin"))["terminalsAvailable"] is True


def test_admin_can_open_a_terminal(terminal):
    c, created, ws_url = terminal
    assert created.status_code == 200

    async def run() -> str:
        ws = await websocket_connect(_ws_request(ws_url, cookies=_cookie_header(c)))
        try:
            await ws.write_message(json.dumps(["stdin", "echo ok\r"]))
            seen = ""
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                raw = await asyncio.wait_for(ws.read_message(), 30)
                assert raw is not None, "the terminal WebSocket closed"
                kind, *rest = json.loads(raw)
                if kind == "stdout":
                    seen += rest[0]
                    if any(line.strip() == "ok" for line in re.split(r"\r?\n", seen)):
                        return seen
            return seen
        finally:
            ws.close()

    out = asyncio.run(run())
    assert any(line.strip() == "ok" for line in re.split(r"\r?\n", out)), out


def test_csp_header(server):
    anon = server.client()
    c = server.login()
    exact = [
        anon.get("lab"),
        anon.get("login"),
        anon.get("login", params={"launch": server.token()}),
        c.get("lab"),
        c.get("lab/tree/a.ipynb"),
    ]
    for r in exact:
        assert r.headers["content-security-policy"] == CSP, (r.request.url, r.status_code)
    # API and file handlers append to the configured policy; they never replace it.
    extended = [
        anon.get("api/status"),
        c.get("api/contents"),
        c.get("api/status"),
        c.get("api/kernelspecs"),
    ]
    for r in extended:
        assert r.headers["content-security-policy"].startswith(CSP + "; "), r.request.url


def test_user_written_html_is_never_served(server, kernel):
    page = "<html><body><script>document.title = 'owned'</script></body></html>"
    targets = [
        server.home / ".local/share/jupyter/labextensions/evil/static/x.html",
        server.home / ".jupyter/x.html",
        server.home / ".jupyter/custom/x.html",
        server.root / "x.html",
    ]
    # Written by the owner's own kernel, as a user would.
    c, url = kernel
    code = (
        "import pathlib\n"
        f"for p in {[str(t) for t in targets]!r}:\n"
        "    p = pathlib.Path(p); p.parent.mkdir(parents=True, exist_ok=True)\n"
        f"    p.write_text({page!r})\n"
        f"d = pathlib.Path({str(server.data_dir)!r}) / 'labextensions/evil/static'\n"
        "try:\n"
        "    d.mkdir(parents=True)\n"
        "    print('data dir writable')\n"
        "except PermissionError:\n"
        "    print('data dir read-only')\n"
    )
    request = _ws_request(url, cookies=_cookie_header(c))
    assert asyncio.run(_execute(request, code)) == "data dir read-only\n"
    assert all(t.read_text() == page for t in targets)

    # The lab extension route does serve files from the environment's extensions...
    builtin = sorted(Path(sys.prefix, "share/jupyter/labextensions").glob("*/static/*.js"))
    assert builtin, "no lab extension is installed in the environment"
    served = builtin[0].relative_to(Path(sys.prefix, "share/jupyter/labextensions"))
    assert c.get(f"lab/extensions/{served.as_posix()}").status_code == 200
    # ...but never the user's.
    anon = server.client()
    for client in (anon, c):
        assert client.get("lab/extensions/evil/static/x.html").status_code == 404
        for path in ("custom/x.html", "static/x.html"):
            r = client.get(path)  # anonymous: a redirect to the login page
            assert r.status_code in (302, 404), (path, r.status_code)
            assert "<script>" not in r.text

    # /files/ wants a same-host Referer (or the XSRF token), as a browser in the lab sends.
    assert c.get("files/x.html").status_code == 403
    files = c.get("files/x.html", headers={"Referer": f"{server.url}lab"})
    assert files.status_code == 200
    assert files.text == page
    assert "sandbox allow-scripts" in files.headers["content-security-policy"]
    assert anon.get("files/x.html").status_code in (302, 403)

    notebook = {
        "type": "notebook",
        "content": {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": "<script>document.title = 'owned'</script>",
                }
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        },
    }
    assert c.put("api/contents/n.ipynb", json=notebook, headers=_xsrf(c)).status_code == 201
    converted = c.get("nbconvert/html/n.ipynb", headers={"Referer": f"{server.url}lab"})
    assert converted.status_code == 200
    assert "sandbox allow-scripts" in converted.headers["content-security-policy"]
    assert anon.get("nbconvert/html/n.ipynb").status_code in (302, 403)


def test_launch_token_never_reaches_the_log(server):
    scrubbed = "/login?[hidden]"
    before = server.log.read_text().count(scrubbed)
    # Refused sign-ins are where tornado would name the request URI, token included.
    anon = server.client()
    accepted = server.token()
    refused = [server.token(exp_in=-1), server.token(sub="8"), accepted[:-4] + "AAAA"]
    for token in refused:
        assert anon.get("login", params={"launch": token}).status_code == 403
    assert anon.get("login", params={"launch": accepted}).status_code == 302
    assert server.client().get("login", params={"launch": accepted}).status_code == 403
    # Also a key the access log's scrubbing would not recognise.
    encoded = server.token()
    assert anon.get(f"login?%6Caunch={encoded}").status_code == 403
    # The access log line is written after the response: wait until all six are there.
    deadline = time.monotonic() + 5
    while server.log.read_text().count(scrubbed) < before + 6 and time.monotonic() < deadline:
        time.sleep(0.1)
    log = server.log.read_text()
    assert log.count(scrubbed) >= before + 6, log
    # No token of this module, nor either half of one, appears anywhere.
    for token in [*server.tokens, *refused]:
        _, payload, signature = token.split(".")
        assert payload not in log
        assert signature not in log


@pytest.mark.parametrize(
    "case",
    ["no-owner", "no-key", "writable-data-dir", "jupyter-path-set"],
)
def test_server_refuses_to_start_without_owner_or_key(tmp_path, case):
    dirs = _layout(tmp_path)
    for name in ("config", "data"):
        dirs[name].chmod(0o555)
    changes = {
        "no-owner": {"FIONE_NB_OWNER": None},
        "no-key": {"FIONE_NB_KEY": None},
        "writable-data-dir": {},
        "jupyter-path-set": {"JUPYTER_PATH": str(tmp_path / "work")},
    }[case]
    if case == "writable-data-dir":
        dirs["data"].chmod(0o755)
    log = tmp_path / "server.log"
    port = _free_port()  # a clash would fail the "fione_notebook: " check below, not pass
    proc = _start(_server_env(dirs, os.urandom(32), **changes), port, dirs["work"], log)
    try:
        code = proc.wait(EXIT_TIMEOUT)
    except subprocess.TimeoutExpired:
        code = None
    finally:
        _stop(proc)
        for name in ("config", "data"):
            dirs[name].chmod(0o755)
    assert code not in (None, 0), log.read_text()
    assert "fione_notebook: " in log.read_text()  # refused by the extension, not by accident
    with pytest.raises(httpx.TransportError):
        httpx.get(f"http://127.0.0.1:{port}{BASE}api/status", timeout=2)


def test_anonymous_api_root_and_metrics(server):
    anon = server.client()
    r = anon.get("api")
    assert r.status_code == 200
    assert set(r.json()) == {"version"}
    assert anon.get("metrics").status_code == 403


def test_lab_settings_and_workspaces_are_not_writable(server):
    # JupyterLab's settings, workspaces, extensions, build, plugins, news and update handlers
    # are @web.authenticated only: the authorizer does not see them, so every role reaches
    # them. Their writes fail here because the config and data dirs are read-only (the image
    # also keeps its environment root-owned) and the gateway refuses settings and workspace
    # writes.
    c = server.login("viewer")
    settings = c.put(
        "lab/api/settings/@jupyterlab/apputils-extension:themes",
        json={"raw": '{"theme": "JupyterLab Dark"}'},
        headers=_xsrf(c),
    )
    workspace = c.put(
        "lab/api/workspaces/x", json={"data": {}, "metadata": {"id": "x"}}, headers=_xsrf(c)
    )
    # Observed: the read-only dirs make both writes fail with a server error.
    assert (settings.status_code, workspace.status_code) == (500, 500)
    assert not any(server.data_dir.rglob("*"))
