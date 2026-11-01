import numpy as np
import pandas as pd
import pytest

from fione.engine import features
from fione.engine.automl import AutoML
from fione.engine.config import Deadline, TrainConfig
from fione.engine.features import (
    CategoryFrequency,
    CategoryPairs,
    ClusterDistances,
    DateDifferences,
    DateParts,
    GroupMeans,
    NumberPairs,
    RowCounts,
    TextShape,
    TextTokens,
    ValueFrequency,
    paired,
    passes,
    select_groups,
)
from fione.engine.model import attribution, feature_importance
from fione.engine.prep import Prep

TITLES = ["Mr", "Mrs", "Miss", "Master", "Rev"]


def people(n=600, seed=0):
    """Names whose title decides the label; the other columns are noise."""
    rng = np.random.default_rng(seed)
    title = rng.choice(TITLES, n, p=[0.4, 0.2, 0.2, 0.15, 0.05])
    surname = rng.choice([f"Name{i}" for i in range(80)], n)
    X = pd.DataFrame(
        {
            "name": [
                f"{s}, {t}. Person{i}" for i, (s, t) in enumerate(zip(surname, title, strict=True))
            ],
            "noise": rng.normal(size=n),
            "group": rng.choice(["a", "b", "c"], n),
        }
    )
    y = np.isin(title, ["Mrs", "Miss", "Master"]).astype(int)
    flip = rng.random(n) < 0.05
    return X, np.where(flip, 1 - y, y)


def noise_text(n=600, seed=1):
    """Free text from a vocabulary that has nothing to do with the label."""
    rng = np.random.default_rng(seed)
    words = [f"w{i}" for i in range(30)]
    X = pd.DataFrame(
        {
            "text": [" ".join(rng.choice(words, rng.integers(1, 6))) for _ in range(n)],
            "x": rng.normal(size=n),
        }
    )
    return X, rng.integers(0, 2, n)


def test_text_tokens_flags_common_letter_runs_and_keeps_missing():
    X, _ = people()
    X.loc[0, "name"] = None
    group = TextTokens("name").fit(X)
    assert {"name__has_mr", "name__has_mrs", "name__has_miss", "name__has_master"} <= set(
        group.names
    )
    out = group.transform(X)
    assert out["name__has_mr"].isna().tolist() == [True] + [False] * (len(X) - 1)
    mrs = X["name"].str.contains(", Mrs.", regex=False)
    assert (out["name__has_mrs"][1:] == mrs[1:].astype(float)).all()
    assert all(group.sources[i] == ("name",) for i in range(len(group.names)))


def test_text_tokens_splits_letters_from_digits():
    X = pd.DataFrame({"cabin": ["C85", "C23 C25", "B5", "B57", "C1", "B9", "E1", "E2"] * 4})
    group = TextTokens("cabin").fit(X)
    assert {"cabin__has_c", "cabin__has_b"} <= set(group.names)


def test_text_shape_measures_length_words_digits_and_the_first_number():
    X = pd.DataFrame({"t": ["PC 17599", "A/5 21171", None, "ab", "ab cd", "x1", "y22", "z"]})
    group = TextShape("t").fit(X)
    out = group.transform(X)
    assert out["t__length"].tolist()[:2] == [8.0, 9.0]
    assert out["t__words"].iloc[0] == 2
    assert out["t__number"].iloc[:2].tolist() == [17599.0, 5.0]
    assert out["t__digit_share"].iloc[0] == pytest.approx(5 / 8)
    assert out["t__length"].isna().iloc[2]


def test_constant_outputs_are_dropped():
    X = pd.DataFrame({"t": ["abcdef", "ghijkl"] * 5})
    names = TextShape("t").fit(X).names
    assert "t__length" not in names and "t__words" not in names


def test_category_frequency_unseen_is_zero_and_missing_stays_missing():
    X = pd.DataFrame({"c": ["a"] * 6 + ["b"] * 3 + [None]})
    group = CategoryFrequency(["c"]).fit(X)
    out = group.transform(pd.DataFrame({"c": ["a", "b", "zzz", None]}))["c__frequency"]
    assert out.iloc[:3].tolist() == pytest.approx([6 / 9, 3 / 9, 0.0])  # of the non-missing rows
    assert np.isnan(out.iloc[3])


