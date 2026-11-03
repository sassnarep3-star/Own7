# Line-by-line verification — 2026-11-03

Session: `session-arena-7a0b6563-own7` (branch `arena/7a0b6563-own7`).
Method: official NBA.com pages were fetched through the Arena fetch tool. Each page's values were transcribed and compared with the repository CSV, column by column, by script (team table 30 rows × 18 mapped columns; standings 30 rows × 10 columns; players 15 rows × 25 columns). Total: 0 mismatches in 60 rows. stats.nba.com JSON was tried again and is still unreachable from the sandbox, so every check uses the nba.com HTML pages.

## Results

| Dataset | Official source (fetched 2026-11-03) | Rows checked | Matched | Mismatches | Notes |
|---|---|---|---|---|---|
| `data/teams-2025-26.csv` | https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season (5 chunks, all read) | 30 of 30 | 30 of 30 | 0 | Every mapped column matched: GP, W, L, WIN%, PTS, FG%, 3P%, FT%, OREB, DREB, REB, AST, TOV, STL, BLK, PF, PFD, +/-. Not in CSV: MIN, FGM, FGA, 3PM, 3PA, FTM, FTA, BLKA. |
| `data/standings-2026-27.csv` | https://www.nba.com/standings (2 chunks, all read) | 30 of 30 | 30 of 30 | 0 | Programmatic comparison (W, L, WIN%, GB, CONF, DIV, HOME, ROAD, LAST10, STREAK).  Notes text is flagged (see below). |
| `data/players-2025-26-top15.csv` | https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame (chunks 2 and 3, ranks 1–15) | 15 of 15 | 15 of 15 | 0 | Programmatic comparison of 25 columns (Rank through PF). Rank, GP, W, L, MIN, PTS, FGM, FGA, FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%, OREB, DREB, REB, AST, TOV, STL, BLK, PF matched. Team codes mapped to full names. |
| `docs/executive-summary.md`, the superseded `pages/executive-summary.html` copy | Derived from the team table above | 2 claims | 0 of 2 correct before fix | 2 | Corrected. See below. |
| `root index.html` (2023-24 league averages) | https://www.nba.com/news/2023-24-nba-stats-survey-league-scoring-averages | 2 values | 2 of 2 | 0 | Pace 99.2 and offensive efficiency 114.5 confirmed. |
| `root index.html` (pace / offensive rating definitions) | Same NBA page (footnotes: "Pace = Possessions per team per 48 minutes", "OffRtg = Points scored per 100 possessions") | 2 | 2 | 0 | The NBA glossary (https://www.nba.com/stats/help/glossary) was fetched but only its first chunk was read, which does not include the PACE entry. The definition was confirmed from the survey page instead. |

## Corrections made in this session

1. **Highest team PPG** was stated as Miami Heat 120.9. Official value: **Denver Nuggets 122.1**. Miami 120.9 is second. Corrected in `docs/executive-summary.md` and the superseded `pages/executive-summary.html` copy.
2. **Highest team FG%** was stated as Denver Nuggets 49.6%. Official value: **Los Angeles Lakers 50.2%**. Denver 49.6% is second. Corrected in both files.
3. **Correlation register** showed an assumed value ("blank (assumed 0)") for cross-game legs. Changed to blank, per the no-inference rule.
4. **`pages/dashboard.html` (pre-merge)** used root-relative paths from inside `pages/`. 21 links and the stylesheet and script paths were broken. Fixed.

## Unchanged, verified in this session

- Team-table values in `data/teams-2025-26.csv` (30 rows) — no change.
- Player top-15 values in `data/players-2025-26-top15.csv` (15 rows) — no change.
- Standings values in `data/standings-2026-27.csv` (30 rows) — no change.

## Irregularities found (also listed on review.html, F02 and F10–F13)

| # | Item | Official source | Disposition |
|---|---|---|---|
| 1 | Standings note reads "~8 games played" for every team. Actual games played (W+L) are 5 to 8. Phoenix (1-4) has 5 games and different wording. | https://www.nba.com/standings | Values match. Note text flagged for the next refresh. |
| 2 | The "unmapped" teams-table column is BLKA (blocks against). It was excluded on purpose. | https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season | Resolved. |
| 3 | stats.nba.com JSON endpoint is unreachable from the sandbox. | https://stats.nba.com | Open. Blocks play-by-play correlation. |
| 4 | NBA.com publishes no betting odds or player-prop lines. | https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season | Market cells remain blank (see flagged page). |
| 5 | Team-level correlations are season cross-sections (n = 30), not bet-leg correlations. | data/team-correlations-2025-26.csv | Labelled as descriptive. |

## Reproduce

- Team correlations: `python3 scripts/compute_team_correlations.py`
- Site checks: `python3 scripts/check_site.py` (local links, plus an HTTPS source on every table row except rows marked `class="method"`)
- Verified-data site: `python3 scripts/verify_verified_site.py`
