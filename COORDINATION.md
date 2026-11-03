# Coordination board

| Task | Status | Owner | File scope |
|---|---|---|---|
| Repository review, NBA research, site and final integration | needs review | arena-b0cbee88 | README.md, COORDINATION.md, site files, .github/workflows |

## Log
- 2026-11-03: Claimed integration work. Repository initially contained only README.md; no existing task board. This session uses the Arena-assigned branch, rather than creating a separate session branch.

## Integration notes
- Initial review: README.md contained only `# Own7`; no data, strategies, or existing site were present.
- Official NBA glossary checked for pace and ratings: https://www.nba.com/stats/help/glossary. The NBA 2023–24 survey was checked for the historical league averages displayed: https://www.nba.com/news/2023-24-nba-stats-survey-league-scoring-averages.
- Official NBA injury snapshot checked for its dated nature: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-02_05_30PM.pdf. scikit-learn documentation checked for time-order and calibration: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html and https://scikit-learn.org/stable/modules/calibration.html. NIST source on bootstrap uncertainty: https://nvlpubs.nist.gov/nistpubs/ir/2018/NIST.IR.8218.pdf.
- Irregularities: no historical executable market prices, joint observations, models, backtests, reward funding or competition operator; no actual edge, correlation, ranking or skill claim can be verified. Published on Flagged for Review. Gate thresholds and candidate signals are explicitly proposed, not verified findings. Luck cannot be eliminated.
- Verification: `python3 scripts/check_site.py` verifies local relative links and an HTTPS link in each table body row. It does not verify third-party link availability or support for claims. Sources were reviewed against the specific factual claims; proposals are labeled as such.
- Pull request: https://github.com/sassnarep3-star/Own7/pull/1. Implementation complete; unresolved data and empirical validation are flagged on the site. Merged at bd4db431002e26d28be67585d638bc0a4aae4ffd; GitHub Pages deployment run https://github.com/sassnarep3-star/Own7/actions/runs/41706106982 succeeded. The automated Pages workflow warned that its upload action targets deprecated Node 20 and is forced onto Node 24; build and deploy passed.

---

## Session 5051651b — verified-data site (`verified/`)

Shared task board for all agent sessions working on `sassnarep3-star/Own7`.

**Branch note:** this session is bound to branch `arena/5051651b-own7` (fixed by Arena). The
`session-<id>/<task>` naming in the brief cannot be used by this session; all work stays on
`arena/5051651b-own7`. Logged as an irregularity on the Repo Review page.

**Session ID:** `5051651b` (single session active at time of claim; no other sessions detected in repo)

**Status legend:** unclaimed · in progress · done · needs review (published on Flagged for Review; does not block)

| # | Task | Status | Owner | Files touched (scope) | Sources / verification | Log |
|---|------|--------|-------|-----------------------|------------------------|-----|
| T1 | Repo review (line-by-line, irregularities) | done | 5051651b | `verified/repo-review.html`, `data/repo_review.json` | GitHub repo, commit 74c945e, Pages API (see page) | RR-01–RR-12 recorded; irregularities flagged |
| T2 | Research: official NBA data & betting-rule sources | needs review | 5051651b | `data/sources.json`, `data/rules.json` | nba.com/stats, aglc.ca, aglc.ca/gaming/igaming, playalberta.ca | NBA numeric data NOT retrieved (blocked); NBA Oct-2026 memo reported by media only (R-05–R-08, flagged) |
| T3 | Responsible gambling / Alberta helplines | done | 5051651b | `data/helplines.json`, `verified/responsible-gambling.html` | gamesenseab.ca, selfexclusion.ca, myhealth.alberta.ca | 1-866-461-1259 left blank (unofficial only) – flagged F-04 |
| T4 | Strategy framework, validation gates, correlation method | done | 5051651b | `data/strategies.json`, `data/gates.json`, `data/correlation.json`, `data/leaderboard.json`, pages | internal method; inputs link to official sources | 0 strategies tested, 0 passing gates; all metrics blank |
| T5 | Executive summary + Flagged for Review page | done | 5051651b | `verified/executive-summary.html`, `verified/flagged.html`, `data/flagged.json` | all of the above | F-01–F-07 flagged |
| T6 | Site build, verification script, GitHub Pages deploy (integration) | in progress | 5051651b | `verified/index.html`, `verified/assets/*`, `scripts/*`, `README.md`, Pages config | `scripts/verify_verified_site.py` | integration run by the same session (only active session) |

## Log

- 2026-11-03 — 5051651b — Claimed T1–T5. Verified reachability: `fetch_page` reaches nba.com and aglc.ca / gamesenseab.ca / selfexclusion.ca / myhealth.alberta.ca. Direct `stats.nba.com` and `cdn.nba.com` JSON endpoints returned errors (HTTP 500 / failed), so no official box-score or odds data could be pulled. See Repo Review page.
- 2026-11-03 — 5051651b — T1–T5 completed on branch `arena/5051651b-own7`. Site generated by `scripts/build_site.py`; verified by `scripts/verify_verified_site.py` (9 data files, 178 internal links, 11 pages; official-source and blank-value rules pass).
- 2026-11-03 — 5051651b — Irregularities logged: NBA stats endpoints unreachable; Oct-2026 NBA memo reported only by media; AGLC homepage vs. iGaming page conflict on operators; conflicting Alberta helpline number; repo has no license; Pages source must switch to `/docs`.
- 2026-11-03 — 5051651b — Handoff: none. No other session claimed any task.
- 2026-11-03 — 5051651b — Integration: PR https://github.com/sassnarep3-star/Own7/pull/3 (`arena/5051651b-own7` → `main`) opened. Merge and Pages deploy to follow.
- 2026-11-03 — 5051651b — Merge conflict: `main` gained PRs #1 and #2 from session arena-b0cbee88 while this branch was open. Both sides kept in full. Conflicting filenames renamed: this session's checker is `scripts/verify_verified_site.py` (not `scripts/check_site.py`, which belongs to arena-b0cbee88) and this session's builder is `scripts/build_verified_site.py`. The verified-data site moved from `docs/` to `verified/` so it does not overwrite the root site. A link from the root index points to `verified/`.
- 2026-11-03 — 5051651b — Handoff: none. Other session's files untouched except the root `index.html` link and the README/COORDINATION merge.
- 2026-11-03 — 5051651b — Integration re-verification of arena-b0cbee88 citations (line-by-line for the cited numbers): NBA 2023–24 survey page confirms pace 99.2 and offensive efficiency 114.5 (https://www.nba.com/news/2023-24-nba-stats-survey-league-scoring-averages). NBA glossary page loads (https://www.nba.com/stats/help/glossary); only the first of 10 chunks was read, so the full PACE/OffRtg entries were NOT fully re-read (noted, not blocking). Injury PDF link and scikit-learn/NIST links were NOT re-fetched in this session.
- 2026-11-03 — 5051651b — Added `.github/workflows/verify-verified-site.yml` (new file) to run `scripts/verify_verified_site.py` on push/PR.
