"""The serving API contract (v1-compatible ``/invocations``) and the serving bundle."""

import asyncio
import json
import os
import shlex
import shutil
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import load_iris

from fione.config import Settings
from fione.engine.artifact import MODEL_FILE, read_manifest, save_model
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.models.bundle import make_serving_bundle
from fione.models.service import ModelNotFound, ModelRecord
from fione.storage import LocalStorage
from fione_serving.app import create_app
from fione_serving.loader import ModelLoadError, load

with warnings.catch_warnings():
    # Starlette prefers httpx2 for its TestClient; httpx is what the lockfile has and works.
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")
    from fastapi.testclient import TestClient

SECRET = b"k" * 32
TAG = "1.2.3"
PREFIX = "models/7/"
LABELS = ["良", "悪", "普通"]
COLORS = ["red", "green", "blue"]
SRC = Path(__file__).resolve().parents[2] / "src"


def _fit(frame: pd.DataFrame, target: str):
    config = TrainConfig(target=target, max_runtime_secs=10, max_models=2, nfolds=3)
    return AutoML(config, lambda event: None).fit(frame)


@pytest.fixture(scope="module")
def iris_model():
    data = load_iris(as_frame=True)
    frame = data.data.copy()
    frame.columns = ["SepalLength", "SepalWidth", "PetalLength", "PetalWidth"]
    frame["species"] = data.target_names[data.target]
    return _fit(frame, "species")


