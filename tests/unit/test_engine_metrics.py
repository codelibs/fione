import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr
from sklearn import metrics as sk

from fione import i18n
from fione.engine import metrics
from fione.engine.config import _METRICS, ConfigError
from fione.engine.prep import _sorted_labels

RNG = np.random.default_rng(0)


def _probabilities(n, k):
    p = RNG.random((n, k)) ** 3
    return p / p.sum(axis=1, keepdims=True)


def _labels(pred):
    return np.array([RNG.choice(len(row), p=row) for row in pred])


BINARY = _probabilities(300, 2)
BINARY_Y = _labels(BINARY)
MULTI = _probabilities(300, 5)
MULTI_Y = _labels(MULTI)
VALUES = RNG.gamma(2.0, 3.0, 300)
PRED = VALUES * RNG.lognormal(0, 0.3, 300) + 0.5


def test_the_config_names_are_the_registry_and_auto():
    assert _METRICS == {"auto", *metrics.REGISTRY}
    assert set(metrics.ALLOWED["classification"]).isdisjoint(metrics.ALLOWED["regression"])
    assert [metrics.ALLOWED[t][0] for t in metrics.ALLOWED] == ["logloss", "rmse"]


@pytest.mark.parametrize("lang", i18n.LANGUAGES)
def test_every_metric_has_its_words_in_each_language(lang):
    catalog = i18n.catalog(lang)
    for name in metrics.REGISTRY:
        for key in (f"train.metric.{name}", f"metric.{name}", f"metric.{name}.explain"):
            assert catalog.get(key), key


def test_the_labels_agree_between_the_languages_on_the_task():
    en, ja = i18n.catalog("en"), i18n.catalog("ja")
    for name, metric in metrics.REGISTRY.items():
        if name in ("auc", "logloss", "accuracy", "rmse", "mae", "r2"):
            continue
        word_en, word_ja = (
            ("classification", "分類")
            if metric.task == "classification"
            else (
                "regression",
                "回帰",
            )
        )
        assert word_en in en[f"train.metric.{name}"]
        assert word_ja in ja[f"train.metric.{name}"]


@pytest.mark.parametrize(
    "name, reference",
    [
        ("aucpr", lambda y, p, c: sk.average_precision_score(y, p[:, 1])),
        ("gini", lambda y, p, c: 2 * sk.roc_auc_score(y, p[:, 1]) - 1),
        ("accuracy", lambda y, p, c: sk.accuracy_score(y, c)),
        ("balanced_accuracy", lambda y, p, c: sk.balanced_accuracy_score(y, c)),
        ("misclassification", lambda y, p, c: 1 - sk.accuracy_score(y, c)),
        ("mean_per_class_error", lambda y, p, c: 1 - sk.balanced_accuracy_score(y, c)),
        ("f1", lambda y, p, c: sk.f1_score(y, c)),
        ("precision", lambda y, p, c: sk.precision_score(y, c)),
        ("recall", lambda y, p, c: sk.recall_score(y, c)),
        ("mcc", lambda y, p, c: sk.matthews_corrcoef(y, c)),
        ("kappa", lambda y, p, c: sk.cohen_kappa_score(y, c)),
        ("qwk", lambda y, p, c: sk.cohen_kappa_score(y, c, weights="quadratic")),
        ("brier", lambda y, p, c: sk.brier_score_loss(y, p[:, 1])),
    ],
)
def test_two_class_metrics_match_scikit_learn(name, reference):
    picked = BINARY.argmax(axis=1)
    assert metrics.value(name, BINARY_Y, BINARY) == pytest.approx(
        reference(BINARY_Y, BINARY, picked)
    )


