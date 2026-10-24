import time

import pytest

from fione.engine.config import ConfigError, Deadline, NoModelError, TrainConfig
from fione.engine.events import Event


def test_train_config_defaults():
    config = TrainConfig(target="y")
    assert config.task == "auto"
    assert config.max_runtime_secs == 3600
    assert config.max_runtime_secs_per_model is None
    assert config.max_models is None
    assert config.nfolds == 5
    assert config.seed == 0
    assert config.balance_classes is False
    assert (config.stopping_rounds, config.stopping_metric, config.stopping_tolerance) == (
        3,
        "auto",
        0.001,
    )
    assert config.sort_metric == "auto"
    assert config.ignored_columns == []
    assert TrainConfig(target="y").ignored_columns is not config.ignored_columns


def test_train_config_dict_round_trip():
    config = TrainConfig(target="y", task="regression", max_runtime_secs=60, ignored_columns=["id"])
    assert TrainConfig.from_dict(config.to_dict()) == config


def test_from_dict_rejects_unknown_and_missing_keys():
    with pytest.raises(ConfigError, match="unknown parameters: \\['colour'\\]"):
        TrainConfig.from_dict({"target": "y", "colour": "red"})
    with pytest.raises(ConfigError, match="target is required"):
        TrainConfig.from_dict({"nfolds": 3})


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"target": ""}, "target"),
        ({"task": "clustering"}, "task"),
        ({"max_runtime_secs": 0}, "max_runtime_secs"),
        ({"max_runtime_secs": True}, "max_runtime_secs"),
        ({"max_runtime_secs_per_model": 0}, "max_runtime_secs_per_model"),
        ({"max_models": 0}, "max_models"),
        ({"nfolds": 1}, "nfolds"),
        ({"seed": 1.5}, "seed"),
        ({"stopping_rounds": -1}, "stopping_rounds"),
        ({"stopping_tolerance": -0.1}, "stopping_tolerance"),
        ({"stopping_metric": "f1"}, "stopping_metric"),
        ({"sort_metric": "speed"}, "sort_metric"),
        ({"balance_classes": "yes"}, "balance_classes"),
        ({"ignored_columns": "id"}, "ignored_columns"),
        ({"ignored_columns": ["y"]}, "target"),
    ],
)
def test_validate_rejects_bad_values(changes, message):
    with pytest.raises(ConfigError, match=message):
        TrainConfig(**{"target": "y", **changes}).validate()


def test_validate_accepts_h2o_metric_names_case_insensitively():
    config = TrainConfig(target="y", stopping_metric="AUC", sort_metric="logloss", max_models=10)
    assert config.validate() is config


def test_error_types():
    assert issubclass(ConfigError, ValueError)
    assert issubclass(NoModelError, RuntimeError)


def test_deadline_counts_down_and_expires():
    deadline = Deadline(0.05)
    assert 0 < deadline.remaining() <= 0.05
    assert not deadline.expired()
    time.sleep(0.06)
    assert deadline.expired()
    assert deadline.remaining() == 0.0


def test_deadline_child_never_outlives_parent():
    parent = Deadline(0.05)
    child = parent.child(10)
    parents_remaining = parent.remaining()
    assert child.remaining() <= parents_remaining  # measured later, so never more
    assert parent.child(0.01).remaining() <= 0.01
    time.sleep(0.06)
    assert parent.child(10).expired()


def test_event_defaults_timestamp_and_data():
    before = time.time()
    event = Event("trial", data={"score": 0.5})
    assert event.type == "trial"
    assert before <= event.ts <= time.time()
    assert Event("started").data == {}