def _japanese_frame(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    x, width = rng.normal(size=n), rng.normal(size=n)
    color = rng.choice(COLORS, n)
    score = x + (color == "red") - width
    return pd.DataFrame(
        {
            "x": x,
            "幅": width,
            "color": color,
            "判定": np.select([score < -0.5, score > 0.5], [LABELS[1], LABELS[0]], LABELS[2]),
            "value": score + rng.normal(scale=0.1, size=n),
        }
    )


@pytest.fixture(scope="module")
def jp_model():
    return _fit(_japanese_frame().drop(columns=["value"]), "判定")


@pytest.fixture(scope="module")
def reg_model():
    return _fit(_japanese_frame().drop(columns=["判定"]), "value")


@pytest.fixture(scope="module")
def stored(tmp_path_factory):
    """``stored(model)`` -> (storage, model dir) with the artifact saved under ``PREFIX``."""
    base = tmp_path_factory.mktemp("stored")
    count = []

    def put(model, tag=TAG):
        root = base / str(len(count))
        count.append(root)
        storage = LocalStorage(root)
        save_model(model, storage, PREFIX, SECRET, image_tag=tag)
        return storage, root / PREFIX.rstrip("/")

    return put


def client_for(model_dir: Path, tag: str = TAG) -> TestClient:
    return TestClient(create_app(model_dir, image_tag=tag))


@pytest.fixture(scope="module")
def iris(iris_model, stored):
    return client_for(stored(iris_model)[1])


@pytest.fixture(scope="module")
def jp(jp_model, stored):
    return client_for(stored(jp_model)[1])


@pytest.fixture(scope="module")
def reg(reg_model, stored):
    return client_for(stored(reg_model)[1])


SETOSA = {"SepalLength": 5.1, "SepalWidth": 3.5, "PetalLength": 1.4, "PetalWidth": 0.2}
JP_ROW = {"x": 0.3, "幅": -0.2, "color": "red"}


def strict(text: str):
    def refuse(name):
        raise AssertionError(f"non-standard JSON constant {name}")

    return json.loads(text, parse_constant=refuse)


def invoke(client, instances):
    return client.post("/invocations", json={"instances": instances})


# --- /invocations: the predictions ------------------------------------------------------------


def test_iris_response_has_the_v1_shape_and_key_order(iris):
    r = invoke(iris, [SETOSA])
    assert r.status_code == 200
    assert r.text.startswith('{"predictions":[{"label":"setosa","index":0,"class_probabilities":[')
    (row,) = strict(r.text)["predictions"]
    assert list(row) == ["label", "index", "class_probabilities"]
    assert row["label"] == "setosa" and row["index"] == 0
    assert len(row["class_probabilities"]) == 3
    assert sum(row["class_probabilities"]) == pytest.approx(1.0)
    assert row["class_probabilities"][0] == max(row["class_probabilities"])


def test_the_response_is_exactly_the_predictions_list(iris):
    body = strict(invoke(iris, [SETOSA]).text)
    assert list(body) == ["predictions"] and len(body["predictions"]) == 1


def test_the_label_matches_the_probabilities_for_many_rows(iris):
    data = load_iris(as_frame=True).data
    rows = [dict(zip(SETOSA, map(float, r), strict=True)) for r in data.to_numpy()[::10]]
    predictions = strict(invoke(iris, rows).text)["predictions"]
    assert len(predictions) == len(rows)
    classes = ["setosa", "versicolor", "virginica"]
    for p in predictions:
        assert p["label"] == classes[p["index"]]
        assert p["index"] == int(np.argmax(p["class_probabilities"]))


def test_regression_rows_are_a_value(reg):
    r = invoke(reg, [JP_ROW, {"x": -1, "幅": 1, "color": "blue"}])
    rows = strict(r.text)["predictions"]
    assert [list(row) for row in rows] == [["value"], ["value"]]
    assert all(isinstance(row["value"], float) for row in rows)


def test_one_bad_row_does_not_fail_the_request(iris):
    bad = dict(SETOSA, SepalLength="abc")
    r = invoke(iris, [SETOSA, bad, dict(SETOSA, PetalLength=5.0, PetalWidth=1.9)])
    assert r.status_code == 200
    rows = strict(r.text)["predictions"]
    assert [list(x) for x in rows] == [
        ["label", "index", "class_probabilities"],
        ["exception"],
        ["label", "index", "class_probabilities"],
    ]
    assert "SepalLength" in rows[1]["exception"] and "abc" in rows[1]["exception"]
    assert rows[0]["label"] == "setosa" and rows[2]["label"] == "virginica"


def test_missing_columns_name_them(iris):
    (row,) = strict(invoke(iris, [{"SepalLength": 5.1, "PetalWidth": 0.2}]).text)["predictions"]
    assert row == {"exception": "missing columns: ['SepalWidth', 'PetalLength']"}


@pytest.mark.parametrize("instance", [5, "text", None, [1, 2], True])
def test_a_row_that_is_not_an_object_is_an_exception(iris, instance):
    rows = strict(invoke(iris, [SETOSA, instance]).text)["predictions"]
    assert list(rows[0]) == ["label", "index", "class_probabilities"]
    assert list(rows[1]) == ["exception"] and "object" in rows[1]["exception"]


def test_structured_values_in_a_numeric_column_are_an_exception(iris):
    rows = strict(invoke(iris, [dict(SETOSA, SepalLength=[1]), SETOSA]).text)["predictions"]
    assert "SepalLength" in rows[0]["exception"] and "label" in rows[1]


def test_numbers_as_text_and_nulls_still_predict(iris):
    rows = strict(
        invoke(iris, [dict(SETOSA, SepalLength="5.1"), dict(SETOSA, SepalWidth=None)]).text
    )
    assert all("label" in row for row in rows["predictions"])


def test_an_unseen_category_predicts(jp):
    (row,) = strict(invoke(jp, [dict(JP_ROW, color="purple")]).text)["predictions"]
    assert row["label"] in LABELS and len(row["class_probabilities"]) == 3


def test_japanese_names_and_labels_round_trip(jp):
    r = invoke(jp, [JP_ROW])
    (row,) = strict(r.text)["predictions"]
    assert row["label"] in LABELS and row["index"] == sorted(LABELS).index(row["label"])
    assert row["label"] in r.text  # not \u-escaped


def test_an_empty_list_is_an_empty_prediction_list(iris):
    r = invoke(iris, [])
    assert r.status_code == 200 and r.text == '{"predictions":[]}'


def test_only_bad_rows_still_answers_every_row(iris):
    rows = strict(invoke(iris, [5, {}]).text)["predictions"]
    assert [list(x) for x in rows] == [["exception"], ["exception"]]


def test_a_failing_batch_falls_back_to_one_prediction_per_row(jp_model, stored, monkeypatch):
    app = create_app(stored(jp_model)[1], image_tag=TAG)
    model = app.state.loaded.model
    real = type(model).predict_proba

    def flaky(self, df):
        if len(df) > 1 or df["x"].iloc[0] > 100:
            raise RuntimeError("secret internal detail")
        return real(self, df)

    monkeypatch.setattr(type(model), "predict_proba", flaky)
    client = TestClient(app)
    rows = strict(invoke(client, [JP_ROW, dict(JP_ROW, x=1000), JP_ROW]).text)["predictions"]
    assert [list(x) for x in rows] == [
        ["label", "index", "class_probabilities"],
        ["exception"],
        ["label", "index", "class_probabilities"],
    ]
    assert "secret internal detail" not in rows[1]["exception"]


def test_responses_are_strict_json(iris, reg):
    for client, row in ((iris, SETOSA), (reg, JP_ROW)):
        strict(invoke(client, [row, 5]).text)
        strict(client.get("/model").text)


def test_the_model_error_does_not_echo_the_request(jp):
    marker = "SECRET-MARKER-" + "x" * 500
    r = invoke(jp, [dict(JP_ROW, x=marker)])
    message = strict(r.text)["predictions"][0]["exception"]
    assert marker not in message and len(message) < 300


# --- /invocations: the request ----------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [b"not json", b"", b"\xff\xfe", b'{"instances": [NaN]}', b"[" * 100000],
)
def test_a_body_that_is_not_json_is_400(iris, body):
    r = iris.post("/invocations", content=body)
    assert r.status_code == 400
    assert list(r.json()) == ["error"] and isinstance(r.json()["error"], str)


