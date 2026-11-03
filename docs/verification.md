# Verification Log

Method: every table row was checked against the linked official NBA.com page. Values are recorded exactly as displayed. No value was inferred, estimated, or filled in. Where no official source confirms a value, the cell is left blank and the row is flagged on site/pages/flagged.html.

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
| 2 | Column labelled BLKA (between BLK and PF) was not in the CSV. Added to verified/data/nba_teams.json; meaning to be confirmed | data/teams-2025-26.csv | Resolved in part; flagged F-11 |
| 3 | Betting lines/odds not published by NBA.com | All strategy tables | Cells blank + unverified; sportsbook line capture required at bet time |
| 4 | 2026-27 standings: 5 to 8 games per team | data/standings-2026-27.csv | Small-sample flag; context only, not a signal |
| 5 | stats.nba.com JSON API not reached; game-level logs not pulled. Season-level correlations are computed (verified/data/correlation_computed.json); leg correlations stay blank | docs/strategies.md | Partly resolved |

## Verification statement
All numeric values in data/ tables match the official NBA.com pages listed above as fetched on 2026-11-03. Nothing was inferred.
