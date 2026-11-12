# Ten fail-closed NFL validation gates

Canonical pass rules and current evidence are in [`research/nfl-catalog.json`](../research/nfl-catalog.json). Numerical floors, risk limits and reward rules are **project design choices**, not official NFL standards or proof of skill. No current candidate passes all applicable gates.

| Gate | Evidence required | Current no-go | Primary method / official reference |
|---|---|---|---|
| NG01 Provenance / contract | Official row receipts, original publication and capture times, input hashes, exact operator/market/line/settlement contract. | Stats snapshots checked; quotes and original pregame timing absent. | [NFL standings](https://www.nfl.com/standings/) |
| NG02 Chronology | Freeze all features/model/selection/calibration before kickoff; available_at ≤ cutoff; group legs/game and purge calendar splits. | No contemporaneous pregame record. | [NFL injury report](https://www.nfl.com/injuries/league/2026/reg7) |
| NG03 Coverage / power | Screening floor: 500 settled selections, 200 distinct games, 60 dates; predeclared power/missingness/selection-bias analysis. | Season aggregates only; no market selections or power calculation. | [NFL passing](https://www.nfl.com/stats/player-stats/) |
| NG04 Forecast quality | Common untouched event universe; beat frozen simple and same-contract de-vigged-market baselines in proper scores; inspect reliability. | No forecast evaluation; no market baseline. | [NFL team offense](https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all) |
| NG05 Joint dependence | Aligned event pairs, n/date/CI, conditional residual study, feasible marginals/joint probabilities and held-out joint calibration. | Descriptive estimates only; no executable combo evidence. Explicitly N/A for singles with an artifact, not a pass. | [NFL passing](https://www.nfl.com/stats/player-stats/) |
| NG06 Executable economics | Actual timely quote, offered market, costs/limits, full push/void/overtime/DNP settlement and same-contract close. | No operator prices/contracts. | [NFL terms](https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions) |
| NG07 Uncertainty / robustness | Net return lower 95% date-block interval >0 after costs; drawdown, coverage, CLV, block/season sensitivity. | ROI, CLV and return intervals blank. CLV alone would not establish skill. | [NFL standings](https://www.nfl.com/standings/) |
| NG08 Multiplicity | Every attempted variant logged; valid preregistered null tests; Holm familywise α=0.05 over the full family. | No confirmatory test family or p-values. | [NFL passing](https://www.nfl.com/stats/player-stats/) |
| NG09 Forward shadow / risk | Freeze common future evaluation; at least 60 calendar days and 200 games; paper caps and abstention log. | No prospective record; cash execution disabled. | [NFL schedule](https://www.nfl.com/schedules/2026/REG7/) |
| NG10 Reproduction / rights | Reproduce hashes, probabilities, settlement and scores; establish source rights/operator/contest permissions. | Reproduction works; NFL gambling-use restrictions confirmed, separate permission absent. | [NFL terms §1.3/§12](https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions) |

Missing, failed, partial, blocked or unknown evidence cannot rank. Ranking rewards only qualified paper entries with non-monetary merit points (3/2/1); no eligible entries means no points. Cash amounts stay blank.
