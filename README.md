# OWN7 · research lab (NBA archive · SF rental · NFL)

[Live dashboard](https://sassnarep3-star.github.io/Own7/) · [NFL research site](https://sassnarep3-star.github.io/Own7/nfl/index.html) · [**NFL line-origination lab**](https://sassnarep3-star.github.io/Own7/nfl/origination/index.html) · [NFL assurance handoff](https://sassnarep3-star.github.io/Own7/nfl-assurance-9580ac3f/site/index.html) · [NBA executive brief](docs/executive-summary.md) · [Sources](research/sources.json) · [Coordination / release evidence](COORDINATION.md)

> **Sections by status.** The **NFL sections** are the active programme and are split in two layers, described below. The **NBA research** section is an earlier, retained audit and is now an archive of that work. The **SF rental** sections are a separate, unrelated analysis. Shared navigation labels each group; nothing was deleted and no historical claim was relabelled as verified.

## NFL · two layers, one navigation group

Two sessions built NFL content on the same day. They answer different questions, they are cross-linked, and they write disjoint files. Neither overwrote the other.

### 1. NFL research site — `nfl/` (session `arena/a4e560bc-own7`, Week 7 snapshot)

A source-linked research workspace: standings and player/team statistics, a signal library, generic pricing identities, injuries and backup coverage, validation gates, an empty leaderboard, a requirements ledger, suggestions and questions, and a Flagged for Review register (NF01–NF11). Its position is explicit: **no NFL lines are originated there** and NFL-derived betting prices are withheld under the source-rights gate.

### 2. NFL line-origination lab — `nfl/origination/` (session `arena/20394b77-own7`, Week 10 snapshot)

Adds the part the first layer withholds, as a model-only demonstration: spreads and totals for all 14 Week 10 games from a shrunk win-percentage and Pythagorean baseline with sensitivity bounds, 210 injury rows checked against two official NFL.com pages, depth-chart deficiencies for three clubs joined to that injury report, ten fail-closed gates, and **Suggestions** and **Open questions** registers.

- **Verified:** 32/32 standings rows pass three arithmetic identities (win percentage, net points, and league-wide points for = points against at 6,246 over 272 team-games); injury practice status agrees with the official Wednesday roundup on every overlapping player; injury-report deadlines are quoted from the league's calendar.
- **Model-derived, never a market price:** every line is labelled as the model's output. No sportsbook was scraped, and no price, edge, ROI or CLV value exists anywhere in the tree.
- **Not verified, therefore blank:** every market price, every leg-level correlation, 21 injury types the sources do not publish, depth evidence for 25 of the 28 slate clubs, and the reason four clubs are absent from the slate.
- **Nothing qualifies.** Eight strategies are registered and all are blocked; the leaderboard is empty; no reward is paid and no cash prize exists.
- **Rights:** [NFL.com Terms §1.3](https://www.nfl.com/legal/terms/) permits individual, non-commercial, informational use only and prohibits systematic retrieval or compilation. This is a small dated sample under that limit, not a data product.

Reproduce (standard library only, no network): `python nfl/build.py --check`, `python nfl/origination/originate.py --check`, `python -m unittest discover -s nfl/origination -p "test_*.py" -v`.

Detailed evidence: `docs/nfl-executive-summary.md` (research site), `docs/nfl-origination-summary.md` (lab), `docs/nfl-repo-review-2026-11-12.md` (repo review, irregularities I-01…I-11), `COORDINATION.md` (claims, collision and resolution).

### 3. NFL assurance handoff — `nfl-assurance-9580ac3f/` (session `arena/9580ac3f-own7`)

An independent, bounded assurance supplement: 276 official Week 10 injury rows, 289 club-published depth slots across ten clubs, a 150-file / 14,244-line frozen-baseline inventory, executable fail-closed validation/leaderboard primitives, reviewable suggestions/questions and a Flagged for Review register. It preserves shared cells, blank columns and missing statuses; it does not infer replacements, performance deficits, market prices, correlations, ROI or CLV. Source IDs are namespaced `A958-*` to avoid re-pointing canonical registry entries.

Reproduce: `python nfl-assurance-9580ac3f/build.py --check`, `python nfl-assurance-9580ac3f/check.py`, `python -m unittest discover -s nfl-assurance-9580ac3f/tests -v`.

---

## NBA research archive

One static, source-linked dashboard replaces the repository’s three inconsistent earlier sites. It contains **107 checked official snapshot rows**, eight strategy hypotheses, six paired-game exploratory estimates plus 17 contributed aggregate-correlation rows (with overlaps), 88 retrospective probability demonstrations, ten fail-closed validation gates, an empty qualified leaderboard, a requirements ledger and a complete baseline file audit.

**No verified betting edge, executable NBA line, ROI, CLV, cash prize or winning strategy is claimed.** Blank values are intentional. Luck cannot be removed.

## Independent verification

`nfl/verify_independent.py` is a second implementation that shares no code with the
pipeline that produced the published figures. It re-derives all 7 published
correlations, the 32 standings rows against league identities, and the passer-rating
formula from the committed snapshots, and reports 2 printed yards-per-attempt values
that disagree with their own row (recorded as NF12, a publisher-side disagreement
confirmed by re-fetch). See `docs/nfl-independent-verification.md`.

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
