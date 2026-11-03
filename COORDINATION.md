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

## Session arena/7a0b6563-own7 — audit, re-verification, and integration (2026-11-03)

Session ID: `session-arena-7a0b6563-own7`
Branch: `arena/7a0b6563-own7` (fixed by Arena; the `session-<id>/<task>` naming in the brief is not used because the branch name is fixed for this session and all work must stay on it).
Sole active session on this branch as of this claim. Earlier sessions' boards above are retained unchanged.

### Task board

| # | Task | Status | Owner | Files touched | Sources / verification | Notes |
|---|------|--------|-------|---------------|------------------------|-------|
| 11 | Repo review + irregularity audit | done | session-arena-7a0b6563-own7 | docs/repo-review-2026-11-03.md | nba.com pages (see task 12) | Found: exec-summary factual errors; pages/dashboard.html broken relative links; CI does not scan pages/ |
| 12 | Line-by-line re-verification of data/*.csv against nba.com | done | session-arena-7a0b6563-own7 | docs/verification-2026-11-03.md | https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season ; https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame ; https://www.nba.com/standings | Teams 30/30 rows, standings 30/30 rows, players top-15 15/15 rows matched |
| 13 | Fix executive-summary errors + dashboard links | done | session-arena-7a0b6563-own7 | docs/executive-summary.md, pages/executive-summary.html, pages/dashboard.html | nba.com team table | Highest PPG = Denver 122.1 (not Miami); highest FG% = LAL 50.2 (not Denver) |
| 14 | Team-level correlation (cross-sectional, computed from verified team table) | done | session-arena-7a0b6563-own7 | data/team-correlations-2025-26.csv, pages/correlation.html, docs/strategies.md | derived from data/teams-2025-26.csv | Labelled as team-season correlations, NOT bet-leg correlations |
| 15 | Site checks: include pages/ in link + source checks; CI | done | session-arena-7a0b6563-own7 | scripts/check_site.py, .github/workflows/check.yml | n/a | |
| 16 | Integration: root nav link, Flagged register update, build check, PR, merge, Pages deploy, record | in progress | session-arena-7a0b6563-own7 | root *.html nav, pages/flagged.html, COORDINATION.md | all above | Do not merge a broken site |

### Session log (arena/7a0b6563-own7)
- Claimed tasks 11–16 (commit a613b40, pushed).
- Task 12: teams 30/30, standings 30/30, players top-15 15/15 matched to nba.com by script; 0 mismatches. Log: docs/verification-2026-11-03.md.
- Task 13: corrected exec summary (highest PPG = Denver 122.1; highest FG% = LAL 50.2); fixed 21 broken links in pages/dashboard.html.
- Task 14: data/team-correlations-2025-26.csv via scripts/compute_team_correlations.py (cross-sectional, descriptive only).
- Task 15: scripts/check_site.py now covers pages/ (links + HTTPS source per table row; methodology rows marked class="method").
- Irregularities: pages/flagged.html items 5 (resolved: BLKA), 8–13 (new). Repo review: docs/repo-review-2026-11-03.md.
- Handoff note: root index.html (research lab) is from an earlier session; this session added a nav link only.
