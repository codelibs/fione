"""Engine targets on real datasets (spec 5.6): accuracy, wall time, artifact size, latency.

Slow and needs the network, so they only run with ``-m acceptance`` (nightly in CI):
``uv run pytest tests/acceptance -m acceptance -q -s``.
"""

import time

import numpy as np
import pytest
from sklearn.datasets import fetch_california_housing, fetch_openml
from sklearn.model_selection import train_test_split

from fione.engine.artifact import load_model, save_model
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.storage import LocalStorage

pytestmark = pytest.mark.acceptance

SECRET = bytes(range(32))
MB = 1024 * 1024


def _download(fetch):
    try:
        return fetch()
    except Exception as e:  # any network, cache or parsing failure means no data to test on
        pytest.skip(f"dataset download failed: {type(e).__name__}: {e}")


def _fit_save_load(train, config, tmp_path, test):
    """Fit, save and reload; return the loaded model and the numbers worth reporting."""
    started = time.monotonic()
    model = AutoML(config).fit(train)
    fit_secs = time.monotonic() - started

    storage = LocalStorage(tmp_path / "store")
    save_model(model, storage, "models/1/", SECRET, image_tag="fione:acceptance")
    artifact_bytes = sum(storage.size(key) for key in storage.list("models/1/"))
    loaded = load_model(storage, "models/1/", SECRET)

    rows = test.head(1_000)
    started = time.perf_counter()
    loaded.predict(rows)
    predict_secs = time.perf_counter() - started
    started = time.perf_counter()
    loaded.predict(rows)
    warm_predict_secs = time.perf_counter() - started

    trials = model.trials[model.trials["state"] == "complete"].groupby("family").size().to_dict()
    members = model.leaderboard[model.leaderboard["weight"] > 0]
    print(
        f"\n  fit {fit_secs:.1f}s (budget {config.max_runtime_secs}s, stop: {model.stop_reason}), "
        f"artifact {artifact_bytes / MB:.1f} MB, predict 1,000 rows {predict_secs:.3f}s "
        f"(second call {warm_predict_secs:.3f}s)"
        f"\n  complete trials per family: {trials}"
        f"\n  members:\n{members[['model', 'family', 'cv_score', 'weight']].to_string(index=False)}"
    )
    return loaded, fit_secs, artifact_bytes, predict_secs


def test_adult_classification_targets(tmp_path):
    adult = _download(lambda: fetch_openml("adult", version=2, as_frame=True).frame)
    train, test = train_test_split(adult, test_size=0.25, random_state=0)
    config = TrainConfig(target="class", max_runtime_secs=120, seed=0)

    model, fit_secs, artifact_bytes, predict_secs = _fit_save_load(train, config, tmp_path, test)

    accuracy = (model.predict(test).astype(str) == test["class"].astype(str)).mean()
    print(f"  test accuracy {accuracy:.4f} (spike 0.876)")
    assert fit_secs <= 126  # 1.05 x the budget
    assert artifact_bytes <= 100 * MB
    assert predict_secs <= 0.5
    assert accuracy >= 0.866  # within 0.01 of the spike's 0.876


def test_california_housing_regression_targets(tmp_path):
    frame = _download(lambda: fetch_california_housing(as_frame=True).frame)
    train, test = train_test_split(frame, test_size=0.25, random_state=0)
    config = TrainConfig(target="MedHouseVal", max_runtime_secs=60, seed=0)

    model, fit_secs, artifact_bytes, predict_secs = _fit_save_load(train, config, tmp_path, test)

    rmse = float(np.sqrt(((model.predict(test) - test["MedHouseVal"]) ** 2).mean()))
    print(f"  test RMSE {rmse:.4f} (spike 0.4335, H2O 0.4387)")
    assert fit_secs <= 63  # 1.05 x the budget
    assert artifact_bytes <= 100 * MB
    assert predict_secs <= 0.5
    assert rmse <= 0.46
