"""Roles and membership end to end: an administrator creates an editor and a viewer (users
page) and shares the project with them (sharing page); the viewer sees no write controls
and is refused by the API, a non-member finds nothing, the editor can run, anonymous
visitors go to the login page; pages carry the CSP and the console stays clean (the
``new_page`` fixture fails on any console error)."""

import httpx
import pytest

from e2e_helpers import sign_in, wait_for_job

pytestmark = pytest.mark.e2e

PASSWORD = "e2e-member-password-1"  # test-only


def create_user(page, username: str, role: str) -> None:
    page.goto("/admin/users")
    page.click("details.card > summary")
    page.fill("#new-username", username)
    page.fill("#new-password", PASSWORD)
    page.select_option("#new-role", role)
    page.click("form[action='/admin/users'] button[type=submit]")
    page.wait_for_url("**/admin/users?done=created*")


def share(page, project: str, username: str, access: str) -> None:
    page.goto(project + "/members")
    page.fill("#member-username", username)
    page.check(f"#access-{access}")
    page.click(f"form[action='{project}/members'] button[type=submit]")
    page.wait_for_url("**/members?done=saved")


def token_of(page) -> str:
    csrf = page.get_attribute("meta[name=csrf-token]", "content")
    r = page.request.post("/api/v1/tokens", data={"name": "e2e"}, headers={"X-CSRF-Token": csrf})
    assert r.ok, r.text()
    return r.json()["token"]


def test_roles_and_membership(stack, admin, trained, new_page, console):
    project = trained.project
    pid = project.rsplit("/", 1)[1]
    api = admin.api(stack)
    datasets = api.get(f"/api/v1/projects/{pid}/datasets").json()
    (dataset,) = [d for d in datasets if d["type"] == "train"]
    analyze = f"{project}/datasets/{dataset['id']}/analyze"

    page = new_page()
    sign_in(page, admin.username, admin.password)
    create_user(page, "e2e-editor", "editor")
    create_user(page, "e2e-viewer", "viewer")
    create_user(page, "e2e-outsider", "editor")
    share(page, project, "e2e-editor", "editor")
    share(page, project, "e2e-viewer", "viewer")

    # The viewer: everything to read, no control to change anything, 403 from the API.
    viewer = new_page()
    sign_in(viewer, "e2e-viewer", PASSWORD)
    response = viewer.goto(project)
    assert response.status == 200
    assert viewer.locator(f"a[href='{project}/upload']").count() == 0
    viewer.goto(analyze)
    assert viewer.locator("#run-button").count() == 0
    viewer.goto(project + "/datasets")
    assert viewer.locator("form[action$='/delete']").count() == 0
    console.expect_error(stack.base + project + "/upload")
    assert viewer.goto(project + "/upload").status == 403
    headers = {"Authorization": f"Bearer {token_of(viewer)}"}
    body = {"dataset_id": dataset["id"], "config": {"target": "species", "max_runtime_secs": 60}}
    r = httpx.post(f"{stack.base}/api/v1/projects/{pid}/jobs/automl", json=body, headers=headers)
    assert r.status_code == 403
    r = httpx.delete(f"{stack.base}/api/v1/projects/{pid}", headers=headers)
    assert r.status_code == 403

    # Someone who is no member: the project does not exist for them.
    outsider = new_page()
    sign_in(outsider, "e2e-outsider", PASSWORD)
    console.expect_error(stack.base + project)
    assert outsider.goto(project).status == 404
    headers = {"Authorization": f"Bearer {token_of(outsider)}"}
    assert httpx.get(f"{stack.base}/api/v1/projects/{pid}", headers=headers).status_code == 404

    # The editor member runs a training from the analysis page.
    editor = new_page()
    sign_in(editor, "e2e-editor", PASSWORD)
    editor.goto(analyze)
    editor.check("#runtime-1")
    editor.click("#run-button")
    editor.wait_for_url("**/jobs/*")
    job_id = int(editor.url.rsplit("/", 1)[1])
    job = wait_for_job(api, job_id, {"done", "failed", "cancelled"}, 180)
    assert job["status"] == "done", job  # also frees the queue for the next tests

    # Anonymous visitors are sent to the login page; pages carry the CSP.
    anonymous = new_page()
    anonymous.goto(project)
    assert "/login?next=" in anonymous.url
    response = anonymous.goto("/login")
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "script-src 'self'" in csp
