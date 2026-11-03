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
