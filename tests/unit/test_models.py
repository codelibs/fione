import dataclasses
import io
import json
import logging

import pandas as pd
import pytest
from sklearn.datasets import load_iris

from fione import db
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.engine.artifact import UntrustedArtifactError, save_model
from fione.engine.automl import AutoML
from fione.engine.config import ConfigError, TargetError, TrainConfig
from fione.jobs import store
from fione.models import service as models
from fione.models.service import ModelNotFound
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv
from fione.projects.service import DatasetNotFound, DatasetType, ProjectNotFound
from fione.storage import LocalStorage

SECRET = bytes(range(32))
CONFIG = {"target": "species", "max_runtime_secs": 10, "max_models": 3, "nfolds": 3}


def iris_csv() -> bytes:
    df = load_iris(as_frame=True).frame
    df["species"] = df.pop("target").map({0: "setosa", 1: "versicolor", 2: "virginica"})
    return df.to_csv(index=False).encode()


@pytest.fixture(scope="module")
def trained():
    df = load_iris(as_frame=True).frame
    df["species"] = df.pop("target").map({0: "setosa", 1: "versicolor", 2: "virginica"})
    config = TrainConfig(**CONFIG)
    return AutoML(config, families=["ExtraTrees"]).fit(df), df


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "fione.db")
    db.migrate(c)
    yield c
    c.close()


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "storage")


@pytest.fixture
def owner(conn):
    return auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)


@pytest.fixture
def project(conn, owner):
    return projects.create_project(conn, owner, "iris")


@pytest.fixture
def dataset(conn, storage, project):
    return ingest_csv(storage, conn, project.id, "iris", DatasetType.TRAIN, io.BytesIO(iris_csv()))


@pytest.fixture
def stored(conn, storage, project, dataset, trained):
    """A model saved under the project's prefix and recorded, as the handler does."""
    model, _ = trained
    job = store.enqueue(conn, "automl", project.id, project.owner_id, {})
    prefix = f"projects/{project.id}/models/abc123/"
    save_model(model, storage, prefix, SECRET, image_tag="test")
    return models.add_model(
        conn,
        project_id=project.id,
        dataset_id=dataset.id,
        job_id=job.id,
        name="iris model",
        model=model,
        storage_prefix=prefix,
    )


# --- records ------------------------------------------------------------------


def test_add_model_records_the_training_outcome(stored, trained, dataset):
    model, _ = trained
    assert stored.id > 0 and stored.name == "iris model"
    assert (stored.task, stored.target, stored.trusted) == ("classification", "species", 1)
    assert stored.dataset_id == dataset.id and stored.stop_reason == model.stop_reason
    assert stored.storage_prefix.endswith("/models/abc123/") and stored.created_at > 0
    assert stored.config["target"] == "species" and stored.config["max_models"] == 3
    assert [row["model"] for row in stored.leaderboard] == list(model.leaderboard["model"])
    assert {r["model"]: r["weight"] for r in stored.leaderboard}["Ensemble"] is None
    assert set(stored.importance) == set(model.columns)
    assert sum(stored.importance.values()) == pytest.approx(1.0)
    assert stored.metrics == pytest.approx(model.metrics)
    assert {t["family"] for t in stored.trials} == {"ExtraTrees"}
    json.dumps(stored.leaderboard, allow_nan=False)


def test_a_single_member_model_is_named_after_that_member(stored):
    assert stored.best_model.startswith("ExtraTrees_")


def test_best_model_rule():
    def row(model, weight):
        return {"model": model, "weight": weight}

    ensemble = [row("Ensemble", None), row("A_1", 0.6), row("B_2", 0.4), row("C_3", 0.0)]
    assert models.best_model_name(ensemble) == "Ensemble"
    # An ensemble of one member is that member, even if it is not the top row.
    single = [row("Ensemble", None), row("C_3", 0.0), row("A_1", 1.0)]
    assert models.best_model_name(single) == "A_1"


