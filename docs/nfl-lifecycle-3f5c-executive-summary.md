# Market-lifecycle desk — executive summary (session arena/3f5c4cd6-own7, 2026-11-14)

Live pages: [`nfl-lifecycle-3f5c/site/index.html`](../nfl-lifecycle-3f5c/site/index.html) ·
[Price snapshots](../nfl-lifecycle-3f5c/site/price-snapshots.html) ·
[Fair / market / diff](../nfl-lifecycle-3f5c/site/fair-market-diff.html) ·
[Signal vs staking](../nfl-lifecycle-3f5c/site/leaderboard.html) ·
[Demotion gate](../nfl-lifecycle-3f5c/site/demotion.html) ·
[Replacement depth](../nfl-lifecycle-3f5c/site/replacement-depth.html)

## What this desk adds

Eight requirements from the 2026-11-14 brief, each mapped to a deterministic, source-linked
artefact inside `nfl-lifecycle-3f5c/`. No pre-existing page, value or test was overwritten;
integration with the shared site is additive only.

| Requirement | Artefact | Result |
|---|---|---|
| Price-snapshot store (opening and closing numbers for every originated market) | `snapshots.py` → `data/price-snapshots.json` | 42 records (14 games × side/total/moneyline); opening = v2026-11-12, closing = v2026-11-14 for the 13 pre-kickoff games, terminal for the one played game; append-only policy; market cells blank with a stated reason (XS09/CF10). |
| Verified results feed so backtests are possible | consumed read-only (`nfl-results/analysis.json`, 136 official scores) | 30 graded variants re-published on the lifecycle leaderboard; tiers inherited verbatim. |
| Originate side → total → moneyline | `stages.py` → `data/origination-order.json` | Three explicit stages with disclosed dependencies; reconciles field-for-field with the canonical engine (14/14, 0 mismatches). |
| Fair line, market line, difference as separate columns | `site/fair-market-diff.html` | Three columns per market per game; market and difference blank for all 42 rows until a rights-cleared price source exists; difference is computed only when both inputs exist. |
| Separate signal from staking | `leaderboard.py` → `site/leaderboard.html` | Two tables; `rank_by_signal()` reads only signal fields and raises otherwise; a test proves permuting/corrupting staking fields cannot move a rank; staking table has no rank column. |
| Track depth of the replacement | `depth.py` → `site/replacement-depth.html` | Read-only over the cfdd injury × depth join: 173 starter losses, 158 with a printed named next-in-line; 72 rows print no backup; 61 rows not on any chart; 12-row spot re-verification, 12/12 traced. |
| Correlations only from official numbers, with n | `corr_audit.py` → `site/correlation-audit.html` | 22 published rows audited: every coefficient carries n ≥ 3 and registered official sources; 4 blanks carry stated reasons; 0 failures. |
| Demotion gate back to paper | `demotion.py` → `site/demotion.html` | DG-1 pre-registered with fixed triggers D1–D5 (alpha 0.01 / 0.05, Brier margin 0.05, integrity, governance); state machine paper → live → paper(demoted); armed and idle at 0 live entries; unit-tested on synthetic windows. |

## Fresh official attestation performed this session (2026-11-14)

* `https://www.nfl.com/standings/` read (2 chunks): all 32 rows traced verbatim; 30 identical to
  the frozen 2026-11-12 snapshot; NYG 5-2-1→5-3-1 and WAS 2-5-1→3-5-1 moved exactly per the
  officially published Thursday result.
* `https://www.nfl.com/schedules/2026/REG10/` read (3 chunks): all 14 fixtures with kickoff
  windows and networks re-attested; byes CHI/DEN/PHI/TB confirmed; **"Commanders 24, Giants 21,
  FINAL"** printed by the page — consistent with the standings scoring delta (WAS +24/+21,
  NYG +21/+24).
* Evidence saved verbatim under `nfl-lifecycle-3f5c/evidence/`; three new register entries
  (`LC-NFL-STANDINGS-1114`, `LC-NFL-SCHED-REG10-1114`, `LC-NFL-GAME-W10-01`).

## What the snapshot store already teaches

The only non-zero open→close moves between the two vintages are 13 total-market moves of about
−0.0022 points (the league scoring anchor shifted when the Thursday result entered the standings).
Side and moneyline did not move for the 13 pre-kickoff games: the league term cancels in the
margin algebra (margin = (home_off + away_def + league)/3 + hfa − (away_off + home_def +
league)/3). That is a fact about the model, not about any market — and exactly the kind of fact a
snapshot store exists to expose. A real market-side open/close history requires the rights-cleared
price source that suggestion LS01 asks the reviewer to approve.

## Verification performed

`python scripts/build_site.py` → 46 canonical + 104 auxiliary pages · `python scripts/check_site.py`
→ passed (170 recursive pages, 6,875 tbody rows, 170 registered sources, 0 errors) ·
`python -m unittest discover -s tests` → 111 pass · `python -m unittest discover -s
nfl-lifecycle-3f5c/tests` → 37 pass · `python nfl-lifecycle-3f5c/build.py --check` → byte-identical ·
`python -m nfl_origination run --check` → reproduces exactly · `npm run test:browser` → 150 desktop +
150 mobile pages, WCAG A/AA, 10 interaction groups, no runtime errors · `python scripts/nfl_extract.py
--check` → OK.

## Flags this desk adds

LC-F01 (capture-hour caveat for the terminal W10-01 close), LC-F02 (no market price anywhere —
rights), LC-F05 (Houston depth chart still unobtainable), LC-F07 (72 no-backup + 61 not-on-chart
injury rows), all published with sources on the desk's Flagged page. Explained flags: LC-F03
(anchor-invariance of side/ML), LC-F04 (publisher rounds winning percentage half-up; Python's
default is half-even), LC-F06 (unnamed standings column, inherited CF02), LC-F08 (gate never
operated on a live entry yet).

## Decisions requested from the reviewer

10 questions and 10 suggestions (each with evidence, unlocks, cost, risk, acceptance test) are on
the desk's Questions and Suggestions pages with deliberately blank decision records. Highest
leverage: LS01 (approve a rights-cleared price source — unlocks market columns, difference,
CLV, ROI, rewards, a meaningful gate), LS03 (injury/depth-adjusted variant as a pre-registered
paper trial on the saved weeks 1–9 scores), LS04 (sensitivity sweep for HFA and margin-sd,
closes gate G07's FAIL), LS06 (paper replay of DG-1 over the graded history).
