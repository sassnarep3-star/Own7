# OWN7 · NFL Origination Lab

[Live site](https://sassnarep3-star.github.io/Own7/) · [NFL executive summary](docs/nfl-origination-summary.md) · [Decision brief](https://sassnarep3-star.github.io/Own7/nfl-decisions.html) · [Suggestions](https://sassnarep3-star.github.io/Own7/nfl-suggestions.html) · [Flagged for review](https://sassnarep3-star.github.io/Own7/nfl-review.html) · [Coordination board](COORDINATION.md)

## New: official results & skill lab (2026-11-14)

Every earlier session recorded that no NFL result archive existed, so the leaderboard stayed empty
and luck could not be removed. **That premise was wrong.** NFL.com publishes a final score for
every past game on its by-week pages, and 136 of them are now captured and reconciled
(160/160 standings fields) with a build that aborts on any mismatch.

That unlocks the analysis the requirements actually asked for:

| Page | What it answers |
|---|---|
| `nfl-results.html` | Overview and the five findings |
| `nfl-results-games.html` | All 136 official scores and 16 byes, each with its source page |
| `nfl-results-skill.html` | Skill vs luck: spread board **64.2%** (permutation p=0.0021, BH q=0.022) against a total board at exactly **50.0%** |
| `nfl-results-correlation.html` | Leg dependence measured from joint outcomes: phi −0.068 (p=0.47), not independent enough to reprice |
| `nfl-results-leaderboard.html` | 30 variants graded; 1 provisional, 0 qualified, **every reward blank** because no price exists |
| `nfl-results-decisions.html` | 8 questions split into known-with-source and still-missing |
| `nfl-results-suggestions.html` | 6 ranked suggestions with evidence, cost, risk and an acceptance test |
| `nfl-results-flagged.html` | 10 irregularities, including two bugs found and fixed before publication |

```sh
python nfl-results/extract.py    # re-parse saved official text; refuses contradictions
python nfl-results/engine.py     # leakage-free walk-forward grading, permutation null, FDR
python -m unittest discover -s nfl-results/tests   # 23 tests
```

Full write-up: [`docs/nfl-results-executive-summary.md`](docs/nfl-results-executive-summary.md).

## New: market-lifecycle desk (2026-11-14, session arena/3f5c4cd6-own7)

The eight lifecycle requirements from the brief now have deterministic, source-linked artefacts in
`nfl-lifecycle-3f5c/` (14 pages, 8 data files, 37 tests; additive to every prior desk):

| Requirement | Where |
|---|---|
| Price-snapshot store (open + close per originated market) | [`nfl-lifecycle-3f5c/site/price-snapshots.html`](nfl-lifecycle-3f5c/site/price-snapshots.html) — 42 records, append-only, market cells blank by rights |
| Originate side → total → moneyline | [`nfl-lifecycle-3f5c/site/origination-order.html`](nfl-lifecycle-3f5c/site/origination-order.html) — reconciles exactly with the canonical engine (14/14) |
| Fair / market / difference as separate columns | [`nfl-lifecycle-3f5c/site/fair-market-diff.html`](nfl-lifecycle-3f5c/site/fair-market-diff.html) — difference blank whenever the market line is blank |
| Signal separated from staking | [`nfl-lifecycle-3f5c/site/leaderboard.html`](nfl-lifecycle-3f5c/site/leaderboard.html) — rank computed from signal fields only, proven by test |
| Depth of the replacement | [`nfl-lifecycle-3f5c/site/replacement-depth.html`](nfl-lifecycle-3f5c/site/replacement-depth.html) — 173 starter losses, 158 printed named replacements, 12/12 spot-traced |
| Correlations from official numbers with n | [`nfl-lifecycle-3f5c/site/correlation-audit.html`](nfl-lifecycle-3f5c/site/correlation-audit.html) — 22 rows audited, 0 failures |
| Demotion gate (live → paper) | [`nfl-lifecycle-3f5c/site/demotion.html`](nfl-lifecycle-3f5c/site/demotion.html) — DG-1 pre-registered, armed, 0 live entries |
| Questions / suggestions for review | [`nfl-lifecycle-3f5c/site/questions.html`](nfl-lifecycle-3f5c/site/questions.html) · [`nfl-lifecycle-3f5c/site/suggestions.html`](nfl-lifecycle-3f5c/site/suggestions.html) |

Fresh official reads this session: nfl.com standings + REG10 schedule (2026-11-14), including the
official final **Commanders 24, Giants 21**. Executive summary:
[`docs/nfl-lifecycle-3f5c-executive-summary.md`](docs/nfl-lifecycle-3f5c-executive-summary.md).

```sh
python nfl-lifecycle-3f5c/build.py            # rebuild desk artefacts + pages
python nfl-lifecycle-3f5c/build.py --check    # byte-identical reproduction
python -m unittest discover -s nfl-lifecycle-3f5c/tests   # 37 tests
```

## What this is now

The landing page is an **NFL research workspace**. It originates its own lines from official NFL
data, then tries to falsify them. It publishes what it knows, what it does not know, and a ranked
list of suggestions for closing the gaps, so a change can be reviewed and chosen before anything
is implemented.

- **66 verified NFL rows**, parsed from saved official page text on 2026-11-12 and re-derived
  arithmetically before publication: 32 club standings rows, 20 injury-report rows, 14 Week 10
  fixtures. `scripts/nfl_extract.py` aborts instead of publishing a contradiction.
- **14 originated games** with a model spread, total and fair price from one coherent score pair.
  No sportsbook price was retrieved, so market cells, ROI and CLV are blank by rule.
- **10 ranked suggestions**, **14 decision questions**, **12 review flags**, **10 validation gates**
  (two pass, one partial, one open on rights) and **8 blocked strategies** with an empty leaderboard.
- **Zero** qualified strategies, rewards, wagers or recommendations. Since 2026-11-14 a retrieval gap has been closed: 136 official final scores are captured and graded, and the results are on the `nfl-results` pages.

NFL data is attributed to NFL.com. This is not affiliated with or endorsed by the NFL. NFL.com terms
§1.3 permit individual non-commercial informational use and prohibit systematic retrieval to compile
a collection without written consent, so no dataset is released and nothing is scraped on a schedule.

## Reproduce without manual data entry

Python 3.11+; no third-party Python packages.

```sh
python scripts/nfl_extract.py --check   # re-parse saved official NFL text; refuse contradictions
python -m nfl_origination run                   # derive lines, calibration, correlations, gates
python -m unittest discover -s tests    # 108 tests
python scripts/build_site.py            # regenerate every page deterministically
python scripts/check_site.py            # links, fragments, per-row sources, blank rules
npm ci && npm run test:browser          # 46 desktop + 46 mobile pages, WCAG A/AA
python scripts/serve_site.py --host 0.0.0.0 --port 8080
```

## The NFL section

| Page | What it answers |
|---|---|
| `index.html` | Overview, headline findings and the five things that matter |
| `nfl-suggestions.html` | **Suggestions to review** — a decision hub: ranked proposals, 1-5 scores, prerequisites, an acceptance test and a review workflow, plus a crosswalk to the sub-site register |
| `nfl-decisions.html` | What we know, what we do not know, and what closes each gap |
| `nfl-questions.html` | 17 questions, each split into sourced and open parts |
| `nfl-lines.html` | Line origination: method, assumptions, originated board |
| `nfl-correlation.html` | Team-level dependence, and what is deliberately not estimated |
| `nfl-injuries.html` | Official statuses, and why starter/backup impact is blank |
| `nfl-standings.html` | All 32 clubs, re-derived; six of sixteen displayed fields withheld and explained |
| `nfl-validation.html` | Ten gates and the per-strategy gate matrix |
| `nfl-leaderboard.html` | The frozen competition format, empty by rule |
| `nfl-verification-2026-11-13.html` | **Re-verification, 13 Nov 2026** — every published NFL value re-read from the publisher, all 32 rows side by side |
| `nfl-review.html` | 21 flagged irregularities with official source links (17 open, 4 corrected) |

## New: readiness-audit desk (2026-11-17, session arena/e7efbde7-own7)

A fresh session re-verified the published NFL data line by line against new official reads and
published the brief's decision-readiness table in full:

| Page | What it answers |
|---|---|
| [`nfl-readiness-e7ef/site/index.html`](nfl-readiness-e7ef/site/index.html) | Desk overview: what was read, what was reconciled, what was found |
| [`nfl-readiness-e7ef/site/verification-2026-11-17.html`](nfl-readiness-e7ef/site/verification-2026-11-17.html) | Line-by-line verification: 32 standings rows, 13 Week 10 finals + 1 pending game, 13 Week 11 fixtures + 6 byes, 347 injury rows — each with its official source |
| [`nfl-readiness-e7ef/site/requirement-readiness.html`](nfl-readiness-e7ef/site/requirement-readiness.html) | **One row per requirement of the brief**, with the gate that blocks it and the number that would clear it (80 rows: satisfied / partial / open) |
| [`nfl-readiness-e7ef/site/flagged.html`](nfl-readiness-e7ef/site/flagged.html) | 5 desk flags (2 state/open, 3 explained) + 2 publisher-side resolutions since 2026-11-14 |
| [`nfl-readiness-e7ef/site/sources.html`](nfl-readiness-e7ef/site/sources.html) | The four hashed evidence transcripts and the desk's registered sources |

Fresh official reads (2026-11-17 00:45 UTC): [standings](https://www.nfl.com/standings/),
[REG10 schedule](https://www.nfl.com/schedules/2026/REG10/),
[Week 11](https://www.nfl.com/schedules/2026/by-week/week-11),
[injury report](https://www.nfl.com/injuries/). The Monday LAC@BAL game was pre-kickoff at read
time and is stored as pending, never imputed. Verification checks (three-way standings
reconciliation, fixture joins, games-played ledger against the 136-game corpus, Week 11 slate
completeness, injury-row matching, cross-page record consistency) re-run on every build and in
CI; a single mismatch aborts.

```sh
python nfl-readiness-e7ef/collect.py --check   # re-parse evidence, refuse contradictions
python nfl-readiness-e7ef/build.py --check     # byte-identical desk pages
python -m unittest discover -s nfl-readiness-e7ef/tests -t .   # 13 tests
```

## Skill & availability desk (2026-11-14)

New self-contained desk at `nfl-skill-cfdd/`, published at
[`nfl-skill-cfdd/site/index.html`](nfl-skill-cfdd/site/index.html). Executive summary:
[`docs/skill-cfdd-executive-summary.md`](docs/skill-cfdd-executive-summary.md).

- **32/32 standings rows re-verified** on 2026-11-14 with `PCT`, `NET`, `PF = PA` and `W = L`
  re-derived; the build aborts on any contradiction. Two clubs moved and their deltas imply
  exactly one result, WAS 24 - NYG 21.
- **The four clubs with no captured depth chart were the four Week 10 bye clubs** (CHI, DEN, PHI,
  TB). All four are now captured: 231 printed slots, 265 of 326 injury rows matched, and Houston
  recorded as unreadable on two independent reads.
- **Skill was tested, not asserted.** Pythagorean residuals give chi-square 19.03 on 32 df,
  **p = 0.966**, variance inflation 0.59 - no detectable club-level skill in this snapshot.
  10 strategies, **12 computed gates** (6 pass, 5 fail, 1 blocked on source rights),
  **0 qualified, 0 rewards**. At 80% power a 60% true rate needs **153 settled bets**; a 52.4%
  rate needs 2,682. There are 0.
- **15 questions, 10 suggestions, 12 flags**, with a decision record that is deliberately blank.

```sh
cd nfl-skill-cfdd
python collect.py && python depth.py && python index.py && python luck.py \
  && python ledger.py && python decisions.py && python build.py
python -m unittest discover -s tests -v      # 49 tests
```

## Price & market desk (2026-11-14)

New self-contained desk at `nfl-pricing/`, published at
[`nfl-pricing/site/index.html`](nfl-pricing/site/index.html).

- **136 closing prices** reconciled from 32 club pages: the two pages per game must agree on the
  total and be exact negatives on the signed spread, and all 272 publisher verdicts were re-derived
  with **0 mismatches**. No source read publishes an **opening** number, a moneyline or a player
  prop, so those cells are blank and flagged, never estimated.
- **Side → total → moneyline in that order**, enforced in code: 120 of 136 games produce all three,
  and the 16 withheld rows carry no total and no moneyline because the side is missing.
- **Signal is ranked; staking is not.** 12 variants, **0 ranked**, 11 eligible-but-not-significant,
  8 returned to paper by gate DG01. At 80% power a 55% rate needs **617 settled selections**.
- **The market is sharper than we are, and it is printed that way.** The published close correlates
  −0.439 with the actual margin (n=136); our fair line correlates −0.2227 (n=120). Our **total** has
  the **wrong sign** (−0.0418 against the market's +0.3771) and is published as a defect, not tuned
  away on the same games.
- **Depth of the replacement**: 1,817 printed slots from two non-overlapping files, 265 matched
  injury rows, 65 where no name is printed behind the injured player.
- **12 questions, 8 suggestions, 14 flags**, with a decision record that is deliberately blank.

```sh
python nfl-pricing/collect.py && python nfl-pricing/originate.py \
  && python nfl-pricing/leaderboard.py && python nfl-pricing/correlations.py \
  && python nfl-pricing/depth.py && python nfl-pricing/questions.py && python nfl-pricing/build.py
python -m unittest discover -s nfl-pricing/tests -t . -v      # 32 tests
```

## Re-verification (2026-11-13)

Every published NFL value was re-read from the publisher on 2026-11-13, one week after the frozen
snapshot: **30 of 32** standings rows, **20 of 20** injury rows and **14 of 14** fixtures are identical.
Two rows moved (WAS and NYG) because the Thursday fixture was played, and the publisher now prints a
final score on one page while still printing "Hidden Score" on the same page. Both are published on
`nfl-verification-2026-11-13.html`; nothing was back-filled into the frozen snapshot. The audit of that
work, including the four defects it fixed and the seven it flagged, is in
`docs/nfl-repo-review-2026-11-13.md` and `docs/nfl-verification-2026-11-13.md`.

## Known limits

One partial season, eight or nine games per club. Every NFL value is single-source. No depth chart,
snap count, player log or market price was retrieved. Division standings columns could not be
identified from the rendered table and are withheld. Five of ten team correlations are arithmetic
artefacts and are labelled as such. Team-level correlation is not leg-level dependence, so no parlay
is priced. Luck cannot be removed. The earlier NBA and rental research remains on the site, unchanged
and separately scoped.

---

## Earlier NBA research workspace (retained, unchanged)

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
