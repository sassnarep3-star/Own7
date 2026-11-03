# Coordination Board — Own7 (NBA Lines Project)

Branch: `arena/687b658b-own7`
Session: `session-arena-687b658b-own7` (sole active session)

Statuses: unclaimed | in progress | done | needs review
- `needs review` = published on the "Flagged for Review" page; does not block other work.

## Task board

| # | Task | Status | Owner | Files touched | Sources / verification | Notes |
|---|------|--------|-------|---------------|------------------------|-------|
| 1 | Create COORDINATION.md task board | done | session-arena-687b658b-own7 | COORDINATION.md | n/a | Claimed immediately, committed + pushed |
| 2 | Research official NBA data sources (stats.nba.com, NBA.com) | in progress | session-arena-687b658b-own7 | docs/sources.md | stats.nba.com, NBA.com | Verify each source link is reachable |
| 3 | Data collection framework & validation gates | unclaimed | session-arena-687b658b-own7 | data/, docs/validation-gates.md | Official NBA stats only | Values not confirmable → blank + flagged |
| 4 | Strategy development: single bets, parlays, player prop combos, correlation | unclaimed | session-arena-687b658b-own7 | docs/strategies.md | Official NBA stats | Skill-based, no manual input |
| 5 | Executive summary | unclaimed | session-arena-687b658b-own7 | docs/executive-summary.md | All task sources | |
| 6 | GitHub Pages site: landing page + category subpages, data tables | unclaimed | session-arena-687b658b-own7 | site/ (HTML/CSS/JS) | Linked per table row | Clean dashboard UI |
| 7 | Line-by-line verification pass; Flagged for Review page | unclaimed | session-arena-687b658b-own7 | site/flagged.html, docs/verification.md | Official sources per row | Blank + unverified where no official source |
| 8 | Integration: re-verify combined data, build check, no broken links | unclaimed | session-arena-687b658b-own7 | All | All task sources | Final integration session |
| 9 | PR from integration branch to main + merge; confirm GitHub Pages deploy; record PR link + result | unclaimed | session-arena-687b658b-own7 | main branch, GitHub Pages | COORDINATION.md | Do not merge a broken site |

## Rules for this session
- Single session active; claim each task by updating status to `in progress`, commit + push immediately.
- Scopes are non-overlapping within this session; work line by line, verify from official verified trusted sources.
- Never infer or fill in values; leave blank + flag as unverified if no official source confirms.
- Small, frequent commits; `git pull --rebase` before every push.
- On conflict: stop, resolve without discarding other work, log in this board.