@pytest.mark.parametrize(
    "name, reference",
    [
        ("balanced_accuracy", lambda y, p, c: sk.balanced_accuracy_score(y, c)),
        ("f1", lambda y, p, c: sk.f1_score(y, c, average="macro")),
        ("precision", lambda y, p, c: sk.precision_score(y, c, average="macro", zero_division=0)),
        ("recall", lambda y, p, c: sk.recall_score(y, c, average="macro")),
        ("mcc", lambda y, p, c: sk.matthews_corrcoef(y, c)),
        ("kappa", lambda y, p, c: sk.cohen_kappa_score(y, c)),
        ("qwk", lambda y, p, c: sk.cohen_kappa_score(y, c, weights="quadratic")),
        ("top3_accuracy", lambda y, p, c: sk.top_k_accuracy_score(y, p, k=3)),
        ("brier", lambda y, p, c: np.mean(np.sum((p - np.eye(5)[y]) ** 2, axis=1))),
    ],
)
def test_multiclass_metrics_match_scikit_learn(name, reference):
    picked = MULTI.argmax(axis=1)
    assert metrics.value(name, MULTI_Y, MULTI) == pytest.approx(reference(MULTI_Y, MULTI, picked))


def test_map_at_3_and_the_lift_follow_their_definitions():
    pred = np.array([[0.5, 0.3, 0.1, 0.1], [0.1, 0.2, 0.3, 0.4], [0.4, 0.3, 0.2, 0.1]])
    y = np.array([0, 1, 3])  # ranks 1, 3 (0.2 is third), and 4 (outside the top 3)
    assert metrics.value("map3", y, pred) == pytest.approx((1 + 1 / 3 + 0) / 3)
    assert metrics.value("top3_accuracy", y, pred) == pytest.approx(2 / 3)
    scores = np.linspace(0, 1, 20)
    rate = np.zeros(20, dtype=int)
    rate[-2:] = 1  # the two best of twenty are the cases
    both = np.column_stack([1 - scores, scores])
    assert metrics.value("lift_top_group", rate, both) == pytest.approx(1.0 / 0.1)


def test_a_missing_class_does_not_break_the_per_class_means():
    pred = np.array([[0.9, 0.05, 0.05], [0.1, 0.8, 0.1], [0.2, 0.7, 0.1], [0.8, 0.1, 0.1]])
    y = np.array([0, 1, 1, 0])  # the third class occurs nowhere
    for name in ("f1", "precision", "recall", "balanced_accuracy"):
        assert metrics.value(name, y, pred) == pytest.approx(1.0)


def test_the_decision_prior_moves_the_counted_class():
    y = np.array([0, 0, 0, 1])
    pred = np.array([[0.6, 0.4], [0.7, 0.3], [0.6, 0.4], [0.6, 0.4]])
    assert metrics.value("recall", y, pred) == 0.0
    assert metrics.value("recall", y, pred, np.array([0.75, 0.25])) == 1.0


def test_qwk_orders_the_classes_by_their_numbers_not_their_text():
    labels = _sorted_labels(pd.Series([2, 10, 1, 12, 3, 11]))
    assert labels == [1, 2, 3, 10, 11, 12]
    k = 12
    y = np.repeat(np.arange(k), 5)
    near = np.eye(k)[np.clip(y + 1, 0, k - 1)]
    far = np.eye(k)[(y + 6) % k]
    assert metrics.value("qwk", y, near) > metrics.value("qwk", y, far)
    assert metrics.value("kappa", y, near) == pytest.approx(metrics.value("kappa", y, far), abs=0.1)


@pytest.mark.parametrize(
    "name, reference",
    [
        ("mse", lambda y, p: sk.mean_squared_error(y, p)),
        ("rmsle", lambda y, p: np.sqrt(sk.mean_squared_log_error(y, p))),
        ("mape", lambda y, p: sk.mean_absolute_percentage_error(y, p)),
        ("medae", lambda y, p: sk.median_absolute_error(y, p)),
        ("explained_variance", lambda y, p: sk.explained_variance_score(y, p)),
        ("pearson", lambda y, p: np.corrcoef(y, p)[0, 1]),
        ("spearman", lambda y, p: spearmanr(y, p).statistic),
        ("poisson", lambda y, p: sk.mean_poisson_deviance(y, p)),
        ("smape", lambda y, p: np.mean(2 * np.abs(y - p) / (np.abs(y) + np.abs(p)))),
        ("rmspe", lambda y, p: np.sqrt(np.mean(((y - p) / y) ** 2))),
    ],
)
def test_regression_metrics_match_their_definitions(name, reference):
    assert metrics.value(name, VALUES, PRED) == pytest.approx(reference(VALUES, PRED))


