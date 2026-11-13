# NFL line-by-line re-verification — 2026-11-13

Session `session-arena-a97a5100-own7`. Companion to [`nfl-repo-review-2026-11-13.md`](nfl-repo-review-2026-11-13.md).

This document records exactly what was re-read, how it was reached, and what it does or does not
support. It deliberately separates three things that are easy to blur:

1. **The value the repository publishes** (from the frozen 2026-11-12 snapshot).
2. **The value the official page prints today**, re-read this session.
3. **The delta**, which is either "identical", "moved because a game was played", or "not re-checked".

A value is only called *re-verified* if it was read again from the publisher today. Values that were
not re-read are marked **not re-checked**, not "unchanged".

## Access method, stated because it limits the evidence class

| Path | Result today |
|---|---|
| `fetch_page` (Arena page reader) → `nfl.com` pages | Works; returns rendered page text in chunks |
| `curl` from the sandbox → `https://www.nfl.com/standings/` | Fails, HTTP code `000` (egress restricted) |
| `curl` → `https://github.com/` | Works, HTTP 200 |

Consequence: every official value below is a **rendered-text retrieval through a page reader**, not an
HTTP archive and not an independent second source. That evidence class is stated on the site rather
than being implied to be stronger. `docs/nfl-verification.md` (2026-11-12) did not record this.

## Sources re-read this session

| ID | URL | Reached | Chunks read | Verbatim capture |
|---|---|---|---|---|
| NFL-STANDINGS | https://www.nfl.com/standings/ | Yes | 1–2 of 2 | `research/nfl/evidence-2026-11-13/standings-2026-11-13.retrieved.md` |
| NFL-INJ-W10 | https://www.nfl.com/injuries/ | Yes | 1 of 8 (Thursday block, complete) | `research/nfl/evidence-2026-11-13/injury-report-w10-tnf.retrieved.md` |
| NFL-SCHED-W10 | https://www.nfl.com/schedules/ | Yes | 1–2 of 3 | `research/nfl/evidence-2026-11-13/schedule-2026-w10.retrieved.md` |
| NFL-TERMS-LEGAL | https://www.nfl.com/legal/terms/ | Yes | 1, 3, 4 of 9 | `research/nfl/evidence-2026-11-13/terms-2026-11-13.retrieved.md` |
| NFL-DEPTH-PATH | https://www.nfl.com/teams/new-england-patriots/depth-chart | Yes, returns **404** | 1 of 1 | quoted in §3 below |

Deep link note: `https://www.nfl.com/schedules/2026/REG11/` is still served as the Week 10 board
(page self-reports WEEK 10 and its footer links are `week-9` / `week-11`). This is the same
irregularity as before and is not a new finding.

---

## 1. Standings — 32 of 32 rows compared field by field

Fields compared: W, L, T, PCT, PF, PA, NET PTS, HOME, ROAD, STRK. Fields withheld in both captures:
DIV, CONF and the two further record columns, because the rendered table still has **no header row**
and the legend order contradicts the rendered field order. That is unchanged and still open.

| Club | Published (snapshot 11-12) W-L-T · PF-PA | Read today | Delta |
|---|---|---|---|
| BUF | 7-1-0 · 256-187 | 7-1-0 · 256-187 | none |
| NE | 5-4-0 · 211-207 | 5-4-0 · 211-207 | none |
| NYJ | 2-7-0 · 182-223 | 2-7-0 · 182-223 | none |
| MIA | 1-7-0 · 126-200 | 1-7-0 · 126-200 | none |
| PIT | 6-2-0 · 180-144 | 6-2-0 · 180-144 | none |
| CIN | 6-2-0 · 240-175 | 6-2-0 · 240-175 | none |
| CLE | 5-4-0 · 161-196 | 5-4-0 · 161-196 | none |
| BAL | 4-5-0 · 189-236 | 4-5-0 · 189-236 | none |
| JAX | 6-2-0 · 229-121 | 6-2-0 · 229-121 | none |
| HOU | 3-5-0 · 209-192 | 3-5-0 · 209-192 | none |
| IND | 2-7-0 · 184-249 | 2-7-0 · 184-249 | none |
| TEN | 1-7-0 · 144-199 | 1-7-0 · 144-199 | none |
| DEN | 7-2-0 · 198-186 | 7-2-0 · 198-186 | none |
| KC | 6-2-0 · 202-143 | 6-2-0 · 202-143 | none |
| LV | 4-5-0 · 238-268 | 4-5-0 · 238-268 | none |
| LAC | 0-8-0 · 121-219 | 0-8-0 · 121-219 | none |
| NYG | **5-2-1** · **182-172** | **5-3-1 · 203-196** | **moved: game played** |
| DAL | 4-5-0 · 246-236 | 4-5-0 · 246-236 | none |
| WAS | **2-5-1** · **172-202** | **3-5-1 · 196-223** | **moved: game played** |
| PHI | 2-7-0 · 148-221 | 2-7-0 · 148-221 | none |
| CHI | 7-2-0 · 241-184 | 7-2-0 · 241-184 | none |
| DET | 6-2-0 · 222-189 | 6-2-0 · 222-189 | none |
| MIN | 6-2-0 · 146-116 | 6-2-0 · 146-116 | none |
| GB | 6-3-0 · 216-191 | 6-3-0 · 216-191 | none |
| CAR | 3-5-0 · 199-219 | 3-5-0 · 199-219 | none |
| NO | 3-5-0 · 185-216 | 3-5-0 · 185-216 | none |
| TB | 3-6-0 · 202-178 | 3-6-0 · 202-178 | none |
| ATL | 3-6-0 · 188-223 | 3-6-0 · 188-223 | none |
| SF | 7-1-0 · 235-156 | 7-1-0 · 235-156 | none |
| SEA | 5-4-0 · 202-162 | 5-4-0 · 202-162 | none |
| LA | 5-4-0 · 214-181 | 5-4-0 · 214-181 | none |
| AZ | 3-6-0 · 178-255 | 3-6-0 · 178-255 | none |

