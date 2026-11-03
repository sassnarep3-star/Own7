# Own7 NBA Research Lab

A static research dashboard for NBA line origination, candidate signals, validation gates, a proposed leaderboard, and unresolved items. The project does **not** contain collected odds, fitted models, performance results, correlation estimates, or betting recommendations.

## Run and verify

Run `python3 scripts/check_site.py` to check local HTML links and the presence of an HTTPS source in each table body row. This check does not validate external links, page claims, or source authority. Run `python3 -m http.server 8000` from the repository root to serve the site locally. GitHub Pages is configured to publish the root of `main`.

See the [source register](sources.html) and [Flagged for Review](review.html). The validation thresholds and competition rules are proposals, not empirically established results. Gambling entails risk; luck cannot be eliminated.

## Verified-data site (`verified/`)

A second, data-first site lives in `verified/` (published with the root of `main` at `/verified/`). Every row has an official `source_url` or is blank and flagged. Its data is `verified/data/*.json`.

- Rebuild: `python3 scripts/build_verified_site.py`
- Verify: `python3 scripts/verify_verified_site.py` (must print `OK`)

Pages: Executive Summary, Sources, Betting Rules, Strategies, Validation Gates, Correlation, Leaderboard, Responsible Gambling, Repo Review, Flagged for Review. Current results: 0 strategies tested, 0 passing gates; no NBA numeric data verified (the NBA stats endpoints were not reachable from the build environment).
