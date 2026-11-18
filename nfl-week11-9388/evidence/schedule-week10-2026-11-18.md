# Retained transcript — NFL Week 10 schedule (tail), read 2026-11-18

- **Source URL:** https://www.nfl.com/schedules/2026/by-week/week-10
- **Page title as served:** `NFL Week 10 Schedule 2026: Games, Times, Matchups & Tickets`
- **Read through:** Arena `fetch_page`, chunk index 1 of 2 (page reported `totalChunks: 2`). Only the
  tail of the week was read, because the single fact this desk needed from Week 10 is the result of
  the Monday night fixture that was still pending when every earlier session read the page.
- **Fetch instant (sandbox UTC clock):** within the window 2026-11-18T03:47:13Z – 2026-11-18T03:51:41Z.
- **Clock printed by the publisher:** none.
- **What this file is:** a verbatim transcription of the fixture rows contained in the chunk that
  was read. The chunk began mid-row; the first row below is therefore partial and is marked as
  such. Nothing is reconstructed.

## Rows as printed

### (partial row — chunk began inside this fixture)

- `... 46 points` / `Winner Indicator`
- COWBOYS 4-6 — `40` — `40 points`
- `Final` · `Nov 15` · Replay link `https://www.nfl.com/games/49ers-at-cowboys-2026-reg-10`

The away club of that row is not contained in the chunk that was read, so this desk records only
that the home club was Dallas with 40 points and the row carried a `Winner Indicator` next to the
other club. The full result is not needed by this desk and is not reconstructed here.

### Sunday Night Football, November 15th

- **Steelers 18, Bengals 38, FINAL, Sunday, November 15th** — `https://www.nfl.com/games/steelers-at-bengals-2026-reg-10`
  - STEELERS 6-3 — `18` — `18 points`
  - BENGALS 7-2 — `38` — `38 points` — `Winner Indicator`
  - `Final` · `Nov 15`

### Monday Night Football, November 16th

- **Chargers 23, Ravens 20, FINAL, Monday, November 16th** — `https://www.nfl.com/games/chargers-at-ravens-2026-reg-10`
  - CHARGERS 1-8 — `23` — `23 points` — `Winner Indicator`
  - RAVENS 4-6 — `20` — `20 points`
  - `Final` · `Nov 16`

## Teams on Bye

| Club | Record as printed |
|---|---|
| CHI Chicago Bears | 7-2 |
| DEN Denver Broncos | 7-2 |
| PHI Philadelphia Eagles | 2-7 |
| TB Tampa Bay Buccaneers | 3-6 |

## Why this read matters

Every earlier desk in this repository recorded the Chargers at Ravens fixture as scheduled but not
final, because it was read before kickoff. This read is the first in the repository to carry the
official final: **Chargers 23, Ravens 20**. It is reconciled two ways by `collect.py`:

1. against the standings delta between the frozen 2026-11-17 snapshot and today's read
   (BAL 4-5 → 4-6, LAC 0-8 → 1-8, PF/PA moves of +20/+23 and +23/+20); and
2. against the 149-game official results corpus, which does not contain this fixture.
