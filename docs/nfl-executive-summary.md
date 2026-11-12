# NFL research - executive summary

Snapshot 2026-11-12 · session `session-arena-a129b881-own7` · live site: https://sassnarep3-star.github.io/Own7/

## One paragraph

The NFL section is built, sourced and reproducible, and it overturns nothing. Sixty-six rows were
read from official NFL.com pages and re-derived before publication. The scoring information is
real and mildly informative: a points-based expectation separates clubs better than a coin flip
(Brier 0.1575 against 0.25 on 32 clubs). Fourteen Week 10 games now have originated spreads,
totals and fair prices that come from one coherent score pair each. What does **not** exist is a
market: no sportsbook price, limit, hold or settlement rule was retrieved, so every ROI,
closing-line value and market-comparison cell is blank rather than zero. No strategy is ranked, no
reward exists, and nothing on the site is a recommendation.

## Five things that matter

1. **The data is real and re-checkable.** 32 standings rows, 20 injury rows and 14 fixtures, each
   with an official URL and a check date. The extractor re-parses the saved page text on every
   build and aborts instead of publishing a number that fails its own arithmetic check.
2. **The scoring signal is exploratory, not a strategy.** The Pythagorean baseline beats a flat
   guess inside this snapshot. That is one partial season, scored in-sample, with a published
   exponent. It cannot support a claim of forward predictive skill.
3. **Nothing is far from expectation.** Every club is within about 2.2 wins of its points-based
   expectation. Denver and Tampa Bay are the widest gaps. In nine games that is ordinary noise,
   not a mispriced market.
4. **The injury requirement is documented but not measured.** Official statuses are published for
   20 players in one game. No depth chart and no snap share was retrieved, so "second- or
   third-string replacement" impact is blank on purpose, with a named fix.
5. **Four gaps block any reward decision.** A dated market price, a starter/backup depth source,
   per-player usage data, and a measured same-game leg dependence. Each has a ranked suggestion.

## What is decided and what is not

| Ready | Not ready |
|---|---|
| Publishing this as a non-commercial research note | Claiming any edge over a market |
| Showing originated numbers as a labelled model exercise | Ranking or rewarding a strategy |
| Keeping every blank visible and linked to a cause | Converting an injury status into lost points |
| Reproducing every number from saved official text | Asserting forward predictive skill |

## The review workflow you asked for

`nfl-suggestions.html` ranks ten proposals by decision value. Each names the question it closes,
what it unlocks, what it costs and what happens if it is skipped. `nfl-decisions.html` splits what
we know from what we do not. `nfl-questions.html` holds fourteen questions, each with a sourced
part and an open part. `nfl-review.html` publishes twelve irregularities with their sources. Any
proposal is judged against five acceptance tests, including "no cell may move from blank to a value
without an official URL and a check date".

## Sources

- Standings: https://www.nfl.com/standings/
- Injury report: https://www.nfl.com/injuries/
- Schedule: https://www.nfl.com/schedules/
- Injury-report category definitions: https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693
- NFL.com terms, section 1.3: https://www.nfl.com/legal/terms/
- Pythagorean method (tertiary; method only): https://en.wikipedia.org/wiki/Pythagorean_expectation
- Publisher glossary, Expected W-L: https://www.pro-football-reference.com/about/glossary.htm

## Limits

One partial season. Single-source values. No market prices. No depth charts or snap counts. Team-level
correlation is not leg-level dependence. NFL.com terms restrict systematic retrieval and commercial
use, so nothing here is released as a dataset or offered as a betting service. Luck cannot be removed;
it can only be acknowledged and, where possible, separated from measurable signal.
