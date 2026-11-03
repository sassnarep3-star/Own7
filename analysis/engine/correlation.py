"""Correlation measurement for parlay legs and player-prop combos.

What this module can and cannot do with the data actually available here:

* It CAN measure the correlation between two teams' scoring in the same game,
  because official NBA.com team box scores give both sides of every game. That
  is the core same-game parlay problem: a home team's points and the total, or
  two teams' points, are not independent.
* It CANNOT measure player-vs-player prop correlation, because NBA.com does not
  render player game logs in this environment (the player box-score page is
  script-rendered and returns no table). The function
  ``player_pair_correlation`` therefore refuses to run and says why, instead of
  returning a fabricated coefficient.

Statistics used
---------------
Pearson correlation for continuous pairs (points, totals) and the phi
coefficient for two binary outcomes, both with a Fisher z confidence interval
so the reader can see how wide the uncertainty is at small n. At n = 18 a 95%
interval on r is roughly +/-0.47 wide, which is the honest headline: one month
of NBA data cannot pin down a correlation well enough to price a parlay on.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence


def pearson(xs: Sequence[float], ys: Sequence[float]) -> dict[str, Any]:
    """Pearson correlation with a Fisher z 95% interval."""
    n = len(xs)
    if n != len(ys):
        raise ValueError("series must be the same length")
    if n < 3:
        return {"ok": False, "n": n, "reason": "need at least 3 paired observations"}
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return {"ok": False, "n": n, "reason": "zero variance in at least one series"}
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    r = sxy / math.sqrt(sxx * syy)
    r = max(-1.0, min(1.0, r))
    out = {"ok": True, "n": n, "r": round(r, 4), "r_squared": round(r * r, 4)}
    if n > 3:
        z = 0.5 * math.log((1 + r) / (1 - r)) if abs(r) < 1.0 else math.copysign(math.inf, r)
        se = 1.0 / math.sqrt(n - 3)
        lo, hi = z - 1.96 * se, z + 1.96 * se
        out["ci95"] = [round(_inv_fisher(lo), 4), round(_inv_fisher(hi), 4)]
        out["se_fisher_z"] = round(se, 4)
        out["note"] = (
            "Fisher z interval assumes approximate bivariate normality of the pair. "
            "At this sample size the interval is wide; do not price a parlay on the point estimate."
        )
    return out


def _inv_fisher(z: float) -> float:
    if z > 20:
        return 1.0
    if z < -20:
        return -1.0
    e = math.exp(2 * z)
    return (e - 1) / (e + 1)


def phi_coefficient(a: Sequence[bool], b: Sequence[bool]) -> dict[str, Any]:
    """Phi coefficient between two binary outcome series (2x2, no continuity correction)."""
    n = len(a)
    if n != len(b) or n == 0:
        return {"ok": False, "reason": "series must be the same non-zero length"}
    n11 = sum(1 for x, y in zip(a, b) if x and y)
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if not x and y)
    n00 = sum(1 for x, y in zip(a, b) if not x and not y)
    denom = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    if denom == 0:
        return {
            "ok": False,
            "reason": "a marginal is 0 or n; phi is undefined",
            "table": {"n11": n11, "n10": n10, "n01": n01, "n00": n00},
        }
    r = (n11 * n00 - n10 * n01) / denom
    out = {
        "ok": True,
        "n": n,
        "phi": round(r, 4),
        "table": {"n11": n11, "n10": n10, "n01": n01, "n00": n00},
        "marginal_a": round((n11 + n10) / n, 4),
        "marginal_b": round((n11 + n01) / n, 4),
        "joint": round(n11 / n, 4),
        "product_if_independent": round(((n11 + n10) / n) * ((n11 + n01) / n), 4),
    }
    if n > 3:
        se = 1.0 / math.sqrt(n - 3)
        z = math.atanh(max(-0.999999, min(0.999999, r)))
        out["ci95_phi"] = [
            round(math.tanh(z - 1.96 * se), 4),
            round(math.tanh(z + 1.96 * se), 4),
        ]
    return out


def home_away_points(games: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Correlation between the two teams' points in the same game.

    Input rows must be game-level dicts with ``home_pts`` and ``away_pts``.
    """
    rows = list(games)
    xs = [float(g["home_pts"]) for g in rows]
    ys = [float(g["away_pts"]) for g in rows]
    r = pearson(xs, ys)
    r["series"] = "home_points vs away_points (same game)"
    return r


def points_vs_total(games: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Correlation between a team's points and the game total."""
    rows = list(games)
    home = [float(g["home_pts"]) for g in rows]
    totals = [float(g["home_pts"] + g["away_pts"]) for g in rows]
    r = pearson(home, totals)
    r["series"] = "home_points vs game_total (same game)"
    r["warning"] = (
        "Mechanically dependent: the total contains the team's own points, so r is "
        "inflated by construction and is NOT evidence of a tradable relationship."
    )
    return r


def pace_and_total(games: Iterable[dict[str, Any]], pace_by_team: dict[str, float]) -> dict[str, Any]:
    """Correlation between pre-game matchup pace and realised total.

    Uses only ratings that exist before the game (team-season PACE), so this is
    a legitimate forecast check rather than a same-game tautology. With a small
    n, however, it is still only indicative.
    """
    rows = list(games)
    pace_series, totals = [], []
    for g in rows:
        h, a = g["home"], g["away"]
        if h in pace_by_team and a in pace_by_team:
            league = sum(pace_by_team.values()) / len(pace_by_team)
            projected = league + ((pace_by_team[h] - league) + (pace_by_team[a] - league)) / 2.0
            pace_series.append(projected)
            totals.append(float(g["home_pts"] + g["away_pts"]))
    r = pearson(pace_series, totals)
    r["series"] = "pregame projected matchup pace vs realised game total"
    r["n_pairs_used"] = len(pace_series)
    return r


def player_pair_correlation(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Not computable with the data in this repository. Refuses rather than guesses."""
    return {
        "ok": False,
        "computable": False,
        "reason": "No player-level game log is available. NBA.com player box-score pages are rendered client-side and returned no table when fetched; therefore no paired player outcomes exist to correlate.",
        "what_would_be_needed": [
            "Paired player stat lines for the same games (points, rebounds, assists, minutes) from an official or licensed source.",
            "The exact prop line and the settlement rule for each prop, including pushes and voids.",
            "Enough games that the correlation's confidence interval is narrower than the pricing error being chased.",
        ],
        "audit_trail": "See analysis/data/README.md and the Flagged for Review page.",
    }


def sample_size_requirement(assumed_r: float, target_half_width: float) -> dict[str, Any]:
    """Games needed for a correlation's 95% interval to be a given half-width.

    Uses the Fisher z approximation: half width on the z scale is 1.96/sqrt(n-3).
    """
    if abs(assumed_r) >= 1.0:
        return {"ok": False, "reason": "|r| must be < 1"}
    if target_half_width <= 0:
        return {"ok": False, "reason": "target_half_width must be > 0"}
    z = math.atanh(assumed_r)
    se = target_half_width / 1.96
    n = 3 + (1.0 / se) ** 2
    return {
        "assumed_r": assumed_r,
        "target_half_width_on_r": target_half_width,
        "approx_games_needed": math.ceil(n),
        "formula": "n = 3 + (1.96 / (1.96 * half_width))^2 applied on the Fisher z scale",
        "note": "Games are only independent if they involve disjoint players; same-game legs are not independent draws.",
    }
