# NFL decision desk — source ledger

Every figure published under `nfl-desk/` traces to one of the seventeen entries below. The machine
copy of this table is [`nfl-desk/data/sources.json`](../../nfl-desk/data/sources.json), which the
build and `scripts/check_site.py` both read; the two are kept in step by
`nfl-desk/test_build.py` and a host check that rejects any URL outside its declared publisher.

Read date for every row: **12 November 2026**. Nothing here was inferred, averaged, or carried over
from a prior session. Where a page could not supply a value, the value is blank on the site and
listed as a flag on `nfl-desk/review.html`.

## The ledger

| ID | Publisher | URL | Access | What was actually read | Read on |
|---|---|---|---|---|---|
| `NFL-STANDINGS-2026` | NFL.com (National Football League) | <https://www.nfl.com/standings/league/2026/reg> | public, no login | Both result chunks read. All 32 club rows transcribed for W, L, T, PCT, PF, PA, NET PTS. Division/conference, home/road, streak and clinch columns were not transcribed because the rendered table has no header row in the capture (flag DF-04). | 2026-11-12 |
| `NFL-STANDINGS-DIV-2026` | NFL.com (National Football League) | <https://www.nfl.com/standings/division/2026/REG> | public, no login | Both chunks read. Confirms each club's division grouping (AFC East/North/South/West, NFC East/North/South/West) and that the same seven numeric fields repeat identically. Used only for division assignment, cross-checked against the league table. | 2026-11-12 |
| `NFL-TEAM-PASS-2026` | NFL.com (National Football League) | <https://www.nfl.com/stats/team-stats/offense/points/2026/reg/all> | public, no login | Full 32-row table read. The captured table is unlabeled. Only ATT, CMP, PCT, AVG, YDS were transcribed, and only after the build verified round(CMP/ATT*100,1)==PCT and round(YDS/ATT,1)==AVG on every row. TD/INT/longest and five further columns were not identified and are not filled (flag DF-03). | 2026-11-12 |
| `NFL-INJURY-W10-2026` | NFL.com (National Football League) | <https://www.nfl.com/injuries/> | public, no login | All seven result chunks read. 278 player rows across 26 clubs transcribed with the four rendered fields (Position, Injuries, Practice Status, Game Status); two clubs rendered 'No Injuries Reported'. Four clubs were on bye and are absent. This is one page state, not a live feed. | 2026-11-12 |
| `NFL-SCHEDULE-2026` | NFL.com (National Football League) | <https://www.nfl.com/schedules/2026/REG/> | public, no login | All three chunks read. Confirmed the Week 10 fixture list used for the availability table (14 games), kickoff times, and the four clubs on bye (CHI, DEN, PHI, TB). Start times are the site's displayed local-to-user times and are not re-expressed. | 2026-11-12 |
| `NFL-TIEBREAK-2026` | NFL.com (National Football League) | <https://www.nfl.com/standings/tie-breaking-procedures> | public, no login | Read. Used only to describe why division rank cannot be computed from win-loss record alone: head-to-head, division, common-games and strength-of-victory steps precede points. This is why DF-05 leaves tie-break-dependent fields blank. | 2026-11-12 |
| `NFL-TERMS` | NFL Enterprises, LLC | <https://www.nfl.com/legal/terms/> | public, no login | Read sections 1.1–1.3, 7–11. §1.3 limits use to individual non-commercial informational purposes and prohibits systematic retrieval or compilation without prior written consent. §11(f) prohibits using the Services to harvest information for a commercial purpose. No gambling permission is granted and none is inferred here. | 2026-11-12 |
| `NFL-OPS` | NFL Football Operations | <https://operations.nfl.com/> | public, no login | Read. Confirmed the 2026 Rulebook hub and the league calendar exist. A guessed injury-report-policy URL under this host returned an empty capture, so no policy paragraph is attributed to it (flag DF-08). | 2026-11-12 |
| `NFL-NEWS-W10-ROUNDUP` | NFL.com (National Football League) | <https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11> | public, no login | Chunks 0–1 read. Used only for quarterback starter changes that are stated in the article text (WAS, ARI, CLE) and for nothing else. | 2026-11-12 |
| `NFL-NEWS-WILLIS-IR` | NFL.com (National Football League) | <https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start> | public, no login | Read. Source of the MIA quarterback replacement chain (Willis to IR; McCord to start) and of the statement that Brady Cook is on the practice squad. | 2026-11-12 |
| `NFL-NEWS-NACUA-IR` | NFL.com (National Football League) | <https://www.nfl.com/news/rams-wr-puka-nacua-likely-to-be-placed-on-injured-reserve-with-turf-toe-sprained-mcl-and-pcl> | public, no login | Read. Source of the LAR receiver-room statement (Atwell, Mumpfield, Whittington, Daniels) and of the 44.2%/48% target-share figures quoted by the article. Treats 'likely' as reported, not as a confirmed roster move. | 2026-11-12 |
| `NFL-NEWS-DARNOLD` | NFL.com (National Football League) | <https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again> | public, no login | Read. Source of the SEA quarterback replacement chain (Darnold out; Lock expected to start; Milroe backing up). | 2026-11-12 |
| `NFL-CLUB-DC-WAS` | Washington Commanders (official club site) | <https://www.commanders.com/team/depth-chart> | public, no login | Read. Offense and defense two-deep transcribed for the positions the club lists. Club depth charts are unofficial coaching estimates in general; only the listing order on this page is reported here. | 2026-11-12 |
| `NFL-CLUB-DC-NYG` | New York Giants (official club site) | <https://www.giants.com/team/depth-chart> | public, no login | Read. Offense and defense listings transcribed as displayed, including multi-player first-string cells (WR, CB). | 2026-11-12 |
| `NFL-CLUB-DC-SEA` | Seattle Seahawks (official club site) | <https://www.seahawks.com/team/depth-chart/> | public, no login | Read. Offense and defense listings transcribed as displayed, including the two-player WR1 cell and the four-deep RB cell. | 2026-11-12 |
| `SCIPY-PEARSON` | SciPy | <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html> | public, no login | Read. Reference for the Pearson coefficient and its p-value definition used in the engine's documentation. The repository's own implementation is dependency-free and is unit-tested against known values. | 2026-11-12 |
| `REPO` | This repository | <https://github.com/sassnarep3-star/Own7> | public | Project policy, build scripts and this session's coordination record. | 2026-11-12 |

