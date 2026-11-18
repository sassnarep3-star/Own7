# Official NFL standings page — rendered text, verbatim, as read 2026-11-18

- Source URL: https://www.nfl.com/standings/
- Retrieved: 2026-11-18 (after the Week 10 Monday night game, Chargers at Ravens,
  was played on Monday, November 16th)
- Reader: Arena `fetch_page`; direct HTTPS from this sandbox to nfl.com returns
  curl 000 (recorded by every prior session too), so the rendered-text channel is
  the only one available here.
- Method: rendered page text retrieved in two chunks. The 16 value cells per club
  row are recorded below in the publisher's column order. The publisher's rendered
  table has no text header row, so cell identity is by position and is **validated
  arithmetically** before any value is published: PCT must equal (W + T/2)/games,
  NET PTS must equal PF - PA, and HOME + ROAD must equal the overall record. All
  32 rows pass all three checks (see `data/standings-checks.json`).
- No value below is inferred. The two `/legends` differences from the 2026-11-17
  capture are the Week 10 Monday-night result and are reconciled in
  `data/week10-completion.json`.

## Chunk 0 (AFC)

| club | W | L | T | PCT | PF | PA | HOME | ROAD | DIV | CONF | STRK | LAST5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Buffalo Bills | 8 | 1 | 0 | 0.889 | 287 | 199 | 3 - 1 - 0 | 5 - 0 - 0 | 1 - 1 - 0 | 5 - 1 - 0 | 5W | 5 - 0 - 0 |
| New England Patriots | 5 | 5 | 0 | 0.500 | 221 | 242 | 3 - 1 - 0 | 2 - 4 - 0 | 3 - 0 - 0 | 5 - 1 - 0 | 2L | 2 - 3 - 0 |
| New York Jets | 2 | 8 | 0 | 0.200 | 194 | 254 | 1 - 4 - 0 | 1 - 4 - 0 | 0 - 3 - 0 | 2 - 5 - 0 | 5L | 0 - 5 - 0 |
| Miami Dolphins | 1 | 8 | 0 | 0.111 | 148 | 224 | 0 - 4 - 0 | 1 - 4 - 0 | 1 - 1 - 0 | 1 - 5 - 0 | 3L | 1 - 4 - 0 |
| Cincinnati Bengals | 7 | 2 | 0 | 0.778 | 278 | 193 | 3 - 1 - 0 | 4 - 1 - 0 | 2 - 1 - 0 | 5 - 2 - 0 | 5W | 5 - 0 - 0 |
| Pittsburgh Steelers | 6 | 3 | 0 | 0.667 | 198 | 182 | 4 - 0 - 0 | 2 - 3 - 0 | 2 - 2 - 0 | 3 - 3 - 0 | 1L | 4 - 1 - 0 |
| Cleveland Browns | 6 | 4 | 0 | 0.600 | 188 | 220 | 4 - 0 - 0 | 2 - 4 - 0 | 2 - 1 - 0 | 4 - 3 - 0 | 1W | 3 - 2 - 0 |
| Baltimore Ravens | 4 | 6 | 0 | 0.400 | 209 | 259 | 1 - 4 - 0 | 3 - 2 - 0 | 0 - 2 - 0 | 2 - 5 - 0 | 5L | 0 - 5 - 0 |
| Jacksonville Jaguars | 7 | 2 | 0 | 0.778 | 269 | 144 | 4 - 1 - 0 | 3 - 1 - 0 | 2 - 1 - 0 | 6 - 2 - 0 | 3W | 4 - 1 - 0 |
| Houston Texans | 3 | 6 | 0 | 0.333 | 233 | 219 | 0 - 4 - 0 | 3 - 2 - 0 | 2 - 1 - 0 | 3 - 4 - 0 | 1L | 3 - 2 - 0 |
| Indianapolis Colts | 3 | 7 | 0 | 0.300 | 208 | 271 | 2 - 3 - 0 | 1 - 4 - 0 | 1 - 2 - 0 | 2 - 5 - 0 | 1W | 1 - 4 - 0 |
| Tennessee Titans | 1 | 8 | 0 | 0.111 | 167 | 239 | 0 - 5 - 0 | 1 - 3 - 0 | 1 - 2 - 0 | 1 - 6 - 0 | 3L | 1 - 4 - 0 |
| Kansas City Chiefs | 7 | 2 | 0 | 0.778 | 237 | 156 | 4 - 0 - 0 | 3 - 2 - 0 | 3 - 1 - 0 | 6 - 1 - 0 | 2W | 3 - 2 - 0 |
| Denver Broncos | 7 | 2 | 0 | 0.778 | 198 | 186 | 4 - 0 - 0 | 3 - 2 - 0 | 2 - 1 - 0 | 3 - 1 - 0 | 5W | 5 - 0 - 0 |
| Las Vegas Raiders | 4 | 6 | 0 | 0.400 | 251 | 289 | 1 - 4 - 0 | 3 - 2 - 0 | 1 - 1 - 0 | 3 - 3 - 0 | 2L | 1 - 4 - 0 |
| Los Angeles Chargers | 1 | 8 | 0 | 0.111 | 144 | 239 | 0 - 4 - 0 | 1 - 4 - 0 | 0 - 3 - 0 | 1 - 5 - 0 | 1W | 1 - 4 - 0 |

