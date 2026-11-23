import pickle

import numpy as np
import pandas as pd
import pytest
from sklearn.tree import DecisionTreeClassifier

from fione.engine import features
from fione.engine.automl import AutoML
from fione.engine.config import Deadline, TrainConfig
from fione.engine.features import (
    CategoryFrequency,
    CategoryPairs,
    ClusterDistances,
    CodeParts,
    DateDifferences,
    DateParts,
    GroupMeans,
    IdParts,
    NumberPairs,
    RowCounts,
    RowStatistics,
    SetStatistics,
    TextPairs,
    TextShape,
    TextTokens,
    TextTopics,
    ValueEncoding,
    ValueFrequency,
    alike_columns,
    encoding_keys,
    encoding_rows,
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
            "name": [f"{s}, {t}." for s, t in zip(surname, title, strict=True)],
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


def sentences(n=300, seed=0):
    """Short texts about one of three subjects; the label is the subject."""
    rng = np.random.default_rng(seed)
    subjects = {
        "space": "rocket orbit launch moon satellite telescope planet engine crew mission".split(),
        "food": "bread cheese soup butter pepper dinner kitchen recipe flour sauce".split(),
        "law": "court judge appeal verdict statute lawyer clause trial ruling contract".split(),
    }
    labels = rng.choice(list(subjects), n)
    texts = [" ".join(rng.choice(subjects[label], 8)) for label in labels]
    return pd.DataFrame({"text": texts}), labels


def test_text_topics_separate_subjects_and_keep_missing():
    X, labels = sentences()
    X.loc[0, "text"] = None
    group = TextTopics("text").fit(X)
    assert group.names[0] == "text__topic0" and 2 <= len(group.names) <= features.TOPICS
    assert all(group.sources[i] == ("text",) for i in range(len(group.names)))
    out = group.transform(X)
    assert out.iloc[0].isna().all() and not out.iloc[1:].isna().any().any()
    # a plain tree on the topics must tell the subjects apart
    tree = DecisionTreeClassifier(max_depth=4, random_state=0).fit(out.iloc[1:], labels[1:])
    assert tree.score(out.iloc[1:], labels[1:]) > 0.9
    assert np.array_equal(
        group.transform(X.head(1)).to_numpy()[0], out.iloc[0].to_numpy(), equal_nan=True
    )


def test_text_topics_without_words_give_no_features():
    X = pd.DataFrame({"text": ["", "-", "?!", ".."] * 10})
    assert TextTopics("text").fit(X).names == []


def test_text_topics_are_offered_for_prose_only():
    X, _ = sentences()
    X["name"] = [f"Mr. Number{i}" for i in range(len(X))]  # 2 words: a name, not prose
    labels = [g.label for g in features.candidates(Prep().fit(X), X, [])]
    assert "text topics of text" in labels and "text topics of name" not in labels


def test_text_topics_survive_pickling_and_the_views():
    import pickle

    X, _ = sentences()
    prep = Prep().fit(X, [TextTopics("text")])
    clone = pickle.loads(pickle.dumps(prep))  # noqa: S301 - a frame this test built
    for view in ("tree", "dense", "catboost", "linear"):
        pd.testing.assert_frame_equal(getattr(prep, view)(X), getattr(clone, view)(X))


def test_constant_outputs_are_dropped():
    X = pd.DataFrame({"t": ["abcdef", "ghijkl"] * 5})
    names = TextShape("t").fit(X).names
    assert "t__length" not in names and "t__words" not in names


def test_category_frequency_unseen_is_the_rarest_share_and_missing_stays_missing():
    X = pd.DataFrame({"c": ["a"] * 6 + ["b"] * 3 + [None]})
    group = CategoryFrequency(["c"]).fit(X)
    out = group.transform(pd.DataFrame({"c": ["a", "b", "zzz", None]}))["c__frequency"]
    assert out.iloc[:3].tolist() == pytest.approx([6 / 9, 3 / 9, 3 / 9])  # of the non-missing rows
    assert np.isnan(out.iloc[3])


def test_category_frequency_pickled_without_the_unseen_share_keeps_zero():
    X = pd.DataFrame({"c": ["a"] * 6 + ["b"] * 3})
    group = CategoryFrequency(["c"]).fit(X)
    del group.__dict__["_unseen"]
    loaded = pickle.loads(pickle.dumps(group))
    assert loaded.transform(pd.DataFrame({"c": ["zzz"]}))["c__frequency"].tolist() == [0.0]


def test_row_counts_count_missing_and_zero_values():
    X = pd.DataFrame({"a": [0, 1, None, 0], "b": [None, None, 5, 0], "c": ["x", None, "y", "z"]})
    out = RowCounts(["a", "b", "c"], ["a", "b"]).fit(X).transform(X)
    assert out["missing_count"].tolist() == [1, 2, 1, 0]
    assert out["zero_count"].tolist() == [1, 0, 0, 2]


def test_row_statistics_summarise_the_numbers_that_are_neither_zero_nor_missing():
    X = pd.DataFrame({"a": [0, 3.0, None, -3.0], "b": [0, 0, 0, 7.0], "c": [0, 1.0, 0, 0]})
    group = RowStatistics(["a", "b", "c"]).fit(X)
    out = group.transform(X)
    one, three, seven = np.log1p(1), np.log1p(3), np.log1p(7)
    assert list(out.columns) == [f"{n}_nonzero" for n in ("mean", "median", "max", "std")]
    assert out.loc[0].isna().all()  # nothing but zeros
    assert out.loc[1, "mean_nonzero"] == pytest.approx((three + one) / 2)
    assert out.loc[1, "max_nonzero"] == pytest.approx(three)
    assert out.loc[2].isna().all()  # a gap and zeros
    assert out.loc[3, "max_nonzero"] == pytest.approx(seven)  # the sign survives the log
    assert out.loc[3, "median_nonzero"] == pytest.approx((seven - three) / 2)
    assert out.loc[3, "std_nonzero"] == pytest.approx(np.std([-three, seven]))
    assert group.sources == [("a", "b", "c")] * 4


def hands(n=1500, seed=0):
    """Five cards as suits S1..S5 (1-4) and ranks C1..C5 (1-13), and a class that depends only on
    how the ranks repeat and whether the suits agree, never on which card is where."""
    rng = np.random.default_rng(seed)
    ranks = rng.integers(1, 14, (n, 5))
    pairs = rng.random(n) < 0.3  # a repeated rank is rare among random hands
    ranks[pairs, 1] = ranks[pairs, 0]
    suits = rng.integers(1, 5, (n, 5))
    flush = rng.random(n) < 0.3
    suits[flush] = suits[flush, :1]
    X = pd.DataFrame(
        np.hstack([suits, ranks]),
        columns=[f"S{i}" for i in range(1, 6)] + [f"C{i}" for i in range(1, 6)],
    )
    repeats = 5 - np.array([len(set(row)) for row in ranks])
    return X, np.minimum(repeats, 1) + 2 * flush


def test_set_statistics_describe_a_row_whatever_the_order_of_its_columns():
    X = pd.DataFrame(
        {
            "d1": [2, 5, 3, 1],
            "d2": [2, 5, 3, 2],
            "d3": [2, 4, 1, 3],
            "d4": [4, 6, 3, 4],
            "d5": [4, 4, 3, 5],
        }
    )
    group = SetStatistics([list(X.columns)]).fit(X)
    out = group.transform(X)
    name = "d1..d5"
    assert out[f"{name} distinct values"].tolist() == [2, 3, 2, 5]
    assert out[f"{name} commonest count"].tolist() == [3, 2, 4, 1]
    assert out[f"{name} second commonest count"].tolist() == [2, 2, 1, 1]
    assert out[f"{name} range"].tolist() == [2, 2, 2, 4]
    assert out[f"{name} value 1 in order"].tolist() == [2, 4, 1, 1]
    assert out[f"{name} value 5 in order"].tolist() == [4, 6, 3, 5]
    assert group.sources == [tuple(X.columns)] * len(group.names)
    shuffled = group.transform(X[["d4", "d2", "d5", "d1", "d3"]].set_axis(X.columns, axis=1))
    pd.testing.assert_frame_equal(shuffled, out)  # the same cards in another order


def test_set_statistics_leave_a_row_with_a_gap_missing_and_do_not_mind_other_numbers():
    X = pd.DataFrame({"a": [1.0, 2, 3], "b": [1.0, 2, None], "c": [2.0, 2, 3]})
    group = SetStatistics([["a", "b", "c"]]).fit(X)
    out = group.transform(X)
    assert out.loc[2].isna().all() and not out.loc[:1].isna().any().any()
    assert out["a..c distinct values"].tolist()[:2] == [2, 1]
    odd = pd.DataFrame({"a": [1.5, 2.0], "b": [1.5, 2.5], "c": [9.0, 9.0]})  # not whole numbers
    assert group.transform(odd)["a..c commonest count"].tolist() == [2, 1]


def test_set_statistics_do_not_depend_on_how_many_rows_are_computed_at_once(monkeypatch):
    X, _ = hands(40)
    group = SetStatistics([list(X.columns[:5]), list(X.columns[5:])]).fit(X)
    whole = group.transform(X)
    monkeypatch.setattr(features, "STATISTIC_CELLS", 30)  # 3 rows at a time
    pd.testing.assert_frame_equal(group.transform(X), whole)
    pd.testing.assert_frame_equal(group.transform(X), whole)  # and the same again
    assert len(group.transform(X.head(0))) == 0


def test_alike_columns_are_numbers_over_the_same_few_whole_values():
    rng = np.random.default_rng(0)
    n = 200
    X = pd.DataFrame(
        {
            **{f"d{i}": rng.integers(1, 7, n) for i in range(4)},  # dice
            **{f"s{i}": rng.integers(0, 2, n) for i in range(3)},  # flags
            "age": rng.integers(18, 90, n),
            "price": rng.normal(size=n),
            "text": rng.choice(list("xyz"), n),
        }
    )
    prep = Prep().fit(X)
    assert alike_columns(prep, X, {}) == [["d0", "d1", "d2", "d3"], ["s0", "s1", "s2"]]
    assert alike_columns(prep, X, {"s1": 0}) == [["s0", "s1", "s2"], ["d0", "d1", "d2", "d3"]]
    labels = [g.label for g in features.candidates(prep, X, [])]
    assert "statistics of alike columns per row" in labels


def test_no_set_when_columns_differ_in_domain_or_are_too_few_or_too_many_or_not_whole():
    rng = np.random.default_rng(1)
    n = 100

    def sets(frame):
        return alike_columns(Prep().fit(frame), frame, {})

    assert not sets(
        pd.DataFrame(
            {"a": rng.integers(1, 7, n), "b": rng.integers(1, 5, n), "c": rng.integers(0, 9, n)}
        )
    )
    assert not sets(pd.DataFrame({"a": rng.integers(1, 7, n), "b": rng.integers(1, 7, n)}))  # two
    wide = pd.DataFrame(rng.integers(0, 2, (n, 13)), columns=[f"f{i}" for i in range(13)])
    assert not sets(wide)  # too many to be a hand
    assert sets(wide.iloc[:, :12])
    floats = pd.DataFrame(rng.integers(1, 7, (n, 3)) + 0.5, columns=list("abc"))
    assert not sets(floats)
    wide_range = pd.DataFrame(rng.integers(0, 1000, (n, 4)), columns=list("abcd"))
    assert not sets(wide_range)  # a span of hundreds is a measure, not a kind of value
    many = pd.DataFrame(
        {f"g{k}_{i}": rng.integers(0, k + 2, n) for k in range(5) for i in range(3)}
    )
    assert len(sets(many)) == features.MAX_SETS


def test_the_gate_adopts_set_statistics_for_a_label_that_depends_on_how_cards_repeat():
    X, y = hands()
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert "statistics of alike columns per row" in {g.label for g in kept}
    rng = np.random.default_rng(3)  # the same cards with a label that has nothing to do with them
    kept, verdicts = select_groups(
        X, rng.integers(0, 3, len(X)), "classification", 5, 0, Deadline(120)
    )
    assert "statistics of alike columns per row" not in {g.label for g in kept}


def test_set_statistics_survive_pickling():
    X, _ = hands(60)
    group = SetStatistics([list(X.columns[:5]), list(X.columns[5:])]).fit(X)
    clone = pickle.loads(pickle.dumps(group))  # noqa: S301 - a frame this test built
    pd.testing.assert_frame_equal(clone.transform(X), group.transform(X))
    assert clone.sources == group.sources


def test_candidates_offer_row_statistics_only_for_many_numbers():
    rng = np.random.default_rng(0)
    wide = pd.DataFrame(rng.normal(size=(50, 12)), columns=[f"n{i}" for i in range(12)])
    labels = [g.label for g in features.candidates(Prep().fit(wide), wide, [])]
    assert "statistics of numbers per row" in labels
    narrow = wide.iloc[:, :4]
    labels = [g.label for g in features.candidates(Prep().fit(narrow), narrow, [])]
    assert "statistics of numbers per row" not in labels


def test_row_statistics_do_not_depend_on_how_many_rows_are_computed_at_once(monkeypatch):
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(25, 4)) * (rng.random((25, 4)) < 0.6), columns=list("abcd"))
    group = RowStatistics(list(X.columns)).fit(X)
    whole = group.transform(X)
    monkeypatch.setattr(features, "STATISTIC_CELLS", 12)  # 3 rows at a time
    pd.testing.assert_frame_equal(group.transform(X), whole)
    assert len(group.transform(X.head(0))) == 0


