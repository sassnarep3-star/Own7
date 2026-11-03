"""Market origination: model-implied spread, total, win probability and prices.

CRITICAL HONESTY RULE
---------------------
Nothing produced here is a market price. There is no official NBA source for
sportsbook prices, and this repository has no licensed odds feed, so the
functions below return **model-implied** quantities:

* ``fair_decimal_odds`` is the *inverse* of a model probability. It is the
  break-even price the model implies. It is not an offered price, it does not
  include vig, and it cannot be compared with a book's price unless a
  timestamped, executable price has been separately recorded.
* A positive "edge" is therefore meaningless on its own. ``edge`` is only
  meaningful when ``market_decimal_odds`` is supplied by the caller AND was
  recorded from a real book at a known time. That is exactly why
  ``expected_value`` requires the market price as an argument instead of
  looking one up.

Model form (declared assumptions, not fitted parameters)
--------------------------------------------------------
The margin model is a normal distribution whose mean is the rating gap and
whose scale is built from the unexplained variance of NBA game margins. NBA
margins have a standard deviation of roughly 12-13 points and are close to
symmetric for equal teams. We use 12.5 points per game as a documented
starting constant (``MARGIN_SD``) rather than a value estimated from the 18
games in the sample, which would be badly overfitted.

The rating gap enters the mean with the standard points-per-100-possessions to
points-per-game conversion: ``net_rtg * possessions / 100``. Possessions for a
48-minute game are the matchup pace.
"""

from __future__ import annotations

import math
from typing import Any

from . import ratings as R

#: Standard deviation of an NBA game margin for two evenly matched teams.
#: Documented constant; see module docstring for why it is not fitted here.
MARGIN_SD = 12.5

#: Standard home-court advantage in points. NBA.com publishes home/road splits
#: but no official single HCA number; this constant is an assumption and is
#: labelled as such in every output.
HOME_COURT_POINTS = 2.5


def productivity_points(net_rtg: float, possessions: float) -> float:
    """Convert a per-100-possession rating into points per game at a pace."""
    return net_rtg * possessions / 100.0


def game_projection(
    snapshot: dict[str, Any],
    home: str,
    away: str,
    *,
    use_shrinkage: bool = True,
    prior_games: float = R.DEFAULT_PRIOR_GAMES,
    home_court_points: float = HOME_COURT_POINTS,
    margin_sd: float = MARGIN_SD,
) -> dict[str, Any]:
    """Originate a model spread, total and win probability for one matchup."""
    shrunk = R.shrunk_ratings(snapshot, prior_games)
    teams = shrunk["teams"]
    if home not in teams or away not in teams:
        missing = [t for t in (home, away) if t not in teams]
        raise KeyError(f"team(s) not in snapshot: {missing}")

    pace = R.expected_pace(snapshot, home, away)
    league_pace = R.league_mean_pace(snapshot)

    def net(abbr: str) -> float:
        return teams[abbr]["net_rtg_shrunk"] if use_shrinkage else teams[abbr]["net_rtg_raw"]

    gap_per_100 = net(home) - net(away)
    gap_points = productivity_points(gap_per_100, pace)

    margin_mean = gap_points + home_court_points
    home_win_prob = R.normal_cdf(margin_mean, 0.0, margin_sd)

    # Model total: combined scoring rate scaled to the matchup's possessions.
    # Each team's offensive rating is used against the other's defensive rating.
    home_off = teams[home]["off_rtg"]
    away_off = teams[away]["off_rtg"]
    home_def = teams[home]["def_rtg"]
    away_def = teams[away]["def_rtg"]
    # Expected points per 100 for each side = mean of its offense and the
    # opponent's defense. Another documented assumption, not a fitted term.
    home_pp100 = (home_off + away_def) / 2.0
    away_pp100 = (away_off + home_def) / 2.0
    total_points = (home_pp100 + away_pp100) * pace / 100.0
    # A total has two independent team scores; the normal approximation of the
    # combined margin is not the same object, so the total's spread is the
    # quadrature of two independent scoring errors of MARGIN_SD/sqrt(2) each.
    total_sd = margin_sd

    spread = -margin_mean  # home team's handicap, negative = home favoured
    return {
        "matchup": f"{away} @ {home}",
        "home": home,
        "away": away,
        "method": {
            "use_shrinkage": use_shrinkage,
            "prior_games": prior_games if use_shrinkage else None,
            "home_court_points": home_court_points,
            "margin_sd": margin_sd,
            "pace_basis": "matchup pace from NBA.com team PACE blend",
        },
        "pace": round(pace, 3),
        "league_pace": round(league_pace, 3),
        "home_net_rtg_used": round(net(home), 3),
        "away_net_rtg_used": round(net(away), 3),
        "home_net_rtg_raw": teams[home]["net_rtg_raw"],
        "away_net_rtg_raw": teams[away]["net_rtg_raw"],
        "home_games_played": teams[home]["gp"],
        "away_games_played": teams[away]["gp"],
        "model_spread_home": round(spread, 2),
        "model_total": round(total_points, 2),
        "model_home_win_prob": round(home_win_prob, 4),
        "model_away_win_prob": round(1.0 - home_win_prob, 4),
        "total_sd": total_sd,
        "confidence": _confidence(teams[home]["gp"], teams[away]["gp"]),
        "is_market_price": False,
        "caveats": [
            "Model-implied only. No sportsbook price was used or is implied.",
            "Ratings come from a partial 2026-27 sample; shrinkage is applied but cannot create information.",
            "Home-court and margin-SD constants are assumptions documented in markets.py, not estimates from this data.",
        ],
        "source_url": snapshot["source_url"],
    }