## Chunk 1 (NFC)

| club | W | L | T | PCT | PF | PA | HOME | ROAD | DIV | CONF | STRK | LAST5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| New York Giants | 5 | 3 | 1 | 0.611 | 203 | 196 | 3 - 2 - 0 | 2 - 1 - 1 | 2 - 1 - 1 | 3 - 3 - 1 | 1L | 2 - 2 - 1 |
| Dallas Cowboys | 4 | 6 | 0 | 0.400 | 286 | 282 | 1 - 4 - 0 | 3 - 2 - 0 | 2 - 1 - 0 | 2 - 5 - 0 | 1L | 2 - 3 - 0 |
| Washington Commanders | 3 | 5 | 1 | 0.389 | 196 | 223 | 2 - 2 - 1 | 1 - 3 - 0 | 2 - 2 - 1 | 3 - 4 - 1 | 1W | 2 - 2 - 1 |
| Philadelphia Eagles | 2 | 7 | 0 | 0.222 | 148 | 221 | 1 - 4 - 0 | 1 - 3 - 0 | 1 - 3 - 0 | 1 - 6 - 0 | 7L | 0 - 5 - 0 |
| Detroit Lions | 7 | 2 | 0 | 0.778 | 257 | 199 | 5 - 0 - 0 | 2 - 2 - 0 | 2 - 0 - 0 | 4 - 1 - 0 | 5W | 5 - 0 - 0 |
| Minnesota Vikings | 7 | 2 | 0 | 0.778 | 176 | 126 | 3 - 1 - 0 | 4 - 1 - 0 | 3 - 1 - 0 | 5 - 1 - 0 | 1W | 3 - 2 - 0 |
| Chicago Bears | 7 | 2 | 0 | 0.778 | 241 | 184 | 4 - 1 - 0 | 3 - 1 - 0 | 0 - 2 - 0 | 5 - 2 - 0 | 4W | 4 - 1 - 0 |
| Green Bay Packers | 6 | 4 | 0 | 0.600 | 226 | 221 | 3 - 2 - 0 | 3 - 2 - 0 | 1 - 3 - 0 | 4 - 4 - 0 | 1L | 3 - 2 - 0 |
| Carolina Panthers | 4 | 5 | 0 | 0.444 | 219 | 236 | 1 - 3 - 0 | 3 - 2 - 0 | 2 - 1 - 0 | 4 - 3 - 0 | 1W | 2 - 3 - 0 |
| Tampa Bay Buccaneers | 3 | 6 | 0 | 0.333 | 202 | 178 | 1 - 4 - 0 | 2 - 2 - 0 | 2 - 0 - 0 | 3 - 3 - 0 | 1L | 3 - 2 - 0 |
| New Orleans Saints | 3 | 6 | 0 | 0.333 | 202 | 236 | 1 - 5 - 0 | 2 - 1 - 0 | 0 - 2 - 0 | 1 - 4 - 0 | 1L | 2 - 3 - 0 |
| Atlanta Falcons | 3 | 7 | 0 | 0.300 | 201 | 258 | 1 - 5 - 0 | 2 - 2 - 0 | 1 - 2 - 0 | 3 - 3 - 0 | 3L | 1 - 4 - 0 |
| San Francisco 49ers | 8 | 1 | 0 | 0.889 | 281 | 196 | 5 - 0 - 0 | 3 - 1 - 0 | 3 - 0 - 0 | 5 - 1 - 0 | 2W | 4 - 1 - 0 |
| Seattle Seahawks | 6 | 4 | 0 | 0.600 | 223 | 175 | 4 - 2 - 0 | 2 - 2 - 0 | 2 - 1 - 0 | 2 - 3 - 0 | 2W | 3 - 2 - 0 |
| Los Angeles Rams | 6 | 4 | 0 | 0.600 | 248 | 187 | 2 - 3 - 0 | 4 - 1 - 0 | 1 - 2 - 0 | 4 - 2 - 0 | 4W | 4 - 1 - 0 |
| Arizona Cardinals | 3 | 7 | 0 | 0.300 | 184 | 289 | 0 - 4 - 0 | 3 - 3 - 0 | 1 - 4 - 0 | 2 - 6 - 0 | 2L | 2 - 3 - 0 |

## Page legend (verbatim, chunk 1)

W : Wins / L : Losses / T : Ties / PCT : Winning Percentage / HOME : Home Record /
ROAD : Road Record / DIV : Division Record / CONF : Conference Record /
PF : Total Points For / PA : Total Points Against / NET PTS : Net Points / STRK : Streak

Note: the rendered page prints 12 value cells per row plus an unlabelled 13th cell
between DIV and STRK (the conference-winning-percentage column) and an unlabelled
final column (the point differential column). The canonical parser in
`nfl-results/extract.py` identifies cells 0-15 by position and validates them
arithmetically; this capture records the 12 labelled, printed fields and the
derived NET PTS, and does not assert a value for any cell it could not label.