def test_get_and_list_models_newest_first(conn, project, stored, trained, dataset):
    model, _ = trained
    second = models.add_model(
        conn,
        project_id=project.id,
        dataset_id=None,
        job_id=None,
        name="second",
        model=model,
        storage_prefix=f"projects/{project.id}/models/def456/",
    )
    assert models.get_model(conn, stored.id) == stored
    assert [m.id for m in models.list_models(conn, project.id)] == [second.id, stored.id]
    assert models.list_models(conn, "no-such-project") == []
    with pytest.raises(ModelNotFound):
        models.get_model(conn, 9999)


def test_add_model_stores_diagnostics(conn, stored, trained):
    model, _ = trained
    assert model.diagnostics["task"] == "classification"
    assert stored.diagnostics == model.diagnostics
    row = conn.execute("SELECT diagnostics_json FROM models WHERE id = ?", (stored.id,)).fetchone()
    assert json.loads(row[0]) == model.diagnostics


def test_brief_records_have_no_diagnostics(conn, project, stored):
    assert stored.diagnostics is not None
    assert [r.diagnostics for r in models.list_models_brief(conn, project.id)] == [None]


def add_with_diagnostics(conn, project, trained, diagnostics):
    model, _ = trained
    return models.add_model(
        conn,
        project_id=project.id,
        dataset_id=None,
        job_id=None,
        name="d",
        model=dataclasses.replace(model, diagnostics=diagnostics),
        storage_prefix=f"projects/{project.id}/models/d/",
    )


def test_a_model_without_diagnostics_stores_null(conn, project, trained):
    record = add_with_diagnostics(conn, project, trained, None)
    assert record.diagnostics is None
    row = conn.execute("SELECT diagnostics_json FROM models WHERE id = ?", (record.id,)).fetchone()
    assert row[0] is None


def padded(size: int) -> dict:
    """Diagnostics whose JSON is ``size`` bytes of UTF-8."""
    empty = len(json.dumps({"pad": ""}).encode())
    return {"pad": "a" * (size - empty)}


@pytest.mark.parametrize(
    "diagnostics",
    [
        {"version": 1, "auc": float("nan")},
        {"version": 1, "labels": [pd.Timestamp("2020-01-01")]},
        {"version": 1, "labels": ["\ud800"]},
        ["not", "an", "object"],
        padded(models.MAX_DIAGNOSTICS_BYTES + 1),
    ],
    ids=["nan", "not-json", "surrogate", "list", "too-large"],
)
def test_diagnostics_that_cannot_be_stored_never_fail_the_model(
    conn, project, trained, diagnostics, caplog
):
    with caplog.at_level(logging.WARNING, logger="fione.models.service"):
        record = add_with_diagnostics(conn, project, trained, diagnostics)
    assert record.diagnostics is None and record.name == "d"
    assert "diagnostics" in caplog.text


def test_diagnostics_up_to_the_cap_are_stored(conn, project, trained):
    diagnostics = padded(models.MAX_DIAGNOSTICS_BYTES)
    assert add_with_diagnostics(conn, project, trained, diagnostics).diagnostics == diagnostics


def test_load_trained_predicts_the_training_labels(stored, storage, trained):
    model, df = trained
    loaded = models.load_trained(storage, stored, SECRET)
    labels = loaded.predict(df.drop(columns=["species"]))
    assert (labels.to_numpy() == df["species"].to_numpy()).mean() > 0.9
    assert list(labels) == list(model.predict(df.drop(columns=["species"])))


@pytest.mark.parametrize("trusted", [0, 1])
def test_load_trained_refuses_an_artifact_that_does_not_verify(conn, stored, storage, trusted):
    conn.execute("UPDATE models SET trusted = ? WHERE id = ?", (trusted, stored.id))
    record = models.get_model(conn, stored.id)
    key = record.storage_prefix + "model.joblib"
    storage.put(key, storage.get(key) + b"tampered")
    with pytest.raises(UntrustedArtifactError):
        models.load_trained(storage, record, SECRET)


