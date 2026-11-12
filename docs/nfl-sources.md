# NFL official sources · checked 2026-11-12

All NFL values in this lab come from the official NFL sources below. Each was read via Arena fetch_page on 2026-11-12. No values were inferred; anything not confirmed on the official page is left blank and flagged.

| ID | Official source | What was checked | Scope / limits |
|---|---|---|---|
| NFL-STANDINGS | [Standings · 2026](https://www.nfl.com/standings/) | 32 division rows: W, L, T, PCT, PF, PA, Net Pts, Home, Road, Div, Conf, Strk, Last 5 | Frozen snapshot; early-season context, not a live signal. |
| NFL-PASSING | [Player passing · 2026](https://www.nfl.com/stats/player-stats/) | Top 25 by passing yards: Yds, Yds/Att, Att, Cmp, Cmp %, TD, INT, Rate, 1st, 1st%, 20+, 40+, Lng, Sck, SckY | Passing-selected subset, not a complete player universe. |
| NFL-RUSHING | [Player rushing · 2026](https://www.nfl.com/stats/player-stats/category/rushing/2026/reg/all/rushingyards/desc) | Top 25 by rushing yards | Rushing-selected subset. |
| NFL-RECEIVING | [Player receiving · 2026](https://www.nfl.com/stats/player-stats/category/receiving/2026/reg/all/receivingreceptions/desc) | Top 25 by receptions | Receiving-selected subset. |
| NFL-TEAM-OFF | [Team offense passing · 2026](https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all) | 32 team rows: Att, Cmp, Cmp %, Yds/Att, Yds, TD, INT, Rate, 1st, 1st%, 20+, 40+, Lng, Sck, SckY | Passing offense only; rushing/scoring not transcribed. |
| NFL-TEAM-DEF | [Team defense passing · 2026](https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all) | 32 team rows: Att, Cmp, Cmp %, Yds/Att, Yds, TD, INT, Rate, 1st, 1st%, 20+, 40+, Lng, Sck | Passing defense only. |
| NFL-INJURY | [Injury report Week 7 · 2026](https://www.nfl.com/injuries/league/2026/reg7) | Bounded: Thu Oct 22 NE+CHI, Sun Oct 25 PIT+NO (45 rows): Player, Position, Injuries, Practice Status, Game Status | Remaining Week 7 teams not collected. Replacements/deficiency not stated on page — blank. |
| NFL-SCHEDULE | [Schedule · 2026](https://www.nfl.com/schedules/2026/REG7/) | Page existence observed; no rows transcribed | Rest/travel features blank until bounded transcription. |
| NFL-TERMS | [NFL.com Terms and Conditions](https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions) | §1.3 non-commercial/informational only; §11(f) harvesting ban; §12 gambling/wagering prohibition | No separate permission evidenced. NFL-derived betting prices, bulk collection, wagering disabled. |
| NFL-ROSTER | [Teams / rosters](https://www.nfl.com/teams/) | Roster pages exist per team | No rows transcribed; backup depth blank until bounded transcription. |

## Rights gate (confirmed)

- §1.3: "You may use the Services solely for your own individual non-commercial and informational purposes only. Any other use, including for any commercial purposes, is strictly prohibited without our express prior written consent. Systematic retrieval of data or other content from the Services ... is prohibited absent our express prior written consent."
- §11(f): prohibited to use spiders/robots to harvest/collect information for any commercial purpose.
- §12: "you are prohibited from gambling or wagering on the result of any gaming features provided on or through the Services, or from using the Services to gamble or wager on the result of any NFL game."

This lab is therefore a frozen, attributed statistical audit and non-commercial methods demonstration only. No executable NFL line, odds, ROI, CLV, cash prize or wagering signal is released. This is not legal advice.
