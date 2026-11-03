# Validation Gates

Every strategy must pass ALL gates before it is considered for the leaderboard. Gates are applied in order; a strategy that fails any gate is rejected or flagged, not traded.

## Gate 1 — Official-source gate
Rule: Every input value in a strategy table row must come from an official NBA source (nba.com / stats.nba.com) and carry a source link.
Pass condition: Source link present and reachable.
Fail action: Value left blank, row flagged "unverified" on the Flagged for Review page.
Note: NBA.com does not publish betting lines/odds. Market-line cells are intentionally blank and flagged (see Flagged for Review). Lines must be obtained from the sportsbook at bet time and are outside this repo's verification boundary.

## Gate 2 — Sample-size gate
Rule: A signal requires a minimum observed sample before it can be considered skill-based.
- Team-level signal (spread/total): >= 25 games (full-season equivalent basis from 2025-26: 82 games).
- Player prop signal: >= 25 games AND >= 25 minutes per game average.
- 2026-27 in-season standings: only ~8 games played as of 2026-11-03 → FAILS sample-size gate. Used for context only, never as a standalone signal.
Fail action: Signal marked "small sample — excluded from leaderboard".

## Gate 3 — Correlation gate
Rule: Multi-leg bets (parlays, player-prop combos) must disclose the correlation between legs and how the joint probability is computed.
Pass condition: Correlation method stated; independence assumption explicitly labeled; positive-correlation edges require a skill rationale, not same-game coincidence.
Fail action: Combo excluded from parlay leaderboard.

## Gate 4 — No-luck / skill gate
Rule: Strategies must be selectively skill-based: a repeatable, statistics-driven edge, not a random guess or a "due for a win" heuristic.
- Allowed inputs: official NBA stats (team/player splits, home/road, pace, efficiency), correlation structure, implied probability from sportsbook lines.
- Disallowed: "gut" picks, injury rumors, media narratives, streaks without statistical basis, martingale/stake progression.
Fail action: Strategy rejected.

## Gate 5 — Reproducibility gate
Rule: Another person must be able to recompute the signal from the linked official sources + the documented formula, with no manual input from the strategy author.
Fail action: Strategy flagged "not reproducible".

## Verification record
| Gate | Source checked | Result |
|------|----------------|--------|
| Official source | https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season | Pass — all 30 team rows transcribed, source linked |
| Official source | https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame | Pass — top 15 player rows transcribed, source linked |
| Official source | https://www.nba.com/standings | Pass — 2026-27 standings transcribed; small-sample caveat applied |
| Betting lines | NBA.com | Fail by design — NBA.com publishes no betting lines; cells blank + unverified |
