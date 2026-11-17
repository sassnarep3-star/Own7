# NFL decision readiness — executive summary (2026-11-17)

Desk: `nfl-readiness/`, branch `arena/383626a6-own7`, base `be2462d`.
Published pages: `nfl-readiness/site/index.html` (18 pages).
Everything below is generated from files in this repository; no number on this page was typed in by hand.

## The one-paragraph answer

The desk can originate a line, score it properly, and say exactly how much of what it sees is luck.
It cannot yet say that any of it is skill. On the 2026 corpus, the best of 21 pre-registered singles
entries (model `M04-SIDE`) earns +0.0571 Brier skill against a frozen coin-flip benchmark over weeks
6–9 (n = 57), with a week-clustered lower bound of +0.0154 — and a multiplicity-adjusted q of 0.060
across the family, a family-wise permutation p of 0.348, and a development-versus-evaluation rank
agreement of 1 position in 21. At n = 57 a genuine 55% edge would need 2,241 settled selections
(173 weeks) before it could be seen at 80% power. **0 of 21 entries qualify, and no reward exists.**

## What is verified

| Claim | Number | Where |
|---|---|---|
| Week 11 fixtures transcribed | 13 (both rest counts on 13) | `fixture-context.json` |
| Injury report rows read, 17 Nov | 347 across 28 clubs (4 on bye have no section) | `availability.json` |
| Rows carrying a game designation | 171 (70 out, 11 doubtful, 90 questionable) | `availability.json` |
| Printed depth slots transcribed | 172 across 6 clubs | `availability.json` |
| Injured players joined to a printed chart | 64 on chart, 44 with a printed replacement name | `availability.json` |
| Absences **confirmed** | **0** — no inactive list, Game Book or snap count | `availability.json` |
| Scored backtest games | 120 (week 1 excluded: no prior week to learn from) | `backtest.json` |
| Pre-registration hash | `c73e95fe07c0…`, copied into every downstream artefact | `registration.json` |

## What the evidence refuses to say

- **No market number.** No registered publisher of NFL prices permits this use, so every market cell
  is blank, no ROI or CLV exists, and no reward can be paid (gate `PG-PRICE-SOURCE`).
- **No confirmed replacement.** A depth-chart rank is not playing time. The "actual replacement"
  column is empty on all 347 rows and the reason is printed beside each one.
- **No fixed injury penalty.** The ablation's *with-personnel* arm is empty because no absence is
  confirmed, so the desk publishes an empty arm instead of an unmeasured constant.
- **No parlay.** Measured phi between side and total is −0.096 (n = 120, 95% interval −0.271 to
  +0.085), so the marginal product is wrong; and no operator void/push rule is registered. `JG-1`
  closes both same-game and cross-game combinations. Marginal products used: 0.
- **No weather.** No forecast feed and no stadium register are captured; the columns exist, are
  blank, and carry `PG-WEATHER`.

## The five findings that matter

1. **The ranking is not stable.** Development and evaluation order agree in 1 of 21 positions. The
   leaderboard is a property of weeks 6–9, not of the model, and it says so on the page.
2. **Single-test significance is the trap.** The best record (37/57) has a single-test p of 0.0166;
   the same best-of-21 under coin flips reaches 37 about 29.6% of the time (family p 0.348).
3. **Two total estimators disagree harmlessly.** M03 beats M01 by 0.14 points of MAE and 69 games to
   51, but the lines differ by an sd of 1.13 against an actual-total spread of 13.77. Neither is retired.
4. **Depth order survives a real test.** Multi-player rank-1 cells (Seattle's two receivers, two
   safeties) and an empty rank-1 cell are kept as groups rather than flattened.
5. **The prior desks' claims do not all reproduce.** Baltimore's printed quarterbacks and Washington's
   "empty slot" both failed a fresh read; both are flagged with the text that replaced them.

## The five gaps that block a decision

1. No inactive lists → "expected starter" can never become "confirmed starter" (S01/S02).
2. No permitted price → no residual against market, no ROI, no reward (S04).
3. No player-level records → no prop combinations, at all (PG-PROPS).
4. One season → no season-level holdout (PG-SEASONS).
5. Terms §1.3 forbids systematic retrieval → no daily series without written consent (S05).

## Choice on offer

Fifteen proposals are ranked on the suggestions page with cost, risk and an acceptance test, and a
decision column that is deliberately blank. The desk's own recommendation is **S01 (inactive lists)**
first: it is the single purchase of information that closes Q03 and Q19 and unblocks the ablation.
Acceptance buys the experiment, not the result.

## Reproduce

```bash
python nfl-readiness/requirements.py --check && python nfl-readiness/availability.py --check &&
python nfl-readiness/fixture_context.py --check && python nfl-readiness/backtest.py --check &&
python nfl-readiness/leaderboard.py --check && python nfl-readiness/luck.py --check &&
python nfl-readiness/correlation.py --check && python nfl-readiness/analysis.py --check &&
python nfl-readiness/questions.py --check && python nfl-readiness/suggestions.py --check &&
python nfl-readiness/strategies.py --check && python nfl-readiness/site.py --check &&
python -m unittest discover -s nfl-readiness/tests -v && python scripts/check_site.py
```

All thirteen builders are byte-reproducible; 18 contract tests pass; the recursive site audit passes
with 0 errors.
