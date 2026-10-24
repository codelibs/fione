import numpy as np
import pandas as pd
import pytest
from predict_models import LABELS, classifier, features, regressor

from fione.predict import PredictInputError, batch_predict, predict_chunks

PROBA = [f"p_{label}" for label in sorted(LABELS)]


@pytest.fixture(scope="module")
def cls():
    return classifier()


@pytest.fixture(scope="module")
def reg():
    return regressor()


def test_columns_are_prediction_then_probabilities_then_the_inputs(cls):
    df = features()
    out = batch_predict(cls, df)
    assert list(out.columns) == ["predict", *PROBA, *df.columns]
    assert set(out["predict"]) <= set(LABELS)
    pd.testing.assert_frame_equal(out[list(df.columns)], df.reset_index(drop=True))


def test_predictions_equal_the_models_own(cls):
    df = features(50)
    out = batch_predict(cls, df)
    assert (out["predict"] == cls.predict(df).to_numpy()).all()
    np.testing.assert_allclose(out[PROBA].to_numpy(), cls.predict_proba(df).to_numpy())


def test_probabilities_sum_to_one(cls):
    out = batch_predict(cls, features(100))
    assert np.allclose(out[PROBA].sum(axis=1), 1.0, atol=1e-6)


def test_row_order_and_count_follow_the_input_whatever_its_index(cls):
    df = features(30)
    df.index = np.random.default_rng(0).permutation(np.arange(100, 130))
    out = batch_predict(cls, df)
    assert list(out.index) == list(range(30))
    expected = cls.predict(df.reset_index(drop=True))
    assert (out["predict"] == expected).all()
    assert (out["x"].to_numpy() == df["x"].to_numpy()).all()


def test_a_duplicated_index_is_handled_positionally(cls):
    df = features(10)
    df.index = [0] * 10
    out = batch_predict(cls, df)
    assert len(out) == 10 and list(out.index) == list(range(10))


def test_missing_columns_are_all_listed(cls):
    df = features().drop(columns=["x", "color"])
    with pytest.raises(PredictInputError) as e:
        batch_predict(cls, df)
    assert str(e.value) == "missing columns: ['x', 'color']"


def test_missing_columns_are_reported_for_an_empty_frame_too(cls):
    with pytest.raises(PredictInputError, match="missing columns"):
        batch_predict(cls, features().drop(columns=["x"]).iloc[:0])


def test_extra_columns_are_ignored_by_the_model_but_kept_in_the_output(cls):
    df = features()
    plain = batch_predict(cls, df)
    extra = df.assign(note="n", 番号=range(len(df)))
    out = batch_predict(cls, extra)
    assert list(out.columns) == ["predict", *PROBA, *extra.columns]
    pd.testing.assert_frame_equal(out[plain.columns], plain)
    assert list(out["番号"]) == list(range(len(df)))


def test_an_unseen_category_predicts_without_error(cls):
    df = features(10)
    df.loc[0, "color"] = "purple"
    df.loc[1, "color"] = None
    out = batch_predict(cls, df)
    assert len(out) == 10 and out["predict"].isin(LABELS).all()
    assert out.loc[0, "color"] == "purple"


def test_a_string_in_a_numeric_column_names_the_column_and_the_values(cls):
    df = features(10).astype({"x": object})
    df.loc[2, "x"] = "abc"
    df.loc[5, "x"] = "n/a"
    with pytest.raises(PredictInputError) as e:
        batch_predict(cls, df)
    message = str(e.value)
    assert "'x'" in message and "'abc'" in message and "'n/a'" in message


def test_at_most_three_offending_values_are_shown(cls):
    df = features(10).astype({"幅": object})
    df["幅"] = [f"bad{i}" for i in range(10)]
    with pytest.raises(PredictInputError) as e:
        batch_predict(cls, df)
    message = str(e.value)
    assert "'幅'" in message and "bad0" in message and "bad2" in message and "bad3" not in message


def test_numbers_written_as_text_and_missing_values_are_not_errors(cls):
    df = features(10).astype({"x": object})
    df["x"] = ["1.5", None, *["0.2"] * 8]
    assert len(batch_predict(cls, df)) == 10


def test_a_bad_value_in_a_later_chunk_fails_before_any_prediction(cls):
    df = features(30).astype({"x": object})
    df.loc[29, "x"] = "oops"
    with pytest.raises(PredictInputError, match="oops"):
        predict_chunks(cls, df, chunk_rows=7)


def test_include_columns_picks_and_orders_the_inputs(cls):
    df = features()
    out = batch_predict(cls, df, ["color", "x"])
    assert list(out.columns) == ["predict", *PROBA, "color", "x"]
    assert out["color"].tolist() == df["color"].tolist()


def test_no_input_columns_can_be_requested(cls):
    out = batch_predict(cls, features(), [])
    assert list(out.columns) == ["predict", *PROBA]


def test_unknown_include_columns_are_rejected(cls):
    with pytest.raises(PredictInputError) as e:
        batch_predict(cls, features(), ["x", "nope", "zzz"])
    assert str(e.value) == "unknown columns in include_columns: ['nope', 'zzz']"


def test_input_columns_that_collide_with_outputs_are_renamed(cls):
    df = features(10).assign(predict="mine", **{"p_良": 1, "input_predict": "taken"})
    out = batch_predict(cls, df)
    assert list(out.columns) == [
        "predict",
        *PROBA,
        "x",
        "幅",
        "color",
        "input_predict_2",
        "input_p_良",
        "input_predict",
    ]
    assert (out["input_predict_2"] == "mine").all()
    assert (out["input_predict"] == "taken").all()
    assert (out["input_p_良"] == 1).all()
    assert out["predict"].isin(LABELS).all()


def test_chunking_does_not_change_the_output(cls):
    df = features(53)
    df.index = np.arange(53)[::-1]
    whole = batch_predict(cls, df, chunk_rows=10_000)
    pieces = list(predict_chunks(cls, df, chunk_rows=7))
    assert [len(p) for p in pieces] == [7] * 7 + [4]
    pd.testing.assert_frame_equal(batch_predict(cls, df, chunk_rows=7), whole)
    pd.testing.assert_frame_equal(pd.concat(pieces, ignore_index=True), whole)


def test_an_empty_frame_gives_an_empty_frame_with_the_columns(cls):
    df = features().iloc[:0]
    out = batch_predict(cls, df)
    assert len(out) == 0 and list(out.columns) == ["predict", *PROBA, *df.columns]
    assert len(list(predict_chunks(cls, df))) == 1


def test_japanese_names_and_labels_survive(cls):
    out = batch_predict(cls, features(), ["幅"])
    assert list(out.columns)[:4] == ["predict", "p_悪", "p_普通", "p_良"]
    assert "幅" in out.columns and out["predict"].isin(LABELS).all()


def test_a_regression_model_gives_only_predict(reg):
    df = features()
    out = batch_predict(reg, df)
    assert list(out.columns) == ["predict", *df.columns]
    assert out["predict"].dtype == float
    assert np.allclose(out["predict"], reg.predict(df))


def test_chunk_rows_must_be_positive(cls):
    with pytest.raises(ValueError, match="chunk_rows"):
        batch_predict(cls, features(), chunk_rows=0)
