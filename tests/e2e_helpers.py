"""Browser steps shared by the end-to-end tests (tests/e2e)."""

import time
from pathlib import Path

import httpx


def sign_in(page, username: str, password: str) -> None:
    page.goto("/login")
    page.fill("#login-username", username)
    page.fill("#login-password", password)
    page.click("form[data-json-form] button[type=submit]")
    page.wait_for_url("**/")


def upload(page, path: Path) -> None:
    page.set_input_files("#upload-file", str(path))
    page.click("form[data-upload-form] button[type=submit]")


def wait_for_job(api: httpx.Client, job_id: int, statuses: set[str], seconds: float) -> dict:
    """Poll the API until the job's status is one of ``statuses``; the last job seen."""
    deadline = time.monotonic() + seconds
    while True:
        job = api.get(f"/api/v1/jobs/{job_id}").json()
        if job["status"] in statuses or time.monotonic() > deadline:
            return job
        time.sleep(0.5)


def upload_by_api(api: httpx.Client, project_id: str, path: Path, name: str) -> dict:
    with path.open("rb") as f:
        r = api.post(
            f"/api/v1/projects/{project_id}/datasets",
            data={"name": name, "type": "train"},
            files={"file": (path.name, f, "text/csv")},
        )
    assert r.status_code == 201, r.text
    return r.json()
