"""The star rating of the EasyML prediction summary (fione.models.rating)."""

import math
from contextlib import closing

import numpy as np
import pandas as pd
import pytest

from api_helpers import add_user, connect, login, upload
from fione.auth.roles import Role
from fione.engine import metrics
from fione.models.rating import Baseline, Rating, star_rating, target_baseline
from fione.projects import service as projects

NAN = float("nan")


@pytest.mark.parametrize(
    ("task", "model_metrics", "baseline", "degraded", "expected"),
    [
        # classification: (accuracy - majority) / (1 - majority)
        ("classification", {"accuracy": 0.95}, {"majority_rate": 1 / 3}, False, (5, "accuracy")),
        ("classification", {"accuracy": 0.5}, {"majority_rate": 0.5}, False, (1, "accuracy")),
        ("classification", {"accuracy": 0.4}, {"majority_rate": 0.5}, False, (1, "accuracy")),
        ("classification", {"accuracy": 0.6}, {"majority_rate": 0.5}, False, (2, "accuracy")),
        ("classification", {"accuracy": 1.0}, {"majority_rate": 0.9}, False, (5, "accuracy")),
        # the band edges: 0.2, 0.4, 0.6 and 0.8 each add a star
        ("classification", {"accuracy": 0.2}, {"majority_rate": 0.0}, False, (2, "accuracy")),
        ("classification", {"accuracy": 0.4}, {"majority_rate": 0.0}, False, (3, "accuracy")),
        ("classification", {"accuracy": 0.6}, {"majority_rate": 0.0}, False, (4, "accuracy")),
        ("classification", {"accuracy": 0.8}, {"majority_rate": 0.0}, False, (5, "accuracy")),
        ("classification", {"accuracy": 0.7999}, {"majority_rate": 0.0}, False, (4, "accuracy")),
        ("classification", {"accuracy": 0.1999}, {"majority_rate": 0.0}, False, (1, "accuracy")),
        # a degraded model is capped at 2 stars
        ("classification", {"accuracy": 0.99}, {"majority_rate": 0.5}, True, (2, "accuracy")),
        ("classification", {"accuracy": 0.55}, {"majority_rate": 0.5}, True, (1, "accuracy")),
        # no training data any more: binary models fall back to AUC
        ("classification", {"accuracy": 0.9, "auc": 0.95}, {}, False, (5, "auc")),
        ("classification", {"accuracy": 0.9, "auc": 0.62}, {}, False, (2, "auc")),
        ("classification", {"accuracy": 0.9, "auc": 0.4}, {}, False, (1, "auc")),
        # regression: 1 - rmse / std
        ("regression", {"rmse": 1.0}, {"target_std": 10.0}, False, (5, "rmse")),
        ("regression", {"rmse": 5.0}, {"target_std": 10.0}, False, (3, "rmse")),
        ("regression", {"rmse": 12.0}, {"target_std": 10.0}, False, (1, "rmse")),
        ("regression", {"rmse": 2.0}, {"target_std": 10.0}, True, (2, "rmse")),
        # no training data any more: from r2 (rmse / std = sqrt(1 - r2))
        ("regression", {"rmse": 1.0, "r2": 0.99}, {}, False, (5, "r2")),
        ("regression", {"rmse": 1.0, "r2": -0.5}, {}, False, (1, "r2")),
    ],
)
def test_star_rating(task, model_metrics, baseline, degraded, expected):
    rating = star_rating(task, model_metrics, degraded=degraded, **baseline)
    assert (rating.stars, rating.metric) == expected
    assert 0.0 <= rating.skill <= 1.0
    assert rating.note == ("degraded" if degraded else None)


@pytest.mark.parametrize(
    ("task", "model_metrics", "baseline", "note"),
    [
        ("classification", {"accuracy": 1.0}, {"majority_rate": 1.0}, "single_class"),
        ("classification", {"accuracy": NAN}, {"majority_rate": 0.5}, "no_metric"),
        ("classification", {"accuracy": NAN, "auc": NAN}, {}, "no_metric"),
        ("classification", {}, {"majority_rate": 0.5}, "no_metric"),
        ("classification", {"accuracy": 0.9}, {"majority_rate": NAN}, "no_metric"),
        ("regression", {"rmse": 0.0}, {"target_std": 0.0}, "constant_target"),
        ("regression", {"rmse": NAN, "r2": NAN}, {"target_std": 3.0}, "no_metric"),
        ("regression", {"rmse": None}, {}, "no_metric"),
        ("regression", {"rmse": True}, {"target_std": 3.0}, "no_metric"),  # not a number
        ("clustering", {"accuracy": 0.9}, {"majority_rate": 0.1}, "no_metric"),
    ],
)
def test_without_a_usable_metric_the_rating_is_one_star_with_a_note(
    task, model_metrics, baseline, note
):
    rating = star_rating(task, model_metrics, **baseline)
    assert (rating.stars, rating.skill, rating.note) == (1, None, note)
    assert isinstance(rating, Rating)


def test_the_r2_fallback_equals_the_rmse_rule():
    """With metrics.value's r2, 1 - rmse/std(ddof=0) == 1 - sqrt(1 - r2) exactly."""
    rng = np.random.default_rng(0)
    y = rng.normal(5, 2, 200)
    pred = y + rng.normal(0, 0.8, 200)
    rmse, r2 = metrics.value("rmse", y, pred), metrics.value("r2", y, pred)
    by_rmse = star_rating("regression", {"rmse": rmse}, target_std=float(np.std(y)))
    by_r2 = star_rating("regression", {"rmse": rmse, "r2": r2})
    assert math.isclose(by_rmse.skill, by_r2.skill, rel_tol=1e-9)
    assert by_rmse.stars == by_r2.stars


def test_baseline_reads_the_whole_training_target(make_client):
    client = make_client()
    user = add_user(client, "ed", Role.EDITOR)
    with closing(connect(client)) as conn:
        project = projects.create_project(conn, user, "P")
    csrf = login(client, "ed")
    frame = pd.DataFrame({"x": range(10), "label": ["a"] * 7 + ["b"] * 3, "y": [1.0, 3.0] * 5})
    r = upload(
        client, project.id, frame.to_csv(index=False).encode(), headers={"X-CSRF-Token": csrf}
    )
    dataset_id = r.json()["id"]
    storage = client.app.state.storage
    with closing(connect(client)) as conn:
        args = (storage, conn, project.id, dataset_id)
        assert target_baseline(*args, "label", "classification") == Baseline(majority_rate=0.7)
        assert target_baseline(*args, "y", "regression") == Baseline(target_std=1.0)
        assert target_baseline(*args, "nope", "regression") == Baseline()
        assert target_baseline(storage, conn, "other", dataset_id, "y", "regression") == Baseline()
        assert target_baseline(storage, conn, project.id, None, "y", "regression") == Baseline()
