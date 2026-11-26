"""A table whose only input is text: the families that read a constant column are left out."""

import numpy as np
import pandas as pd

from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.engine.families import FAMILIES
from fione.engine.prep import Prep

WORDS = {
    "a": "river stone quiet harbor lantern marsh".split(),
    "b": "engine copper signal bridge voltage circuit".split(),
    "c": "garden velvet orchard whisper meadow blossom".split(),
}


def _texts(n=240, seed=0):
    rng = np.random.default_rng(seed)
    labels = rng.choice(list(WORDS), n)
    common = "the of and with over under between across around near".split()
    text = [
        " ".join(rng.choice(WORDS[k] + common * 2, 14)) + " " + str(rng.integers(0, 9))
        for k in labels
    ]
    return pd.DataFrame({"text": text, "y": labels})


def test_a_table_of_text_only_reads_only_prose():
    X = _texts().drop(columns="y")
    assert Prep().fit(X).reads_only_prose
    X["n"] = np.random.default_rng(1).normal(size=len(X))
    assert not Prep().fit(X).reads_only_prose  # a number is an input too
    X = _texts().drop(columns="y")
    X["kind"] = np.random.default_rng(1).choice(["p", "q", "r"], len(X))
    assert not Prep().fit(X).reads_only_prose  # so is a category
    X = _texts().drop(columns="y")
    X["id"] = [f"row-{i:05d}" for i in range(len(X))]
    assert Prep().fit(X).reads_only_prose  # an id, whose values are all different, carries nothing
    X["id"] = [f"key-{i % 80:03d}" for i in range(len(X))]  # a key of 3 rows each is no id
    assert not Prep().fit(X).reads_only_prose


def test_a_table_of_text_only_is_not_fitted_by_the_families_that_read_a_constant():
    events = []
    config = TrainConfig(
        target="y", max_runtime_secs=240, stopping_rounds=1, stopping_tolerance=0.5,
        feature_engineering=False,
    )  # fmt: skip
    model = AutoML(config, events.append).fit(_texts())
    families = set(model.trials["family"])
    assert families and all(FAMILIES[name].view.startswith("text") for name in families)
    kinds = [e.data.get("kind") for e in events if e.type == "notice"]
    assert "families_left_out" in kinds and "family_error" not in kinds
    assert model.predict(_texts(30, seed=3).drop(columns="y")).shape[0] == 30


def test_families_named_by_the_caller_are_kept():
    config = TrainConfig(
        target="y", max_runtime_secs=120, stopping_rounds=1, stopping_tolerance=0.5,
        feature_engineering=False,
    )  # fmt: skip
    model = AutoML(config, families=["LightGBM", "TextLinear"]).fit(_texts())
    assert "LightGBM" in set(model.trials["family"])