def test_row_counts_count_missing_and_zero_values():
    X = pd.DataFrame({"a": [0, 1, None, 0], "b": [None, None, 5, 0], "c": ["x", None, "y", "z"]})
    out = RowCounts(["a", "b", "c"], ["a", "b"]).fit(X).transform(X)
    assert out["missing_count"].tolist() == [1, 2, 1, 0]
    assert out["zero_count"].tolist() == [1, 0, 0, 2]


def test_date_parts_and_differences():
    X = pd.DataFrame(
        {
            "a": pd.to_datetime(["2024-01-06 13:30", "2024-03-02 01:00", "2024-07-01 23:59"]),
            "b": pd.to_datetime(["2024-01-05 13:30", "2024-03-01 01:00", "2024-06-01 23:59"]),
        }
    )
    parts = DateParts(["a"]).fit(X)
    out = parts.transform(X)
    assert out["a__hour"].tolist() == [13, 1, 23]
    assert out["a__is_weekend"].tolist() == [1.0, 1.0, 0.0]
    diff = DateDifferences(["a", "b"]).fit(X).transform(X)
    assert diff["a - b"].tolist() == [86400.0, 86400.0, 30 * 86400.0]
    assert DateDifferences(["a", "b"]).fit(X).sources == [("a", "b")]


def test_number_pairs_cover_each_operation_and_guard_division():
    X = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [0.0, 2.0, 5.0, 8.0]})
    assert NumberPairs("sum", ["a", "b"]).fit(X).transform(X)["a + b"].tolist() == [1, 4, 8, 12]
    assert NumberPairs("product", ["a", "b"]).fit(X).transform(X)["a * b"].tolist() == [
        0,
        4,
        15,
        32,
    ]
    ratio = NumberPairs("ratio", ["a", "b"]).fit(X)
    assert set(ratio.names) == {"a / b", "b / a"}
    assert np.isnan(ratio.transform(X)["a / b"].iloc[0])
    assert ratio.transform(X)["b / a"].tolist() == [0, 1, 5 / 3, 2]


def test_group_means_need_enough_rows_per_level():
    X = pd.DataFrame({"c": ["a"] * 6 + ["b"] * 2, "n": [1.0, 2, 3, 4, 5, 6, 10, 20]})
    group = GroupMeans(["c"], ["n"]).fit(X)
    out = group.transform(X)
    assert out["n mean by c"].iloc[0] == pytest.approx(3.5)
    assert np.isnan(out["n mean by c"].iloc[-1])  # two rows: not enough
    assert out["n minus mean by c"].iloc[0] == pytest.approx(-2.5)


def test_category_pairs_share_of_the_combination():
    X = pd.DataFrame({"a": ["x", "x", "y", "y"], "b": ["p", "p", "p", "q"]})
    out = CategoryPairs(["a", "b"]).fit(X).transform(X)["a x b frequency"]
    assert out.tolist() == [0.5, 0.5, 0.25, 0.25]


def test_prep_adds_groups_after_the_plain_features_and_names_their_sources():
    X, _ = people()
    plain = Prep().fit(X)
    prep = Prep().fit(X, [TextTokens("name")])
    assert prep.feature_names[: len(plain.feature_names)] == plain.feature_names
    extra = prep.feature_names[len(plain.feature_names) :]
    assert extra and all(name.startswith("name__has_") for name in extra)
    assert prep.sources[len(plain.feature_names) :] == [("name",)] * len(extra)
    for view in (prep.tree(X), prep.dense(X), prep.catboost(X)):
        assert view.shape == (len(X), len(prep.feature_names))
    assert prep.linear(X).shape[0] == len(X)
    assert prep.columns == plain.columns  # derived features need no extra input columns


def test_prep_skips_groups_on_columns_it_does_not_use():
    X, _ = people()
    X["const"] = 1
    prep = Prep().fit(X, [TextTokens("const"), TextTokens("name")])
    assert [g.columns for g in prep.groups] == [("name",)]


def test_groups_are_fitted_on_a_copy():
    X, _ = people()
    group = TextTokens("name")
    Prep().fit(X, [group])
    assert not hasattr(group, "_tokens")


