"""The serving API contract (``/invocations``) and the serving bundle."""

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
from fione.engine import explain
from fione.engine.artifact import MODEL_FILE, read_manifest, save_model
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.models.bundle import BundleError, make_serving_bundle
from fione.models.service import ModelNotFound, ModelRecord
from fione.storage import LocalStorage
from fione_serving.app import (
    DEFAULT_MAX_CONTRIBUTION_INSTANCES,
    DEFAULT_MAX_CONTRIBUTION_REQUESTS,
    Predictor,
    create_app,
)
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
def bin_model():
    """A yes/no model whose inputs are named ``bias`` and ``BiasTerm`` (and ``color``)."""
    frame = (
        _japanese_frame().drop(columns=["value"]).rename(columns={"x": "bias", "幅": "BiasTerm"})
    )
    frame["判定"] = np.where(frame["判定"] == LABELS[0], "yes", "no")
    return _fit(frame, "判定")


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


@pytest.fixture(scope="module")
def binary(bin_model, stored):
    return client_for(stored(bin_model)[1])


SETOSA = {"SepalLength": 5.1, "SepalWidth": 3.5, "PetalLength": 1.4, "PetalWidth": 0.2}
JP_ROW = {"x": 0.3, "幅": -0.2, "color": "red"}
BIN_ROW = {"bias": 0.3, "BiasTerm": -0.2, "color": "red"}


def strict(text: str):
    def refuse(name):
        raise AssertionError(f"non-standard JSON constant {name}")

    return json.loads(text, parse_constant=refuse)


def invoke(client, instances, **fields):
    return client.post("/invocations", json={"instances": instances, **fields})


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


def invoke_text(client, instances):
    """POST with ASCII-only JSON, so a lone surrogate travels as a ``\\ud800`` escape."""
    return client.post("/invocations", content=json.dumps({"instances": instances}))


@pytest.mark.parametrize("field", ["color", "x"])
def test_a_lone_surrogate_costs_only_its_own_row(jp, field):
    rows = [JP_ROW, dict(JP_ROW, **{field: "\ud800"}), dict(JP_ROW, x=-1.0), JP_ROW]
    r = invoke_text(jp, rows)
    assert r.status_code == 200
    out = strict(r.text)["predictions"]
    assert [list(x) for x in out] == [
        ["label", "index", "class_probabilities"],
        ["exception"],
        ["label", "index", "class_probabilities"],
        ["label", "index", "class_probabilities"],
    ]
    assert repr(field) in out[1]["exception"] and "ud800" not in r.text
    assert out[0] == out[3]


def test_a_surrogate_beside_a_mixed_type_column_is_one_exception(jp):
    rows = [dict(JP_ROW, color="\ud800"), dict(JP_ROW, color=1)] + [JP_ROW] * 20
    out = strict(invoke_text(jp, rows).text)["predictions"]
    assert list(out[0]) == ["exception"]
    assert all("label" in row for row in out[1:])


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


@pytest.fixture
def counted(jp_model, stored, monkeypatch):
    """(client, calls): the model's ``predict_proba`` fails on any frame holding x > 100."""
    app = create_app(stored(jp_model)[1], image_tag=TAG)
    model = app.state.loaded.model
    real = type(model).predict_proba
    calls: list[int] = []

    def flaky(self, df):
        calls.append(len(df))
        if (df["x"] > 100).any():
            raise RuntimeError("secret internal detail")
        return real(self, df)

    monkeypatch.setattr(type(model), "predict_proba", flaky)
    return TestClient(app), calls


def thousand(bad: set[int]) -> list[dict]:
    return [dict(JP_ROW, x=1000.0 if i in bad else i / 1000) for i in range(1000)]


def test_one_bad_row_among_a_thousand_costs_few_model_calls(counted):
    client, calls = counted
    rows = strict(invoke(client, thousand({617})).text)["predictions"]
    assert [i for i, row in enumerate(rows) if "exception" in row] == [617]
    assert len(calls) <= 2 * 10 + 3


def test_scattered_bad_rows_cost_a_bounded_number_of_model_calls(counted):
    client, calls = counted
    bad = {3, 250, 251, 600, 999}
    rows = strict(invoke(client, thousand(bad)).text)["predictions"]
    assert {i for i, row in enumerate(rows) if "exception" in row} == bad
    assert all("secret" not in row.get("exception", "") for row in rows)
    assert len(calls) <= 5 * (2 * 10 + 2)
    alone = strict(invoke(client, [thousand(set())[i] for i in sorted(bad)]).text)["predictions"]
    assert all("label" in row for row in alone)
    assert [r["label"] for i, r in enumerate(rows) if i not in bad][:5]  # neighbours are intact


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


