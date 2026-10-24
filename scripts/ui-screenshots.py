"""Save screenshots of the web UI for review: every page in the light and dark theme, on a
desktop and a phone viewport, plus a few Japanese ones.

    uv run playwright install chromium   # once
    uv run python scripts/ui-screenshots.py OUTPUT_DIR

Starts Fione on a free port with a temporary data directory, creates the first admin, signs in
and creates two projects through the UI, then walks the EasyML wizard with the iris data (a real
training run of at most a minute, a prediction, a failed and a cancelled run) and writes PNGs to
OUTPUT_DIR. Fails if a page logs a console error (a Content-Security-Policy violation, say),
raises one, or scrolls sideways.
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright
from sklearn.datasets import load_iris

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


def sign_in(page: Page, base: str, username: str = ADMIN) -> None:
    page.goto(f"{base}/login")
    page.fill("#login-username", username)
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

        # The first admin, created through the form: a wrong token, then mismatched passwords
        # (both shown as translated errors), then the real thing.
        page = s.page("light", "desktop")
        page.goto(f"{base}/first-admin")
        page.fill("#setup-token", "not-the-token")
        page.fill("#setup-username", ADMIN)
        page.fill("#setup-password", PASSWORD)
        page.fill("#setup-password2", PASSWORD)
        submit = "form[data-json-form] button[type=submit]"
        page.click(submit)
        expect(page.locator("[data-form-error]")).to_contain_text("setup token is not correct")
        s.shot(page, "first-admin-error-en-light-desktop", full_page=False)
        page.fill("#setup-token", SETUP_TOKEN)
        page.fill("#setup-password2", "something-else")
        page.click(submit)
        expect(page.locator("[data-form-error]")).to_contain_text("do not match")
        page.fill("#setup-password2", PASSWORD)
        page.click(submit)
        page.wait_for_url(f"{base}/")
        page.context.close()

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
            page.wait_for_selector(f".project-card__link:text-is('{name}')")
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

        # The theme toggle switches and is remembered across a reload.
        page = s.page("light", "desktop")
        sign_in(page, base)
        page.click("[data-theme-toggle]")
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        expect(page.locator("[data-theme-toggle]").first).to_have_attribute("aria-pressed", "true")
        s.shot(page, "theme-toggled-dark-en-light-desktop", full_page=False)

        # Tabs by keyboard: ArrowRight selects and shows the next tab; the focus ring shows.
        page.goto(f"{base}/_design")
        first = page.locator("#light-tab-overview")
        first.focus()
        page.keyboard.press("ArrowRight")
        expect(page.locator("#light-tab-columns")).to_have_attribute("aria-selected", "true")
        expect(page.locator("#light-tab-columns")).to_be_focused()
        expect(page.locator("#light-panel-columns")).to_be_visible()
        expect(page.locator("#light-panel-overview")).to_be_hidden()
        page.locator("#light-tab-columns").scroll_into_view_if_needed()
        s.shot(page, "design-tabs-keyboard-en-dark-desktop", full_page=False)

        # Toasts: no kind means success; errors are capped at 3 (oldest dropped), a repeated
        # message shows once, and only confirmations go away by themselves.
        page.evaluate("window.fione.showToast('Saved.')")
        for message in ("Error 1", "Error 2", "Error 2", "Error 3", "Error 4"):
            page.evaluate("m => window.fione.showToast(m, 'danger')", message)
        expect(page.locator("#toasts .toast-success")).to_have_count(1)
        expect(page.locator("#toasts .toast-danger .toast__text")).to_have_text(
            ["Error 2", "Error 3", "Error 4"]
        )
        page.wait_for_timeout(400)  # let the slide-in animation finish
        s.shot(page, "toasts-en-dark-desktop", full_page=False)
        page.wait_for_timeout(6500)
        expect(page.locator("#toasts .toast-success")).to_have_count(0)
        expect(page.locator("#toasts .toast-danger")).to_have_count(3)
        page.context.close()

        easyml(s, base)
        browser.close()


def write_data(directory: Path) -> dict[str, Path]:
    """The CSV files the wizard is shown with."""
    frame = load_iris(as_frame=True).frame
    frame["species"] = frame.pop("target").map({0: "setosa", 1: "versicolor", 2: "virginica"})
    files = {
        "iris": directory / "iris.csv",
        "iris_test": directory / "iris_test.csv",
        "partial": directory / "iris_partial.csv",
        "empty": directory / "empty.csv",
        "gaps": directory / "gaps.csv",
    }
    frame.to_csv(files["iris"], index=False)
    frame.drop(columns=["species"]).to_csv(files["iris_test"], index=False)
    frame[["sepal length (cm)", "petal width (cm)"]].to_csv(files["partial"], index=False)
    files["empty"].write_bytes(b"")
    gaps = frame.head(60).copy()
    gaps.loc[::7, "species"] = None  # the column to predict has gaps: training refuses it
    gaps.to_csv(files["gaps"], index=False)
    return files


def upload_file(page: Page, path: Path) -> None:
    page.set_input_files("#upload-file", str(path))
    page.click("form[data-upload-form] button[type=submit]")
    page.wait_for_load_state()


def shoot_all(
    s: "Shooter", base: str, url: str, name: str, langs=("en",), username: str = ADMIN
) -> None:
    for lang, scheme, viewport in s.variants(langs):
        page = s.page(scheme, viewport, lang)
        sign_in(page, base, username)
        page.goto(base + url)
        wait_settled(page)
        s.shot(page, f"{name}-{lang}-{scheme}-{viewport}")
        page.context.close()


def wait_for_url(page: Page, pattern: str, seconds: int) -> None:
    """Wait while the page polls (wait_for_url evaluates nothing, so the CSP allows it)."""
    page.wait_for_url(pattern, timeout=seconds * 1000)


def easyml(s: "Shooter", base: str) -> None:
    with tempfile.TemporaryDirectory() as work:
        files = write_data(Path(work))
        page = s.page("light", "desktop")
        sign_in(page, base)
        page.click(".project-card__link:text-is('Iris species')")
        page.wait_for_url("**/projects/*")
        project = page.url.removeprefix(base)
        page.context.close()
        shoot_all(s, base, project, "project-empty")
        shoot_all(s, base, project + "/upload", "upload")

        # Upload errors in plain words, then the real upload.
        page = s.page("light", "desktop")
        sign_in(page, base)
        page.goto(base + project + "/upload")
        upload_file(page, files["empty"])
        expect(page.locator("#upload-error")).to_contain_text("The file is empty")
        s.shot(page, "upload-error-en-light-desktop")
        upload_file(page, files["iris"])
        page.wait_for_url("**/analyze")
        analysis = page.url.removeprefix(base)

        # Changing the column to predict refreshes the section below it (HTMX) and keeps focus.
        page.focus("#target-select")
        page.select_option("#target-select", "petal width (cm)")
        wait_settled(page)
        expect(page.locator("#task-regression")).to_be_checked()
        expect(page.locator("#target-select")).to_be_focused()
        s.shot(page, "analysis-other-target-en-light-desktop")
        page.select_option("#target-select", "species")
        wait_settled(page)
        expect(page.locator("#task-classification")).to_be_checked()
        # Typing custom minutes picks "other"; no input column is refused inline by the server.
        page.fill("#runtime-custom-minutes", "5")
        expect(page.locator("#runtime-custom")).to_be_checked()
        page.click("[data-check-none]")
        page.click("#run-button")
        page.wait_for_selector("#run-errors")
        expect(page.locator("#run-errors")).to_be_focused()
        s.shot(page, "analysis-error-en-light-desktop")
        page.context.close()
        shoot_all(s, base, analysis, "analysis", ("en", "ja"))

        # Train for at most a minute; the progress page polls and moves on by itself.
        page = s.page("light", "desktop")
        sign_in(page, base)
        page.goto(base + analysis)
        page.check("#runtime-1")
        page.click("#run-button")
        page.wait_for_url("**/jobs/*")
        job = page.url.removeprefix(base)
        page.wait_for_selector("[data-job-status=running]", timeout=60_000)
        page.wait_for_timeout(3000)  # a few polls: models are being tried
        wait_settled(page)
        running = 0
        for lang, scheme, viewport in s.variants():
            other = s.page(scheme, viewport, lang)
            sign_in(other, base)
            other.goto(base + job)
            if other.locator("[data-job-status=running]").count():
                s.shot(other, f"progress-{lang}-{scheme}-{viewport}")
                running += 1
            other.context.close()
        if running < len(list(s.variants())):
            s.errors.append(f"only {running} shots of the running job: training ended too soon")
        page.click("details.confirm > summary")
        s.shot(page, "progress-cancel-panel-en-light-desktop", full_page=False)
        page.click("[data-confirm-close]")
        expect(page.locator("details.confirm > summary")).to_be_focused()
        wait_for_url(page, "**/summary", 180)
        summary = page.url.removeprefix(base)
        page.context.close()
        shoot_all(s, base, summary, "summary", ("en", "ja"))
        shoot_all(s, base, job, "progress-done")
        model = summary.removesuffix("/summary")

        # A new prediction: the columns the model needs, a file missing some, then the real one.
        shoot_all(s, base, model + "/predict", "predict")
        page = s.page("light", "desktop")
        sign_in(page, base)
        page.goto(base + model + "/predict")
        upload_file(page, files["partial"])
        expect(page.locator("#upload-error")).to_contain_text("missing 2 columns")
        s.shot(page, "predict-missing-en-light-desktop")
        upload_file(page, files["iris_test"])
        page.wait_for_url("**/predict?dataset=*")
        columns = page.url.removeprefix(base)
        page.uncheck("#out-1")
        page.click("form[data-run-form] button[type=submit]")
        wait_for_url(page, "**/result", 120)
        result = page.url.removeprefix(base)
        link = page.locator("a[download][href*='/download']").first.get_attribute("href")
        response = page.request.get(base + link)
        assert response.ok and "predict_iris_test.csv" in response.headers["content-disposition"]
        page.context.close()
        shoot_all(s, base, columns, "predict-columns")
        shoot_all(s, base, result, "result")

        # A run that fails (gaps in the column to predict) and one that is cancelled.
        page = s.page("light", "desktop")
        sign_in(page, base)
        page.goto(base + project + "/upload")
        upload_file(page, files["gaps"])
        page.wait_for_url("**/analyze")
        s.shot(page, "analysis-warning-en-light-desktop")
        page.check("#runtime-1")
        page.click("#run-button")
        page.wait_for_url("**/jobs/*")
        failed = page.url.removeprefix(base)
        page.wait_for_selector("[data-job-status=failed]", timeout=120_000)
        page.goto(base + analysis)
        page.check("#runtime-1")
        page.click("#run-button")
        page.wait_for_url("**/jobs/*")
        page.click("details.confirm > summary")
        page.click("details.confirm button[type=submit]")
        page.wait_for_selector("[data-job-status=cancelled]", timeout=60_000)
        cancelled = page.url.removeprefix(base)
        page.context.close()
        shoot_all(s, base, failed, "progress-failed")
        shoot_all(s, base, cancelled, "progress-cancelled")
        shoot_all(s, base, project, "project")

        # The error pages: an unknown path, and a write page for a member who may only view.
        shoot_all(s, base, "/no-such-page", "not-found")
        page = s.page("light", "desktop")
        sign_in(page, base)
        page.goto(base + project)
        csrf = {"X-CSRF-Token": page.get_attribute("meta[name=csrf-token]", "content")}
        user = {"username": "viewer", "password": PASSWORD, "role": "editor"}
        assert page.request.post(f"{base}/api/v1/users", data=user, headers=csrf).ok
        share = {"username": "viewer", "access": "viewer"}
        api_project = project.replace("/projects/", "/api/v1/projects/")
        assert page.request.post(f"{base}{api_project}/share", data=share, headers=csrf).ok
        page.context.close()
        shoot_all(s, base, project, "project-viewer", username="viewer")
        shoot_all(s, base, project + "/upload", "forbidden", username="viewer")


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
            "FIONE_RUNNER_ENABLED": "true",
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