def test_attribution_splits_a_feature_over_its_sources_and_sums_to_one():
    X = pd.DataFrame({"a": np.arange(30.0), "b": np.arange(30.0)[::-1] ** 2, "c": list("xy") * 15})
    prep = Prep().fit(X, [NumberPairs("sum", ["a", "b"])])
    matrix = attribution(prep)
    assert matrix.shape == (3, len(prep.feature_names))
    assert np.allclose(matrix.sum(axis=0), 1.0)
    pair = prep.feature_names.index("a + b")
    assert matrix[:, pair].tolist() == [0.5, 0.5, 0.0]


def test_attribution_reads_models_whose_sources_are_plain_names():
    X = pd.DataFrame({"a": np.arange(30.0), "b": np.arange(30.0)[::-1] ** 2})
    prep = Prep().fit(X)
    prep.sources = ["a", "b"]  # what models of older versions hold
    assert attribution(prep).tolist() == [[1.0, 0.0], [0.0, 1.0]]


def test_a_prep_pickled_by_an_older_version_still_transforms():
    import pickle

    rng = np.random.default_rng(0)
    X = pd.DataFrame({"a": rng.normal(size=60), "c": rng.choice(list("xy"), 60)})
    prep = Prep().fit(X)
    for name in ("groups", "_logged"):  # attributes that older versions never set
        prep.__dict__.pop(name, None)
    prep.sources = [s[0] for s in prep.sources]  # older versions held plain names
    old = pickle.loads(pickle.dumps(prep))  # noqa: S301 - a frame this test built
    assert old.tree(X).shape == (60, 2) and old.linear(X).shape[0] == 60
    assert attribution(old).tolist() == [[1.0, 0.0], [0.0, 1.0]]


def test_linear_view_log_transforms_skewed_non_negative_numbers_only():
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"skew": rng.exponential(1.0, 500) ** 4, "even": rng.normal(size=500)})
    prep = Prep().fit(X)
    view = prep.linear(X)
    assert prep._logged == ("f0",)
    assert abs(view["f0"].mean()) < 1e-9 and abs(view["f0"].skew()) < 2
    assert view["f1"].corr(X["even"]) > 0.999


def test_value_frequency_counts_repeated_numbers_and_treats_unseen_as_a_single_row():
    X = pd.DataFrame({"fare": [7.25] * 6 + [10.0] * 3 + [None]})
    group = ValueFrequency(["fare"]).fit(X)
    out = group.transform(pd.DataFrame({"fare": [7.25, 10.0, 99.0, None]}))["fare__value_frequency"]
    assert out.iloc[:3].tolist() == pytest.approx([6 / 9, 3 / 9, 1 / 9])  # unseen = single row
    assert np.isnan(out.iloc[3])


def test_cluster_distances_assign_a_cluster_and_a_distance_to_every_row():
    rng = np.random.default_rng(0)
    near = rng.normal(0, 0.1, (150, 2))
    far = rng.normal(10, 0.1, (150, 2))
    X = pd.DataFrame(np.vstack([near, far]), columns=["a", "b"])
    X.loc[0, "a"] = None
    group = ClusterDistances(["a", "b"]).fit(X)
    out = group.transform(X)
    assert out.shape == (300, 2) and not out.isna().any().any()
    assert out["cluster"].iloc[1] != out["cluster"].iloc[-1]
    assert out["cluster_distance"].max() < 3  # every row is close to a centre
    assert group.sources == [("a", "b")] * 2


def test_candidates_offer_value_frequency_only_for_repeating_numbers():
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"repeats": rng.choice(np.arange(20.0), 300), "unique": rng.normal(size=300)})
    labels = [g.label for g in features.candidates(Prep().fit(X), X, ["unique", "repeats"])]
    assert "frequencies of repeated numbers" in labels
    assert "clusters of numbers" in labels
    only_unique = X[["unique"]]
    labels = [g.label for g in features.candidates(Prep().fit(only_unique), only_unique, [])]
    assert "frequencies of repeated numbers" not in labels and "clusters of numbers" not in labels