def asgi_post(app, chunks: list[bytes], declared: int | str) -> tuple[int, bytes]:
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
        "headers": [(b"content-length", str(declared).encode("latin-1"))],
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


def test_a_non_ascii_digit_content_length_is_ignored_not_a_500(iris):
    body = json.dumps({"instances": [SETOSA]}).encode()
    status, _ = asgi_post(iris.app, [body], "\u00b2")
    assert status == 200


def test_a_body_at_the_cap_still_works(iris_model, stored, monkeypatch):
    body = json.dumps({"instances": [SETOSA]}).encode()
    monkeypatch.setenv("FIONE_SERVING_MAX_BODY", str(len(body)))
    client = client_for(stored(iris_model)[1])
    assert client.post("/invocations", content=body).status_code == 200
    assert client.post("/invocations", content=body + b" ").status_code == 413


# --- /invocations: contributions, on request ---------------------------------------------------

CLASSIFIER_KEYS = ["label", "index", "class_probabilities"]
CLIENT_ROWS = {"iris": SETOSA, "jp": JP_ROW, "reg": JP_ROW, "binary": BIN_ROW}


def _mixed_rows(row: dict) -> list:
    first = next(iter(row))
    return [row, dict(row, **{first: "abc"}), 5, {}, dict(row, **{first: None}), row]


def _without_contributions(rows: list[dict]) -> list[dict]:
    return [{k: v for k, v in row.items() if k != "contributions"} for row in rows]


@pytest.mark.parametrize("name", ["iris", "reg", "binary"])
def test_default_bytes_are_unchanged(request, name):
    client = request.getfixturevalue(name)
    rows = _mixed_rows(CLIENT_ROWS[name])
    plain = invoke(client, rows)
    assert plain.status_code == 200
    for flag in (False, None):  # null counts as no key (typed clients send unset fields so)
        off = invoke(client, rows, contributions=flag)
        assert off.status_code == 200
        assert off.content == plain.content and dict(off.headers) == dict(plain.headers)
    on = invoke(client, rows, contributions=True)
    assert on.status_code == 200
    assert (
        _without_contributions(strict(on.text)["predictions"]) == strict(plain.text)["predictions"]
    )


def test_whole_request_errors_are_unchanged_by_the_flag(iris):
    for fields in ({}, {"contributions": False}, {"contributions": None}):
        r = iris.post("/invocations", json={"instance": [SETOSA], **fields})
        assert r.status_code == 400 and r.json() == {
            "error": '"instances" must be a list of objects'
        }
        assert "retry-after" not in r.headers


def test_contributions_key_order(iris, reg):
    columns = list(iris.app.state.loaded.model.columns)
    (row,) = strict(invoke(iris, [SETOSA], contributions=True).text)["predictions"]
    assert list(row) == [*CLASSIFIER_KEYS, "contributions"]
    assert list(row["contributions"]) == ["bias", "columns"]
    assert list(row["contributions"]["columns"]) == columns
    (row,) = strict(invoke(reg, [JP_ROW], contributions=True).text)["predictions"]
    assert list(row) == ["value", "contributions"]
    assert list(row["contributions"]["columns"]) == list(reg.app.state.loaded.model.columns)


def _explained(row: dict, task: str) -> float:
    if task == "regression":
        return row["value"]
    return row["class_probabilities"][1 if task == "binary" else row["index"]]


@pytest.mark.parametrize(
    ("name", "task"),
    [("binary", "binary"), ("iris", "multiclass"), ("jp", "multiclass"), ("reg", "regression")],
)
def test_contributions_are_additive(request, name, task):
    client = request.getfixturevalue(name)
    if name == "iris":
        data = load_iris(as_frame=True).data
        rows = [dict(zip(SETOSA, map(float, r), strict=True)) for r in data.to_numpy()[::10]]
    else:
        frame = _japanese_frame(20)
        if name == "binary":
            frame = frame.rename(columns={"x": "bias", "幅": "BiasTerm"})
        rows = frame[list(CLIENT_ROWS[name])].to_dict("records")
        first = next(iter(CLIENT_ROWS[name]))
        rows += [dict(rows[0], color="purple"), dict(rows[1], **{first: None})]
    out = strict(invoke(client, rows, contributions=True).text)["predictions"]
    assert len(out) == len(rows)
    for row in out:
        c = row["contributions"]
        assert c["bias"] + sum(c["columns"].values()) == pytest.approx(
            _explained(row, task), abs=1e-6
        )
    assert any(v != 0 for row in out for v in row["contributions"]["columns"].values())