def test_normalized_gini_is_one_for_the_right_order_and_zero_for_a_constant():
    y = np.array([0.0, 1.0, 3.0, 0.0, 7.0, 2.0])
    assert metrics.value("normalized_gini", y, y * 5 + 1) == pytest.approx(1.0)
    assert metrics.value("normalized_gini", y, np.zeros(6)) == pytest.approx(
        metrics.value("normalized_gini", y, np.ones(6))
    )
    assert metrics.value("normalized_gini", y, -y) < 0


def test_rating_cuts_serve_rounded_qwk_where_the_predictions_are_squeezed():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 4, 600).astype(float)
    pred = 0.4 * y + 0.5 + rng.normal(0, 0.12, 600)  # 0.5..1.7: rounding never reaches 3
    cuts = metrics.tune_rating_cuts(y, pred)
    assert isinstance(cuts, metrics.Cuts) and len(cuts) == 4 and cuts[0] == 0  # low + 3 cuts
    assert list(cuts[1:]) == sorted(cuts[1:])
    plain = metrics.value("rounded_qwk", y, pred)
    fitted = metrics.value("rounded_qwk", y, pred, cuts)
    assert fitted > plain + 0.3
    assert metrics.tune_prior("rounded_qwk", y, pred)[0] == 0  # tune_prior serves a regression
    # a subset without the lowest rating still counts its ratings by the same cut points
    kept = y > 0
    assert np.isfinite(metrics.value("rounded_qwk", y[kept], pred[kept], cuts))


def test_rounded_qwk_rounds_inside_the_range_of_the_ratings():
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 3.0])
    assert metrics.value("rounded_qwk", y, y + 0.2) == pytest.approx(1.0)
    assert metrics.value("rounded_qwk", y, y + 40.0) < 1.0  # clipped to 5, not counted as far
    assert metrics.value("rounded_qwk", y, y + 0.2) > metrics.value("rounded_qwk", y, y[::-1])


def test_smape_counts_the_rows_with_two_zeros_as_no_error():
    assert metrics.value("smape", np.array([0.0, 2.0]), np.array([0.0, 1.0])) == pytest.approx(
        (0 + 2 / 3) / 2
    )


def test_a_metric_reports_its_direction_through_loss():
    for name, metric in metrics.REGISTRY.items():
        assert (name in metrics.HIGHER_IS_BETTER) == metric.higher_is_better
    p = np.array([[0.9, 0.1], [0.2, 0.8], [0.3, 0.7], [0.6, 0.4]])
    y = np.array([0, 1, 1, 0])
    for name in metrics.ALLOWED["classification"]:
        if name in ("top3_accuracy", "map3"):
            continue
        assert metrics.loss(name, y, p) <= metrics.loss(name, y, p[:, ::-1]), name


def test_an_undefined_value_is_the_worst_loss():
    y = np.zeros(4, dtype=int)
    assert metrics.loss("kappa", y, np.eye(2)[y]) == float("inf")
    assert metrics.loss("pearson", np.ones(4), np.arange(4.0)) == float("inf")


@pytest.mark.parametrize(
    "name, y, classes",
    [
        ("rmsle", np.array([-1.0, 2.0]), 0),
        ("poisson", np.array([-1.0, 2.0]), 0),
        ("normalized_gini", np.array([-1.0, 2.0]), 0),
        ("mape", np.array([0.0, 2.0]), 0),
        ("rounded_qwk", np.array([0.5, 2.0]), 0),
        ("top3_accuracy", np.array([0, 1]), 3),
        ("map3", np.array([0, 1]), 2),
        ("normalized_gini", np.array([3.0, 3.0]), 0),
    ],
)
def test_check_rejects_a_target_the_metric_is_not_defined_for(name, y, classes):
    with pytest.raises(ConfigError, match=name):
        metrics.check(name, y, classes, "sort_metric")


def test_check_accepts_a_target_it_fits():
    metrics.check("rmsle", np.array([0.0, 2.0]), 0, "sort_metric")
    metrics.check("top3_accuracy", np.array([0, 1]), 4, "sort_metric")
    metrics.check("rounded_qwk", np.array([1.0, 5.0]), 0, "sort_metric")


