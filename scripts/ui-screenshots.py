"""Save screenshots of the web UI for review: every page in the light and dark theme, on a
desktop and a phone viewport, plus a few Japanese ones.

    uv run playwright install chromium   # once
    uv run python scripts/ui-screenshots.py OUTPUT_DIR

Starts Fione on a free port with a temporary data directory, creates the first admin, signs in
and creates two projects through the UI, then walks the EasyML wizard with the iris data (a real
training run of at most a minute, a prediction, a failed and a cancelled run) and writes PNGs to
OUTPUT_DIR. The notebook page is shown not running and starting, against a stub launcher this
script runs (a running notebook needs the Docker stack: tests/e2e). Fione-kun's page is shown
against the fake LLM of tests/fake_llm.py, run as a process, with a pending training proposal.
Fails if a page logs a
console error (a Content-Security-Policy violation, say), raises one, or scrolls sideways.
"""

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd
from playwright.sync_api import Page, expect, sync_playwright
from sklearn.datasets import load_iris

from fione import db
from fione.api.app import DB_FILE
from fione.auth import service as auth_service
from fione.auth.tokens import TokenScope

FAKE_LLM = Path(__file__).resolve().parent.parent / "tests" / "fake_llm.py"
SETUP_TOKEN = "screenshot-setup-token-0123456789"
ADMIN, PASSWORD = "admin", "screenshot-password"
LAUNCHER_SECRET = "screenshot-launcher-secret-0123456789"
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
        self.mode: str | None = None
        self.last = "start"

    def page(self, scheme: str, viewport: str, lang: str = "en") -> Page:
        width, height = VIEWPORTS[viewport]
        context = self.browser.new_context(
            viewport={"width": width, "height": height},
            color_scheme=scheme,
            locale="ja-JP" if lang == "ja" else "en-US",
            extra_http_headers={"Accept-Language": lang},
        )
        if self.mode:  # the view preference (simple unless set)
            context.add_cookies([{"name": "fione_mode", "value": self.mode, "url": self.base}])
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


def sign_in(page: Page, base: str, username: str = ADMIN, password: str = PASSWORD) -> None:
    page.goto(f"{base}/login")
    page.fill("#login-username", username)
    page.fill("#login-password", password)
    page.click("form[data-json-form] button[type=submit]")
    page.wait_for_url(f"{base}/")


def run(base: str, out: Path, errors: list[str], data_dir: Path) -> None:
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

        project = easyml(s, base)
        view_preference(s, base, project)
        s.mode = "detailed"  # the AutoML screens are the detailed view's
        automl(s, base, project)
        model_screens(s, base, project)
        account_and_admin(s, base, project, data_dir)
        notebook_page(s, base)
        assistant_page(s, base, project)
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
        "constant": directory / "constant.csv",
    }
    frame.to_csv(files["iris"], index=False)
    frame.drop(columns=["species"]).to_csv(files["iris_test"], index=False)
    frame[["sepal length (cm)", "petal width (cm)"]].to_csv(files["partial"], index=False)
    files["empty"].write_bytes(b"")
    gaps = frame.head(60).copy()
    gaps.loc[::7, "species"] = None  # the column to predict has gaps: training refuses it
    gaps.to_csv(files["gaps"], index=False)
    constant = pd.DataFrame({"flat": [1] * 40, "label": ["yes", "no"] * 20})
    constant.to_csv(files["constant"], index=False)
    return files


def upload_file(page: Page, path: Path) -> None:
    page.set_input_files("#upload-file", str(path))
    page.click("form[data-upload-form] button[type=submit]")
    page.wait_for_load_state()


def submit_twice(page: Page, selector: str, suffix: str) -> int:
    """Click a submit button, then click it again while its request is held back; returns how
    many requests the form sent. easyml.js must make it one (the busy button is disabled, and
    a busy form's second submit is cancelled); without it the browser would send a second."""
    held = []
    pattern = re.compile(re.escape(suffix) + "$")
    page.route(pattern, lambda route: held.append(route))  # each request waits here
    button = page.locator(selector)
    button.scroll_into_view_if_needed()
    box = button.bounding_box()
    try:
        button.click(no_wait_after=True)
        page.wait_for_timeout(300)
        # The page is navigating, so locators would wait: click where the button is.
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.wait_for_timeout(300)
        return len(held)
    finally:
        if held:
            held[-1].continue_()  # the last one is the one the page waits for
        page.unroute(pattern)


