# Probes for an official snap-count source — read 2026-11-18

QUESTION|Does an official NFL source publish per-player or per-team snap counts, so that depth order can
QUESTION|be modelled from playing time rather than from jersey order or club depth charts?

PROBE_1_URL|https://www.nfl.com/stats/team-stats/offense/snapcounts/2026/reg/all
PROBE_1_TITLE|2026 NFL offense snapcounts stats by Team | NFL.com
PROBE_1_RESULT|The URL resolves to a page titled "... offense snapcounts stats by Team", but the table rendered
PROBE_1_RESULT|is the PASSING table (columns Att, Cmp, Cmp %, Yds, ... Sacks). The left-hand category menu on
PROBE_1_RESULT|the rendered page lists only: Passing, Rushing, Receiving, Scoring, Downs. No snap-count table
PROBE_1_RESULT|is present. Verdict: NO official team snap-count table at this URL.

PROBE_2_URL|https://www.nfl.com/stats/player-stats/
PROBE_2_TITLE|NFL 2026 Player Stats | passing Stats | NFL.com
PROBE_2_RESULT|The rendered category menu lists exactly: Passing, Rushing, Receiving, Fumbles, Tackles,
PROBE_2_RESULT|Interceptions, Field Goals, Kickoffs, Kickoff Returns, Punting, Punt Returns.
PROBE_2_RESULT|No snap-count category exists. Verdict: NO official player snap-count table.

PROBE_3_URL|https://static.www.nfl.com/image/upload/v1794916121/gamecenter/ab78ad5a-4feb-11f1-abca-2c54536568a9.pdf
PROBE_3_TITLE|Official NFL Game Book, Los Angeles Chargers at Baltimore Ravens, 11/16/2026
PROBE_3_RESULT|The Game Book prints: Lineups (offence and defence, 11 each), Substitutions, Did Not Play,
PROBE_3_RESULT|Not Active, Field Goals, team quarter scores, Scoring Plays, Final Individual Statistics,
PROBE_3_RESULT|Final Defensive Statistics, drive charts and play-by-play. No snap-count field appears.
PROBE_3_RESULT|Verdict: NO snap counts in the official Game Book.

PROBE_4_METHOD|Text search of the 13 official Game Book extracts retained by the nfl-gamebook-5213243e desk
PROBE_4_PATH|nfl-gamebook-5213243e/raw/g01-WAS-NYG.txt ... g13-LAR-AZ.txt (read-only, not modified)
PROBE_4_RESULT|Case-insensitive search for "snap" across all 13 retained Game Book extracts returns 0 hits.
PROBE_4_RESULT|Verdict: no snap counts in any retained official Game Book.

VERDICT|No official snap-count source was found on nfl.com on 2026-11-18 across four independent probes.
VERDICT|The brief's requirements that depend on playing time (R11 depth from playing time, R31 capture
VERDICT|official snap counts, R56 snap counts as the starter proxy) therefore stay OPEN, with the
VERDICT|official Game Book "Lineups / Substitutions / Did Not Play / Not Active" blocks as the only
VERDICT|official playing-participation evidence this desk could verify.
CAVEAT|Absence of evidence on four probed surfaces is not proof that no official snap product exists
CAVEAT|anywhere (for example behind a licensed data feed). This desk records what it read, and nothing
CAVEAT|about products it did not read.
