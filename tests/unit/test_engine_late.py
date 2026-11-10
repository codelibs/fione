"""The late phase of the search: families that run only in the search time the others leave."""

import pickle
import time

import numpy as np
import pandas as pd
import pytest

from fione.engine import automl as automl_module
from fione.engine import explain, search
from fione.engine.automl import FAMILY_ORDER, LATE_ORDER, AutoML
from fione.engine.config import TrainConfig
from fione.engine.ensemble import caruana
from fione.engine.families import FAMILIES, TextLinear
from fione.engine.features import TextShape
from fione.engine.model import Member, TrainedModel, feature_importance
from fione.engine.prep import Prep

CLASSES = ["food", "law", "space"]


def _posts(n=300, seed=0):
    """Short texts on three subjects, and a number that says nothing."""
    rng = np.random.default_rng(seed)
    subjects = {
        "space": "rocket orbit launch moon crew planet".split(),
        "food": "bread cheese soup butter sauce flour".split(),
        "law": "court judge appeal verdict trial clause".split(),
    }
    labels = rng.choice(list(subjects), n)
    texts = [" ".join(rng.choice(subjects[label], 8)) for label in labels]
    return pd.DataFrame({"post": texts, "noise": rng.normal(size=n), "topic": labels})


def _codes(df):
    return pd.Categorical(df["topic"], categories=CLASSES).codes.astype(np.int64)


def _fit(df, families=None, **config):
    # A generous budget: a family whose time share expires before its first trial finishes is
    # skipped, and a loaded machine would then leave it out. With max_models set, the search
    # ends early, so a long budget only matters when time is short.
    config.setdefault("max_runtime_secs", 600)
    return AutoML(TrainConfig(**config), families=families).fit(df)


# --- the schedule: a search with stand-ins that take no time -------------------------------


def _schedule(
    monkeypatch, reference_secs, max_models=None, late=LATE_ORDER, exhaust=False, spend=None
):
    """Run ``AutoML._search`` over the base families and ``late`` with a ``run_family`` that
    takes no time (with ``exhaust``, the last base family takes the whole search time, 0.3 s).
    TextLinear's first trial took ``reference_secs``. With ``spend`` (the search time, in
    seconds), every base family uses up its whole share. Returns ``(name, time share, max trials)``
    per call."""
    calls = []
    total = search.Deadline(spend or (0.3 if exhaust else 100.0))

    def fake(name, X, y, folds, task, prep, deadline, *args, max_trials=None, **kwargs):
        calls.append((name, deadline.remaining(), max_trials))
        if exhaust and name == FAMILY_ORDER[-1]:
            time.sleep(total.remaining())
        if spend and name in FAMILY_ORDER:
            time.sleep(deadline.remaining())
        row = {
            "family": name,
            "trial": 0,
            "state": "complete",
            "score": 0.5,
            "elapsed": reference_secs,
            "params": {},
        }
        return search.FamilyResult(
            np.zeros((1, 2)),
            [object()],
            {},
            1,
            0.5,
            0.0,
            FAMILIES[name],
            "no_improvement",
            log=[row],
        )

    monkeypatch.setattr(automl_module, "run_family", fake)
    runner = AutoML(TrainConfig(target="y", max_models=max_models))
    families = [*FAMILY_ORDER, *late]
    runner._search(families, None, None, None, "classification", None, total, None, None)
    return calls


def test_late_families_get_a_share_of_the_search_time_left(monkeypatch):
    calls = _schedule(monkeypatch, reference_secs=0.1)
    assert [name for name, _, _ in calls] == [*FAMILY_ORDER, *LATE_ORDER]
    shares = {name: share for name, share, _ in calls}
    # Nothing was used, so 100 s are left; each gets its weight among those not yet run.
    assert shares["TextLinearChar"] == pytest.approx(50, rel=0.01)
    assert shares["TextLinearPlain"] == pytest.approx(50, rel=0.01)
    assert shares["TextLinearWide"] == pytest.approx(100, rel=0.01)


