# Retained transcript — state of the Week 11 league injury report, read 2026-11-18

- **URL requested:** https://www.nfl.com/injuries/league/2026/REG11
- **Canonical URL the page reports it served:** `https://www.nfl.com/injuries/league/2026/reg10`
  (this appears in the "Skip to main content" anchor at the very top of the response)
- **Page title as served:** `Official NFL Injury Report for Players - Week 10 of the 2026 Season | NFL.com`
- **Heading as served:** `## Injuries - WEEK 10`
- **Read through:** Arena `fetch_page`, chunk index 0 of 8 (page reported `totalChunks: 8`).
  All four reads returned byte-identical content for this chunk, including the same
  canonical URL and the same title.

## Read events (this is the timestamped series)

| # | Fetch instant (sandbox UTC) | Result |
|---|---|---|
| 1 | before 2026-11-18T03:47:13Z | URL served the **Week 10** report |
| 2 | 2026-11-18T03:51:41Z (sandbox clock read in the same batch as the fetch) | URL served the **Week 10** report |
| 3 | 2026-11-18T03:51:41Z + seconds (second confirmatory read) | URL served the **Week 10** report |
| 4 | 2026-11-18T04:18:50Z (third confirmatory read, 27 minutes after read 2) | URL served the **Week 10** report |

- **Clock printed by the publisher:** none. The injury page prints a game date and a kickoff time
  per fixture (`## THURSDAY, NOVEMBER 12TH`, `8:15 PMEST`) but no capture, update or "as of" time.
  The sandbox UTC clock is therefore the only clock available, and it is recorded as the fetch
  instant. This is the same limitation every earlier desk recorded.
- **Conclusion recorded by this desk:** at 2026-11-18T04:18Z there is **no published Week 11 league
  injury report**. The Week 11 tab exists in the page's week selector (`WEEK 1 ... WEEK 10 WEEK 11`)
  but selecting it returns the Week 10 document. Nothing about Week 11 availability is inferred
  from this page.

## What the served (Week 10) document printed in the chunk that was read

The chunk contains the Thursday and Sunday-early fixtures of Week 10. Transcribed verbatim:

### THURSDAY, NOVEMBER 12TH — 8:15 PMEST — Prime Video

WAS Commanders (3-5-1)

| Player | Position | Injuries | Practice Status | Game Status |
|---|---|---|---|---|
| John Bates | TE | | Full Participation in Practice | |
| Treylon Burks | WR | | Did Not Participate In Practice | |
| Jayden Daniels | QB | | Full Participation in Practice | |
| Matt Gulbin | C | | Full Participation in Practice | |
| Chig Okonkwo | TE | | Full Participation in Practice | |
| Lucas Patrick | C | Concussion | Did Not Participate In Practice | Out |
| Amik Robertson | CB | | Limited Participation in Practice | |
| Shy Tuttle | DT | | Full Participation in Practice | |
| Colson Yankoff | TE | Knee | Did Not Participate In Practice | Out |

NYG Giants (5-3-1)

| Player | Position | Injuries | Practice Status | Game Status |
|---|---|---|---|---|
| Abdul Carter | LB | | Full Participation in Practice | |
| Jermaine Eluemunor | T | | Full Participation in Practice | |
| Malik Harrison | LB | Groin | Limited Participation in Practice | Questionable |
| Colton Hood | CB | | Full Participation in Practice | |
| Theo Johnson | TE | | Full Participation in Practice | |
| Charlie Jones | WR | | Full Participation in Practice | |
| J.J. McCarthy | QB | | Full Participation in Practice | |
| Darnell Mooney | WR | | Full Participation in Practice | |
| Malik Nabers | WR | | Full Participation in Practice | |
| Cam Skattebo | RB | | Full Participation in Practice | |
| Andrew Thomas | T | | Full Participation in Practice | |

### SUNDAY, NOVEMBER 15TH — 9:30 AMEST — FOX, FOX DEPORTES

NE Patriots (5-5)

| Player | Position | Injuries | Practice Status | Game Status |
|---|---|---|---|---|
| Ben Brown | C | Knee | Did Not Participate In Practice | Out |
| A.J. Brown | WR | Ankle, Knee | Limited Participation in Practice | Questionable |
| Kevin Byard | S | Chest | Full Participation in Practice | Questionable |
| Carlton Davis III | CB | Knee | Did Not Participate In Practice | Out |
| Reggie Gilliam | FB | Knee | Limited Participation in Practice | Questionable |
| TreVeyon Henderson | RB | Illness | Did Not Participate In Practice | Out |
| Hunter Henry | TE | | Limited Participation in Practice | |
| Cameron Latu | TE | Back | Limited Participation in Practice | Questionable |
| Drake Maye | QB | | Full Participation in Practice | |
| Morgan Moses | T | | Full Participation in Practice | |
| Walter Rouse | T | Concussion | Limited Participation in Practice | Questionable |
| Brenden Schooler | S | Hamstring | Limited Participation in Practice | Questionable |
| Rhamondre Stevenson | RB | Knee | Limited Participation in Practice | Questionable |
| Greg Van Roten | G | Hamstring | Full Participation in Practice | Questionable |
| Charles Woods | CB | Hamstring | Full Participation in Practice | Questionable |

DET Lions (7-2)

| Player | Position | Injuries | Practice Status | Game Status |
|---|---|---|---|---|
| Brian Branch | S | | Full Participation in Practice | |
| Jared Goff | QB | | Full Participation in Practice | |
| Kerby Joseph | S | Knee | Did Not Participate In Practice | Out |
| Cade Mays | C | Ankle | Did Not Participate In Practice | Out |
| D.J. Reed | CB | Hip | Did Not Participate In Practice | Out |
| Jacob Saylors | RB | | Full Participation in Practice | |
| Amon-Ra St. Brown | WR | Rib | Limited Participation in Practice | Questionable |
| Sione Vaki | RB | Ankle | Limited Participation in Practice | Questionable |
| DJ Wonnum | DE | | Full Participation in Practice | |

### SUNDAY, NOVEMBER 15TH — 1:00 PMEST — CBS — KC Chiefs (7-2) at ATL Falcons (3-7)

The chunk ended inside the Chiefs table. Rows printed before the cut:

| Player | Position | Injuries | Practice Status | Game Status |
|---|---|---|---|---|
| Jeffrey Bassa | LB | | Full Participation in Practice | |
| Mansoor Delane | CB | Shoulder | Full Participation in Practice | Questionable |
| Justin Fields | QB | | Full Participation in Practice | |
| Jaden Hicks | S | | Full Participation in Practice | |
| Travis Kelce | TE | | Full Participation in Practice | |
| Patrick Mahomes | QB | | Full Participation in Practice | (row cut by the chunk boundary) |

<!-- table truncated by the chunk boundary: the Chiefs table is not complete and its rows are
     excluded from every comparison in collect.py -->

## Use of this transcript

`collect.py` compares the 44 fully-printed rows above (9 WAS + 11 NYG + 15 NE + 9 DET) against the
canonical Week 10 capture held in `nfl-availability-28ef/data/injuries-week10-2026.csv`, which was
taken on 2026-11-13. The Chiefs table is excluded from that comparison because the chunk cut it
mid-row.