def test_text_pairs_compare_the_words_of_two_columns():
    X = pd.DataFrame(
        {
            "a": ["How to learn Python 3", "What is a cat", "Same words", None, "go 2 the end"],
            "b": [
                "how to learn Python 3?",
                "Why is the sky blue today",
                "words Same",
                "x y",
                "go 3 the end",
            ],
        }
    )
    group = TextPairs(["a", "b"]).fit(X)
    out = group.transform(X).set_axis(TextPairs._PARTS, axis=1)
    assert out.loc[0, "equal"] == 1 and out.loc[0, "jaccard"] == 1 and out.loc[0, "common"] == 5
    assert out.loc[1, "common"] == 1 and out.loc[1, "same_first"] == 0
    assert out.loc[1, "words_diff"] == 2 and out.loc[1, "words_ratio"] == pytest.approx(4 / 6)
    assert out.loc[1, "shorter_share"] == pytest.approx(1 / 4)
    assert out.loc[2, "jaccard"] == 1 and out.loc[2, "equal"] == 0  # the same words, not the order
    assert out.loc[2, "same_first"] == 0 and out.loc[2, "same_last"] == 0
    assert out.loc[3].isna().all()  # a missing text
    assert out.loc[4, "same_numbers"] == 0 and out.loc[4, "same_first"] == 1
    assert out.loc[4, "same_last"] == 1
    assert group.sources == [("a", "b")] * len(TextPairs._PARTS)


def test_text_pairs_do_not_depend_on_how_many_rows_are_read_at_once(monkeypatch):
    X = pd.DataFrame(
        {
            "a": [f"x{i % 3} y z{i % 5}" for i in range(25)],
            "b": [f"y x{i % 4} q" for i in range(25)],
        }
    )
    group = TextPairs(["a", "b"]).fit(X)
    whole = group.transform(X)
    monkeypatch.setattr(features, "PAIR_ROWS", 4)
    pd.testing.assert_frame_equal(group.transform(X), whole)
    assert len(group.transform(X.head(0))) == 0


def test_the_gate_adopts_row_statistics_that_explain_a_target_of_many_sparse_columns(monkeypatch):
    rng = np.random.default_rng(0)
    n, width = 1200, 40
    X = pd.DataFrame(
        rng.exponential(1000, (n, width)) * (rng.random((n, width)) < 0.2),
        columns=[f"n{i}" for i in range(width)],
    )
    level = rng.normal(size=n)  # the log scale of a row's values moves them all together
    X = X * np.exp(level)[:, None]
    y = np.log1p(X.where(X > 0)).mean(axis=1).fillna(0).to_numpy()
    kept, verdicts = select_groups(X, y, "regression", 5, 0, Deadline(120))
    assert "statistics of numbers per row" in {g.label for g in kept}
    monkeypatch.setattr(features, "MIN_STATISTIC_COLUMNS", 10**6)  # not offered
    kept, verdicts = select_groups(X, y, "regression", 5, 0, Deadline(120))
    assert "statistics of numbers per row" not in {v.group for v in verdicts}


def test_candidates_offer_text_pairs_only_for_two_text_columns():
    rng = np.random.default_rng(0)
    words = [f"word{i}" for i in range(40)]
    sentence = lambda: " ".join(rng.choice(words, 6))  # noqa: E731
    X = pd.DataFrame({"a": [sentence() for _ in range(200)], "b": [sentence() for _ in range(200)]})
    labels = [g.label for g in features.candidates(Prep().fit(X), X, [])]
    assert "similarity of texts" in labels
    one = X[["a"]]
    labels = [g.label for g in features.candidates(Prep().fit(one), one, [])]
    assert "similarity of texts" not in labels


def test_candidates_try_text_pairs_early_for_running_texts_and_last_for_other_texts():
    rng = np.random.default_rng(0)
    words = [f"word{i}" for i in range(40)]
    sentence = lambda n: " ".join(rng.choice(words, n))  # noqa: E731
    prose = pd.DataFrame({c: [sentence(8) for _ in range(200)] for c in "ab"})
    labels = [g.label for g in features.candidates(Prep().fit(prose), prose, [])]
    assert labels.index("similarity of texts") < labels.index("text tokens of a")
    codes = pd.DataFrame({c: [f"{rng.choice(words)} {k % 50}" for k in range(200)] for c in "ab"})
    labels = [g.label for g in features.candidates(Prep().fit(codes), codes, [])]
    assert labels[-1] == "similarity of texts"  # no identifier column here