@pytest.mark.parametrize("flag", ["yes", "true", "null", 1, 0, [], {}])
def test_non_bool_contributions_is_400(iris, flag):
    r = invoke(iris, [SETOSA], contributions=flag)
    assert r.status_code == 400 and list(r.json()) == ["error"]
    assert "contributions" in r.json()["error"]


def test_too_many_contribution_instances_is_413(iris_model, stored, monkeypatch):
    monkeypatch.setenv("FIONE_SERVING_MAX_CONTRIBUTION_INSTANCES", "3")
    client = client_for(stored(iris_model)[1])
    assert invoke(client, [SETOSA] * 3, contributions=True).status_code == 200
    r = invoke(client, [SETOSA] * 4, contributions=True)
    assert r.status_code == 413 and list(r.json()) == ["error"] and "3" in r.json()["error"]
    assert invoke(client, [SETOSA] * 4).status_code == 200
    assert invoke(client, [SETOSA] * 4, contributions=False).status_code == 200


def test_the_contribution_limits_default_to_100_and_2():
    assert DEFAULT_MAX_CONTRIBUTION_INSTANCES == 100
    assert DEFAULT_MAX_CONTRIBUTION_REQUESTS == 2


def test_101_contribution_instances_need_a_raised_setting(iris, iris_model, stored, monkeypatch):
    rows = [SETOSA] * 101
    r = invoke(iris, rows, contributions=True)
    assert r.status_code == 413 and "at most 100" in r.json()["error"]
    assert invoke(iris, rows).status_code == 200
    monkeypatch.setenv("FIONE_SERVING_MAX_CONTRIBUTION_INSTANCES", "101")
    raised = client_for(stored(iris_model)[1])
    out = strict(invoke(raised, rows, contributions=True).text)["predictions"]
    assert len(out) == 101 and all("contributions" in row for row in out)


@pytest.fixture
def spied(iris, monkeypatch):
    """The model calls made by ``iris`` requests: ``contributions`` and ``predict_proba``."""
    calls: list[str] = []
    model = iris.app.state.loaded.model
    real_proba, real_contributions = type(model).predict_proba, explain.contributions

    def proba(self, df):
        calls.append("predict_proba")
        return real_proba(self, df)

    def contributions(model, df):
        calls.append("contributions")
        return real_contributions(model, df)

    monkeypatch.setattr(type(model), "predict_proba", proba)
    monkeypatch.setattr(explain, "contributions", contributions)
    return calls


def test_the_contribution_cap_is_checked_before_any_work(iris, spied):
    r = invoke(iris, [SETOSA] * (DEFAULT_MAX_CONTRIBUTION_INSTANCES + 1), contributions=True)
    assert r.status_code == 413 and spied == []
    assert invoke(iris, [SETOSA], contributions=True).status_code == 200
    assert spied == ["predict_proba", "contributions"]


def test_a_model_too_wide_for_the_rows_is_422(iris, spied, monkeypatch):
    model = iris.app.state.loaded.model
    monkeypatch.setattr(explain, "CELLS", 2 * len(model.classes_) * len(model.prep.sources))
    assert invoke(iris, [SETOSA] * 2, contributions=True).status_code == 200
    spied.clear()
    r = invoke(iris, [SETOSA] * 3, contributions=True)
    assert r.status_code == 422 and list(r.json()) == ["error"] and "2" in r.json()["error"]
    monkeypatch.setattr(explain, "CELLS", 1)
    r = invoke(iris, [SETOSA], contributions=True)
    assert r.status_code == 422 and "too many" in r.json()["error"]
    assert spied == []
    assert invoke(iris, [SETOSA] * 3).status_code == 200  # plain predictions are not limited


def test_failing_row_has_no_contributions(iris):
    rows = strict(invoke(iris, _mixed_rows(SETOSA), contributions=True).text)["predictions"]
    assert [list(row) for row in rows] == [
        [*CLASSIFIER_KEYS, "contributions"],
        ["exception"],
        ["exception"],
        ["exception"],
        [*CLASSIFIER_KEYS, "contributions"],
        [*CLASSIFIER_KEYS, "contributions"],
    ]


def test_a_failing_batch_is_bisected_with_contributions(counted):
    client, calls = counted
    hundred = thousand({61})[:DEFAULT_MAX_CONTRIBUTION_INSTANCES]
    rows = strict(invoke(client, hundred, contributions=True).text)["predictions"]
    assert [i for i, row in enumerate(rows) if "exception" in row] == [61]
    assert list(rows[61]) == ["exception"] and "secret" not in rows[61]["exception"]
    assert all(list(row) == [*CLASSIFIER_KEYS, "contributions"] for row in rows[:61])
    assert len(calls) <= 2 * 7 + 3