def test_a_share_of_the_search_time_is_kept_for_the_late_families(monkeypatch):
    weights = automl_module.FAMILY_WEIGHTS
    share = automl_module.LATE_SHARE
    assert share == 0.15
    calls = _schedule(monkeypatch, reference_secs=0.1)
    base = [(name, secs) for name, secs, _ in calls if name in FAMILY_ORDER]
    for i, (name, secs) in enumerate(base):
        # No time was used: each takes its weight of what is left. TextLinear (the family the
        # late ones vary) sees all 100 s, as without late families, the others 85 s.
        left = 100 if name == "TextLinear" else 100 * (1 - share)
        expected = left * weights[name] / sum(weights[f] for f in FAMILY_ORDER[i:])
        assert secs == pytest.approx(expected, rel=0.01)
    assert base[-1][1] == pytest.approx(85, rel=0.01)  # the last one: all that the base may use
    # Each uses its whole share: the base families spend 85% of 2 s, the late ones get the rest.
    calls = _schedule(monkeypatch, reference_secs=0.001, spend=2.0)
    shares = {name: secs for name, secs, _ in calls}
    assert shares["TextLinearChar"] == pytest.approx(0.5 * 0.3, rel=0.25)
    assert [name for name, _, _ in calls][-3:] == list(LATE_ORDER)  # and they all ran
    others = sum(secs for name, secs, _ in calls if name in FAMILY_ORDER and name != "TextLinear")
    assert others <= (1 - share) * 2.0 * 1.02  # the others together never pass 85% of the time


def test_textlinear_keeps_the_share_it_has_without_late_families(monkeypatch):
    with_late = _schedule(monkeypatch, reference_secs=0.001, spend=2.0)
    without = _schedule(monkeypatch, reference_secs=0.001, spend=2.0, late=())
    share = {name: secs for name, secs, _ in with_late}["TextLinear"]
    # LightGBM ran under a smaller share, so more of the time is left for TextLinear.
    assert share >= {name: secs for name, secs, _ in without}["TextLinear"] * 0.99


def test_late_families_alone_have_the_whole_search_time(monkeypatch):
    calls = []

    def fake(name, X, y, folds, task, prep, deadline, *args, **kwargs):
        calls.append((name, deadline.remaining()))
        raise automl_module.NoModelError("stop")

    monkeypatch.setattr(automl_module, "run_family", fake)
    runner = AutoML(TrainConfig(target="y"), families=["TextLinearWide"])
    runner._search(
        ["TextLinearWide"],
        None,
        None,
        None,
        "classification",
        None,
        search.Deadline(100),
        None,
        None,
    )
    assert calls[0][1] == pytest.approx(100, rel=0.01)  # not 15 s


@pytest.mark.parametrize("name", LATE_ORDER)
def test_an_explicit_list_of_late_families_is_trained_even_without_prose(name):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(150, 3)), columns=list("abc"))
    df["y"] = (df["a"] > 0).astype(int)
    model = _fit(df, [name], target="y", max_models=1, max_runtime_secs=30)
    assert set(model.leaderboard["family"]) == {name, "Ensemble"}


def test_late_families_do_not_run_when_the_others_used_the_search_time(monkeypatch):
    # What follows the search (the refit and the reserve) is not theirs to take.
    calls = _schedule(monkeypatch, reference_secs=0.1, exhaust=True)
    assert [name for name, _, _ in calls] == list(FAMILY_ORDER)


def test_a_late_family_runs_only_if_its_first_trial_is_expected_to_fit(monkeypatch):
    # TextLinear's first trial took 20 s: the character variant (5 times as long) needs 100 s
    # but its share is 50 s; the time it leaves is shared by the others.
    calls = _schedule(monkeypatch, reference_secs=20.0)
    late = [(name, share) for name, share, _ in calls if name in LATE_ORDER]
    assert [name for name, _ in late] == ["TextLinearPlain", "TextLinearWide"]
    assert late[0][1] == pytest.approx(100 * 0.25 / 0.5, rel=0.01)
    assert late[1][1] == pytest.approx(100, rel=0.01)


def test_late_families_take_no_trials_from_the_others_and_stop_at_max_models(monkeypatch):
    base = [(n, trials) for n, _, trials in _schedule(monkeypatch, 0.1, 10, late=())]
    calls = _schedule(monkeypatch, reference_secs=0.1, max_models=10)
    assert [(n, trials) for n, _, trials in calls if n in FAMILY_ORDER] == base
    # The base families finished 8 trials of the 10: two late families ran, one trial each.
    assert [n for n, _, _ in calls[len(FAMILY_ORDER) :]] == ["TextLinearChar", "TextLinearPlain"]


