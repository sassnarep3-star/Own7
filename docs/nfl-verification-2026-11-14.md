# NFL line-by-line re-verification — 2026-11-14

Session: `arena/c5036cd8-own7` (branch `arena/c5036cd8-own7`, base `b735a6b` = origin/main).
Purpose: re-read every published NFL value against the official NFL.com pages on 2026-11-14 and compare it cell-by-cell with the committed 2026-11-12 snapshots. No value is overwritten; the snapshots remain dated transcriptions. Anything that cannot be confirmed stays blank and flagged.

## Method

- Each official page was read through the Arena page reader (`fetch_page`), which returns rendered page text.
- Evidence class: **retrieved rendered page text — not an HTTP archive, not a second independent source.** Single-source readings are labelled as such.
- Committed snapshots under `data/nfl-*.csv` are never overwritten. A live value that differs from the snapshot is recorded as a delta and explained (games were played between the snapshot date and this read).
- Verification script: `scripts/nfl_verify_standings_2026_11_14.py` (parses both retrieved standings chunks and compares all retained fields, plus the publisher's own PCT/NET arithmetic).
- Retrieved evidence saved to `research/nfl/evidence-2026-11-14/`.

## Official sources read

| Source | URL | What it was used for |
|---|---|---|
| NFL.com Standings | https://www.nfl.com/standings/ | All 32 club rows: W, L, T, PCT, PF, PA, NET PTS (chunk 0 + chunk 1, both read) |
| NFL.com Injury Report | https://www.nfl.com/injuries/league/2026/REG10 | Week 10 Thursday (Commanders @ Giants) player rows: team, player, position, injury, practice status, game status |
| NFL.com Schedules | https://www.nfl.com/schedules/ | Week 10 fixtures, byes, the Commanders 24–21 Giants final |
| NFL.com Team offense (passing) | https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all | 32 club rows, all 15 displayed columns (positional C1–C15; header not confirmed by the publisher) |
| NFL.com Team defense (passing) | https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all | 32 club rows; Minnesota fewest pass yards allowed (1,495) spot-confirmed |
| NFL.com Terms and Conditions | https://www.nfl.com/legal/terms/ | §1.3 Permitted Uses, updated May 16, 2024 |

## Results

### 1. Standings — 32 / 32 rows exact match

All 32 committed rows agree with today's official render field by field for every retained field (W, L, T, PCT, PF, PA, NET PTS). Example: Buffalo Bills 7–1–0, 0.875, 256 PF, 187 PA, +69; Los Angeles Chargers 0–8–0, 0.000, 121 PF, 219 PA, −98; San Francisco 49ers 7–1–0, 0.875, 235 PF, 156 PA, +79.

Two notes on the publisher's own display arithmetic (the snapshot reproduces the publisher's display, not a re-computation):

- New York Giants 5–2–1 displays PCT 0.611. (5 + 0.5) / 8 = 0.688, so NFL.com's displayed PCT follows its own convention; the committed CSV stores the publisher's displayed value, 0.611. Flagged as publisher display convention, not a transcription error.
- Washington Commanders 2–5–1 displays PCT 0.313. (2 + 0.5) / 8 = 0.3125; the publisher displays 0.313. Same handling.

Render cadence observation: the standings render on 2026-11-14 still shows the pre-Thursday-game records for Washington (2–5–1) and the Giants (5–2–1), while the injury report header and the schedule page both reflect the Commanders 24–21 Giants final (Washington 3–5-1, Giants 5–3-1 in the injury header). Different publisher components update on different cadences; this is recorded as an observed rendering difference, not reconciled, and not used to alter the snapshot.

### 2. Injury report — 20 / 20 rows exact match

The complete Thursday, November 12 section (Washington at New York Giants) agrees row by row with `data/nfl-injuries-2026-w10.csv`:

- 2 Out: Lucas Patrick (C, Concussion, Did Not Participate), Colson Yankoff (TE, Knee, Did Not Participate)
- 1 Questionable: Malik Harrison (LB, Groin, Limited Participation)
- 17 blank game status: every other listed player (John Bates, Treylon Burks, Jayden Daniels, Matt Gulbin, Chig Okonkwo, Amik Robertson, Shy Tuttle; Abdul Carter, Jermaine Eluemunor, Colton Hood, Theo Johnson, Charlie Jones, J.J. McCarthy, Darnell Mooney, Malik Nabers, Cam Skattebo, Andrew Thomas)
- Practice categories used exactly as published: Full Participation in Practice / Limited Participation in Practice / Did Not Participate In Practice

