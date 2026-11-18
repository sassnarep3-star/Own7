# NFL origination — executive summary and decision status

**Review date:** 2026-11-18 (UTC)  
**Scope:** Repository and reproducibility audit; this is not a fresh independent audit of every upstream NFL page.  
**Live site:** [Own7 NFL research dashboard](https://sassnarep3-star.github.io/Own7/)

## Executive takeaway

The repository now contains a broad, source-linked NFL research and decision-readiness site, reproducible data desks, and explicit validation / review workflows. It is **not** a validated betting product or a leaderboard that can responsibly pay rewards. Keep all strategies in research or shadow status until prospective, point-in-time inputs and independently verified market prices and results support out-of-sample skill.

The locally available integrity suite passed on this review: 119 general unit tests; NFL result reproduction; six NFL build tests; and the recursive site audit (280 HTML pages, 15,332 table body rows, 302 registered source records, zero reported integrity errors). These checks establish reproducibility, source-link contracts, blank-value rules, and local navigation—not the truth of every upstream claim, legal rights to republish data, prediction quality, or profitability.

## What can be decided now

| Decision | Current answer | Gate / evidence |
|---|---|---|
| Publish a research dashboard | Yes, with explicit limitations and source links | The repository's recursive audit passed locally; the deployed site is linked above. |
| Treat originated lines as proven edge | No | Require chronological holdouts, prospective forecasts, market snapshots and benchmark-relative proper scores with uncertainty. |
| Rank or reward strategies | No | Require preregistration, prospective eligibility, proper-score qualification and a stated reward / governance policy. No ROI or short-run win-rate substitute. |
| Use injury labels as point penalties | No | Validate timestamped designations against official game-day status and participation; test ablations with uncertainty. |
| Infer depth from roster order, jersey number or absence from a report | No | Require dated official depth / starter evidence or a validated participation-based proxy; preserve shared/empty slots and roster events. |
| Publish marginal-probability products as parlay skill | No | Require directly validated joint probabilities and documented push/void settlement rules. |

## Current blockers before a decision-grade competition

1. **Point-in-time price evidence:** immutable opening and closing market snapshots, source / terms policy, timestamps, and reproducible vig removal are prerequisites for residuals and CLV.
2. **Point-in-time availability:** dated official injury, depth, inactive, reserve and transaction evidence must be retained with hashes and conflict flags. A current page or a single capture cannot establish what was known before kickoff.
3. **Verified outcomes and participation:** use official game books / results and verified game-day status and snap evidence; reconcile corpus coverage before computing ROI or player availability effects.
4. **Pre-registered evaluation:** freeze model, features, target, sample windows, benchmark and gates before outcomes; separate training, validation and final holdout seasons and then prospective escrow.
5. **Uncertainty-aware ranking:** report calibrated probabilities and proper scores, benchmark-relative skill, clustered uncertainty and multiplicity control. Show signal separately from staking; staking results do not establish signal quality.
6. **Dependence:** compute correlation only from official, compatible observations, publish `n` and uncertainty, and do not build parlay rankings by multiplying marginals.
7. **Data rights and operations:** resolve source terms and lawful storage/redistribution before expanding automated collection; monitor freshness and schema drift and keep raw restricted data separate from public derived analysis.

## Questions that need answers before choosing a path

| Question | Information already available | Missing information / suggested discovery | Decision it blocks |
|---|---|---|---|
| Which market and price source defines the benchmark? | The project specifies opening/closing snapshots and a policy decision. | Written policy naming books/exchanges, capture clock, market identity, stale/limits handling, push rules, and permitted retention; verify each source's terms. | Fair-line residual, CLV, ROI and eligibility. |
| What is the canonical pregame information cutoff? | The project requires immutable availability snapshots and no lookahead. | Operationally fixed kickoff-relative cutoff, timezone, late inactive handling, fetch timestamps and failed-capture behavior. | Backtest integrity and actionable forecasts. |
| What constitutes a verified starter / replacement? | Official game books, club depth, transaction events and snap counts are requested. | Coverage audit across all clubs/seasons; treatment of shared or empty depth groups; verified participation denominator and replacement depth definition. | Injury/depth features and matchup matrix. |
| Which target is scored for each product? | Singles, parlays and prop combos are requested as separate divisions. | Versioned settlement specification including ties, pushes, voids, player non-participation and same-game joint outcomes. | Comparable proper scores and leaderboard eligibility. |
| When is a strategy allowed to enter the leaderboard? | Preregistration and validation gates are explicit requirements. | Frozen rule, hash, sample minima, benchmark, uncertainty method, trial-count correction, prospective duration and demotion thresholds. | Rewards, public ranks and live/paper transitions. |
| Which evidence can be published? | The repository distinguishes public derived analysis from raw data concerns. | Source-by-source terms review and storage/retention approval, especially for automated snapshots. | Data collection, hosting and commercial use. |

## Recommended review order

1. Adopt a written source/rights and timestamp policy before publishing any backtest.
2. Close source coverage and immutable snapshot gaps, including official inactive and participation evidence.
3. Establish result/settlement definitions and reconcile the historical corpus.
4. Pre-register a simple singles-only baseline and controls; freeze the prospective evaluation window.
5. Evaluate with proper scores and uncertainty on untouched chronological holdouts; publish failures and ablations.
6. Only then evaluate prospective leaderboard escrow. Keep parlays and prop combos ineligible until joint evidence and settlement semantics pass their own gate.

## Irregularity and freshness note

The repository's existing `docs/nfl-origination-summary.md` is dated 2026-11-12 and describes a smaller snapshot (including 14 Week 10 fixtures and 20 injury rows). Do **not** read those counts as current status: later dated desks and results reconciliation exist in the repository. This review does not replace or silently edit that historical snapshot. Likewise, a green local checker is not a substitute for opening and verifying each source page; upstream facts, stale captures, coverage discrepancies, source terms, and any unverified values remain review items on the site's [Flagged for Review](https://sassnarep3-star.github.io/Own7/nfl-review.html) page and its dated sub-desk review pages.

## Links for manual review

- [NFL dashboard](https://sassnarep3-star.github.io/Own7/)
- [Decision readiness](https://sassnarep3-star.github.io/Own7/nfl-readiness.html)
- [Suggestions](https://sassnarep3-star.github.io/Own7/nfl-suggestions.html)
- [Decision questions](https://sassnarep3-star.github.io/Own7/nfl-questions.html)
- [Flagged for review](https://sassnarep3-star.github.io/Own7/nfl-review.html)
- [NFL.com standings](https://www.nfl.com/standings/)
- [NFL.com injuries](https://www.nfl.com/injuries/)
- [NFL.com schedules](https://www.nfl.com/schedules/)
- [NFL.com legal terms](https://www.nfl.com/legal/terms/)