def test_load_trained_with_another_secret_is_refused(stored, storage):
    with pytest.raises(UntrustedArtifactError):
        models.load_trained(storage, stored, bytes(range(1, 33)))


# --- deletion -----------------------------------------------------------------


def test_delete_model_removes_row_and_objects(conn, storage, stored):
    assert storage.list(stored.storage_prefix)
    models.delete_model(conn, storage, stored.id)
    assert storage.list(stored.storage_prefix) == []
    with pytest.raises(ModelNotFound):
        models.get_model(conn, stored.id)


def test_delete_model_tolerates_missing_objects(conn, storage, stored):
    storage.delete_prefix(stored.storage_prefix)
    models.delete_model(conn, storage, stored.id)
    assert models.list_models(conn, stored.project_id) == []


def test_a_storage_failure_keeps_the_row_so_it_never_points_at_deleted_data(
    conn, storage, stored, monkeypatch
):
    def fail(prefix):
        raise OSError("storage down")

    monkeypatch.setattr(storage, "delete_prefix", fail)
    with pytest.raises(OSError):
        models.delete_model(conn, storage, stored.id)
    assert models.get_model(conn, stored.id) == stored


def test_deleting_the_project_removes_its_models(conn, storage, owner, project, stored):
    projects.delete_project(conn, storage, owner, project.id)
    assert conn.execute("SELECT COUNT(*) FROM models").fetchone()[0] == 0
    assert storage.list("projects/") == []


def test_deleting_the_dataset_or_job_keeps_the_model(conn, storage, stored, dataset):
    projects.delete_dataset(conn, storage, dataset.id)
    conn.execute("DELETE FROM jobs WHERE id = ?", (stored.job_id,))
    kept = models.get_model(conn, stored.id)
    assert kept.dataset_id is None and kept.job_id is None


# --- submit_training ----------------------------------------------------------


def job_count(conn):
    return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]


def test_submit_training_enqueues_an_automl_job(conn, storage, owner, project, dataset):
    job = models.submit_training(conn, storage, owner, project.id, dataset.id, CONFIG, name="mine")
    assert (job.kind, job.project_id, job.owner_id) == ("automl", project.id, owner.id)
    assert job.payload["dataset_id"] == dataset.id and job.payload["name"] == "mine"
    assert job.payload["config"] == TrainConfig(**CONFIG).to_dict()


def test_submit_training_takes_a_config_object_and_an_editor_member(
    conn, storage, owner, project, dataset
):
    member = auth.create_user(conn, "member", "pw-member-1", Role.EDITOR)
    projects.share_project(conn, owner, project.id, "member", ProjectAccess.EDITOR)
    job = models.submit_training(
        conn, storage, member, project.id, dataset.id, TrainConfig(**CONFIG)
    )
    assert job.payload["name"] is None and job.owner_id == member.id


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (
            {**CONFIG, "ignored_columns": ["nope"]},
            r"unknown columns in ignored_columns: \['nope'\]",
        ),
        ({**CONFIG, "target": "nope"}, "target column 'nope' is not in the data"),
        ({**CONFIG, "ignored_columns": ["species"]}, "cannot also be ignored"),
        ({**CONFIG, "nfolds": 1}, "nfolds"),
        ({"max_runtime_secs": 5}, "target is required"),
        ({**CONFIG, "bogus": 1}, "unknown parameters"),
    ],
)
def test_a_bad_config_is_refused_before_a_job_is_queued(
    conn, storage, owner, project, dataset, config, message
):
    with pytest.raises(ConfigError, match=message):
        models.submit_training(conn, storage, owner, project.id, dataset.id, config)
    assert job_count(conn) == 0


def test_a_viewer_cannot_train(conn, storage, owner, project, dataset):
    viewer = auth.create_user(conn, "viewer", "pw-viewer-1", Role.VIEWER)
    projects.share_project(conn, owner, project.id, "viewer", ProjectAccess.VIEWER)
    with pytest.raises(PermissionError):
        models.submit_training(conn, storage, viewer, project.id, dataset.id, CONFIG)
    assert job_count(conn) == 0


