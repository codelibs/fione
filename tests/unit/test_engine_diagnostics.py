import copy
import datetime
import decimal
import json
import time

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import load_iris
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from fione.engine import automl as automl_module
from fione.engine import metrics
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.engine.diagnostics import diagnostics
from fione.engine.events import jsonable


def _six(value):
    return None if np.isnan(value) else float(f"{value:.6g}")


def _leaves(value):
    if isinstance(value, dict):
        assert all(type(k) is str for k in value)
        for v in value.values():
            yield from _leaves(v)
    elif type(value) is list:
        for v in value:
            yield from _leaves(v)
    else:
        yield value


def _strict(d):
    """``d`` survives strict JSON unchanged: builtins only (no numpy scalars, which may pass
    ``json.dumps``), no NaN or infinity, no tuples."""
    assert json.loads(json.dumps(d, allow_nan=False)) == d
    assert {type(v) for v in _leaves(d)} <= {str, int, float, bool, type(None)}
    return d


def _binary(n=2_000, seed=0):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    p = np.clip(0.3 * y + rng.uniform(0, 0.7, n), 0, 1)
    return y, np.column_stack([1 - p, p])


def _multiclass(n, k, seed=0):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, k, n)
    logits = rng.normal(size=(n, k))
    logits[np.arange(n), y] += 1.5
    pred = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
    return y, pred


def test_binary_matches_sklearn():
    y, pred = _binary()
    d = _strict(diagnostics("classification", y, pred, ["no", "yes"]))
    assert d["version"] == 1 and d["task"] == "classification"
    assert d["n_rows"] == len(y) and d["sampled"] is False
    assert d["labels"] == ["no", "yes"]
    predicted = pred.argmax(axis=1)
    assert d["confusion"]["classes"] == [0, 1]
    assert d["confusion"]["matrix"] == confusion_matrix(y, predicted).tolist()  # rows actual
    p, r, f, s = precision_recall_fscore_support(y, predicted, zero_division=np.nan)
    assert d["per_class"] == [
        {
            "class": i,
            "precision": _six(p[i]),
            "recall": _six(r[i]),
            "f1": _six(f[i]),
            "support": s[i],
        }
        for i in range(2)
    ]
    assert d["per_class_truncated"] is False
    assert d["auc"] == _six(metrics.value("auc", y, pred))
    for name, keys in (("roc", ("fpr", "tpr", "threshold")), ("pr", ("precision", "recall"))):
        curve = d[name]
        lengths = {len(curve[key]) for key in (*keys, "threshold")}
        assert len(lengths) == 1 and 2 <= lengths.pop() <= 200
        assert all(np.isfinite(curve["threshold"]))
    assert d["roc"]["threshold"][0] == 1.0  # sklearn's inf
    assert (d["roc"]["fpr"][0], d["roc"]["tpr"][0]) == (0.0, 0.0)
    assert (d["roc"]["fpr"][-1], d["roc"]["tpr"][-1]) == (1.0, 1.0)
    assert (d["pr"]["recall"][0], d["pr"]["recall"][-1]) == (1.0, 0.0)
    calibration = d["calibration"]
    assert sum(row["count"] for row in calibration) == len(y)
    assert 1 <= len(calibration) <= 10
    assert all(0 <= row["predicted"] <= 1 and 0 <= row["observed"] <= 1 for row in calibration)


def test_calibration_bins_are_equal_width_and_skip_empty_ones():
    y = np.array([0, 1, 1, 1, 0, 1])
    p = np.array([0.05, 0.05, 0.95, 1.0, 0.55, 0.55])
    d = _strict(diagnostics("classification", y, np.column_stack([1 - p, p]), [0, 1]))
    assert d["calibration"] == [
        {"predicted": 0.05, "observed": 0.5, "count": 2},
        {"predicted": 0.55, "observed": 0.5, "count": 2},
        {"predicted": 0.975, "observed": 1.0, "count": 2},  # 1.0 falls in the last bin
    ]


