"""The TextEmbedding family: a linear model on the vectors a backend gives the prose columns."""

import pickle

import numpy as np
import pandas as pd
import pytest

from fione.engine import embedding
from fione.engine.automl import AutoML
from fione.engine.config import ConfigError, TrainConfig
from fione.engine.embedding import CACHE_ENV, text_keys

DIM = 32
MARKS = {"a": " ;;", "b": " ??", "c": " !!"}  # how each class ends its texts: a style, not a topic


class StyleBackend:
    """Counts of character pairs: it sees the punctuation, not the topic."""

    calls: list[int] = []

    def __init__(self, spec):
        self.spec = spec

    def embed(self, texts):
        StyleBackend.calls.append(len(texts))
        out = np.zeros((len(texts), DIM), dtype=np.float32)
        for row, text in enumerate(texts):
            for at in range(len(text) - 1):
                out[row, (ord(text[at]) * 31 + ord(text[at + 1])) % DIM] += 1
        return out / np.maximum(1, np.linalg.norm(out, axis=1, keepdims=True))


@pytest.fixture(autouse=True)
def backend(monkeypatch, tmp_path):
    StyleBackend.calls = []
    embedding.forget()
    monkeypatch.setitem(embedding.BACKENDS, "style", StyleBackend)
    monkeypatch.setenv(CACHE_ENV, str(tmp_path / "cache"))
    yield
    embedding.forget()


def _texts(n=240, seed=0):
    rng = np.random.default_rng(seed)
    words = "river stone engine copper garden velvet harbor signal meadow bridge".split()
    labels = rng.choice(list(MARKS), n)
    text = [" ".join(rng.choice(words, 14)) + MARKS[k] for k in labels]
    return pd.DataFrame({"text": text, "y": labels})


def _config(**more):
    return TrainConfig(
        target="y", max_runtime_secs=120, stopping_rounds=1, stopping_tolerance=0.5,
        feature_engineering=False, embedding_backend="style", embedding_model="toy",
        **more,
    )  # fmt: skip


def test_the_family_is_searched_with_a_backend_and_embeds_each_text_once():
    events = []
    model = AutoML(_config(), events.append, families=["TextLinear", "TextEmbedding"]).fit(_texts())
    assert "TextEmbedding" in set(model.trials["family"])
    kinds = [e.data.get("kind") for e in events if e.type == "notice"]
    assert "embedding_rows" in kinds and "family_error" not in kinds
    assert sum(StyleBackend.calls) <= 240  # the trials and folds read the cache, never the model
    assert model.predict(_texts(30, seed=3).drop(columns="y")).shape[0] == 30


def test_it_is_not_searched_without_a_backend_and_cannot_be_asked_for():
    config = _config().to_dict() | {"embedding_backend": None}
    model = AutoML(TrainConfig(**config), families=["TextLinear"]).fit(_texts())
    assert "TextEmbedding" not in set(model.trials["family"]) and not StyleBackend.calls
    with pytest.raises(ConfigError, match="needs an embedding_backend"):
        AutoML(TrainConfig(**config), families=["TextEmbedding"])


def test_a_model_holds_the_fingerprint_and_no_path_and_predicts_from_the_cache(tmp_path):
    model = AutoML(_config(), families=["TextEmbedding"]).fit(_texts())
    blob = pickle.dumps(model)
    assert str(tmp_path).encode() not in blob  # nothing of where the cache is
    new = _texts(20, seed=5).drop(columns="y")
    expected = model.predict(new)
    embedding.forget()  # another process: nothing in memory, the cache on disk
    StyleBackend.calls = []
    again = pickle.loads(blob).predict(new)
    assert list(again) == list(expected) and StyleBackend.calls == []


def test_a_row_the_cache_lacks_is_embedded_by_the_backend_at_prediction():
    model = AutoML(_config(), families=["TextEmbedding"]).fit(_texts())
    StyleBackend.calls = []
    fresh = pd.DataFrame({"text": ["completely new words here ;;", "other new words ??"]})
    assert len(model.predict(fresh)) == 2 and sum(StyleBackend.calls) == 2


def test_training_stops_at_the_start_when_the_backend_cannot_run(monkeypatch):
    monkeypatch.setitem(embedding.BACKENDS, "style", "no_such_module:Nothing")
    embedding.forget()
    with pytest.raises(ConfigError, match="cannot run here"):
        AutoML(_config(), families=["TextEmbedding"]).fit(_texts())


def test_the_prose_view_holds_only_the_texts():
    from fione.engine.prep import Prep

    X = _texts().drop(columns="y")
    X["n"] = np.arange(len(X), dtype=float)
    prep = Prep().fit(X)
    view = prep.text_prose(X)
    assert view.shape[1] == 1 and view.columns[0].endswith("_t")
    assert text_keys(view.iloc[:, 0].tolist()).shape == (len(X),)