def test_resolve_accepts_every_registered_name_for_its_task_only():
    for name, metric in metrics.REGISTRY.items():
        assert metrics.resolve(name.upper(), metric.task, "sort_metric") == name
        other = "regression" if metric.task == "classification" else "classification"
        with pytest.raises(ConfigError):
            metrics.resolve(name, other, "sort_metric")


def test_tied_predictions_give_no_credit_and_do_not_depend_on_the_row_order():
    flat = np.full((4, 5), 0.2)
    assert metrics.value("top3_accuracy", np.array([4, 3, 2, 0]), flat) == pytest.approx(
        0.6 / 3 * 0 + 0.25 * 0 + 0.0
    )
    spike = np.tile([1.0, 0, 0, 0, 0], (4, 1))  # zeros tie: only the first class is ranked
    y = np.array([4, 3, 2, 0])
    assert metrics.value("top3_accuracy", y, spike) == pytest.approx(0.25)
    assert metrics.value("map3", y, spike) == pytest.approx(0.25)
    constant = np.tile([0.7, 0.3], (20, 1))
    for positives in (slice(0, 2), slice(18, 20)):
        answers = np.zeros(20, dtype=int)
        answers[positives] = 1
        assert metrics.value("lift_top_group", answers, constant) == pytest.approx(1.0)
    for answers in (np.arange(6.0, 0, -1), np.arange(1.0, 7)):
        assert metrics.value("normalized_gini", answers, np.full(6, 3.0)) == pytest.approx(0.0)


def test_map_at_3_is_defined_for_three_classes_and_top_3_is_not():
    metrics.check("map3", np.array([0, 1, 2]), 3, "sort_metric")
    with pytest.raises(ConfigError, match="top3_accuracy"):
        metrics.check("top3_accuracy", np.array([0, 1, 2]), 3, "sort_metric")


def test_tune_prior_picks_the_threshold_that_serves_the_metric():
    y = np.array([0] * 90 + [1] * 10)
    p1 = np.concatenate([np.linspace(0.0, 0.5, 90), np.linspace(0.3, 0.9, 10)])
    pred = np.column_stack([1 - p1, p1])
    prior = metrics.tune_prior("f1", y, pred)
    assert prior.sum() == pytest.approx(1.0) and (prior > 0).all()
    tuned = metrics.value("f1", y, pred, prior)
    assert tuned > metrics.value("f1", y, pred)  # at 0.5 almost nothing is predicted
    for t in np.linspace(0.05, 0.95, 19):  # no other threshold does better
        assert tuned >= metrics.value("f1", y, pred, np.array([1 - t, t])) - 1e-12
    picked = metrics.choose(pred, prior)
    assert (picked == (p1 > prior[1]).astype(int)).all()


def test_only_metrics_that_count_right_answers_can_be_tuned():
    assert "f1" in metrics.TUNABLE and "qwk" in metrics.TUNABLE
    assert not {"logloss", "auc", "precision", "recall", "brier"} & metrics.TUNABLE
    assert metrics.TUNABLE <= set(metrics.ALLOWED["classification"])


@pytest.mark.parametrize("name", sorted(metrics.TUNABLE))
def test_tune_prior_is_the_best_threshold_by_brute_force(name):
    rng = np.random.default_rng(3)
    y = (rng.random(400) < 0.2).astype(int)
    p1 = np.round(np.clip(0.15 + 0.5 * y + rng.normal(0, 0.25, 400), 0.01, 0.99), 1)  # many ties
    pred = np.column_stack([1 - p1, p1])
    prior = metrics.tune_prior(name, y, pred)
    best = metrics.loss(name, y, pred, prior)
    # every cut of the distinct probabilities, none and all predicted positive included
    cuts = np.concatenate([[1.0], np.unique(p1)[::-1], [0.0]])
    others = [
        metrics.loss(name, y, pred, np.array([1 - t, t]))
        for t in (cuts[:-1] + cuts[1:]) / 2
        if 0 < t < 1
    ]
    assert best <= min(others) + 1e-9
    assert not ((p1 == prior[1]).any())  # no row sits on the threshold


