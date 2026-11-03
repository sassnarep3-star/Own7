> SUPERSEDED HISTORICAL DOCUMENT: Earlier claims have not been endorsed by the 2026-11-03 independent audit. Current summary: ../index.html ; findings: ../review.html . Numeric values must not be used as verified data.

# Verification Log

Method: every table row was checked against the linked official NBA.com page. Values are recorded exactly as displayed. No value was inferred, estimated, or filled in. Where no official source confirms a value, the cell is left blank and the row is flagged on review.html (Flagged for Review).

## Verified data (source: nba.com)

| File | Rows | Source URL | Checked | Verified | Unverified/blank |
|------|------|------------|---------|----------|------------------|
| data/teams-2025-26.csv | 30 | https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season | 30 | 30 | 0 |
| data/players-2025-26-top15.csv | 15 | https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame | 15 | 15 | 0 |
| data/standings-2026-27.csv | 30 | https://www.nba.com/standings | 30 | 30 | 0 |

## Irregularities

| # | Item | Location | Disposition |
|---|------|----------|-------------|
| 1 | Direct `curl` to nba.com/stats.nba.com blocked from sandbox (exit 35); `fetch_page` proxy used | docs/sources.md | Noted; all data still from official nba.com pages |
| 2 | One display column between BLK and PF in NBA.com teams table could not be unambiguously mapped; excluded from all tables | data/teams-2025-26.csv | Excluded, flagged |
| 3 | Betting lines/odds not published by NBA.com | All strategy tables | Cells blank + unverified; sportsbook line capture required at bet time |
| 4 | 2026-27 standings are ~8 games into the season | data/standings-2026-27.csv | Small-sample flag; context only, not a signal |
| 5 | stats.nba.com JSON API unreachable; correlation values cannot be computed from play-by-play | docs/strategies.md | Correlation cells blank + unverified |

## Verification statement
All numeric values in data/ tables match the official NBA.com pages listed above as fetched on 2026-11-03. Nothing was inferred.
