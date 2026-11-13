# NFL line-by-line verification record — session arena/edcc0589-own7 (2026-11-13)

## Scope

Every NFL observation in this repo was re-checked against its official NFL.com source on 2026-11-13 (UTC date; user-local timezone America/New_York, UTC). No value was inferred or filled in. Where today's official rendering differs from a committed snapshot, the difference is documented below as expected snapshot aging — the snapshots are frozen transcriptions from 2026-11-12, not a live feed.

Official sources consulted (all nfl.com / support.nfl.com):

| Source ID | URL | Checked | Role |
|---|---|---|---|
| NFL-STANDINGS | https://www.nfl.com/standings/ | 2026-11-13 | 32 club standings rows |
| NFL-PASSING | https://www.nfl.com/stats/player-stats/ | 2026-11-13 | Top-25 passing player rows |
| NFL-TEAM-DEF | https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all | 2026-11-13 | 32 team defense passing rows |
| NFL-TEAM-OFF | https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all | 2026-11-13 | 32 team offense passing rows (positional C1-C15) |
| NFL-SCHED-W10 | https://www.nfl.com/schedules/ | 2026-11-13 | Week 10 fixtures |
| NFL-INJ-W10 | https://www.nfl.com/injuries/ | 2026-11-13 | Week 10 injury report structure |
| NFL-TERMS-LEGAL | https://www.nfl.com/legal/terms/ | 2026-11-13 | NFL.com Terms and Conditions |
| NFL-TERMS | https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions | 2026-11-13 | Same terms, support mirror |

## Result summary

- All local automated checks pass: 96 unit tests, `scripts/check_site.py` (115 HTML pages, 2,728 table body rows, 0 errors), `nfl/build.py --check` (16 pages), `nfl/test_build.py -v` (6 tests), `nfl/origination/originate.py --check` (14 pages), `nfl/verify_independent.py` (independent re-derivation), market-evidence, rental, and nfl-assurance checks.
- Browser/accessibility suite was running at the time of this record (see COORDINATION.md).

## Dataset-by-dataset verification

### Standings — data/nfl-standings-2026.csv (frozen snapshot, checked 2026-11-12)

30 of 32 committed rows match today's official rendering exactly. The two exceptions are fully explained by the New York Giants at Washington Commanders game of Thursday, November 12, 2026, which the official schedule page shows as FINAL, Commanders 24, Giants 21 (https://www.nfl.com/games/commanders-at-giants-2026-reg-10):

| Team | Committed (snapshot 2026-11-12) | Official today (2026-11-13) | Delta | Explanation |
|---|---|---|---|---|
| Washington Commanders | 2-5-1, PF 172, PA 202 | 3-5-1, PF 196, PA 223 | +1 W, +24 PF, +21 PA | Won 24-21 vs NYG on Nov 12 |
| New York Giants | 5-2-1, PF 182, PA 172 | 5-3-1, PF 203, PA 196 | +1 L, +21 PF, +24 PA | Lost 21-24 vs WAS on Nov 12 |

The delta is exactly one game whose result matches the official final score (WAS +24 PF / +21 PA over its snapshot; NYG +21 PF / +24 PA). All arithmetic in the committed snapshot re-derives correctly (PCT = (W + T/2) / games within display rounding, NetPts = PF − PA, league wins = league losses = 135, PF = PA = 6,246). Minnesota allows fewest pass yards (1,495) in both the committed table and today's official defense table.

**Irregularity flagged:** committed standings values cannot be re-confirmed against today's live page for WAS and NYG because the page has advanced past the snapshot date. The snapshots remain single-source, dated transcriptions; no values were altered.

### Team defense passing — data/nfl-team-defense-passing-2026.csv

30 of 32 committed rows match today's official rendering exactly; WAS and NYG differ for the same Nov 12 game reason above. Minimum pass yards allowed: Minnesota 1,495 (matches executive-summary finding E5). All 32 teams present; source-linked per row.

