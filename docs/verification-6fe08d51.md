# Independent verification — session arena/6fe08d51-own7 (2026-11-03)

Method: every row of every published data table was re-read from the live official NBA.com pages via the fetch proxy on 2026-11-03 (UTC) and compared cell by cell against the repository CSVs. No inherited verification was assumed. Nothing was inferred; mismatches would be blanked and flagged.

## Sources re-read (live)

| # | Official page | URL | Chunks read |
|---|---------------|-----|-------------|
| 1 | NBA.com — Teams Traditional, 2025-26 Regular Season | https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season | 5/5 |
| 2 | NBA.com — Players Traditional, 2025-26 Regular Season, Per Game | https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame | table header + rows 1-16 read |
| 3 | NBA.com — Standings, 2026-27 Regular Season | https://www.nba.com/standings | 2/2 |

## Row-by-row results

| File | Rows checked | Columns compared | Match | Mismatch | Blank/flagged |
|------|--------------|------------------|-------|----------|---------------|
| data/teams-2025-26.csv | 30/30 | GP, W, L, WIN%, PTS, FG%, 3P%, FT%, OREB, DREB, REB, AST, TOV, STL, BLK, PF, PFD, +/- (18 per row) | 30 | 0 | 0 |
| data/players-2025-26-top15.csv | 15/15 | Age, GP, W, L, MIN, PTS, FGM, FGA, FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%, OREB, DREB, REB, AST, TOV, STL, BLK, PF (23 per row) | 15 | 0 | 0 |
| data/standings-2026-27.csv | 30/30 | W, L, WIN%, GB, CONF, DIV, HOME, ROAD, LAST10, STREAK (10 per row) | 30 | 0 | 0 |
| data/team-correlations-2025-26.csv | 6/6 pairs | r, r_squared recomputed from data/teams-2025-26.csv by scripts/compute_team_correlations.py | 6 | 0 | 0 |

Total cells compared: 30×18 + 15×23 + 30×10 + 6×2 = **1,086**. Mismatches: **0** (statistical columns).

Rank-column follow-up (2026-11-04): after the b11f3baa audit surfaced the Utah rank discrepancy, Rank was added to the comparison scope - 30 team ranks + 30 standings ranks re-read live. One mismatch found and fixed (Utah 27 to 26, V-6). With the fix, Rank now matches 60/60.

## Derived-claim checks (docs/executive-summary.md and index.html)

| Claim | Live value | Result |
|-------|-----------|--------|
| Best record OKC 64-18 (.780) | OKC 82 G, 64-18, .780 | match |
| Worst record Washington 17-65 (.207) | WAS 82 G, 17-65, .207 | match |
| Highest PPG Denver 122.1 | DEN 122.1 | match |
| Next PPG Miami 120.9 | MIA 120.9 | match |
| Lowest PPG Brooklyn 105.9 | BKN 105.9 | match |
| Highest FG% Lakers 50.2 | LAL 50.2 | match |
| Next FG% Denver 49.6 | DEN 49.6 | match |
| Best 3P% Denver 39.6 | DEN 39.6 | match |
| Top scorer Luka Doncic 33.5 PPG, 64 GP | 33.5, 64 GP | match |
| SGA 31.1 PPG, 68 GP | 31.1, 68 GP | match |

## Irregularities found in this pass

| # | Item | Disposition |
|---|------|-------------|
| V-1 | 2026-27 standings are a live in-season snapshot; team game counts range 5-8 (PHX 5 G, most teams 7-8 G). The CSV note "~8 games" is approximate. | Already flagged as F10; snapshot verified as of 2026-11-03; re-verification required if the page is read on a later date. |
| V-2 | NBA.com player names include diacritics (Dončić, Jokić); CSV uses ASCII (Doncic, Jokic). All numeric cells match. | Naming convention only; no value affected. Noted, not blocking. |
| V-3 | Live teams table includes a BLKA (blocks against) column between BLK and PF; it is intentionally excluded from the CSV. | Correct exclusion; earlier flag resolved (BLKA identified). |
| V-4 | docs/executive-summary.md carries a "SUPERSEDED HISTORICAL DOCUMENT" banner while its numeric content was corrected and matches live data. The canonical summary is index.html. | Banner retained (docs file, not a data table); canonical page unaffected. Noted for review. |
| V-5 | NBA.com publishes no betting lines/odds; market-line cells remain blank and flagged across all strategy pages. | By design; flagged on Flagged for Review pages. |
| V-6 | Rank-column gap: the offline teams/standings snapshots omitted Rank, masking that Utah Jazz was published at rank 27 while the official table shows 26 (tied with Sacramento; competition ranking skips 27). First flagged by session b11f3baa (independent-audit/nba-csv-review.md); confirmed live by this session on 2026-11-04. | Fixed: data/teams-2025-26.csv rank 27 to 26; Rank prepended to both snapshots; verifier now checks Rank for teams and standings; findings.html regenerated; flag F14 published. |

## Statement

All 75 data rows (30 teams + 15 players + 30 standings) and 6 correlation pairs published in this repository matched the official NBA.com sources listed above when re-read on 2026-11-03. Zero mismatches. No value was inferred or filled in.
