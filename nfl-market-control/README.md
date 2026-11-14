# NFL market-control sub-site

This is a source-linked, paper-only desk for the OWN7 NFL line-originations. It adds a fail-closed price-snapshot schema and makes the existing signal evidence, staking economics, market order and live-to-paper control visible as separate decisions.

## Important state

- The current model board has 14 frozen Week 10 game projections. It is not a live board.
- Market order is **side/point spread → total → moneyline**.
- The quote store `data/quote_snapshots.jsonl` is intentionally empty. The site shows 84 game/market/selection rows and 168 expected opening/closing quote slots; expected slots are not observed prices.
- No ROI, CLV, stake or reward is calculated. Model fair values are never copied into market fields.
- The signal and staking leaderboards are separate. One existing signal is provisional; zero strategies are qualified.
- The demotion gate is implemented and tested, but inactive: there is no live strategy.
- The result feed is the existing `nfl-results/` pipeline. It captures NFL.com schedule results, checks them against official standings and publishes the results with per-row sources. This desk consumes its deterministic analysis rather than duplicating that feed.

## Quote record contract

The JSONL store is append-only. One observation identifies a game, market, `mainline` variant, selection, operator and `opening`/`closing` phase. Required fields include the market line (except moneyline), American odds, a timezone-aware UTC capture timestamp, a registered HTTPS source ID and URL, a documented authorized-rights reference, verified status and an evidence SHA-256.

`engine.append_quote()` refuses unknown games, unsupported markets/selections, unregistered/non-price sources, source-host or registered-path mismatches, rights not recorded as authorized in the source registry, unverified evidence, duplicate slots, malformed odds and a closing timestamp earlier than opening. A publishable market source must carry a checked scope/date/access record plus an authorized-use scope and non-sensitive rights reference; the quote must match that reference. A new price publisher must be registered in `research/sources.json` **and** in the recursive site's source-host allowlist before its quotes can be published. The public store must not include private contract contents. The supplied evidence digest is checked for SHA-256 syntax only; the original source evidence is not stored or independently re-hashed.

Expected-value semantics:

- Spread/total: `difference = model fair point line − market point line`.
- Moneyline: compare the model fair win probability with the raw probability implied by American odds; that raw value includes vig and is not called an edge.
- Missing market input means blank difference; it is not a zero and does not pass a validation gate.

## Demotion rule

A live strategy returns to paper immediately on a provenance failure, rights invalidation, missing/stale quote snapshot, settlement mismatch, risk-limit breach, unvalidated model/input change or non-reproducible build. After at least 100 settled bets in the locked cohort, it also returns to paper when a pre-registered one-sided 95% lower confidence bound for net ROI is at or below zero. The bound must use the registered dependence and multiplicity design. The 100-bet floor is a disclosed project choice inherited from the existing result gate, not a league rule or universal power claim. Promotion back to live is never automatic.

## Build and tests

```sh
python nfl-market-control/build.py
python nfl-market-control/build.py --check
python -m unittest discover -s nfl-market-control/tests -v
```

The nine generated pages are under `site/`. The top page is the executive summary; the site includes Price snapshots, Signal vs staking, Origination order, Live-to-paper gate, Questions & answers, Suggestions to review, Flagged for review and Sources & method.