def shoot_all(
    s: "Shooter",
    base: str,
    url: str,
    name: str,
    langs=("en",),
    username: str = ADMIN,
    charts: bool = False,
    ready: str | None = None,
) -> None:
    for lang, scheme, viewport in s.variants(langs):
        page = s.page(scheme, viewport, lang)
        sign_in(page, base, username)
        page.goto(base + url)
        if ready:  # a fragment the page loads by itself has been swapped in
            page.locator(ready).first.wait_for(timeout=60_000)
        wait_settled(page)
        if charts:
            charts_drawn(s, page, name)
        s.shot(page, f"{name}-{lang}-{scheme}-{viewport}")
        page.context.close()


def charts_drawn(s: "Shooter", page: Page, name: str) -> None:
    """Every visible chart has been drawn: a canvas of non-zero size."""
    visible = page.locator("[data-chart]:visible, [data-chart-spec]:visible")
    if not visible.count():
        s.errors.append(f"{name}: no chart shown")
    for index in range(visible.count()):
        canvas = visible.nth(index).locator("canvas").first
        canvas.wait_for(timeout=10_000)
        box = canvas.bounding_box()
        if not box or box["width"] < 10 or box["height"] < 10:
            s.errors.append(f"{name}: a chart was not drawn ({box})")
    page.wait_for_timeout(1200)  # ECharts' entry animation (1 s) has finished


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
        runs = submit_twice(page, "#run-button", "/run")
        if runs != 1:
            s.errors.append(f"submitting the run form twice sent {runs} requests")
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
        shoot_all(s, base, result, "result", ("en", "ja"), ready="#why .why-row")

        # A run the engine would refuse (gaps in the column to predict) is refused inline;
        # one that fails in the worker (only a constant input), and one that is cancelled.
        page = s.page("light", "desktop")
        sign_in(page, base)
        page.goto(base + project + "/upload")
        upload_file(page, files["gaps"])
        page.wait_for_url("**/analyze")
        s.shot(page, "analysis-warning-en-light-desktop")
        page.check("#runtime-1")
        page.click("#run-button")
        page.wait_for_selector("#run-errors")
        expect(page.locator("#run-errors")).to_contain_text("Training would refuse")
        s.shot(page, "analysis-refused-en-light-desktop", full_page=False)
        page.goto(base + project + "/upload")
        upload_file(page, files["constant"])
        page.wait_for_url("**/analyze")
        page.check("[name=inputs][value=flat]")  # unchecked by Fione: no use for training
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
        cancels = submit_twice(page, "details.confirm button[type=submit]", "/cancel")
        if cancels != 1:
            s.errors.append(f"submitting the cancel form twice sent {cancels} requests")
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
        return project


