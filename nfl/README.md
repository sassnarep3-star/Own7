# NFL Research Lab (sub-site)

Deterministic, source-linked NFL research. Checked 2026-11-12. 216 verified rows, 8 hypotheses, 10 gates, 10 descriptive correlations, empty leaderboard.

No verified betting edge, executable NFL line, ROI, CLV, cash prize or winning strategy is claimed. Blank values are intentional. Luck cannot be removed.

## Reproduce

```sh
python -m nfl_lab run
python nfl/build.py
python nfl/build.py --check
python nfl/test_build.py -v
```

## Rights

NFL Terms §1.3 (non-commercial/informational only; systematic retrieval prohibited without consent), §11(f) (harvesting ban), §12 (gambling/wagering prohibition). No separate permission evidenced. NFL-derived betting prices, bulk collection, wagering and cash payments are disabled. This is a frozen, attributed statistical audit and non-commercial methods demonstration, not a licensed gambling data product or legal advice.

## Data

- `data/nfl-*.csv`: 32 standings, 25 passing, 25 rushing (positional), 25 receiving (positional), 32 team offense passing, 32 team defense passing, 45 bounded injuries.
- `research/nfl-catalog.json`, `research/nfl-protocol.json`, `research/nfl-results.json`: strategies, gates, competition, correlations.
- `research/nfl-suggestions.json`, `research/nfl-questions.json`: reviewable proposals and Q/I/A ledger.
