# Repository review — NFL conversion, 2026-11-12

Session: `session-arena-a129b881-own7` · Branch `arena/a129b881-own7` · Base commit `a989d67`

This is a scoped review, not a blanket re-verification of every historical sentence in the
repository. It records what was checked, how, what was found, and what remains open. Every
finding below is reproducible from the commands listed at the end.

## 1. Baseline state before this session's work

| Check | Result |
|---|---|
| Commits on `main` before this session | `a989d67` merge of PR #20 |
| Tracked files | 150 |
| Python tests | 62 passed |
| `scripts/check_site.py` | passed: 25 canonical pages, 20 redirects, 54 HTML files, 738 sourced table rows, 65 registered sources |
| Deterministic rebuild | byte-identical |
| Open pull requests | #17 (a dated, unrelated NBA claims record) |

The repository was internally consistent before any change here. Nothing in this review claims
that earlier factual content was wrong; only that its own stated limits still apply.

## 2. What was verified in this session

| Item | Scope verified | Source | Result |
|---|---|---|---|
| NFL division standings | All 32 club rows, 16 value cells each | https://www.nfl.com/standings/ | 32/32 parsed; PCT, NET PTS, HOME+ROAD and league W/L all reconcile |
| NFL Week 10 injury listing | Complete Thursday game section, 20 players | https://www.nfl.com/injuries/ | 20/20 parsed; practice and game statuses all inside the official categories |
| NFL Week 10 fixtures | 14 fixtures, 4 byes | https://www.nfl.com/schedules/ | 28 clubs in fixtures plus 4 byes equals exactly 32 |
| Injury-report category definitions | Practice and game-status definitions | https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693 | Read in full; quoted on the availability page |
| NFL.com terms | Section 1.3 permitted uses | https://www.nfl.com/legal/terms/ | Read; restriction on systematic retrieval recorded |
| Pythagorean method | Formula form and the NFL exponent 2.37 | https://en.wikipedia.org/wiki/Pythagorean_expectation and https://www.pro-football-reference.com/about/glossary.htm | Method only; no observation taken from either page |

## 3. Irregularities found and how they were handled

| # | Irregularity | Disposition |
|---|---|---|
| RR01 | The NFL standings page rendered **no text header row**, and the displayed field order does not match the order given in the page legend. | Division record and conference record are named in the legend, but the displayed field order does not follow it and four middle fields are unidentified. **Six of sixteen displayed fields were therefore not transcribed**, and the reason is published. |
| RR02 | The NFL injury listing leaves **"Game Status" blank for 17 of 20** listed players while still showing practice participation. | Blanks are preserved. A test fails if a blank is ever converted into an implication of availability. |
| RR03 | `https://www.nfl.com/depth-charts/` returned a **404** page to the reader. | No depth chart was used. The starter/backup requirement is documented as unmeasured rather than approximated. |
| RR04 | Score pages rendered some completed games as **"Hidden Score"**. | No game results were transcribed, so **no backtest is offered**. Guessing scores would have fabricated the entire history. |
| RR05 | The deep link `/schedules/2026/REG11/` was served from `/schedules` and the page self-identified as **WEEK 10**. | The canonical URL is cited and the served week is recorded. Fixtures were validated against the official `-2026-reg-10` game slugs. |
| RR06 | `https://www.nfl.com/stats/2026/regular` returned a **404**. | Team-level rates were derived from standings PF/PA instead; no page statistics were invented. |
| RR07 | `parse_pythagorean`-style formatting bug: the Washington PCT (.313) is not the exact `(W + T/2)/games` value because the league displays it **rounded to three places**. | The check uses an explicit 0.00051 rounding tolerance rather than requiring exact equality, and the tolerance is stated in the extractor. |
| RR08 | Ten team-level correlations were initially produced, but **five share inputs by construction** (net points with PF/PA and wins; the residual with wins). | Each is labelled "not independent evidence" with its reason. They are displayed, not deleted, and a test asserts exactly five are independent. |
| RR09 | A first draft counted a `not applicable` gate as a pass for single bets. | Corrected: N/A leaves the denominator and is never counted as a pass. A test now asserts `passed == count(pass)` and `applicable == count(not n/a)`. |
| RR10 | Small `.source-line` links failed the WCAG 2.2 target-size check (11px tall). | Fixed with a CSS rule; the full browser suite then passed with zero violations. |
| RR11 | Root `index.html` was replaced by the NFL landing page, so NBA-era "Overview" links still resolve to the root. | The NBA overview is preserved at `nba-overview.html` and linked as "NBA overview" in its own navigation group. The logo returns to the site home by design. |
| RR12 | The repository's snapshot stamp read "03 Nov 2026" while the NFL data is dated 2026-11-12. | The stamp was updated and the per-row check date is carried in every dataset. |

## 4. Cross-check performed on the inherited content

- The NBA and rental sections were not edited and their source IDs were not modified.
- Adding seven source IDs changed the hash of `research/sources.json`, which is an input to the
  NBA run hash. `python -m nba_lab run` was re-run so `research/results.json` matches; no NBA
  value changed and 86 tests pass.
- `scripts/check_site.py` was extended with the new hosts, keeping its "registry IDs must equal
  the host map" invariant intact.

## 5. What this review does not establish

- Factual truth of any inherited NBA or rental claim: out of scope and unchanged.
- That the NFL pages are correct beyond one official page per value: every NFL number here is
  **single-source**, and this is flagged on the review page.
- That the derived model has predictive value: one partial season, no market comparison.
- That the site's use of NFL material is permitted beyond individual non-commercial reading.

## 6. Reproduce this review

```sh
python scripts/nfl_extract.py --check      # re-parse saved official text, refuse contradictions
python -m nfl_lab run --check              # reproduce derived results exactly
python -m unittest discover -s tests       # 86 tests
python scripts/check_site.py               # links, fragments, per-row sources, determinism
npm run test:browser                       # 46 desktop + 46 mobile pages, WCAG A/AA
```

## 7. Review links for manual inspection

- Standings: https://www.nfl.com/standings/
- Injury report: https://www.nfl.com/injuries/
- Schedule: https://www.nfl.com/schedules/
- Injury-report policy: https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693
- Site terms §1.3: https://www.nfl.com/legal/terms/
- Pythagorean method: https://en.wikipedia.org/wiki/Pythagorean_expectation
- Publisher glossary (Expected W-L): https://www.pro-football-reference.com/about/glossary.htm