### Team offense passing — data/nfl-team-offense-passing-2026.csv

30 of 32 committed rows match today's official rendering exactly; WAS and NYG differ for the same Nov 12 game reason. Header row was not rendered on the official page, so columns are retained positionally (C1-C15: Att, Cmp, Cmp%, Yds/Att, Yds, TD, INT, Rate, First, FirstPct, Plus20, Plus40, Lng, Sck, SckY) and meanings are not asserted (flag NF11). No offense-header-based named comparisons are made anywhere in the site.

### Player passing — data/nfl-players-passing-2026.csv (top 25)

Ranks 1-24 match today's official rendering exactly, including Jordan Love leading at 2,618 yards. Rank 25 (Michael Penix Jr., 1,444 yards) appears at rank 25 in the committed snapshot but is not among the visible rows on today's rendering (last visible row: Sam Darnold, 1,478). Snapshot retained as dated transcription; not re-confirmed on today's page.

### NF12 — publisher-side Yds/Att disagreement, CONFIRMED live

Re-fetched the official passing table on 2026-11-13; it still prints:
- Patrick Mahomes: 2,037 yards / 263 attempts, printed 7.8 Yds/Att (own inputs give 7.7452 → 7.7)
- Deshaun Watson: 1,806 yards / 249 attempts, printed 7.2 Yds/Att (own inputs give 7.2530 → 7.3)

Neither printed rate is reachable by rounding from its own row's yards and attempts. Confirmed on both https://www.nfl.com/stats/player-stats/ and https://support.nfl.com mirror. This is a publisher-side disagreement between columns, not a transcription error. The Yds/Att vs Rate correlation is reported on the column as printed (0.829085; exact yards/attempt variant 0.831578, delta 0.0025). No strategy or conclusion depends on this coefficient.

### Schedule — data/nfl-schedule-2026-w10.csv

14 Week 10 fixtures, all with official `-2026-reg-10` game slugs. Today's official schedules page lists the same fixtures: Commanders@Giants (Thu Nov 12, final), Patriots@Lions, Chiefs@Falcons, Texans@Browns, Vikings@Packers, Dolphins@Colts, Panthers@Saints, Bills@Jets, Jaguars@Titans, Rams@Cardinals, Seahawks@Raiders, 49ers@Cowboys, Steelers@Bengals, Chargers@Ravens (Mon Nov 16). The four bye teams are CHI, DEN, PHI, TB (absent from the slate). All 14 fixture links resolve to official nfl.com game pages.

### Injuries — data/nfl-injuries-2026-w10.csv

20 rows from the Week 10 TNF listing (Commanders @ Giants, Thursday Nov 12) match today's official injury report rendering exactly (names, positions, injuries, practice statuses, game statuses). The older data/nfl-injuries-week7-2026.csv (45 rows, NE/CHI/PIT/NO, Week 7) is a bounded historical snapshot.

**Blank replacements/deficiencies:** The official injury report does not state replacement players (2nd/3rd/4th string) or quantify deficiencies, for either offense or defense. These cells are intentionally blank and are never inferred (flag NF10). Tracking design is documented on the Injuries & backups page.

### NFL Terms and Conditions — VERIFIED verbatim

