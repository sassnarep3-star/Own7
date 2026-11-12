# Repository review — 12 November 2026 (NFL session `arena/20394b77-own7`)

Scope: the repository as inherited at `a989d67` plus the NFL additions. This is a **consistency and provenance review**, not a re-verification of inherited NBA or rental claims; those are out of scope and untouched.

## 1. What the repository contained at session start

- 150 tracked files, three coexisting programmes (NBA research, two overlapping SF-rental presentations, one market-evidence register), one generated static site with a single build script and a strict output contract.
- No NFL data, page, source, test or workflow step existed: no tracked file path at `a989d67` contains `nfl`.

## 2. Contract discovered and reused

`scripts/check_site.py` enforces: every HTML page registered in `research/site-manifest.json` with a matching SHA-256; every table body row carrying registered source IDs **and** a link to the registered URL; every blank cell genuinely empty; HTTPS only; no protocol-relative links; single `h1`/`main`; `lang="en"`; deterministic rebuild byte-identical. `scripts/build_site.py` regenerates all canonical pages plus auxiliary sub-sites and rewrites the manifest.

The NFL sub-site was built to that contract rather than beside it, so any violation fails the whole site check.

## 3. Line-by-line checks performed

| # | Check | Result |
|---|---|---|
| 1 | Arithmetic identity `PCT = (W + 0.5T)/(W+L+T)` on all 32 standings rows | 32/32 pass |
| 2 | Arithmetic identity `NET = PF − PA` on all 32 rows | 32/32 pass |
| 3 | League-wide `ΣPF = ΣPA` (each point scored is a point allowed) | 6,246 = 6,246 over 272 team-games |
| 4 | Games played per club ∈ {8, 9} and total implied games even | 16 clubs on 8, 16 on 9, 136 games |
| 5 | Every club in the Week 10 slate has a standings row; no club appears twice | 28 distinct, 0 duplicates |
| 6 | Clubs in the standings but not in the slate | CHI, DEN, PHI, TB (reason not published — flagged F-06) |
| 7 | Every injury row's club is in the slate; `(club, player)` unique | 210 rows, 0 duplicates |
| 8 | Practice status cross-check between the injury page and the official Wednesday roundup | Agrees on every overlapping player |
| 9 | Every depth-chart starter with a status joins to an injury row by exact name | 36 rows join; 3 name variants documented (Mack Wilson Sr., Ronnie Hickman Jr., Deebo Samuel Sr.) |
| 10 | Every depth row's status matches the injury table exactly | pass after the three aliases were resolved |
| 11 | No depth row invents a backup where the club chart lists none | 5 "no backup/no second/no third" rows verified against the chart |
| 12 | Every source URL is HTTPS on a closed host allowlist | 76 registered IDs; 11 NFL-era hosts |
| 13 | Every source ID used in any CSV/JSON is registered, and every registered ID is used | 0 orphans both directions |
| 14 | Every table body row on every page has registered IDs and its own source link | 1,241 rows across 68 HTML pages |
| 15 | No market price, edge, ROI or leg correlation appears anywhere | 0 found; market column blank on all 14 projections |

## 4. Irregularities found (and what was done)

| ID | Irregularity | Disposition |
|---|---|---|
| I-01 | README described the repository as an NBA lab only and did not mention the NFL or rental sections | README updated with an explicit section-status banner; full restructuring left as suggestion S-11 |
| I-02 | Legacy `verified/` directory name reads as a verification claim, although its JSON files are deprecated pointers | Left in place to preserve URLs; recorded as flag F-14 |
| I-03 | Three overlapping rental presentations (root `rental*.html`, `rental/`, `rent-*.html`) with separate builders | Not modified; recorded for review (R-06) |
| I-04 | `COORDINATION.md` carries several historical boards whose claims of exclusive ownership overlap | Earlier boards retained verbatim; this session appended a scoped board only |
| I-05 | PR #17 from an earlier session still open | Not touched; this session opened its own PR |
| I-06 | Cleveland depth chart lists Michael Burton at RB while the injury report calls him a fullback | Published as a documented position-mismatch row rather than silently reconciled |
| I-07 | Two source typos in the official roundup ("limted", "hamtring") | Status normalised to the policy's three categories; the typo is recorded in the row note |
| I-08 | `research/results.json` hashes `research/sources.json`, so adding NFL sources made the NBA research result stale | `python -m nba_lab run` regenerated it; diff confirmed **only** `run_hash` and the `sources.json` input hash changed — no NBA value was altered |
| I-09 | `nfl.com/teams/depth-chart` and `nfl.com/odds/` both return 404 | Registered as scope-limit sources with the exact paths checked, not as proof of universal absence |
| I-10 | WCAG 2.2 target-size failure on new sidebar footer links in the browser suite | Fixed with `nfl/style.css` (stacked 32 px targets); suite then passed 48 desktop + 48 mobile pages with zero axe violations |

## 5. What was not verified

- Anything outside `nfl/**`: the NBA and rental claims were not re-read against their sources in this session.
- External HTTP status of every cited URL: pages were read through a fetch tool, not attested by a direct HTTP check. The two 404 paths are the exception, where the 404 page itself was observed.
- Factual truth of an official page beyond the values transcribed: the checks establish transcription integrity and internal consistency, not that the league's page is correct.
