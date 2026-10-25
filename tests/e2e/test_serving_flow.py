"""The serving bundle of the trained model, downloaded from the summary page and run in the
serving image exactly as the page's command says (only the host port and a name added),
asked for a prediction and then for the same prediction with its contributions."""

import json
import re
import shlex
import socket
import subprocess
import time
import zipfile

import httpx
import pytest

from e2e_helpers import sign_in

pytestmark = pytest.mark.e2e

COMMAND = re.compile(r'docker run --rm -p 8081:8080 -v "\$PWD/model:/model:ro" (\S+)')


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def serving_container(stack):
    """``start(model_dir, image) -> base URL``; the container (by its exact name) is removed
    at the end, whatever happened."""
    name = f"{stack.project}-serving"
    started = []

    def start(model_dir, image) -> str:
        port = free_port()
        command = [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-p",
            f"127.0.0.1:{port}:8080",
            "-v",
            f"{model_dir}:/model:ro",
            image,
        ]
        started.append(name)
        subprocess.run(command, check=True, capture_output=True, timeout=120)
        return f"http://127.0.0.1:{port}"

    yield start
    for container in started:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=60)


def test_the_bundle_runs_as_the_page_says(
    stack, admin, trained, new_page, tmp_path, serving_container
):
    page = new_page()
    sign_in(page, admin.username, admin.password)
    page.goto(trained.summary)
    command = page.locator("#run-command").inner_text().strip()
    match = COMMAND.fullmatch(command)
    assert match, command
    image = match.group(1)
    assert image == stack.serving_image
    assert shlex.split(command)[-1] == image
    with page.expect_download() as caught:
        page.click("a[href$='/serving']")
    bundle = tmp_path / caught.value.suggested_filename
    caught.value.save_as(bundle)
    with zipfile.ZipFile(bundle) as z:
        z.extractall(tmp_path)
    assert (tmp_path / "model" / "manifest.json").is_file()

    base = serving_container(tmp_path / "model", image)
    deadline = time.monotonic() + 60
    while True:
        try:
            if httpx.get(f"{base}/ping", timeout=3).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        assert time.monotonic() < deadline, "the serving container did not answer /ping"
        time.sleep(1)

    row = {
        "sepal length (cm)": 6.3,
        "sepal width (cm)": 3.3,
        "petal length (cm)": 6.0,
        "petal width (cm)": 2.5,
    }
    r = httpx.post(f"{base}/invocations", json={"instances": [row]}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert list(body) == ["predictions"] and len(body["predictions"]) == 1
    (prediction,) = body["predictions"]
    assert list(prediction) == ["label", "index", "class_probabilities"]
    assert isinstance(prediction["label"], str) and isinstance(prediction["index"], int)
    probabilities = prediction["class_probabilities"]
    assert len(probabilities) == 3 and all(isinstance(p, float) for p in probabilities)
    assert abs(sum(probabilities) - 1) < 1e-6
    assert prediction["label"] == "virginica"

    r = httpx.post(
        f"{base}/invocations", json={"instances": [row], "contributions": True}, timeout=30
    )
    assert r.status_code == 200, r.text
    (explained,) = r.json()["predictions"]
    assert list(explained) == ["label", "index", "class_probabilities", "contributions"]
    assert {k: explained[k] for k in prediction} == prediction  # the same prediction
    contributions = explained["contributions"]
    assert list(contributions) == ["bias", "columns"] and set(contributions["columns"]) == set(row)
    total = contributions["bias"] + sum(contributions["columns"].values())
    assert abs(total - probabilities[prediction["index"]]) < 1e-5  # the predicted class

    model = httpx.get(f"{base}/model", timeout=10)
    assert model.status_code == 200 and isinstance(json.loads(model.text), dict)
