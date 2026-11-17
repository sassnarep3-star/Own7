"""The origination model, as an explicit three-stage pipeline.

Requirement 3 is an ordering requirement, so the ordering is structural here rather
than a comment: `originate()` calls stage_side, then stage_total, then stage_moneyline,
and each stage returns the values the next one is allowed to use. stage_total is given
the stage-1 score pair and may not model points again; stage_moneyline is given the
stage-1 margin and the measured spread of official margins and may not re-model the
score. A stage that needs an input it has not been handed raises instead of guessing.

Parameters are measured from official final scores (n published with each one), not
assumed. The two parameters the older board assumed - two points of home advantage and
a 13.86-point margin spread - are replaced here by the mean and standard deviation of
the 137 official home margins in the verified results feed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import mean, normal_cdf, read_csv, stdev  # noqa: E402

FEED = Path(__file__).resolve().parent / "data" / "results-feed.csv"

# Pythagorean exponent: a published convention, not fitted here and not an NFL figure.
PYTH_EXPONENT = 2.37
RECENCY_DECAY = 0.85
SHRINK_GAMES = 4.0

STAGES = [
    {"stage": 1, "market": "Side",
     "produces": "home_points, away_points, margin_home, spread_home, total_input",
     "may_use": "official scoring rates, official league mean, measured home margin",
     "reads_from_previous_stage": "nothing - this is the first stage"},
    {"stage": 2, "market": "Total",
     "produces": "total",
     "may_use": "the stage-1 score pair only",
     "reads_from_previous_stage": "home_points, away_points"},
    {"stage": 3, "market": "Moneyline",
     "produces": "p_home, p_away, fair_price_home, fair_price_away",
     "may_use": "the stage-1 margin and the measured margin spread only",
     "reads_from_previous_stage": "margin_home"},
]


def load_feed():
    return read_csv(FEED)


def team_rates(games):
    """Per-club scoring rates from official final scores. No shrinkage applied."""
    table = {}
    for row in games:
        hp, ap = int(row["home_score"]), int(row["away_score"])
        for club, scored, allowed, home in ((row["home"], hp, ap, True),
                                            (row["away"], ap, hp, False)):
            entry = table.setdefault(club, {"gp": 0, "pf": 0, "pa": 0,
                                            "home_gp": 0, "home_pf": 0, "home_pa": 0,
                                            "away_gp": 0, "away_pf": 0, "away_pa": 0})
            entry["gp"] += 1
            entry["pf"] += scored
            entry["pa"] += allowed
            if home:
                entry["home_gp"] += 1
                entry["home_pf"] += scored
                entry["home_pa"] += allowed
            else:
                entry["away_gp"] += 1
                entry["away_pf"] += scored
                entry["away_pa"] += allowed
    for entry in table.values():
        entry["off"] = entry["pf"] / entry["gp"]
        entry["def"] = entry["pa"] / entry["gp"]
        entry["net"] = (entry["pf"] - entry["pa"]) / entry["gp"]
    return table


def league_mean(games):
    """League points per team-game, from the same official scores."""
    total = sum(int(r["home_score"]) + int(r["away_score"]) for r in games)
    team_games = 2 * len(games)
    return total / team_games if team_games else None


def measured_home_margin(games):
    """Mean and SD of official home margins. This is the measured home allowance.

    It confounds any true home effect with schedule asymmetry, because home clubs are
    not a random sample of equal strength. The interval is published so a reader can see
    how weak the estimate is: with n = 137 and SD about 13.2 the standard error is near
    1.1 points, so both zero and the conventional two points sit inside it.
    """
    margins = [int(r["home_score"]) - int(r["away_score"]) for r in games]
    if len(margins) < 2:
        return {"n": len(margins), "mean": None, "sd": None, "se": None,
                "ci95_low": None, "ci95_high": None}
    mu = mean(margins)
    sd = stdev(margins)
    se = sd / math.sqrt(len(margins)) if sd else None
    return {
        "n": len(margins), "mean": mu, "sd": sd, "se": se,
        "ci95_low": mu - 1.959963985 * se if se else None,
        "ci95_high": mu + 1.959963985 * se if se else None,
    }


def pythagorean(pf, pa, exponent=PYTH_EXPONENT):
    if pf <= 0 or pa <= 0:
        return None
    return (pf ** exponent) / (pf ** exponent + pa ** exponent)


# ------------------------------------------------------------ stage 1: side

def stage_side(home_rates, away_rates, league, hfa, shrink=0.0, defense_weight=1.0):
    """Stage 1. Produce one coherent score pair, then the side from it.

    team_points = (own scoring rate + opponent concession rate x weight + league mean)
                  / (2 + weight), shrunk toward the league mean, plus the measured home
                  allowance for the home club.
    """
    if league is None or league <= 0:
        raise ValueError("Stage 1 needs a positive league scoring mean")
    if hfa is None:
        raise ValueError("Stage 1 needs a measured home allowance")

    def side_points(rates, opponent_rates, home):
        off = rates["off"]
        dfn = opponent_rates["def"]
        weight = max(0.0, float(shrink))
        games = rates["gp"]
        base = (off + defense_weight * dfn + league) / (2.0 + defense_weight)
        shrunk = (games * base + weight * league) / (games + weight)
        return shrunk + (hfa if home else 0.0)

    home_points = side_points(home_rates, away_rates, True)
    away_points = side_points(away_rates, home_rates, False)
    margin = home_points - away_points
    return {
        "stage": 1,
        "home_points": home_points,
        "away_points": away_points,
        "margin_home": margin,
        # Convention: a negative home spread means the home club is favoured.
        "spread_home": -margin,
        "formula": ("home = (home_off + w*away_def + league)/(2+w) shrunk to league "
                    "by games/(games+k) + hfa; away = same without hfa; "
                    "spread_home = away - home"),
    }


# ----------------------------------------------------------- stage 2: total

def stage_total(stage_one):
    """Stage 2. The total is the sum of the stage-1 pair. It is never re-modelled."""
    home_points = stage_one.get("home_points")
    away_points = stage_one.get("away_points")
    if home_points is None or away_points is None:
        raise ValueError("Stage 2 requires the stage-1 score pair")
    return {
        "stage": 2,
        "total": home_points + away_points,
        "identity": "total = stage_1.home_points + stage_1.away_points",
        "independent_of": "no second model of scoring is fitted; the total carries "
                          "exactly the information in the side",
    }


# ------------------------------------------------------- stage 3: moneyline

def stage_moneyline(stage_one, margin_sd, tie_rate=None):
    """Stage 3. The moneyline is a function of the stage-1 margin alone.

    P(home win) uses a normal approximation on the stage-1 margin with the spread
    measured from official home margins. Ties are split, which is a stated
    approximation: one tie exists in 137 games.
    """
    margin = stage_one.get("margin_home")
    if margin is None:
        raise ValueError("Stage 3 requires the stage-1 margin")
    if not margin_sd or margin_sd <= 0:
        raise ValueError("Stage 3 requires a positive measured margin spread")
    p_home = normal_cdf(margin / margin_sd)
    if tie_rate:
        # Splitting the tie moves probability mass from each side to a third outcome.
        p_home = p_home * (1 - tie_rate)
    p_away = 1 - p_home - (tie_rate or 0.0)
    return {
        "stage": 3,
        "p_home": p_home,
        "p_away": p_away,
        "p_tie": tie_rate or 0.0,
        "fair_price_home": american_from_probability(p_home),
        "fair_price_away": american_from_probability(p_away),
        "inputs": "stage_1.margin_home, measured margin SD, measured tie rate",
        "monotonic_in_side": "P(home win) is strictly increasing in the stage-1 home "
                             "margin for a fixed SD, so the moneyline can never "
                             "contradict the side",
    }


def american_from_probability(p):
    """Fair, zero-hold American price. Not an offered price; no operator publishes one."""
    if p is None or not 0 < p < 1:
        return None
    if p >= 0.5:
        return int(round(-100 * p / (1 - p)))
    return int(round(100 * (1 - p) / p))


def originate(home_rates, away_rates, league, hfa, margin_sd, tie_rate=None,
              shrink=0.0, defense_weight=1.0):
    """Run the three stages in order and return them in order."""
    one = stage_side(home_rates, away_rates, league, hfa, shrink, defense_weight)
    two = stage_total(one)
    three = stage_moneyline(one, margin_sd, tie_rate)
    return {"side": one, "total": two, "moneyline": three}
