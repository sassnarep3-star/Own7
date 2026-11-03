"""Separating skill from luck. Tests, not vibes.

The single most common way a betting strategy fooled its author is a hot
streak. This module implements the standard battery for deciding whether a
record is distinguishable from chance:

1. ``binomial_p_value`` - is the win rate above the break-even rate the prices
   implied? One-sided exact binomial test.
2. ``probabilistic_sharpe_ratio`` - Bailey & Lopez de Prado's PSR, which asks
   "what is the probability the true Sharpe ratio is positive, given this track
   record, its sample size and its skew and kurtosis?" This is the correct
   correction for the fact that short track records with fat tails look good
   by accident.
3. ``deflated_sharpe_ratio`` - PSR adjusted for the number of strategies tried.
   If you test 200 ideas and keep the best, the best one's Sharpe must be
   discounted by the expected maximum of 200 null Sharpes.
4. ``min_track_record_length`` - how many bets are needed before a given Sharpe
   is statistically distinguishable from zero.
5. ``expected_max_sharpe_of_n_trials`` - the multiple-testing threshold.
6. ``luck_share_of_variance`` - variance decomposition: for a bettor with no
   edge, how much of the observed spread in results is pure noise? Used to show
   why leaderboards rank noise at short horizons.
7. ``block_bootstrap_p_value`` - resampling test that keeps serial dependence,
   for streaks measured in time rather than as a single tally.

Every function returns the numbers it used and a plain-language verdict. None
of them can prove skill; they can only fail to reject the no-skill hypothesis.
"""

from __future__ import annotations

import math
import random
from typing import Any, Sequence


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse normal CDF, Acklam approximation (same as markets._z)."""
    from .markets import _z

    return _z(p)


# ---------------------------------------------------------------------------
# 1. Exact binomial test
# ---------------------------------------------------------------------------

def binomial_p_value(wins: int, losses: int, p0: float = 0.5, alternative: str = "greater") -> dict[str, Any]:
    """Exact one-sided binomial test of win rate against a break-even rate.

    ``p0`` should be the break-even probability implied by the average price
    paid (for -110 two-way prices, p0 ~ 0.5238). Using 0.5 by default is only
    correct for even-money bets.
    """
    n = wins + losses
    if n == 0:
        return {"ok": False, "reason": "no settled bets"}
    if not (0.0 < p0 < 1.0):
        return {"ok": False, "reason": "p0 must be in (0,1)"}

    tail = sum(math.comb(n, k) * p0**k * (1 - p0) ** (n - k) for k in range(wins, n + 1))
    if alternative == "greater":
        p = tail
    elif alternative == "less":
        p = 1.0 - tail + math.comb(n, wins) * p0**wins * (1 - p0) ** (n - wins)
    elif alternative == "two-sided":
        p = min(1.0, 2.0 * min(tail, 1.0 - tail))
    else:
        raise ValueError("alternative must be greater, less or two-sided")

    observed = wins / n
    se = math.sqrt(p0 * (1 - p0) / n)
    z = (observed - p0) / se
    return {
        "ok": True,
        "n": n,
        "wins": wins,
        "losses": losses,
        "observed_win_rate": round(observed, 4),
        "break_even_rate": p0,
        "p_value": round(p, 6),
        "z_score": round(z, 4),
        "alternative": alternative,
        "verdict": _binomial_verdict(p),
        "required_n_for_signal": _n_for_detectable_edge(observed, p0),
    }


def _binomial_verdict(p: float) -> str:
    if p < 0.01:
        return "strong evidence against pure chance (still not proof of skill)"
    if p < 0.05:
        return "moderate evidence against pure chance; needs out-of-sample confirmation"
    if p < 0.10:
        return "weak, inconclusive"
    return "indistinguishable from chance"


def _n_for_detectable_edge(observed: float, p0: float) -> int | None:
    """Rough n needed for a one-sided 5% test to have 80% power at this edge."""
    edge = observed - p0
    if edge <= 0:
        return None
    se_needed = edge / (1.96 + 0.84)  # z_alpha + z_beta
    return int(math.ceil(p0 * (1 - p0) / (se_needed**2)))


# ---------------------------------------------------------------------------
# 2-5. Sharpe-based tests (Bailey & Lopez de Prado)
# ---------------------------------------------------------------------------

def _moments(returns: Sequence[float]) -> dict[str, float]:
    n = len(returns)
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    if sd == 0:
        return {"n": n, "mean": mean, "sd": 0.0, "skew": 0.0, "kurtosis": 3.0}
    m3 = sum((r - mean) ** 3 for r in returns) / n
    m4 = sum((r - mean) ** 4 for r in returns) / n
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "skew": m3 / sd**3,
        "kurtosis": m4 / sd**4,  # non-excess; normal == 3
    }


def probabilistic_sharpe_ratio(returns: Sequence[float], benchmark_sr: float = 0.0) -> dict[str, Any]:
    """PSR: P(true Sharpe > benchmark | observed track record).

    ``returns`` are per-bet net returns per unit staked (e.g. +0.909, -1.0).
    The Sharpe ratio here is per-bet (mean/sd), not annualised, because a bet
    series has no natural time index.
    """
    if len(returns) < 3:
        return {"ok": False, "reason": "need at least 3 returns"}
    m = _moments(returns)
    if m["sd"] == 0:
        return {"ok": False, "reason": "zero variance in returns"}
    sr = m["mean"] / m["sd"]
    n = m["n"]
    # PSR formula (Bailey & Lopez de Prado 2012), non-excess kurtosis form.
    denom = 1.0 - m["skew"] * sr + ((m["kurtosis"] - 1.0) / 4.0) * sr**2
    if denom <= 0:
        return {"ok": False, "reason": "PSR denominator non-positive (pathological moments)"}
    z = (sr - benchmark_sr) * math.sqrt(n - 1) / math.sqrt(denom)
    psr = _norm_cdf(z)
    return {
        "ok": True,
        "n": n,
        "sharpe_per_bet": round(sr, 4),
        "skew": round(m["skew"], 4),
        "kurtosis": round(m["kurtosis"], 4),
        "psr": round(psr, 4),
        "benchmark_sr": benchmark_sr,
        "verdict": (
            "true Sharpe likely positive" if psr > 0.95
            else "inconclusive" if psr > 0.5
            else "cannot distinguish from zero-skill"
        ),
        "note": "PSR is a probability statement about the observed series, not a forecast.",
    }


def expected_max_sharpe_of_n_trials(n_trials: int, sr_sd: float = 1.0) -> float:
    """Expected maximum Sharpe among ``n_trials`` zero-skill strategies.

    Uses the standard extreme-value approximation
    E[max] ~ sr_sd * ((1-g)*Z^-1(1-1/N) + g*Z^-1(1-1/(N*e)))
    with g the Euler-Mascheroni constant. This is the threshold a best-of-N
    strategy must beat before its Sharpe means anything.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if n_trials == 1:
        return 0.0
    g = 0.5772156649015329
    return sr_sd * ((1 - g) * _norm_ppf(1 - 1.0 / n_trials) + g * _norm_ppf(1 - 1.0 / (n_trials * math.e)))