def test_class_never_predicted_has_null_precision():
    y, pred = _multiclass(600, 3)
    pred[:, 2] = 0.0  # class 2 is never the argmax
    d = diagnostics("classification", y, pred, ["a", "b", "c"])
    json.dumps(d, allow_nan=False)
    _strict(d)
    row = d["per_class"][2]
    assert row["class"] == 2 and row["precision"] is None and row["recall"] == 0.0
    p, r, f, s = precision_recall_fscore_support(y, pred.argmax(axis=1), zero_division=np.nan)
    assert [row["f1"] for row in d["per_class"]] == [_six(v) for v in f]
    assert "roc" not in d and "pr" not in d and "auc" not in d and "calibration" not in d


@pytest.mark.parametrize("labels", [[False, True], ["1", 1], [np.False_, np.True_]])
def test_bool_and_mixed_labels_are_json(labels):
    y, pred = _binary(200)
    d = json.loads(json.dumps(diagnostics("classification", y, pred, labels), allow_nan=False))
    assert d["labels"] == jsonable(labels)
    assert [type(v) for v in d["labels"]] == [type(v) for v in jsonable(labels)]


@pytest.mark.parametrize(
    "labels, expected",
    [
        (
            [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-02")],
            ["2020-01-01 00:00:00", "2020-01-02 00:00:00"],  # as the artifact manifest has them
        ),
        ([pd.Timedelta(days=1), pd.Timedelta(days=2)], ["1 days 00:00:00", "2 days 00:00:00"]),
        ([decimal.Decimal("1.5"), datetime.date(2020, 1, 1)], ["1.5", "2020-01-01"]),
        ([np.int64(3), np.float64(0.5)], [3, 0.5]),
    ],
)
def test_labels_json_lacks_become_strings(labels, expected):
    y, pred = _binary(200)
    d = _strict(diagnostics("classification", y, pred, labels))
    assert d["labels"] == expected


def test_many_classes_are_capped():
    y, pred = _multiclass(20_000, 100)
    d = _strict(diagnostics("classification", y, pred, [f"c{i}" for i in range(100)]))
    classes, matrix = d["confusion"]["classes"], d["confusion"]["matrix"]
    assert len(matrix) == 31 and all(len(row) == 31 for row in matrix)
    assert classes[-1] == -1 and len(set(classes[:-1])) == 30
    support = np.bincount(y, minlength=100)
    assert sorted(support[classes[:-1]]) == sorted(support)[-30:]  # the 30 largest
    assert sum(map(sum, matrix)) == len(y)
    assert [sum(row) for row in matrix[:-1]] == support[classes[:-1]].tolist()
    assert "roc" not in d and "pr" not in d and "calibration" not in d
    assert len(d["per_class"]) == 100 and d["per_class_truncated"] is False
    assert len(json.dumps(d)) <= 256 * 1024


def test_confusion_keeps_the_largest_classes_in_index_order():
    y = np.repeat(np.arange(40), np.arange(1, 41))  # class i has i + 1 rows
    pred = np.eye(40)[y]
    d = _strict(diagnostics("classification", y, pred, list(range(40))))
    assert d["confusion"]["classes"] == [*range(10, 40), -1]
    assert d["confusion"]["matrix"][-1][-1] == sum(range(1, 11))  # "other" predicted as "other"


def test_per_class_keeps_the_200_largest_in_index_order():
    k = 250
    y = np.repeat(np.arange(k), np.where(np.arange(k) % 2 == 0, 3, 2))
    pred = np.eye(k)[y]
    d = _strict(diagnostics("classification", y, pred, list(range(k))))
    assert d["per_class_truncated"] is True
    # The 125 classes with 3 rows, then ties broken by index: the first 75 with 2 rows.
    expected = sorted([*range(0, k, 2), *range(1, 150, 2)])
    assert [row["class"] for row in d["per_class"]] == expected


def test_regression():
    rng = np.random.default_rng(0)
    y = rng.normal(10, 3, 5_000)
    pred = y + 1.0 + rng.normal(0, 0.1, 5_000)  # over-predicts by about 1
    d = _strict(diagnostics("regression", y, pred, None, seed=5))
    assert diagnostics("regression", y, pred, None, seed=5) == d
    assert diagnostics("regression", y, pred, None, seed=6)["points"] != d["points"]
    assert d["version"] == 1 and d["task"] == "regression"
    assert d["n_rows"] == 5_000 and d["sampled"] is False
    assert "labels" not in d and "confusion" not in d
    residuals = d["residuals"]
    assert len(residuals["edges"]) == 31 and len(residuals["counts"]) == 30
    assert sum(residuals["counts"]) == d["n_rows"]
    assert residuals["edges"][-1] < 0  # residual = actual - predicted
    deciles = d["by_decile"]
    assert len(deciles) == 10 and sum(row["count"] for row in deciles) == 5_000
    assert all(row["residual_mean"] < 0 for row in deciles)
    means = [row["predicted_mean"] for row in deciles]
    assert means == sorted(means)
    points = d["points"]
    assert len(points["actual"]) == len(points["predicted"]) == 2_000
    assert all(a < p for a, p in zip(points["actual"], points["predicted"], strict=True))


def test_regression_with_few_rows_and_a_constant_prediction():
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    d = _strict(diagnostics("regression", y, np.full(5, 3.0), None))
    assert sum(d["residuals"]["counts"]) == 5
    assert sum(row["count"] for row in d["by_decile"]) == 5
    assert sorted(d["points"]["actual"]) == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert d["points"]["predicted"] == [3.0] * 5


def test_points_are_not_in_row_order():
    y = np.arange(1_500.0)  # integers, so rounding is exact
    d = _strict(diagnostics("regression", y, y + 0.5, None, seed=1))
    actual = d["points"]["actual"]
    assert sorted(actual) == y.tolist() and actual != y.tolist()
    assert d["points"]["predicted"] == [a + 0.5 for a in actual]  # still paired
    assert diagnostics("regression", y, y + 0.5, None, seed=1)["points"]["actual"] == actual
    big = np.arange(3_000.0)
    sample = diagnostics("regression", big, big, None)["points"]["actual"]
    assert len(sample) == 2_000 and sample != sorted(sample)


def test_decile_std_has_ddof_0():
    pred = np.arange(20.0)  # 10 deciles of 2 rows each
    y = pred + np.tile([0.0, 2.0], 10)  # residuals 0 and 2 in every decile
    d = _strict(diagnostics("regression", y, pred, None))
    assert [row["residual_std"] for row in d["by_decile"]] == [1.0] * 10
    assert [row["residual_mean"] for row in d["by_decile"]] == [1.0] * 10


def test_values_large_against_their_spread_stay_distinct():
    rng = np.random.default_rng(0)
    residual = 1e6 + rng.uniform(0, 1e-3, 1_000)
    d = _strict(diagnostics("regression", residual, np.zeros(1_000), None))
    edges = d["residuals"]["edges"]
    assert len(set(edges)) == 31 and edges == sorted(edges)
    epoch = 1.7e9 + np.arange(100.0)  # epoch seconds: 6 digits would round to the 1,000
    d = _strict(diagnostics("regression", epoch, epoch - 3.0, None))
    assert sorted(d["points"]["actual"]) == epoch.tolist()
    means = [row["predicted_mean"] for row in d["by_decile"]]
    assert len(set(means)) == 10
    assert means[0] == 1.7e9 - 3.0 + 4.5  # the mean of the first 10 predictions, exactly


def test_floats_have_six_significant_digits():
    y = np.array([1 / 3, 2 / 3, 1e-9 / 7, 12345.6789])
    d = _strict(diagnostics("regression", y, np.zeros(4), None))
    assert sorted(d["points"]["actual"]) == [1.42857e-10, 0.333333, 0.666667, 12345.7]


def test_sampling():
    y, pred = _binary(250_000, seed=1)
    d = _strict(diagnostics("classification", y, pred, [0, 1], seed=3))
    assert d["n_rows"] == 200_000 and d["sampled"] is True
    assert sum(map(sum, d["confusion"]["matrix"])) == 200_000
    assert diagnostics("classification", y, pred, [0, 1], seed=3) == d
    assert diagnostics("classification", y, pred, [0, 1], seed=4) != d
    assert diagnostics("classification", y, pred, [0, 1], max_rows=1_000)["n_rows"] == 1_000


def test_binary_curves_need_both_classes():
    pred = np.column_stack([np.full(10, 0.7), np.full(10, 0.3)])
    d = _strict(diagnostics("classification", np.zeros(10, dtype=int), pred, ["a", "b"]))
    assert not {"auc", "roc", "pr", "calibration"} & set(d)
    assert d["confusion"]["matrix"] == [[10, 0], [0, 0]]


@pytest.mark.timing
def test_200k_binary_rows_take_at_most_a_second():
    y, pred = _binary(200_000, seed=2)
    start = time.perf_counter()
    diagnostics("classification", y, pred, [0, 1])
    assert time.perf_counter() - start <= 1.0


# --- AutoML.fit -----------------------------------------------------------------


def _iris():
    return load_iris(as_frame=True).frame


@pytest.fixture(scope="module")
def iris_model():
    config = TrainConfig(
        target="target", max_runtime_secs=10, max_models=4, keep_cv_predictions=True
    )
    return AutoML(config).fit(_iris())


def test_automl_fit_stores_diagnostics(iris_model):
    model = iris_model
    json.dumps(model.diagnostics, allow_nan=False)
    d = _strict(model.diagnostics)
    assert d["labels"] == jsonable(model.classes_)  # the JSON form of classes_
    assert d["n_rows"] == 150
    # Of the blended OOF predictions (iris's target holds the class codes).
    y = _iris()["target"].to_numpy()
    assert d["confusion"]["matrix"] == confusion_matrix(y, model.cv_predictions.argmax(1)).tolist()


def test_automl_fit_diagnoses_the_blend_with_its_seed():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"x": rng.normal(size=200)})
    df["y"] = 2 * df["x"] + rng.normal(scale=0.1, size=200)
    config = TrainConfig(
        target="y", max_runtime_secs=10, max_models=1, seed=5, keep_cv_predictions=True
    )
    model = AutoML(config, families=["LightGBM"]).fit(df)
    y = df["y"].to_numpy()
    assert model.diagnostics == diagnostics("regression", y, model.cv_predictions, None, seed=5)
    assert model.diagnostics != diagnostics("regression", y, model.cv_predictions, None, seed=0)


def test_diagnostics_failure_does_not_fail_training(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("broken\nsecond line")

    monkeypatch.setattr(automl_module, "diagnostics", fail)
    events = []
    config = TrainConfig(target="target", max_runtime_secs=10, max_models=1)
    model = AutoML(config, events.append, families=["LightGBM"]).fit(_iris())
    assert model.diagnostics is None
    notices = [e.data for e in events if e.type == "notice"]
    notice = next(n for n in notices if n.get("kind") == "diagnostics_error")
    assert notice["exception"] == "ValueError" and "broken" in notice["message"]
    assert events[-1].type == "finished"
    assert model.predict(_iris()).isin([0, 1, 2]).all()


def test_phase1_pickle_loads_without_diagnostics(iris_model, tmp_path):
    model = copy.copy(iris_model)
    assert model.diagnostics is not None
    del model.__dict__["diagnostics"]  # what a Phase 1 pickle holds
    joblib.dump(model, tmp_path / "model.joblib")
    loaded = joblib.load(tmp_path / "model.joblib")  # a file this test wrote itself
    assert loaded.diagnostics is None
    assert isinstance(loaded.predict_proba(_iris().head()), pd.DataFrame)
