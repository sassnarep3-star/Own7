# NFL signal research and line-origination contracts

This document describes project hypotheses and mathematical definitions, **not winning strategies**. Canonical records: [`research/nfl-catalog.json`](../research/nfl-catalog.json), [`research/nfl-protocol.json`](../research/nfl-protocol.json), [`nfl_lab/`](../nfl_lab/).

## Explicit model families

| ID | Category | Research contract | Main failure to guard against | Official input / primary method |
|---|---|---|---|---|
| NS01 | Single: margin / moneyline | Lagged, opponent-adjusted team strength; shrinkage; coherent final-score/margin distribution. | Win percentage is not a matchup probability; full-season data leaks when used for earlier games. | [NFL standings](https://www.nfl.com/standings/), [team offense](https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all) |
| NS02 | Single: total | Joint points model using passing efficiency and points for/against; calibrated distribution, overtime/push handling. | Adding historical PF+PA is not an opponent-adjusted total model. Passing-only snapshot omits rushing/scoring. | [NFL standings](https://www.nfl.com/standings/), [team defense](https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all) |
| NS03 | Single: schedule / availability | Rest/bye/travel covariates and timestamped official injury reports. | Schedule rows not transcribed; injury snapshot bounded (4 teams). Unknown availability requires abstention. | [NFL injury report](https://www.nfl.com/injuries/league/2026/reg7), [NFL schedule](https://www.nfl.com/schedules/2026/REG7/) |
| NS04 | Player passing | Attempts × completion rate × yards/attempt; predictive distribution. | Season totals are not a prop distribution; top-25 passing subset is biased. | [NFL passing](https://www.nfl.com/stats/player-stats/), [team defense](https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all) |
| NS05 | Rushing / receiving | Touches/opportunities and conversion with overdispersion; joint component dependence. | Rushing/receiving headers not rendered — positional only. No sign assumed. | [NFL rushing](https://www.nfl.com/stats/player-stats/category/rushing/2026/reg/all/rushingyards/desc), [NFL receiving](https://www.nfl.com/stats/player-stats/category/receiving/2026/reg/all/receivingreceptions/desc) |
| NS06 | Cross-game parlay | Start with separately validated legs; estimate full joint win distribution; compare actual combined quote. | Different games are not automatically independent; do not invent operator payouts. | [NFL standings](https://www.nfl.com/standings/), [NFL terms](https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions) |
| NS07 | Same-player passing + rushing/receiving | Aligned threshold hits or calibrated joint simulation; later joint calibration. | No game logs collected. Raw-stat r differs from event-hit correlation. | [NFL passing](https://www.nfl.com/stats/player-stats/), [NFL rushing](https://www.nfl.com/stats/player-stats/category/rushing/2026/reg/all/rushingyards/desc) |
| NS08 | Teammate / team-total combo | Shared play volume, snaps, targets and game-script model and actual settlement matrix. | No presumed sign; pairwise correlations cannot determine a three-plus-leg joint distribution. | [NFL passing](https://www.nfl.com/stats/player-stats/), [NFL injury report](https://www.nfl.com/injuries/league/2026/reg7) |

References identify input definitions, not an NFL endorsement or evidence of edge. None has verified operator offers, economic returns or all-gate evidence. No fitted team model or live player projection is claimed.

## Generic, implemented pricing identities

For decimal odds `d > 1`, implied probability is `1/d`. No-push fair odds are `1/p`; with push probability `q`, fair odds are `(1-q)/p`, undefined when `p=0`. Per-unit expected net return is `p_win*(d-1) - p_lose`.

A proportional de-vig convention normalizes reciprocal odds over a **complete mutually exclusive outcome set** from the same operator, line, timestamp and settlement contract. It is a modeling convention, not true-probability identification. Positive forecast-minus-de-vigged-market difference alone is insufficient: executable price/cost EV matters.

A parlay uses the actual joint event probability and actual operator combined quote. Product-of-probabilities requires full independence; product-of-odds is not a universal same-game payout rule. Partial voids, pushes, DNP, overtime, fees, taxes and limits require the actual contract — not inferred rules.

## Confirmed source-rights no-go

[NFL Terms §1.3](https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions) restricts Services to own individual non-commercial and informational purposes; systematic retrieval prohibited without consent. §11(f) prohibits harvesting for commercial purpose. §12 prohibits gambling/wagering on gaming features or using Services to gamble/wager on any NFL game. Separate permission is not established. **NFL-derived betting prices are withheld.** No bulk collection, wagering, cash rewards or operator account activity is enabled.
