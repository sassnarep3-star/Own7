# NFL repository review — 2026-11-13

Session `session-arena-a97a5100-own7`, branch `arena/a97a5100-own7`, base `b5e3957`.
Companion document: [`nfl-verification-2026-11-13.md`](nfl-verification-2026-11-13.md) (line-by-line
re-check against official sources).

This review is **not** an inheritance of earlier reviews. Every item below was found by reading the
repository and by re-running every builder, test and checker in it today. Where an item repeats an
earlier finding, it is marked *(carried)* and was re-confirmed rather than copied.

Toolchain replayed today, all green before any change was made:

| Command | Result |
|---|---|
| `python -m unittest discover -s tests` | 96 tests, OK |
| `python scripts/nfl_extract.py --check` | 32 standings rows, 20 injury rows, 14 fixtures, 0 flags |
| `python -m nfl_origination run --check` | reproduces exactly from receipt-checked inputs |
| `python scripts/check_site.py` | 115 HTML pages, 2,728 table rows, 117 sources, 0 errors |

The toolchain being green is **not** evidence that the content is true. Several findings below are
cases where a check passed while the published claim was wrong, because no check covered that claim.

---

## A. Factual and internal-consistency irregularities

### A-RR13 — A result that the site says it could not read is now printed by the publisher
`nfl-review.html` and `docs/nfl-repo-review-2026-11-12.md` record RR04: "score pages rendered
'Hidden Score' (no game results transcribed, therefore no backtest)". Today the schedule page prints,
for the same fixture, both `Commanders 24, Giants 21, FINAL` in link text and `Hidden Score` in the
score banners. **The "no result exists" claim is no longer accurate as of today**, even though it was
accurate when written. Reproduced and quoted in
`research/nfl/evidence-2026-11-13/schedule-2026-w10.retrieved.md`.
*Disposition:* published as a new open flag. The snapshot is not rewritten, because rewriting a dated
snapshot with later data would break the receipt chain.

### A-RR14 — Two clubs' published records are now stale
The frozen 2026-11-12 snapshot lists WAS 2-5-1 / PF 172 / PA 202 and NYG 5-2-1 / PF 182 / PA 172.
Today's same page lists WAS 3-5-1 / PF 196 / PA 223 and NYG 5-3-1 / PF 203 / PA 196. Deltas are
internally consistent (WAS +24 PF / +21 PA, NYG +21 PF / +24 PA = a 24-21 Commanders win).
*Disposition:* the freeze is kept and labelled with its capture date; the update is published on the
new verification page so a reader is never told a stale record is current.

### A-RR15 — The landing page says "fourteen open questions"; the register holds fifteen
`research/nfl/questions.json` contains 15 questions (`Q-01`…`Q-15`). The generated pages still print
"Fourteen": `index.html` W1 row, `nfl-questions.html` notice, `scripts/build_site.py` page subtitle,
`README.md`, and `docs/nfl-origination-summary.md`. `Q-15` ("Can luck be removed from the equation?")
is the extra row.
*Cause:* the count is typed as prose in the generator instead of being read from the data.
*Disposition:* fixed by deriving the count from the data and adding a test, so the prose can never
drift from the register again.

### A-RR16 — The "Flagged for review" navigation counter reads 10 while the register holds 12
`scripts/build_site.py` computes `NFL_OPEN` as *open* (`Needs review`) items only, of which there are
10; `research/nfl/flags.json` holds 12 rows, two of which are `Corrected`. On every NFL page the
sidebar therefore shows a count that does not match the page it links to, and `nfl-review.html`
itself heads its table "Flagged for review — NFL" with 12 rows beside a badge of 10.
*Disposition:* the counter is relabelled so it states what it counts (open items), and the review
page states both totals. A count that means two different things in two places is a defect even
when both numbers are individually correct.

### A-RR17 — "Eleven pages · 66 verified rows" describes a twelve-page section
The landing page's workstream table (row W1) states 11 pages. The NFL origination section actually
publishes 12 canonical pages (`index`, `nfl-suggestions`, `executive-summary`, `nfl-decisions`,
`nfl-questions`, `nfl-lines`, `nfl-correlation`, `nfl-injuries`, `nfl-standings`, `nfl-validation`,
`nfl-leaderboard`, `nfl-review`). The row count of 66 is correct (32 + 20 + 14). The same table says
W2 is 15 pages / 216 rows and W3 is 14 pages / 210 rows, and those two are correct.
*Disposition:* fixed by deriving the page count from the build; `README.md` corrected.

