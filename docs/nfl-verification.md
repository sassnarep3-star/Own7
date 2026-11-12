# NFL verification · checked 2026-11-12

Every NFL table row was compared against the official rendered page via Arena fetch_page. Normalized transcriptions are retained under `research/evidence/nfl-*-normalized.csv` (identical to `data/nfl-*.csv`). Hashes prove integrity, not independent truth.

## Row checks

| Dataset | Rows | Source | Result |
|---|---|---|---|
| Standings 2026 | 32 | https://www.nfl.com/standings/ | 32/32 matched (W,L,T,PCT,PF,PA,Net,Home,Road,Div,Conf,Strk,Last5) |
| Passing top 25 | 25 | https://www.nfl.com/stats/player-stats/ | 25/25 matched (Yds,Yds/Att,Att,Cmp,Cmp%,TD,INT,Rate,1st,1st%,20+,40+,Lng,Sck,SckY) |
| Rushing top 25 | 25 | https://www.nfl.com/stats/player-stats/category/rushing/2026/reg/all/rushingyards/desc | 25/25 values matched in displayed order; headers not rendered — positional C1-C9, meanings not asserted (NF08) |
| Receiving top 25 | 25 | https://www.nfl.com/stats/player-stats/category/receiving/2026/reg/all/receivingreceptions/desc | 25/25 values matched in displayed order; headers not rendered — positional C1-C9 (NF08) |
| Team offense passing | 32 | https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all | 32/32 matched; header confirmed by arithmetic + defense header (NF11) |
| Team defense passing | 32 | https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all | 32/32 matched |
| Injuries Week 7 bounded | 45 | https://www.nfl.com/injuries/league/2026/reg7 | 45/45 matched (Player,Position,Injuries,PracticeStatus,GameStatus); Replacement/Deficiency blank (NF10) |

Total: 216 rows. Arithmetic spot-checks: passing Yds/Att = Yds/Att (e.g. Jordan Love 2618/341=7.68→7.7); team offense Cmp% = Cmp/Att; standings Net = PF-PA; PCT = (W+0.5T)/(W+L+T).

## Irregularities flagged

- NF08: Rushing/receiving headers not rendered — published positionally, no meanings asserted.
- NF09: Schedule and roster pages exist but no rows transcribed — features blank.
- NF10: Injury replacements/deficiencies not stated on page — blank.
- NF11: Team offense header not rendered — confirmed by arithmetic, flagged for manual re-check.
- NF04: NFL Terms restrict gambling use — betting prices disabled.
- All other flags (NF01-NF07) published on the Flagged for Review page.

No values were inferred or filled in. Blank cells are intentional.
