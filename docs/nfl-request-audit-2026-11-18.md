# NFL project request audit — 2026-11-18

**Session:** `arena/600119f6-own7`  
**Review time:** 2026-11-18 06:35 UTC  
**Purpose:** Consolidated implementation/readiness review of the NFL requirements in the project brief. This is a repository and source audit, not a betting recommendation, legal opinion, or claim of profitability.

## Executive decision

**Do not use the current output to place or reward bets.** The repository now contains a results archive, model-originated lines, strategy registers, validation/demotion gates, separate signal/staking panels, availability/depth work, a decision-readiness register, suggestions, and flagged-review pages. The checks below establish reproducibility, source-link and blank-value contracts, and browser/accessibility behavior. They do **not** establish that any strategy is profitable, that every source permits collection/redistribution, or that the live injury/depth data is complete.

The hard blockers are still external: (1) a written/otherwise rights-cleared policy for collecting and retaining source data, (2) a permitted, reproducible opening/closing price feed and settlement rules, and (3) enough prospectively timestamped forecasts and verified availability evidence to evaluate skill without leakage. NFL.com’s current terms say use is limited to individual non-commercial informational purposes and prohibit systematic retrieval to create or compile a collection absent express prior written consent (§1.3). This review therefore does **not** add a scheduled scraper or start a repeating collection job.

## What is present, and what it means

