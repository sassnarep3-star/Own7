"""Line-origination engine for NBA markets.

Design rules enforced throughout this package:

1. Every numeric input carries a source. Inputs come from
   ``analysis/data/official-*.json``, which records the NBA.com URL each value
   was read from. Nothing is scraped at run time.
2. Market prices are never invented. No function here outputs a price that is
   not either (a) a documented mathematical transform of a probability, or
   (b) a number the caller supplied and labelled as a market number.
3. Anything the model cannot support is returned as ``None`` with a reason,
   never as a plausible-looking number.
4. All randomness is seeded and all results are deterministic.

Statistical honesty notes that the rest of the package relies on:

* A spread/total model built from season ratings is a *state model*. Its
  inputs (team efficiency ratings) are measured with error and drift, so the
  output is a distribution, not a prediction.
* "Removing luck" is not possible. What is possible is (i) shrinking small
  samples toward a prior, (ii) testing whether an observed record is
  distinguishable from chance, and (iii) comparing a strategy with a no-skill
  baseline over enough independent bets.
"""

from . import ratings, markets, correlation, skill, gates, leaderboard

__all__ = [
    "ratings",
    "markets",
    "correlation",
    "skill",
    "gates",
    "leaderboard",
]