## Retrieval note

Links are given for manual review; they are references, not endorsements. One behavioural fact is
worth recording because it affects reproducibility: direct command-line retrieval of `nfl.com` hosts
was refused from this environment, while the reader used for this session retrieved the same pages
normally. A reader re-running the check should therefore expect to use a browser, and should expect
the live page to have moved on from the 12 November state.

## What was deliberately **not** transcribed

| Page | Column or field | Why not |
|---|---|---|
| `nfl.com/standings/league/2026/reg` | division, conference, home/road, streak, clinch marks | the capture rendered these columns with no header row, so a column cannot be named with confidence (DF-04) |
| `nfl.com/stats/team-stats/offense/points/2026/reg/all` | TD, INT, longest, and five further columns | the captured table is unlabeled; only ATT/CMP/PCT/AVG/YDS could be identified (DF-03) |
| `nfl.com/stats/team-stats/offense/points/2026/reg/all` | AVG (yards per attempt) | published only to one decimal, and inconsistent with YDS/ATT on 4 of 32 rows; a derived `ypa` is published instead and the exclusion is stated (DF-03, SG-06) |
| `nfl.com/stats/team-stats/defense/scoring/...` | all columns | the capture was column-mangled and could not be re-aligned with confidence; no defensive figure is published anywhere |
| `nfl.com/injuries/` | per-report timestamp | the page shows the current week state only, with no per-report or per-player timestamp in it (DF-02) |
| club depth charts | 29 of 32 clubs | those clubs' charts were not read in this session, so no ordering is claimed for them (DF-06, DF-07) |

## Rights and use

`https://www.nfl.com/legal/terms/` §1.3 permits personal, non-commercial informational use and
prohibits systematic retrieval or compilation, and it prohibits gambling-related use. This desk
stores bounded, attributed, dated transcribeds of a handful of pages, cites each one by link, and
publishes **no** odds, lines, prices or wagers anywhere. That is the narrowest use compatible with
the briefs's requirement that every figure be checkable. It is still a use of another party's site,
so flag DF-14, not this paragraph, is the authority on whether it may continue, and gate G01 keeps
every candidate blocked until a written answer exists.

## Known gaps to close first

1. **No price source.** Every economic field on the site is blank (DF-01). Nothing economic can be
   computed until a licensed, timestamped archive exists.
2. **No archive.** A single page state cannot establish what was knowable before a kickoff (DF-02).
   Until reports are captured as dated snapshots, no availability signal can be tested forward.
3. **Depth coverage is 3/32.** Replacement chains exist only where a club's own chart was read
   (DF-06). The other 29 clubs are blank, and blank is the correct state.
4. **No licensed use.** Whether this data may support a betting-adjacent product is unresolved
   (DF-14). Gates G01 and G08 stay closed until it is.

See `nfl-desk/decisions.html` for the twelve questions these gaps generate, and
`nfl-desk/suggestions.html` for the twelve proposals that would close them.
