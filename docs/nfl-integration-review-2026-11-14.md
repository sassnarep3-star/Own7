# NFL integration review — 2026-11-14

**Purpose:** fresh release/integrity check of the NFL research site and a bounded re-read of current official NFL pages. This is not a live-data update, a licensed feed, a profitability claim, or a complete re-verification of every historical NFL source.

## Executive decision

- Keep the NFL pages online as an **auditable, frozen research desk**. Do **not** release a live betting line, assert a skill edge, rank a strategy as qualified, award cash, or treat a blank injury status as availability.
- The existing site already has the requested landing page, executive summary, sourced category pages, decision questions, suggestions register, validation gates, correlation discussion, injury/depth material, leaderboard, and **Flagged for Review** page. The fresh source recheck is added to the existing flags rather than being mistaken for newly collected game data.
- Two official pages were freshly re-read on 2026-11-14. The 2026 standings’ 32 team names and W/L/T/PF/PA cells were compared with the dated local snapshot. **30 rows match; WAS and NYG are the only differences**, explained by the 24–21 final already recorded in the dated evidence. The snapshot was not overwritten.
- The NFL injury page’s opening rendered chunk now shows the Week 10 heading, the Thursday Nov 12 WAS–NYG section, and Sunday Nov 15 sections. The older origination table has 20 Thursday-only rows. The separate availability desk has a 326-row Week 10 snapshot for 28 clubs captured on Nov 13; its remaining rows were **not** re-audited on Nov 14, so this report does not call it current or complete as of Nov 14.
- NFL.com Terms §1.3 says systematic retrieval for a collection is prohibited absent express prior written consent. No separate permission is evidenced. Therefore this review makes no new bulk collection, and the repository must not be treated as an automated injury/odds feed.

## Official pages opened on 2026-11-14

| Check | Observed scope and result | Official source |
|---|---|---|
| Standings | Both rendered chunks read. Manually compared all 32 club names and W/L/T/PF/PA fields against `data/nfl-standings-2026.csv`: exact team-name coverage; 30 rows match; only Washington and the Giants differ. No CSV values changed. | [NFL 2026 standings](https://www.nfl.com/standings/) |
| Injury report | One of eight rendered chunks read. It identifies the page as the 2026 Week 10 report and shows Thursday Nov 12 WAS–NYG and Sunday Nov 15 sections, including NE–DET. This confirms the 20-row origination table is bounded to Thursday, not the entire current report. The rest of the live report was not read. | [NFL injury report](https://www.nfl.com/injuries/) |
| Terms | The official terms page was opened; its page states “Updated: May 16, 2024” and §1.3 limits use to individual non-commercial informational purposes and prohibits systematic retrieval to compile a collection without express prior written consent. | [NFL.com Terms and Conditions](https://www.nfl.com/legal/terms/) |

Access method: Arena `fetch_page` rendered page text; these are not raw HTTP archives or independent source copies. The injury report was only partially read. The terms check was limited to the opening rendered chunk and §1.3; prior repository verification dated Nov 13 records the other provisions. No inference was made from any field not displayed.

## Freshness findings now on the site

Both items are on the [NFL Flagged for Review page](../nfl-review.html), with official links attached to the table rows:

| Existing flag | Freshly verified point | Disposition | Source |
|---|---|---|---|
| NF14 — two clubs moved after the snapshot | Re-read and compared all 32 official standings club rows on Nov 14. The frozen Nov 12 snapshot still differs only for WAS and NYG; the difference is the already recorded Thursday result. | Keep the snapshot dated; do not replace historical rows with current standings. | [NFL standings](https://www.nfl.com/standings/) |
| NF09 — bounded injury coverage | Live page opening chunk shows additional Week 10 Sunday sections. The repo’s 20-row origination table is Thursday-only; a separate 326-row/28-club Week 10 snapshot was captured Nov 13 but was not re-audited today. | Preserve the older snapshot and explicitly avoid saying that it is a current full-week feed. | [NFL injury report](https://www.nfl.com/injuries/) |

The other datasets (passing/rushing/receiving and team statistics, older injury snapshots, schedule, club depth charts, and their historical evidence) were **not re-fetched as part of this Nov 14 source check**. Their existing dated verification records remain the relevant evidence; this review does not silently extend their verified-through dates.

## Release checks performed

All checks were run on the current integration branch after regenerating affected deterministic outputs:

| Check | Result |
|---|---|
| `python -m unittest discover -s tests -v` | 109 tests passed |
| NFL extraction + origination reproducibility | `scripts/nfl_extract.py --check`, `python -m nfl_origination run --check`, independent NFL verification and origination build all passed; 7/7 published correlations reproduced, two publisher-side Yds/Att disagreements remain reported |
| `python scripts/check_site.py` | Passed: 38 canonical pages, 20 compatibility redirects, 68 auxiliary pages, 126 recursive HTML pages, 5,197 table body rows, 138 registered sources, 0 errors |
| Browser/accessibility | `node --check js/app.js` and `npm run test:browser` passed: 106 desktop + 106 mobile pages; WCAG A/AA; no runtime errors |
| Other maintained workstreams | NBA, market-evidence, rental, NFL assurance, NFL availability/depletion builders and tests passed; exact command results are recorded in `COORDINATION.md` |
| Deterministic outputs | Rebuilt NBA/NFL research outputs and site after the source registry and review flags changed; recursive audit passed afterward |

These checks establish internal consistency, provenance contracts, empty/unknown-cell behavior, deterministic output and local routing. They do **not** establish external truth for data that was not re-fetched, source-use rights, model skill, or profitability.

## Known decision blockers (remain open)

1. **Prices/market terms:** there is no rights-cleared executable odds feed, no verified market close, and no ROI/CLV evidence. Market price fields remain blank.
2. **Skill versus variance:** no untouched prospective sample establishes positive out-of-sample performance. Historical small-sample correlations are descriptive, not proof that luck has been removed.
3. **Parlays/prop combos:** the computed team-level correlations are not leg-level dependence. Joint player/game outcome history and settlement rules are missing; do not price or rank these combinations.
4. **Injuries and replacements:** injury status, practice participation, an official depth chart, actual game-day role, and snap/target/carry share are distinct facts. The repo does not infer a replacement or assign a points impact when sources do not say so. Houston’s missing chart, unofficial club charts, multiple-name slots, and incomplete official game-status fields remain flagged in the availability desk.
5. **Data permissions:** NFL terms restrict systematic collection absent written consent. A production decision needs documented rights review and permission before any recurring capture or commercial/betting use.

No strategy currently passes all applicable validation gates. The leaderboard remains empty; any planned recognition remains non-transferable merit only, not a cash award.

## Manual review links

- [NFL dashboard](../index.html)
- [Executive summary](../nfl-executive-summary.html)
- [Suggestions and review workflow](../nfl-suggestions.html)
- [Decision questions and missing information](../nfl-questions.html)
- [Lines, methods and validation gates](../nfl-lines.html) · [correlations](../nfl-correlation.html) · [injuries and backups](../nfl-injuries.html) · [leaderboard](../nfl-leaderboard.html)
- [Flagged for Review](../nfl-review.html)
