import numpy as np
import pytest

from fione.engine import metrics
from fione.engine.config import ConfigError
from fione.engine.survival import concordance, km_target


def _brute_concordance(time, event, score):
    agree = tied = comparable = 0
    for i in range(len(time)):
        for j in range(len(time)):
            # a censored row lasts as long as an event at its own time
            if event[i] and (time[i] < time[j] or time[i] == time[j] and not event[j]):
                comparable += 1
                agree += score[i] < score[j]
                tied += score[i] == score[j]
    return (agree + 0.5 * tied) / comparable


def test_the_km_target_of_ties_and_a_censored_last_row_by_hand():
    time = np.array([2.0, 3.0, 3.0, 4.0, 5.0, 6.0])
    event = np.array([1, 1, 1, 0, 1, 0])
    # S after t=2: 5/6; after t=3 (2 events of 5 at risk): 1/2; after t=5 (1 of 2): 1/4.
    # The censored row at 4 expects to last until 5, the last event time, where S is 1/4;
    # the one at 6 is past it and stays.
    assert km_target(time, event) == pytest.approx([1 / 6, 1 / 2, 1 / 2, 3 / 4, 3 / 4, 3 / 4])


def test_the_km_target_of_a_censored_first_row_adds_the_expected_rest_of_its_time():
    time = np.array([1.0, 2.0, 3.0, 4.0])
    event = np.array([0, 1, 1, 1])
    # S: 2/3 after 2, 1/3 after 3, 0 after 4. The area under S from 1 to 4 is 1 + 2/3 + 1/3 = 2
    # and S(1) is 1, so the row is taken to last until 3, where S is 1/3.
    assert km_target(time, event) == pytest.approx([2 / 3, 1 / 3, 2 / 3, 1.0])


def test_the_km_target_grows_with_the_time_when_nothing_is_censored():
    time = np.array([5.0, 1.0, 3.0, 2.0])
    target = km_target(time, np.ones(4))
    assert target == pytest.approx([1.0, 0.25, 0.75, 0.5])


@pytest.mark.parametrize("seed", range(4))
def test_concordance_matches_the_pairwise_count_with_ties_and_censoring(seed):
    rng = np.random.default_rng(seed)
    n = 150
    time = rng.integers(1, 30, n).astype(float)  # many equal times
    event = rng.random(n) < 0.6
    score = rng.integers(0, 12, n).astype(float) + 0.0 * time  # many equal scores
    assert concordance(time, event, score) == pytest.approx(_brute_concordance(time, event, score))
    noisy = -time + rng.normal(0, 5, n)
    assert concordance(time, event, noisy) == pytest.approx(_brute_concordance(time, event, noisy))


def test_concordance_by_hand():
    time = np.array([1.0, 2.0, 3.0])
    event = np.array([1, 1, 0])
    assert concordance(time, event, np.array([1.0, 2.0, 3.0])) == 1.0
    assert concordance(time, event, np.array([3.0, 2.0, 1.0])) == 0.0
    assert concordance(time, event, np.zeros(3)) == 0.5
    # the censored row (3) has no event, so only the pairs (1,2), (1,3), (2,3) count: 2 of 3 agree
    assert concordance(time, event, np.array([1.0, 3.0, 2.0])) == pytest.approx(2 / 3)


def test_a_censored_row_at_the_time_of_an_event_lasts_longer_as_in_lifelines():
    time, event = np.array([1.0, 1.0]), np.array([1, 0])
    assert concordance(time, event, np.array([1.0, 2.0])) == 1.0
    assert concordance(time, event, np.array([2.0, 1.0])) == 0.0
    # two events at one time, or two censored rows, are not a pair
    assert np.isnan(concordance(time, np.array([1, 1]), np.array([1.0, 2.0])))
    assert np.isnan(concordance(time, np.array([0, 0]), np.array([1.0, 2.0])))


def test_concordance_without_a_comparable_pair_is_not_a_number():
    assert np.isnan(concordance(np.array([1.0, 2.0]), np.array([0, 0]), np.array([1.0, 2.0])))


def test_the_concordance_metric_reads_a_time_and_an_event_column_and_only_those():
    y = np.column_stack([[1.0, 2.0, 3.0], [1, 1, 0]])
    pred = np.array([1.0, 2.0, 3.0])
    assert metrics.value("concordance", y, pred) == 1.0
    assert "concordance" in metrics.HIGHER_IS_BETTER
    assert metrics.summary("regression", y, pred) == {"concordance": 1.0}
    assert "concordance" not in metrics.summary("regression", y[:, 0], pred)


def test_concordance_is_the_automatic_metric_with_an_event_column_and_only_then():
    assert metrics.resolve("auto", "regression", "sort_metric", None, True) == "concordance"
    assert metrics.resolve("auto", "regression", "sort_metric") == "rmse"
    with pytest.raises(ConfigError, match="needs an event_column"):
        metrics.resolve("concordance", "regression", "sort_metric")
    with pytest.raises(ConfigError, match="must be auto or concordance"):
        metrics.resolve("rmse", "regression", "sort_metric", None, True)
