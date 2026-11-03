"""Team rating estimation with explicit small-sample shrinkage.

The only inputs are official NBA.com season aggregates. Two estimators are
provided because they fail in different ways:

``raw_net_rating``
    NBA.com's published NetRtg. For a handful of games this is dominated by
    noise; a team that is +12.8 over 8 games is not necessarily a +12.8 team.

``shrunk_net_rating``
    Empirical-Bayes style shrinkage of the observed net rating toward the
    league mean, using an explicit prior strength. The shrinkage factor is
    ``gp / (gp + k)``. This is the standard James-Stein / credibility form used
    in sports rating work. ``k`` is a *prior strength in games*, NOT an
    estimate measured from this data, and it is declared in the output so the
    reader can see the assumption.

Why shrinkage matters for line origination: using a raw 7-game net rating to
price a game systematically overstates the difference between good and bad
teams, which is exactly the error that makes a naive model look confident while
being wrong.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

#: Prior strength in games. A team with k games of data gets half its weight
#: from the prior. 20 is a deliberately weak prior (an NBA team's rating takes
#: roughly a quarter to a third of a season to stabilise); the value is exposed
#: in every output object so it can be challenged rather than hidden.
DEFAULT_PRIOR_GAMES = 20.0


def load_ratings(season: str) -> dict[str, Any]:
    """Load an official ratings snapshot. Raises if the file is missing."""
    path = DATA_DIR / f"official-team-ratings-{season}.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def by_abbr(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["abbr"]: row for row in snapshot["rows"]}


def league_mean_net_rating(snapshot: dict[str, Any]) -> float:
    """Possession-weighted league mean of net rating.

    Teams differ in games played, so a plain average over teams over-weights
    teams that have played fewer games. Weighting by possessions is the
    least-wrong simple correction. If possessions are unavailable the plain
    mean is used and that is reported.
    """
    rows = snapshot["rows"]
    if all("poss" in r and r["poss"] for r in rows):
        total = sum(r["poss"] for r in rows)
        return sum(r["net_rtg"] * r["poss"] for r in rows) / total
    return sum(r["net_rtg"] for r in rows) / len(rows)


def shrinkage_weight(games_played: int, prior_games: float = DEFAULT_PRIOR_GAMES) -> float:
    """Weight given to the observed rating: gp / (gp + k)."""
    if games_played < 0:
        raise ValueError("games_played must be >= 0")
    if prior_games <= 0:
        raise ValueError("prior_games must be > 0")
    return games_played / (games_played + prior_games)


def shrunk_net_rating(
    observed: float,
    games_played: int,
    league_mean: float,
    prior_games: float = DEFAULT_PRIOR_GAMES,
) -> float:
    """Pull an observed net rating toward the league mean."""
    w = shrinkage_weight(games_played, prior_games)
    return league_mean + w * (observed - league_mean)


def shrunk_ratings(snapshot: dict[str, Any], prior_games: float = DEFAULT_PRIOR_GAMES) -> dict[str, Any]:
    """Return both raw and shrunk ratings for every team in the snapshot."""
    mean = league_mean_net_rating(snapshot)
    out = {}
    for row in snapshot["rows"]:
        out[row["abbr"]] = {
            "team": row["team"],
            "gp": row["gp"],
            "w": row["w"],
            "l": row["l"],
            "net_rtg_raw": row["net_rtg"],
            "off_rtg": row["off_rtg"],
            "def_rtg": row["def_rtg"],
            "pace": row["pace"],
            "shrink_weight": round(shrinkage_weight(row["gp"], prior_games), 4),
            "net_rtg_shrunk": round(shrunk_net_rating(row["net_rtg"], row["gp"], mean, prior_games), 3),
        }
    return {
        "season": snapshot["season"],
        "source_url": snapshot["source_url"],
        "snapshot_utc": snapshot["snapshot_utc"],
        "prior_games": prior_games,
        "league_mean_net_rtg": round(mean, 3),
        "teams": out,
    }


def expected_pace(snapshot: dict[str, Any], home: str, away: str) -> float:
    """League-relative pace estimate for a matchup.

    NBA.com defines PACE as possessions per 48 minutes. The matchup estimate is
    the mean of the two team paces, adjusted so the result is league-relative:

        pace_matchup = league_pace + ((pace_home - league_pace) + (pace_away - league_pace)) / 2

    This is an assumption (a linear, symmetric blend), documented here because
    it cannot be derived from published season totals alone.
    """
    teams = by_abbr(snapshot)
    league_pace = sum(r["pace"] for r in snapshot["rows"]) / len(snapshot["rows"])
    h, a = teams[home]["pace"], teams[away]["pace"]
    return league_pace + ((h - league_pace) + (a - league_pace)) / 2.0


def league_mean_pace(snapshot: dict[str, Any]) -> float:
    return sum(r["pace"] for r in snapshot["rows"]) / len(snapshot["rows"])


def normal_cdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    """Standard normal CDF via erf (no SciPy dependency)."""
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))
