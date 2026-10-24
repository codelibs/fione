"""Save screenshots of the web UI for review: every page in the light and dark theme, on a
desktop and a phone viewport, plus a few Japanese ones.

    uv run playwright install chromium   # once
    uv run python scripts/ui-screenshots.py OUTPUT_DIR

Starts Fione on a free port with a temporary data directory, creates the first admin, signs in
and creates two projects through the UI, then writes PNGs to OUTPUT_DIR. Fails if a page logs
a console error (a Content-Security-Policy violation, say), raises one, or scrolls sideways.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

SETUP_TOKEN = "screenshot-setup-token-0123456789"
ADMIN, PASSWORD = "admin", "screenshot-password"
VIEWPORTS = {"desktop": (1280, 800), "phone": (390, 844)}
SCHEMES = ("light", "dark")
# After an HTMX swap: the request has finished and the new content has settled.
SETTLED = "!document.querySelector('.htmx-request, .htmx-settling, .htmx-swapping')"


def wait_settled(page: Page) -> None:
    # Polled from here: wait_for_function evaluates with eval, which the page's CSP blocks.
    for _ in range(100):
        if page.evaluate(SETTLED):
            return
        page.wait_for_timeout(50)
    raise SystemExit("HTMX did not settle")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_until_up(base: str, server: subprocess.Popen) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise SystemExit("the server exited during startup")
        try:
            urllib.request.urlopen(f"{base}/api/v1/auth/status", timeout=2)
            return
        except OSError:
            time.sleep(0.3)
    raise SystemExit("the server did not start")


def create_admin(base: str) -> None:
    body = {"setup_token": SETUP_TOKEN, "username": ADMIN, "password": PASSWORD}
    request = urllib.request.Request(
        f"{base}/api/v1/auth/first-admin",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(request, timeout=30)


class Shooter:
    def __init__(self, browser, base: str, out: Path, errors: list[str]):
        self.browser, self.base, self.out = browser, base, out
        self.errors = errors
        self.last = "start"

    def page(self, scheme: str, viewport: str, lang: str = "en") -> Page:
        width, height = VIEWPORTS[viewport]
        context = self.browser.new_context(
            viewport={"width": width, "height": height},
            color_scheme=scheme,
            locale="ja-JP" if lang == "ja" else "en-US",
            extra_http_headers={"Accept-Language": lang},
        )
        page = context.new_page()
        page.on("console", lambda m: self.console(page, m))
        page.on("pageerror", lambda e: self.errors.append(f"{page.url}: {e}"))
        return page

    def console(self, page: Page, message) -> None:
        # The wrong password and the blank project name fail on purpose (401, 422); CSP
        # violations ("Refused to ...") and script errors count.
        if message.type == "error" and not message.text.startswith("Failed to load resource"):
            self.errors.append(f"{page.url} (after {self.last}): {message.text}")

    def shot(self, page: Page, name: str, *, full_page: bool = True) -> None:
        if page.evaluate("document.documentElement.scrollWidth > window.innerWidth"):
            self.errors.append(f"{name}: the page scrolls horizontally")
        self.last = name
        path = self.out / f"{name}.png"
        page.screenshot(path=str(path), full_page=full_page)
        print(path)

    def variants(self, langs=("en",)):
        for lang in langs:
            for scheme in SCHEMES:
                for viewport in VIEWPORTS:
                    yield lang, scheme, viewport


def sign_in(page: Page, base: str) -> None:
    page.goto(f"{base}/login")
    page.fill("#login-username", ADMIN)
    page.fill("#login-password", PASSWORD)
    page.click("form[data-json-form] button[type=submit]")
    page.wait_for_url(f"{base}/")


def run(base: str, out: Path, errors: list[str]) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        s = Shooter(browser, base, out, errors)
        extra_ja = [("ja", "light", "desktop"), ("ja", "dark", "phone")]
        variants = list(s.variants()) + extra_ja

        for lang, scheme, viewport in variants:
            page = s.page(scheme, viewport, lang)
            page.goto(f"{base}/first-admin")
            s.shot(page, f"first-admin-{lang}-{scheme}-{viewport}")
            page.context.close()

        create_admin(base)

        for lang, scheme, viewport in variants:
            page = s.page(scheme, viewport, lang)
            page.goto(f"{base}/login")
            s.shot(page, f"login-{lang}-{scheme}-{viewport}")
            page.fill("#login-username", ADMIN)
            page.fill("#login-password", "wrong-password")
            page.click("form[data-json-form] button[type=submit]")
            page.wait_for_selector("[data-form-error]:not([hidden])")
            s.shot(page, f"login-error-{lang}-{scheme}-{viewport}")
            page.context.close()

        for lang, scheme, viewport in variants:
            page = s.page(scheme, viewport, lang)
            sign_in(page, base)
            s.shot(page, f"home-empty-{lang}-{scheme}-{viewport}")
            page.context.close()

        # Two projects, created through the HTMX form (the toast of the second one shows).
        page = s.page("light", "desktop")
        sign_in(page, base)
        for name in ("Iris species", "売上予測 2026"):
            page.fill("#project-name", name)
            page.click("#new-project button[type=submit]")
            page.wait_for_selector(f".project-card__name:text-is('{name}')")
            wait_settled(page)
        s.shot(page, "home-projects-toast-en-light-desktop", full_page=False)
        page.fill("#project-name", "   ")  # blank: the server's inline error
        page.click("#new-project button[type=submit]")
        page.wait_for_selector(".field__error")
        wait_settled(page)
        s.shot(page, "home-name-error-en-light-desktop", full_page=False)
        page.context.close()

        for lang, scheme, viewport in variants:
            page = s.page(scheme, viewport, lang)
            sign_in(page, base)
            s.shot(page, f"home-projects-{lang}-{scheme}-{viewport}")
            if viewport == "phone":
                page.click(".nav-toggle")
                page.click(".menu > summary")
                s.shot(page, f"home-menu-{lang}-{scheme}-{viewport}", full_page=False)
            page.goto(f"{base}/_design")
            s.shot(page, f"design-{lang}-{scheme}-{viewport}")
            page.context.close()

        browser.close()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory() as data_dir:
        env = {
            **os.environ,
            "FIONE_DATA_DIR": data_dir,
            "FIONE_SETUP_TOKEN": SETUP_TOKEN,
            "FIONE_RUNNER_ENABLED": "false",
            # The script signs in with a wrong password once per variant on purpose.
            "FIONE_LOGIN_MAX_FAILURES": "1000",
        }
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "fione.api.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            env=env,
        )
        errors: list[str] = []
        try:
            wait_until_up(base, server)
            run(base, out, errors)
        finally:
            server.terminate()
            server.wait(timeout=30)
            if errors:
                print("\n".join(["Page errors:", *errors]), file=sys.stderr)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