def test_a_row_whose_contributions_fail_is_an_exception(jp, monkeypatch):
    real = explain.contributions

    def flaky(model, df):
        if (df["x"] > 100).any():
            raise RuntimeError("secret internal detail")
        return real(model, df)

    monkeypatch.setattr(explain, "contributions", flaky)
    rows = [JP_ROW, dict(JP_ROW, x=1000.0), JP_ROW]
    out = strict(invoke(jp, rows, contributions=True).text)["predictions"]
    assert [list(row) for row in out] == [
        [*CLASSIFIER_KEYS, "contributions"],
        ["exception"],
        [*CLASSIFIER_KEYS, "contributions"],
    ]
    assert "secret" not in out[1]["exception"]
    assert all("label" in row for row in strict(invoke(jp, rows).text)["predictions"])


def _hold_every_slot(app) -> int:
    held = 0
    while app.state.contribution_requests.acquire(blocking=False):
        held += 1
    return held


def _free(app, held: int) -> None:
    for _ in range(held):
        app.state.contribution_requests.release()


def test_in_flight_cap_returns_503(iris):
    held = _hold_every_slot(iris.app)
    try:
        assert held == DEFAULT_MAX_CONTRIBUTION_REQUESTS
        r = invoke(iris, [SETOSA], contributions=True)
        assert r.status_code == 503 and r.headers["retry-after"] == "1"
        assert list(r.json()) == ["error"]
        assert invoke(iris, [SETOSA]).status_code == 200
        assert invoke(iris, [SETOSA], contributions=False).status_code == 200
    finally:
        _free(iris.app, held)
    assert invoke(iris, [SETOSA], contributions=True).status_code == 200


def test_rejected_and_failed_contribution_requests_free_their_slot(iris_model, stored, monkeypatch):
    monkeypatch.setenv("FIONE_SERVING_MAX_CONTRIBUTION_REQUESTS", "1")
    monkeypatch.setenv("FIONE_SERVING_MAX_CONTRIBUTION_INSTANCES", "2")
    app = create_app(stored(iris_model)[1], image_tag=TAG)
    client = TestClient(app, raise_server_exceptions=False)
    assert invoke(client, [SETOSA], contributions="yes").status_code == 400
    assert invoke(client, [SETOSA] * 3, contributions=True).status_code == 413
    with monkeypatch.context() as m:
        m.setattr(explain, "CELLS", 1)
        assert invoke(client, [SETOSA], contributions=True).status_code == 422
    with monkeypatch.context() as m:
        m.setattr(Predictor, "predict", lambda *a, **k: 1 / 0)
        assert invoke(client, [SETOSA], contributions=True).status_code == 500
    held = _hold_every_slot(app)
    _free(app, held)
    assert held == 1
    assert invoke(client, [SETOSA], contributions=True).status_code == 200
    assert _hold_every_slot(app) == 1


@pytest.mark.parametrize(
    "name", ["FIONE_SERVING_MAX_CONTRIBUTION_INSTANCES", "FIONE_SERVING_MAX_CONTRIBUTION_REQUESTS"]
)
def test_a_bad_contribution_limit_setting_is_refused(iris_model, stored, monkeypatch, name):
    _, model_dir = stored(iris_model)
    for raw in ("0", "lots"):
        monkeypatch.setenv(name, raw)
        with pytest.raises(ValueError, match=name):
            create_app(model_dir, image_tag=TAG)


def test_model_description_is_unchanged(iris, reg, binary):
    phase1 = [
        "names", "domains", "responseColumn", "category", "nclasses", "nfeatures",
        "uuid", "instance", "engine", "fioneVersion",
    ]  # fmt: skip
    for client in (iris, reg, binary):
        assert list(strict(client.get("/model").text)) == phase1


def test_a_column_named_BiasTerm_or_bias_stays_in_columns(binary, bin_model):
    r = invoke(binary, [BIN_ROW], contributions=True)
    (row,) = strict(r.text)["predictions"]
    assert list(row) == [*CLASSIFIER_KEYS, "contributions"]
    contributions = row["contributions"]
    assert list(contributions) == ["bias", "columns"]
    assert list(contributions["columns"]) == list(bin_model.columns)
    assert {"bias", "BiasTerm"} <= set(contributions["columns"])
    assert isinstance(contributions["bias"], float)


def test_japanese_column_names_are_not_escaped_in_contributions(jp):
    r = invoke(jp, [JP_ROW], contributions=True)
    assert '"幅":' in r.text


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