def test_paired_and_passes_demand_a_clear_consistent_gain():
    before = np.full(10, 0.5)
    assert passes(before, before - np.linspace(0.02, 0.03, 10))
    assert not passes(before, before)  # no gain
    noisy = before - np.array([0.1, -0.09, 0.1, -0.09, 0.1, -0.09, 0.1, -0.09, 0.1, -0.08])
    assert not passes(before, noisy)  # a mean gain the folds do not agree on
    assert not passes(before, before - 1e-5)  # too small a share of the loss
    gain, error, share = paired(before, before - 0.01)
    assert gain == pytest.approx(0.01) and share == 1.0 and error == pytest.approx(0.0)


def test_the_gate_adopts_a_group_that_explains_the_label():
    X, y = people()
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    adopted = {v.group for v in verdicts if v.adopted}
    assert "text tokens of name" in adopted
    assert [g.label for g in kept] == [v.group for v in verdicts if v.adopted]
    assert all(v.reason == "adopted" for v in verdicts if v.adopted)


def test_the_gate_adopts_nothing_for_noise():
    X, y = noise_text()
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert kept == []
    assert not any(v.adopted for v in verdicts)
    assert verdicts  # the candidates were judged


def test_the_gate_does_not_reward_columns_that_carry_nothing():
    """The label is learnable (a product of two numbers) but only from those two columns, so a
    group must not win merely by adding columns that a column-sampling model could draw."""
    rng = np.random.default_rng(0)
    n = 600
    X = pd.DataFrame(
        {
            "a": rng.normal(size=n),
            "b": rng.normal(size=n),
            "c": rng.choice(list("wxyz"), n),
            "t": [f"x{k} y" for k in rng.integers(0, 40, n)],
        }
    )
    y = (X["a"] * X["b"] > 0).astype(int).to_numpy()
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    adopted = {v.group for v in verdicts if v.adopted}
    assert not adopted & {
        "text shape of t",
        "text tokens of t",
        "means of numbers within categories",
    }
    assert "product of numbers" in adopted or not adopted  # the real structure may be found


def test_the_sample_keeps_every_class_and_never_fails(monkeypatch):
    monkeypatch.setattr(features, "GATE_ROWS", 300)
    rng = np.random.default_rng(0)
    for n, classes in ((301, 2), (305, 10), (2000, 3)):
        y = np.arange(n) % classes
        rows = features._sample(y, "classification", 0)
        assert set(y[rows]) == set(range(classes)) and len(rows) >= 300
        assert (np.diff(rows) > 0).all()
    X = pd.DataFrame({"a": rng.normal(size=301), "b": rng.normal(size=301)})
    kept, verdicts = select_groups(X, np.arange(301) % 2, "classification", 5, 0, Deadline(60))
    assert verdicts
    assert len(features._sample(np.zeros(1000), "regression", 0)) == 300


def test_the_gate_works_for_regression_too():
    X, y = people()
    kept, verdicts = select_groups(X, y.astype(float), "regression", 5, 0, Deadline(120))
    assert "text tokens of name" in {g.label for g in kept}


def test_the_gate_stops_at_the_deadline_and_on_cancellation():
    X, y = people()
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(0))
    assert (
        kept == [] and verdicts and {v.reason for v in verdicts} <= {"time", "no varying feature"}
    )
    kept, verdicts = select_groups(
        X, y, "classification", 5, 0, Deadline(120), should_stop=lambda: True
    )
    assert kept == []


def test_the_final_check_drops_everything_when_the_kept_groups_do_not_hold_up(monkeypatch):
    X, y = people()
    real = features.passes
    calls = []

    def fail_the_last(before, after, z=features.GATE_Z):
        calls.append(len(before))
        return False if len(before) == 2 * features.GATE_FOLDS else real(before, after, z)

    monkeypatch.setattr(features, "passes", fail_the_last)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert kept == []
    assert any(v.reason == "final check" for v in verdicts)


def test_the_gate_samples_large_data_without_changing_the_columns(monkeypatch):
    monkeypatch.setattr(features, "GATE_ROWS", 300)
    X, y = people(900)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert "text tokens of name" in {g.label for g in kept}