def test_text_pairs_compare_running_texts_even_when_other_text_columns_rank_higher():
    rng = np.random.default_rng(0)
    words = [f"word{i}" for i in range(60)]
    n = 300
    X = pd.DataFrame(
        {
            **{f"c{i}": [f"{rng.choice(words[:5])} {k % 40}" for k in range(n)] for i in range(3)},
            **{
                q: [" ".join(rng.choice(words, 9)) + f" {k}" for k in range(n)]
                for q in ("q1", "q2")
            },
        }
    )
    ranked = ["c0", "c1", "c2", "q1", "q2"]
    found = features.candidates(Prep().fit(X), X, ranked)
    pairs = next(g for g in found if g.label == "similarity of texts")
    assert pairs.columns[:2] == ("q1", "q2")
    labels = [g.label for g in found]
    assert labels.index("similarity of texts") < labels.index("text tokens of c0")


def test_the_gate_adopts_text_pairs_that_explain_whether_two_texts_match(monkeypatch):
    rng = np.random.default_rng(0)
    words = [f"w{i}" for i in range(300)]
    n = 1500
    first, second, y = [], [], []
    for _ in range(n):
        one = list(rng.choice(words, 8, replace=False))
        same = rng.random() < 0.5
        other = list(one) if same else list(rng.choice(words, 8, replace=False))
        if same:
            rng.shuffle(other)
            other[0] = str(rng.choice(words))
        first.append(" ".join(one))
        second.append(" ".join(other))
        y.append(int(same))
    X, y = pd.DataFrame({"a": first, "b": second}), np.array(y)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert "similarity of texts" in {g.label for g in kept}
    monkeypatch.setattr(features, "MAX_PAIR_TEXTS", 1)  # never offered
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert "similarity of texts" not in {v.group for v in verdicts}


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


def test_date_parts_of_day_first_strings():
    X = pd.DataFrame(
        {
            "a": ["25-12-2024 13:30", "02-10-2024 01:00"],
            "b": ["24-12-2024 13:30", "30-09-2024 01:00"],
        }
    )
    out = DateParts(["a"]).fit(X).transform(X)
    assert out["a__hour"].tolist() == [13, 1] and out["a__dayofyear"].tolist() == [360, 276]
    diff = DateDifferences(["a", "b"]).fit(X).transform(X)
    assert diff["a - b"].tolist() == [86400.0, 2 * 86400.0]
    fitted = DateParts(["a"]).fit(X)
    one = fitted.transform(X.head(1).assign(a="03-11-2024 10:00"))
    assert one["a__dayofyear"].tolist() == [308]  # 3 November: day first, as fitted


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


def test_category_pairs_give_an_unseen_pair_the_rarest_share():
    X = pd.DataFrame({"a": ["x", "x", "y", "y"], "b": ["p", "p", "p", "q"]})
    group = CategoryPairs(["a", "b"]).fit(X)
    new = pd.DataFrame({"a": ["x", "z"], "b": ["q", "p"]})  # a new combination, a new category
    assert group.transform(new)["a x b frequency"].tolist() == [0.25, 0.25]


def test_category_pairs_pickled_without_the_unseen_share_keep_zero():
    X = pd.DataFrame({"a": ["x", "x", "y", "y"], "b": ["p", "p", "p", "q"]})
    group = CategoryPairs(["a", "b"]).fit(X)
    del group.__dict__["_unseen"]
    loaded = pickle.loads(pickle.dumps(group))
    out = loaded.transform(pd.DataFrame({"a": ["z"], "b": ["p"]}))["a x b frequency"]
    assert out.tolist() == [0.0]


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


def test_value_frequency_counts_repeated_numbers_and_gives_unseen_the_rarest_share():
    X = pd.DataFrame({"fare": [7.25] * 6 + [10.0] * 3 + [None]})
    group = ValueFrequency(["fare"]).fit(X)
    out = group.transform(pd.DataFrame({"fare": [7.25, 10.0, 99.0, None]}))["fare__value_frequency"]
    assert out.iloc[:3].tolist() == pytest.approx([6 / 9, 3 / 9, 3 / 9])  # unseen = rarest
    assert np.isnan(out.iloc[3])
    singles = pd.DataFrame({"fare": [7.25] * 6 + [10.0] * 3 + [1.0]})
    out = ValueFrequency(["fare"]).fit(singles).transform(pd.DataFrame({"fare": [99.0]}))
    assert out["fare__value_frequency"].tolist() == pytest.approx([1 / 10])  # one row's share


def test_value_frequency_pickles_with_its_unseen_share():
    X = pd.DataFrame({"fare": [7.25] * 6 + [10.0] * 3})
    loaded = pickle.loads(pickle.dumps(ValueFrequency(["fare"]).fit(X)))
    out = loaded.transform(pd.DataFrame({"fare": [99.0]}))["fare__value_frequency"]
    assert out.tolist() == pytest.approx([3 / 9])


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


def test_the_gate_keeps_the_rows_of_a_group_in_one_fold():
    X, y = people()
    groups = np.arange(len(X)) // 6
    gate = features._Gate(X, y, "classification", 5, 0, groups=groups)
    for repeat in range(2):
        for train, valid in gate.folds(repeat):
            assert not set(groups[train]) & set(groups[valid])
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120), row_groups=groups)
    assert verdicts


def test_the_gate_lowers_its_folds_to_the_groups_it_has():
    X, y = people()
    gate = features._Gate(X, y, "classification", 5, 0, groups=np.arange(len(X)) % 3)
    assert gate.nfolds == 3


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


def _gate_sizes(monkeypatch, deadline_secs):
    """Rows of every gate that ``select_groups`` builds, when a repeat of the folds takes 10 s."""
    sizes = []

    class Recording(features._Gate):
        def __init__(self, X, *args, **kwargs):
            sizes.append(len(X))
            super().__init__(X, *args, **kwargs)

        def secs(self, groups):
            return 10.0

    monkeypatch.setattr(features, "_Gate", Recording)
    monkeypatch.setattr(features, "GATE_ROWS", 600)
    monkeypatch.setattr(features, "GATE_MIN_ROWS", 100)
    X, y = people(1000)
    _, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(deadline_secs))
    return sizes, verdicts


def test_a_short_gate_judges_on_fewer_rows(monkeypatch):
    (first, second), verdicts = _gate_sizes(
        monkeypatch, 60
    )  # 60 s cover 6 repeats of the 40 wanted
    assert first == 600 and 100 <= second < 600
    assert any(v.reason != "time" for v in verdicts)  # groups were judged on the smaller gate


def test_a_gate_with_time_enough_keeps_all_its_rows(monkeypatch):
    assert _gate_sizes(monkeypatch, 10_000)[0] == [600]


def test_the_gate_works_for_regression_too():
    X, y = people()
    kept, verdicts = select_groups(X, y.astype(float), "regression", 5, 0, Deadline(120))
    assert "text tokens of name" in {g.label for g in kept}


def test_the_gate_builds_no_view_once_the_time_is_gone(monkeypatch):
    X, y = people()
    gate = features._Gate(X, y, "classification", 5, 0, lambda: True)
    monkeypatch.setattr(
        features.Prep, "tree", lambda *_: pytest.fail("the view was built after the deadline")
    )
    with pytest.raises(features._OutOfTime):
        gate.losses([], range(1))


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
    monkeypatch.setattr(features, "DECISIVE_GAIN", 2.0)  # no gain is that large
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert kept == [] and not any(v.adopted for v in verdicts)
    assert "time" in {v.reason for v in verdicts}


def test_a_decisive_group_is_kept_when_the_deadline_cuts_the_last_check(monkeypatch):
    X, y = people()
    real = features._Gate.losses

    def cut_the_final_check(self, groups, repeats):
        if min(repeats) >= features.GATE_REPEATS:
            raise features._OutOfTime
        return real(self, groups, repeats)

    monkeypatch.setattr(features._Gate, "losses", cut_the_final_check)
    monkeypatch.setattr(features, "DECISIVE_GAIN", 0.0)  # every adopted group counts
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    adopted = {v.group for v in verdicts if v.adopted}
    assert adopted and {g.label for g in kept} == adopted


def test_the_gate_fits_each_group_once_however_many_views_read_it(monkeypatch):
    X, y = people()
    fits = []
    real = features.Group.fit

    def counting(self, frame, y=None):
        fits.append(self.label)
        return real(self, frame, y)

    monkeypatch.setattr(features.Group, "fit", counting)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert kept and len(fits) == len(set(fits))
    assert {v.group for v in verdicts if v.features} <= set(fits)


class _Clock:
    """A deadline with this much time left that never expires, so only the choice of what to
    judge can be told apart from the gate being cut off."""

    def __init__(self, left):
        self.left = left

    def remaining(self):
        return self.left

    def expired(self):
        return False