def deflated_sharpe_ratio(returns: Sequence[float], n_trials: int) -> dict[str, Any]:
    """PSR evaluated against the best-of-N null threshold."""
    if n_trials < 1:
        return {"ok": False, "reason": "n_trials must be >= 1"}
    m = _moments(returns)
    if m["sd"] == 0:
        return {"ok": False, "reason": "zero variance in returns"}
    n = m["n"]
    sr = m["mean"] / m["sd"]
    # Standard error of the Sharpe estimator on the per-bet scale.
    sr_se = math.sqrt((1 - m["skew"] * sr + ((m["kurtosis"] - 1) / 4) * sr**2) / (n - 1))
    threshold = expected_max_sharpe_of_n_trials(n_trials, sr_sd=sr_se)
    z = (sr - threshold) / sr_se
    dsr = _norm_cdf(z)
    return {
        "ok": True,
        "n": n,
        "sharpe_per_bet": round(sr, 4),
        "n_trials": n_trials,
        "null_max_sharpe_threshold": round(threshold, 4),
        "deflated_sharpe": round(dsr, 4),
        "verdict": (
            "survives multiple-testing deflation" if dsr > 0.95
            else "not distinguishable from best-of-N luck" if dsr < 0.5
            else "inconclusive after deflation"
        ),
        "note": "Report n_trials honestly. Undercounting trials is the main way this test is gamed.",
    }


def min_track_record_length(returns: Sequence[float], target_sr: float, confidence: float = 0.95) -> dict[str, Any]:
    """Minimum n for which an observed Sharpe would be significant."""
    m = _moments(returns)
    if m["sd"] == 0:
        return {"ok": False, "reason": "zero variance"}
    sr = m["mean"] / m["sd"]
    if target_sr == 0:
        return {"ok": False, "reason": "target_sr must be non-zero"}
    z = _norm_ppf(confidence)
    denom = 1 - m["skew"] * sr + ((m["kurtosis"] - 1) / 4) * sr**2
    if denom <= 0:
        return {"ok": False, "reason": "pathological moments"}
    n = 1 + denom * (z / target_sr) ** 2
    return {
        "ok": True,
        "observed_sharpe_per_bet": round(sr, 4),
        "target_sharpe": target_sr,
        "confidence": confidence,
        "min_track_record_bets": int(math.ceil(n)),
        "note": "Doubles the required sample when the target Sharpe halves.",
    }


