# Verification log, session 243828fc (14 Nov 2026, Singapore time)

Each item records what was read and when. Anything not listed here is UNVERIFIED.

| # | Check | Source | Result |
|---|---|---|---|
| 1 | Live Week 10 injury report, chunks 0–7 read | https://www.nfl.com/injuries/league/2026/REG10 | Read. Row transcription NOT yet checked line by line; all row-level values UNVERIFIED and withheld from the site. |
| 2 | Saved ledger game-status scope | nfl-availability-28ef/data/injuries-week10-2026.csv (326 rows) | 5 clubs have a game status (25 rows). Confirmed by reading the file. |
| 3 | Standings spot check, 24 of 32 teams | https://www.nfl.com/standings/ | 22 match repo file data/nfl-standings-week10-2026.csv (W-L-T, PF, PA, streak). NYG (repo 5-2-1 vs live 5-3-1) and WAS (repo 2-5-1 vs live 3-5-1) differ; cause not established. ARI, ATL, CAR, LAR, NO, SEA, SF, TB not checked. |
| 4 | Detroit chart label | https://www.detroitlions.com/team/depth-chart | Headed "2026 Unofficial Depth Chart". Kerby Joseph not printed. |
| 5 | NFL.com terms §1.3 | https://www.nfl.com/legal/terms (updated May 16, 2024) | Personal, non-commercial, informational use; compilation prohibited without written consent. |
| 6 | Subscription terms (not general terms) | https://www.nfl.com/legal/subscriptions_terms | NFL+ only in 50 US states and DC. Not cited for §1.3. |
| 7 | NFL 2026 player stats page exists | https://www.nfl.com/stats/player-stats/ | Read; used as the source for question Q04. No backup-comparison data collected. |
| 8 | Singapore GRA pages | https://www.gra.gov.sg/harm-minimisation/unlawful-remote-gambling-activities ; .../problem-gambling | Read. Penalties as stated on the GRA page. |
| 9 | Remote Gambling Act 2014 statute | https://sso.agc.gov.sg/Act/RGA2014 | "Page Not Found" from this sandbox. Statute text UNVERIFIED. |
| 10 | Repo CI-equivalent baseline | P1 in COORDINATION.md | 27 of 27 commands exit 0 on this branch before changes. |

Not done in this session (carried to Flagged for Review): line-by-line verification of the live transcription; full standings check of 8 teams; the second standings file's canonical status; re-check of other clubs' chart labels.