| Area | Repository evidence / current state | Decision implication | Official source for manual review |
|---|---|---|---|
| Results and opponent-aware inputs | The current complete results artifact is `nfl-results/data/games-2026-w1-10-complete.csv`; its analysis metadata declares 150 finals and 134 scored rows. The dataset is sourced to NFL schedule pages and reconciled in the project’s saved receipts. | Results permit controlled outcome analysis; they are not market prices, and outcome-only grading is not ROI. Keep each dated vintage distinct. | [NFL Week 10 schedule](https://www.nfl.com/schedules/2026/by-week/week-10) · [NFL standings](https://www.nfl.com/standings/) |
| NFL live availability report | A direct official read at review time rendered the **Week 11** report at `nfl.com/injuries/league/2026/reg11`. The earlier Week 10-only read in older reports is a historical observation, not a current statement. | The live page is not a point-in-time archive. Do not replace or rewrite old captures; record the new read as a separately dated observation only after the project’s rights policy allows it. | [NFL Week 11 injury report](https://www.nfl.com/injuries/league/2026/reg11) |
| Pricing / fair-v-market | The repo has model-line and market-price schemas, but market quotes are blank where no rights-cleared operator quote is recorded. | No market residual, closing-line value, ROI, or stake-based reward is established by a model fair line alone. | [NFL.com terms §1.3](https://www.nfl.com/legal/terms/) |
| Availability, starters, depth and replacement | Dedicated availability, Game Book, snap-count, depth, and replacement artifacts exist, with source-specific gaps recorded on their flagged pages. | An injury designation alone is not proof of who started, who replaced them, or how many snaps the replacement played. Use official Game Books/inactives and sourced snap counts; do not infer from jersey number, roster order, experience, salary, or a blank report cell. | [NFL Game Books / game centre](https://www.nfl.com/scores/) · [NFL injury report](https://www.nfl.com/injuries/) |
| Competition and validation | The project includes pre-registration, paper/live status gates, proper-score and uncertainty concepts, controls, multiplicity handling, and demotion rules. Multiple desks hold different versioned ledgers. | A rule being implemented or a test passing is not a strategy qualifying. Do not treat backtest output as a prospective leaderboard or reward. | [NFL schedules/results](https://www.nfl.com/schedules/) |
| Suggestions and questions | Dedicated Suggestions, Questions/Decisions, Executive Summary, Decision Readiness, and Flagged for Review pages are present. Suggestions are reviewable proposals rather than silently authorized changes. | Keeping the adoption choice pending is correct where the brief requires someone to choose, or where the choice is legal, financial, or a data-rights decision. | [NFL.com terms](https://www.nfl.com/legal/terms/) |

## Confirmed checks performed in this session

- `npm run check` passed: 119 repository unit tests, NFL extraction/origination checks, and the recursive site audit. The audit reported 280 HTML pages, 15,332 table body rows, 15,095 internal references, 26,056 external references, 302 registered sources, blank unknown values, and zero errors. Its own scope statement correctly warns that this does not prove external factual truth, source rights, or profitability.
- `npm ci` completed with no reported vulnerabilities; `npm run test:browser` passed for 256 desktop and 256 mobile pages, WCAG A/AA, 10 interaction groups, and no runtime errors.
- I freshly read the official NFL standings page, the current Week 11 injury report, and the NFL.com Terms page. The terms page labels itself updated May 16, 2024 and §1.3 expressly prohibits systematic retrieval for compiling a collection absent prior written consent.
- These checks are reproducibility and presentation checks. They are not a fresh, row-by-row recapture of every historical NFL page, and must not be represented as such.

## Irregularities and reconciliation items

1. **Multiple intentional result vintages must remain clearly labeled.** The repo contains 136-game Week 1–9, 149-game Week 1–10, and 150-game completed Week 1–10 files; `nfl-competition/data/results-feed.csv` is a separately dated 137-row feed. These are not interchangeable datasets. The 150-row file is the current completed results input for the results analysis; the smaller files are historical snapshots/subcorpora. Any public leaderboard needs to identify exactly which frozen corpus and registration it uses. The official schedule is the source for final/scheduled states; the repo’s receipts record the read dates.
2. **Readiness documents are snapshots, not live truth.** The readiness register and some executive summaries predate the latest Week 11 injury-page read. The Week 10 injury read remains useful as a dated historical source; its page should not be described as the current injury report. Current Week 11 status is visible on the official live page, but this one read does not create a replayable daily series.
3. **Price policy is still a gate, not a completed price store.** A row structure for model snapshots does not satisfy the requirement for official/rights-cleared market open and close observations. Market cells should remain blank and ROI/CLV should remain unavailable until a source, license/terms, timestamp convention, vig normalization, and settlement rule are documented.
4. **Availability is not yet a verified replacement graph across all clubs and time.** Historic evidence helps, but no single live report can establish every expected starter, actual starter, inactive, snap share, replacement depth, or roster event. Conflicts and source gaps must remain visible on the Flagged for Review pages.
5. **No automated live-data promise is supportable yet.** The repository’s static GitHub Pages deployment is not an immutable, private snapshot store with freshness alerts. Scheduled retention must wait for a documented permission/terms decision and an approved storage location.

## Questions that must be answered before a decision

These questions are intentionally **not** answered by guessing:

1. **Data rights:** Is there written NFL permission or a licensed feed that expressly permits scheduled retrieval, historical retention, derived analysis, and public display? If not, which requirements are dropped or sourced elsewhere?
2. **Price policy:** Which licensed source supplies opening and closing numbers for side, total, and moneyline; what timezone/capture clock and book/consensus rule apply; how are vig, line moves, pushes, voids, and stale/missing prices handled?
3. **Forecast protocol:** Which strategy versions are frozen before the next evaluation window, what are the train/validation/final seasons, and what constitutes the single prospective evaluation set? How are exploratory/backtest rows technically prevented from reaching the leaderboard?
4. **Eligibility/reward:** What is the minimum game-clustered sample and lower confidence bound, benchmark-relative Brier-skill criterion, multiplicity correction, and prospective CLV escrow required before qualification? What, if anything, counts as a reward, and who has authority to authorize it?
5. **Availability coverage:** Which official source is verified for all 32 clubs for depth slots, actual starters, inactives, and snap counts? What permitted source supplies dated roster/transaction events and conflict resolution?
6. **Parlays and props:** Which joint-event data, operator void/push rules, and calibration sample will authorize a combo? Until both joint probability and settlement rules are validated, these remain blocked.
7. **Public/private boundary:** Which raw player-level rows may be public under the source terms, and which must remain in a private, access-controlled store?

## Highest-value next suggestions (not implemented automatically)

1. **Resolve the rights and price-source policy first.** It gates the snapshot ledger, ROI/CLV, scheduled injury history, and rewards. Acceptance evidence: written permission or a license and a documented source/retention/display policy.
2. **Use one canonical, frozen results corpus per registered run.** Keep dated vintages immutable; bind each strategy registration to a corpus hash, scoring/settlement code hash, and train/validation/holdout window. Acceptance evidence: build-time refusal when a run mixes vintages or evaluates a strategy on a corpus outside its registered window.
3. **Require prospective probabilistic forecasts before ranking.** Record probabilities, inputs, timestamps, and version before kickoff; publish benchmark-relative proper scores with clustered uncertainty and multiplicity adjustment. Keep in-sample diagnostics off the leaderboard.
4. **Gate player features on verified availability evidence.** Compare the same model with/without verified availability features on chronological holdouts; report uncertainty. Do not add fixed injury penalties or infer replacement depth from jersey order.
5. **Keep singles as the baseline; hold combos behind joint validation.** Require direct joint calibration and operator-specific settlement/void rules before a combo can be ranked.

## Source links

- [NFL standings](https://www.nfl.com/standings/) — official league standings page.
- [NFL Week 10 schedule](https://www.nfl.com/schedules/2026/by-week/week-10) — official results/schedule page used by the completed results corpus.
- [NFL Week 11 injury report](https://www.nfl.com/injuries/league/2026/reg11) — official page read during this review; current page state, not a historical archive.
- [NFL injury reports landing page](https://www.nfl.com/injuries/) — official injury-report source.
- [NFL Game Books / scores](https://www.nfl.com/scores/) — official game-centre entry point; use the actual linked Game Book for starter evidence, not inference.
- [NFL.com Terms and Conditions](https://www.nfl.com/legal/terms/) — §1.3 is the reason this review did not add a recurring capture process.

## Reproduction

```sh
npm run check
npm run test:browser
```
