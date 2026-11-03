# COORDINATION.md — Shared Task Board

Project: **Own7 — NBA Lines Originator** (collect, organize, analyze NBA betting lines; skill-based strategies; leaderboard; GitHub Pages site).
Session date: 2026-11-03 (UTC). Working branch: `arena/4d6319a9-own7` (fixed for this Arena session — per session rules all work happens on this branch; PR to `main` at the end).

## Sessions

| Session ID | Branch | Status | Notes |
| --- | --- | --- | --- |
| arena-4d6319a9 | arena/4d6319a9-own7 | active | Only session currently working this repo. Claims all tasks below. |

## Task Board

| # | Task | Status | Owner session | Files touched | Notes / sources |
| --- | --- | --- | --- | --- | --- |
| 1 | Repo review (line-by-line, flag irregularities) | in progress | arena-4d6319a9 | README.md, repo root | Repo contained only `README.md` ("# Own7") at start — verified via `git log`/`git status`. |
| 2 | Collect official NBA data (standings, team stats, game logs, schedule, injury reports) with source links | unclaimed | arena-4d6319a9 | data/raw/, data/processed/ | Sources: nba.com, stats.nba.com (nba.com/stats), ak-static.cms.nba.com injury PDFs |
| 3 | Collect betting lines (spread/total/ML/props) for upcoming slate from official sportsbook sources | unclaimed | arena-4d6319a9 | data/raw/lines/, data/processed/lines.json | Source: DraftKings Sportsbook (sportsbook.draftkings.com) lines as displayed on ESPN odds (espn.com/nba/odds); anything not confirmable left blank + flagged |
| 4 | Signal engine + strategy definitions (singles, parlays, prop combos) | unclaimed | arena-4d6319a9 | src/, analysis/strategies.md | |
| 5 | Validation gates + backtests (walk-forward, significance, CLV tracking, drawdown) | unclaimed | arena-4d6319a9 | src/, analysis/validation.md, data/processed/backtests.json | |
| 6 | Correlation analysis (parlay leg correlation + strategy return correlation) | unclaimed | arena-4d6319a9 | src/, analysis/correlation.md, data/processed/correlation.json | |
| 7 | Leaderboard + rewards (top-performing strategies) | unclaimed | arena-4d6319a9 | src/, data/processed/leaderboard.json, leaderboard.html | |
| 8 | Executive summary | unclaimed | arena-4d6319a9 | analysis/EXECUTIVE_SUMMARY.md | |
| 9 | GitHub Pages site build (landing + category subpages + tables + flagged page) | unclaimed | arena-4d6319a9 | index.html, *.html, assets/, site build script in src/ | Pages already configured: branch `main`, path `/`, https://sassnarep3-star.github.io/Own7/ |
| 10 | Line-by-line verification pass (every table row has official source link; blanks flagged) | unclaimed | arena-4d6319a9 | flagged.html, data/processed/verification.json, src/verify.py | |
| 11 | Final integration: PR to main, merge, Pages deploy confirm, log results here | unclaimed | arena-4d6319a9 | COORDINATION.md (log), PR | |

## Rules (from task brief)
- Claim by writing session ID + file scope (done above, single session claims all).
- Small, frequent commits; `git pull --rebase` before every push.
- Never mark verified without an official source link.
- Unverifiable values: leave blank, flag on "Flagged for Review" page.
- Shared outputs (site index/nav, table data) finalized by integration session (here: arena-4d6319a9) before PR.

## Log

- 2026-11-03 — Session arena-4d6319a9 started on branch `arena/4d6319a9-own7` (base commit 74c945e). Repo review: single file `README.md` containing `# Own7`; clean tree; no irregularities. GitHub Pages already enabled on repo (source: main `/`, build_type legacy, public, https enforced). gh auth OK (sassnarep3-star, admin on repo).
- 2026-11-03 — Sandbox network allowlist confirmed: only github.com, codeload.github.com, api.github.com, registry.npmjs.org, pypi.org, files.pythonhosted.org reachable via curl. Official web sources (nba.com, espn.com, sportsbook sites, ak-static.cms.nba.com PDFs) are accessed through the session's verified page-fetch/search tools; raw captures saved under data/raw/ with URL + fetch timestamp for provenance.
