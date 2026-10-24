import numpy as np
import pytest

from fione.engine import metrics
from fione.engine.config import ConfigError
from fione.engine.ensemble import caruana
from fione.engine.search import score


def _probabilities(y, noise, rng, k=2):
    """Class probabilities that favour the true class, blurred by ``noise``."""
    logits = rng.normal(scale=noise, size=(len(y), k))
    logits[np.arange(len(y)), y] += 1.0
    e = np.exp(logits)
    return e / e.sum(axis=1, keepdims=True)


def test_weights_sum_to_one_and_cover_every_candidate():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500)
    oof = {name: _probabilities(y, 1.0, rng) for name in ("A", "B", "C")}
    weights = caruana(oof, y, "classification")
    assert list(weights) == ["A", "B", "C"]
    assert sum(weights.values()) == pytest.approx(1.0)
    assert all(w >= 0 for w in weights.values())


def test_complementary_models_are_mixed_and_beat_the_best_single():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 2_000)
    oof = {"A": _probabilities(y, 1.0, rng), "B": _probabilities(y, 1.0, rng)}
    weights = caruana(oof, y, "classification")
    assert 0 < weights["A"] < 1 and 0 < weights["B"] < 1
    blend = weights["A"] * oof["A"] + weights["B"] * oof["B"]
    best_single = min(score("classification", y, p) for p in oof.values())
    assert score("classification", y, blend) < best_single


def test_weights_collapse_onto_the_best_model_when_others_only_hurt():
    rng = np.random.default_rng(2)
    y = rng.integers(0, 2, 1_000)
    good = _probabilities(y, 0.3, rng)
    noise = rng.dirichlet([1, 1], len(y))
    assert caruana({"noise": noise, "good": good}, y, "classification") == {
        "noise": 0.0,
        "good": 1.0,
    }


def test_ties_go_to_the_first_candidate():
    rng = np.random.default_rng(3)
    y = rng.integers(0, 3, 300)
    p = _probabilities(y, 1.0, rng, k=3)
    assert caruana({"A": p, "B": p.copy()}, y, "classification") == {"A": 1.0, "B": 0.0}


def test_regression_uses_rmse_and_a_custom_metric_is_honoured():
    rng = np.random.default_rng(4)
    y = rng.normal(size=1_000)
    oof = {"A": y + rng.normal(scale=0.5, size=len(y)), "B": y + rng.normal(scale=0.5, size=len(y))}
    weights = caruana(oof, y, "regression")
    assert 0 < weights["A"] < 1
    # A metric that only rewards matching model B selects B alone.
    only_b = caruana(
        oof, y, "regression", metric=lambda _, pred: float(np.abs(pred - oof["B"]).sum())
    )
    assert only_b == {"A": 0.0, "B": 1.0}


# --- metrics ------------------------------------------------------------------


@pytest.mark.parametrize(
    "task, name, resolved",
    [
        ("classification", "auto", "logloss"),
        ("classification", "AUC", "auc"),
        ("classification", "accuracy", "accuracy"),
        ("regression", "auto", "rmse"),
        ("regression", "mae", "mae"),
        ("regression", "r2", "r2"),
    ],
)
def test_resolve_metric(task, name, resolved):
    assert metrics.resolve(name, task, "sort_metric") == resolved


@pytest.mark.parametrize(
    "task, name",
    [("classification", "rmse"), ("regression", "auc"), ("classification", "aucpr")],
)
def test_resolve_rejects_metrics_that_do_not_fit_the_task(task, name):
    with pytest.raises(ConfigError, match="sort_metric"):
        metrics.resolve(name, task, "sort_metric")


def test_losses_are_lower_is_better():
    y = np.array([0, 1, 1, 0])
    good = np.array([[0.9, 0.1], [0.2, 0.8], [0.3, 0.7], [0.6, 0.4]])
    bad = good[:, ::-1]
    for name in ("logloss", "auc", "accuracy"):
        assert metrics.loss(name, y, good) < metrics.loss(name, y, bad)
    yr = np.array([1.0, 2.0, 3.0, 4.0])
    for name in ("rmse", "mae", "r2"):
        assert metrics.loss(name, yr, yr + 0.1) < metrics.loss(name, yr, yr[::-1])


def test_multiclass_auc_is_one_vs_rest_macro():
    y = np.array([0, 1, 2, 0, 1, 2])
    p = np.eye(3)[y] * 0.7 + 0.1
    assert metrics.value("auc", y, p) == pytest.approx(1.0)


def test_summary_lists_the_task_metrics():
    y = np.array([0, 1, 1, 0])
    p = np.array([[0.9, 0.1], [0.2, 0.8], [0.3, 0.7], [0.6, 0.4]])
    assert set(metrics.summary("classification", y, p)) == {"logloss", "accuracy", "auc"}
    assert set(metrics.summary("classification", np.array([0, 1, 2]), np.eye(3))) == {
        "logloss",
        "accuracy",
    }
    assert set(metrics.summary("regression", np.arange(4.0), np.arange(4.0))) == {
        "rmse",
        "mae",
        "r2",
    }