# ---------------------------------------------------------------------------
# 6. Luck share of variance
# ---------------------------------------------------------------------------

def luck_share_of_variance(n_bets: int, win_prob: float, decimal_odds: float) -> dict[str, Any]:
    """Share of the observed spread in a record that is pure chance.

    For n independent bets with identical probability p and decimal odds d,
    the standard deviation of the *win rate* under no skill is
    sqrt(p(1-p)/n). After n bets, a no-skill bettor's record still has a
    standard deviation of that size, so two no-skill bettors separated by two
    standard deviations is entirely routine. This function quantifies the
    spread that luck alone produces.
    """
    if n_bets <= 0:
        return {"ok": False, "reason": "n_bets must be > 0"}
    if not (0.0 < win_prob < 1.0):
        return {"ok": False, "reason": "win_prob must be in (0,1)"}
    sd_rate = math.sqrt(win_prob * (1 - win_prob) / n_bets)
    ev_per_bet = win_prob * decimal_odds - 1.0
    sd_return = math.sqrt(win_prob * (decimal_odds - 1) ** 2 + (1 - win_prob) * 1.0 - ev_per_bet**2) / math.sqrt(n_bets)
    return {
        "ok": True,
        "n_bets": n_bets,
        "win_prob": win_prob,
        "decimal_odds": decimal_odds,
        "ev_per_bet": round(ev_per_bet, 4),
        "no_skill_sd_of_win_rate": round(sd_rate, 4),
        "no_skill_sd_of_roi": round(sd_return, 4),
        "win_rate_95pct_band_if_no_skill": [
            round(max(0.0, win_prob - 1.96 * sd_rate), 4),
            round(min(1.0, win_prob + 1.96 * sd_rate), 4),
        ],
        "bets_to_halve_noise": n_bets * 4,
        "note": "Noise falls as 1/sqrt(n): quadrupling the sample halves the luck band.",
    }


def leaderboard_noise_check(n_bettors: int, n_bets_each: int, win_prob: float, decimal_odds: float) -> dict[str, Any]:
    """How many of N identical no-skill bettors will look 'good' by chance."""
    if n_bettors < 1:
        return {"ok": False, "reason": "n_bettors must be >= 1"}
    sd_rate = math.sqrt(win_prob * (1 - win_prob) / n_bets_each)
    ev = win_prob * decimal_odds - 1.0
    # A "good" record defined as ROI > 0.
    # Approximate per-bet return distribution by a two-point variable.
    per_bet_sd = math.sqrt(win_prob * (decimal_odds - 1) ** 2 + (1 - win_prob) * 1.0 - ev**2)
    total_sd = per_bet_sd * math.sqrt(n_bets_each)
    total_mean = ev * n_bets_each
    z = (0.0 - total_mean) / total_sd if total_sd else 0.0
    frac_profitable = 1.0 - _norm_cdf(z)
    return {
        "ok": True,
        "n_bettors": n_bettors,
        "n_bets_each": n_bets_each,
        "win_prob": win_prob,
        "expected_profitable_no_skill": round(n_bettors * frac_profitable, 2),
        "expected_profitable_no_skill_pct": round(100 * frac_profitable, 2),
        "sd_of_win_rate": round(sd_rate, 4),
        "note": "If the leaderboard threshold is 'positive ROI', roughly this share of pure-chance entries clears it.",
    }


# ---------------------------------------------------------------------------
# 7. Block bootstrap for serial dependence
# ---------------------------------------------------------------------------

def block_bootstrap_p_value(returns: Sequence[float], block: int = 5, resamples: int = 5000, seed: int = 20261103) -> dict[str, Any]:
    """Resampling test of mean return > 0 that preserves short-range dependence.

    Returns the share of sign-flipped-centred bootstrap samples whose mean
    falls below zero, i.e. a one-sided p-value under the no-edge null.
    """
    n = len(returns)
    if n < 10:
        return {"ok": False, "reason": "need at least 10 returns"}
    if block < 1 or block > n:
        return {"ok": False, "reason": "block size out of range"}
    rng = random.Random(seed)
    observed = sum(returns) / n
    centred = [r - observed for r in returns]  # null: true mean is zero
    hits = 0
    n_blocks = math.ceil(n / block)
    for _ in range(resamples):
        sample: list[float] = []
        for _ in range(n_blocks):
            start = rng.randrange(0, n - block + 1)
            sample.extend(centred[start : start + block])
        sample = sample[:n]
        if sum(sample) / n >= observed:
            hits += 1
    return {
        "ok": True,
        "n": n,
        "block": block,
        "resamples": resamples,
        "seed": seed,
        "observed_mean_return": round(observed, 6),
        "p_value": round(hits / resamples, 6),
        "note": "Seeded and deterministic. p is relative to a zero-mean null, so it ignores vig.",
    }
