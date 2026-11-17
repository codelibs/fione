"""Right-censored time targets: the regression target the models learn and the concordance index.

A survival table has a time and an event flag per row (1: the event happened at that time,
0: the row was last seen at that time and the event may come later). ``km_target`` turns the two
into one number a regression can learn, ``concordance`` scores how well a prediction orders the
rows by time, counting only the pairs the censoring leaves comparable.
"""

import numpy as np


def km_target(time: np.ndarray, event: np.ndarray) -> np.ndarray:
    """The Kaplan-Meier probability that the event has happened by a row's time, ``1 - S(t)``,
    per row: a number from 0 to 1 that grows with the time, so the larger it is the longer
    the row lasted.

    The curve ``S`` is that of all the rows given. A row with an event is at its own time. A
    censored row is at its time plus what remains of the expected time to the event: the area
    under ``S`` from its time up to the last event time (the curve is not known beyond), divided
    by ``S`` at its time. A censored row at or after the last event time stays at its time."""
    event = event.astype(bool)
    knots, events = np.unique(time[event], return_counts=True)
    at_risk = len(time) - np.searchsorted(np.sort(time), knots, side="left")
    after = np.cumprod(1.0 - events / at_risk)  # S just after each knot
    # area[i]: the area under S from the first knot to knot i
    area = np.concatenate([[0.0], np.cumsum(after[:-1] * np.diff(knots))])

    def curve(x: np.ndarray) -> np.ndarray:
        return np.concatenate([[1.0], after])[np.searchsorted(knots, x, side="right")]

    def integral(x: np.ndarray) -> np.ndarray:
        k = np.searchsorted(knots, x, side="right")  # knots up to x
        before = np.maximum(k - 1, 0)
        return np.where(k == 0, x - knots[0], area[before] + after[before] * (x - knots[before]))

    last = knots[-1]
    reach = time.astype(float).copy()
    open_ = ~event & (time < last)
    reach[open_] += (integral(np.array([last]))[0] - integral(time[open_])) / curve(time[open_])
    return 1.0 - curve(reach)


def concordance(time: np.ndarray, event: np.ndarray, score: np.ndarray) -> float:
    """Harrell's C-index: of the pairs where one row has its event before the other row's time,
    the share the score puts in the order of the times, a row with the larger score lasting
    longer; a pair with equal scores counts half. A censored row is taken to last beyond an
    event at its own time, so that pair counts too (as in lifelines); two events at one time,
    and two censored rows, do not. NaN when no pair is comparable. It sorts by time and counts
    the pairs with a Fenwick tree over the ranks of the scores: O(n log n)."""
    event = event.astype(bool)
    _, rank = np.unique(score, return_inverse=True)
    size = int(rank.max()) + 1 if len(rank) else 0
    tree = [0] * (size + 1)

    def count_upto(i: int) -> int:  # rows inserted with a rank of at most i - 1
        total = 0
        while i > 0:
            total += tree[i]
            i -= i & -i
        return total

    def insert(rank_of_row: int) -> None:
        j = rank_of_row + 1
        while j <= size:
            tree[j] += 1
            j += j & -j

    order = np.argsort(-time, kind="stable")  # the latest first
    ranks, events = rank[order].tolist(), event[order].tolist()
    ends = (np.flatnonzero(np.diff(time[order]) != 0) + 1).tolist() + [len(order)]
    agree = tied = comparable = inserted = start = 0
    for end in ends:  # a block of equal times: its events are asked against the rows after them
        for i in range(start, end):
            if not events[i]:  # a censored row lasts as long as the events of its block
                insert(ranks[i])
                inserted += 1
        for i in range(start, end):
            if events[i]:
                below, up_to = count_upto(ranks[i]), count_upto(ranks[i] + 1)
                agree += inserted - up_to
                tied += up_to - below
                comparable += inserted
        for i in range(start, end):
            if events[i]:
                insert(ranks[i])
                inserted += 1
        start = end
    return (agree + 0.5 * tied) / comparable if comparable else float("nan")
