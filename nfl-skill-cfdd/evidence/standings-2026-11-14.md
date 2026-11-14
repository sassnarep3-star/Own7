# NFL.com standings — read 2026-11-14
url: https://www.nfl.com/standings/
title: "2026 NFL Division Standings"
read_on: 2026-11-14
retrieval: Arena page reader (rendered text). Direct HTTPS from the sandbox to nfl.com returns
           curl code 000, so this is a rendered-text evidence class, not an HTTP archive.
note: The rendered row below each club is a pipe table. Columns are printed in this order:
      W | L | T | PCT | PF | PA | NET PTS | (3-part record) | (3-part record) | (3-part record) |
      (decimal) | (3-part record) | (decimal) | (3-part record) | STRK | (3-part record)
      The page LEGEND names W, L, T, PCT, HOME, ROAD, DIV, CONF, PF, PA, NET PTS, STRK but the
      rendered column order does not let the three unnamed 3-part records be identified by name.
      Following the standing rule of this repository, unnamed columns are NOT assigned: only
      W, L, T, PCT, PF, PA, NET PTS, STRK and the trailing 5-game record are transcribed.
      This is the same limitation recorded on nfl-standings.html.

## AMERICAN FOOTBALL CONFERENCE

| Buffalo Bills | 7 | 1 | 0 | 0.875 | 256 | 187 | 69 | 3 - 1 - 0 | 4 - 0 - 0 | 0 - 1 - 0 | 0.000 | 4 - 1 - 0 | 0.800 | 3 - 0 - 0 | 4W | 4 - 1 - 0 |
| New England Patriots | 5 | 4 | 0 | 0.556 | 211 | 207 | 4 | 3 - 1 - 0 | 2 - 3 - 0 | 3 - 0 - 0 | 1.000 | 5 - 1 - 0 | 0.833 | 0 - 3 - 0 | 1L | 3 - 2 - 0 |
| New York Jets | 2 | 7 | 0 | 0.222 | 182 | 223 | -41 | 1 - 3 - 0 | 1 - 4 - 0 | 0 - 2 - 0 | 0.000 | 2 - 4 - 0 | 0.333 | 0 - 3 - 0 | 4L | 1 - 4 - 0 |
| Miami Dolphins | 1 | 7 | 0 | 0.125 | 126 | 200 | -74 | 0 - 4 - 0 | 1 - 3 - 0 | 1 - 1 - 0 | 0.500 | 1 - 4 - 0 | 0.200 | 0 - 3 - 0 | 2L | 1 - 4 - 0 |
| Pittsburgh Steelers | 6 | 2 | 0 | 0.750 | 180 | 144 | 36 | 4 - 0 - 0 | 2 - 2 - 0 | 2 - 1 - 0 | 0.667 | 3 - 2 - 0 | 0.600 | 3 - 0 - 0 | 4W | 4 - 1 - 0 |
| Cincinnati Bengals | 6 | 2 | 0 | 0.750 | 240 | 175 | 65 | 2 - 1 - 0 | 4 - 1 - 0 | 1 - 1 - 0 | 0.500 | 4 - 2 - 0 | 0.667 | 2 - 0 - 0 | 4W | 4 - 1 - 0 |
| Cleveland Browns | 5 | 4 | 0 | 0.556 | 161 | 196 | -35 | 3 - 0 - 0 | 2 - 4 - 0 | 2 - 1 - 0 | 0.667 | 3 - 3 - 0 | 0.500 | 2 - 1 - 0 | 2L | 2 - 3 - 0 |
| Baltimore Ravens | 4 | 5 | 0 | 0.444 | 189 | 236 | -47 | 1 - 3 - 0 | 3 - 2 - 0 | 0 - 2 - 0 | 0.000 | 2 - 4 - 0 | 0.333 | 2 - 1 - 0 | 4L | 1 - 4 - 0 |
| Jacksonville Jaguars | 6 | 2 | 0 | 0.750 | 229 | 121 | 108 | 4 - 1 - 0 | 2 - 1 - 0 | 1 - 1 - 0 | 0.500 | 5 - 2 - 0 | 0.714 | 1 - 0 - 0 | 2W | 4 - 1 - 0 |
| Houston Texans | 3 | 5 | 0 | 0.375 | 209 | 192 | 17 | 0 - 4 - 0 | 3 - 1 - 0 | 2 - 1 - 0 | 0.667 | 3 - 3 - 0 | 0.500 | 0 - 2 - 0 | 1W | 3 - 2 - 0 |
| Indianapolis Colts | 2 | 7 | 0 | 0.222 | 184 | 249 | -65 | 1 - 3 - 0 | 1 - 4 - 0 | 1 - 2 - 0 | 0.333 | 1 - 5 - 0 | 0.167 | 1 - 2 - 0 | 5L | 0 - 5 - 0 |
| Tennessee Titans | 1 | 7 | 0 | 0.125 | 144 | 199 | -55 | 0 - 4 - 0 | 1 - 3 - 0 | 1 - 1 - 0 | 0.500 | 1 - 5 - 0 | 0.167 | 0 - 2 - 0 | 2L | 1 - 4 - 0 |
| Denver Broncos | 7 | 2 | 0 | 0.778 | 198 | 186 | 12 | 4 - 0 - 0 | 3 - 2 - 0 | 2 - 1 - 0 | 0.667 | 3 - 1 - 0 | 0.750 | 4 - 1 - 0 | 5W | 5 - 0 - 0 |
| Kansas City Chiefs | 6 | 2 | 0 | 0.750 | 202 | 143 | 59 | 4 - 0 - 0 | 2 - 2 - 0 | 3 - 1 - 0 | 0.750 | 6 - 1 - 0 | 0.857 | 0 - 1 - 0 | 1W | 3 - 2 - 0 |
| Las Vegas Raiders | 4 | 5 | 0 | 0.444 | 238 | 268 | -30 | 1 - 3 - 0 | 3 - 2 - 0 | 1 - 1 - 0 | 0.500 | 3 - 3 - 0 | 0.500 | 1 - 2 - 0 | 1L | 1 - 4 - 0 |
| Los Angeles Chargers | 0 | 8 | 0 | 0.000 | 121 | 219 | -98 | 0 - 4 - 0 | 0 - 4 - 0 | 0 - 3 - 0 | 0.000 | 0 - 5 - 0 | 0.000 | 0 - 3 - 0 | 8L | 0 - 5 - 0 |

