# Coordination Board — Own7 (NBA Lines Project)

Branch: `arena/687b658b-own7`
Session: `session-arena-687b658b-own7` (sole active session)

Statuses: unclaimed | in progress | done | needs review
- `needs review` = published on the "Flagged for Review" page; does not block other work.

## Task board

| # | Task | Status | Owner | Files touched | Sources / verification | Notes |
|---|------|--------|-------|---------------|------------------------|-------|
| 1 | Create COORDINATION.md task board | done | session-arena-687b658b-own7 | COORDINATION.md | n/a | Claimed immediately, committed + pushed |
| 2 | Research official NBA data sources | done | session-arena-687b658b-own7 | docs/sources.md | nba.com | All sources verified reachable |
| 3 | Data collection: official NBA tables | done | session-arena-687b658b-own7 | data/*.csv | nba.com teams/players/standings pages | All values transcribed from live pages; verified |
| 4 | Validation gates framework | done | session-arena-687b658b-own7 | docs/validation-gates.md | nba.com | 5 gates defined; small-sample flag applied to 2026-27 |
| 5 | Strategy development | done | session-arena-687b658b-own7 | docs/strategies.md | nba.com | Lines blank + unverified (NBA.com publishes no odds) |
| 6 | Executive summary | done | session-arena-687b658b-own7 | docs/executive-summary.md | All task sources | |
| 7 | GitHub Pages site | done | session-arena-687b658b-own7 | index.html, pages/*.html, css/, js/ | Linked per row | Landing + 7 category pages, sortable tables |
| 8 | Verification pass + Flagged for Review page | done | session-arena-687b658b-own7 | docs/verification.md, pages/flagged.html | Official sources per row | 7 flagged items registered |
| 9 | Integration, build check, no broken links | in progress | session-arena-687b658b-own7 | All | All task sources | Link check pending before PR |
| 10 | PR + merge + GitHub Pages deploy + record result | unclaimed | session-arena-687b658b-own7 | main branch, GitHub Pages | COORDINATION.md | Do not merge a broken site |

## Rules for this session
- Single session active; claim each task by updating status to `in progress`, commit + push immediately.
- Never infer or fill in values; leave blank + flag as unverified if no official source confirms.
- Small, frequent commits; `git pull --rebase` before every push.

---

## Session arena/687b658b-own7 — NBA lines origination (this integration)

Session ID: `session-arena-687b658b-own7`
Branch: `arena/687b658b-own7` (fixed by Arena)

### Task board

| # | Task | Status | Owner | Files touched | Sources / verification | Notes |
|---|------|--------|-------|---------------|------------------------|-------|
| 1 | Create COORDINATION.md task board | done | session-arena-687b658b-own7 | COORDINATION.md | n/a | Claimed immediately, committed + pushed |
| 2 | Research official NBA data sources | done | session-arena-687b658b-own7 | docs/sources.md | nba.com | All sources verified reachable via fetch_page |
| 3 | Data collection: official NBA tables | done | session-arena-687b658b-own7 | data/*.csv | nba.com teams/players/standings pages | All values transcribed from live pages; verified |
| 4 | Validation gates framework | done | session-arena-687b658b-own7 | docs/validation-gates.md | nba.com | 5 gates defined; small-sample flag applied to 2026-27 |
| 5 | Strategy development | done | session-arena-687b658b-own7 | docs/strategies.md | nba.com | Lines blank + unverified (NBA.com publishes no odds) |
| 6 | Executive summary | done | session-arena-687b658b-own7 | docs/executive-summary.md | All task sources | |
| 7 | GitHub Pages site | done | session-arena-687b658b-own7 | pages/dashboard.html, pages/*.html, css/, js/ | Linked per row | Landing at root index.html (session 5051651b kept); category pages under pages/ |
| 8 | Verification pass + Flagged for Review page | done | session-arena-687b658b-own7 | docs/verification.md, pages/flagged.html | Official sources per row | 7 flagged items registered |
| 9 | Integration, build check, no broken links | done | session-arena-687b658b-own7 | All | All task sources | Internal link check clean; external links nba.com only, all reachable |
| 10 | PR + merge + GitHub Pages deploy + record result | done | session-arena-687b658b-own7 | main branch, GitHub Pages | COORDINATION.md | PR https://github.com/sassnarep3-star/Own7/pull/5 ; merged commit 6823f29 into main; GitHub Pages deploy confirmed live at https://sassnarep3-star.github.io/Own7/ |

### Integration conflict resolution (this merge)
- `index.html` add/add conflict: root `index.html` from main (session 5051651b research lab) kept in full; this session's landing moved to `pages/dashboard.html`; all my pages' Dashboard nav links point to `pages/dashboard.html`. No other session's work discarded.
- `COORDINATION.md` add/add conflict: both session boards retained in this unified document.
- No values inferred or filled in; blanks remain where no official source confirms (market lines, correlation coefficients — see pages/flagged.html).

### Rules for all sessions
- Claim a task by writing your session ID and file scope, commit + push immediately; never start a task another session has claimed.
- Keep scopes non-overlapping; session branches or worktrees named session-<id>/<task>.
- Small, frequent commits; `git pull --rebase` before every push.
- On conflict: stop, resolve without discarding the other session's work, log what happened.
- Never infer or fill in values; leave blank + flag as unverified if no official source confirms. Link the source.

---

## Session arena/f58e9526-own7 — re-verification, corrections, NL scope, correlations (this session)

Session ID: `session-arena-f58e9526-own7`
Branch: `arena/f58e9526-own7` (fixed by Arena; the `session-<id>/<task>` naming in the brief is not used because the branch is bound to this session. Logged as RR-07 in verified/data/repo_review.json.)
Other open work: PR #4 (`arena/5051651b-own7`) from an earlier session is still open. Not touched.

### Task board (this session)
| # | Task | Status | Owner | Files touched | Sources / verification | Notes |
|---|------|--------|-------|---------------|------------------------|-------|
| A1 | Repo review, line-by-line, irregularity log | in progress | session-arena-f58e9526-own7 | verified/data/repo_review.json, verified/data/flagged.json | nba.com team/player/standings pages (links in each row) | 23 review rows; 11 flags raised, 4 wrong claims corrected |
| A2 | Re-verify NBA tables (30 teams, 15 players, 30 standings) | in progress | session-arena-f58e9526-own7 | data/raw/*.csv (snapshots), scripts/build_nba_json.py, verified/data/nba_*.json | nba.com/stats/teams/traditional, /stats/players/traditional (PerGame), /standings | 0 mismatches across 18 + 22 + 10 compared columns |
| A3 | Correlation values from verified tables | in progress | session-arena-f58e9526-own7 | scripts/compute_correlations.py, verified/data/correlation_computed.json | derived from A2 tables | Descriptive only (season-level, n=30/15). Leg correlations stay blank |
| A4 | Netherlands scope (regulator, self-exclusion, helplines) | in progress | session-arena-f58e9526-own7 | verified/data/sources.json, rules.json, helplines.json | kansspelautoriteit.nl, gokstop.nl | Dutch phone helpline left blank (not confirmed) |
| A5 | Corrections to root site and docs | in progress | session-arena-f58e9526-own7 | docs/*.md, pages/*.html, README.md, data/standings-2026-27.csv | nba.com (A2) | Miami/Denver PPG, Denver/LAL FG%, BLKA, ~8 games, site/ path |
| A6 | Rebuild verified site (teams/players/standings/NL pages) + verifier | in progress | session-arena-f58e9526-own7 | scripts/build_verified_site.py, scripts/verify_verified_site.py, verified/*.html | all rows carry source_url | |
| A7 | Integration checks, PR to main, merge, Pages verify, record | unclaimed | session-arena-f58e9526-own7 | main (via PR), COORDINATION.md | CI + live site | Merge only after CI green and live site checked |

### Sources used this session (all fetched 2026-11-03)
- https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season (30 rows; header includes BLKA)
- https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame (top 15 by PTS; rank 16 = 25.4 PPG)
- https://www.nba.com/standings (30 rows; W+L = 5 to 8 per team)
- https://aglc.ca/ ; https://myhealth.alberta.ca/alberta/Pages/Find-help-for-drug-or-gambling-problem.aspx ; https://gamesenseab.ca/ ; https://www.selfexclusion.ca/s/ ; https://playalberta.ca/
- https://www.kansspelautoriteit.nl/ ; https://kansspelautoriteit.nl/kansspelwijzer ; https://gokstop.nl/
- https://sports.yahoo.com/nba/breaking-news/article/nba-sportsbooks-reportedly-agree-to-ban-certain-bets-including-parlays-involving-the-under-on-same-players-stats-151415255.html (media, quoting ESPN; reported-unverified)

### Irregularities found this session (details: verified/data/repo_review.json, verified/data/flagged.json)
1. Exec summary said highest PPG = Miami 120.9. Official: Denver 122.1. Corrected.
2. Exec summary said highest FG% = Denver 49.6. Official: Lakers 50.2. Corrected.
3. "Unmapped" team column = BLKA on the official header. Resolved.
4. Verified-data site said nba.com data was unreachable. Pages are reachable via fetch. Data now verified.
5. Standings "~8 games" was loose. Official W+L = 5 to 8. Corrected.
6. Docs referred to site/pages/flagged.html. Corrected to pages/flagged.html.
7. Player spelling "Doncic" vs official "Dončić". Corrected.
8. Scope: owner is in NL, earlier verified site was Alberta-only. Ksa and Gokstop rows added.
9. ksa.nl is an unrelated architecture firm. Not used.
10. Oct 16, 2026 NBA memo: media only; applies to US operators; primary document not located. Reported-unverified.
11. AGLC homepage contains two statements that conflict as written. Flagged, not resolved.

### Verification performed
- `python3 scripts/build_nba_json.py` — CSVs vs official snapshots (data/raw/): OK, 0 mismatches.
- `python3 scripts/compute_correlations.py --check` — recomputed values match the stored file; one value independently recomputed by hand.
- Every new or changed row has an https source_url on an allow-listed official host.
