"""Operations inside the Linux container: cancelling a running training from the UI and
restarting the fione container in the middle of one leave no worker process behind; the
interrupted job is failed by orphan recovery, and the data stays."""

import numpy as np
import pandas as pd
import pytest

from e2e_helpers import sign_in, upload_by_api, wait_for_job

pytestmark = pytest.mark.e2e

LONG_RUNTIME_SECS = 180


@pytest.fixture(scope="module")
def long_data(stack, admin, tmp_path_factory) -> tuple[str, int]:
    """A project with a regression set big enough that training takes minutes."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=(20_000, 20))
    frame = pd.DataFrame(x, columns=[f"x{i}" for i in range(20)])
    frame["y"] = x @ rng.normal(size=20) + np.sin(x[:, 0] * 3) + rng.normal(scale=0.5, size=20_000)
    path = tmp_path_factory.mktemp("e2e-long") / "long.csv"
    frame.to_csv(path, index=False)
    api = admin.api(stack)
    project = api.post("/api/v1/projects", json={"name": "Operations e2e"}).json()["id"]
    dataset = upload_by_api(api, project, path, "long")
    return project, dataset["id"]


def only_the_server(stack) -> list[str]:
    """The fione container's processes: init and the one uvicorn, nothing else."""
    processes = stack.processes()
    assert not [p for p in processes if "fione.jobs.worker" in p], processes
    assert len(processes) == 2, processes
    assert processes[0].startswith("/sbin/docker-init") and "uvicorn" in processes[1]
    return processes


def test_cancel_from_the_ui_leaves_no_worker_in_the_linux_container(
    stack, admin, new_page, long_data
):
    project, dataset = long_data
    page = new_page()
    sign_in(page, admin.username, admin.password)
    page.goto(f"/projects/{project}/datasets/{dataset}/analyze")
    page.check("#runtime-custom")
    page.fill("#runtime-custom-minutes", str(LONG_RUNTIME_SECS // 60))
    page.click("#run-button")
    page.wait_for_url("**/jobs/*")
    page.wait_for_selector("[data-job-status=running]", timeout=60_000)
    assert any("fione.jobs.worker" in p for p in stack.processes())
    page.click("details.confirm > summary")
    page.click("details.confirm button[type=submit]")
    page.wait_for_selector("[data-job-status=cancelled]", timeout=15_000)
    job = admin.api(stack).get(f"/api/v1/jobs/{page.url.rsplit('/', 1)[1]}").json()
    assert job["status"] == "cancelled"
    only_the_server(stack)


def test_a_restart_mid_training_fails_the_job_and_keeps_the_data_in_the_linux_container(
    stack, admin, trained, long_data
):
    project, dataset = long_data
    api = admin.api(stack)
    config = {"target": "y", "max_runtime_secs": LONG_RUNTIME_SECS}
    r = api.post(
        f"/api/v1/projects/{project}/jobs/automl", json={"dataset_id": dataset, "config": config}
    )
    assert r.status_code == 201, r.text
    job = wait_for_job(api, r.json()["id"], {"running"}, 120)
    assert job["status"] == "running", job
    stack.compose("restart", "fione", timeout=120)
    stack.wait_healthy()
    job = api.get(f"/api/v1/jobs/{job['id']}").json()
    assert (job["status"], job["message"]) == ("failed", "interrupted by restart")
    only_the_server(stack)
    trained_project = trained.project.rsplit("/", 1)[1]
    assert api.get(f"/api/v1/projects/{trained_project}/models").json()
    names = [d["name"] for d in api.get(f"/api/v1/projects/{project}/datasets").json()]
    assert names == ["long"]