## NATIONAL FOOTBALL CONFERENCE

| New York Giants | 5 | 3 | 1 | 0.611 | 203 | 196 | 7 | 3 - 2 - 0 | 2 - 1 - 1 | 2 - 1 - 1 | 0.625 | 3 - 3 - 1 | 0.500 | 2 - 0 - 0 | 1L | 2 - 2 - 1 |
| Dallas Cowboys | 4 | 5 | 0 | 0.444 | 246 | 236 | 10 | 1 - 3 - 0 | 3 - 2 - 0 | 2 - 1 - 0 | 0.667 | 2 - 4 - 0 | 0.333 | 2 - 1 - 0 | 1W | 2 - 3 - 0 |
| Washington Commanders | 3 | 5 | 1 | 0.389 | 196 | 223 | -27 | 2 - 2 - 1 | 1 - 3 - 0 | 2 - 2 - 1 | 0.500 | 3 - 4 - 1 | 0.438 | 0 - 1 - 0 | 1W | 2 - 2 - 1 |
| Philadelphia Eagles | 2 | 7 | 0 | 0.222 | 148 | 221 | -73 | 1 - 4 - 0 | 1 - 3 - 0 | 1 - 3 - 0 | 0.250 | 1 - 6 - 0 | 0.143 | 1 - 1 - 0 | 7L | 0 - 5 - 0 |
| Chicago Bears | 7 | 2 | 0 | 0.778 | 241 | 184 | 57 | 4 - 1 - 0 | 3 - 1 - 0 | 0 - 2 - 0 | 0.000 | 5 - 2 - 0 | 0.714 | 2 - 0 - 0 | 4W | 4 - 1 - 0 |
| Detroit Lions | 6 | 2 | 0 | 0.750 | 222 | 189 | 33 | 4 - 0 - 0 | 2 - 2 - 0 | 2 - 0 - 0 | 1.000 | 4 - 1 - 0 | 0.800 | 2 - 1 - 0 | 4W | 4 - 1 - 0 |
| Minnesota Vikings | 6 | 2 | 0 | 0.750 | 146 | 116 | 30 | 3 - 1 - 0 | 3 - 1 - 0 | 2 - 1 - 0 | 0.667 | 4 - 1 - 0 | 0.800 | 2 - 1 - 0 | 2L | 3 - 2 - 0 |
| Green Bay Packers | 6 | 3 | 0 | 0.667 | 216 | 191 | 25 | 3 - 1 - 0 | 3 - 2 - 0 | 1 - 2 - 0 | 0.333 | 4 - 3 - 0 | 0.571 | 2 - 0 - 0 | 2W | 4 - 1 - 0 |
| Carolina Panthers | 3 | 5 | 0 | 0.375 | 199 | 219 | -20 | 1 - 3 - 0 | 2 - 2 - 0 | 1 - 1 - 0 | 0.500 | 3 - 3 - 0 | 0.500 | 0 - 2 - 0 | 3L | 2 - 3 - 0 |
| New Orleans Saints | 3 | 5 | 0 | 0.375 | 185 | 216 | -31 | 1 - 4 - 0 | 2 - 1 - 0 | 0 - 1 - 0 | 0.000 | 1 - 3 - 0 | 0.250 | 2 - 2 - 0 | 1W | 2 - 3 - 0 |
| Tampa Bay Buccaneers | 3 | 6 | 0 | 0.333 | 202 | 178 | 24 | 1 - 4 - 0 | 2 - 2 - 0 | 2 - 0 - 0 | 1.000 | 3 - 3 - 0 | 0.500 | 0 - 3 - 0 | 1L | 3 - 2 - 0 |
| Atlanta Falcons | 3 | 6 | 0 | 0.333 | 188 | 223 | -35 | 1 - 4 - 0 | 2 - 2 - 0 | 1 - 2 - 0 | 0.333 | 3 - 3 - 0 | 0.500 | 0 - 3 - 0 | 2L | 1 - 4 - 0 |
| San Francisco 49ers | 7 | 1 | 0 | 0.875 | 235 | 156 | 79 | 5 - 0 - 0 | 2 - 1 - 0 | 3 - 0 - 0 | 1.000 | 4 - 1 - 0 | 0.800 | 3 - 0 - 0 | 1W | 4 - 1 - 0 |
| Seattle Seahawks | 5 | 4 | 0 | 0.556 | 202 | 162 | 40 | 4 - 2 - 0 | 1 - 2 - 0 | 2 - 1 - 0 | 0.667 | 2 - 3 - 0 | 0.400 | 3 - 1 - 0 | 1W | 2 - 3 - 0 |
| Los Angeles Rams | 5 | 4 | 0 | 0.556 | 214 | 181 | 33 | 2 - 3 - 0 | 3 - 1 - 0 | 0 - 2 - 0 | 0.000 | 3 - 2 - 0 | 0.600 | 2 - 2 - 0 | 3W | 3 - 2 - 0 |
| Arizona Cardinals | 3 | 6 | 0 | 0.333 | 178 | 255 | -77 | 0 - 3 - 0 | 3 - 3 - 0 | 1 - 3 - 0 | 0.250 | 2 - 5 - 0 | 0.286 | 1 - 1 - 0 | 1L | 2 - 3 - 0 |