def test_a_non_member_cannot_train(conn, storage, project, dataset):
    stranger = auth.create_user(conn, "stranger", "pw-stranger-1", Role.EDITOR)
    with pytest.raises(PermissionError):
        models.submit_training(conn, storage, stranger, project.id, dataset.id, CONFIG)
    assert job_count(conn) == 0


def test_the_project_must_exist(conn, storage, owner, dataset):
    with pytest.raises(ProjectNotFound):
        models.submit_training(conn, storage, owner, "no-such-project", dataset.id, CONFIG)


def test_only_a_train_dataset_can_be_used(conn, storage, owner, project):
    predict = ingest_csv(
        storage, conn, project.id, "p", DatasetType.PREDICT, io.BytesIO(iris_csv())
    )
    with pytest.raises(ValueError, match="training needs a train dataset"):
        models.submit_training(conn, storage, owner, project.id, predict.id, CONFIG)
    assert job_count(conn) == 0


def test_a_dataset_of_another_project_is_not_found(conn, storage, owner, project):
    other = projects.create_project(conn, owner, "other")
    foreign = ingest_csv(storage, conn, other.id, "iris", DatasetType.TRAIN, io.BytesIO(iris_csv()))
    with pytest.raises(DatasetNotFound):
        models.submit_training(conn, storage, owner, project.id, foreign.id, CONFIG)
    with pytest.raises(DatasetNotFound):
        models.submit_training(conn, storage, owner, project.id, 9999, CONFIG)
    assert job_count(conn) == 0


@pytest.mark.parametrize(
    ("frame", "config", "code"),
    [
        (pd.DataFrame({"x": range(20), "y": [1.0, None] * 10}), {"target": "y"}, "missing"),
        (pd.DataFrame({"x": range(20), "y": ["a"] * 20}), {"target": "y"}, "single_value"),
        (pd.DataFrame({"x": range(5), "y": [0, 1, 0, 1, 0]}), {"target": "y"}, "few_rows"),
        (
            pd.DataFrame({"x": range(20), "y": ["a", "b"] * 10}),
            {"target": "y", "task": "regression"},
            "not_numeric",
        ),
    ],
)
def test_a_target_the_engine_would_refuse_is_refused_before_a_job_is_queued(
    conn, storage, owner, project, frame, config, code
):
    """The whole target column goes through the engine's own check, not a sample."""
    data = io.BytesIO(frame.to_csv(index=False).encode())
    dataset = ingest_csv(storage, conn, project.id, "d", DatasetType.TRAIN, data)
    with pytest.raises(TargetError) as raised:
        models.submit_training(conn, storage, owner, project.id, dataset.id, config)
    assert raised.value.code == code
    assert job_count(conn) == 0


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({**CONFIG, "sort_metric": "rmse"}, "sort_metric 'rmse' does not apply to classification"),
        ({**CONFIG, "stopping_metric": "r2"}, "stopping_metric 'r2' does not apply"),
        ({**CONFIG, "sort_metric": "deviance"}, "does not apply to classification"),
        ({**CONFIG, "seed": -1}, "seed must be a whole number from 0 to 4294967295"),
        ({**CONFIG, "seed": 2**32}, "seed must be a whole number from 0 to 4294967295"),
    ],
)
def test_metrics_and_seed_the_engine_cannot_use_are_refused_up_front(
    conn, storage, owner, project, dataset, config, message
):
    with pytest.raises(ConfigError, match=message):
        models.submit_training(conn, storage, owner, project.id, dataset.id, config)
    assert job_count(conn) == 0


def test_the_largest_seed_and_task_metrics_are_accepted(conn, storage, owner, project, dataset):
    config = {**CONFIG, "seed": 2**32 - 1, "sort_metric": "AUC", "stopping_metric": "accuracy"}
    job = models.submit_training(conn, storage, owner, project.id, dataset.id, config)
    assert job.payload["config"]["seed"] == 2**32 - 1
