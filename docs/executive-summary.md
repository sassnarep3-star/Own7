# Executive Summary — Own7 NBA Lines Project

## Purpose
Originate NBA betting lines (single bets, parlays, player-prop combos) from official statistics, run strategies as a skill-based leaderboard, and remove luck by requiring reproducible, source-verified signals with validation gates.

## Data basis (official, NBA.com)
- 2025-26 regular season team stats: all 30 teams, complete 82-game season (data/teams-2025-26.csv)
- 2025-26 regular season player stats: top 15 scorers, per game (data/players-2025-26-top15.csv)
- 2026-27 standings: in progress as of 2026-11-03 (~8 games — small sample, context only)

## Key observations from verified 2025-26 data
- Best record: Oklahoma City Thunder 64-18 (.780); worst: Washington Wizards 17-65 (.207)
- Highest PPG team: Denver Nuggets 122.1 (next: Miami Heat 120.9); lowest: Brooklyn Nets 105.9
- Highest FG% team: Los Angeles Lakers 50.2% (next: Denver Nuggets 49.6%); best 3P%: Denver Nuggets 39.6%
- Top scorer: Luka Doncic (LAL) 33.5 PPG (64 GP); SGA (OKC) 31.1 PPG on 68 GP
- Note: 2025-26 reflects player movement reflected on NBA.com (e.g., Doncic–Lakers, Durant–Rockets)

## Strategy status
- Framework defined: single bets, parlays, player-prop combos (docs/strategies.md)
- Validation gates defined and applied (docs/validation-gates.md)
- Team-level correlations (cross-sectional, n = 30, computed from the verified team table): Win% vs +/- r = 0.973; Points vs FG% r = 0.577; Rebounds vs offensive rebounds r = 0.690. These are descriptive, not bet-leg correlations (data/team-correlations-2025-26.csv).
- No strategy is leaderboard-eligible yet: betting lines are not published by NBA.com, so all market-line cells are blank and flagged unverified (Flagged for Review page)

## Verification
- Every table row in data/ carries a source link to NBA.com and a "verified" flag.
- No values were inferred or filled in; blanks remain where no official source confirms the value.
- Full verification log: docs/verification.md; flagged items: site/pages/flagged.html

## Site
- GitHub Pages site at the repo root: landing page + category subpages (single bets, parlays, player props, correlation, validation gates, flagged for review, executive summary)
- All tables are source-linked and sortable/filterable client-side.
