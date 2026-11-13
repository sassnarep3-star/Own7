# Availability and depletion desk — executive summary

Session `arena/28efbbd0-own7`. Read on 2026-11-13. Published at
`nfl-availability-28ef/site/index.html`.

## The question this desk answers

When the league lists a player Out, Doubtful or Questionable, what does the club's own printed
depth chart say about who is behind him? That is the entire scope. It is answered per player, with
the printed chain, the next name in line, and the official link for both sides of the join.

It deliberately does **not** produce a point value, a win probability, a price, a stake or a bet
recommendation. No performance deficit is estimated, because no official source publishes one and
inventing one would be fabrication.

## Five findings

1. The official Week 10 injury report lists **326 players** across **28 clubs** (14 games).
   Only **25 rows carry a game status** — 14 Out, 11 Questionable. The remaining 301 rows are
   blank on the page itself.
2. **Ten printed starters** carry a game status: **7 ruled out**, **3 questionable**. Of the seven
   ruled out, four are defenders, two are offensive players and one is a long snapper.
3. In **six of seven** cases the club's printed chart names a second string as the next man in.
   In one case — the Colts long snapper Luke Rhodes — the chart prints **no further name at all**.
4. One chain is already **two deep**: New England's printed starting running back is questionable
   and the printed second string is out, which leaves the third string as the next available name.
5. **Twenty-seven of the 28 clubs** on the report have a printed chart. Houston's page returned no
   table, so its 16 injury rows have no rank and no replacement — they are published blank.

## Four gaps that block a decision

1. **A game status is published for 5 clubs only** (DET, IND, NE, NYG, WAS). No depletion count can
   be league-wide until the other clubs publish one.
2. **Club charts are labelled unofficial by their own publishers** (KC, DAL, LAR, MIN, NO, NYJ,
   TEN). They are printed opinions, not confirmed game-day personnel.
3. **No market price exists anywhere in the record**, so no depletion finding can be turned into an
   edge, a stake or a reward.
4. **No results and no inactives.** The only list that decides who plays is the official inactives
   list issued shortly before kickoff; it has not been read.

## The players with a published status who appear on their club's chart

| Club | Player | Position | Status | Printed rank | Next name printed in line |
|---|---|---|---|---|---|
| DET | Cade Mays | C | Out | 1st string | Juice Scruggs |
| DET | D.J. Reed | CB | Out | 1st string | Rock Ya-Sin |
| IND | Akeem Davis-Gaither | LB | Out | 1st string | CJ Allen |
| IND | Jaylon Carlies | LB | Out | 1st string | Bryce Boettcher |
| IND | Jalen Travis | T | Out | 1st string | Luke Tenuta |
| IND | Luke Rhodes | LS | Out | 1st string | **no further name printed** |
| IND | Jerry Tillery | DT | Out | 2nd string | Tim Smith |
| IND | Mo Alie-Cox | TE | Out | 2nd string | Drew Ogletree |
| NE | A.J. Brown | WR | Questionable | 1st string | Efton Chism III |
| NE | Kevin Byard | S | Questionable | 1st string | Jaylen Reed |
| NE | Rhamondre Stevenson | RB | Questionable | 1st string | Corey Kiner (2nd string is also Out) |
| NE | Carlton Davis III | CB | Out | 1st string | Channing Canada |
| NE | TreVeyon Henderson | RB | Out | 2nd string | Corey Kiner |
| NE | Ben Brown | C | Out | 2nd string | **no further name printed** |
| NE | Brenden Schooler | S | Questionable | 3rd string | **no further name printed** |
| NE | Cameron Latu | TE | Questionable | 3rd string | **no further name printed** |
| NE | Charles Woods | CB | Questionable | 2nd string | **no further name printed** |
| NE | Walter Rouse | T | Questionable | 2nd string | **no further name printed** |
| WAS | Colson Yankoff | TE | Out | 2nd string | **no further name printed** |

Six further players carry a game status but are **not named on their club's printed chart**:
Lucas Patrick (WAS, Out), Malik Harrison (NYG, Questionable), Reggie Gilliam (NE, Questionable),
Greg Van Roten (NE, Questionable), Kerby Joseph (DET, Out), Arden Key (IND, Questionable). Their
rank and replacement are blank; the sources read do not say why.

## What is flagged for review

Ten items are published on `flagged.html` with an official link each. The four that constrain any
use of the numbers: game status published for 5 of 28 clubs (XF01); Houston's chart not rendered
(XF02); two read dates in one table — 17 charts read 2026-11-13, 10 reused from a 2026-11-12 read
already in this repository (XF03); and publishers calling their own charts unofficial (XF04).

## What was read

| Source | Scope actually read | Read on |
|---|---|---|
| `https://www.nfl.com/injuries/league/2026/REG10` | All 14 Week 10 games, 326 player rows, practice and game status, 8 rendered chunks saved verbatim | 2026-11-13 |
| 17 club depth-chart pages | The printed depth table as rendered | 2026-11-13 |
| 10 club depth-chart pages | Printed depth table already transcribed in `nfl-assurance-9580ac3f/data/depth.csv`, reused as an 11-12 snapshot | 2026-11-12 |
| `https://www.houstontexans.com/team/depth-chart` | Page returned a heading and no table — nothing obtained | 2026-11-13 |

## Boundary

Each page was read through the Arena page reader, which returns rendered text. That is not an
HTTP-status attestation, not an archive and not a licence. NFL.com's terms restrict systematic
retrieval and prohibit use of the services to wager, so nothing here is automated against the
league site and no dataset is redistributed.

## Reproduce

```
python3 nfl-availability-28ef/collect.py          # transcription of the saved injury report
python3 nfl-availability-28ef/depth.py            # printed depth chains
python3 nfl-availability-28ef/depletion.py        # the join
python3 nfl-availability-28ef/build.py            # the 10 pages
python3 nfl-availability-28ef/collect.py --check  # and each of the above with --check
python3 scripts/build_site.py && python3 scripts/check_site.py
```