### A-RR18 — Every page in the site carries an NBA `<meta name="description">`
`scripts/build_site.py` hard-codes `content="OWN7 NBA research: …"` in the page template, so all 37
canonical pages — including the NFL landing page and every NFL sub-page — describe themselves to
search engines and link previews as NBA research.
*Disposition:* fixed by making the description a per-page value with an NFL default for NFL pages.

### A-RR19 — Two independent suggestion registers with different IDs and different counts
The site publishes `research/nfl/decisions.json` (10 suggestions, `S01`–`S10`, "ranked by decision
value") and the sub-site `nfl/suggestions.html` publishes `research/nfl-suggestions.json`
(12 suggestions, `SU-01`–`SU-12`, "Twelve proposals for review"). The same suggestion appears under
two identifiers with two different texts — e.g. depth charts are `S02` in one register and `SU-03` in
the other. The decision brief's cross-references (`M02` → `S02`) resolve only inside the main register,
so a reader who follows the sub-site's `SU-03` cannot find it from the decision brief.
*Disposition:* not merged (that would discard another workstream's register), but a single
**crosswalk** is now published so either identifier can be followed to the other, and the reviewer
chooses one register to adopt.

### A-RR20 — "Ten validation gates, two pass" is true by construction, not by testing
`nfl_origination/engine.py` assigns gate strings for the eight candidate strategies. `G01` and `G02`
are `pass` for strategies whose inputs are the frozen snapshot, and `G10` is `open` for all eight.
No code executes a statistical test whose outcome could make a gate fail; the gate table is a
hand-written matrix, asserted by a test that it contains the right strings. The page's phrasing
("Ten gates, two passes, one partial and one open rights question. A missing input never counts as a
pass") is accurate about the matrix, but a reader can reasonably infer that gates were *run*.
*Disposition:* published as a flag with the exact code path named, so the claim can be audited.

### A-RR21 — A 0.500 reference is described as a baseline for a quantity that is not a coin flip
`executive-summary.html` E1/H1 compare the Pythagorean Brier score (0.1575) with a "Flat .500 (no
information)" reference (0.25). The 0.25 is the Brier score of a 50% forecast; for NFL home teams the
unconditional home-win rate is not 50%, and the site does not state which rate it used.
*Disposition:* flagged. The comparison direction is not in doubt (the model is better than 0.25), but
the reference is under-specified and is not a market comparison.

### A-RR22 — A model line for a game that had already kicked off is presented in the present tense
`research/nfl/results.json` carries originated spreads and totals for all 14 Week 10 fixtures,
including W10-01 (WAS @ NYG, 2026-11-12 20:15 ET). As of today that game is final. Nothing on
`nfl-lines.html` says the W10-01 number is a closed, unpre-registered retrospection rather than a
live projection, and `G02` (temporal integrity) is marked a blanket `PASS` for "the originated lines"
in the published prose.
*Disposition:* flagged. G02 remains a pass for the eleven fixtures still unplayed, and W10-01 is
labelled as a post-kickoff retrospection. No result is used to score the model on that row.

---

## B. Claims the repository makes that its own data does not support

### B-RR23 — "Starter vs backup exposure" is the owner's central requirement and is not delivered
The request names second-, third- and fourth-string replacements on both sides of the ball.
What exists: `nfl/injuries.html` and `nfl/origination/depth.html` publish positional depth chains for
a bounded set of clubs from **club** sites, and `nfl-injuries.html` publishes 20 official statuses.
What does not exist: a single published mapping from an injured player to the player who replaced him
in a game, and no snap-share, target-share or carry-share column anywhere in the repository.
`nfl.com/teams/<club>/depth-chart` and `nfl.com/teams/depth-chart` were re-checked today and both
return **404**, which is recorded rather than worked around.
*Disposition:* kept blank and flagged. The suggestions section now ranks the depth-and-usage task
first for this reason.

### B-RR24 — Parlays and player-prop combos are named in the navigation and absent in the data
The sub-site publishes pages titled for parlays and player properties, but no combined-leg
distribution exists: `G05` (joint dependence) is `blocked` or `n/a` for every candidate, and there is
no player-level game log in the repository to build one from.
*Disposition:* flagged, with the exact missing inputs listed in the questions register.

### B-RR25 — Correlation is team-level only and cannot support a parlay
Every computed correlation is cross-sectional across 32 club-season rows. Five of ten are arithmetic
artefacts and are already labelled. None is a leg-to-leg correlation, and the site says so.
*Disposition:* no change to the numbers; the missing leg-level work is now an explicit
must-answer-before-parlay question with its own acceptance test.

---

## C. Process irregularities

### C-RR26 — Six NFL workstreams, three suggestion registers, and no single entry point
The repository now contains the origination lab (12 pages), the NFL research lab (16 pages), the line
origination sub-site (14 pages), the assurance handoff (19 pages), plus NBA, rental and market
evidence sub-sites. There are three separate suggestion registers and four separate "flagged for
review" pages. This is the direct cause of A-RR19 and of a reader not being able to tell which page is
authoritative.
*Disposition:* a single **Suggestions and decision hub** is published with a register crosswalk, and
the landing page names one starting point per intent. Nothing is deleted.

### C-RR27 — The audit documents do not state that the working environment cannot reach most of the web
`docs/nfl-verification.md` describes values as verified against official pages. It does not record that
the verification runs through a page-reading proxy and that raw HTTP from the sandbox to `nfl.com`
fails (`curl` returns code 000). A later reader cannot tell whether a row was fetched or recalled.
*Disposition:* today's verification page states the access method per row and records the failure mode.

### C-RR28 — My own draft contained a typed league total, and it was wrong
While writing `docs/nfl-verification-2026-11-13.md` I typed "league total wins (256) = league total
losses (256) across 288 team-games". The real sums over the 32 committed rows are **135 wins, 135
losses, 136 team-games, PF = PA = 6,246**. 256 is Buffalo's points-for. The error is recorded in place
in that document and the correct value is now computed by a test, not typed. This is exactly the class
of defect the review is supposed to catch, so it is listed rather than quietly corrected.

---

## D. What is in good order, and was re-checked rather than assumed

- **Extraction is real.** `scripts/nfl_extract.py` reparses saved page text and aborts on a
  contradiction: PCT = (W + T/2)/games, NET PTS = PF − PA, HOME + ROAD = overall record, league wins
  = league losses. All 32 rows pass today.
- **Blanks are structurally blank.** A blank game-status cell is emitted as a blank `<td>`, never as
  "available", and a test fails if a blank is ever read as participation.
- **No invented prices.** Every market, ROI, CLV and closing-line cell in the repository is blank, and
  `nfl.com/odds/` is registered as a checked-and-absent path rather than a source.
- **The freeze is honest.** Snapshots carry a capture date, a saved retrieval and a hash receipt.
- **The site builds deterministically.** A rebuild is byte-identical, and the checker fails on an
  unmanaged page, a broken fragment or a row with no registered source.

---

## E. Disposition summary

| ID | Class | Blocks publication? | Blocks a priced/rewarded decision? |
|---|---|---|---|
| A-RR13 | Stale claim | No | Yes |
| A-RR14 | Stale value | No | Yes |
| A-RR15 | Wrong count | No | No |
| A-RR16 | Misleading badge | No | No |
| A-RR17 | Wrong count | No | No |
| A-RR18 | Wrong metadata | No | No |
| A-RR19 | Duplicate registers | No | Yes, until one is chosen |
| A-RR20 | Unsupported inference | No | Yes |
| A-RR21 | Under-specified baseline | No | Yes |
| A-RR22 | Temporal claim | No | Yes |
| B-RR23 | Missing capability | No | Yes |
| B-RR24 | Missing capability | No | Yes |
| B-RR25 | Missing capability | No | Yes |
| C-RR26 | Structure | No | No |
| C-RR27 | Process record | No | No |

None of these stops an honest research page from being published. Every one of them stops a priced
line, a skill claim or a reward from being made.
