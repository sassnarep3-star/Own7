# OWN7 · NBA Research Lab

[Live dashboard](https://sassnarep3-star.github.io/Own7/) · [Executive brief](docs/executive-summary.md) · [Sources](research/sources.json) · [Coordination / release evidence](COORDINATION.md)

One static, source-linked dashboard replaces the repository’s three inconsistent earlier sites. It contains **107 checked official snapshot rows**, eight strategy hypotheses, six paired-game exploratory estimates plus 17 contributed aggregate-correlation rows (with overlaps), 88 retrospective probability demonstrations, ten fail-closed validation gates, an empty qualified leaderboard, a requirements ledger and a complete baseline file audit.

**No verified betting edge, executable NBA line, ROI, CLV, cash prize or winning strategy is claimed.** Blank values are intentional. Luck cannot be removed.

## Important source restriction

[NBA terms §9(iv)](https://www.nba.com/termsofuse) expressly prohibit using NBA Statistics in connection with gambling activity, including legal gambling. Separate authorization is not evidenced. NBA-derived betting-price release, bulk data harvesting, wagering and cash payments are disabled. This is a frozen, attributed statistical audit and non-commercial methods demonstration, not a licensed gambling data product or legal advice.

## Reproduce without manual data entry

Python 3.11+; the research and static build use the standard library only:

```sh
python -m nba_lab run
python -m unittest discover -s tests -v
python scripts/build_site.py
python scripts/check_site.py
```

Optional full browser/accessibility verification (Linux x64; Node 22.17+):

```sh
npm ci
npm run test:browser
```

The browser binary ships in an npm development package; no runtime dependency, CDN or browser download is needed. To view locally:

```sh
python scripts/serve_site.py --host 0.0.0.0 --port 8080
```

## Evidence and limits

- `data/*.csv`: 30 team rows, 15 scoring-filtered players, 30 standings rows and a complete explicit 32-game Jokić window. Every row has an official source URL. Snapshots checked 2026-11-03, not live feeds.
- `research/evidence/`: exact scopes, normalized transcriptions, row checks and integrity receipts. **Not raw HTTP archives or independent second sources.** Later hash/equality checks establish integrity, not factual truth.
- `research/sources.json`: primary-source publisher, URL, check date and actual checked scope. NBA values are observed; model outputs are explicitly derived; policies/thresholds are project designs.
- `research/results.json`: deterministic correlation/interval/joint-rate calculations, chronological probability ledger, null prices/ROI/CLV, blocked gates, input/code hashes and run hash.
- `research/catalog.json`, `research/protocol.json`: hypotheses, all ten gates, review items, method choices and non-monetary competition rules.
- `research/audit/`: 54-file / 2,630-line baseline inventory and dispositions; tests and release evidence. Original historical assertions remain inspectable in git, not as active verified facts.
- `research/requirements.json`: every requirement mapped to an artifact and honest status; blocked research/rights requirements are not marked complete.

The cohort, player, thresholds and window were selected retrospectively. Paired five-game block intervals are exploratory, not selection-adjusted confidence in an edge. No source quote archive, licensed odds feed, pregame information archive or untouched prospective test exists. A scoring-selected top-15 table is not a complete player universe. Details are on **Flagged for Review**.

## Website and deployment

`scripts/build_site.py` generates all canonical root pages and redirects old `pages/` and `verified/` HTML URLs to the matching current category. The old JSON schemas are explicit deprecation pointers, not duplicate sources of truth. The original script names remain compatibility entrypoints.

GitHub Pages publishes the root of `main`. CI checks source/blank contracts, receipts, math, chronology, recursive links/fragments, byte-identical rebuilds, keyboard interactions, CSV export, desktop/mobile rendering and accessibility. Scheduled source-health checks save non-mutating audit artifacts; they never collect NBA feeds or promote a source URL to factual verification. Claims/deployment evidence are recorded in `COORDINATION.md`.

No repository license was inferred or granted. Third-party source terms remain applicable. Non-monetary merit points have no cash/transferable value; no eligible strategy currently earns any.

## Parallel-session integration

Incoming main `37e1bbd` contained 77 files and multiple completed contributions. All source dossiers, historical transcriptions, dated audits, append-only boards and correlation outputs were retained. Shared canonical pages use the one generator; `findings.html` also redirects to the data library.

The canonical **Market evidence** category exposes all 24 B1 operator-specific findings; all six MF flags are on central review. The original source-linked card dossier is retained at `market-evidence/index.html`, with its own eight structural tests. It is a supplementary primary-source packet, not an alternative betting dashboard. Relevant official paragraphs were independently re-read during final integration.

Six team coefficients and 11 F58 season-level rows are independently recomputed and displayed separately from paired-game dependence. Their Fisher intervals are nominal assumption-based calculations; team dependence, scoring selection and lack of generalizable coverage are flagged. The original scripts/outputs remain attributed under `handoff/f58e9526/`.

Netherlands context, Kansspelwijzer and Gokstop are linked. Current NBA operator/market applicability and US-to-NL memo applicability remain blank. The earlier Dutch support gap was resolved by the official Cruks contact page (Open over Gokken, 0800 24 000 22, 24/7). This does not validate legacy Alberta or media-policy claims.
