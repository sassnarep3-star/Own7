# Own7 NBA Research Lab

Canonical dashboard: https://sassnarep3-star.github.io/Own7/

An audited static research workspace for NBA line origination: eight candidate strategies, nine proposed validation gates, correlation protocol, proposed competition rules, official standings snapshot and clearly flagged missing evidence.

**Not a working betting system:** no executable odds archive, fitted model, strategy backtest or measured betting correlations. No strategy has passed validation. Luck cannot be eliminated. Results are blank rather than invented; no cash reward is funded.

## Build and test

```sh
python3 scripts/build_dashboard.py
python3 scripts/check_site.py
python3 scripts/test_research.py
python3 scripts/verify_official_snapshots.py
python3 scripts/compute_team_correlations.py
python3 -m http.server 8000 --bind 0.0.0.0
```

Standard library only. GitHub Pages publishes root of `main`. CI rebuilds and checks generated HTML, recursive local links and table source presence, plus synthetic unit tests for pricing/correlation identities. These are structural tests, not verification of scientific truth or external uptime.

## Evidence and audit

- `sources.html`: scope actually read from primary sources on 2026-11-03.
- `review.html`: missing data, unsupported old claims, jurisdiction issues and rewards.
- `data/standings-2026-27.csv`: 30-row official NBA snapshot compared to NBA standings during audit; not live.
- Other CSVs: unconfirmed historical numeric values intentionally blank; identities retained as unverified records.
- `scripts/research_math.py`: tested identities only; no fitted forecasts or genuine NBA correlations.
- `pages/` and `verified/` HTML: retained URLs with superseded notices. `verified/data/` and `docs/` are historical artifacts, explicitly superseded, not current certified evidence. Earlier content remains in Git history.
- `COORDINATION.md`: task ownership and deployment log; earlier verification statements are historical.

A static site cannot autonomously authenticate to bookmakers or establish future predictive skill. Licensed, timestamped input data, pre-registered power analysis and forward evidence are still needed before any edge can be claimed. No manual setup is needed to view the published research.