def automl(s: "Shooter", base: str, project: str) -> None:
    """The AutoML screens, on the data the wizard left behind (iris, its test file...)."""
    page = s.page("light", "desktop")
    sign_in(page, base)
    page.goto(base + project + "/datasets")
    link = page.locator("table a", has_text=re.compile("^iris$")).first
    dataset = link.get_attribute("href")
    page.click("details.upload-panel > summary")
    s.shot(page, "datasets-upload-en-light-desktop", full_page=False)
    page.context.close()
    shoot_all(s, base, project + "/datasets", "datasets")
    shoot_all(s, base, dataset, "dataset-summary", ("en", "ja"))
    for tab in ("columns", "data"):
        shoot_all(s, base, f"{dataset}?tab={tab}", f"dataset-{tab}", ("en", "ja"))
    shoot_all(
        s, base, f"{dataset}?tab=correlation", "dataset-correlation", ("en", "ja"), charts=True
    )
    numeric = dataset + "/columns/" + "petal%20length%20(cm)"
    shoot_all(s, base, numeric, "column-numeric", charts=True)
    shoot_all(s, base, dataset + "/columns/species", "column-categorical", charts=True)
    shoot_all(s, base, dataset + "/train", "train", ("en", "ja"))
    shoot_all(s, base, project + "/jobs", "jobs")

    # The chart's accessible name stays the translated one (ECharts' aria writes English).
    page = s.page("light", "desktop", "ja")
    sign_in(page, base)
    page.goto(f"{base}{dataset}?tab=correlation")
    charts_drawn(s, page, "dataset-correlation-ja-label")
    label = page.get_attribute("#corr-chart", "aria-label")
    if "相関" not in (label or ""):
        s.errors.append(f"the Japanese chart lost its label: {label!r}")
    page.context.close()

    page = s.page("dark", "desktop")
    sign_in(page, base)
    # A chart in a hidden tab is drawn when the tab is opened; its tooltip is canvas text.
    page.goto(base + dataset)
    page.click("#tab-correlation")
    charts_drawn(s, page, "dataset-correlation-tab")
    box = page.locator("#corr-chart canvas").first.bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.6, box["y"] + 60)
    page.wait_for_timeout(400)
    s.shot(page, "dataset-correlation-tooltip-en-dark-desktop", full_page=False)
    # Keyboard tabs: ArrowRight moves to the next tab.
    page.focus("#tab-correlation")
    page.keyboard.press("Home")
    expect(page.locator("#tab-summary")).to_be_focused()
    # The theme toggle redraws the chart in the other theme's colours.
    page.goto(base + numeric)
    charts_drawn(s, page, "column-theme")
    page.click("[data-theme-toggle]")
    page.wait_for_timeout(300)
    s.shot(page, "column-numeric-toggled-en-dark-desktop", full_page=False)
    # The training form: an inline error, nothing queued.
    page.goto(base + dataset + "/train")
    page.fill("#f-nfolds", "1")
    page.evaluate("() => document.getElementById('f-nfolds').removeAttribute('min')")
    page.click("#run-button")
    page.wait_for_selector("#run-errors")
    s.shot(page, "train-error-en-dark-desktop", full_page=False)
    # The job list's confirm panel.
    page.goto(base + project + "/jobs")
    page.locator("#job-list details.confirm-inline > summary").first.click()
    s.shot(page, "jobs-confirm-en-dark-desktop", full_page=False)
    page.context.close()


def view_preference(s: "Shooter", base: str, project: str) -> None:
    """The simple and the detailed view of the same dashboard, switched from the account menu."""
    page = s.page("light", "desktop")
    sign_in(page, base)
    page.goto(base + project)
    expect(page.locator(".subnav a", has_text="Jobs")).to_have_count(0)
    s.shot(page, "view-simple-en-light-desktop", full_page=False)
    page.click(".menu > summary")
    s.shot(page, "view-menu-en-light-desktop", full_page=False)
    page.click("button[name=mode][value=detailed]")
    page.wait_for_url(base + project)
    expect(page.locator(".subnav a", has_text="Jobs")).to_have_count(1)
    s.shot(page, "view-detailed-en-light-desktop", full_page=False)
    page.click(".menu > summary")
    page.click("button[name=mode][value=simple]")
    page.wait_for_url(base + project)
    page.context.close()


