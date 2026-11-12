# Executive summary · OWN7 NFL Research Lab

Snapshot checked: **2026-11-12**. Scope: an auditable statistical-research dashboard, not an approved betting system.

## Decision

**Do not release live NFL betting lines or assert a skill-based wagering edge.** No candidate passes all applicable gates. No ROI, closing-line value (CLV), executable price, cash prize or qualified winner is known; those fields are blank. Luck cannot be eliminated.

A substantive constraint was confirmed: [NFL Terms §1.3](https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions) restricts Services to own individual non-commercial and informational purposes; systematic retrieval prohibited without consent. §11(f) prohibits harvesting for commercial purpose. §12 prohibits gambling/wagering on gaming features or using Services to gamble/wager on any NFL game. No separate permission is evidenced. NFL-derived betting-price release, bulk data harvesting, wagering and cash payments are disabled. This is a frozen, attributed statistical audit and non-commercial methods demonstration, not a licensed gambling data product or legal advice.

## Verified observations

| Item | Finding | Official source |
|---|---|---|
| Standings | All 32 2026 REG division rows checked. Buffalo and San Francisco lead at 7-1 (.875); Los Angeles Chargers 0-8 (.000). | [NFL standings](https://www.nfl.com/standings/) |
| Passing leaders | Top 25 by passing yards checked. Jordan Love leads at 2,618 yards; Joe Burrow 2,386; Dak Prescott 2,381. Passing-selected subset, not a complete universe. | [NFL passing](https://www.nfl.com/stats/player-stats/) |
| Rushing leaders | Top 25 by rushing yards checked (positional C1-C9; headers not rendered). Bijan Robinson leads at 880 (C1). | [NFL rushing](https://www.nfl.com/stats/player-stats/category/rushing/2026/reg/all/rushingyards/desc) |
| Receiving leaders | Top 25 by receptions checked (positional C1-C9). Trey McBride leads at 73 receptions (C1); Jaxon Smith-Njigba 1,036 yards (C2). | [NFL receiving](https://www.nfl.com/stats/player-stats/category/receiving/2026/reg/all/receivingreceptions/desc) |
| Team offense (passing) | 32 team rows checked. Green Bay leads at 2,618 pass yards. | [NFL team offense](https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all) |
| Team defense (passing) | 32 team rows checked. Seattle allows fewest at 1,519 pass yards. | [NFL team defense](https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all) |
| Injuries (bounded) | Week 7 Thu Oct 22 NE+CHI and Sun Oct 25 PIT+NO fully transcribed (45 rows). Replacements/deficiencies not stated — blank. | [NFL injury report](https://www.nfl.com/injuries/league/2026/reg7) |

Every retained input field was compared against returned official rendered tables. Evidence files are normalized transcriptions, **not raw HTTP archives**; integrity hashes do not independently establish truth. Exact receipts: [`research/evidence/nfl-receipts.json`](../research/evidence/nfl-receipts.json).

## Calculated research results — not official NFL statistics or proof of edge

Ten descriptive cross-sectional Pearson correlations were calculated from verified season aggregates (see `research/nfl-results.json`). Examples: W vs Net Pts r=0.846 (n=32); Pass Yds vs TD (QBs) r=0.839 (n=25). These describe the snapshot; they are **not** bet-leg correlations and not predictive. Bet-leg correlations (teammate, cross-game, 3+ leg) are blank — no game logs collected.

## Strategy and competition design

Eight explicit hypotheses cover opponent-adjusted margin/moneyline, total points, schedule/availability, QB passing props, rushing/receiving props, cross-game parlays, same-player combos and teammate/team-total combos. Inputs, output contracts and failure modes are documented. None is a demonstrated profitable strategy.

Ten fail-closed gates cover provenance/contract, chronology, coverage/power, forecast quality, joint dependence, executable economics, uncertainty, multiple testing, forward shadow/risk, and reproducibility/rights. Numerical floors and exposure limits are **project policy**, not externally established skill thresholds.

The proposed leaderboard specifies separate market classes, common frozen windows/offer/exposure rules, a positive lower-bound-return ranking, deterministic ties and explicit abstention logging. Evaluation and ranking are not implemented; every current entry is blocked. Only qualified ranks receive **non-transferable, non-monetary merit points (3/2/1)**. No cash pool or payment amount is inferred. Current leaderboard: empty.

## Injury / backup tracking

The tracker records official injury status (player, position, injury, practice, game status) for 45 players across 4 teams. Replacement players (2nd/3rd/4th string) and quantified deficiencies are **blank** — the injury page does not state them, and rosters were not transcribed. The system design (schema, deficiency method, abstention rules) is documented on the Injuries page; no deficiency is asserted without evidence.

## Suggestions and questions

Twelve proposals (SU-01..SU-12) and fifteen questions (Q-01..Q-15) are published for review. No suggestion is implemented until marked Approved. All answers that cannot be confirmed from an official source remain blank.

## Repository and site

216 NFL rows across 7 datasets, 8 strategies, 10 gates, 10 correlations, 12 suggestions, 15 questions and 11 flags. The NFL requirement ledger, official data tables, source receipts, methods, gate matrix, correlations, results and **Flagged for Review** are public site categories. Review flags do not block publishing an honest site, but do block unsupported strategy/price/cash release.