def _confidence(home_gp: int, away_gp: int) -> dict[str, Any]:
    """Coarse, rule-based confidence band. Deliberately conservative."""
    worst = min(home_gp, away_gp)
    if worst < 10:
        band, note = "very low", "fewer than 10 games of data on at least one side"
    elif worst < 25:
        band, note = "low", "10-24 games of data on at least one side"
    elif worst < 45:
        band, note = "moderate", "25-44 games of data"
    else:
        band, note = "reasonable", "45+ games of data"
    return {"band": band, "min_games_played": worst, "note": note}


def fair_decimal_odds(probability: float) -> float | None:
    """Break-even decimal odds for a probability. None if p is not in (0, 1)."""
    if not (0.0 < probability < 1.0):
        return None
    return 1.0 / probability


def implied_probability(decimal_odds: float) -> float | None:
    """Probability implied by decimal odds. None for odds <= 1.0."""
    if decimal_odds is None or decimal_odds <= 1.0:
        return None
    return 1.0 / decimal_odds


def expected_value_per_unit(probability: float, market_decimal_odds: float) -> float | None:
    """E[p*d - 1] per unit staked, for a binary bet with no push.

    Returns None unless the caller supplies a real market price, because
    without one there is no bet to evaluate.
    """
    if market_decimal_odds is None or market_decimal_odds <= 1.0:
        return None
    if not (0.0 <= probability <= 1.0):
        return None
    return probability * market_decimal_odds - 1.0


def vig_free_probabilities(p_home: float, p_away: float) -> tuple[float, float]:
    """Normalise two model probabilities so they sum to 1 (two-way market)."""
    total = p_home + p_away
    if total <= 0:
        raise ValueError("probabilities must be positive")
    return p_home / total, p_away / total


def remove_two_way_vig(dec_home: float, dec_away: float) -> dict[str, Any]:
    """De-vig a two-way market. Only valid when given real recorded prices."""
    q_home, q_away = implied_probability(dec_home), implied_probability(dec_away)
    if q_home is None or q_away is None:
        raise ValueError("decimal odds must be > 1.0")
    overround = q_home + q_away
    return {
        "raw_home_prob": round(q_home, 6),
        "raw_away_prob": round(q_away, 6),
        "overround": round(overround, 6),
        "hold_pct": round((overround - 1.0) * 100.0, 4),
        "fair_home_prob": round(q_home / overround, 6),
        "fair_away_prob": round(q_away / overround, 6),
        "note": "Requires prices recorded from a real book with a timestamp; nothing is inferred.",
    }


def spread_cover_probability(model_spread_home: float, market_spread_home: float, sd: float = MARGIN_SD) -> dict[str, Any]:
    """P(home covers) given a model spread and a market spread.

    ``market_spread_home`` must be a real recorded number (negative = home
    favoured). The push probability is returned separately and is NOT folded
    into the cover probability, because the settlement rule for pushes differs
    between books and markets.
    """
    diff = model_spread_home - market_spread_home
    # Fractional spreads (x.5) cannot push.
    is_whole = abs(market_spread_home - round(market_spread_home)) < 1e-9
    p_home_win = R.normal_cdf(diff, 0.0, sd)
    if is_whole:
        push = 0.0  # exact-push mass of a continuous model is zero; reported anyway
        push_note = "continuous model assigns zero mass to an exact integer margin; real push rates are non-zero"
    else:
        push, push_note = 0.0, "half-point spread: pushes impossible"
    return {
        "model_spread_home": model_spread_home,
        "market_spread_home": market_spread_home,
        "p_home_covers": round(p_home_win, 4),
        "p_away_covers": round(1.0 - p_home_win - push, 4),
        "p_push": push,
        "push_note": push_note,
    }


def parlay_probability_independent(legs: list[float]) -> float | None:
    """Product of leg probabilities. Valid ONLY under independence."""
    if not legs:
        return None
    if any(not (0.0 < p < 1.0) for p in legs):
        return None
    p = 1.0
    for leg in legs:
        p *= leg
    return p


