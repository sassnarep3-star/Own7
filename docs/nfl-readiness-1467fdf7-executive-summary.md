# NFL decision-readiness desk — executive summary (2026-11-17)

**Desk:** [`nfl-readiness-1467fdf7/site/index.html`](../nfl-readiness-1467fdf7/site/index.html) · branch `arena/1467fdf7-own7` · registration commit `813ce25`

## Bottom line

- **No strategy is qualified, no reward is paid, and no price is used.** Nothing in the repo can yet support a betting decision.
- **Results are verified, prices are not.** 136 official final scores (weeks 1–9) are in the repo, one of them a tie (Giants 27, Commanders 27) confirmed on the official week-5 page. There is still no opening line, no licensed close, and no executable price, so ROI, CLV and reward remain blank.
- **Naive picks do not beat chance.** Always-home and seeded random picks sit near 50% (49.6% each, n = 135). The record-based control reaches **60.7%** (82 of 135; 95% interval 52.3%–68.6%). It fails the sample gate (n ≥ 153), and its 95% lower bound (52.3%) sits below the chance band's upper edge (58.5%), so it is not distinguishable from chance at this sample size. It stays on paper.
- **The availability desk disagrees with the official Week 10 page on three Detroit rows.** Of 44 rows compared for four complete clubs, 3 differ (Kerby Joseph's practice status; Amon-Ra St. Brown and Sione Vaki's injury and game status). The cause is open because the desk stores a date, not a clock time.
- **The brief's largest requirement is blocked by the NFL's terms.** Scheduled daily captures, immutable archives and a point-in-time ledger are systematic retrieval to compile a database, which [NFL.com Terms §1.3](https://www.nfl.com/legal/terms/) prohibits without written consent. No scheduled capture was added.

## What the decision-readiness table says

79 requirement rows, grouped A–G. Status counts: 7 Built, 6 Built here, 2 Resolved in part, 24 Partial, 18 Not started, 12 Blocked (data), 6 Blocked (rights), 2 Decision needed, 2 Rejected by the brief. 25 rows link an official source; the other rows are internal methods, decisions or repo states, and are marked "none (internal)" rather than given a false link.

The rows that are blocked and the number that would clear each one are listed on the landing page. Examples:

| Requirement | Blocked by | Number that would clear it |
|---|---|---|
| Price snapshots and ROI | No opening line; no licensed close | Opening and closing numbers for 136 games × 3 markets from a permitted source |
| Two-stage leaderboard, Brier skill | No stored probability forecasts | ≥ 153 settled probability forecasts (the sample size for 80% power at a one-sided 5% level to detect 60% against 50%: ((1.645·√0.25 + 0.8416·√0.24)/0.1)² ≈ 152.5, rounded up) |
| Injury reads with clock time | NFL.com §1.3 | Written consent or a licensed feed, then timestamped captures |
| Depth for all 32 clubs | Route (a) verified for fewer than 32 clubs | 32 of 32 clubs verified |
| Parlays and prop combos | No joint-probability evidence | A validated joint probability and void/push rules |

## Controls and the removal-of-luck panel

Pre-registered in [`strategies.py`](../nfl-readiness-1467fdf7/strategies.py) and committed at `813ce25` before the controls ran. Rules: straight-up winner only; ties excluded; picks use only earlier weeks; record ties go to the home team; week 1 goes to the home team.

| Control | n | Hit rate | 95% interval | Result |
|---|---|---|---|---|
| C-RAND (seed 20261117) | 135 | 49.6% | 41.3%–58.0% | is the chance reference |
| C-HOME (always home) | 135 | 49.6% | 41.3%–58.0% | below 50% overall; halves 56.2% / 43.7% |
| C-REC (higher prior win %) | 135 | 60.7% | 52.3%–68.6% | fails G3 (n < 153) and G4 (lower bound inside band); halves 57.8% / 63.4% |

Chance band (10,000 seeded replicates): 41.5%–58.5%. The cross-referenced spread board from the results desk (in-sample backtest, not a leaderboard entry) shows 64.2% over 120 bets with permutation p = 0.0021; that figure is flagged because the brief forbids backtest numbers on the leaderboard (F08).

## Spread board multiplicity

- `nfl-results/analysis.json`: best directional test BOARD-SA has p = 0.001223 (120 bets, 77 wins, 64.2%).
- The file's family-wise false-positive figure, 0.0218, uses `strategies_tested` = 18. Its leaderboard counts 30 tested.
- Recomputed here from the same best p-value: 1 − (1 − 0.001223)^18 ≈ 0.022 and 1 − (1 − 0.001223)^30 ≈ 0.036.
- Register row E03 now shows both figures. No entry is qualified, so the figure is not a claim.

## Injury spot-check

The official Week 10 page was read on 2026-11-17 (saved text, SHA-256 `8bc949124864…`, [evidence file](../nfl-readiness-1467fdf7/evidence/nfl-injuries-week10-2026-official-read-2026-11-17.md)). Source: [nfl.com/injuries](https://www.nfl.com/injuries/).

- Complete clubs compared: WAS, NYG, NE, DET (44 rows). Disagreements: DET only (3).
- KC was not compared: the saved read stops after Patrick Mahomes. Chunks 1–7 of the 8 official chunks are unread; this is recorded, not inferred.
- The brief's live row count (279) is not reconciled with the desk's 326 rows; neither was confirmed by a full read of the eight pages (F06).
- The brief says Cincinnati lists 4 players; the desk has 8; the official Cincinnati table was not read (F05). Seattle matches the brief's 15.

## Decisions needed from you

1. **F01 — Rights.** Do you obtain written consent from NFL Enterprises, buy a licensed feed, or drop the scheduled-capture requirements? Six requirements depend on this. §1.3 and §11(f) of the terms both restrict systematic retrieval.
2. **F15 — Price-data policy.** Which source is permitted for opening and closing prices, and on what terms? No backtest or ROI can be published until this is decided.
3. **F16 — Public vs private layers.** The repo publishes row-level CSVs (for example 326 injury rows). Should raw rows move to a private store until the terms are read?
4. **F17 — Reward policy.** No reward is defined. Confirm that rewards stay blank until a strategy passes G1–G7.
5. **D05 — Depth route.** Route (a) (per-club official depth pages) or route (b) (snap counts)? Route (a) is the only one that could be verified club by club, and it needs 32 clubs checked.

## Flags for review

Twenty flags are on the [Flagged for review page](../nfl-readiness-1467fdf7/site/flagged.html): 19 open, 1 closed (the tie, F11). F20 is attached to every register row that has no repo artefact, so blank evidence is never unflagged. F18 records that the registry's description of NFL terms §12 does not match the page read. F19 records that the week-5 schedule page has no row in the source registry; adding one would change the pricing desk's week-page attribution, so it was not added. The highest-severity open items are the three Detroit disagreements (F02, F03), the Cincinnati count (F05), the unreconciled row count (F06), the backtest figure on the results leaderboard (F08), and the non-official closing prices behind one correlation (F09).

Other desks' data and content were **not** changed. Their generated pages gained one readiness navigation entry from the root build, and nothing else; this was checked token by token against the base commit (46 pages). One attempt in this session added registry rows that changed another desk's attribution; it was reverted and is recorded here. Where a file in another desk is wrong (for example the stale Kerby Joseph row in `nfl/origination/data/injuries-2026-w10.csv`, F10), the fix is logged for that desk's owner.

## What this session did not do

- No scheduled or repeated capture of nfl.com (blocked by F01).
- No full read of the eight-page injury report; only the first chunk, which covers four complete clubs.
- No NFL Game Book, depth-chart, snap-count, transaction or roster-event capture.
- No probability forecasts, Brier scores, CLV or ROI.
- No NWS weather overlay and no roof designation capture.
- No change to the results, pricing, lifecycle or availability desks' data. Their pages gained only the readiness navigation entry.

## Reproduce

```sh
python nfl-readiness-1467fdf7/controls.py          # rebuild controls.json
python nfl-readiness-1467fdf7/injury_check.py      # rebuild the injury comparison
python nfl-readiness-1467fdf7/build.py             # rebuild the desk pages
python nfl-readiness-1467fdf7/build.py --check     # byte-identical reproduction
python -m unittest discover -s nfl-readiness-1467fdf7/tests -v
```

NFL data is attributed to NFL.com. This project is not affiliated with or endorsed by the NFL. Nothing here is a betting recommendation.
