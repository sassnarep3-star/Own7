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

## Active integration — session-arena-a934e8c3-own7 (2026-11-03)

Branch: `arena/a934e8c3-own7` (the fixed Arena branch; no additional branches/worktrees will be created).

The boards above are historical records, not current verification. The last repository commit is dated 2026-11-03 19:57 UTC, over 60 minutes before this session. The incomplete integration claim in the first historical board is superseded by the completed integration in its second board and this explicitly claimed re-audit. Other sessions' branches and open PR #4 are left untouched. This session is the final integration owner of the scopes below; please log cross-scope change requests here rather than editing these files concurrently.

| ID | Task | Status | Owner | Exclusive file scope | Verification / notes |
|---|---|---|---|---|---|
| A1 | Audit every tracked text/data/workflow file; quarantine unsupported claims and inventory provenance | done | session-arena-a934e8c3-own7 | README.md, docs/**, data/**, verified/** | Prior “verified” labels are not accepted without fresh source checks. |
| A2 | Official-source research; reproducible line origination, correlations, validation and leaderboard protocol | needs review | session-arena-a934e8c3-own7 | research/**, nba_lab/**, tests/**, requirements.txt, pyproject.toml | No invented observations, odds, coefficients, returns or winning strategies. |
| A3 | Integrate a single accessible category dashboard and Flagged for Review page | done | session-arena-a934e8c3-own7 | *.html, pages/**, assets/**, css/**, js/** | All data-table rows must expose an official source or an explicit unverified blank. |
| A4 | Automated audits, CI, link/build/browser checks and deployment integration | in progress | session-arena-a934e8c3-own7 | scripts/**, .github/**, .gitignore, package.json, package-lock.json | External official domains may be inaccessible in this environment; record failures, never relabel as verified. |
| A5 | PR, merge, Pages deployment confirmation and final evidence | in progress | session-arena-a934e8c3-own7 | COORDINATION.md | Push only this branch; record PR/deploy IDs and any infrastructure limitations. |

Claim committed and pushed before implementation. Historical source and deploy claims above will be independently checked where possible and otherwise explicitly qualified.

### A1/A2 progress — independent source and calculation checks

- Re-read the existing 54 tracked files (2,630 text lines); preserved baseline file paths, complete line scopes and SHA-256 hashes in `research/audit/baseline-inventory.json`. Historical claims not retained as facts unless rechecked.
- Rechecked all 30 team rows, 15 scoring-filtered player rows and 30 standings rows via the exact NBA URLs in `research/evidence/receipts.json`. Corrected Utah’s tied rank (26) and identified incorrect executive-summary maxima (Denver PTS 122.1; Lakers FG% 50.2). Team conference/division fields not supported by that table were removed.
- Collected every row of an explicitly date-filtered, one-page 32-game Jokić log. Rejected an ignored LastNGames filter/paginated scope. Saved normalized transcriptions, NOT claimed raw HTTP captures.
- Implemented dependency-free correlation, paired circular-block intervals, threshold-event joint rates, chronological retrospective probability demos, proper scores, pricing primitives, Holm adjustment and fail-closed leaderboard contracts. 52 Python tests passed; results reproduce exactly. No ROI, CLV, executable prices, cash prizes or winning strategies invented.
- Important official restriction: [NBA Terms §9](https://www.nba.com/termsofuse) expressly prohibits using NBA Statistics in connection with any gambling activity, including legal gambling. Separate permission is not established. Bulk collection, NBA-derived betting-price release, cash wagering and payments remain disabled. Statistical audit/methodology demonstration only. F09 published with the integration site.
- Method sources freshly checked: [NBA glossary](https://www.nba.com/stats/help/glossary), [NBA injury policy](https://official.nba.com/nba-injury-report-2026-27-season/), [SciPy Pearson](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html), [scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html), [time splits](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html), [statsmodels Holm](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html), [Dutch regulator](https://kansspelautoriteit.nl/voor-spelers), [GitHub Pages docs](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).
- Next integration step: replace the conflicting public views with one generated, source-linked dashboard; publish all unresolved items, the full per-file audit and requirements traceability; run recursive/static/browser/CI checks before PR/merge.

### A1/A2 completion; A3/A4 integration verification

- Full baseline per-file dispositions and all 26 request-to-evidence entries are published in `research/audit/file-review.json` and `research/requirements.json`. This is review coverage, not a blanket re-verification of withdrawn historical claims.
- Runtime source-rights no-go now rejects missing/enabled rights or cash flags. The NBA-specific demo cannot emit betting prices. Generic synthetic pricing math is separate.
- 57 Python tests pass, including future-outcome leakage, malformed gate evidence, common offer/event-universe enforcement, duplicate identities and timestamp-aware ranking. Source/code hashes regenerated; no qualified candidate, ROI or cash amount.
- A unified generated dashboard and 19 legacy redirects have passed initial recursive checks (33 HTML files, 391 source-linked body rows, 431 local references) and 14 desktop + 14 mobile WCAG A/AA/interaction checks. Improved contrast, touch targets, visible text links and navigation focus; test screenshots are ignored artifacts, not source data.
- Final CI/source-health automation, final browser rerun and PR/Pages verification are still in progress; no new deployment is claimed yet. Earlier claim runs 41740265168/41740264896 and backend runs 41741617837/41741617880 completed successfully.

### Final local verification before integration PR

- A1 complete; A3 complete. A2 research/software complete, **needs review for actual strategy qualification and source rights**: all eight candidates blocked and all nine unresolved items publicly listed. No manual user input or approval is being requested.
- Full final local run: 57/57 Python tests, byte-identical research/site rebuilds, 33 recursive HTML paths, 391 source-linked table body rows and 431 valid local references; zero unresolved local links/fragments. External references counted, not falsely claimed to have all received HTTP checks.
- Chromium 153.0.8010.0: 14 desktop + 14 mobile pages; no WCAG 2.0/2.1/2.2 A/AA automated violations; no JS/network/console errors; nine interaction groups including numeric keyboard sorting, CSV with source URLs, search/reset, all 19 redirects, no-JS reading and mobile focus restoration. Automated accessibility checks do not replace every manual assistive-technology review.
- Final local testing caught incomplete guard/fixture edits; fixed and the entire suite rerun successfully before this push. No broken revision is being merged. Source-rights flags cannot enable prices/collection/cash through config.
- Scheduled source checks are deliberately non-mutating availability audits, not numerical scrapes or factual certification. Legacy verification script names forward to the integrated checks.
- Test evidence: `research/audit/{check-results,static-checks,browser-checks}.json`. Screenshots/temporary CSVs/dependencies/bytecode are ignored rather than committed. Live preview binds 0.0.0.0 and serves only public files, not .git or dependencies.
