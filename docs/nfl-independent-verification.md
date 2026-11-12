# Independent verification of the NFL section — 2026-11-12

A second, separate session re-derived every published number in the NFL research
section from the committed snapshots and reports what does not reconcile.

The verifier is `nfl/verify_independent.py`. It shares **no code** with
`nfl_lab/engine.py`, the module that produced the published figures. It
reimplements Pearson and Spearman correlation, the league standings identities
and the NFL passer-rating formula independently. A coding error in one
implementation therefore cannot silently confirm itself in the other.

Run it with:

```sh
python nfl/verify_independent.py
```

Exit code 0 means the published numbers follow from the published inputs. It does
**not** mean the inputs match the live official pages — that is a separate,
dated act recorded in `research/sources.json` and `research/nfl-protocol.json`.

## What was checked

| Check | Input | Result |
|---|---|---|
| Club count, duplicates, conference split | `data/nfl-standings-2026.csv` | 32 clubs, 16 AFC / 16 NFC |
| `NetPts = PF − PA` on every row | standings | 32/32 |
| `PCT = (W + T/2) / (W + L + T)` on every row | standings | 32/32 |
| Home + road games = total games | standings | 32/32 |
| Home + road wins = total wins | standings | 32/32 |
| Division ≤ conference component-wise | standings | 32/32 |
| `Last5` totals five games | standings | 32/32 |
| League wins = league losses | standings | 135 = 135 |
| League PF = league PA | standings | 6,246 = 6,246 |
| Home team-games = road team-games | standings | 136 = 136 |
| Every published Pearson and Spearman | `research/nfl-results.json` | 7/7 to 1e-6 |
| `Cmp% = Cmp / Att` | passing | 25/25 |
| NFL passer rating from Att/Cmp/PassYds/TD/INT | passing | 25/25 within 0.15 |

The blank-by-design coefficients are listed on the page rather than omitted, so
that an absent value is visible instead of implied.

## The one real discrepancy

Two printed yards-per-attempt values cannot be reached by rounding from the same
row's own yards and attempts:

| Player | Printed | Yard / attempts | Exact | Delta |
|---|---|---|---|---|
| Patrick Mahomes | 7.8 | 2,037 / 263 | 7.7452 | +0.0548 |
| Deshaun Watson | 7.2 | 1,806 / 249 | 7.2530 | −0.0530 |

A published one-decimal rate may legitimately differ from its own inputs by at
most half a unit in the last place, that is 0.05. Both rows exceed that.

I re-fetched `https://www.nfl.com/stats/player-stats/` on 2026-11-12 and the
official page still prints 2,037 / 263 / 7.8 and 1,806 / 249 / 7.2. **Therefore
this is a disagreement between columns inside the publisher's own table, not a
transcription error in this repository.** It is recorded as irregularity **NF12**
on the Flagged for Review page.

Neither value reconciles by a one-attempt difference, so the most likely
explanations are a rounding convention applied to an unrounded upstream value, or
a stats cut refreshed at a different moment than the yardage columns. **Neither
explanation is asserted as fact**, because no official statement of the
convention was found. What is asserted is the arithmetic: the columns disagree.

## Effect on the published analysis

The only coefficient that uses that column is Yds/Att versus passer rating:

| Basis | Pearson | Spearman |
|---|---|---|
| Column as printed | 0.829085 | 0.870763 |
| Exact PassYds / Att | 0.831578 | 0.870899 |
| Difference | 0.0025 | 0.0001 |

The published figure is internally consistent with the column it names, so it
stands as the descriptive statistic it claims to be. The exposure is published
rather than hidden. No conclusion in the project depends on it, because no
strategy has cleared a single evaluation gate.

## A correction during this review

My first attempt attributed both rows to the publisher rounding half away from
zero. That was **wrong**: 7.7452 and 7.2530 are not half-way values, so no
rounding convention reconciles them. The hypothesis was discarded and replaced by
the arithmetic test above. Recording this because the first explanation would
have been a comfortable and incorrect story.

## Scope limits

- This verifies internal consistency only. It does not adjudicate whether the
  snapshot matches the live page, and it cannot detect a transcription error that
  is arithmetically self-consistent.
- It does not test profitability, predictive value, calibration or edge. There is
  no price data and no qualifying strategy.
- Correlations are cross-sectional and descriptive. They say nothing about
  bet-leg dependence, which needs aligned game logs that are not collected.
