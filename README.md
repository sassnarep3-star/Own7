# OWN7 · NFL Origination Lab

[Live site](https://sassnarep3-star.github.io/Own7/) · [NFL executive summary](docs/nfl-executive-summary-2026-11-18.md) · [Historical 2026-11-12 summary](docs/nfl-origination-summary.md) · [Decision brief](https://sassnarep3-star.github.io/Own7/nfl-decisions.html) · [Suggestions](https://sassnarep3-star.github.io/Own7/nfl-suggestions.html) · [Flagged for review](https://sassnarep3-star.github.io/Own7/nfl-review.html) · [Coordination board](COORDINATION.md)

## New: Week 11 injury desk — first Wednesday read, register re-grade (2026-11-18, session arena/3e6166df-own7)

The official NFL injury report now serves **Week 11** (Thursday 19 Nov, Colts at Texans first).
This desk takes one verbatim read of every section on 2026-11-18, derives every row from that
transcript, and cross-checks the fixtures against the official Week 11 schedule transcript and the
team records against the official standings read.

- **26 printed rows**: Colts 11, Texans 15. **24 clubs** print "No Injuries Reported". 13 games, 6 byes.
- **Blank as printed**: all 26 Game Status cells and all 26 Injuries (body part) cells are empty on this read. They stay blank and are flagged (W11-F01, W11-F02).
- **Absent is not available**: the report does not list injured-reserve players. The page's own headline reports QB Malik Willis on injured reserve (W11-F03).
- **Terms gate verified**: NFL.com section 1.3, read verbatim, prohibits systematic retrieval to compile a collection without written consent. So this is one read, not a scheduled series. DR-54 stays Blocked.
- **Register**: DR-54's gate text now cites the terms read and this desk's read. The proposed re-grades of DR-61, DR-64 and DR-68 (Open to Partial) are withdrawn: their artifacts are not yet verified line by line, and one DR-68 quotation does not match the rulebook capture (logged on COORDINATION.md, flagged for review).

| Page | What it answers |
|---|---|
| `nfl-w11-injuries-3e61/site/index.html` | Overview, what is verified, what is blank and why |
| `nfl-w11-injuries-3e61/site/injuries.html` | The 26 printed rows, each linked to the official report |
| `nfl-w11-injuries-3e61/site/slate.html` | 13 games with the printed status of each club, and the 6 byes |
| `nfl-w11-injuries-3e61/site/flagged.html` | Flags W11-F01 to W11-F07, non-blocking |
| `nfl-w11-injuries-3e61/site/sources.html` | Registered sources, read dates, SHA-256 of the transcript |

```sh
python nfl-w11-injuries-3e61/build.py --check          # desk reproduces byte-identically
python -m unittest discover -s nfl-w11-injuries-3e61/tests   # 17 tests
## New: decision-ledger re-grade audit (2026-11-18, session arena/aedccbe5-own7)

Checks every row of the decision-readiness register against the files in the tree and the registered sources,
and proposes re-grades only where the cited artifact contains the quoted text.

| Result | Where |
|---|---|
| 70 of 70 rows: artifact present, every source id registered; 58 rows show an official NFL/club link, 12 are repo-only and say so | [`nfl-ledger-aedccbe5/site/ledger.html`](nfl-ledger-aedccbe5/site/ledger.html) |
| Four proposed re-grades, each with the matched text extracted from its artifact: DR-61, DR-64, DR-68 (Open → Partial) and DR-22 (landing table is 16 NR rows, not the 70-row register) | [`nfl-ledger-aedccbe5/site/regrades.html`](nfl-ledger-aedccbe5/site/regrades.html) |
| Five gates re-read against official pages on 2026-11-18: NFL.com Terms §1.3 (retrieval prohibition) and the 404 at nfl.com/odds | [`nfl-ledger-aedccbe5/site/blocked.html`](nfl-ledger-aedccbe5/site/blocked.html) |
| Six non-blocking flags, including the landing-table mismatch and two canonical results files (149 and 150 rows) | [`nfl-ledger-aedccbe5/site/flagged.html`](nfl-ledger-aedccbe5/site/flagged.html) |

The register is not edited by this desk; the integration owner applies the proposals.

```sh
python nfl-ledger-aedccbe5/build.py --check   # byte-identical reproduction
python -m unittest discover -s nfl-ledger-aedccbe5/tests -v   # 13 tests
```

## New: fresh-reads desk — Week 10 completion + Week 11 readiness (2026-11-18, session arena/6c72a9fa-own7)

Official reads taken the morning after the Week 10 Monday game (`nfl-week11-6c72a9fa/`, 7 pages,
10 tests, deterministic `build.py --check`):

| Result | Where |
|---|---|
| **Chargers 23, Ravens 20 — final** verified from the official game centre and the overnight-published **Game Book #14** (official starters 22+22, Not Active 12, M&T Bank Stadium, Clear 49°F NW 2 mph, attendance 69,679) | [`nfl-week11-6c72a9fa/site/verification-2026-11-18.html`](nfl-week11-6c72a9fa/site/verification-2026-11-18.html) |
| **32/32 standings cells re-verified**: fresh page = 2026-11-17 pre-MNF capture + the LAC@BAL final exactly (BAL +1L +20PF +23PA; LAC +1W +23PF +20PA; 30 clubs cell-identical), and frozen 2026-11-12 + all 14 Week 10 finals re-derives every club | same page |
| **Week 10 venue coverage now 14/14** (closes the 13-of-14 gap, DR-23/DR-25) | same page |
| **League reserve-list sweep** (Nov + Oct windows, +8/-8 rows vs the 2026-11-17 capture) with the rolling-window limitation flagged (FG01); November trades page dates the Brissett (AZ→BAL, 11/06), Allen (IND→SF) and Downs (IND→KC) moves (RG02) | [`nfl-week11-6c72a9fa/site/reserve-sweep.html`](nfl-week11-6c72a9fa/site/reserve-sweep.html) |
| **First what-changed ledger (DR-61)**: standings movement, availability-event churn, injury-report stability (50 re-read rows, 0 diffs) and schedule stability (13/13 unchanged vs 2026-11-17) | [`nfl-week11-6c72a9fa/site/what-changed.html`](nfl-week11-6c72a9fa/site/what-changed.html) |
| **Week 11 readiness**: 13 fixtures + 6 byes, venues complete incl. **Estadio Banorte, Mexico City** from the official game centre; injuries hub still served Week 10 at read time (first Week 11 read pending Wednesday publication) | [`nfl-week11-6c72a9fa/site/week11-schedule.html`](nfl-week11-6c72a9fa/site/week11-schedule.html) |
| **Flags FG01–FG07** incl. the rolling-window data-loss property and the LAC@BAL absence from the canonical 149-final corpus (cross-scope request logged, not patched) | [`nfl-week11-6c72a9fa/site/flagged.html`](nfl-week11-6c72a9fa/site/flagged.html) |

```sh
python nfl-week11-6c72a9fa/collect.py      # parse verbatim evidence; aborts on any contradiction
python nfl-week11-6c72a9fa/build.py --check   # byte-identical reproduction
python -m unittest discover -s nfl-week11-6c72a9fa/tests   # 10 tests
```

## New: integration audit — Week 10 completed, DR-68 closed (2026-11-18, session arena/c815bdd2-own7)

A desk that re-derives what the other desks publish, from the official pages, and publishes
the disagreements instead of smoothing them over. Two verifiable results:

- **The Week 10 slate is complete and the feed is one game behind.** Chargers 23, Ravens 20 was
  final on the [official Week 10 page](https://www.nfl.com/schedules/2026/by-week/week-10). The
  canonical feed still holds **149** finals; the [official standings](https://www.nfl.com/standings/)
  read 2026-11-18 imply **150** (sum(W) = sum(L) = 149, sum(PF) = sum(PA) = 6923, 300 club-games).
  The delta between the two official captures is exactly the settled headline, and re-tallying
  the feed leaves exactly that one game. Proved three ways; the build aborts otherwise.
  The stale feed is **flagged, not patched** — it belongs to another session.
- **Requirement DR-68 is closed from the official rulebook.** Rule **6-1-6** of the
  [2026 Official Playing Rules](https://media.nfl.com/content/dam/communications/Official%20Playing%20Rules/2026%20Official%20Playing%20Rules.pdf)
  permits a declared onside kick **at any time during the game**, with mandatory notification to
  the Referee (so no surprise kick); 6-1-5 sets the 50-yard touchback spot; 6-1-3 changed the
  setup-zone alignment. Every value is pattern-extracted from the retained capture, so a wording
  change fails the build. The *frequency* of declared kicks stays blank: no official
  play-by-play capture is held, and none is estimated.

| Page | What it answers |
|---|---|
| [`nfl-integration-c815/site/index.html`](nfl-integration-c815/site/index.html) | Overview and how to read the desk |
| [`week10-completion.html`](nfl-integration-c815/site/week10-completion.html) | The three-way proof that the feed is one game behind |
| [`requirements.html`](nfl-integration-c815/site/requirements.html) | All 70 requirement rows: published claim beside an independent artefact check |
| [`rules-2026.html`](nfl-integration-c815/site/rules-2026.html) | The 2026 kickoff/onside regime, verbatim, plus the bias register |
| [`suggestions.html`](nfl-integration-c815/site/suggestions.html) | 5 ranked changes, each with an acceptance test |
| [`flagged.html`](nfl-integration-c815/site/flagged.html) | 4 irregularities, non-blocking |
| [`sources.html`](nfl-integration-c815/site/sources.html) | Every official URL read, with the capture SHA-256 |

```sh
python nfl-integration-c815/build.py            # regenerate the desk
python nfl-integration-c815/build.py --check    # byte-identical reproduction
python -m unittest discover -s nfl-integration-c815/tests   # 19 tests
```

## New: weeks 1-10 results feed completed, fresh 2026-11-18 reads (session arena/92cad499-own7)

The verified results feed is **complete through Week 10: 150 official finals**. The frozen
2026-11-17 read held 13 of 14 Week 10 finals; the 2026-11-18 completion re-read of the
official by-week page adds **Chargers 23, Ravens 20, FINAL, Monday, November 16th**, is
cross-checked line by line against the frozen read before publication, and reconciles against
a fresh 2026-11-18 standings snapshot. Week 11 (13 fixtures + 6 byes) and Week 12 (16 fixtures,
including a Wednesday and a Friday game) are captured as scheduled fixtures only — a fixture
with a kickoff time is never a result.

| Page | What it answers |
|---|---|
| `nfl-fresh-1118/site/index.html` | Overview: read receipts with SHA-256, FV1-FV7 checks, what changed |
| `nfl-fresh-1118/site/results-feed.html` | The Week 10 completion, corpus shape, the five reconciliation identities |
| `nfl-fresh-1118/site/schedule.html` | Weeks 11-12 slates exactly as printed, beside the league's dated schedule announcement |
| `nfl-fresh-1118/site/flagged.html` | 4 flags, including the flagged-partial injury-hub read and the REG10 URL redirect |

- **Five reconciliation identities now hold** (160 fields each, 800 total): weeks 1-9 vs the
  frozen pre-kickoff snapshot, the frozen weeks 1-10 feed vs the 2026-11-17 snapshot, the
  completed weeks 1-10 feed vs the 2026-11-18 snapshot, and both chain identities between
  snapshots. Every frozen 2026-11-14/11-17 artefact stays byte-identical.
- **The skill engine re-graded on the completed corpus** (134 scored rows): spread board
  **61.2%** (permutation p=0.0065, BH q=0.086), total board 49.3%, leg dependence phi −0.032
  (p=0.72, n=128). Still zero qualified strategies and zero rewards.
- **Decision-readiness ledger re-graded** (DR-02/16/19/26) — DR-02's published clearing
  condition ("the feed reaches 150 when the Monday night final posts") is now met.
- **Injury hub read flagged partial** (chunks 0-3 of 8; the Week 11 view was client-side and
  not fetchable, returning the site's 404): recorded with its clock time, no delta published
  from an incomplete capture; follow-up task F1 is on the coordination board.

```sh
python nfl-results/extract.py       # five reconciliation identities; refuses contradictions
python nfl-results/engine.py        # re-grade on the completed 150-final corpus
python nfl-fresh-1118/build.py --check          # desk reproduces byte-identically
python -m unittest discover -s nfl-fresh-1118/tests   # 8 tests
```

---

## New: Week 11 decision desk — Week 10 closure, availability joins and the snap-count verdict (2026-11-18, session arena/a10fed14-own7)

Live desk: [Week 11 decision desk](https://sassnarep3-star.github.io/Own7/nfl-week11-4c7d/site/index.html) ·
[Executive summary](https://sassnarep3-star.github.io/Own7/nfl-week11-4c7d/site/executive-summary.html) ·
[Questions](https://sassnarep3-star.github.io/Own7/nfl-week11-4c7d/site/questions.html) ·
[Suggestions](https://sassnarep3-star.github.io/Own7/nfl-week11-4c7d/site/suggestions.html) ·
[Flagged for review](https://sassnarep3-star.github.io/Own7/nfl-week11-4c7d/site/flagged.html)

- **Week 10 is closed.** The Monday-night game that was still pending for every earlier capture is
  now final — **Los Angeles Chargers 23, Baltimore Ravens 20** — and its official Game Book is
  captured. All 14 games and 28 clubs now hold official starters, substitutions, Did Not Play and
  Not Active lists, plus venue, roof and surface, weather, temperature, humidity, wind and
  attendance.
- **The closure is proven, not asserted.** The standings read on 2026-11-18 reproduce exactly from
  the retained 2026-11-17 snapshot plus that one result: **32 clubs, seven fields each
  (W, L, T, PCT, PF, PA, net points), zero mismatches.**
- **The availability join is complete for the week: 329 rows**, matched on club, surname and first
  initial so that two players with the same surname on one club (New England's A.J. Brown and Ben
  Brown) are not confused, and generational suffixes are stripped (the report prints Carlton Davis
  III where the Game Book prints C.Davis).
- **The reserve-list gap is measured: 86 of 158 official inactives (0.5443) appear nowhere on the
  weekly injury report.** "Not listed" can never be read as "available".
- **No official snap-count source exists.** Four probes read on 2026-11-18 — nfl.com team stats,
  nfl.com player stats, the official Game Book, and 13 retained Game Book extracts — and none of
  them publishes snap counts. Requirements R11, R31 and R56 therefore stay open, and the Game Book
  starter list remains the only official playing-participation evidence.
- **A new lookahead-leak surface was found.** The NFL injury report re-renders club records after
  kickoff: identical Monday rows printed LAC (0-8) and BAL (4-5) on 2026-11-17 and print LAC (1-8)
  and BAL (4-6) on 2026-11-18. Captures must be taken before kickoff, always.
- **The Week 11 injury report was not published at read time** (the Week 11 URL served Week 10), so
  no Week 11 personnel row is transcribed. Nothing was inferred in its place.
- Decision content: **10 questions** (held / missing / what closes it), **8 ranked suggestions**
  (adopt, defer and reject paths) and a **10-row requirement delta** naming the gate that blocks
  each item and the number that would clear it.
- No price, odds, ROI, closing-line value, stake, wager or reward is produced anywhere on this desk.
- Batteries green: 35 desk unit tests, byte-identical rebuild, `check.py` clean (13 pages, 235
  table rows, 10 registered sources), recursive site audit (256 pages, 9,984 rows, 273 registered
  sources, 0 errors) and 236 desktop + 236 mobile browser pages at WCAG A/AA.

## New: integration, Week 10 extension, decision-readiness landing (2026-11-17, session arena/e15f05e0-own7)

- **The verified results feed now reaches Week 10.** Official reads on 2026-11-17 (standings +
  REG10 schedule) extend the feed from 136 to **149 finals**. Three reconciliations hold: weeks
  1-9 vs the frozen pre-kickoff snapshot, weeks 1-10 (minus the one scheduled-not-final game,
  Chargers at Ravens) vs the fresh 2026-11-17 snapshot, and fresh = frozen + parsed Week 10
  deltas. The frozen origination input was not touched (no lookahead).
- **The landing page now carries the decision-readiness ledger** the brief asked for: one row per
  requirement, the gate that blocks it, and the number that would clear it (`research/nfl-decision-readiness.json`, 70 rows).
- **The competition lab (PR #51) was merged additively** into the integrated tree (16 pages, 59
  tests, its own price store/origination-order/boards/leaderboard/depth/correlations/demotion
  artifacts). Four stale sibling PRs (#17, #27, #48, #50) were closed with documented rationale —
  published as flag NF22 on the Flagged for Review page.
- All batteries green on the combined tree: 111 + 27 + 59 + desk suites, every desk `--check`,
  recursive site check (registered row sources, blank rules, receipts, deterministic rebuilds),
  and 190 desktop + 190 mobile browser pages at WCAG A/AA.

## New: official results & skill lab (2026-11-14)

Every earlier session recorded that no NFL result archive existed, so the leaderboard stayed empty
and luck could not be removed. **That premise was wrong.** NFL.com publishes a final score for
every past game on its by-week pages, and 149 of them are now captured and reconciled
(160/160 standings fields per snapshot: weeks 1-9 against the frozen pre-kickoff read,
weeks 1-10 against the fresh 2026-11-17 read, and fresh = frozen + parsed Week 10 deltas)
with a build that aborts on any mismatch.

That unlocks the analysis the requirements actually asked for:

| Page | What it answers |
|---|---|
| `nfl-results.html` | Overview and the five findings |
| `nfl-results-games.html` | All 149 official scores and 20 bye rows (plus 1 scheduled-not-final fixture), each with its source page |
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

## New: decision-readiness desk (2026-11-17, session arena/1467fdf7-own7)

[`nfl-readiness-1467fdf7/site/index.html`](nfl-readiness-1467fdf7/site/index.html) answers, for each of the 79 requirement rows in the brief: what is built, what blocks it, and what number would clear it. It also holds the pre-registered controls, the two-sided "what would change our mind" register, and an injury spot-check against the official Week 10 page.

- **Controls** (`strategies.py` frozen at commit `813ce25`): always-home 49.6%, seeded random 49.6%, higher-prior-win-% 60.7% (n = 135). None clears the sample gate (n ≥ 153), and none is ranked.
- **Injury spot-check:** 44 rows compared against the official page; 3 Detroit rows disagree. Cause open.
- **Blocked by rights:** scheduled and repeated captures of nfl.com are systematic retrieval under [Terms §1.3](https://www.nfl.com/legal/terms/). No such capture was added. See flag F01.
- Executive summary: [`docs/nfl-readiness-1467fdf7-executive-summary.md`](docs/nfl-readiness-1467fdf7-executive-summary.md).

```sh
python nfl-readiness-1467fdf7/build.py --check
python -m unittest discover -s nfl-readiness-1467fdf7/tests -v
```

## New: Week 10 completion, weekly diff, 2026 rules (2026-11-18, session arena/03dcea07-own7)

[`nfl-slate-03dcea07/site/index.html`](nfl-slate-03dcea07/site/index.html) closes the last open
Week 10 item and turns the dated official reads into a rendered "what changed" view:

- **The 14th Game Book (LAC at BAL).** The official Game Book PDF now publishes the Monday game
  (Chargers 23, Ravens 20 — the season's 150th final). Week 10's venue, roof/surface, weather,
  attendance, actual-starters (44 rows) and Not-Active capture is complete at **14/14**
  (13 committed by the Game Book desk + this desk's W10-14, emitted in the same CSV schema).
- **Weekly diff (DR-61).** Three dated official standings reads (2026-11-12 frozen,
  2026-11-17, 2026-11-18) produce rendered per-club deltas; every nonzero delta is re-derived
  from the finals between the reads (checks V2/V3 re-derive all 32 clubs' W/L/T/PCT/PF/PA/NET/
  Home/Road — and Div/Conf from the 2026-11-17 baseline — with zero mismatches).
- **2026 rules (DR-68).** The official 2026 rulebook table is quoted verbatim, including
  Rule 6-1-6 "Permits the kicking team to declare an onside kick at any time during the game."
- Flags SL01–SL06 (secondary-source disagreement on the onside rule; Week 11 report not yet
  published at read time; spot-check scope; Game Book copyright notice; one unlabelled rendered
  cell; frozen-corpus cross-scope note) are published on the desk's Flagged page.

```sh
python nfl-slate-03dcea07/build.py --check
python -m unittest discover -s nfl-slate-03dcea07/tests -v
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
- **Zero** qualified strategies, rewards, wagers or recommendations. Since 2026-11-14 a retrieval gap has been closed: 149 official final scores (through Week 10, read 2026-11-17) are captured and graded, and the results are on the `nfl-results` pages.

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

## New: NFL snap-count / playing-time desk (2026-11-18, session arena/e5e4351c-own7)

A new desk captures the official per-player **Playtime Percentage** table (snap counts and snap
share on Offense, Defense and Special Teams) from all 13 played Week 10 NFL Game Books, and
derives the measurable starter/backup split from playing time. This resolves four open brief
requirements: R11 (model depth from playing time, not jersey order), R31 (capture official snap
counts), R52 (the snap count is the official depth-order source) and R56 (snap counts as the
starter proxy where a printed depth chart is unavailable). Depth order here is ranked by snap
count only - never by jersey number, experience or salary.

| Page | What it answers |
|---|---|
| [`nfl-snapcount-e5e4/site/index.html`](nfl-snapcount-e5e4/site/index.html) | Desk overview: 13 Game Books, 1,217 snap records, playing-time depth |
| [`nfl-snapcount-e5e4/site/snap-records.html`](nfl-snapcount-e5e4/site/snap-records.html) | Per-game snap records: the verbatim snap counts and share for every player |
| [`nfl-snapcount-e5e4/site/position-group-shares.html`](nfl-snapcount-e5e4/site/position-group-shares.html) | Position-group snap shares: each group's share of a team's snaps per phase |
| [`nfl-snapcount-e5e4/site/playtime-depth.html`](nfl-snapcount-e5e4/site/playtime-depth.html) | Playing-time depth: every player ranked by snaps; rank 1 = starter |
| [`nfl-snapcount-e5e4/site/replacement-depth.html`](nfl-snapcount-e5e4/site/replacement-depth.html) | Replacement depth: who is behind each starter, by snaps played |
| [`nfl-snapcount-e5e4/site/depth-vs-snap.html`](nfl-snapcount-e5e4/site/depth-vs-snap.html) | Why the printed-depth cross-reference is a published zero-row gap |
| [`nfl-snapcount-e5e4/site/flagged.html`](nfl-snapcount-e5e4/site/flagged.html) | 5 flags: the "(Unofficial)" labels, the zero-row gap, the missing 14th game, 2 dedup notes |

Source: the official NFL Game Book PDFs linked from the [NFL Game Centre](https://www.nfl.com/games/).
Four of the thirteen Playtime Percentage tables are labelled "(Unofficial)" inside their PDFs;
the label is carried verbatim on each row. No price, ROI, CLV, stake or wager is produced.

```sh
python nfl-snapcount-e5e4/build.py --check      # byte-identical data artefacts
python nfl-snapcount-e5e4/build_site.py --check  # byte-identical desk pages
python -m unittest discover -s nfl-snapcount-e5e4/tests -v   # 25 tests
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
