# Executive summary · OWN7 NFL Research Lab

Snapshot checked: **2026-11-12**. Scope: an auditable statistical-research dashboard, not an approved betting system.

## Decision

**Do not release live NFL betting lines or assert a skill-based wagering edge.** No candidate passes all applicable gates. No ROI, closing-line value (CLV), executable price, cash prize or qualified winner is known; those fields are blank. Luck cannot be eliminated.

A substantive constraint was confirmed: [NFL Terms §1.3](https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions) restricts Services to own individual non-commercial and informational purposes; systematic retrieval prohibited without consent. §11(f) prohibits harvesting for commercial purpose. §12 prohibits gambling/wagering on gaming features or using Services to gamble/wager on any NFL game. No separate permission is evidenced. NFL-derived betting-price release, bulk data harvesting, wagering and cash payments are disabled. This is a frozen, attributed statistical audit and non-commercial methods demonstration, not a licensed gambling data product or legal advice.

## Verified observations

All values below were re-read from the publisher on **2026-11-13** and compared row by row with the
frozen 2026-11-12 snapshot. The comparison is published on
[`nfl-verification-2026-11-13.html`](../nfl-verification-2026-11-13.html) and its verbatim captures sit
in `research/nfl/evidence-2026-11-13/`.

| Item | Finding | Official source |
|---|---|---|
| Standings | All 32 division rows re-checked; **30 of 32 identical**. Buffalo and San Francisco lead at 7-1 (.875); Los Angeles Chargers 0-8 (.000). | [NFL standings](https://www.nfl.com/standings/) |
| Standings, moved rows | Washington moved 2-5-1 → 3-5-1 and the Giants 5-2-1 → 5-3-1 after the Thursday fixture. | [NFL standings](https://www.nfl.com/standings/) |
| Passing leaders | Top 25 by passing yards checked. Jordan Love leads at 2,618 yards; Joe Burrow 2,386; Dak Prescott 2,381. Passing-selected subset, not a complete universe. | [NFL passing](https://www.nfl.com/stats/player-stats/) |
| Rushing leaders | Top 25 by rushing yards checked (positional C1-C9; headers not rendered). Bijan Robinson leads at 880 (C1). | [NFL rushing](https://www.nfl.com/stats/player-stats/category/rushing/2026/reg/all/rushingyards/desc) |
| Receiving leaders | Top 25 by receptions checked (positional C1-C9). Trey McBride leads at 73 receptions (C1); Jaxon Smith-Njigba 1,036 yards (C2). | [NFL receiving](https://www.nfl.com/stats/player-stats/category/receiving/2026/reg/all/receivingreceptions/desc) |
| Team offense (passing) | 32 team rows checked positionally; headers and named leader withheld (NF11). | [NFL team offense](https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all) |
| Team defense (passing) | 32 team rows checked. Minnesota allows fewest at 1,495 pass yards. | [NFL team defense](https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all) |
| Injuries (bounded) | Week 7 Thu Oct 22 NE+CHI and Sun Oct 25 PIT+NO fully transcribed (45 rows). The Week 10 Thursday block was re-read on 2026-11-13: 20 of 20 rows identical, 17 game-status cells still blank. Replacements/deficiencies not stated — blank. | [NFL injury report](https://www.nfl.com/injuries/league/2026/reg7) |
| Fixtures | 14 of 14 Week 10 fixtures and the four byes identical. One fixture now prints "Commanders 24, Giants 21, FINAL" in link text while both of its score banners still print "Hidden Score". | [NFL schedule](https://www.nfl.com/schedules/) |

Every retained input field was compared against returned official rendered tables. Evidence files are
normalized transcriptions, **not raw HTTP archives**; integrity hashes do not establish truth, and the
site's own check suite cannot detect a stale value. That limitation is now itself a published question
(DQ16). Direct HTTPS from the build sandbox to `nfl.com` fails (code 000), so all retrievals went
through a page reader; that access class is stated rather than implied to be stronger.

## Calculated research results — not official NFL statistics or proof of edge

Seven descriptive cross-sectional Pearson correlations were calculated from verified season aggregates (see `research/nfl-results.json`). Examples: W vs Net Pts r=0.846 (n=32); Pass Yds vs TD (QBs) r=0.839 (n=25). These describe the snapshot; they are **not** bet-leg correlations and not predictive. Bet-leg correlations (teammate, cross-game, 3+ leg) are blank — no game logs collected.

## Strategy and competition design

Eight explicit hypotheses cover opponent-adjusted margin/moneyline, total points, schedule/availability, QB passing props, rushing/receiving props, cross-game parlays, same-player combos and teammate/team-total combos. Inputs, output contracts and failure modes are documented. None is a demonstrated profitable strategy.

Ten fail-closed gates cover provenance/contract, chronology, coverage/power, forecast quality, joint dependence, executable economics, uncertainty, multiple testing, forward shadow/risk, and reproducibility/rights. Numerical floors and exposure limits are **project policy**, not externally established skill thresholds.

The proposed leaderboard specifies separate market classes, common frozen windows/offer/exposure rules, a positive lower-bound-return ranking, deterministic ties and explicit abstention logging. Evaluation and ranking are not implemented; every current entry is blocked. Only qualified ranks receive **non-transferable, non-monetary merit points (3/2/1)**. No cash pool or payment amount is inferred. Current leaderboard: empty.

## Injury / backup tracking — the requirement that is not met

The tracker records official injury status (player, position, injury, practice, game status) for 45
players across 4 teams, plus 20 players in the Week 10 Thursday block. **The second-, third- and
fourth-string requirement is not satisfied.** Neither source names a starter, a depth rank, a
replacement, a snap count or a share of targets or carries. On 2026-11-13 the league depth-chart path
served no chart and a club depth-chart path returned a 404, so no league-site citation exists for a
depth ordering at all.

Replacement players and quantified deficiencies therefore stay **blank**. The design (schema,
deficiency method, abstention rules) is documented; the data is not collected. This is the single
largest gap between what was asked for and what this repository can support, and it is ranked second
in the suggestions register for that reason.

## Suggestions and questions — how to choose a path

A reviewer now has one decision page: **`nfl-suggestions.html`**. It publishes ten ranked proposals
(`S01`–`S10`) with a 1-5 score for decision value, effort, cost, confidence gain and reversibility, a
priority index that is the arithmetic of those scores, an explicit prerequisite, the question each
proposal closes, the evidence that must exist before it is called done, and the review workflow
(`Proposed → Under review → Approved / Rejected → Implemented`).

Two honest caveats are published on that page rather than hidden:

- The sub-site publishes a **second** register of twelve proposals (`SU-01`–`SU-12`) under different
  identifiers for overlapping work. Both are kept and a crosswalk maps them; the reviewer is asked to
  adopt one.
- **No proposal is approved, and nothing is implemented.** There is no approve button, by design: a
  decision is recorded in the register and rebuilt, which leaves an auditable commit.

Elsewhere: 17 questions (`DQ01`–`DQ17`) each split into what is known with a source and what is still
open, 21 review flags of which 17 are open, ten validation gates and an empty leaderboard.

## Repository and site

216 NFL rows across 7 datasets, 8 strategies, 10 gates, 7 correlations, 10+12 suggestions across two
registers, 17 questions and 21 flags (17 open, 4 corrected). The 2026-11-13 re-verification adds a
38th canonical page and 70 further sourced rows. The NFL requirement ledger, official data tables, source receipts, methods, gate matrix, correlations, results and **Flagged for Review** are public site categories. Review flags do not block publishing an honest site, but do block unsupported strategy/price/cash release.
