"""Auditable pricing/statistics primitives. No market prices or NBA values live here."""
from __future__ import annotations

import math
import random
from statistics import fmean
from typing import Callable, Sequence


def finite(value: float) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric observation")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite value")
    return number


def probability(value: float) -> float:
    number = finite(value)
    if not 0 <= number <= 1:
        raise ValueError("Probability must be in [0, 1]")
    return number


def decimal_from_american(odds: float) -> float:
    value = finite(odds)
    if abs(value) < 100:
        raise ValueError("American odds must have magnitude >= 100")
    return 1 + (value / 100 if value > 0 else 100 / -value)


def implied_probability(decimal_odds: float) -> float:
    odds = finite(decimal_odds)
    if odds <= 1:
        raise ValueError("Decimal odds must exceed 1")
    return 1 / odds


def proportional_devig(decimal_odds: Sequence[float]) -> list[float]:
    """Modeling convention, not identification of true probabilities.

    Caller must supply a complete, mutually exclusive outcome set from the same
    operator, line, time and settlement contract. Two unrelated prices are invalid.
    """
    if len(decimal_odds) < 2:
        raise ValueError("Complete outcome set required")
    raw = [implied_probability(d) for d in decimal_odds]
    total = math.fsum(raw)
    return [p / total for p in raw]


def fair_decimal(p_win: float, p_push: float = 0) -> float | None:
    win, push = probability(p_win), probability(p_push)
    if win + push > 1 + 1e-12:
        raise ValueError("Win + push exceeds 1")
    return None if win == 0 else (1 - push) / win


def expected_net(p_win: float, decimal_odds: float, p_push: float = 0) -> float:
    win, push = probability(p_win), probability(p_push)
    implied_probability(decimal_odds)  # validate quoted odds
    if win + push > 1 + 1e-12:
        raise ValueError("Win + push exceeds 1")
    return win * (decimal_odds - 1) - (1 - win - push)


def bernoulli_joint(p_a: float, p_b: float, rho: float) -> float:
    """Exact TWO Bernoulli variables only; not continuous correlation or 3+ legs."""
    a, b, correlation = probability(p_a), probability(p_b), finite(rho)
    if not -1 <= correlation <= 1:
        raise ValueError("Correlation outside [-1, 1]")
    variance = a * (1 - a) * b * (1 - b)
    if variance == 0:
        raise ValueError("Correlation undefined for a constant Bernoulli variable")
    joint = a * b + correlation * math.sqrt(variance)
    lower, upper = max(0, a + b - 1), min(a, b)
    if not lower - 1e-12 <= joint <= upper + 1e-12:
        raise ValueError("Infeasible correlation for these marginals (Fréchet bounds)")
    return min(upper, max(lower, joint))


def paired(x: Sequence[float], y: Sequence[float]) -> tuple[list[float], list[float]]:
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("At least two aligned observations required")
    return [finite(v) for v in x], [finite(v) for v in y]


def pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    a, b = paired(x, y)
    mx, my = fmean(a), fmean(b)
    xx = math.fsum((v - mx) ** 2 for v in a)
    yy = math.fsum((v - my) ** 2 for v in b)
    if xx == 0 or yy == 0:
        return None  # blank, NOT zero
    cov = math.fsum((v - mx) * (w - my) for v, w in zip(a, b))
    return max(-1.0, min(1.0, cov / math.sqrt(xx * yy)))


def ranks(values: Sequence[float]) -> list[float]:
    v = [finite(x) for x in values]
    order = sorted(range(len(v)), key=lambda i: v[i])
    result = [0.0] * len(v)
    start = 0
    while start < len(v):
        stop = start + 1
        while stop < len(v) and v[order[stop]] == v[order[start]]:
            stop += 1
        rank = (start + 1 + stop) / 2
        for i in order[start:stop]:
            result[i] = rank
        start = stop
    return result


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    a, b = paired(x, y)
    return pearson(ranks(a), ranks(b))


def joint_hit_rate(x: Sequence[float], y: Sequence[float]) -> float:
    a, b = paired(x, y)
    if any(v not in (0, 1) for v in a + b):
        raise ValueError("Hit indicators must be binary")
    return fmean(v * w for v, w in zip(a, b))


def quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("Empty quantile")
    ordered = sorted(finite(v) for v in values)
    pos = probability(q) * (len(ordered) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def circular_block_interval(
    x: Sequence[float], y: Sequence[float], statistic: Callable = pearson,
    *, draws: int = 10000, block_length: int = 5, seed: int = 20261103,
    confidence: float = 0.95,
) -> dict:
    """Paired circular moving-block percentile interval on game-order observations.

    Five-game blocks are a sensitivity assumption, NOT proof that remaining
    dependence is absent. A degenerate original statistic stays blank. Invalid
    resamples are counted; too few valid resamples leaves the interval blank.
    This is exploratory, not a selection-adjusted significance procedure.
    """
    a, b = paired(x, y)
    if not isinstance(draws, int) or isinstance(draws, bool) or draws < 100:
        raise ValueError("At least 100 integer resamples required")
    if not isinstance(block_length, int) or isinstance(block_length, bool) or not 1 <= block_length < len(a):
        raise ValueError("Block length must be an integer in [1, n)")
    level = probability(confidence)
    if level in (0, 1):
        raise ValueError("Confidence must be strictly between 0 and 1")
    if statistic(a, b) is None:
        return {"low": None, "high": None, "valid_resamples": 0, "draws": draws}
    rng, samples = random.Random(seed), []
    n = len(a)
    for _ in range(draws):
        indices = []
        while len(indices) < n:
            start = rng.randrange(n)
            indices.extend((start + j) % n for j in range(block_length))
        indices = indices[:n]
        value = statistic([a[i] for i in indices], [b[i] for i in indices])
        if value is not None and math.isfinite(value):
            samples.append(value)
    alpha = (1 - level) / 2
    enough = len(samples) >= 0.95 * draws
    return {"low": quantile(samples, alpha) if enough else None,
            "high": quantile(samples, 1 - alpha) if enough else None,
            "valid_resamples": len(samples), "draws": draws}


def log_loss(outcomes: Sequence[int], probabilities: Sequence[float]) -> float:
    if len(outcomes) != len(probabilities) or not outcomes:
        raise ValueError("Aligned nonempty predictions required")
    terms = []
    for y, p in zip(outcomes, probabilities):
        if y not in (0, 1):
            raise ValueError("Binary outcome required")
        p = probability(p)
        if (y == 1 and p == 0) or (y == 0 and p == 1):
            return math.inf
        terms.append(-math.log(p if y else 1 - p))
    return fmean(terms)


def brier_score(outcomes: Sequence[int], probabilities: Sequence[float]) -> float:
    if len(outcomes) != len(probabilities) or not outcomes:
        raise ValueError("Aligned nonempty predictions required")
    if any(y not in (0, 1) for y in outcomes):
        raise ValueError("Binary outcome required")
    return fmean((probability(p) - y) ** 2 for y, p in zip(outcomes, probabilities))


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values over the ENTIRE registered trial family."""
    p = [probability(v) for v in p_values]
    order = sorted(range(len(p)), key=lambda i: p[i])
    result, previous = [0.0] * len(p), 0.0
    for rank, i in enumerate(order):
        previous = max(previous, min(1.0, (len(p) - rank) * p[i]))
        result[i] = previous
    return result