def model_screens(s: "Shooter", base: str, project: str) -> None:
    """The models list, every tab of a model page, import, and the Python modules."""
    page = s.page("light", "desktop")
    sign_in(page, base)
    page.goto(base + project + "/models")
    model = page.locator("table th.cell-name a").first.get_attribute("href")
    # The explain job queued after training: its result is what the Explain tab shows.
    explained = f"{base}/api/v1/models/{model.rsplit('/', 1)[1]}/explanations"
    deadline = time.monotonic() + 180
    while (status := page.request.get(explained).json()["status"]) != "done":
        if status in ("failed", "cancelled") or time.monotonic() > deadline:
            raise SystemExit(f"the explanation was not computed ({status})")
        time.sleep(1)
    page.context.close()
    shoot_all(s, base, project + "/models", "models", charts=True)
    shoot_all(s, base, model, "model-overview", ("en", "ja"))
    for tab, charts in (
        ("leaderboard", False),
        ("importance", True),
        ("history", True),
        ("metrics", False),
    ):
        shoot_all(s, base, f"{model}?tab={tab}", f"model-{tab}", charts=charts)
    shoot_all(s, base, f"{model}?tab=history", "model-history", ("ja",), charts=True)
    shoot_all(s, base, f"{model}?tab=explain", "model-explain", ("en", "ja"), charts=True)
    shoot_all(s, base, project + "/models/import", "import", ("en", "ja"))
    shoot_all(s, base, "/modules", "modules", ("en", "ja"))
    shoot_all(s, base, "/modules/upload", "module-upload", ("en", "ja"))

    page = s.page("dark", "desktop")
    sign_in(page, base)
    # A bad archive is explained; the trust box comes back unchecked.
    page.goto(base + project + "/models/import")
    with tempfile.TemporaryDirectory() as work:
        bad = Path(work) / "not-a-model.zip"
        bad.write_bytes(b"not a zip")
        page.set_input_files("#import-file", str(bad))
        page.check("#trust-foreign")
        page.click("form[data-upload-form] button[type=submit]")
        page.wait_for_selector("#upload-error")
        expect(page.locator("#trust-foreign")).not_to_be_checked()
        s.shot(page, "import-error-en-dark-desktop", full_page=False)
        # A module upload without the acknowledgement is refused by the server.
        source = Path(work) / "mine.py"
        source.write_text(
            'MODULE = {"name": "Mine", "kind": "frame",'
            ' "params": {"type": "object", "properties": {}}}\n'
            "def run(df, params, ctx):\n    return df\n"
        )
        page.goto(base + "/modules/upload")
        page.fill("#module-id", "mine")
        page.set_input_files("#module-file", str(source))
        page.evaluate("() => document.getElementById('acknowledge').removeAttribute('required')")
        page.click("form[data-upload-form] button[type=submit]")
        page.wait_for_selector("#upload-error")
        s.shot(page, "module-upload-error-en-dark-desktop", full_page=False)
        page.set_input_files("#module-file", str(source))
        page.check("#acknowledge")
        page.click("form[data-upload-form] button[type=submit]")
        page.wait_for_url(base + "/modules")
    s.shot(page, "modules-uploaded-en-dark-desktop")
    # The history chart's legend and the model delete panel.
    page.goto(base + model + "?tab=history")
    charts_drawn(s, page, "model-history-tab")
    page.goto(base + project + "/models")
    page.locator("details.confirm-inline > summary").first.click()
    s.shot(page, "models-delete-panel-en-dark-desktop", full_page=False)
    page.context.close()


def seed_scoped_tokens(data_dir: Path) -> None:
    """A notebook token and an expired one for the admin, so the account page shows both."""
    with closing(db.connect(data_dir / DB_FILE)) as conn:
        (admin_id,) = conn.execute("SELECT id FROM users WHERE username = ?", (ADMIN,)).fetchone()
        auth_service.create_token(
            conn,
            admin_id,
            "notebook session",
            scope=TokenScope.NOTEBOOK,
            expires_at=auth_service.expiry_after(12 * 3600),
        )
        auth_service.create_token(
            conn, admin_id, "last week's script", expires_at=auth_service.expiry_after(-3600)
        )