All three rights provisions cited by the project were confirmed on the official terms page (https://www.nfl.com/legal/terms/ and support.nfl.com mirror, updated May 16, 2024):

- **§1.3 Permitted Uses:** "You may use the Services solely for your own individual non-commercial and informational purposes only... Systematic retrieval of data or other content from the Services, whether to create or compile, directly or indirectly, a collection, compilation, database, or directory, is prohibited absent our express prior written consent."
- **§11(f) Prohibited Uses:** "...use or attempt to use any engine, software, tool, agent or other device or mechanism (including, browsers, spiders, robots, avatars or intelligent agents) to navigate or search the Services to harvest or otherwise collect information from the Services to be used for any commercial purpose."
- **§12 User Content and Communications:** "Any gaming features that we make available on the Services, including fantasy football features, are provided exclusively for entertainment purposes. In addition, you are prohibited from gambling or wagering on the result of any gaming features provided on or through the Services, or from using the Services to gamble or wager on the result of any NFL game."

No separate written permission is evidenced. NFL-derived betting prices, bulk collection, cash wagering, and payments remain disabled (source_rights flags false in research/nfl-results.json). This is a frozen, attributed statistical audit only — not legal advice.

## Correlations (derived, descriptive, not predictive)

Seven cross-sectional correlations recomputed independently and reproduced to 1e-6 by nfl/verify_independent.py (shares no code with the build pipeline):

| Pair | n | Pearson r | Spearman | Kind | Status |
|---|---|---|---|---|---|
| W vs NetPts (standings) | 32 | 0.8462609 | 0.84354644 | Team cross-sectional | Derived · descriptive |
| PF vs PA (standings) | 32 | -0.08156453 | -0.19414894 | Team cross-sectional | Derived · descriptive |
| PCT vs NetPts (standings) | 32 | 0.86902587 | 0.85753803 | Team cross-sectional | Derived · descriptive |
| Off Yds vs Def Yds Allowed | — | — | — | Not collected | Blank (NF11) |
| Off Rate vs Def Rate Allowed | — | — | — | Not collected | Blank (NF11) |
| Off TD vs Def TD Allowed | — | — | — | Not collected | Blank (NF11) |
| Pass Yds vs TD (QBs) | 25 | 0.83922578 | 0.83762032 | Player cross-sectional | Derived · descriptive |
| Pass Yds vs INT (QBs) | 25 | -0.08889027 | -0.06399418 | Player cross-sectional | Derived · descriptive |
| Yds/Att vs Rate (QBs) | 25 | 0.82908532 | 0.87076297 | Player cross-sectional | Derived · descriptive (on printed column) |
| Cmp% vs Rate (QBs) | 25 | 0.76138609 | 0.72335519 | Player cross-sectional | Derived · descriptive |
| Teammate leg A / leg B | — | — | — | Not collected | Blank |
| Cross-game leg A / leg B | — | — | — | Not collected | Blank |
| Three-or-more-leg joint distribution | — | — | — | Not collected | Blank |

Bet-leg and joint-event correlations are blank — no game logs were collected (suggestion SU-01).

## Strategies, gates, leaderboard

All eight strategies (NS01-NS08: singles, parlays, player-prop combos) remain **Blocked** on validation gates NG01-NG10; zero passed; leaderboard empty; cash rewards null; ROI/CLV/market lines null. No executable NFL line, edge, ROI, CLV, cash prize, or winning strategy is claimed. Rewards are non-monetary merit points only.

## Irregularities and flags (published on Flagged for Review)

NF01-NF12 remain as registered in research/nfl-catalog.json (flags). None block publishing; all block unsupported price/skill/cash release. New observation this session: NF07-like snapshot-aging note for WAS/NYG standings rows (values advanced one game past the snapshot date; delta matches official final score).

## Verification method

Each committed row was compared cell-by-cell to the rendered official table; arithmetic re-derived (PCT, NetPts, passer rating, Yds/Att, correlations). Sources are linked per table row on the site. Snapshots were retrieved via rendered-page text, not raw HTTP archives; automated link health is not factual verification (flag NF07).

## Links for manual review

- Standings: https://www.nfl.com/standings/
- Player passing: https://www.nfl.com/stats/player-stats/
- Team defense: https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all
- Team offense: https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all
- Week 10 schedule: https://www.nfl.com/schedules/
- Week 10 injuries: https://www.nfl.com/injuries/
- Commanders@Giants box (final 24-21): https://www.nfl.com/games/commanders-at-giants-2026-reg-10
- NFL Terms: https://www.nfl.com/legal/terms/ ; https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions
