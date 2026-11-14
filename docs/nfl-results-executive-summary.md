# NFL results & skill lab — executive summary

Session `arena/196424c5-own7`, 2026-11-14. Live pages:
[overview](https://sassnarep3-star.github.io/Own7/nfl-results.html) ·
[games](https://sassnarep3-star.github.io/Own7/nfl-results-games.html) ·
[skill](https://sassnarep3-star.github.io/Own7/nfl-results-skill.html) ·
[correlation](https://sassnarep3-star.github.io/Own7/nfl-results-correlation.html) ·
[leaderboard](https://sassnarep3-star.github.io/Own7/nfl-results-leaderboard.html) ·
[questions](https://sassnarep3-star.github.io/Own7/nfl-results-decisions.html) ·
[suggestions](https://sassnarep3-star.github.io/Own7/nfl-results-suggestions.html) ·
[flagged](https://sassnarep3-star.github.io/Own7/nfl-results-flagged.html)

## The headline

Every previous session on this repository recorded the same blocking limitation: *no NFL result
archive exists*, therefore the leaderboard is empty, ROI and closing-line value are blank, and
"luck cannot be removed". **That premise was false.** NFL.com publishes a final score for every
past game on its by-week schedule pages. The project had a retrieval gap, not a data gap.

Closing it changed what the rest of the site can honestly say. The leaderboard now has a real
graded entry. Correlation is measured rather than declared unmeasurable. And one strategy claim
survives a serious attempt to destroy it — while its sibling does not.

## What was collected

136 official final scores, weeks 1–9 of the 2026 season, plus 16 bye rows.

- Source: `https://www.nfl.com/schedules/2026/by-week/week-{1..9}`, read 2026-11-14.
- The rendered text as read is saved verbatim under `nfl-results/evidence/`.
- The parser (`nfl-results/extract.py`) re-reads only those files and **refuses to publish** unless
  the scores reproduce the frozen official standings exactly: 32 clubs × 5 fields
  (W, L, T, PF, PA) = **160 checks, all matching**. A single mismatch aborts the build.
- Week 1 is published as data but excluded from scoring, because a forecast needs prior games.

## The finding that matters

The originated board was tested on 120 scored games. Two markets, same model, same data:

| Market | Record | Hit rate | Permutation p | Both halves > 50% | Verdict |
|---|---|---|---|---|---|
| Spread (margin) | 77–43 | **64.2%** | 0.0021 | 55.0% / 70.0% | Information |
| Total (points) | 60–60 | **50.0%** | 0.59 | 48.3% / 51.7% | No signal |

The spread result also survives Benjamini–Hochberg correction for testing 30 variants
(**q = 0.022**), and stays between 57.7% and 65.4% when any single week is removed. The totals
market lands exactly on a coin flip. Publishing only the spread number would be cherry-picking,
so both sit in the same table.

**What this does not mean.** It is not proof of profit. There is no price in this project, so no
ROI, no closing-line value and no vig-adjusted edge can be computed. It is one partial season.
The family-wise chance of a fluke this good somewhere in a 30-variant search is still about 2%,
which is small but not zero.

## Luck removal, concretely

Five independent defences, all in code:

1. **Exact chance null.** Every record is priced against a fair coin by binomial tail.
2. **Benjamini–Hochberg.** Adjusted across all 30 variants; only the bench-mark survives at q ≤ 0.10.
3. **Permutation test.** Results are shuffled 20,000 times; the observed spread record is beaten by
   chance in 0.21% of shuffles (null 95th percentile: 57.5%).
4. **Split-half and leave-one-week-out.** Both halves must clear 50%, and no week may carry it.
5. **Power honesty.** About 75 settled bets are needed to detect this edge at 80% power; there are 120.

## Correlation, finally measured

Same-game leg dependence, from real joint outcomes on the originated board:

- Phi between the spread leg and the total leg: **−0.068** (p = 0.47, n = 114).
- P(home covers **and** over) observed 20.2% vs 21.9% if the legs were independent.

Small, negative, and indistinguishable from zero at this sample size. No parlay is repriced and
none is priced at all, because no price exists. Player-prop combinations stay **blank**: per-player
per-game logs were not retrieved, and guessing them would be invention.

## Leaderboard and rewards

30 variants tested (7 models × 2 markets × 2 selectivity rules, plus 2 board benchmarks).

- **Qualified: 0.** A qualified entry requires an executable price (gate RG03) and release rights
  (gate RG10). Both are blocked by the environment, and a blocked gate is never counted as a pass.
- **Provisional: 1.** The originated spread board passes all eight testable gates and earns
  **no merit points and no reward**, because a reward needs something to settle against.
- Every ROI and CLV cell on the site is `None`. This is enforced by a test, not by convention.

## Two defects found and fixed before publication

Recorded because they would each have produced a false claim:

1. **A units error** treated the combined points in a game as a per-team rate, doubling every
   implied total. Caught because implied totals (~92) were absurd against real totals (~46).
2. **Circular grading** scored a model against the board it had itself produced, which guarantees
   a 50% record and proves nothing. Replaced with proper out-of-sample and leave-one-week-out
   grading against the originated board.

Both are now pinned by tests in `nfl-results/tests/test_results.py` (23 tests).

## Questions that still block a decision

| # | Question | Still missing |
|---|---|---|
| Q01 | Is the spread edge real or luck? | A pre-kickoff price archive to convert a hit rate into money |
| Q02 | Why does the total market show nothing? | Pace, plays per game, red-zone and turnover data |
| Q03 | Do parlay legs move together enough to reprice? | A far larger sample before a small dependence is estimable |
| Q04 | Can player-prop combos be priced? | Per-player per-game logs |
| Q05 | Do weeks 1–9 injuries change those lines? | A pre-kickoff injury archive for the scored weeks |
| Q06 | Is one season enough? | Prior seasons and a forward test |
| Q07 | What edge is worth acting on? | A price, its vig, and a bankroll policy |
| Q08 | Is publication permitted? | A written licence if a redistributable dataset is ever wanted |

## Suggestions, ranked

Six proposals are published on the suggestions page, each with the evidence, cost, risk and an
acceptance test written in advance. The top three:

1. **Retrieve per-game player logs** — unlocks prop combinations, which are currently blank.
2. **Archive pre-kickoff prices under a licensed feed** — unlocks ROI, CLV and every reward.
3. **Add pace and red-zone inputs** — the reason totals failed is that the model cannot see them.

## Source and rights position

NFL.com terms §1.3 permit individual non-commercial informational use and prohibit systematic
retrieval to compile a collection without written consent. This session read published pages at
human pace, saved the rendered text it read, released no dataset and ran no feed. Nothing here is
a betting product, a recommendation, or a cash reward. Not affiliated with or endorsed by the NFL.

## Reproduce

```sh
python nfl-results/extract.py            # re-parse evidence; abort on any contradiction
python nfl-results/engine.py             # rebuild analysis.json deterministically
python -m unittest discover -s nfl-results/tests   # 23 tests
python scripts/build_site.py             # regenerate every page
python scripts/check_site.py             # links, per-row sources, blank rules, rebuild equality
```
