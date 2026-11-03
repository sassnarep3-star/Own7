# analysis/ — verified NBA line-origination engine

A self-contained, reproducible engine and dashboard. It reads only the
hand-verified NBA.com snapshots in `data/`, so it runs offline.

```
python3 analysis/run.py                                       # results/*.json
python3 analysis/build_site.py                                # 10 dashboard pages
python3 analysis/check_nav.py                                 # links + per-row provenance
python3 -m unittest discover -s analysis/tests -t analysis     # 51 tests
```

Read [`EXECUTIVE-SUMMARY.md`](EXECUTIVE-SUMMARY.md) first, then open
[`index.html`](index.html).

## Hard rules this directory enforces

1. **No invented numbers.** Every value in `data/*.json` records the NBA.com URL it
   was read from and the UTC timestamp of the read. Cells that could not be read
   unambiguously are omitted, not filled in.
2. **No invented prices.** Model outputs are marked `is_market_price: false`. Fair
   odds are `1/p`, the break-even price a probability implies — not an offered price.
   Market-price fields are `null` because no official NBA source publishes prices.
3. **Blank beats guessed.** `correlation.player_pair_correlation()` refuses to run and
   explains why, rather than returning a coefficient.
4. **Unknown is never a pass.** `gates.py` returns `not_evaluable`, which rolls up to
   `unproven`, never to `passed`.
5. **Deterministic.** All randomness is seeded; a test re-runs the analysis and fails
   if any output byte changes.

## What is NOT in here

- Sportsbook prices, spreads, totals or prop lines (no official source).
- Player-level stat lines (NBA.com player box-score pages returned no table).
- Backtested strategy returns (no priced bet record exists).
- Competition rewards (owner decision; not inferred).

All of the above are listed with source links on `flagged.html`.
