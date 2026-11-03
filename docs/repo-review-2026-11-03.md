# Repo review — 2026-11-03

Scope: every top-level file, `pages/`, `docs/`, `data/`, `scripts/`, `.github/workflows/`, `verified/`, and `COORDINATION.md`. Official sources for data claims: see docs/verification-2026-11-03.md.

## What was checked

| Area | Method | Result |
|---|---|---|
| Data CSVs | Compared against official nba.com pages, column by column | Data correct (see verification log) |
| Executive summary | Compared against official team table | 2 factual errors, corrected |
| Internal links | `scripts/check_site.py` (extended to `pages/`) | Was not covered before. Dashboard page had 21 broken links, fixed. All links now resolve. |
| Table source links | Every `<tbody>` row must carry an HTTPS source | Was not covered for `pages/`. Found 10 rows with none; fixed or marked as methodology (class `method`). |
| CI | `.github/workflows/check.yml`, `verify-verified-site.yml` | Both run; `check.yml` now covers `pages/` too. |
| Root landing (research lab) | Nav links | Root site did not link to the NBA data dashboard. Link added to every root page. |
| COORDINATION.md | Read in full | Earlier board is retained. Its header still shows the older branch name `arena/687b658b-own7` and is out of date. |

## Irregularities (for your review)

See pages/flagged.html for the register with source links. Summary:

1. Executive summary had the wrong highest-PPG and highest-FG% team (corrected).
2. Standings note "~8 games" is approximate; actual games played are 5 to 8.
3. Cross-game correlation cell said "assumed 0" (changed to blank).
4. Dashboard page links were broken (fixed).
5. stats.nba.com unreachable, so no play-by-play correlations (open).
6. Two repos of pages: root `index.html` is a separate research-lab landing from an earlier session; the NBA data site is under `pages/`. Both are now linked.
7. `verified/` uses non-NBA sources (AGLC, Play Alberta, GameSense, Boston Globe report, Government of Alberta). They are outside the NBA-only rule of the main site; owner decision needed.
8. The Verified-data site's `leaderboard.json` and `strategies.json` contain 0 strategies. Nothing is ranked yet.
9. COORDINATION.md header is stale (see above).

## What this review did not do

- It did not re-verify the `verified/` site's regulator and news claims line by line. Those are outside the NBA scope and are listed as flagged in `verified/data/flagged.json`.
- It did not verify the odds or prop-line cells, because no official source publishes them.
