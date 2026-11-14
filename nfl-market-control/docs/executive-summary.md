# NFL market-control desk — executive summary

**Status:** research and paper-only controls; no live strategy. **Snapshot used by the originating board:** 12 November 2026. **This session:** 14 November 2026.

## Decision

Do **not** treat any originated number as an executable NFL line or staking recommendation. The repository has a reproducible official-results feed and model-only Week 10 outputs, but no registered, authorized sportsbook-quote source. The opening and closing market values therefore remain blank. No market difference, ROI, CLV, stake, reward or cash payout is calculated.

The new control desk publishes at [`site/index.html`](../site/index.html), with a separate quote-slot matrix, signal leaderboard, staking ledger, origination order, demotion rule, questions, suggestions and flags. The matrix is a schema/coverage manifest—not a record that a quote was offered.

## What is present

- **14** frozen Week 10 game projections; spread, total and model moneyline outputs are kept separate from external prices.
- **84** game × market × selection rows: 14 games × 3 market families × 2 sides/selections. Each row reserves an opening and a closing observation, yielding **168 expected slots**.
- **0** authorized price-snapshot records in `data/quote_snapshots.jsonl`. The quote store refuses unregistered market-price sources, unverified observations, rights authorization not recorded in the source registry, timezone-free timestamps, duplicate slots, and malformed SHA-256 digests. The digest's syntax is checked; original source evidence is not stored or independently re-hashed.
- **136** official final-score rows from the existing NFL.com Weeks 1–9 result feed. The existing extractor was rerun and reported reconciliation with the NFL standings on W-L-T, points for and points against. The stored result analysis is reproducible.
- The stored results analysis reports the originated **spread** board at **77–43 (64.2%)** and the **total** board at **60–60 (50.0%)** on 120 scored games. It tests 30 variants; one is provisional and none is qualified. These are retrospective signal measures, not ROI or proof of a profitable edge.
- The existing same-game spread/total dependence estimate is **phi −0.068401, p=0.468094, n=114**. The result page labels it as dependence of the project's own legs, not an operator-market edge. Player-prop joint outcomes remain unmeasured.
- Printed depth and replacement evidence is maintained separately in the existing [skill/depth desk](../../nfl-skill-cfdd/site/depletion.html). This control desk does not turn injury status or depth rank into a point adjustment.

## Market order and field semantics

1. **Side = point spread** — first research priority; the historical directional signal is provisional and paper-only.
2. **Total** — second; no calibrated over/under probability is available.
3. **Moneyline** — third; model fair win probabilities / American prices exist for the frozen snapshot, but no market comparison or prospective calibration exists.

Spread and total comparisons use separate fair-line, opening-line, opening-difference, closing-line and closing-difference fields (points). Moneyline comparisons use a fair model probability and the raw probability implied by any captured American price; that raw market probability includes vig and is not called an edge. Missing values stay blank.

## Signal, staking and demotion

The signal leaderboard reports outcomes, a wins–losses–pushes record, hit rate (graded decisive bets only), first/second-half rates, null tests, adjustment and uncertainty. The staking ledger is a different table for prices, stakes, net ROI, CLV and rewards. None of those economics fields is populated. There is no blended score by which a lucky stake path can promote a weak signal.

A future live strategy is sent back to paper immediately on any provenance, rights, quote freshness, settlement, risk-limit, version-control or reproducibility failure. A second trigger demotes after at least 100 settled bets if a pre-registered one-sided 95% lower confidence bound for net ROI is at or below zero. The bound must use the locked dependence and multiplicity design. This is an explicit project policy choice, not an NFL rule or a claim that 100 bets is sufficient for every market. The gate is currently **inactive** because no strategy is live; re-promotion is never automatic.

## Questions that still block a decision

1. Which provider can supply NFL opening and closing quotes with documented rights for the intended use?
2. What exact timestamp and settlement/void rule defines opening and closing?
3. Does the provisional spread signal survive a frozen prospective test?
4. What inputs and distribution calibrate the total over/under probability?
5. Are moneyline probabilities calibrated against both market sides after the agreed vig method?
6. Which dated official depth, inactives, player-log and snap data support second-/third-/fourth-string replacement estimates?
7. What player-game and market-price coverage is needed to estimate prop-combo dependence with n?
8. Which dependence-aware confidence-sequence and exposure thresholds should govern demotion?

Each question has its evidence, missing information and a discovery/closure step on the [Questions & Answers page](../site/questions.html). Six reviewable options—with cost, risk and acceptance tests—are on [Suggestions](../site/suggestions.html); none is preselected. Unverified items are on [Flagged for review](../site/flagged.html).

## Verification boundaries and sources

This session reran local receipt, extractor, model-reproduction, site, and test commands. It **did not make a fresh external NFL.com fetch**. The official links below identify the publisher's pages for manual review; local hashes and arithmetic checks do not substitute for a fresh source read or a data-use licence.

- [NFL Week 10 schedule](https://www.nfl.com/schedules/) — event context for the frozen projection board.
- [NFL 2026 by-week schedules](https://www.nfl.com/schedules/2026/by-week/week-1) — official result-feed source pages (Weeks 1–9 are linked row-by-row in the results desk).
- [NFL standings](https://www.nfl.com/standings/) — frozen model inputs and result reconciliation.
- [NFL.com Terms and Conditions](https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions) — review before systematic retrieval or publication.
- [Project repository](https://github.com/sassnarep3-star/Own7) — policy, code and reproducible artifacts.

## Reproduce

```sh
python nfl-market-control/build.py --check
python -m unittest discover -s nfl-market-control/tests -v
python nfl-results/extract.py
python nfl-results/engine.py --check
python -m nfl_origination run --check
python scripts/build_site.py
python scripts/check_site.py
```
