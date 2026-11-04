# Signal research and line-origination contracts

This document describes project hypotheses and mathematical definitions, **not winning strategies**. Canonical records: [`research/catalog.json`](../research/catalog.json), [`research/protocol.json`](../research/protocol.json), [`nba_lab/`](../nba_lab/).

## Explicit model families

| ID | Category | Research contract | Main failure to guard against | Official input / primary method |
|---|---|---|---|---|
| S01 | Single: margin / moneyline | Lagged, opponent-adjusted team strength; shrinkage; coherent final-score/margin distribution. | Win percentage is not a matchup probability; full-season data leaks when used for earlier games. | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season), [time splits](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) |
| S02 | Single: total | Joint possessions and both teams’ PPP; calibrated distribution, overtime/push handling. | Adding historical PPG is not an opponent-adjusted total model. | [NBA glossary](https://www.nba.com/stats/help/glossary), [calibration](https://scikit-learn.org/stable/modules/calibration.html) |
| S03 | Single: schedule / availability | Rest/B2B covariates and timestamped official participation reports. | Known-after-tipoff minutes/injuries leak future information; unknown availability requires abstention. | [NBA injury policy](https://official.nba.com/nba-injury-report-2026-27-season/), [time splits](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) |
| S04 | Player points | Participation × minutes × role/opportunities; predictive count distribution. | PPG is not a probability distribution; scoring-selected sample is biased. | [NBA player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame&CF=PTS*GE*26), [NBA glossary](https://www.nba.com/stats/help/glossary) |
| S05 | Rebounds / assists / PRA | Model opportunities, overdispersion and joint component dependence. | Summing independent variances without a joint model; role/threshold drift. | [NBA game log](https://www.nba.com/stats/player/203999/boxscores?Season=2025-26&SeasonType=Regular%20Season&DateFrom=02%2F01%2F2026&DateTo=04%2F12%2F2026), [Pearson method](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html) |
| S06 | Cross-game parlay | Start with separately validated legs; estimate full joint win distribution; compare actual combined quote. | Different games are not automatically independent; do not invent operator payouts. | [Pearson limitations](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html), [project contract](https://github.com/sassnarep3-star/Own7/blob/main/research/protocol.json) |
| S07 | Same-player points / assists | Aligned threshold hits or calibrated joint simulation; later joint calibration. | Raw-stat r differs from event-hit φ; the present retrospective study is not gate evidence. | [NBA game log](https://www.nba.com/stats/player/203999/boxscores?Season=2025-26&SeasonType=Regular%20Season&DateFrom=02%2F01%2F2026&DateTo=04%2F12%2F2026), [calibration](https://scikit-learn.org/stable/modules/calibration.html) |
| S08 | Teammate / team-total combo | Shared possession/minute/usage/game-script model and actual settlement matrix. | No presumed sign; pairwise correlations cannot determine a three-plus-leg joint distribution. | [NBA glossary](https://www.nba.com/stats/help/glossary), [Pearson limitations](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html) |

References identify input definitions/methods, not an NBA endorsement or evidence of edge. None has verified operator offers, economic returns or all-gate evidence. No fitted team model or live player minutes projection is claimed.

## Generic, implemented pricing identities

For decimal odds `d > 1`, implied probability is `1/d`. No-push fair odds are `1/p`; with push probability `q`, fair odds are `(1-q)/p`, undefined when `p=0`. Per-unit expected net return is `p_win*(d-1) - p_lose`.

A proportional de-vig convention normalizes reciprocal odds over a **complete mutually exclusive outcome set** from the same operator, line, timestamp and settlement contract. It is a modeling convention, not true-probability identification. Positive forecast-minus-de-vigged-market difference alone is insufficient: executable price/cost EV matters.

A parlay uses the actual joint event probability and actual operator combined quote. Product-of-probabilities requires full independence; product-of-odds is not a universal same-game payout rule. Partial voids, pushes, DNP, overtime, fees, taxes and limits require the actual contract—not inferred rules.

## Retrospective methods demonstration

`nba_lab.models.walk_forward_demo` calculates Beta(1,1) earlier-game threshold probabilities on one complete 32-game historical window. Four event definitions, ten warmup games and 22 later games each produce 88 rows. Joint probabilities use paired joint hits. Proper scores are calculated; neutral p=0.5 is only an illustrative reference, not a market baseline or evidence of skill. No tuning, pre-registration, market evaluation or prospective performance is claimed.

## Confirmed source-rights no-go

[NBA terms §9(iv)](https://www.nba.com/termsofuse) prohibit NBA Statistics use connected with gambling activity, including legal gambling. Separate permission is not established. **NBA-derived betting prices are withheld**, even though generic pricing primitives work on synthetic test inputs. No bulk collection, wagering, cash rewards or operator account activity is enabled.
