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


def test_predicting_no_rows_gives_nothing_even_in_a_fresh_process():
    model = AutoML(_config(), families=["TextEmbedding"]).fit(_texts())
    embedding.forget()
    empty = _texts().drop(columns="y").iloc[:0]
    assert len(model.predict(empty)) == 0
    assert model.predict_proba(empty).shape[0] == 0


def test_an_empty_text_has_a_vector_like_any_other():
    model = AutoML(_config(), families=["TextEmbedding"]).fit(_texts())
    odd = pd.DataFrame({"text": ["", " ", None]})
    assert len(model.predict(odd)) == 3


def test_asking_for_it_on_data_without_prose_is_refused():
    frame = pd.DataFrame(
        {"x": np.arange(120.0), "z": np.arange(120.0) % 7, "y": np.arange(120) % 2}
    )
    with pytest.raises(ConfigError, match="needs a column of text"):
        AutoML(_config(), families=["TextEmbedding"]).fit(frame)
    model = AutoML(_config(), families=["LightGBM", "TextEmbedding"]).fit(frame)  # not searched
    assert "TextEmbedding" not in set(model.trials["family"])


def test_its_contributions_add_up_to_the_prediction_per_text_column():
    from fione.engine import explain

    frame = _texts()
    frame["n"] = np.arange(len(frame), dtype=float) % 5
    model = AutoML(_config(), families=["TextEmbedding"]).fit(frame)
    assert [m.key for m in model.members] == ["TextEmbedding"]
    X = frame.drop(columns="y").iloc[:12]
    out = explain.contributions(model, X)
    assert out.columns == ["text", "n"] and out.values.shape == (12, 3, 2)
    assert np.allclose(out.values[:, :, 1], 0)  # the number is not in this view
    assert np.allclose(out.prediction, model.predict_proba(X), atol=1e-6)
    assert explain.pd_rows(model, 100, 5) >= 1 and explain.contribution_rows(model, 100) >= 1
    curve = explain.partial_dependence(model, X, "n", grid_size=3, max_rows=6)
    assert curve is not None


def _binary_texts(n=200, seed=1):
    frame = _texts(n, seed)
    frame["y"] = (frame["y"] == "a").astype(int)
    return frame


def test_a_binary_task_fits_predicts_and_explains():
    from fione.engine import explain

    frame = _binary_texts()
    model = AutoML(_config(), families=["TextEmbedding"]).fit(frame)
    X = frame.drop(columns="y")
    assert model.predict(X.iloc[:0]).shape[0] == 0 and len(model.predict(X)) == len(X)
    out = explain.contributions(model, X.iloc[:10])
    assert np.allclose(
        out.prediction[:, 0], np.asarray(model.predict_proba(X.iloc[:10]))[:, 1], atol=1e-6
    )


def test_a_regression_task_fits_predicts_and_explains():
    from fione.engine import explain

    frame = _texts(200, 2)
    frame["y"] = frame["text"].str.len().astype(float) + (frame["y"] == "a") * 5.0
    model = AutoML(_config(), families=["TextEmbedding"]).fit(frame)
    X = frame.drop(columns="y")
    assert model.predict(X.iloc[:0]).shape[0] == 0 and len(model.predict(X)) == len(X)
    out = explain.contributions(model, X.iloc[:10])
    assert np.allclose(out.prediction[:, 0], model.predict(X.iloc[:10]), atol=1e-4)


def test_extra_rows_are_embedded_before_the_search_and_a_broken_backend_stops_there(monkeypatch):
    own, more = _texts(120, 0), _texts(100, 9)
    events = []
    AutoML(_config(), events.append, families=["TextEmbedding"]).fit(own, extra=more)
    first = next(i for i, e in enumerate(events) if e.type == "embedding")
    assert (
        first < next(i for i, e in enumerate(events) if e.type == "trial")
        if any(e.type == "trial" for e in events)
        else True
    )
    assert sum(StyleBackend.calls) <= 220  # every text once, extra rows included
    monkeypatch.setitem(embedding.BACKENDS, "style", "no_such_module:Nothing")
    embedding.forget()
    with pytest.raises(ConfigError, match="cannot run here"):
        AutoML(_config(), families=["TextEmbedding"]).fit(_texts(80, 4), extra=_texts(60, 8))