def test_without_prose_the_time_shares_are_what_they_are_without_late_families(monkeypatch):
    X = pd.DataFrame({"a": np.arange(40.0), "b": np.arange(40.0)[::-1]})
    y = np.arange(40) % 2
    assert AutoML(TrainConfig(target="y"))._late_families(Prep().fit(X), X, y, "regression") == []
    calls = _schedule(monkeypatch, reference_secs=0.1, late=())
    weights = automl_module.FAMILY_WEIGHTS
    for i, (name, share, _) in enumerate(calls):
        # No time was used, so all 100 s are left for the next one, which takes its weight.
        assert name == FAMILY_ORDER[i]
        assert share == pytest.approx(
            100 * weights[name] / sum(weights[f] for f in FAMILY_ORDER[i:]), rel=0.01
        )


def test_without_prose_the_search_gets_exactly_the_base_families(monkeypatch):
    rng = np.random.default_rng(1)
    df = pd.DataFrame(rng.normal(size=(120, 3)), columns=list("abc"))
    df["y"] = (df["a"] > 0).astype(int)
    seen = []
    real = AutoML._search

    def spy(self, families, *args):
        seen.append(list(families))
        return real(self, families, *args)

    monkeypatch.setattr(AutoML, "_search", spy)
    _fit(df, target="y", max_models=len(FAMILY_ORDER), max_runtime_secs=30)
    assert seen == [[f for f in FAMILY_ORDER if f != "TextLinear"]]  # nothing late, no TextLinear


def test_without_prose_a_fit_has_the_base_families_and_no_late_one():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(300, 4)), columns=list("abcd"))
    df["y"] = (df["a"] + df["b"] > 0).astype(int)
    model = _fit(df, None, target="y", max_models=len(FAMILY_ORDER), seed=3)
    base = set(FAMILY_ORDER) - {"TextLinear"}  # TextLinear needs prose too
    assert set(model.trials["family"]) == base
    assert set(model.leaderboard["family"]) == base | {"Ensemble"}


# --- which late families apply -------------------------------------------------------------


def _prose():
    df = _posts()
    X = df.drop(columns=["topic"])
    return AutoML(TrainConfig(target="topic")), Prep().fit(X, [TextShape("post")]), X, _codes(df)


def test_prose_makes_every_late_family_apply():
    runner, prep, X, y = _prose()
    assert runner._late_families(prep, X, y, "classification") == list(LATE_ORDER)
    assert AutoML(TrainConfig(target="t"), families=["TextLinearWide"]).late == ["TextLinearWide"]
    assert AutoML(TrainConfig(target="t"), families=["LightGBM"]).late == []


def test_the_plain_variant_needs_derived_features_to_differ_from_textlinear():
    df = _posts()
    X = df.drop(columns=["topic"])
    runner = AutoML(TrainConfig(target="topic"))
    late = runner._late_families(Prep().fit(X), X, _codes(df), "classification")
    assert late == ["TextLinearChar", "TextLinearWide"]