def account_and_admin(s: "Shooter", base: str, project: str, data_dir: Path) -> None:
    """The account page (a new token shown once, a password change), the users, sharing and
    system status screens. The admin's own password and role are never changed: every other
    step signs in with them."""
    page = s.page("light", "desktop")
    sign_in(page, base)
    page.goto(base + "/admin/users")
    for username, role in (("editor1", "editor"), ("viewer1", "viewer")):
        page.click("details.card > summary")
        page.fill("#new-username", username)
        page.fill("#new-password", PASSWORD)
        page.select_option("#new-role", role)
        page.click("form[action='/admin/users'] button[type=submit]")
        page.wait_for_url(re.compile(r"/admin/users\?done=created"))
    s.shot(page, "users-created-en-light-desktop", full_page=False)
    # One user may run notebooks, so both states of the column are shown.
    page.locator("tr", has=page.locator("th", has_text="editor1")).get_by_role(
        "button", name="Allow"
    ).click()
    page.wait_for_url(re.compile(r"/admin/users\?done=notebook"))
    # One's own account cannot be deleted: the reason is shown.
    me = page.locator("tr", has=page.locator("th", has_text="admin")).first
    if me.locator("summary").count():
        s.errors.append("users: the admin's own row offers changes")
    other = page.locator("tr", has=page.locator("th", has_text="editor1")).first
    other.locator("details.confirm-inline > summary", has_text="Delete").click()
    s.shot(page, "users-delete-panel-en-light-desktop", full_page=False)
    page.context.close()
    shoot_all(s, base, "/admin/users", "users", ("en", "ja"))
    # On a phone the rows stack: every user's actions are in view, no sideways table.
    page = s.page("light", "phone")
    sign_in(page, base)
    page.goto(base + "/admin/users")
    box = (
        page.locator("tr", has=page.locator("th", has_text="viewer1"))
        .locator("details.confirm-inline > summary", has_text="Delete")
        .bounding_box()
    )
    if not box or box["x"] + box["width"] > 390:
        s.errors.append(f"users: the actions are out of view on a phone ({box})")
    page.context.close()
    shoot_all(s, base, "/admin/system", "system", ("en", "ja"))
    seed_scoped_tokens(data_dir)
    shoot_all(s, base, "/account", "account", ("en", "ja"))

    # A new token: its secret is shown once, and gone after a reload.
    for lang, scheme, viewport in (("en", "light", "desktop"), ("ja", "dark", "phone")):
        page = s.page(scheme, viewport, lang)
        sign_in(page, base)
        page.goto(base + "/account")
        page.fill("#token-name", "nightly report")
        page.click("form[action='/account/tokens'] button[type=submit]")
        page.wait_for_selector(".secret-panel")
        if not re.search(r"fione_[A-Za-z0-9_-]{20,}", page.inner_text(".secret-panel")):
            s.errors.append("account: the new token's secret is not shown")
        s.shot(page, f"account-token-{lang}-{scheme}-{viewport}", full_page=False)
        page.goto(base + "/")
        page.go_back()  # from the page cache or the server: either way, no secret
        if page.locator(".secret-panel").count():
            s.errors.append("account: the secret is shown again after Back")
        page.reload()
        if page.locator(".secret-panel").count():
            s.errors.append("account: the secret is shown again after a reload")
        page.context.close()

    # Wrong current password (inline), then a real change by editor1 (not the admin).
    page = s.page("dark", "desktop")
    sign_in(page, base, "editor1")
    page.goto(base + "/account")
    page.fill("#current-password", "not-my-password")
    page.fill("#new-password", "another-password-1")
    page.fill("#confirm-password", "another-password-1")
    page.click("form[action='/account/password'] button[type=submit]")
    page.wait_for_selector("#current-password-error")
    s.shot(page, "account-password-error-en-dark-desktop", full_page=False)
    page.fill("#current-password", PASSWORD)
    page.fill("#new-password", "another-password-1")
    page.fill("#confirm-password", "another-password-1")
    page.click("form[action='/account/password'] button[type=submit]")
    page.wait_for_url(base + "/account?done=password")
    s.shot(page, "account-password-changed-en-dark-desktop", full_page=False)
    # Not an administrator: the friendly 403 page.
    page.goto(base + "/admin/system")
    s.shot(page, "system-forbidden-en-dark-desktop", full_page=False)
    page.context.close()

    # Sharing: an unknown name is explained, then viewer1 is added.
    page = s.page("light", "desktop")
    sign_in(page, base)
    page.goto(base + project + "/members")
    page.fill("#member-username", "nobody")
    page.click(f"form[action='{project}/members'] button[type=submit]")
    page.wait_for_selector("#members-error")
    s.shot(page, "members-error-en-light-desktop", full_page=False)
    page.fill("#member-username", "viewer1")
    page.check("#access-viewer")
    page.click(f"form[action='{project}/members'] button[type=submit]")
    page.wait_for_url(re.compile(r"/members\?done=saved"))
    # The status card keeps polling without errors.
    page.goto(base + "/admin/system")
    page.wait_for_timeout(10_500)
    wait_settled(page)
    if not page.locator("#system-status[hx-trigger]").count():
        s.errors.append("system: the status card stopped polling")
    page.context.close()
    shoot_all(s, base, project + "/members", "members", ("en", "ja"))

    page = s.page("light", "phone")
    sign_in(page, base)
    page.click(".nav-toggle")
    page.click(".menu > summary")
    s.shot(page, "menu-admin-en-light-phone", full_page=False)
    page.context.close()