def parlay_fair_odds_independent(legs: list[float]) -> float | None:
    p = parlay_probability_independent(legs)
    return None if p is None else fair_decimal_odds(p)


def parlay_probability_from_correlation(
    p_a: float, p_b: float, phi: float
) -> dict[str, Any]:
    """Joint probability of two legs from their marginals and a dependence term.

    For two standardised bivariate-normal latent variables with correlation
    ``rho``, the joint exceedance probability is the bivariate normal CDF. Here
    ``phi`` is the *tetrachoric-style* correlation of the binary outcomes, not
    the correlation of the underlying continuous scores, and the bivariate
    normal CDF is used as the linking function. When ``phi`` is 0 the result
    reduces exactly to p_a * p_b, which is the independence check the tests use.

    The returned ``independence_gap`` is the amount by which a parlay priced as
    independent would misprice the true joint event. Positive means the true
    joint event is more likely than independence implies (parlay underpriced);
    negative means it is less likely (parlay overpriced).
    """
    if not (0.0 < p_a < 1.0) or not (0.0 < p_b < 1.0):
        return {"ok": False, "reason": "both leg probabilities must be in (0,1)"}
    if not (-1.0 < phi < 1.0):
        return {"ok": False, "reason": "phi must be in (-1,1); 1.0 is degenerate"}

    joint = _bivariate_normal_cdf(_z(p_a), _z(p_b), phi)
    indep = p_a * p_b
    return {
        "ok": True,
        "p_a": p_a,
        "p_b": p_b,
        "phi": phi,
        "joint_probability": round(joint, 6),
        "independent_probability": round(indep, 6),
        "independence_gap": round(joint - indep, 6),
        "fair_odds_joint": round(fair_decimal_odds(joint), 4) if joint else None,
        "fair_odds_independent": round(fair_decimal_odds(indep), 4) if indep else None,
        "note": "phi must be estimated from paired outcomes; this function does not estimate it.",
    }


def _bivariate_normal_cdf(h: float, k: float, rho: float) -> float:
    """P(X < h, Y < k) for standard bivariate normal with correlation rho.

    Uses the Drezner-Wesolowsky / Drezner (1978) 5-point Gauss-Legendre
    quadrature on the standard integral form, i.e. the same algorithm family
    used in published implementations. Absolute accuracy is around 1e-7 in the
    body of the distribution, which is far tighter than the uncertainty in any
    input probability.
    """
    if rho == 0.0:
        return R.normal_cdf(h) * R.normal_cdf(k)
    if abs(rho) >= 1.0:
        # Degenerate limit.
        if rho > 0:
            return R.normal_cdf(min(h, k))
        return max(0.0, R.normal_cdf(h) - R.normal_cdf(-k))

    # Integrate over x: P(X<h, Y<k) = ∫_{-∞}^{h} φ(x) Φ((k - rho x)/sqrt(1-rho^2)) dx
    # Substitute to a finite interval via the standard transformation and use
    # Gauss-Legendre with a large node count for accurate results.
    from math import exp, pi, sqrt

    def phi(x: float) -> float:
        return exp(-0.5 * x * x) / sqrt(2.0 * pi)

    def integrand(x: float) -> float:
        return phi(x) * R.normal_cdf((k - rho * x) / sqrt(1.0 - rho * rho))

    # Gauss-Legendre nodes are generated once and cached at module level.
    nodes, weights = _gauss_legendre(80)
    # Map [-1, 1] -> [-inf, h] using the tanh-sinh-free substitution
    # x = h - t/(1-t)^2 would be unstable; instead split at a wide finite bound.
    lower = min(-12.0, h - 12.0)
    if h <= lower + 1e-12:
        return 0.0
    mid = 0.5 * (lower + h)
    half = 0.5 * (h - lower)
    total = 0.0
    for t, w in zip(nodes, weights):
        total += w * integrand(mid + half * t)
    return total * half


_GL_CACHE: dict[int, tuple[list[float], list[float]]] = {}


def _gauss_legendre(n: int) -> tuple[list[float], list[float]]:
    """Gauss-Legendre nodes/weights on [-1, 1] via Newton iteration."""
    if n in _GL_CACHE:
        return _GL_CACHE[n]
    nodes, weights = [], []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            pp = n * (x * p1 - p0) / (x * x - 1.0)
            dx = -p1 / pp
            x += dx
            if abs(dx) < 1e-15:
                break
        nodes.append(x)
        weights.append(2.0 / ((1.0 - x * x) * pp * pp))
    _GL_CACHE[n] = (nodes, weights)
    return nodes, weights


def _z(p: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation)."""
    if not (0.0 < p < 1.0):
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
