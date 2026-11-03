# Independent NBA data spot audit

Audit session: `session-arena-b11f3baa-own7`. Inspected 2026-11-03 UTC via the official NBA pages linked below, using rendered page content. This is a field-limited audit, not a complete verification of every field or the entire repository. A source link is not evidence that every field on a row has been checked. Blank cells mean not checked here, not zero. Source pages, particularly current standings, change over time.

## Material irregularities for integration

1. `docs/executive-summary.md` and `pages/executive-summary.html` label Miami (120.9 PPG) highest, but the [official NBA 2025–26 team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) shows Denver at 122.1, higher than Miami. Remove the highest assertion or independently establish the actual leader.
2. The same files label Denver (49.6%) highest FG%, but the NBA table shows the Lakers at 50.2%. Remove the highest assertion or independently establish the actual leader.
3. `data/teams-2025-26.csv` labels Utah rank 27; the NBA team table displays 26, tied with Sacramento. Flag that cell and check its copies; do not infer a tie-breaking rank.
4. `docs/verification.md` claims all numerical fields match; that claim is contradicted by Utah’s rank. The source table header explicitly labels the omitted field between BLK and PF as BLKA; exclusion is safe, but the assertion that it was unambiguously unmappable should be re-evaluated.
5. The team and player individual URLs currently returned headers but no historical statistical table in this audit’s fetch output. The season-filtered league-wide tables below rendered the actual numbers; use them for manual review, and do not equate the presence of a team or player link with field-level evidence.
6. The dynamic standings lack a captured response timestamp and archive in the CSV, and can change. Its generic “~8 games” note is especially imprecise for Phoenix, which has five games in the displayed snapshot.
7. `docs/verification.md` and `docs/executive-summary.md` reference `site/pages/flagged.html`, which is not present in this checkout; the existing path is `pages/flagged.html`. Check all duplicates and any claims of comprehensive verification.

## Team rows: limited field review

Primary source for each row: [NBA team traditional table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame). Only Denver PTS and FG%, Lakers PTS and FG%, Miami PTS and Utah rank were individually compared here; every other field is unverified by this audit. `Rank` on the NBA source refers to the rendered table order/rank, not postseason conference seeding.

| CSV line | Team | Checked field(s) | Result | Official source |
|---:|---|---|---|---|
| 2 | Oklahoma City Thunder |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 3 | San Antonio Spurs |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 4 | Detroit Pistons |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 5 | Boston Celtics |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 6 | Denver Nuggets | PTS 122.1; FG% 49.6 | match | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 7 | Los Angeles Lakers | PTS 116.3; FG% 50.2 | match | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 8 | New York Knicks |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 9 | Cleveland Cavaliers |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 10 | Houston Rockets |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 11 | Minnesota Timberwolves |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 12 | Atlanta Hawks |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 13 | Toronto Raptors |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 14 | Orlando Magic |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 15 | Philadelphia 76ers |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 16 | Phoenix Suns |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 17 | Charlotte Hornets |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 18 | Miami Heat | PTS 120.9 | match | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 19 | LA Clippers |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 20 | Portland Trail Blazers |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 21 | Golden State Warriors |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 22 | Milwaukee Bucks |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 23 | Chicago Bulls |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 24 | Dallas Mavericks |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 25 | New Orleans Pelicans |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 26 | Memphis Grizzlies |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 27 | Sacramento Kings |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 28 | Utah Jazz | Rank: CSV 27; source 26 | mismatch | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 29 | Brooklyn Nets |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 30 | Indiana Pacers |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 31 | Washington Wizards |  | unverified in this audit | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |

## Player rows: limited field review

For each row below, GP, W, L, and PTS were checked against the [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame); all other fields (including rank eligibility, age, team name expansion and source URL fidelity) were not independently checked. W and L refer to games in which the player appeared.

| CSV line | Player | Checked GP / W / L / PTS | Result | Official source |
|---:|---|---|---|---|
| 2 | Luka Doncic | 64 / 43 / 21 / 33.5 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 3 | Shai Gilgeous-Alexander | 68 / 56 / 12 / 31.1 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 4 | Anthony Edwards | 61 / 37 / 24 / 28.8 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 5 | Jaylen Brown | 71 / 47 / 24 / 28.7 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 6 | Tyrese Maxey | 70 / 38 / 32 / 28.3 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 7 | Kawhi Leonard | 65 / 37 / 28 / 27.9 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 8 | Donovan Mitchell | 70 / 45 / 25 / 27.9 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 9 | Nikola Jokic | 65 / 43 / 22 / 27.7 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 10 | Giannis Antetokounmpo | 36 / 17 / 19 / 27.6 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 11 | Joel Embiid | 38 / 24 / 14 / 26.9 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 12 | Lauri Markkanen | 42 / 17 / 25 / 26.7 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 13 | Stephen Curry | 43 / 24 / 19 / 26.6 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 14 | Devin Booker | 64 / 37 / 27 / 26.1 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 15 | Jalen Brunson | 74 / 50 / 24 / 26.0 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |
| 16 | Kevin Durant | 78 / 48 / 30 / 26.0 | match for listed fields only | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame) |

## Current standings rows: limited field review

For each row below, W and L were compared to the [NBA standings](https://www.nba.com/standings) at fetch time. All other fields were not independently checked in this audit; standings are time-sensitive and this is not a permanent historical capture.

| CSV line | Team | Checked W / L | Result | Official source |
|---:|---|---|---|---|
| 2 | Philadelphia 76ers | 7 / 1 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 3 | Detroit Pistons | 6 / 1 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 4 | Boston Celtics | 5 / 2 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 5 | Washington Wizards | 4 / 3 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 6 | Toronto Raptors | 4 / 3 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 7 | Cleveland Cavaliers | 4 / 3 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 8 | Atlanta Hawks | 4 / 4 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 9 | New York Knicks | 3 / 4 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 10 | Charlotte Hornets | 3 / 5 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 11 | Miami Heat | 2 / 5 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 12 | Orlando Magic | 2 / 5 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 13 | Indiana Pacers | 2 / 6 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 14 | Chicago Bulls | 1 / 6 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 15 | Milwaukee Bucks | 1 / 6 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 16 | Brooklyn Nets | 1 / 6 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 17 | Houston Rockets | 7 / 1 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 18 | Memphis Grizzlies | 6 / 1 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 19 | Portland Trail Blazers | 5 / 1 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 20 | Los Angeles Lakers | 6 / 2 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 21 | Oklahoma City Thunder | 5 / 2 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 22 | San Antonio Spurs | 5 / 2 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 23 | Golden State Warriors | 5 / 3 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 24 | Minnesota Timberwolves | 5 / 3 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 25 | Dallas Mavericks | 4 / 3 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 26 | Denver Nuggets | 3 / 3 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 27 | New Orleans Pelicans | 3 / 4 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 28 | Phoenix Suns | 1 / 4 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 29 | LA Clippers | 1 / 6 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 30 | Sacramento Kings | 1 / 6 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |
| 31 | Utah Jazz | 1 / 6 | match for listed fields only | [NBA standings](https://www.nba.com/standings) |

## Handoff

Integration owner: flag the discrepancies publicly, remove or correct unsupported statements only after source review, recheck every remaining field, preserve another session’s work, and run the site checks before merging. This audit does not establish betting edges, correlations, performance rankings, reward funding, or a working data pipeline.