def test_vectors_that_are_not_finite_never_reach_the_cache(monkeypatch):
    class Overflow(StyleBackend):
        def embed(self, texts):
            return np.full((len(texts), DIM), 1e9, dtype=np.float32)  # float16 holds 65504

    monkeypatch.setitem(embedding.BACKENDS, "style", Overflow)
    embedding.forget()
    with pytest.raises(embedding.EmbeddingUnavailable, match="not finite"):
        embedding.embed_texts(_config().embedding, ["alpha beta"])
    assert embedding.missing(_config().embedding, ["alpha beta"]) == 1


def test_a_stop_is_heard_while_the_vectors_are_made(monkeypatch):
    from fione.engine.config import NoModelError

    monkeypatch.setattr(embedding, "CHUNK", 50)
    stop = lambda: len(StyleBackend.calls) >= 1  # noqa: E731
    with pytest.raises(NoModelError, match="cancelled"):
        AutoML(_config(), should_stop=stop, families=["TextEmbedding"]).fit(_texts())
    assert sum(StyleBackend.calls) <= 100  # not all 240 texts


def _two_models(**more):
    return _config(embedding_extra=[{"model": "toy2", "layer": 0.5}], **more)


def test_each_model_of_embedding_extra_reads_the_texts_in_a_family_of_its_own():
    config = _two_models()
    first, second = config.embedding_for("TextEmbedding"), config.embedding_for("TextEmbedding2")
    assert (first.model, second.model, second.layer) == ("toy", "toy2", 0.5)
    assert (
        config.embedding_for("TextEmbedding3") is None and config.embedding_for("LightGBM") is None
    )
    events = []
    model = AutoML(config, events.append, families=["TextEmbedding", "TextEmbedding2"]).fit(
        _texts()
    )
    assert {"TextEmbedding", "TextEmbedding2"} <= set(model.trials["family"])
    assert sum(StyleBackend.calls) <= 480  # each text once per model, never per trial
    assert len(model.predict(_texts(25, seed=3).drop(columns="y"))) == 25
    from fione.engine import explain

    X = _texts(8, seed=4).drop(columns="y")
    out = explain.contributions(model, X)
    assert np.allclose(out.prediction, model.predict_proba(X), atol=1e-6)


def test_the_settings_of_several_models_are_checked():
    ok = _two_models()
    assert ok.validate() is ok
    for bad in (
        {"embedding_extra": "toy2"},
        {"embedding_extra": [{"model": "a"}, {"model": "b"}, {"model": "c"}]},
        {"embedding_extra": [{"name": "toy2"}]},
        {"embedding_extra": [{"model": " "}]},
        {"embedding_extra": [{"model": "toy2", "layer": 2}]},
    ):
        with pytest.raises(ConfigError):
            _config(**bad).validate()
    with pytest.raises(ConfigError, match="needs an embedding_backend"):
        TrainConfig(target="y", embedding_extra=[{"model": "toy2"}]).validate()
    with pytest.raises(ConfigError, match="embedding_extra"):
        AutoML(_config(), families=["TextEmbedding2"])


def test_the_torch_backend_finds_each_model_in_a_directory_of_models(monkeypatch, tmp_path):
    from fione import embedding_torch
    from fione.engine.embedding import MODEL_ENV, EmbeddingSpec

    (tmp_path / "small").mkdir()
    (tmp_path / "small" / "config.json").write_text("{}")
    monkeypatch.setenv(MODEL_ENV, str(tmp_path))
    assert embedding_torch.model_directory(EmbeddingSpec("torch_lm", "small")) == str(
        tmp_path / "small"
    )
    assert embedding_torch.model_directory(EmbeddingSpec("torch_lm", "big")) == str(tmp_path)