def test_the_search_stops_for_the_last_check_when_time_is_short(monkeypatch):
    X, y = people()
    monkeypatch.setattr(features, "DECISIVE_GAIN", 2.0)  # no gain is that large
    full_kept, full = select_groups(X, y, "classification", 5, 0, Deadline(120))
    monkeypatch.setattr(features._Gate, "last_check_secs", lambda self, groups: 10.0)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, _Clock(5.0))
    adopted = [v.group for v in verdicts if v.adopted]
    assert adopted and [g.label for g in kept] == adopted  # confirmed, not dropped for time
    assert all(v.reason == "adopted" for v in verdicts if v.adopted)
    left = [v for v in verdicts if v.reason == "time"]
    assert left and len(verdicts) == len(full)  # every candidate has a verdict
    assert len(left) > len([v for v in full if v.reason == "time"])


def test_the_search_goes_on_while_the_time_left_covers_the_last_check(monkeypatch):
    X, y = people()
    monkeypatch.setattr(features, "DECISIVE_GAIN", 2.0)
    monkeypatch.setattr(features._Gate, "last_check_secs", lambda self, groups: 1.0)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, _Clock(1e9))
    assert not any(v.reason == "time" for v in verdicts)


def test_a_decisive_group_needs_no_time_for_the_last_check(monkeypatch):
    X, y = people()
    monkeypatch.setattr(features, "DECISIVE_GAIN", 0.0)  # every adopted group counts
    monkeypatch.setattr(features._Gate, "last_check_secs", lambda self, groups: 10.0)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, _Clock(5.0))
    assert not any(v.reason == "time" for v in verdicts)