def _long_texts(n, tail_words, seed=0):
    """Texts whose first 1,000 rows are short (six words) and the others ``tail_words`` long."""
    words = ["alpha", "beta", "gamma", "delta"]
    texts = [" ".join(words + words[:2])] * 1000 + [" ".join(words * (tail_words // 4))] * (
        n - 1000
    )
    df = pd.DataFrame({"post": texts, "x": np.random.default_rng(seed).normal(size=n)})
    return df, (np.arange(n) % 3).astype(np.int64)


def test_the_character_variant_sizes_the_text_on_a_random_sample_of_the_rows():
    df, y = _long_texts(5000, 400)  # about 2,400 characters in 4 of every 5 rows: ~10M
    prep = Prep().fit(df, [TextShape("post")])
    late = AutoML(TrainConfig(target="t"))._late_families(prep, df, y, "classification")
    assert "TextLinearChar" not in late and "TextLinearWide" in late
    small, y = _long_texts(5000, 8)  # the same rows with short texts
    prep = Prep().fit(small, [TextShape("post")])
    late = AutoML(TrainConfig(target="t"))._late_families(prep, small, y, "classification")
    assert "TextLinearChar" in late


def test_the_character_variant_is_not_tried_on_text_without_spaces():
    # Letter runs split by digits are prose; with no spaces the n-grams of a text are far too many.
    rng = np.random.default_rng(0)
    parts = [f"{w}{i}" for w in ["alpha", "beta", "gamma", "delta"] for i in range(8)]
    df = pd.DataFrame({"post": ["".join(rng.permutation(parts)) for _ in range(200)]})
    df["x"] = rng.normal(size=200)
    prep = Prep().fit(df)
    assert prep.prose == ("post",)
    y = np.arange(200) % 2
    late = AutoML(TrainConfig(target="t"))._late_families(prep, df, y, "classification")
    assert "TextLinearChar" not in late and "TextLinearWide" in late


def test_late_families_need_the_reference_result_unless_the_list_is_explicit(monkeypatch):
    calls = []

    def fake(name, X, y, folds, task, prep, deadline, *args, **kwargs):
        calls.append(name)
        if name == "TextLinear":
            raise automl_module.NoModelError("no time")
        row = {
            "family": name,
            "trial": 0,
            "state": "complete",
            "score": 0.5,
            "elapsed": 0.1,
            "params": {},
        }
        return search.FamilyResult(
            np.zeros((1, 2)),
            [object()],
            {},
            1,
            0.5,
            0.0,
            FAMILIES[name],
            "no_improvement",
            log=[row],
        )

    monkeypatch.setattr(automl_module, "run_family", fake)
    names = ["TextLinear", *LATE_ORDER]
    for families, expected in ((None, ["TextLinear"]), (names, names)):
        calls.clear()
        runner = AutoML(TrainConfig(target="y"), families=families)
        runner._search(
            names, None, None, None, "classification", None, search.Deadline(100), None, None
        )
        assert calls == expected  # no estimate of the time a variant needs: only if asked for


def test_late_families_are_left_out_when_the_text_or_its_model_would_be_too_big(monkeypatch):
    runner, prep, X, y = _prose()
    monkeypatch.setattr("fione.engine.families.TEXT_CHAR_BUDGET", 100)
    late = runner._late_families(prep, X, y, "classification")
    assert late == ["TextLinearPlain", "TextLinearWide"]
    monkeypatch.setattr(automl_module, "SIZE_CAP", 1)
    assert runner._late_families(prep, X, y, "classification") == []
    monkeypatch.setattr(automl_module, "SIZE_CAP", 40 * 1024**2)
    monkeypatch.setattr(automl_module, "LINEAR_MAX_CELLS", 10)  # the view is too wide
    assert runner._late_families(prep, X, y, "classification") == []


# --- a real run ----------------------------------------------------------------------------


def test_late_variants_run_in_the_time_left_and_the_ensemble_may_ignore_them():
    df = _posts(400)
    X = df.drop(columns=["topic"])
    model = _fit(
        df,
        ["TextLinear", *LATE_ORDER],
        target="topic",
        max_runtime_secs=120,  # the variants run in the time the base search leaves
        feature_engineering=False,
    )
    board = model.leaderboard
    ran = {"TextLinear", "TextLinearChar", "TextLinearWide", "Ensemble"}  # no derived features
    assert set(board["family"]) == ran
    members = board[board["family"] != "Ensemble"]
    # A variant that adds nothing has weight 0 (it is then not a member of the model).
    assert members["weight"].sum() == pytest.approx(1.0) and (members["weight"] >= 0).all()
    assert set(model.trials["family"]) == ran - {"Ensemble"}
    assert (model.predict(X).to_numpy() == df["topic"].to_numpy()).mean() > 0.9
    restored = pickle.loads(pickle.dumps(model))
    pd.testing.assert_frame_equal(restored.predict_proba(X), model.predict_proba(X))


@pytest.mark.parametrize("name", LATE_ORDER)
def test_a_late_family_with_weight_zero_is_not_a_member(name):
    df = _posts(300)
    X = df.drop(columns=["topic"])
    y = _codes(df)
    prep = Prep().fit(X, [TextShape("post")])
    folds = search.make_folds(y, "classification", 3, 0)
    results = {
        n: search.run_family(
            n,
            X,
            y,
            folds,
            "classification",
            prep,
            search.Deadline(30),
            lambda e: None,
            lambda: False,
            max_trials=1,
        )
        for n in ("TextLinear", name)
    }
    weights = caruana({n: r.oof for n, r in results.items()}, y, "classification")
    assert set(weights) == {"TextLinear", name} and sum(weights.values()) == pytest.approx(1.0)
    clock = search.Clock(search.Deadline(30), lambda: False)
    runner = AutoML(TrainConfig(target="topic"))
    # Whatever the ensemble decided, the members are exactly the candidates with weight above 0.
    members, _ = runner._members(results, weights, X, y, prep, clock, None, "no_improvement")
    assert sorted(m.key for m in members) == sorted(n for n, w in weights.items() if w > 0)
    # A late variant with weight 0 is dropped without any special code.
    zero = {"TextLinear": 1.0, name: 0.0}
    members, _ = runner._members(results, zero, X, y, prep, clock, None, "no_improvement")
    assert [member.key for member in members] == ["TextLinear"]


# --- the variants themselves ---------------------------------------------------------------


def _variant_data():
    df = _posts(240, seed=5)
    X = df.drop(columns=["topic"])
    return df, X, _codes(df), Prep().fit(X, [TextShape("post")])


def _trained(prep, spec, model, df):
    return TrainedModel(
        task="classification",
        target="topic",
        classes_=CLASSES,
        columns=prep.columns,
        leaderboard=None,
        trials=None,
        feature_importance=None,
        stop_reason="no_improvement",
        config=TrainConfig(target="topic"),
        metrics={},
        prep=prep,
        members=[Member(spec, 1.0, [model], spec.name)],
    )


@pytest.mark.parametrize("name", LATE_ORDER)
def test_a_variant_fits_predicts_pickles_and_explains(name):
    df, X, y, prep = _variant_data()
    spec = FAMILIES[name]("classification", 3)
    assert isinstance(spec, TextLinear) and spec.name == name
    view = getattr(prep, spec.view)(X)
    train, valid = slice(0, 180), slice(180, None)
    deadline = search.Deadline(60)
    model = spec.fit(spec.defaults, view.iloc[train], y[train], None, None, deadline)
    spec.fit({"C": 3.0}, view.iloc[train], y[train], None, None, deadline)
    assert len(spec._words) == 1  # the words are read once per training set
    proba = spec.predict(model, view.iloc[valid])
    assert proba.shape == (60, 3) and np.allclose(proba.sum(axis=1), 1)
    assert (proba.argmax(axis=1) == y[valid]).mean() > 0.9
    assert spec.size_bytes(model) > 0 and spec.rounds(model) == 1
    assert pickle.loads(pickle.dumps(spec))._words == {}  # the cache stays out of the model file
    restored = pickle.loads(pickle.dumps(model))
    np.testing.assert_array_equal(spec.predict(restored, view.iloc[valid]), proba)

    trained = _trained(prep, spec, model, df)
    c = explain.contributions(trained, X.iloc[valid])
    np.testing.assert_allclose(c.prediction, spec.predict(model, view.iloc[valid]), atol=1e-6)
    assert c.values.shape == (60, 3, len(prep.columns))
    importance = feature_importance(trained.members, prep)
    assert importance.sum() == pytest.approx(1.0) and len(importance) == len(prep.columns)
    assert explain.cap_threads(trained, 2) is trained


def test_the_variants_read_what_their_names_say():
    df, X, y, prep = _variant_data()
    fitted = {}
    for name in ("TextLinear", *LATE_ORDER):
        spec = FAMILIES[name]("classification", 3)
        fitted[name] = spec.fit(
            spec.defaults, getattr(prep, spec.view)(X), y, None, None, search.Deadline(60)
        )
    base = fitted["TextLinear"]
    assert base.texts == ["f0_t"] and [v.analyzer for v in base.vectorizers] == ["word"]
    wide = fitted["TextLinearWide"].vectorizers[0]
    assert wide.max_features == 100_000 and base.vectorizers[0].max_features == 30_000
    char = fitted["TextLinearChar"]  # words and characters of the one text column
    assert char.texts == ["f0_t", "f0_t"]
    assert [v.analyzer for v in char.vectorizers] == ["word", "char_wb"]
    assert char.vectorizers[1].ngram_range == (2, 5) and char.blocks()[1:] == [
        len(v.vocabulary_) for v in char.vectorizers
    ]
    plain = fitted["TextLinearPlain"]
    derived = len(prep.feature_names) - len(prep.groups[0].names)
    assert max(int(c[1:].split("_")[0]) for c in plain.dense) < derived
    assert max(int(c[1:].split("_")[0]) for c in base.dense) >= derived
    assert plain.texts == base.texts and plain.vectorizers[0].max_features == 30_000


# --- a family that gets no model for lack of time says so ------------------------------------


def _notices(monkeypatch, refused, families):
    """The ``notice`` messages of a search where ``run_family`` raises ``NoModelError`` (needing
    40 s) for the families in ``refused`` and returns a model for the others."""
    seen = []

    def fake(name, X, y, folds, task, prep, deadline, *args, **kwargs):
        if name in refused:
            raise automl_module.NoModelError("no time", 40.0)
        row = {"family": name, "trial": 0, "state": "complete", "score": 0.5, "elapsed": 0.1}
        row["params"] = {}
        return search.FamilyResult(
            np.zeros((1, 2)),
            [object()],
            {},
            1,
            0.5,
            0.0,
            FAMILIES[name],
            "no_improvement",
            log=[row],
        )

    monkeypatch.setattr(automl_module, "run_family", fake)
    runner = AutoML(TrainConfig(target="y"), emit=seen.append)
    runner._search(
        families, None, None, None, "classification", None, search.Deadline(100), None, None
    )
    return [e.data for e in seen if e.type == "notice"]


def test_a_base_family_without_a_model_for_lack_of_time_is_reported(monkeypatch):
    notices = _notices(monkeypatch, {"TextLinear"}, list(FAMILY_ORDER))
    assert [n["family"] for n in notices] == ["TextLinear"]
    message = notices[0]["message"]
    # Its first trial could have half of the 100 s (more than its share, about 24 s).
    assert "estimated to need about 40 s but the search time it could have was 50 s" in message


def test_a_first_trial_may_take_half_of_the_time_left_but_a_late_family_gets_its_share(
    monkeypatch,
):
    firsts = {}

    def fake(name, X, y, folds, task, prep, deadline, *args, first_deadline=None, **kwargs):
        firsts[name] = (
            deadline.remaining(),
            None if first_deadline is None else first_deadline.remaining(),
        )
        row = {"family": name, "trial": 0, "state": "complete", "score": 0.5, "elapsed": 0.1}
        row["params"] = {}
        return search.FamilyResult(
            np.zeros((1, 2)),
            [object()],
            {},
            1,
            0.5,
            0.0,
            FAMILIES[name],
            "no_improvement",
            log=[row],
        )

    monkeypatch.setattr(automl_module, "run_family", fake)
    runner = AutoML(TrainConfig(target="y"))
    runner._search(
        [*FAMILY_ORDER, *LATE_ORDER], None, None, None, "classification", None,
        search.Deadline(100), None, None,
    )  # fmt: skip
    # No time passes, so the base families have 85 s each time: half of it, 42.5 s, is more than
    # any share (LightGBM's is 0.176 x 85 s).
    share, first = firsts["LightGBM"]
    assert share == pytest.approx(0.176 * 85, rel=0.02) and first == pytest.approx(42.5, rel=0.02)
    # Linear is last: its share is all that is left (85 s), more than half of it.
    assert firsts["Linear"][0] == pytest.approx(85, rel=0.02)
    assert firsts["Linear"][1] == pytest.approx(85, rel=0.02)
    assert all(firsts[name][1] is None for name in LATE_ORDER)


def test_late_families_that_do_not_run_for_lack_of_time_are_reported_together(monkeypatch):
    notices = _notices(monkeypatch, set(LATE_ORDER), [*FAMILY_ORDER, *LATE_ORDER])
    assert len(notices) == 1
    assert all(name in notices[0]["message"] for name in LATE_ORDER)
    assert _notices(monkeypatch, set(), [*FAMILY_ORDER, *LATE_ORDER]) == []


def test_late_families_without_the_reference_result_are_not_blamed_on_time(monkeypatch):
    # TextLinear has no model (and says why); the variants have no estimate to be judged by.
    notices = _notices(monkeypatch, {"TextLinear"}, [*FAMILY_ORDER, *LATE_ORDER])
    assert [n["family"] for n in notices] == ["TextLinear"]