**30 of 32 rows are byte-identical. 2 of 32 moved, both accounted for by the Thursday result.**

Arithmetic re-checked on today's capture as well: PCT = (W + T/2)/games for all 32 clubs;
NET PTS = PF − PA for all 32; HOME + ROAD = overall record for all 32 (including the two 9-game ties);
league total wins (256) = league total losses (256) across 288 team-games.

## 2. Injury report — 20 of 20 rows compared

Thursday block only (WAS at NYG). All 20 rows identical: same nine Commanders, same eleven Giants,
same positions, same practice statuses, same game statuses. Still **17 of 20 game-status cells blank**,
still **2 Out** (Lucas Patrick, concussion; Colson Yankoff, knee), still **1 Questionable**
(Malik Harrison, groin).

Values the official report does **not** contain, in either capture, and which the site therefore leaves
blank: starter status, depth rank, expected replacement, snap share, and whether the player is on the
offence or defence side of the ball beyond his listed position. No starter-vs-backup claim is
supported by this source. Not a new finding — the 2026-11-12 review said the same, and today's
re-read confirms it rather than weakly agreeing with it.

Fixtures 2–14 of the Week 10 injury page were **not** transcribed. The site makes no claim about them,
and this document makes none.

## 3. Depth charts — checked, and the publisher does not serve them at the league path

| URL | Result today |
|---|---|
| `https://www.nfl.com/teams/depth-chart` (registered ID `NFL-DEPTH-PATH`) | no league-wide chart at that path |
| `https://www.nfl.com/teams/new-england-patriots/depth-chart` | **404 — "404 - Flag on the Play."** |

So the league site cannot be cited for a starter/backup ordering. Club sites are the only official
route, and they are not uniform: some publish a depth chart, some do not, and none of them state a
snap-share. This is why the requirement to know "2nd, 3rd or 4th string" replacements is published as
**unmet and blocked**, not as partially met.

## 4. Schedule — 14 of 14 fixtures compared

All 14 matchups, days, dates, kickoff times and networks match the published snapshot exactly, and the
four byes (CHI 7-2, DEN 7-2, PHI 2-7, TB 3-6) match. **New in today's capture:** one fixture now
prints a final score, and prints two contradictory things at once:

- link text: `Commanders 24, Giants 21, FINAL`
- score banners: `Hidden Score` (both clubs)

The 24-21 reading is the only one consistent with the standings deltas in §1, so it is what the site
records — with the contradiction quoted, not smoothed over. Eleven fixtures remain unplayed and print
no result; three more (week 10's remaining Sunday/Monday games) had not been played at capture time.

## 5. What could not be verified today, and stays blank

| Value | Status | Why |
|---|---|---|
| Any market spread, total, moneyline or price | **blank** | `nfl.com/odds/` registered as checked-and-absent; no operator quote retrieved; terms §1.3 restrict systematic retrieval |
| Any player prop line | **blank** | no official publisher of prop lines on an NFL domain |
| ROI, CLV, break-even, closing line | **blank** | no price exists in the record to compute them from |
| Snap counts, target share, carry share | **blank** | not published on any page read this session |
| Starter / backup designation per player | **blank** | see §3 |
| Injury-to-replacement mapping | **blank** | requires both of the above |
| Player-level game logs | **blank** | not retrieved; no player stat table was read today |
| Leg-to-leg correlation | **blank** | requires player-level joint outcomes; the only correlations here are cross-sectional across clubs |
| Two independent sources for any value | **not met** | every value is single-source; stated on the flags page |

## 6. Rows that would have been inference, and were therefore not filled

- NYG's new 5-3-1 record does **not** imply which club won beyond the arithmetic; the win is taken
  from the publisher's own score text, not from the record.
- The 24-21 score is **not** used to score the originated line for that game (that would be
  post-hoc and unpre-registered). It is recorded as available for a future, pre-registered backtest.
- The two moved clubs' new PF/PA are **not** back-filled into the frozen snapshot, because the
  snapshot's receipts hash the 2026-11-12 bytes.
- No injury status is translated into "starter out" or "backup in".
- No absent player is assigned a replacement, and no projected points are shifted for an absence.

## 7. Verdict

- Official-source re-verification today: **30/32 standings rows, 20/20 injury rows, 14/14 fixtures**.
- Values that moved: **2**, both explained by one completed game, both published as an update.
- Values published without an official source: **none found** in the NFL canonical section — every
  non-derived row links a registered source. Derived rows are labelled `Derived`.
- Values that are blank and correctly blank: all market, usage, depth, prop and performance cells.
- Anything this document could not check is marked **not re-checked**, not "unchanged".
