# Official NBA Data Sources

Verified reachable from this sandbox via the Arena fetch proxy (direct `curl` to NBA hosts fails; `fetch_page` succeeds). All data in `data/` was transcribed from these live pages.

| # | Source | URL | What it provides | Status |
|---|--------|-----|------------------|--------|
| 1 | NBA.com — Team Traditional Stats (2025-26 Regular Season) | https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season | Full 30-team table: GP, W, L, WIN%, Min, PTS, FGM, FGA, FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%, OREB, DREB, REB, AST, TOV, STL, BLK, PF, PFD, +/- | Reachable; data rendered server-side |
| 2 | NBA.com — Player Traditional Stats (2025-26 Regular Season, Per Game) | https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame | 582-player table; top 15 by PPG transcribed for `data/players-2025-26-top15.csv` | Reachable; data rendered server-side |
| 3 | NBA.com — Standings (2026-27 Regular Season) | https://www.nba.com/standings | Conference standings, W/L, WIN%, GB, streaks | Reachable; reflects ~8 games played as of 2026-11-03 (small sample) |
| 4 | NBA.com — Schedule | https://www.nba.com/schedule | Game dates, times, arenas, official Game IDs (e.g. 0022600173) | Reachable |
| 5 | NBA.com — Stats home | https://www.nba.com/stats | Navigation to traditional/advanced/misc/usage/scoring/opponent stats | Reachable |
| 6 | NBA.com — Teams | https://www.nba.com/teams | Team directory with official team IDs used in stats URLs | Reachable |
| 7 | NBA.com (stats API host) | https://stats.nba.com | Official stats API host (`/stats/...` endpoints) | NOT reachable from sandbox (connection fails); pages on nba.com used instead |

## Irregularities flagged
- Direct `curl` to `stats.nba.com` and `www.nba.com` returns connection failure (exit 35) from this sandbox; `fetch_page` proxy works. No data was obtained from any non-proxied path.
- One display column between `BLK` and `PF` in the NBA.com teams table rendering could not be unambiguously mapped; it is excluded from all tables (flagged, see docs/verification.md).
- Betting lines / odds are NOT published by NBA.com. All market-line cells are left blank and flagged unverified (see docs/strategies.md and site/pages/flagged.html).
