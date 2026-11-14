# NFL skill & availability desk — executive summary (2026-11-14)

Session `arena/cfdd5580-own7`. Every figure below is reproduced by a committed script and is
published on the site at `nfl-skill-cfdd/site/`. Nothing here is estimated.

## The one-paragraph answer

All 32 club standings rows were re-read from the official NFL standings page on 2026-11-14 and
re-derived arithmetically: 30 are identical to the frozen 12 November snapshot and the 2 that moved
(WAS, NYG) are explained by exactly one result, WAS 24 – NYG 21, which falls out of the two
published rows without consulting the score. Four clubs had never had a printed depth chart
captured — CHI, DEN, PHI, TB — and they turn out to be **the four Week 10 bye clubs**, which is
exactly why the gap stayed silent: a bye club has no injury row, so a missing chart never showed up
as an unmatched player. All four are now captured (231 printed slots), raising the injury-to-chart
match to **265 of 326 rows**, with 127 of those rows on offence, 126 on defence and 12 on special
teams. Finally the skill question was tested rather than asserted: the
Pythagorean residuals across 32 clubs give a chi-square of **19.03 on 32 degrees of freedom,
p = 0.966**, a variance inflation of **0.59**. That is inside the null and on the *under*-dispersed
side, so this snapshot contains no detectable club-level skill. **Zero strategies qualify, zero
leaderboard scores are published, and zero rewards are paid.**

## What the data will not support, and why

| Asked for | State | Blocking reason |
|---|---|---|
| Originated lines graded against a market | blanks | no price exists; NFL.com publishes no odds and the rights question is unsettled |
| Single-bet, parlay and prop-combo strategies | 10 defined, **all BLOCKED** | no price (V8), no settled bets (V4/V9), no measured leg dependence (V6) |
| Correlation values for parlays and props | **blank** | leg correlation needs settled joint outcomes; none exist. Club-level r is a *different quantity* and is labelled as such |
| Rewards for top strategies | **none paid** | 153 settled independent bets needed at a 60% rate; there are 0 |
| Point value for an injured starter | **blank** | a printed rank is an ordering, not a measurement; needs snap counts + a before/after series |

## The number that actually decides the competition

From the exact binomial, at 80% power and one-sided α = 0.05:

| True win rate | Settled independent bets needed |
|---|---|
| 52.4% (a strong bettor) | 2,682 |
| 55.0% | 617 |
| 57.5% | 274 |
| 60.0% | 153 |
| 50.0% (break-even) | *blank — cannot be distinguished from itself* |

Luck is not removed by a better model. It is removed by this table.

## What was added

- **Re-verification** — 32/32 rows re-derived; `PCT = (W + T/2)/(W+L+T)` and `NET = PF − PA` on
  every row; league identities `PF = PA = 6,291` and `W = L = 136` enforced, with the build
  aborting otherwise (`collect.py`).
- **Depth coverage** — 4 charts, 231 slots, plus a published record that Houston renders an image
  and no table on two independent reads (`depth.py`, `evidence/depth-*.md`).
- **Depletion index** — 326 injury rows joined to printed ranks for 31 of 32 clubs, offence and
  defence in separate columns, weights disclosed, no point value invented (`index.py`).
- **Skill vs luck** — executed overdispersion test, sample-size table, chance-streak table,
  three correlations with Fisher intervals and Holm adjustment (`luck.py`).
- **Strategies and gates** — 10 strategies, **12 gates computed by scripts** (6 pass, 5 fail,
  1 blocked on rights), leaderboard ranked on evidence debt (`ledger.py`).
- **Decision layer** — 15 questions, 10 suggestions with runnable acceptance tests, 12 flags, and a
  **deliberately blank** choice record (`decisions.py`).
- **Site** — 15 self-contained, source-linked pages; every table row links its official source;
  unknown cells are `data-empty` and asserted blank by a test (`build.py`).

## Verification actually run

```
python -m unittest discover -s tests                        # 109 pass (inherited, unchanged)
python -m unittest discover -s nfl-skill-cfdd/tests         # 66 pass (new)
python scripts/nfl_extract.py --check                       # OK
python -m nfl_origination run                               # 14 originated games
python scripts/build_site.py                                # 38 canonical + 20 redirects + 83 auxiliary
python scripts/check_site.py                                # 141 pages, 0 errors
npm run test:browser                                        # 121 desktop + 121 mobile, WCAG A/AA
```

Special functions are checked against published table values (chi-square, normal, Student-t,
incomplete beta, binomial upper tail) so a silent break in the statistics fails the build rather
than publishing a wrong number.

## Three decisions worth making now

1. **Settle the rights question (P02).** It blocks prices, parlays, props and rewards alike.
2. **Read the 28 club Friday reports (P01).** Game status goes from 4 clubs to 28 and cross-checks
   a league aggregate that at least one club already contradicts in public.
3. **Start the forward shadow ledger (P03) this week.** It is the only path to the 153 settled
   bets, and every week without it is a week the competition cannot start.

What is *not* worth doing: refining a model against this snapshot. At p = 0.966 there is nothing
there to refine, and more modelling on eight games would manufacture confidence.

## Three defects found in this session's own work, and fixed

Kept here because they are the useful part of the audit trail, and because each one would have
published a plausible-looking wrong number.

1. **Depth slots were matched on the wrong key.** A club restarts its slot numbering for every
   printed position, so "slot 1" appears many times inside one unit. Keying a lookup on
   (club, unit, slot) attached the wrong backup to the wrong starter. The key now includes the
   printed position, and every named replacement is verified by a test to be the rank+1 name
   printed in the same slot of the same chart.
2. **118 of 265 matched rows carried a position label that did not match between the club's chart
   and the league's report**, and several were on the wrong side of the ball - a receiver located
   at his punt-return slot (PR), a linebacker at SAM. That silently moved players between the
   offence and defence columns of the depletion index. Fixed with a published position-group map
   and three stated precedence rules; zero wrong-side matches remain, and a test asserts it.
3. **Typed prose drifted from the computed value** - a sentence said "seven" beside a computed 8.
   Every count on the affected pages is now read from the JSON, so prose cannot drift again.

Two ambiguities remain and are **published rather than resolved**:

- **24 of 265 matched rows** are players their own club prints in more than one slot, one of them a
  ruled-out starter. The join uses one slot per player (highest printed rank wins) and marks every
  affected row (flag CF13).
- **Houston** prints no readable chart on two independent reads, so its 16 injury rows keep a blank
  rank and a blank replacement (flag CF06).

## Limits

One partial season, 8–9 games per club. No price, ROI or CLV. No leg dependence. No point value for
an injury. Single-source availability, with a documented club/league disagreement. Rendered-text
evidence class, not an HTTP archive. No repository licence inferred or granted; third-party terms
remain applicable. Not affiliated with or endorsed by the NFL or any club.