def test_automl_records_the_groups_it_tried_and_uses_the_adopted_ones():
    X, y = people()
    df = X.assign(label=np.where(y == 1, "yes", "no"))
    config = TrainConfig(target="label", max_runtime_secs=60, max_models=4)
    events = []
    model = AutoML(config, emit=events.append, families=["LightGBM"]).fit(df)
    tried = {row["group"]: row for row in model.features}
    assert tried["text tokens of name"]["adopted"]
    assert any(name.startswith("name__has_") for name in model.prep.feature_names)
    notice = [e for e in events if e.type == "notice" and e.data.get("kind") == "features"]
    assert len(notice) == 1 and notice[0].data["groups"] == model.features
    assert model.predict(df).tolist() == df["label"].tolist() or model.metrics["accuracy"] > 0.9
    importance = model.feature_importance
    assert importance["name"] > 0.5 and abs(importance.sum() - 1) < 1e-9
    assert feature_importance(model.members, model.prep).equals(importance)


def test_automl_without_feature_engineering_adds_nothing():
    X, y = people()
    df = X.assign(label=np.where(y == 1, "yes", "no"))
    config = TrainConfig(
        target="label", max_runtime_secs=60, max_models=4, feature_engineering=False
    )
    model = AutoML(config, families=["LightGBM"]).fit(df)
    assert model.features is None
    assert model.prep.groups == ()


def test_automl_trains_on_when_the_gate_fails(monkeypatch):
    X, y = people()
    df = X.assign(label=np.where(y == 1, "yes", "no"))

    def boom(*args, **kwargs):
        raise RuntimeError("gate broke")

    monkeypatch.setattr("fione.engine.automl.select_groups", boom)
    events = []
    config = TrainConfig(target="label", max_runtime_secs=60, max_models=4)
    model = AutoML(config, emit=events.append, families=["LightGBM"]).fit(df)
    assert model.prep.groups == () and model.features is None
    assert any(e.data.get("kind") == "features_error" for e in events if e.type == "notice")


def test_feature_engineering_must_be_a_flag():
    from fione.engine.config import ConfigError

    assert TrainConfig(target="t").feature_engineering is True
    with pytest.raises(ConfigError, match="feature_engineering"):
        TrainConfig(target="t", feature_engineering="yes").validate()


def test_groups_whose_last_check_is_cut_short_by_the_deadline_are_not_kept(monkeypatch):
    X, y = people()
    real = features._Gate.losses

    def cut_the_final_check(self, groups, repeats):
        if min(repeats) >= features.GATE_REPEATS:  # the folds only the final check uses
            raise features._OutOfTime
        return real(self, groups, repeats)

    monkeypatch.setattr(features._Gate, "losses", cut_the_final_check)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert kept == [] and not any(v.adopted for v in verdicts)
    assert "time" in {v.reason for v in verdicts}


def test_the_deadline_is_polled_inside_the_comparisons():
    X, y = people()
    polls = []

    def stop():
        polls.append(1)
        return len(polls) > 12  # a few folds into the first candidate

    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120), should_stop=stop)
    assert kept == [] and len(polls) <= 14
    assert {v.reason for v in verdicts} == {"time"}


def test_every_seed_gives_valid_folds(monkeypatch):
    monkeypatch.setattr(features, "GATE_ROWS", 150)  # so that the sampling path runs too
    X, y = people(200)
    kept, verdicts = select_groups(X, y, "classification", 5, 2**32 - 1, Deadline(120))
    assert verdicts


def test_a_model_with_adopted_groups_survives_the_signed_artifact_round_trip(tmp_path):
    from fione.engine.artifact import load_model, save_model
    from fione.engine.explain import contributions
    from fione.storage import LocalStorage

    X, y = people()
    df = X.assign(label=np.where(y == 1, "yes", "no"))
    config = TrainConfig(target="label", max_runtime_secs=60, max_models=4)
    model = AutoML(config, families=["LightGBM"]).fit(df)
    assert model.prep.groups
    storage, secret = LocalStorage(tmp_path / "store"), bytes(range(32))
    save_model(model, storage, "models/1/", secret, image_tag="test")
    loaded = load_model(storage, "models/1/", secret)
    assert loaded.prep.feature_names == model.prep.feature_names
    assert loaded.predict_proba(df).equals(model.predict_proba(df))
    again, before = contributions(loaded, df.head(20)), contributions(model, df.head(20))
    assert np.array_equal(again.values, before.values)
    assert loaded.features == model.features