def test_tune_prior_can_predict_nothing_or_everything():
    y = np.array([0, 0, 0, 0, 1])
    flat = np.tile([0.8, 0.2], (5, 1))
    assert metrics.tune_prior("accuracy", y, flat)[1] > 0.2  # nothing is positive
    y = np.array([1, 1, 1, 1, 0])
    assert metrics.tune_prior("f1", y, flat)[1] < 0.2  # everything is positive


def test_check_tuned_wants_two_classes_and_a_metric_that_counts_right_answers():
    metrics.check_tuned("f1", 2)
    with pytest.raises(ConfigError, match="two classes"):
        metrics.check_tuned("f1", 3)
    for name in ("logloss", "aucpr", "recall"):
        with pytest.raises(ConfigError, match="sort_metric"):
            metrics.check_tuned(name, 2)


def _ordinal(n=3000, k=5, seed=0):
    """Answers 0..k-1 and probabilities that centre on the answer but lean to the middle classes
    (the most probable class is often not the nearest one in order)."""
    rng = np.random.default_rng(seed)
    y = rng.integers(0, k, n)
    score = y + rng.normal(scale=1.2, size=n)
    logits = -((score[:, None] - np.arange(k)[None]) ** 2) / 2.0
    logits[:, k // 2] += 1.2
    pred = np.exp(logits)
    return y, pred / pred.sum(axis=1, keepdims=True)


def test_cuts_choose_the_class_the_expected_class_number_falls_in():
    pred = np.array([[0.7, 0.2, 0.1], [0.1, 0.2, 0.7], [0.2, 0.6, 0.2], [0.4, 0.3, 0.3]])
    cuts = np.array([0.5, 1.5]).view(metrics.Cuts)
    # the expected class numbers are 0.4, 1.6, 1.0 and 0.9
    assert metrics.choose(pred, cuts).tolist() == [0, 2, 1, 1]
    assert metrics.choose(pred).tolist() == [0, 2, 1, 0]


def test_tune_prior_for_qwk_fits_cut_points_that_beat_the_most_probable_class():
    y, pred = _ordinal()
    cuts = metrics.tune_prior("qwk", y, pred)
    assert isinstance(cuts, metrics.Cuts) and len(cuts) == 4 and (np.diff(cuts) > 0).all()
    assert metrics.value("qwk", y, pred, cuts) > metrics.value("qwk", y, pred) + 0.03
    # no single cut point moved a little makes it better
    best = metrics.value("qwk", y, pred, cuts)
    for i in range(4):
        for step in (-0.05, 0.05):
            moved = np.array(cuts, dtype=float)
            moved[i] += step
            if (np.diff(moved) > 0).all():
                assert metrics.value("qwk", y, pred, moved.view(metrics.Cuts)) <= best + 1e-9


def test_check_tuned_allows_many_ordered_classes_for_qwk_only():
    metrics.check_tuned("qwk", 5)
    with pytest.raises(ConfigError, match="two classes"):
        metrics.check_tuned("qwk", metrics.MAX_ORDINAL_CLASSES + 1)
    with pytest.raises(ConfigError, match="two classes"):
        metrics.check_tuned("kappa", 5)


def test_relative_weights_of_a_log1p_target_are_flat_where_the_target_is_large():
    y = np.array([0.001, 0.01, 0.1, 1.0, 10.0, 1000.0, 5000.0, 20000.0])
    plain = metrics.relative_weight(y, "rmspe")
    logged = metrics.relative_weight(y, "rmspe", log1p=True)
    assert plain[3] / plain[-1] > 1e6
    assert logged[3] / logged[-1] < 10  # y = 1 against y = 20000: the log1p already did the rest
    assert logged[0] > logged[-1]  # a target near 0 still weighs most
    assert logged.mean() == pytest.approx(1.0)


def test_relative_weights_have_mean_one_and_cap_the_targets_near_zero():
    y = np.concatenate([np.linspace(1.0, 2.0, 999), [1e-9]])
    for name, power in (("rmspe", 2), ("mape", 1)):
        weight = metrics.relative_weight(y, name)
        assert weight.mean() == pytest.approx(1.0)
        ratio = weight[500] / weight[998]
        assert ratio == pytest.approx((y[998] / y[500]) ** power)  # a row weighs 1 / y ** power
        assert weight[999] == weight.max() < 100  # capped, not 1e18