@pytest.mark.parametrize(
    ("make_target", "first", "classes"),
    [
        (lambda s: s.map({"良": 10, "悪": 20, "普通": 30}), '"label":', [10, 20, 30]),
        (lambda s: s == "良", '"label":', [False, True]),
    ],
    ids=["int", "bool"],
)
def test_class_labels_keep_their_json_type(stored, make_target, first, classes):
    frame = _japanese_frame().drop(columns=["value"])
    frame["判定"] = make_target(frame["判定"])
    client = client_for(stored(_fit(frame, "判定"))[1])
    assert client.get("/model").json()["domains"][-1] == classes
    r = invoke(client, [JP_ROW])
    (row,) = strict(r.text)["predictions"]
    assert type(row["label"]) is type(classes[0]) and row["label"] == classes[row["index"]]
    literal = json.dumps(row["label"])
    assert f'{first}{literal},"index"' in r.text and literal in (
        "true",
        "false",
        *map(str, classes),
    )


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


def test_the_server_exits_1_on_a_bad_limit_setting(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(SRC), "FIONE_SERVING_MAX_BODY": "lots"}
    done = subprocess.run(
        [sys.executable, "-m", "fione_serving"], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 1 and "Traceback" not in done.stderr
    assert "FIONE_SERVING_MAX_BODY" in done.stderr


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


def test_the_example_curl_is_compact_json(jp_model, stored, tmp_path):
    storage, _ = stored(jp_model)
    words = shlex.split(bundle_of(storage, tmp_path).example_curl)
    assert words[words.index("-d") + 1].startswith('{"instances":[{"')


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


def test_a_very_long_name_gives_a_short_filename(jp_model, stored, tmp_path):
    storage, _ = stored(jp_model)
    for name in ("あ" * 300, "a" * 300, "ab " * 100):
        filename = bundle_of(storage, tmp_path, name).filename
        assert filename.isascii() and len(filename) <= 120
        assert filename.startswith("fione-serving-") and filename.endswith("-7.zip")


def stored_with_tag(storage, tag: str) -> None:
    """Rewrite the stored manifest's image tag (the hash and HMAC checks are not run here)."""
    manifest = json.loads(storage.get(PREFIX + "manifest.json"))
    manifest["image_tag"] = tag
    storage.put(PREFIX + "manifest.json", json.dumps(manifest).encode())


@pytest.mark.parametrize(
    "tag",
    [
        "x;touch pwned",
        "a b",
        "$(id)",
        "dev\nrm -rf /",
        "a" * 129,
        "",
        ".dev",
        "-dev",
        "a`b`",
        "dev'",
    ],
)
def test_an_unsafe_image_tag_is_refused(jp_model, stored, tmp_path, tag):
    storage, _ = stored(jp_model)
    stored_with_tag(storage, tag)
    with pytest.raises(BundleError, match="image tag") as e:
        bundle_of(storage, tmp_path)
    assert isinstance(e.value, ValueError) and len(str(e.value)) < 150


@pytest.mark.parametrize("tag", ["dev", "2.0.0.dev0", "v1_2-rc.3", "_x", "a" * 128])
def test_a_valid_image_tag_gives_exactly_the_expected_argv(jp_model, stored, tmp_path, tag):
    storage, _ = stored(jp_model)
    stored_with_tag(storage, tag)
    bundle = bundle_of(storage, tmp_path)
    assert shlex.split(bundle.run_command) == [
        "docker", "run", "--rm", "-p", "8081:8080", "-v", "$PWD/model:/model:ro",
        f"ghcr.io/codelibs/fione-serving:{tag}",
    ]  # fmt: skip


@pytest.mark.parametrize(
    "image", ["ghcr.io/x;id", "a b", "$(id)", "UPPER/case", "x:tag", "/abs", "a//b", "", "a/b\n"]
)
def test_an_unsafe_serving_image_is_refused(jp_model, stored, tmp_path, image):
    storage, _ = stored(jp_model)
    settings = Settings(data_dir=tmp_path, serving_image=image)
    with pytest.raises(BundleError, match="image name"):
        make_serving_bundle(storage, record_for(), settings)


@pytest.mark.parametrize(
    "image",
    ["ghcr.io/codelibs/fione-serving", "localhost:5000/team/fione_serving", "fione-serving"],
)
def test_a_registry_image_name_is_accepted(jp_model, stored, tmp_path, image):
    storage, _ = stored(jp_model)
    bundle = make_serving_bundle(
        storage, record_for(), Settings(data_dir=tmp_path, serving_image=image)
    )
    assert shlex.split(bundle.run_command)[-1] == f"{image}:{TAG}"


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
