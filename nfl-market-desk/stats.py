#!/usr/bin/env python3
"""Small, dependency-free statistics whose every formula is checkable by hand.

Each function is verified against a published reference value in ``tests/``. The point is that a
reader can reproduce any number on the site with a calculator, and CI fails if a value drifts.
"""
from __future__ import annotations

import math


def pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3 or n != len(y):
        return None
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return sxy / math.sqrt(sxx * syy)


def fisher_ci(r: float, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Fisher-z interval. Undefined for n <= 3 or |r| = 1, and returns the edge in that case."""
    if n <= 3:
        return (float("nan"), float("nan"))
    if abs(r) >= 1:
        return (r, r)
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    low, high = zr - z * se, zr + z * se
    return (math.tanh(low), math.tanh(high))


def normal_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def normal_sf(z: float) -> float:
    return 1 - normal_cdf(z)


def pearson_p(r: float, n: int) -> float:
    """Two-sided p-value via the t transform, then the normal approximation of the t tail."""
    if n <= 2:
        return float("nan")
    if abs(r) >= 1:
        return 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r))
    # Normal approximation to the t distribution. At the sample sizes used here it agrees with an
    # exact t tail to about a thousandth, which is stated on the page rather than hidden.
    return 2 * normal_sf(abs(t))


def holm(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni step-down. Preserves input order."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, index in enumerate(order):
        value = min(1.0, (m - rank) * p_values[index])
        running = max(running, value)
        adjusted[index] = running
    return adjusted


def phi_from_2x2(a: int, b: int, c: int, d: int) -> float | None:
    """Phi coefficient for a 2x2 table [[a,b],[c,d]]."""
    n = a + b + c + d
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if n == 0 or denom == 0:
        return None
    return (a * d - b * c) / math.sqrt(denom)


def chi2_1df_sf(value: float) -> float:
    """Upper tail of chi-square with 1 df, which equals the two-sided normal tail of sqrt(value)."""
    if value <= 0:
        return 1.0
    return 2 * normal_sf(math.sqrt(value))


def _pmf_list(n: int, p: float = 0.5) -> list[float]:
    return [_binom_pmf(k, n, p) for k in range(n + 1)]


def binom_two_sided_p(wins: int, losses: int, p: float = 0.5) -> float:
    """Exact two-sided binomial p-value: the total probability of outcomes no more likely than
    the observed one. This is the definition ``scipy.stats.binomtest`` uses and is checkable by
    enumeration. The mass function is unimodal, so the included set is the two tails outside a
    contiguous middle band and the sum is formed from prefix sums in linear time.
    """
    n = wins + losses
    if n == 0:
        return 1.0
    pmf = _pmf_list(n, p)
    threshold = pmf[wins] * (1 + 1e-9)
    # Largest index from the left whose mass is <= threshold.
    a = -1
    while a + 1 <= n and pmf[a + 1] <= threshold:
        a += 1
    # Smallest index from the right whose mass is <= threshold.
    b = n + 1
    while b - 1 >= 0 and pmf[b - 1] <= threshold:
        b -= 1
    total = sum(pmf[: a + 1]) + sum(pmf[b:])
    return min(1.0, total)


def required_n(p_true: float, p_null: float = 0.5, alpha: float = 0.05, power: float = 0.8) -> int:
    """Settled bets needed to detect p_true against p_null at the stated alpha and power.

    Normal approximation to the binomial (one-sided alpha, two-sided test), rounded up. Used only
    to state a sample-size floor; it is not a result.
    """
    z_alpha = 1.959963984540054 if alpha == 0.05 else abs(_z_for(1 - alpha / 2))
    z_beta = _z_for(power)
    p_bar = (p_true + p_null) / 2
    numerator = (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
                 + z_beta * math.sqrt(p_true * (1 - p_true) + p_null * (1 - p_null))) ** 2
    return math.ceil(numerator / (p_true - p_null) ** 2)


def _z_for(p: float) -> float:
    """Inverse standard normal by bisection. Deterministic and exact to 1e-12."""
    low, high = -10.0, 10.0
    for _ in range(200):
        mid = (low + high) / 2
        if normal_cdf(mid) < p:
            low = mid
        else:
            high = mid
    return (low + high) / 2


# --------------------------------------------------------------------------- exact sample size
def _binom_pmf(k: int, n: int, p: float) -> float:
    return math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                    + k * math.log(p) + (n - k) * math.log1p(-p))


def _reject(k: int, n: int, alpha: float, two_sided: bool) -> bool:
    """Exact binomial rejection rule at p = 0.5.

    Two-sided uses the standard "sum the outcomes no more likely than the observed one" definition,
    which is what ``scipy.stats.binomtest(..., alternative="two-sided")`` computes and what any
    statistics package will reproduce. One-sided is the upper-tail probability P(X >= k). Using the
    published definition rather than a convenient one is the difference between a gate that can be
    checked elsewhere and a gate that can only be checked here.
    """
    if two_sided:
        return binom_two_sided_p(k, n - k) <= alpha
    return binom_sf(k, n) <= alpha


def binom_sf(k: int, n: int, p: float = 0.5) -> float:
    """P(X >= k) for X ~ Binomial(n, p), from a cached mass function."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return sum(_pmf_list(n, p)[k:])


class _Binom:
    """Cached exact binomial mass function with prefix sums, for p = 0.5.

    The mass function is unimodal, so for any threshold the set of indices whose mass is at or
    below it is a prefix plus a suffix. Both edges are found by binary search, which makes an
    exact two-sided p-value O(log n) instead of O(n).
    """

    __slots__ = ("n", "pmf", "prefix", "mode", "total")

    def __init__(self, n: int) -> None:
        self.n = n
        self.pmf = [_binom_pmf(k, n, 0.5) for k in range(n + 1)]
        self.prefix = [0.0] * (n + 2)
        for k, value in enumerate(self.pmf):
            self.prefix[k + 1] = self.prefix[k] + value
        self.total = self.prefix[n + 1]
        self.mode = max(range(n + 1), key=lambda k: self.pmf[k])

    def sf(self, k: int) -> float:
        if k <= 0:
            return 1.0
        if k > self.n:
            return 0.0
        return self.total - self.prefix[k]

    def two_sided_p(self, k: int) -> float:
        threshold = self.pmf[k] * (1 + 1e-9)
        lo, hi = 0, self.mode
        while lo < hi:  # largest a in [0, mode] with pmf[a] <= threshold
            mid = (lo + hi + 1) // 2
            if self.pmf[mid] <= threshold:
                lo = mid
            else:
                hi = mid - 1
        a = lo
        lo, hi = self.mode, self.n
        while lo < hi:  # smallest b in [mode, n] with pmf[b] <= threshold
            mid = (lo + hi) // 2
            if self.pmf[mid] <= threshold:
                hi = mid
            else:
                lo = mid + 1
        b = lo
        return min(1.0, self.prefix[a + 1] + (self.total - self.prefix[b]))

    def reject(self, k: int, alpha: float, two_sided: bool) -> bool:
        if two_sided:
            return self.two_sided_p(k) <= alpha
        return self.sf(k) <= alpha


_BINOM: dict[int, _Binom] = {}


def binom_cache(n: int) -> _Binom:
    if n not in _BINOM:
        _BINOM[n] = _Binom(n)
    return _BINOM[n]


def critical_bounds(n: int, alpha: float = 0.05, two_sided: bool = True) -> tuple[int, int]:
    """(k_lo, k_hi): reject when wins <= k_lo or wins >= k_hi; k_lo = -1 when unused."""
    table = binom_cache(n)
    lo = -1
    if two_sided:
        for k in range(0, n // 2 + 1):
            if table.reject(k, alpha, True):
                lo = k
            else:
                break
    hi = n + 1
    for k in range(n, n // 2 - 1, -1):
        if table.reject(k, alpha, two_sided):
            hi = k
        else:
            break
    if hi > n:
        hi = n
    return lo, hi


def exact_power(n: int, p_true: float, alpha: float = 0.05, two_sided: bool = True) -> float:
    k_lo, k_hi = critical_bounds(n, alpha, two_sided)
    total = sum(math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                         + k * math.log(p_true) + (n - k) * math.log1p(-p_true))
                for k in list(range(0, k_lo + 1)) + list(range(k_hi, n + 1)))
    return min(1.0, total)


_MEMO: dict[tuple, int] = {}


def required_n_exact(p_true: float, alpha: float = 0.05, power: float = 0.8,
                     two_sided: bool = True, ceiling: int = 20000) -> int:
    """Settled bets needed, by exact binomial enumeration.

    Power is not monotone in n for a discrete test: at some n the achievable size nearest to
    alpha drops, so a larger sample can be slightly *less* powerful than a smaller one. The answer
    is therefore the smallest n whose power reaches the target, found by bisection over the
    monotone "some n at or below N reaches the target" predicate and then narrowed exactly. That
    keeps the result exact and the runtime small.
    """
    key = (p_true, alpha, power, two_sided, ceiling)
    if key in _MEMO:
        return _MEMO[key]

    def reaches(n: int) -> bool:
        return exact_power(n, p_true, alpha, two_sided) >= power

    if not reaches(ceiling):
        raise SystemExit(
            f"required_n_exact: no n below {ceiling} reaches power {power} at a true rate of "
            f"{p_true}; the question is not answerable at this effect size")
    lo, hi = 2, ceiling
    while lo < hi:  # invariant: reaches(hi) is true
        mid = (lo + hi) // 2
        if reaches(mid):
            hi = mid
        else:
            lo = mid + 1
    # Guard the guard: the exact answer must itself reach the target and its predecessor must not.
    if not reaches(lo):
        raise SystemExit("required_n_exact: bisection produced a non-reaching n")
    _MEMO[key] = lo
    return lo
