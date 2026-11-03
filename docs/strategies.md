> SUPERSEDED HISTORICAL DOCUMENT: Earlier claims have not been endorsed by the 2026-11-03 independent audit. Current summary: ../index.html ; findings: ../review.html . Numeric values must not be used as verified data.

# NBA Signal Strategies

Framework: originate lines from official NBA statistics only. Three bet classes: single bets, parlays, player-prop combos. Every strategy passes the validation gates (docs/validation-gates.md). No manual input — all values computed from linked official sources.

## Core formulas (documented, reproducible)

- Implied probability from decimal odds: p_implied = 1 / decimal_odds
- Model edge: edge = p_model − p_implied (bet only if edge > 0 after vig removal)
- Fair decimal odds from model probability: fair_odds = 1 / p_model
- Correlation between legs A and B: rho = cov(A,B) / (sd(A) × sd(B))
- Joint probability under independence: P(A ∩ B) = P(A) × P(B)
- Positive-correlation adjustment: P(A ∩ B) >= P(A) × P(B) when rho > 0 (must be justified by observed co-occurrence from official play-by-play; values blank until computed)
- Parlay payout (decimal): product of leg decimal odds

## Bet class 1 — Single bets

Signal types (all computed from team-level official stats, data/teams-2025-26.csv):
- Spread signal: team point differential (+/-) vs opponent; compare to sportsbook spread (line cell blank — see Flagged for Review).
- Total signal: team PTS + opponent PTS vs sportsbook total (line cell blank).
- Moneyline signal: win percentage vs implied probability of moneyline (line cell blank).

## Bet class 2 — Parlays

Definition: 2+ single bets combined; payout = product of decimal odds; wins only if ALL legs win.
Correlation handling:
- Cross-game legs (different games): treated as independent unless a shared-factor rationale (e.g., same back-to-back scenario) is documented.
- Same-game legs: require correlation disclosure; positive correlation only where a repeatable mechanism exists (e.g., pace-driven team total + team points).
Gate: parlays must show per-leg implied probabilities, joint probability, and combined edge before appearing on the leaderboard.

## Bet class 3 — Player prop combos

Definition: 2+ player props in one game (same-game combo).
Skill-based, positively correlated examples (rationale only — numeric values blank until computed from official play-by-play):
- Playmaker points + finisher points (same team: assists feed teammate scoring)
- Player points + player rebounds (usage/rebounding correlation for big men)
- Team pace → both teams' combined totals (pace correlation)
Negative-correlation examples (avoid in positive-correlation parlays):
- Two high-usage players on the same team competing for possessions
All player values from data/players-2025-26-top15.csv (official NBA.com source). Prop lines (points/rebounds/assists overs) blank — not published by NBA.com.

## Correlation values

Correlation matrix cells are intentionally blank in this release. Numeric correlation values require official play-by-play game logs (stats.nba.com API endpoint), which is not reachable from this sandbox; nba.com HTML pages do not expose play-by-play correlation data. Cells are flagged unverified, never inferred.

## Leaderboard eligibility

A strategy appears on the site leaderboard only if it passes Gates 1–5, has source-linked inputs, and reports edge and correlation method. Current status: no strategy passes yet — betting-line inputs are blank/unverified pending sportsbook line capture at bet time.