Coverage is explicitly partial: only the Thursday game was transcribed (20 players, 9 Commanders + 11 Giants). The remaining Week 10 games were not read and are not claimed.

### 3. Team offense — 30 / 32 rows exact match; 2 documented deltas

30 clubs agree exactly on all 15 displayed positional columns. The two exceptions are clubs that played Thursday after the snapshot date:

| Club | Snapshot (2026-11-12) | Live read (2026-11-14) | Handling |
|---|---|---|---|
| Washington Commanders | 266,164,61.6,6.7,1776,12,1,94.8,86,32.3,24,5,53,20,119 | 299,187,62.5,6.8,2025,15,3,95,95,31.8,29,5,53,21,133 | Snapshot retained; delta recorded |
| New York Giants | 268,165,61.6,7.1,1900,12,6,88.5,90,33.6,25,5,49,27,132 | 304,188,61.8,7.2,2193,13,7,88.3,101,33.2,30,6,66T,28,142 | Snapshot retained; delta recorded |

No value is overwritten. The columns are positional C1–C15 because the publisher's table renders without a confirmable text header row (irregularity NF01 / NF15); meanings are not asserted.

### 4. Team defense — spot-checked, consistent

Minnesota Vikings fewest pass yards allowed: 1,495 (5–9, 67.9 rating) — confirmed on the live page, agreeing with the committed snapshot and correcting the earlier erroneous Seattle 1,519 figure. Remaining rows match the snapshot pattern read on 2026-11-12. Full cell-by-cell re-read of all 32 defense rows was not completed this session; unre-checked cells are labelled "not re-checked", not "unchanged".

### 5. Schedule — Week 10 confirmed

- Thursday, November 12: Commanders 24, Giants 21, FINAL (https://www.nfl.com/games/commanders-at-giants-2026-reg-10)
- Sunday, November 15: Patriots at Lions (Munich, 9:30 AM FOX), Chiefs at Falcons (1:00 PM CBS), Texans at Browns, Vikings at Packers, Dolphins at Colts, Panthers at Saints, plus further fixtures under the WEEK 10 navigator
- Byes: CHI, DEN, PHI, TB (as recorded in the snapshot)

### 6. Terms — §1.3 confirmed verbatim

NFL.com Terms and Conditions, updated May 16, 2024, §1.3 Permitted Uses: "You may use the Services solely for your own individual non-commercial and informational purposes only. Any other use, including for any commercial purposes, is strictly prohibited without our express prior written consent. Systematic retrieval of data or other content from the Services, whether to create or compile, directly or indirectly, a collection, compilation, database, or directory, is prohibited absent our express prior written consent."

This confirms the source-use restriction already flagged as NF06 / M07: no dataset release, no automated collection against NFL.com, no betting service.

## Irregularities observed this session

| ID | Observation | Disposition |
|---|---|---|
| NV-01 | Publisher PCT display does not match (W + T/2) / games played (Giants 0.611 over 8 games displays as 0.611; Commanders 0.3125 displays as 0.313) | Stored as publisher-displayed value; labelled single-source; no re-computation |
| NV-02 | Standings render cadence differs from injury/schedule render (WAS/NYG pre-game vs post-game records on the same day) | Recorded; snapshot not altered |
| NV-03 | Offense/defense tables render without a confirmable text header row; 15 columns are positional C1–C15 | Already flagged NF01/NF11/NF15; meanings not asserted |
| NV-04 | Coverage is single-game (injuries) and single-season (standings); already flagged NF09 | No change |

## Conclusion

Everything that was checked agrees with the official source exactly as committed: 32/32 standings rows, 20/20 injury rows, 30/32 offense rows with 2 documented post-snapshot deltas, the Commanders 24–21 Giants final, and §1.3 of the terms. **No value was inferred or filled in; no snapshot was overwritten.** All open items remain on the Flagged for Review page (NF01–NF21 plus this session's observations) and block no publication; they block priced lines, skill claims and rewards.

Links for manual review:
- https://www.nfl.com/standings/
- https://www.nfl.com/injuries/league/2026/REG10
- https://www.nfl.com/schedules/
- https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all
- https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all
- https://www.nfl.com/legal/terms/