def test_the_gate_estimates_the_last_check_from_the_repeats_it_has_run():
    X, y = people()
    gate = features._Gate(X, y, "classification", 5, 0)
    group = features.TextTokens("name")
    gate.losses([], range(1))
    gate.losses([group], range(1))
    assert gate.secs([group]) == gate._secs[(group.label,)] > 0
    secs = gate.last_check_secs([group])
    assert secs == features.FINAL_REPEATS * (gate.secs([]) + gate.secs([group])) > 0
    assert gate.secs([features.TextShape("name")]) == max(gate._secs.values())  # not measured


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
            "k1": rng.integers(1, 7, n),
            "k2": rng.integers(1, 7, n),
            "k3": rng.integers(1, 7, n),
            "c": rng.choice(list("xyz"), n),
            "d": rng.choice(list("pq"), n),
            "t": [
                f"{['red', 'green', 'blue'][i % 3]} {['apple', 'pear'][i % 2]} {i}"
                for i in range(n)
            ],
            "u": [f"{['red', 'blue'][i % 2]} {i % 7} apple" for i in range(n)],
            "when": pd.date_range("2024-01-01", periods=n, freq="7h"),
            "then": pd.date_range("2023-06-01", periods=n, freq="5h"),
        }
    )
    groups = [
        TextShape("t"),
        TextTokens("t"),
        CategoryFrequency(["c", "d"]),
        RowCounts(list(X.columns), ["a", "b"]),
        RowStatistics(["a", "b"]),
        TextPairs(["t", "u"]),
        DateParts(["when", "then"]),
        DateDifferences(["when", "then"]),
        NumberPairs("ratio", ["a", "b"]),
        GroupMeans(["c"], ["a", "b"]),
        CategoryPairs(["c", "d"]),
        ValueFrequency(["b"]),
        ClusterDistances(["a", "b"]),
        SetStatistics([["k1", "k2", "k3"]]),
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


@pytest.mark.parametrize(
    ("left", "secs"),
    [(60.0, 18.0), (120.0, 30.0), (180.0, 30.0), (600.0, 60.0), (3600.0, 360.0)],
)
def test_a_short_run_gives_the_feature_choice_a_minimum_of_time(left, secs):
    assert AutoML._feature_secs(left) == pytest.approx(secs)


def _id_frame(n=60):
    # groups of 1, 2 and 3 members, and decks that are not equally common
    pid = [f"{g:04d}_{m:02d}" for g in range(1, n) for m in range(1, (g - 1) % 3 + 2)][:n]
    deck = "ABBCCCDDDD"
    return pd.DataFrame(
        {
            "pid": pid,
            "cabin": [f"{deck[i % 10]}/{i % 17}/{'S' if i % 3 == 0 else 'P'}" for i in range(n)],
            "x": np.arange(n, dtype=float),
        }
    )


def test_id_parts_read_numbers_frequencies_and_the_group_size():
    X = _id_frame()
    group = IdParts(["pid", "cabin"]).fit(X)
    assert group.names == [
        "pid__part1",
        "pid__part2",
        "pid__group_size",
        "cabin__part2",
        "cabin__part3_frequency",
        "cabin__group_size",
    ]
    out = group.transform(X)
    assert out["pid__part1"].iloc[:4].tolist() == [1, 2, 2, 3]
    assert out["pid__part2"].iloc[:4].tolist() == [1, 1, 2, 1]
    assert out["pid__group_size"].iloc[:4].tolist() == [1, 2, 2, 3]
    assert out["cabin__group_size"].iloc[0] == 6  # the deck is the first field: A in 6 rows
    assert out["cabin__part2"].iloc[:3].tolist() == [0, 1, 2]
    assert out["cabin__part3_frequency"].iloc[0] == pytest.approx(20 / 60)  # side S
    assert group.sources == [("pid",)] * 3 + [("cabin",)] * 3


def test_id_parts_give_missing_for_unseen_values_and_do_not_depend_on_the_batch():
    X = _id_frame()
    group = IdParts(["pid", "cabin"]).fit(X)
    new = pd.DataFrame(
        {
            "pid": ["0002_01", "9999_01", None, "oops", "0003_x"],
            "cabin": ["B/3/P", "Z/3/P", None, "B/3", "B/3/Q"],
        }
    )
    out = group.transform(new)
    assert out["pid__group_size"].iloc[0] == 2
    assert out["pid__group_size"].iloc[1:4].isna().all()  # unseen, missing, not splitting
    assert out["pid__part1"].iloc[1] == 9999 and np.isnan(out["pid__part1"].iloc[3])
    assert np.isnan(out["pid__part2"].iloc[4])  # not a number
    assert out["cabin__group_size"].iloc[0] > 0 and np.isnan(out["cabin__group_size"].iloc[1])
    assert out["cabin__part3_frequency"].iloc[0] > 0
    assert np.isnan(out["cabin__part3_frequency"].iloc[4])
    assert out["cabin__group_size"].isna().iloc[[1, 2, 3]].all()  # unseen deck: not zero
    for i in range(len(new)):  # one row at a time gives the same values
        pd.testing.assert_frame_equal(group.transform(new.iloc[[i]]), out.iloc[[i]])
    assert len(group.transform(new.head(0))) == 0


def test_id_parts_are_offered_last_and_only_for_identifier_columns():
    X = _id_frame()
    prep = Prep().fit(X)
    labels = [g.label for g in features.candidates(prep, X, ["x"])]
    assert labels[-1] == "parts of identifiers"
    ids = features.candidates(prep, X, [])[-1]
    assert ids.columns == ("pid", "cabin")
    # without such a column the candidates are the ones there are without this group
    plain = X.assign(
        pid=[f"id{i}" for i in range(len(X))],  # no delimiter
        cabin=[f"{'ABCDE'[i % 5]}/{i % 17}/{'PS'[i % 2]}/{i % 3}/q" for i in range(len(X))],  # 5
    )
    plain_labels = [g.label for g in features.candidates(Prep().fit(plain), plain, [])]
    assert "parts of identifiers" not in plain_labels
    expected = [g.label for g in features.candidates(prep, X, [])][:-1]
    assert [g.label for g in features.candidates(prep, X, [])][-1] == "parts of identifiers"
    assert expected  # the other candidates stay as they are


def test_candidates_are_unchanged_when_no_column_is_an_identifier(monkeypatch):
    rng = np.random.default_rng(0)
    n = 300
    X = pd.DataFrame(
        {
            "name": [f"Smith{i % 40}, Mr. John{i}" for i in range(n)],
            "town": rng.choice([f"Town{chr(97 + i)}" for i in range(20)], n),
            "mixed": [f"{'ABCDE'[i % 5]}{i % 99}" for i in range(n)],
            "a": rng.normal(size=n),
            "b": rng.normal(size=n),
        }
    )
    before = [(type(g).__name__, g.label) for g in features.candidates(Prep().fit(X), X, [])]
    assert "IdParts" not in [name for name, _ in before]
    monkeypatch.setattr(features, "IdParts", None)  # would fail if it were ever built
    after = [(type(g).__name__, g.label) for g in features.candidates(Prep().fit(X), X, [])]
    assert after == before


def test_id_layout_needs_a_common_field_count_and_many_distinct_values():
    layout = features._id_layout
    assert layout(pd.Series([f"{i}_{i % 3}" for i in range(50)])) == ("_", 2)
    assert layout(pd.Series([f"{i}.{i % 3}.{i % 5}" for i in range(50)])) == (".", 3)
    assert layout(pd.Series([f"a:{i}" for i in range(50)])) == (":", 2)
    assert layout(pd.Series([f"{i}" for i in range(50)])) is None  # one field
    assert layout(pd.Series([f"{i}_{i}_{i}_{i}_{i}" for i in range(50)])) is None  # five fields
    assert layout(pd.Series(["a_b", "c_d", "e_f"] * 20)) is None  # three distinct values
    mostly = [f"{i}_{i % 3}" for i in range(97)] + ["x", "y", "z"]
    assert layout(pd.Series(mostly)) == ("_", 2)  # 97 % split alike
    assert layout(pd.Series(mostly[:90] + ["x"] * 10)) is None  # 90 %
    assert layout(pd.Series([None] * 20)) is None


def test_id_parts_pickle_with_a_prep_and_transform_alike():
    import pickle

    X = _id_frame()
    prep = Prep().fit(X, [IdParts(["pid", "cabin"])])
    clone = pickle.loads(pickle.dumps(prep))  # noqa: S301 - a frame this test built
    for view in ("tree", "dense", "catboost", "linear"):
        pd.testing.assert_frame_equal(getattr(prep, view)(X), getattr(clone, view)(X))
    assert not prep.linear(X.head(1)).isna().any().any()  # the linear view fills the gaps


def test_id_parts_skip_fields_that_act_as_a_row_index():
    n = 100
    X = pd.DataFrame(
        {
            "user": [f"user_{1000 + i}" for i in range(n)],  # a running number
            "mixed": [f"g{min(i // 3, 20)}_{i % 4}_{i}" for i in range(n)],  # unique last field
        }
    )
    group = IdParts(["user", "mixed"]).fit(X)
    assert group.names == ["mixed__part2", "mixed__group_size"]
    assert group.transform(X.head(1)).columns.tolist() == group.names


def _code_frame(n=400, length=6, seed=0):
    rng = np.random.default_rng(seed)
    letters = np.array(list("ABCDEFG"))
    codes = ["".join(r) for r in rng.choice(letters, (n, length))]
    return pd.DataFrame({"code": codes, "x": rng.normal(size=n)})


def test_code_parts_read_characters_distinct_characters_and_the_longest_repeat():
    X = _code_frame()
    group = CodeParts(["code"]).fit(X)
    assert group.names == [f"code__char{i}" for i in range(1, 7)] + [
        "code__distinct_chars",
        "code__most_repeated_char",
    ]
    assert group.sources == [("code",)] * 8
    out = group.transform(pd.DataFrame({"code": ["ABCDEF", "GGGAAB", "AAAAAA", "BABABA"]}))
    assert out.iloc[0].tolist() == [0, 1, 2, 3, 4, 5, 6, 1]  # characters by rank, all different
    assert out.iloc[1].tolist() == [6, 6, 6, 0, 0, 1, 3, 3]
    assert out.iloc[2]["code__distinct_chars"] == 1 and out.iloc[2]["code__most_repeated_char"] == 6
    assert out.iloc[3]["code__distinct_chars"] == 2 and out.iloc[3]["code__most_repeated_char"] == 3


def test_code_parts_give_missing_for_unseen_characters_other_lengths_and_missing_values():
    X = _code_frame()
    group = CodeParts(["code"]).fit(X)
    new = pd.DataFrame({"code": ["ABCDEZ", "ABC", None, "ABCDEFG", "abcdef", "GFEDCB"]})
    out = group.transform(new)
    assert out["code__char5"].iloc[0] == 4 and np.isnan(out["code__char6"].iloc[0])  # Z unseen
    assert out["code__distinct_chars"].iloc[0] == 6  # counted on the value itself
    assert out.iloc[1:3].isna().all().all()  # other length, missing
    assert out.iloc[3].isna().all()
    assert out.iloc[4].drop(["code__distinct_chars", "code__most_repeated_char"]).isna().all()
    assert out.iloc[5].tolist() == [6, 5, 4, 3, 2, 1, 6, 1]
    for i in range(len(new)):  # one row at a time gives the same values
        pd.testing.assert_frame_equal(group.transform(new.iloc[[i]]), out.iloc[[i]])
    assert len(group.transform(new.head(0))) == 0


def test_code_parts_read_the_first_positions_of_a_long_code_only():
    X = _code_frame(length=20)
    group = CodeParts(["code"]).fit(X)
    assert len(group.names) == features.MAX_CODE_POSITIONS + 2
    assert "code__char17" not in group.names
    tail = group.transform(pd.DataFrame({"code": ["A" * 16 + "BCDE"]}))
    assert tail["code__distinct_chars"].iloc[0] == 5  # the whole code, not its first positions
    assert tail["code__most_repeated_char"].iloc[0] == 16


def test_code_length_needs_a_common_length_within_range_and_no_spaces():
    length = features._code_length
    assert length(pd.Series([f"AB{i:04d}" for i in range(300)])) == 6
    assert length(pd.Series(["AB1"] * 5 + ["QWERTYU"] * 5)) is None  # half of each
    assert length(pd.Series([f"AB{i:04d}" for i in range(99)] + ["x"])) == 6  # 99 %
    assert length(pd.Series([f"AB{i:04d}" for i in range(90)] + ["x"] * 10)) is None
    assert length(pd.Series([f"A{i:01d}" for i in range(9)])) is None  # two characters
    assert length(pd.Series(["A" * 33] * 20)) is None  # too long
    assert length(pd.Series([f"A B{i:03d}" for i in range(20)])) is None  # a space
    assert length(pd.Series([None] * 20)) is None


def test_code_parts_are_offered_for_nearly_unique_codes_of_one_length_only():
    X = _code_frame()
    prep = Prep().fit(X)
    assert prep.kind_of("code") == "frequency"
    found = [g for g in features.candidates(prep, X, ["x"]) if isinstance(g, CodeParts)]
    assert [g.columns for g in found] == [("code",)]
    skipped = {
        "varying length": X.assign(code=[c[: 3 + i % 4] for i, c in enumerate(X["code"])]),
        "few levels": X.assign(code=[c[:2] + "AB"[i % 2] for i, c in enumerate(X["code"])]),
        "structured text (fields)": X.assign(code=[f"{i:03d}_{i % 7}" for i in range(len(X))]),
        "structured text (letters and digits)": X.assign(
            code=[f"AB{i:04d}" for i in range(len(X))]
        ),
        "spaces": X.assign(code=[f"the {c} fox jumps" for c in X["code"]]),
    }
    for reason, frame in skipped.items():
        labels = [g.label for g in features.candidates(Prep().fit(frame), frame, ["x"])]
        assert "characters of codes" not in labels, reason


def test_code_parts_come_before_the_generic_groups_and_leave_other_candidates_alone():
    X = _code_frame()
    prep = Prep().fit(X)
    labels = [g.label for g in features.candidates(prep, X, ["x"])]
    assert labels[0] == "characters of codes"
    bare = X.drop(columns=["code"])
    others = [g.label for g in features.candidates(Prep().fit(bare), bare, ["x"])]
    assert labels[1:] == others  # the other candidates stay as they are


def test_code_parts_pickle_with_a_prep_and_transform_alike():
    X = _code_frame()
    prep = Prep().fit(X, [CodeParts(["code"])])
    clone = pickle.loads(pickle.dumps(prep))  # noqa: S301 - a frame this test built
    for view in ("tree", "dense", "catboost", "linear"):
        pd.testing.assert_frame_equal(getattr(prep, view)(X), getattr(clone, view)(X))
    assert not prep.linear(X.head(1)).isna().any().any()


def _entities(n_entities, size, seed=0):
    """Rows of entities that each occur ``size`` times, named by an id and a surname that
    neither identifies an entity alone."""
    rng = np.random.default_rng(seed)
    ids = np.repeat(np.arange(n_entities), size)
    return pd.DataFrame(
        {
            "cid": ids + 1000,
            "surname": [f"name{i % 151}" for i in ids],
            "x": rng.normal(size=len(ids)),
        }
    ).sample(frac=1, random_state=seed, ignore_index=True)


def test_an_entity_key_needs_more_than_the_levels_of_a_category_and_a_share_of_repeats():
    def column(levels_repeated, singles):
        return pd.Series(
            [*np.repeat(np.arange(levels_repeated), 2), *range(10_000, 10_000 + singles)]
        )

    # 50 levels in all is a small category; 51 is not.
    assert not features._entity_key(pd.Series(np.tile(np.arange(50), 4)))
    assert features._entity_key(pd.Series(np.tile(np.arange(51), 4)))
    # 300 of 1,000 rows share their value (0.3); 290 do not make it.
    assert features._entity_key(column(150, 700))
    assert not features._entity_key(column(145, 710))
    assert not features._entity_key(pd.Series(np.arange(1000)))  # nothing repeats
    assert not features._entity_key(pd.Series([None] * 100))


def test_candidates_offer_pairs_of_repeated_values_only_for_two_entity_columns():
    X = _entities(300, 6)
    labels = [g.label for g in features.candidates(Prep().fit(X), X, ["x"])]
    assert "frequencies of repeated pairs" in labels
    group = next(
        g
        for g in features.candidates(Prep().fit(X), X, ["x"])
        if g.label == "frequencies of repeated pairs"
    )
    assert set(group.columns) == {"cid", "surname"}
    for kept in (["cid", "x"], ["surname", "x"]):  # one entity column alone has no pair
        one = X[kept]
        labels = [g.label for g in features.candidates(Prep().fit(one), one, ["x"])]
        assert "frequencies of repeated pairs" not in labels
    unique = X.assign(cid=np.arange(len(X)), surname=[f"s{i}" for i in range(len(X))])
    labels = [g.label for g in features.candidates(Prep().fit(unique), unique, ["x"])]
    assert "frequencies of repeated pairs" not in labels


FREQUENCY_LABELS = {"frequencies of repeated pairs", "frequencies of repeated numbers"}


def test_candidates_offer_no_frequencies_when_columns_repeat_together_over_groups_of_rows():
    rng = np.random.default_rng(0)
    X = _entities(300, 6)  # an id and a surname that repeat: frequencies are offered
    X["amount"] = np.round(rng.lognormal(3, 1, len(X)), 1)  # a number that repeats
    labels = {g.label for g in features.candidates(Prep().fit(X), X, ["x"])}
    assert FREQUENCY_LABELS <= labels
    # the same rows with the features of their entity joined on: three numbers shared by the
    # rows of an entity, none a copy of another
    shared = pd.DataFrame(rng.normal(size=(300, 3)), columns=["s1", "s2", "s3"])
    joined = pd.concat([X, shared.loc[X["cid"] - 1000].reset_index(drop=True)], axis=1)
    assert features.repeated_blocks(joined, ["s1", "s2", "s3"]) is not None
    labels = {g.label for g in features.candidates(Prep().fit(joined), joined, ["x"])}
    assert not FREQUENCY_LABELS & labels
    assert "difference of numbers" in labels  # the other groups are still offered


def test_repeated_blocks_need_columns_that_are_not_copies_and_values_that_repeat():
    rng = np.random.default_rng(1)
    base = rng.integers(0, 400, 1200)
    levels = rng.normal(size=(400, 3))
    shared = pd.DataFrame(levels[base], columns=["a", "b", "c"])
    found = features.repeated_blocks(shared, ["a", "b", "c"])
    assert found is not None and set(found[0]) == {"a", "b", "c"}
    assert found[1] == pytest.approx(3, rel=0.1)
    assert features.repeated_blocks(shared, ["a", "b"]) is None  # two columns are not enough
    copies = pd.DataFrame({"a": levels[base, 0]})
    copies["b"], copies["c"] = copies["a"] * 2, np.exp(copies["a"])
    assert features.repeated_blocks(copies, ["a", "b", "c"]) is None
    alone = pd.DataFrame(rng.normal(size=(1200, 3)), columns=["a", "b", "c"])
    assert features.repeated_blocks(alone, ["a", "b", "c"]) is None  # no value repeats
    assert features.repeated_blocks(shared.iloc[:150], ["a", "b", "c"]) is None  # too few rows


def test_repeated_blocks_are_not_found_in_columns_that_only_look_alike():
    rng = np.random.default_rng(2)
    n = 3000
    # three independent numbers that each repeat (rounded): no one is a function of another
    rounded = pd.DataFrame(np.round(rng.normal(size=(n, 3)), 1) * 100, columns=["a", "b", "c"])
    assert features.repeated_blocks(rounded, ["a", "b", "c"]) is None
    # a filler (0 or -999) on the same rows is a repeat of one value, not of many
    filler = pd.DataFrame(rng.normal(size=(n, 3)), columns=["a", "b", "c"])
    filler[rng.random(n) < 0.6] = -999.0
    assert features.repeated_blocks(filler, ["a", "b", "c"]) is None
    # a day of the year and its sine and cosine have fewer levels than the day
    day = rng.integers(1, 366, n)
    cyclic = pd.DataFrame({"day": day.astype(float)})
    cyclic["sin"], cyclic["cos"] = np.sin(2 * np.pi * day / 365), np.cos(2 * np.pi * day / 365)
    assert features.repeated_blocks(cyclic, ["day", "sin", "cos"]) is None
    # one missing value is a value that is not shared
    base = rng.integers(0, 400, n)
    levels = rng.normal(size=(400, 3))
    block = pd.DataFrame(levels[base], columns=["a", "b", "c"])
    assert features.repeated_blocks(block, ["a", "b", "c"]) is not None
    block.loc[0, "c"] = np.nan
    assert features.repeated_blocks(block, ["a", "b", "c"]) is None


def test_candidates_pair_the_entity_columns_with_the_most_levels():
    X = _entities(300, 6)
    X["code"] = X["cid"] % 60  # repeated, 60 levels: fewer than the id
    X["town"] = X["cid"] % 80
    X["more"] = X["cid"] % 70
    group = next(
        g
        for g in features.candidates(Prep().fit(X), X, ["x"])
        if g.label == "frequencies of repeated pairs"
    )
    assert len(group.columns) == features.MAX_ENTITY_COLUMNS
    assert group.columns[0] == "cid" and "code" not in group.columns


def test_candidates_find_entity_columns_in_all_rows_that_a_sample_thins_out():
    rng = np.random.default_rng(0)
    n = 300_000
    ids = np.repeat(np.arange(n // 3), 3)  # an entity occurs 3 times
    X = pd.DataFrame(
        {
            "cid": ids + 1000,
            "surname": [f"name{i % 151}" for i in ids],
            "x": rng.normal(size=n),
        }
    )
    sample = X.sample(20_000, random_state=0).reset_index(drop=True)
    assert not features._entity_key(sample["cid"])  # a sample shows 1 row in 8 of an entity again
    assert features._entity_key(X["cid"])

    def pairs(*args):
        found = features.candidates(Prep().fit(sample), sample, ["x"], *args)
        return [g for g in found if g.label == "frequencies of repeated pairs"]

    assert pairs() == []  # without the rows, as before: only the surname repeats in the sample
    (group,) = pairs(X)
    assert set(group.columns) == {"cid", "surname"}


def test_candidates_leave_duration_columns_out_of_the_entity_columns():
    rng = np.random.default_rng(0)
    n = 3000
    ids = rng.integers(0, 200, n)
    X = pd.DataFrame(
        {
            "cid": ids + 1000,
            "stay": [f"{i % 90 + 1} days" for i in ids],  # a duration with 90 levels that repeat
            "x": rng.normal(size=n),
        }
    )
    prep = Prep().fit(X)
    assert "stay" in prep.duration_columns
    labels = [g.label for g in features.candidates(prep, X, ["x"])]
    assert "frequencies of repeated pairs" not in labels  # only the id is left
    X["town"] = [f"town{i % 120}" for i in ids]
    found = features.candidates(Prep().fit(X), X, ["x"])
    (group,) = [g for g in found if g.label == "frequencies of repeated pairs"]
    assert set(group.columns) == {"cid", "town"}


class _Spy(features.Group):
    """A group that records how many rows it was fitted on."""

    def __init__(self, label, density):
        self.label, self.columns, self.density, self.fitted_on = label, ("x",), density, []

    def _fit(self, X):
        self.fitted_on.append(len(X))
        self._sources = {"spy": ("x",)}

    def _compute(self, df):
        return pd.DataFrame({"spy": df["x"].to_numpy() * 2.0}, index=df.index)


def test_the_gate_fits_groups_that_count_rows_on_all_rows_and_the_others_on_the_sample():
    # About 130,000 rows of entities that occur 4 or 8 times (6 on average).
    X = pd.concat(
        [_entities(10_800, 4), _entities(10_800, 8, seed=1).assign(cid=lambda d: d.cid + 50_000)],
        ignore_index=True,
    )
    X = X.sample(frac=1, random_state=0, ignore_index=True)
    y = (np.arange(len(X)) % 2).astype(int)
    sample = np.sort(np.random.default_rng(1).choice(len(X), 20_000, replace=False))
    Xs, ys = X.iloc[sample].reset_index(drop=True), y[sample]
    gate = features._Gate(Xs, ys, "classification", 5, 0, all_rows=X)
    counting, plain = _Spy("counting", True), _Spy("plain", False)
    gate.fitted(counting), gate.fitted(plain)
    assert gate.fitted(counting).fitted_on == [len(X)]
    assert gate.fitted(plain).fitted_on == [len(Xs)]
    pairs = CategoryPairs(["cid", "surname"], "pairs")
    name = "cid x surname frequency"
    share = gate.fitted(pairs).transform(Xs)[name]
    assert set(np.round(share * len(X))) == {
        4.0,
        8.0,
    }  # the entity's rows of all, not of the sample
    thin = features._Gate(Xs, ys, "classification", 5, 0).fitted(pairs).transform(Xs)[name]
    assert thin.mean() * len(Xs) < 2  # a sample shows an entity once or twice, not 6 times


def test_select_groups_hands_the_gate_all_the_rows_also_after_it_shrinks(monkeypatch):
    rows = []

    class Recording(features._Gate):
        def __init__(self, X, *args, **kwargs):
            super().__init__(X, *args, **kwargs)
            rows.append((len(X), len(self.all_rows)))

        def secs(self, groups):
            return 10.0

    monkeypatch.setattr(features, "_Gate", Recording)
    monkeypatch.setattr(features, "GATE_ROWS", 600)
    monkeypatch.setattr(features, "GATE_MIN_ROWS", 100)
    X, y = people(1000)
    select_groups(X, y, "classification", 5, 0, Deadline(60))
    assert len(rows) == 2 and rows[0][0] == 600 and rows[1][0] < 600
    assert [n for _, n in rows] == [1000, 1000]


def test_the_gate_adopts_pairs_of_repeated_values_when_the_size_of_an_entity_explains_the_label(
    monkeypatch,
):
    monkeypatch.setattr(features, "GATE_ROWS", 3000)
    rng = np.random.default_rng(0)
    sizes = rng.choice([1, 2, 10], 4000, p=[0.5, 0.3, 0.2])
    ids = np.repeat(np.arange(len(sizes)), sizes)
    X = pd.DataFrame(
        {
            "cid": ids + 1000,
            "surname": [f"name{i % 151}" for i in ids],
            "x": rng.normal(size=len(ids)),
        }
    )
    y = (np.repeat(sizes, sizes) >= 10).astype(int)
    flip = rng.random(len(y)) < 0.05
    y = np.where(flip, 1 - y, y)
    assert len(X) > 3 * 3000 / 2
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert "frequencies of repeated pairs" in {v.group for v in verdicts if v.adopted}


def test_category_pairs_with_a_label_pickle_through_prep_and_keep_it():
    X = pd.concat([_entities(60, 2), _entities(40, 5, seed=1).assign(cid=lambda d: d.cid + 5000)])
    group = CategoryPairs(["cid", "surname"], "frequencies of repeated pairs")
    prep = Prep().fit(X, [group])
    clone = pickle.loads(pickle.dumps(prep))  # noqa: S301 - a frame this test built
    assert [g.label for g in clone.groups] == ["frequencies of repeated pairs"]
    pd.testing.assert_frame_equal(prep.tree(X), clone.tree(X))
    assert prep.sources[-1] == ("cid", "surname")


def test_groups_pickled_before_density_existed_still_load_and_count_rows_as_before():
    assert all("density" not in vars(g) for g in (CategoryFrequency(["c"]), ValueFrequency(["b"])))
    for group in (CategoryPairs(["a", "b"]), CategoryFrequency(["a"]), ValueFrequency(["a"])):
        loaded = pickle.loads(pickle.dumps(group))  # noqa: S301 - a group this test built
        assert "density" not in vars(loaded) and loaded.density
    assert not features.Group.density and not TextShape("t").density


def _labels_and_measures(n=3000, seed=0, task="classification"):
    """A label (accounts spread over a wide range, each with its own rate), a measure that
    explains the target smoothly, a label that explains nothing, and an age."""
    rng = np.random.default_rng(seed)
    accounts = rng.choice(rng.integers(0, 500_000, 120), n)
    effect = {a: rng.normal(scale=1.5) for a in np.unique(accounts)}
    measure = rng.integers(0, 40_000, n) * 7  # whole numbers with gaps, each value rare
    measure = np.round(measure / 300).astype(int) * 300  # ~130 values, spread out
    noise_label = rng.choice(rng.integers(0, 500_000, 120), n)
    age = rng.integers(18, 90, n)
    score = (
        pd.Series(accounts).map(effect).to_numpy() + measure / measure.std() + rng.normal(size=n)
    )
    y = (score > np.median(score)).astype(int) if task == "classification" else score
    X = pd.DataFrame(
        {"account": accounts, "measure": measure, "noise_label": noise_label, "age": age}
    )
    return X, y


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_a_label_is_a_code_and_a_measure_or_an_empty_label_is_not(task):
    X, y = _labels_and_measures(task=task)
    assert features.code_columns(Prep().fit(X), X, y, task) == ["account"]


def test_the_codes_stay_whatever_the_gate_judges_of_the_other_groups():
    X, y = _labels_and_measures()
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert kept[0].label == features.CODES_LABEL and kept[0].columns == ("account",)
    assert verdicts[0].group == features.CODES_LABEL and verdicts[0].adopted
    prep = Prep().fit(X, kept)
    assert prep.codes == ("account",)


def test_no_code_group_for_data_without_labels():
    X, y = noise_text()
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    assert features.CODES_LABEL not in [g.label for g in kept] + [v.group for v in verdicts]


def test_the_code_screen_is_deterministic_and_reads_columns_with_missing_values():
    X, y = _labels_and_measures()
    X.loc[::7, "account"] = np.nan
    first = features.code_columns(Prep().fit(X), X, y, "classification")
    assert first == ["account"]
    assert features.code_columns(Prep().fit(X), X, y, "classification") == first


def test_the_code_screen_reads_several_classes_and_many():
    X, y = _labels_and_measures()
    classes = np.digitize(y + np.random.default_rng(1).normal(size=len(y)), [0.3, 0.6])
    assert features.code_columns(Prep().fit(X), X, classes, "classification") == ["account"]
    many = np.random.default_rng(2).integers(0, 15, len(X))  # more classes than it reads
    assert features.code_columns(Prep().fit(X), X, many, "classification") == []


def test_the_code_screen_is_silent_for_a_constant_target_few_rows_and_no_time():
    X, y = _labels_and_measures()
    prep = Prep().fit(X)
    assert features.code_columns(prep, X, np.zeros(len(X), int), "classification") == []
    assert (
        features.code_columns(prep.fit(X.head(200)), X.head(200), y[:200], "classification") == []
    )
    assert features.code_columns(prep.fit(X), X, y, "classification", None, lambda: True) == []


def test_no_codes_are_read_when_the_gate_keeps_the_rows_of_a_group_together():
    X, y = _labels_and_measures()
    kept, verdicts = select_groups(
        X, y, "classification", 5, 0, Deadline(120), row_groups=np.arange(len(X)) // 6
    )
    assert features.CODES_LABEL not in [v.group for v in verdicts]


def test_the_verdict_names_the_code_columns_and_claims_no_gain():
    X, y = _labels_and_measures()
    _, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(120))
    codes = verdicts[0].to_dict()
    assert codes["columns"] == ["account"] and codes["gain"] == 0.0
    assert codes["reason"] == features.CODES_REASON
    assert "columns" not in verdicts[1].to_dict()


def test_a_model_with_codes_keeps_them_after_pickling():
    X, y = _labels_and_measures()
    prep = Prep().fit(X, [features.CodeLevels(["account"])])
    again = pickle.loads(pickle.dumps(prep))
    assert again.codes == ("account",)
    pd.testing.assert_frame_equal(again.catboost(X), prep.catboost(X))
    pd.testing.assert_frame_equal(again.levels(X), prep.levels(X))
    old = pickle.loads(pickle.dumps(Prep().fit(X)))  # fitted before codes existed
    del old.__dict__["codes"], old.__dict__["_code_shares"], old.__dict__["_code_unseen"]
    assert old.codes == () and old.tree(X).shape[1] == len(old.feature_names)


def test_characters_of_codes_are_read_for_two_string_columns_at_most():
    wide = pd.concat(
        [_code_frame(seed=s)["code"].rename(f"code{s}") for s in range(5)] + [_code_frame()["x"]],
        axis=1,
    )
    prep = Prep().fit(wide)
    found = [g for g in features.candidates(prep, wide, ["x"]) if isinstance(g, CodeParts)]
    assert [len(g.columns) for g in found] == [features.MAX_CODE_COLUMNS] == [2]


def test_a_column_that_is_not_all_whole_numbers_is_never_read_as_codes():
    X, _ = _labels_and_measures()
    X["account"] = X["account"] + (np.arange(len(X)) == 5) * 0.5  # one value of 2.5 in a label
    assert Prep().fit(X, [features.CodeLevels(["account"])]).codes == ()


def test_a_label_with_no_effect_is_not_a_code_even_when_the_target_is_rare():
    rng = np.random.default_rng(0)
    for p in (0.05, 0.01):
        fired = 0
        for _ in range(40):
            X = pd.DataFrame({"label": rng.integers(0, 20_000 // 3, 20_000) * 11})
            y = (rng.random(len(X)) < p).astype(int)
            fired += bool(features.code_columns(Prep().fit(X), X, y, "classification"))
        assert fired <= 1


def test_a_label_with_no_effect_is_not_a_code_for_many_classes_or_a_heavy_tailed_target():
    rng = np.random.default_rng(1)
    shares = np.array([0.4, 0.25, 0.15, 0.08, 0.05, 0.03, 0.02, 0.01, 0.005, 0.005])
    fired = 0
    for _ in range(30):
        X = pd.DataFrame({"label": rng.integers(0, 20_000 // 3, 20_000) * 11})
        classes = rng.choice(len(shares), len(X), p=shares)
        fired += bool(features.code_columns(Prep().fit(X), X, classes, "classification"))
        heavy = rng.lognormal(0, 2, len(X))
        fired += bool(features.code_columns(Prep().fit(X), X, heavy, "regression"))
    assert fired <= 1


def _prices(n=4000, seed=0):
    """A price whose whole part decides the label, and an unrelated one."""
    rng = np.random.default_rng(seed)
    price = rng.integers(0, 40, n) + rng.integers(0, 10, n) / 10
    y = (rng.random(n) < np.where(np.floor(price) % 4 == 0, 0.6, 0.05)).astype(int)
    return pd.DataFrame({"price": price, "noise": rng.normal(size=n)}), y


def test_encoding_keys_choose_numbers_with_repeated_values_only():
    X, _ = _prices()
    X["unique"] = np.arange(len(X)) + 0.5
    X["count"] = np.arange(len(X)) % 3
    assert encoding_keys(["price", "noise", "unique", "count"], X) == [
        ("price", "whole"),
        ("price", "value"),
    ]


def test_the_encodings_are_judged_on_more_rows_when_the_time_covers_them():
    from fione.engine.features import ENCODING_ROWS, ENCODING_ROWS_MAX

    assert encoding_rows(1_000_000, 1e-4, 10_000) == ENCODING_ROWS_MAX  # 30 s of 5,000
    assert encoding_rows(1_000_000, 1e-4, 10) == ENCODING_ROWS  # as before: no more than that
    assert ENCODING_ROWS < encoding_rows(1_000_000, 1e-4, 40) < ENCODING_ROWS_MAX
    assert encoding_rows(50_000, 1e-4, 10_000) == 50_000  # never more rows than there are


def _odds(rate):
    """The log-odds of a rate: what a classification's encodings are."""
    return float(np.log(rate / (1 - rate)))


def _amounts(n=20000, seed=0):
    """An amount in cents whose fraction decides the label (a round amount is the risky one)."""
    rng = np.random.default_rng(seed)
    amount = rng.integers(1, 30, n) + rng.integers(0, 100, n) / 100
    cents = np.round((amount - np.floor(amount)) * 100)
    y = (rng.random(n) < np.where(cents == 0, 0.5, 0.05)).astype(int)
    return pd.DataFrame({"amount": amount}), y


def test_encoding_keys_read_the_cents_of_an_amount_but_not_of_a_whole_number():
    X, _ = _amounts()
    X["count"] = np.arange(len(X)) % 50
    kinds = [kind for column, kind in encoding_keys(["amount", "count"], X) if column == "amount"]
    assert "cents" in kinds
    assert ("count", "cents") not in encoding_keys(["amount", "count"], X)
    prices, _ = _prices()  # tenths only: fewer than ENCODING_MIN_LEVELS fractions
    assert ("price", "cents") not in encoding_keys(["price"], prices)


def test_value_encoding_by_cents_gives_the_rate_of_the_fraction():
    X, y = _amounts()
    group = ValueEncoding([("amount", "cents")]).fit(X, y)
    out = group.transform(pd.DataFrame({"amount": [5.0, 5.37, 12.0, np.nan]}))
    rates = out["amount__cents_target"].to_numpy()
    assert rates[0] == pytest.approx(rates[2])  # the same fraction, whatever the whole part
    assert rates[0] > _odds(0.3) > rates[1]  # round amounts are the risky ones
    assert rates[3] == pytest.approx(_odds(y.mean()))


def test_value_encoding_gives_training_rows_rates_that_never_saw_their_own_target():
    X, y = _prices()
    group = ValueEncoding([("price", "value")]).fit(X, y)
    train = group.transform(X)["price__value_target"].to_numpy()
    full = group.transform(X.copy().assign(price=X["price"] + 0.0))["price__value_target"]
    assert np.allclose(train, full)  # a copy of the training rows is still the training rows
    other = group.transform(X.iloc[:50].reset_index(drop=True))["price__value_target"].to_numpy()
    assert not np.allclose(train[:50], other)  # other rows get the rate of all the rows
    # a value that occurs once is given the overall rate (the other folds know nothing of it)
    rng = np.random.default_rng(1)
    prices = np.append(rng.integers(0, 50, 300) / 10, 99.9)
    labels = np.append(rng.integers(0, 2, 300), 1)
    frame = pd.DataFrame({"price": prices})
    one = ValueEncoding([("price", "value")]).fit(frame, labels)
    rates = one.transform(frame)["price__value_target"]
    assert rates.iloc[-1] == pytest.approx(_odds(labels.mean()), abs=1e-5)
    other = one.transform(pd.DataFrame({"price": [99.9]}))["price__value_target"]
    assert other.iloc[0] > rates.iloc[-1]  # a new row with that value gets the rate with its label


def test_value_encoding_reads_a_two_valued_number_as_a_mean_not_a_rate():
    X, _ = _prices()
    y = np.where(np.floor(X["price"].to_numpy()) % 2 == 0, 100.0, 200.0)
    group = ValueEncoding([("price", "whole")]).fit(X, y)
    rates = group.transform(pd.DataFrame({"price": [2.5, 3.5]}))["price__whole_target"]
    assert rates.iloc[0] < 130 < 170 < rates.iloc[1]


def test_value_encoding_gives_unseen_values_the_overall_rate_and_pickles_without_rows():
    X, y = _prices()
    group = ValueEncoding([("price", "whole")]).fit(X, y)
    out = group.transform(pd.DataFrame({"price": [1000.5, np.nan]}))["price__whole_target"]
    assert out.tolist() == pytest.approx([_odds(y.mean())] * 2)
    loaded = pickle.loads(pickle.dumps(group))
    assert loaded._oof is None
    rates = loaded.transform(X.iloc[:5])["price__whole_target"]
    assert rates.tolist() == pytest.approx(
        group.transform(X.iloc[:5])["price__whole_target"].tolist()
    )


def test_prep_fits_a_group_that_reads_the_target_only_when_it_is_given():
    X, y = _prices()
    group = ValueEncoding([("price", "whole")])
    assert Prep().fit(X, [group]).groups == ()
    prep = Prep().fit(X, [group], y)
    assert [g.label for g in prep.groups] == ["target rates of number values"]
    assert prep.tree(X).shape[1] == 3


def test_select_groups_judges_value_encoding_on_more_rows_and_keeps_it_when_it_helps():
    X, y = _prices(60000)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(3600))
    verdict = next(v for v in verdicts if v.group == "target rates of number values")
    assert verdict.adopted and any(isinstance(g, ValueEncoding) for g in kept)


def test_select_groups_does_not_encode_values_for_many_classes_or_grouped_folds():
    X, y = _prices(3000)
    y3 = y + (np.arange(len(y)) % 3 == 0)
    _, verdicts = select_groups(X, y3, "classification", 5, 0, Deadline(60))
    assert all(v.group != "target rates of number values" for v in verdicts)
    groups = np.arange(len(X)) // 6
    _, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(60), row_groups=groups)
    assert all(v.group != "target rates of number values" for v in verdicts)


def test_value_encoding_reads_the_mean_of_a_numeric_target():
    X, _ = _prices()
    y = np.floor(X["price"].to_numpy()) * 2.0 + 100
    group = ValueEncoding([("price", "whole")]).fit(X, y)
    rates = group.transform(pd.DataFrame({"price": [3.5, 10.2]}))["price__whole_target"]
    # the mean of each whole part (106, 120), pulled a little towards the overall mean (about 140)
    assert 106 < rates.iloc[0] < 115 and 120 < rates.iloc[1] < 128


def test_value_encoding_does_not_take_the_training_rows_in_another_order_for_themselves():
    X, y = _prices()
    group = ValueEncoding([("price", "value")]).fit(X, y)
    order = np.random.default_rng(0).permutation(len(X))
    shuffled = group.transform(X.iloc[order].reset_index(drop=True))["price__value_target"]
    straight = group.transform(X)["price__value_target"].to_numpy()
    allrows = group._log_odds(
        X["price"].iloc[order].round(6).map(group._rates[0]).fillna(group._prior).to_numpy()
    )
    allrows = pd.Series(allrows)
    assert np.allclose(shuffled.to_numpy(), allrows.to_numpy())  # the rates of all rows
    assert not np.allclose(shuffled.to_numpy(), straight)  # not the folds' values in their order


def test_automl_keeps_the_value_encoding_honest_and_through_a_save_and_load():
    from sklearn.metrics import roc_auc_score

    X, y = _prices(60000)
    config = TrainConfig(target="label", task="classification", max_runtime_secs=6000, max_models=3)
    model = AutoML(config, families=["LightGBM"]).fit(X.assign(label=y))
    tried = {row["group"]: row for row in model.features}
    assert tried["target rates of number values"]["adopted"]
    fresh_X, fresh_y = _prices(8000, seed=9)
    proba = model.predict_proba(fresh_X)
    auc = roc_auc_score(fresh_y, proba[proba.columns[1]])
    assert abs(auc - model.metrics["auc"]) < 0.02  # the validation did not see its own target
    loaded = pickle.loads(pickle.dumps(model))
    assert np.allclose(loaded.predict_proba(fresh_X).to_numpy(), proba.to_numpy())