def assistant_page(s: "Shooter", base: str, project: str) -> None:
    """Fione-kun's page against the fake LLM: empty, then with a question, what it looked at
    and a pending training proposal (nothing is confirmed, so no job starts)."""
    shoot_all(s, base, project + "/assistant", "assistant-empty", ("en", "ja"))
    page = s.page("light", "desktop")
    sign_in(page, base)
    page.goto(base + project + "/assistant")
    page.fill("#assistant-text", "propose target=species")
    page.click(".chat-form button[type=submit]")
    page.locator(".chat-proposal").wait_for(timeout=60_000)
    wait_settled(page)
    page.context.close()
    shoot_all(s, base, project + "/assistant", "assistant-proposal", ("en", "ja"))


class StubLauncher(BaseHTTPRequestHandler):
    """The notebook launcher's API in memory: a started notebook stays ``starting``."""

    states: dict[str, str] = {}

    def _answer(self, status: int, data: dict | None = None) -> None:
        payload = b"" if data is None else json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        self._answer(200, {"state": self.states.get(self.path, "absent")})

    def do_PUT(self):  # noqa: N802
        self.rfile.read(int(self.headers["Content-Length"]))
        self.states[self.path] = "starting"
        self._answer(200, {"state": "starting"})

    def do_DELETE(self):  # noqa: N802
        self.states.pop(self.path, None)
        self._answer(204)

    def log_message(self, format, *args):  # noqa: A002
        pass


def notebook_page(s: "Shooter", base: str) -> None:
    """The notebook page of an admin (always allowed): not running, then starting (polled)."""
    shoot_all(s, base, "/notebook", "notebook-absent", ("en", "ja"))
    page = s.page("light", "desktop")
    sign_in(page, base)
    page.click("nav a[href='/notebook']")
    page.click("form[action='/notebook/start'] button[type=submit]")
    page.wait_for_selector("#notebook-status[hx-trigger]")
    page.wait_for_timeout(2500)  # one poll, still starting
    wait_settled(page)
    if not page.locator("#notebook-status[hx-trigger]").count():
        s.errors.append("notebook: the status stopped polling")
    page.context.close()
    shoot_all(s, base, "/notebook", "notebook-starting", ("en", "ja"))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    launcher = ThreadingHTTPServer(("127.0.0.1", 0), StubLauncher)
    threading.Thread(target=launcher.serve_forever, daemon=True).start()
    # Fione-kun's language model: tests/fake_llm.py run as the Compose stack runs it (a
    # process, not an import: tests/ is not on this script's path).
    llm_port = free_port()
    fake = subprocess.Popen(
        [sys.executable, str(FAKE_LLM), "--port", str(llm_port), "--policy", "e2e"],
        stdout=subprocess.DEVNULL,
    )
    with tempfile.TemporaryDirectory() as data_dir:
        env = {
            **os.environ,
            "FIONE_DATA_DIR": data_dir,
            "FIONE_SETUP_TOKEN": SETUP_TOKEN,
            "FIONE_RUNNER_ENABLED": "true",
            # The script signs in with a wrong password once per variant on purpose.
            "FIONE_LOGIN_MAX_FAILURES": "1000",
            "FIONE_PUBLIC_URL": base,
            "FIONE_NOTEBOOK_URL": f"http://127.0.0.1:{free_port()}",  # never framed here
            "FIONE_NOTEBOOK_LAUNCHER_URL": f"http://127.0.0.1:{launcher.server_address[1]}",
            "FIONE_NOTEBOOK_LAUNCHER_SECRET": LAUNCHER_SECRET,
            "FIONE_LLM_BASE_URL": f"http://127.0.0.1:{llm_port}/v1",
            "FIONE_LLM_PROVIDER": "ollama",
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
            run(base, out, errors, Path(data_dir))
        finally:
            server.terminate()
            server.wait(timeout=30)
            fake.terminate()
            fake.wait(timeout=30)
            launcher.shutdown()
            if errors:
                print("\n".join(["Page errors:", *errors]), file=sys.stderr)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