@pytest.mark.parametrize(
    "body",
    [{}, {"instances": {"a": 1}}, {"instances": "x"}, {"instances": None}, [1, 2], "x", 5, None],
)
def test_a_body_without_a_list_of_instances_is_400(iris, body):
    r = iris.post("/invocations", json=body)
    assert r.status_code == 400 and list(r.json()) == ["error"]


def test_no_content_type_is_needed(iris):
    r = iris.post("/invocations", content=json.dumps({"instances": [SETOSA]}))
    assert r.status_code == 200 and "label" in strict(r.text)["predictions"][0]


def test_too_many_instances_is_413(iris_model, stored, monkeypatch):
    monkeypatch.setenv("FIONE_SERVING_MAX_INSTANCES", "3")
    client = client_for(stored(iris_model)[1])
    assert invoke(client, [SETOSA] * 3).status_code == 200
    r = invoke(client, [SETOSA] * 4)
    assert r.status_code == 413 and list(r.json()) == ["error"]


@pytest.fixture
def small_body_app(iris_model, stored, monkeypatch):
    monkeypatch.setenv("FIONE_SERVING_MAX_BODY", "1000")
    return create_app(stored(iris_model)[1], image_tag=TAG)


def big_body(size: int = 5000) -> bytes:
    return json.dumps({"instances": [SETOSA] * (size // 60)}).encode()


def test_a_body_over_the_cap_with_a_truthful_length_is_413(small_body_app):
    r = TestClient(small_body_app).post("/invocations", content=big_body())
    assert r.status_code == 413 and list(r.json()) == ["error"]


def test_a_body_over_the_cap_without_a_length_is_413(small_body_app):
    def chunks():
        body = big_body()
        for start in range(0, len(body), 500):
            yield body[start : start + 500]

    r = TestClient(small_body_app).post("/invocations", content=chunks())
    assert r.status_code == 413


def asgi_post(app, chunks: list[bytes], declared: int) -> tuple[int, bytes]:
    """POST ``chunks`` with a Content-Length that says ``declared`` (no server to police it)."""
    sent: list[dict] = []
    pending = [{"type": "http.request", "body": c, "more_body": True} for c in chunks]
    pending.append({"type": "http.request", "body": b"", "more_body": False})

    async def receive():
        return pending.pop(0) if pending else {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "path": "/invocations",
        "raw_path": b"/invocations",
        "query_string": b"",
        "root_path": "",
        "scheme": "http",
        "headers": [(b"content-length", str(declared).encode())],
        "server": ("test", 80),
        "client": ("test", 1),
    }
    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    return status, b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")


def test_a_lying_content_length_does_not_get_around_the_cap(small_body_app):
    body = big_body()
    status, _ = asgi_post(small_body_app, [body[i : i + 500] for i in range(0, len(body), 500)], 10)
    assert status == 413


def test_a_body_at_the_cap_still_works(iris_model, stored, monkeypatch):
    body = json.dumps({"instances": [SETOSA]}).encode()
    monkeypatch.setenv("FIONE_SERVING_MAX_BODY", str(len(body)))
    client = client_for(stored(iris_model)[1])
    assert client.post("/invocations", content=body).status_code == 200
    assert client.post("/invocations", content=body + b" ").status_code == 413


# --- the other endpoints ----------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/ping"])
def test_health_endpoints_are_200_with_an_empty_body(iris, path):
    r = iris.get(path)
    assert r.status_code == 200 and r.content == b""


def test_model_description_of_a_classifier(jp, jp_model, stored):
    r = jp.get("/model")  # no Content-Type needed
    assert r.status_code == 200
    body = strict(r.text)
    assert set(body) == {
        "names", "domains", "responseColumn", "category", "nclasses", "nfeatures",
        "uuid", "instance", "engine", "fioneVersion",
    }  # fmt: skip
    features = list(jp_model.columns)
    assert body["names"] == [*features, "判定"]
    assert body["responseColumn"] == "判定"
    assert body["category"] == "Multinomial" and body["nclasses"] == 3
    assert body["nfeatures"] == len(features)
    domains = dict(zip(body["names"], body["domains"], strict=True))
    assert domains["color"] == sorted(COLORS)
    assert domains["判定"] == sorted(LABELS)
    assert domains["x"] is None and domains["幅"] is None
    assert body["instance"] == {name: "?" for name in features}
    assert body["engine"] == "fione" and body["fioneVersion"]
    assert len(body["uuid"]) == 32 and int(body["uuid"], 16) >= 0


def test_model_description_of_other_tasks(iris, reg):
    iris_body = strict(iris.get("/model").text)
    assert iris_body["category"] == "Multinomial" and iris_body["nclasses"] == 3
    assert iris_body["names"][-1] == "species" and iris_body["domains"][-1] == [
        "setosa", "versicolor", "virginica"
    ]  # fmt: skip
    body = strict(reg.get("/model").text)
    assert body["category"] == "Regression" and body["nclasses"] == 1
    assert body["domains"][-1] is None and body["responseColumn"] == "value"


def test_the_uuid_is_the_model_files_hash_and_stable(jp_model, stored):
    storage, model_dir = stored(jp_model)
    manifest = read_manifest(storage, PREFIX)
    a, b = client_for(model_dir), client_for(model_dir)
    assert a.get("/model").json()["uuid"] == manifest.files[MODEL_FILE][:32]
    assert a.get("/model").json()["uuid"] == b.get("/model").json()["uuid"]


def test_a_binomial_model_is_reported_as_binomial(stored):
    frame = _japanese_frame().drop(columns=["value"])
    frame["判定"] = np.where(frame["判定"] == LABELS[0], "yes", "no")
    client = client_for(stored(_fit(frame, "判定"))[1])
    body = client.get("/model").json()
    assert body["category"] == "Binomial" and body["nclasses"] == 2
    (row,) = invoke(client, [JP_ROW]).json()["predictions"]
    assert row["label"] in ("no", "yes") and len(row["class_probabilities"]) == 2


# --- loading ----------------------------------------------------------------------------------


def test_load_returns_the_model_and_manifest(jp_model, stored):
    _, model_dir = stored(jp_model)
    loaded = load(model_dir, TAG)
    assert loaded.model.columns == jp_model.columns
    assert loaded.manifest.image_tag == TAG


def test_an_image_tag_mismatch_is_refused_naming_both_tags(jp_model, stored):
    _, model_dir = stored(jp_model, tag="1.0.0")
    with pytest.raises(ModelLoadError) as e:
        load(model_dir, "2.0.0")
    assert "1.0.0" in str(e.value) and "2.0.0" in str(e.value)
    with pytest.raises(ModelLoadError):
        create_app(model_dir, image_tag="2.0.0")


def test_a_corrupted_model_file_is_refused(jp_model, stored, tmp_path):
    _, model_dir = stored(jp_model)
    copy = tmp_path / "model"
    shutil.copytree(model_dir, copy)
    path = copy / MODEL_FILE
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0xFF
    path.write_bytes(bytes(data))
    with pytest.raises(ModelLoadError, match="hash"):
        create_app(copy, image_tag=TAG)


def test_a_missing_manifest_or_model_file_is_refused(jp_model, stored, tmp_path):
    _, model_dir = stored(jp_model)
    for name in ("manifest.json", MODEL_FILE):
        copy = tmp_path / name
        shutil.copytree(model_dir, copy)
        (copy / name).unlink()
        with pytest.raises(ModelLoadError, match="missing"):
            load(copy, TAG)
    with pytest.raises(ModelLoadError):
        load(tmp_path / "no-such-dir", TAG)


def test_an_unreadable_manifest_is_refused(jp_model, stored, tmp_path):
    _, model_dir = stored(jp_model)
    copy = tmp_path / "model"
    shutil.copytree(model_dir, copy)
    (copy / "manifest.json").write_text("{not json")
    with pytest.raises(ModelLoadError):
        load(copy, TAG)


def test_the_server_exits_1_with_one_line_on_a_bad_model_dir(tmp_path):
    env = {
        **os.environ,
        "PYTHONPATH": str(SRC),
        "FIONE_MODEL_DIR": str(tmp_path / "nothing-here"),
    }
    done = subprocess.run(
        [sys.executable, "-W", "error", "-m", "fione_serving"],
        env=env, capture_output=True, text=True, timeout=60,
    )  # fmt: skip
    assert done.returncode == 1
    assert "Traceback" not in done.stderr
    assert len(done.stderr.strip().splitlines()) == 1 and "model" in done.stderr


def test_the_server_exits_1_on_an_image_tag_mismatch(jp_model, stored):
    _, model_dir = stored(jp_model, tag="1.0.0")
    env = {
        **os.environ,
        "PYTHONPATH": str(SRC),
        "FIONE_MODEL_DIR": str(model_dir),
        "FIONE_IMAGE_TAG": "9.9.9",
    }
    done = subprocess.run(
        [sys.executable, "-m", "fione_serving"], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 1 and "1.0.0" in done.stderr and "9.9.9" in done.stderr


# --- the serving bundle -----------------------------------------------------------------------


def record_for(name: str = "Iris model", model_id: int = 7, prefix: str = PREFIX) -> ModelRecord:
    return ModelRecord(
        id=model_id, project_id="p", dataset_id=None, job_id=None, name=name, task="x",
        target="t", best_model="m", stop_reason="time", storage_prefix=prefix, trusted=1,
        config={}, leaderboard=[], trials=[], metrics={}, importance={}, created_at=0.0,
    )  # fmt: skip


def bundle_of(storage, tmp_path, name="Iris model", **kw):
    settings = Settings(data_dir=tmp_path / "data")
    (tmp_path / "work").mkdir(exist_ok=True)
    return make_serving_bundle(storage, record_for(name), settings, tmp_dir=tmp_path / "work", **kw)


@pytest.fixture
def work(tmp_path):
    (tmp_path / "work").mkdir()
    return tmp_path / "work"


def test_the_bundle_zip_holds_exactly_the_two_model_files(jp_model, stored, tmp_path, work):
    storage, _ = stored(jp_model)
    bundle = bundle_of(storage, tmp_path)
    data = b"".join(bundle.open())
    zip_path = tmp_path / "b.zip"
    zip_path.write_bytes(data)
    with zipfile.ZipFile(zip_path) as zf:
        assert sorted(zf.namelist()) == ["model/manifest.json", "model/model.joblib"]
        zf.extractall(tmp_path / "unzipped")
    loaded = load(tmp_path / "unzipped" / "model", TAG)
    assert loaded.model.columns == jp_model.columns
    assert list(work.iterdir()) == []


def test_the_bundle_serves_the_same_predictions(jp_model, stored, tmp_path):
    storage, model_dir = stored(jp_model)
    zip_path = tmp_path / "b.zip"
    zip_path.write_bytes(b"".join(bundle_of(storage, tmp_path).open()))
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp_path / "unzipped")
    a, b = client_for(model_dir), client_for(tmp_path / "unzipped" / "model")
    assert invoke(a, [JP_ROW]).text == invoke(b, [JP_ROW]).text


def test_the_run_command_names_the_image_tag_and_the_mount(jp_model, stored, tmp_path):
    storage, _ = stored(jp_model)
    settings = Settings(data_dir=tmp_path, serving_image="registry.example/fione-serving")
    bundle = make_serving_bundle(storage, record_for(), settings)
    assert bundle.run_command == (
        'docker run --rm -p 8081:8080 -v "$PWD/model:/model:ro" '
        f"registry.example/fione-serving:{TAG}"
    )
    assert Settings(data_dir=tmp_path).serving_image == "ghcr.io/codelibs/fione-serving"


def test_the_example_curl_is_valid_json_with_the_feature_names(jp_model, stored, tmp_path):
    storage, _ = stored(jp_model)
    bundle = bundle_of(storage, tmp_path)
    words = shlex.split(bundle.example_curl)
    assert words[:3] == ["curl", "-s", "-X"] and "localhost:8081/invocations" in words
    payload = json.loads(words[words.index("-d") + 1])
    assert payload == {"instances": [{name: "?" for name in jp_model.columns}]}
    assert "幅" in payload["instances"][0]
    assert "Content-Type: application/json" in words


def test_the_example_curl_survives_a_quote_in_a_column_name(tmp_path):
    from fione.models.bundle import example_curl

    words = shlex.split(example_curl(["it's", "幅"]))
    assert json.loads(words[words.index("-d") + 1]) == {"instances": [{"it's": "?", "幅": "?"}]}


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Iris model", "fione-serving-Iris-model-7.zip"),
        ("日本語モデル", "fione-serving-model-7.zip"),
        ('a/b\\c:*?"<>| d', "fione-serving-a-b-c-d-7.zip"),
        ("売上 forecast 2026", "fione-serving-forecast-2026-7.zip"),
    ],
)
def test_the_filename_is_ascii_safe(jp_model, stored, tmp_path, name, expected):
    storage, _ = stored(jp_model)
    assert bundle_of(storage, tmp_path, name).filename == expected


def test_closing_the_stream_early_removes_the_temp_file(jp_model, stored, tmp_path, work):
    storage, _ = stored(jp_model)
    stream = bundle_of(storage, tmp_path).open()
    assert list(work.iterdir()) == []  # nothing is made before the first chunk is asked for
    next(stream)
    stream.close()
    assert list(work.iterdir()) == []


def test_a_missing_artifact_is_model_not_found(jp_model, stored, tmp_path):
    storage, _ = stored(jp_model)
    settings = Settings(data_dir=tmp_path)
    with pytest.raises(ModelNotFound):
        make_serving_bundle(storage, record_for(prefix="models/404/"), settings)
    storage.delete(PREFIX + MODEL_FILE)
    bundle = make_serving_bundle(storage, record_for(), settings, tmp_dir=tmp_path)
    with pytest.raises(ModelNotFound):
        b"".join(bundle.open())
    assert [p.name for p in tmp_path.glob("fione-serving-*")] == []
