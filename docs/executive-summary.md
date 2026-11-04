# Executive summary · OWN7 NBA Research Lab

Snapshot checked: **2026-11-03**. Scope: an auditable statistical-research dashboard, not an approved betting system.

## Decision

**Do not release live NBA betting lines or assert a skill-based wagering edge.** No candidate passes all applicable gates. No ROI, closing-line value (CLV), executable price, cash prize or qualified winner is known; those fields are blank. Luck cannot be eliminated.

A substantive constraint was confirmed: [NBA terms §9(iv)](https://www.nba.com/termsofuse) prohibit using NBA Statistics in connection with gambling activity, including legal gambling. No separate permission is evidenced. NBA-derived betting-price release, bulk data harvesting, wagering and cash payments are disabled. Publication/commercial-use restrictions also require rights review; this is not legal advice.

## Verified observations and corrections

| Item | Finding | Official source |
|---|---|---|
| Team snapshot | All 30 2025–26 team rows rechecked. Denver has the highest displayed PTS average, 122.1; Lakers the highest FG%, 50.2. Earlier summaries incorrectly named Miami and Denver respectively. | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season) |
| Rank correction | Utah shares displayed rank 26, not the old CSV’s 27. BLKA is explicitly labeled between BLK and PF. | [NBA team table](https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season) |
| Player snapshot | Fifteen rows after PTS ≥ 26 filtering; 567 filtered out. The subset is scoring-selected, not a complete player universe. | [NBA filtered player table](https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame&CF=PTS*GE*26) |
| Standings | Thirty 2026–27 rows checked; games played vary from 5 to 8, derived from W+L. A frozen, early-season context snapshot, not a live signal. | [NBA standings](https://www.nba.com/standings) |
| Paired cohort | All 32 Jokić game rows for the explicit 2026-02-01 through 2026-04-12 window checked. Source displays 32 rows on one page. | [NBA date-filtered game log](https://www.nba.com/stats/player/203999/boxscores?Season=2025-26&SeasonType=Regular%20Season&DateFrom=02%2F01%2F2026&DateTo=04%2F12%2F2026) |

Every retained input field was compared against returned official rendered tables. Evidence files are normalized transcriptions, **not raw HTTP archives**; integrity hashes do not independently establish truth. Exact receipts: [`research/evidence/receipts.json`](../research/evidence/receipts.json).

## Calculated research results—not official NBA statistics or proof of edge

| Pair, same 32 games | Calculated Pearson r | Exploratory 95% block interval | Official input / primary method |
|---|---:|---|---|
| PTS / REB | 0.0345 | [-0.4416, 0.4944] | [NBA rows](https://www.nba.com/stats/player/203999/boxscores?Season=2025-26&SeasonType=Regular%20Season&DateFrom=02%2F01%2F2026&DateTo=04%2F12%2F2026), [SciPy definition](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html) |
| PTS / AST | -0.1096 | [-0.4059, 0.1771] | [NBA rows](https://www.nba.com/stats/player/203999/boxscores?Season=2025-26&SeasonType=Regular%20Season&DateFrom=02%2F01%2F2026&DateTo=04%2F12%2F2026), [SciPy definition](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html) |
| REB / AST | 0.4296 | [0.1271, 0.6597] | [NBA rows](https://www.nba.com/stats/player/203999/boxscores?Season=2025-26&SeasonType=Regular%20Season&DateFrom=02%2F01%2F2026&DateTo=04%2F12%2F2026), [SciPy definition](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html) |

Three additional threshold-hit φ estimates and empirical joint rates are calculated separately. Hypothetical thresholds are **not sportsbook lines**. Raw-stat correlation cannot be substituted for hit-event correlation; a zero continuous correlation does not imply independence, and pairwise correlations do not identify a three-plus-leg joint distribution.

Intervals use 10,000 paired circular five-game block resamples, seed 20261103. The horizon is an assumption; intervals are not corrected for choosing this player/window/comparisons. No confirmatory significance claim is made. Exact calculations and input/code hashes: [`research/results.json`](../research/results.json).

Four simple event-probability demonstrations use a Beta(1,1) base-rate estimator, ten warmup games and only earlier-game inputs. Each has 22 later-game rows, **88 rows but only 22 distinct forecast dates**. This retrospective demonstration has no actual historical pregame publication timestamp or sealed holdout. A rare combo beating neutral p=0.5 can reflect base rate alone—not skill. Generic pricing math is tested separately on synthetic inputs; NBA-derived betting prices stay blank.

## Strategy and competition design

Eight explicit hypotheses cover opponent-adjusted margin/moneyline, pace–efficiency totals, schedule/availability, minutes/role props, rebounds/assists, cross-game parlays, same-player combinations and teammate/team-total combinations. Inputs, output contracts and failure modes are documented. None is a demonstrated profitable strategy.

Ten fail-closed gates cover provenance/contract, chronology, coverage/power, forecast quality, joint dependence, executable economics, uncertainty, multiple testing, forward shadow/risk, and reproducibility/rights. Numerical floors and exposure limits are **project policy**, not externally established skill thresholds. Official methodological references: [time splits](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html), [proper scores/calibration](https://scikit-learn.org/stable/modules/calibration.html), [Holm correction](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html).

The leaderboard has separate market classes, common frozen windows/offer/exposure rules, a positive lower-bound-return ranking, deterministic ties and explicit abstention logging. Only qualified ranks receive **non-transferable, non-monetary merit points (3/2/1)**. No cash pool or payment amount is inferred. Current leaderboard: empty.

## Repository and site

The baseline contains 54 tracked files / 2,630 text lines, not the one-file repository described by a stale audit. Every file has a full line scope, hash and disposition. Three overlapping sites are reconciled into one generated dashboard; historical URLs redirect to corresponding categories, and original contents remain in git.

The full requirement ledger, official data tables, source receipts, methods, gate matrix, correlations, results, repository audit and **Flagged for Review** are public site categories. Review flags do not block publishing an honest site, but do block unsupported strategy/price/cash release. Build, PR, merge and Pages evidence are recorded in [`COORDINATION.md`](../COORDINATION.md).