def test_every_kind_of_group_pickles_and_transforms_alike():
    import pickle

    rng = np.random.default_rng(0)
    n = 120
    X = pd.DataFrame(
        {
            "a": rng.normal(size=n),
            "b": rng.integers(0, 20, n).astype(float),
            "c": rng.choice(list("xyz"), n),
            "d": rng.choice(list("pq"), n),
            "t": [
                f"{['red', 'green', 'blue'][i % 3]} {['apple', 'pear'][i % 2]} {i}"
                for i in range(n)
            ],
            "when": pd.date_range("2024-01-01", periods=n, freq="7h"),
            "then": pd.date_range("2023-06-01", periods=n, freq="5h"),
        }
    )
    groups = [
        TextShape("t"),
        TextTokens("t"),
        CategoryFrequency(["c", "d"]),
        RowCounts(list(X.columns), ["a", "b"]),
        DateParts(["when", "then"]),
        DateDifferences(["when", "then"]),
        NumberPairs("ratio", ["a", "b"]),
        GroupMeans(["c"], ["a", "b"]),
        CategoryPairs(["c", "d"]),
        ValueFrequency(["b"]),
        ClusterDistances(["a", "b"]),
    ]
    prep = Prep().fit(X, groups)
    assert {type(g) for g in prep.groups} == {type(g) for g in groups}
    clone = pickle.loads(pickle.dumps(prep))  # noqa: S301 - a frame this test built
    for view in ("tree", "dense", "catboost", "linear"):
        pd.testing.assert_frame_equal(getattr(prep, view)(X), getattr(clone, view)(X))
    for view in ("tree", "dense", "catboost", "linear"):
        assert len(getattr(prep, view)(X.head(0))) == 0
    one_row = X.head(1)
    assert np.array_equal(prep.dense(one_row), prep.dense(X).head(1))  # no batch dependence


def test_text_groups_are_offered_for_structured_strings_only():
    rng = np.random.default_rng(0)
    n = 300
    X = pd.DataFrame(
        {
            "name": [f"Smith{i % 40}, Mr. John{i}" for i in range(n)],
            "cabin": [f"{rng.choice(list('ABCDE'))}{rng.integers(1, 99)}" for _ in range(n)],
            "town": rng.choice([f"Town{chr(97 + i)}" for i in range(20)], n),  # one word
            "x": rng.normal(size=n),
        }
    )
    labels = [g.label for g in features.candidates(Prep().fit(X), X, [])]
    assert "text tokens of name" in labels and "text tokens of cabin" in labels
    assert not any("town" in label for label in labels)


def test_many_string_columns_do_not_crowd_out_the_other_groups():
    rng = np.random.default_rng(0)
    n = 300
    X = pd.DataFrame(
        {f"text{i}": [f"a{j % 30} b{j % 7}" for j in rng.integers(0, 1000, n)] for i in range(25)}
    )
    X["a"], X["b"], X["c"] = rng.normal(size=n), rng.normal(size=n), rng.integers(0, 20, n)
    labels = [g.label for g in features.candidates(Prep().fit(X), X, [])]
    assert sum(label.startswith("text tokens") for label in labels) == features.MAX_TEXT_COLUMNS
    assert "sum of numbers" in labels and "clusters of numbers" in labels
    assert len(labels) <= features.MAX_CANDIDATES


def test_value_frequency_stores_only_repeated_values_up_to_the_cap(monkeypatch):
    monkeypatch.setattr(features, "MAX_REPEATED_VALUES", 3)
    values = [1.0] * 10 + [2.0] * 8 + [3.0] * 6 + [4.0] * 4 + list(np.arange(100.0, 120.0))
    X = pd.DataFrame({"v": values})
    group = ValueFrequency(["v"]).fit(X)
    assert set(group._shares["v"]) == {1.0, 2.0, 3.0}
    out = group.transform(pd.DataFrame({"v": [1.0, 4.0, 105.0, 555.0]}))["v__value_frequency"]
    n = len(values)
    assert out.tolist() == pytest.approx([10 / n, 1 / n, 1 / n, 1 / n])
