# Evidence boundary

Checked on 2026-11-03 through Arena `fetch_page`, which could retrieve rendered official pages even though direct workspace traffic is restricted to GitHub/package hosts.

`receipts.json` records the exact source URLs, chunks read, row counts and SHA-256 of the retained CSV files. The `*-normalized.csv` files and `jokic-window-transcript.csv` are normalized transcriptions compared by this session against the returned official tables. They are **not raw HTTP captures**, independent second sources, or proof that a source never changes. Checksums establish integrity only. A later automated comparison to these files verifies consistency, not source truth.

Retained team fields: official display rank, team, GP, W, L, WIN%, PTS, FG%, 3P%, FT%, OREB, DREB, REB, AST, TOV, STL, BLK, PF, PFD, +/-. The source explicitly labels the column between BLK and PF as BLKA; no ambiguous-column claim remains. Conference/division columns from the old team CSV were removed, not guessed. Utah's tied display rank is 26, not the old 27.

The player table is a PTS >= 26 scoring-selected subset of 15 players, **not a complete player universe**. Full team names are resolved via NBA team links/IDs in the two checked tables. Age is the displayed snapshot field, not an independently calculated season age.

The 2026-27 standings are a frozen snapshot, not a live feed; game counts vary from 5 to 8. Source rows preserve NBA rounding; displayed per-game components need not sum exactly after rounding.

The Jokić cohort is all 32 rows displayed for the explicit 2026-02-01 through 2026-04-12 date filter. Only date, game ID, matchup, W/L, displayed integer MIN, PTS, REB and AST were retained. The profile header's current-season averages are deliberately excluded. A prior `LastNGames=30` URL displayed 65 total rows with pagination and did not apply the intended filter; it was rejected. The explicit window reports 32 rows on one page. All 32 were checked.

The cohort/window/thresholds were chosen retrospectively for a small demonstration. They cannot establish skill, verify pregame information availability, estimate a current market edge, or validate a wagering strategy. No historical odds, future schedules, player participation forecasts, market lines, cash rewards or CLV values have been filled in.
