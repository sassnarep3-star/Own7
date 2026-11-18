#!/usr/bin/env python3
"""Week 11 injury-report desk (session arena/3e6166df-own7).

Every published number is derived from one verbatim transcript:

  evidence/injury-report-week11-2026-11-18.md   the injury sections of
                                                https://www.nfl.com/injuries/ as printed
                                                (Week 11, first Wednesday read, 2026-11-18)

and is cross-checked against two other committed artefacts, never typed twice:

  nfl-results/evidence/week-11.schedule.md      official Week 11 schedule transcript
                                                (fixtures, kickoff times, byes)
  nfl-week11-6c72a9fa/data/official-2026-11-18.json   official standings read
                                                (team codes, short names, W-L-T)

The builder pins expected counts (a drift alarm: a changed or truncated transcript fails
the build) and aborts on any contradiction. Blank cells stay blank. Nothing is inferred.
`--check` re-renders in memory and fails if any committed output differs.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence" / "injury-report-week11-2026-11-18.md"
DATA = HERE / "data"
SITE = HERE / "site"
SCHEDULE_EVIDENCE = ROOT / "nfl-results" / "evidence" / "week-11.schedule.md"
OFFICIAL_JSON = ROOT / "nfl-week11-6c72a9fa" / "data" / "official-2026-11-18.json"

READ_ON = "2026-11-18"
WEEK = 11
SITE_TITLE = "OWN7 · Week 11 injury desk"
REPORT_URL = "https://www.nfl.com/injuries/"
SCHEDULE_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"
TERMS_URL = "https://www.nfl.com/legal/terms/"

# Registered source ids (research/sources.json; hosts pinned in scripts/check_site.py).
S_INJ = "W11-NFL-INJ-1118"
S_SCHED = "C672-SCHED-W11-1118"
S_TERMS = "W11-NFL-TERMS-1118"
REG_URLS = {S_INJ: REPORT_URL, S_SCHED: SCHEDULE_URL, S_TERMS: TERMS_URL}

# Pinned expectations for the transcript (drift alarm). Any change must be deliberate.
PINNED = {
    "games": 13,
    "clubs_total": 26,
    "byes": 6,
    "rows_total": 26,
    "rows_by_club": {"IND": 11, "HOU": 15},
    "no_injury_clubs": 24,
    "league_clubs": 32,
}

NO_INJURY = "No Injuries Reported"
TEAM_RE = re.compile(r"^([A-Z]{2,3}) (.+?) \((\d+-\d+(?:-\d+)?)\)$")
SCHED_RE = re.compile(
    r"^- (?P<away>.+?) at (?P<home>.+?), (?P<day>[A-Za-z]+day), (?P<date>[A-Za-z]+ \d+\w*), "
    r"(?P<time>\d{1,2}:\d{2} [AP]M), (?P<net>.+)$"
)

CSV_INJURY_COLS = [
    "read_on", "report_url", "day", "kickoff_et", "network_printed", "game_away", "game_home",
    "club_code", "club_name", "record_printed", "player", "player_page_printed", "position",
    "injuries_printed", "practice_status_printed", "game_status_printed", "evidence_file",
]
CSV_CLUB_COLS = [
    "club_code", "club_name", "game", "record_printed", "record_standings_2026_11_18",
    "record_check", "status_printed", "rows_printed",
]
CSV_SLATE_COLS = [
    "slot", "day", "kickoff_et", "network_printed", "away_code", "away_name", "home_code",
    "home_name", "schedule_check",
]
EVIDENCE_NAME = "evidence/injury-report-week11-2026-11-18.md"


class BuildError(SystemExit):
    pass


def fail(message: str) -> None:
    raise BuildError("FAIL: " + message)


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def standings_record(w: int, l: int, t: int) -> str:
    return f"{w}-{l}" + (f"-{t}" if t else "")


# ---------------------------------------------------------------- parsing

def parse_evidence(text: str) -> dict:
    games: list[dict] = []
    clubs: list[dict] = []
    rows: list[dict] = []
    day = None
    game = None
    club = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## DAY | "):
            # "THURSDAY, NOVEMBER 19TH" -> "Thursday" (the weekday only; the date is cross-checked
            # against the schedule transcript through the matchup/kickoff key, not re-typed here)
            day = line[len("## DAY | "):].split(",")[0].strip().title()
            game = club = None
            continue
        if line.startswith("### GAME | "):
            parts = [p.strip() for p in line[len("### GAME | "):].split("|")]
            if len(parts) != 4:
                fail(f"game heading has {len(parts)} fields: {line}")
            kickoff, network, away_txt, home_txt = parts
            away = TEAM_RE.match(away_txt)
            home = TEAM_RE.match(home_txt)
            if not away or not home:
                fail(f"unparseable team text: {away_txt!r} / {home_txt!r}")
            game = {
                "day": day, "kickoff_et": kickoff, "network_printed": network,
                "away": {"code": away[1], "name": away[2], "record": away[3]},
                "home": {"code": home[1], "name": home[2], "record": home[3]},
                "clubs": [],
            }
            games.append(game)
            club = None
            continue
        if line.startswith("#### CLUB | "):
            if game is None:
                fail("club heading before any game heading")
            parts = [p.strip() for p in line[len("#### CLUB | "):].split("|")]
            if len(parts) != 2:
                fail(f"club heading has {len(parts)} fields: {line}")
            club = {"code": parts[0], "name": parts[1], "game": game, "rows": [], "status": None}
            clubs.append(club)
            game["clubs"].append(club["code"])
            continue
        if club is None:
            continue
        if line.strip() == NO_INJURY:
            if club["status"] is not None:
                fail(f"duplicate status line for {club['code']}")
            club["status"] = NO_INJURY
            continue
        if line.startswith("| ") and not line.startswith("| Player |") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 6:
                fail(f"row for {club['code']} has {len(cells)} cells, expected 6: {line}")
            player, position, injuries, practice, game_status, page = cells
            if not player or not position or not practice:
                fail(f"required cell empty in row for {club['code']}: {line}")
            if not page.startswith("https://www.nfl.com/players/"):
                fail(f"player link not an NFL player page: {page}")
            row = {
                "day": day, "kickoff_et": game["kickoff_et"],
                "network_printed": game["network_printed"],
                "game_away": game["away"]["code"], "game_home": game["home"]["code"],
                "club_code": club["code"], "club_name": club["name"],
                "record_printed": (game["away"] if game["away"]["code"] == club["code"] else game["home"])["record"],
                "player": player, "player_page_printed": page, "position": position,
                "injuries_printed": injuries, "practice_status_printed": practice,
                "game_status_printed": game_status,
            }
            club["rows"].append(row)
            rows.append(row)
    return {"games": games, "clubs": clubs, "rows": rows}


def parse_schedule(text: str) -> dict:
    fixtures, byes, section = [], [], None
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section and section.startswith("Scheduled"):
            m = SCHED_RE.match(line)
            if m:
                fixtures.append(m.groupdict())
        if section and section.startswith("Teams on Bye"):
            m = re.match(r"^([A-Z]{2,3}) (.+?) (\d+-\d+(?:-\d+)?)$", line.strip())
            if m:
                byes.append({"code": m[1], "name": m[2], "record": m[3]})
    return {"fixtures": fixtures, "byes": byes}


def load_standings() -> dict:
    data = json.loads(OFFICIAL_JSON.read_text(encoding="utf-8"))
    by_code = {}
    for team in data["standings"]:
        by_code[team["code"]] = team
    return by_code


# ---------------------------------------------------------------- derivation

def derive(evidence_text: str, schedule_text: str) -> dict:
    ev = parse_evidence(evidence_text)
    sched = parse_schedule(schedule_text)
    standings = load_standings()
    checks: list[dict] = []

    def check(cid: str, description: str, expected, observed) -> None:
        ok = expected == observed
        checks.append({"id": cid, "check": description, "expected": expected,
                       "observed": observed, "result": "pass" if ok else "FAIL"})
        if not ok:
            fail(f"{cid} {description}: expected {expected!r}, observed {observed!r}")

    # Structure and pinned counts (drift alarm).
    check("W1", "Week 11 games printed", PINNED["games"], len(ev["games"]))
    club_codes = [c["code"] for c in ev["clubs"]]
    check("W2", "clubs printed (26 = 13 games x 2)", PINNED["clubs_total"], len(club_codes))
    check("W3", "clubs are unique", len(club_codes), len(set(club_codes)))
    check("W4", "every game lists exactly two clubs",
          [2] * PINNED["games"], [len(g["clubs"]) for g in ev["games"]])
    rows_by_club = {}
    for c in ev["clubs"]:
        if c["rows"]:
            rows_by_club[c["code"]] = len(c["rows"])
    check("W5", "printed injury rows per club (only IND and HOU carry rows)",
          PINNED["rows_by_club"], rows_by_club)
    check("W6", "total printed injury rows", PINNED["rows_total"], len(ev["rows"]))
    no_inj = [c["code"] for c in ev["clubs"] if c["status"] == NO_INJURY]
    check("W7", "clubs printed 'No Injuries Reported'", PINNED["no_injury_clubs"], len(no_inj))
    check("W8", "every club has either rows or the no-injury line, never both or neither",
          len(ev["clubs"]),
          sum(1 for c in ev["clubs"] if bool(c["rows"]) != (c["status"] == NO_INJURY)))
    # Blank-cell facts as printed (recorded, never filled).
    check("W9", "Game Status cells printed blank (rows)", len(ev["rows"]),
          sum(1 for r in ev["rows"] if r["game_status_printed"] == ""))
    check("W10", "Injuries (body part) cells printed blank (rows)", len(ev["rows"]),
          sum(1 for r in ev["rows"] if r["injuries_printed"] == ""))

    # League coverage: 26 playing clubs + 6 byes = 32 clubs, no overlap.
    bye_codes = [b["code"] for b in sched["byes"]]
    check("W11", "byes in the official schedule transcript", PINNED["byes"], len(bye_codes))
    all_codes = set(standings)
    check("W12", "official standings cover 32 clubs", PINNED["league_clubs"], len(all_codes))
    check("W13", "playing clubs + byes partition the 32 clubs", True,
          set(club_codes) | set(bye_codes) == all_codes and not (set(club_codes) & set(bye_codes)))

    # Schedule cross-check: same 13 matchups, same kickoff time, same day.
    sched_keys = sorted((f["away"], f["home"], f["day"], f["time"]) for f in sched["fixtures"])
    printed_keys = []
    for g in ev["games"]:
        away_short = g["away"]["name"]
        home_short = g["home"]["name"]
        printed_keys.append((away_short, home_short, g["day"].title(),
                             g["kickoff_et"].replace(" EST", "")))
    printed_keys.sort()
    check("W14", "fixtures match the official schedule transcript (matchup, day, kickoff)",
          sched_keys, printed_keys)

    # Standings cross-check: each printed record equals the official standings read.
    mismatches = []
    for c in ev["clubs"]:
        st = standings.get(c["code"])
        expected = standings_record(st["W"], st["L"], st["T"]) if st else None
        printed = c["game"]["away"]["record"] if c["game"]["away"]["code"] == c["code"] else c["game"]["home"]["record"]
        if expected != printed:
            mismatches.append((c["code"], printed, expected))
    check("W15", "printed team records equal the official standings read (26 clubs)", [], mismatches)

    # Name and code consistency between the schedule and the standings.
    names_ok = all(standings[c["code"]]["club_short"] == c["name"] for c in ev["clubs"])
    check("W16", "printed club short names equal the official standings short names", True, names_ok)

    return {"ev": ev, "sched": sched, "standings": standings, "checks": checks}


# ---------------------------------------------------------------- CSV outputs

def csv_text(columns: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in columns})
    return buf.getvalue()


def build_tables(d: dict) -> dict[str, str]:
    ev, standings = d["ev"], d["standings"]
    injury_rows = []
    for r in ev["rows"]:
        out = dict(r)
        out.update({"read_on": READ_ON, "report_url": REPORT_URL, "evidence_file": EVIDENCE_NAME,
                    "game_away": r["game_away"], "game_home": r["game_home"]})
        injury_rows.append(out)
    club_rows = []
    for c in ev["clubs"]:
        g = c["game"]
        printed = g["away"]["record"] if g["away"]["code"] == c["code"] else g["home"]["record"]
        st = standings[c["code"]]
        expected = standings_record(st["W"], st["L"], st["T"])
        club_rows.append({
            "club_code": c["code"], "club_name": c["name"],
            "game": f"{g['away']['code']} at {g['home']['code']}",
            "record_printed": printed, "record_standings_2026_11_18": expected,
            "record_check": "match" if printed == expected else "MISMATCH",
            "status_printed": c["status"] or "", "rows_printed": len(c["rows"]),
        })
    slate_rows = []
    for i, g in enumerate(ev["games"], start=1):
        sched_match = next((f for f in d["sched"]["fixtures"]
                            if f["away"] == g["away"]["name"] and f["home"] == g["home"]["name"]), None)
        slate_rows.append({
            "slot": i, "day": g["day"].title(), "kickoff_et": g["kickoff_et"],
            "network_printed": g["network_printed"],
            "away_code": g["away"]["code"], "away_name": g["away"]["name"],
            "home_code": g["home"]["code"], "home_name": g["home"]["name"],
            "schedule_check": "match" if sched_match else "MISSING",
        })
    return {
        "injuries-week11.csv": csv_text(CSV_INJURY_COLS, injury_rows),
        "clubs-week11.csv": csv_text(CSV_CLUB_COLS, club_rows),
        "slate-week11.csv": csv_text(CSV_SLATE_COLS, slate_rows),
    }


# ---------------------------------------------------------------- HTML

PAGES = [
    ("index.html", "Overview"),
    ("injuries.html", "Injury rows"),
    ("slate.html", "Slate and byes"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

FLAGS = [
    ("W11-F01", "Game Status is blank for all 26 printed rows",
     "On the 2026-11-18 read every Game Status cell in the Week 11 tables is empty. The cells are "
     "left blank here. Nothing is inferred from the practice column. Re-read on a later day to see "
     "whether the cells populate.", "medium", "open"),
    ("W11-F02", "The Injuries (body part) column is blank for all 26 printed rows",
     "The page prints the column header, but no body-part text appears in any Week 11 row on this "
     "read. The Week 10 tables captured on 2026-11-18 by the fresh-reads desk carry body-part text (for example 'Knee', 'Ankle'). Whether this is "
     "the publisher's content or a rendering loss cannot be decided from one read. Left blank; "
     "flagged.", "medium", "open"),
    ("W11-F03", "The injury report does not list players on injured reserve",
     "Malik Willis is not in this report. The same page's news list carries the headline 'Dolphins "
     "place QB Malik Willis (groin) on injured reserve' (quoted in the evidence file, not as injury "
     "data). Absence from the report is therefore not availability. The reserve-list gate remains "
     "open (register DR-64).", "high", "explained"),
    ("W11-F04", "The earlier partial read (FF01, 2026-11-18 04:06Z) is superseded",
     "The fresh-reads desk recorded that the hub still served Week 10 at 04:06Z. This read, at about "
     "06:20 to 06:24Z, serves the Week 11 report. The earlier flag is kept as recorded; it is not "
     "edited.", "low", "explained"),
    ("W11-F05", "One read only; no Wednesday-to-kickoff series exists",
     "This is a single first-Wednesday read. No Thursday or Friday capture was made. NFL.com section "
     "1.3 (read verbatim on 2026-11-18) prohibits systematic retrieval to compile a collection without "
     "written consent, so scheduled captures are not run. The delta and designation-trend questions "
     "(DR-54, DR-55) stay blocked.", "high", "open"),
    ("W11-F06", "'No Injuries Reported' is the printed status, not a health claim",
     "Twenty-four clubs print 'No Injuries Reported' on this read. The line describes what the report "
     "lists. It does not describe reserve players, or players who are absent for reasons the report "
     "does not print.", "medium", "explained"),
    ("W11-F07", "One network label differs from the schedule transcript",
     "The injury page prints 'NBC, UNIVERSO' for Vikings at 49ers. The official schedule transcript "
     "prints 'NBC' for the same game. Both are recorded as printed. Kickoff, date and matchup agree.",
     "low", "explained"),
]


def link(source_id: str, label: str = "official page ↗") -> str:
    return (f'<a href="{esc(REG_URLS[source_id])}" rel="noopener noreferrer" target="_blank">'
            f"{esc(label)}</a>")


def cell(value: str) -> str:
    if value == "" or value is None:
        return '<td data-empty="true"></td>'
    return f"<td>{esc(value)}</td>"


def table(caption: str, head: list[str], rows_html: list[str], note: str | None = None) -> str:
    thead = "".join(f'<th scope="col">{esc(h)}</th>' for h in head)
    note_html = f'<p class="note">{esc(note)}</p>' if note else ""
    return (f'<div class="table-wrap"><table><caption>{esc(caption)}</caption>'
            f'<thead><tr>{thead}</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>'
            f"{note_html}")


def row(cells_html: list[str], source_id: str) -> str:
    return f'<tr data-source-ids="{source_id}">{"".join(cells_html)}</tr>'


def badge(state: str) -> str:
    cls = {"open": "badge-warn", "explained": "badge-ok", "resolved": "badge-ok"}.get(state, "badge-warn")
    return f'<span class="badge {cls}">{esc(state)}</span>'


def page_index(d: dict, t: dict) -> str:
    ev = d["ev"]
    games = len(ev["games"])
    clubs = len(ev["clubs"])
    rows = len(ev["rows"])
    no_inj = sum(1 for c in ev["clubs"] if c["status"] == NO_INJURY)
    kpis = [
        (str(games), "Week 11 games", "Thu 19 Nov to Mon 23 Nov, as printed"),
        (str(clubs), "clubs on the report", f"{32 - clubs} byes, from the schedule transcript"),
        (str(rows), "printed injury rows", "IND 11 and HOU 15 only"),
        (str(no_inj), "clubs printed 'No Injuries Reported'", "as printed at read time"),
        ("0", "delta vs a prior Week 11 read", "none exists: this is the first Wednesday read"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><span class="kpi-value">{esc(v)}</span><span class="kpi-label">{esc(l)}</span>'
        f'<span class="sub">{esc(s)}</span></div>' for v, l, s in kpis)
    return f"""
<p class="eyebrow">Week 11 · first Wednesday read · {READ_ON}</p>
<h1>Week 11 injury report — what the official page printed</h1>
<p class="lead">One read of the official NFL injury report, taken on Wednesday 18 November 2026
(about 06:20 to 06:24 UTC). Every number below is derived from the verbatim transcript in this
desk, checked against the official schedule and standings reads, and linked to the official page.
Blank cells are blank as printed. Nothing is inferred.</p>
<div class="kpis">{kpi_html}</div>
<h2>How to read this desk</h2>
<div class="panel">
<ul>
<li><strong>Injury rows</strong> are the players the report lists, with practice status as printed.
Two of the 26 clubs carry rows; 24 print 'No Injuries Reported'.</li>
<li><strong>Game status is blank</strong> on every printed row. It is not filled from the practice column.
See flag W11-F01.</li>
<li><strong>Absent is not available.</strong> The report does not list players on injured reserve.
See flag W11-F03, and the register gate DR-64.</li>
<li><strong>One read.</strong> A timestamped daily series needs repeated captures. The NFL.com terms
section 1.3 prohibits systematic retrieval to compile a collection without written consent, so no
series is run here (flag W11-F05, register DR-54 stays Blocked).</li>
</ul>
</div>
<h2>Verification performed</h2>
<div class="panel">
<ul>
<li>{len(t['checks'])} checks, all passing (see <a href="sources.html">Sources</a>). The printed counts
are pinned, so a changed or truncated transcript fails the build.</li>
<li>All 13 fixtures match the official Week 11 schedule transcript on matchup, day and kickoff.</li>
<li>All 26 printed team records match the official standings read taken on 2026-11-18.</li>
<li>Together with the 6 bye clubs, the 26 playing clubs partition the 32 clubs.</li>
</ul>
</div>
<h2>Pages</h2>
<div class="panel"><ul>
<li><a href="injuries.html">Injury rows</a>: the 26 printed rows, each linked to the official report.</li>
<li><a href="slate.html">Slate and byes</a>: 13 games with the printed status of each club, and the 6 byes.</li>
<li><a href="flagged.html">Flagged for review</a>: seven items, with the links needed to check them.</li>
<li><a href="sources.html">Sources</a>: registered official sources, read dates and evidence hashes.</li>
</ul></div>
"""


def page_injuries(d: dict) -> str:
    rows_html = []
    for r in d["ev"]["rows"]:
        cells = [
            f'<td><a href="{esc(r["player_page_printed"])}" rel="noopener noreferrer" target="_blank">'
            f'{esc(r["player"])}</a></td>',
            cell(r["club_code"]),
            cell(r["position"]),
            cell(r["injuries_printed"]),
            cell(r["practice_status_printed"]),
            cell(r["game_status_printed"]),
            cell(f'{r["game_away"]} at {r["game_home"]}'),
            f'<td>{link(S_INJ)}</td>',
        ]
        rows_html.append(row(cells, S_INJ))
    head = ["Player (NFL player page)", "Club", "Position", "Injuries (printed)",
            "Practice status (printed)", "Game status (printed)", "Game", "Source"]
    return f"""
<p class="eyebrow">Week 11 · 26 printed rows</p>
<h1>Injury rows, as printed</h1>
<p class="lead">Every row the Week 11 report lists, in page order. The player name links to the
player page printed on the report. The Source column links to the official report. Blank
cells are blank on the printed page; see flags W11-F01 and W11-F02.</p>
{table("Week 11 injury report rows, 2026-11-18 read (IND and HOU only)", head, rows_html,
       "Rows for Indianapolis (11) and Houston (15). The remaining 24 clubs print 'No Injuries Reported' (slate page).")}
"""


def page_slate(d: dict) -> str:
    ev = d["ev"]
    rows_html = []
    for i, g in enumerate(ev["games"], start=1):
        for side in ("away", "home"):
            club_code = g[side]["code"]
            club = next(c for c in ev["clubs"] if c["code"] == club_code)
            status = NO_INJURY if club["status"] == NO_INJURY else f'{len(club["rows"])} rows printed'
            cells = [
                cell(str(i)),
                cell(g["day"].title()),
                cell(g["kickoff_et"]),
                cell(g["network_printed"]),
                cell(f'{g["away"]["code"]} {g["away"]["name"]} at {g["home"]["code"]} {g["home"]["name"]}'),
                cell(f"{club_code} {club['name']} ({g[side]['record']})"),
                cell(status),
                f'<td>{link(S_SCHED)}</td>',
            ]
            rows_html.append(row(cells, S_SCHED))
    head = ["Slot", "Day", "Kickoff (ET, as printed)", "Network (as printed)", "Matchup",
            "Club (printed record)", "Injury report line", "Source"]
    byes = d["sched"]["byes"]
    bye_html = []
    for b in byes:
        bye_html.append(row([cell(b["code"]), cell(b["name"]), cell(b["record"]),
                             f'<td>{link(S_SCHED)}</td>'], S_SCHED))
    return f"""
<p class="eyebrow">Week 11 · 13 games · 6 byes</p>
<h1>Slate and byes</h1>
<p class="lead">The 13 Week 11 games, each club with the status the injury report printed for it.
The fixtures match the official Week 11 schedule transcript on matchup, day and kickoff. The byes
are the six clubs with no Week 11 game.</p>
{table("Week 11 games and printed injury status, each club", head, rows_html,
       "'Injury report line' is the report's own text: 'No Injuries Reported', or the number of printed rows.")}
{table("Week 11 bye clubs (as printed on the official schedule)", ["Code", "Club", "Record", "Source"], bye_html,
       "Byes are not games. They carry no injury rows on this report.")}
"""


def page_flagged(d: dict) -> str:
    rows_html = []
    for fid, title, body, sev, state in FLAGS:
        cells = [cell(fid), cell(title), cell(body), cell(sev), f"<td>{badge(state)}</td>",
                 f'<td>{link(S_INJ)}</td>']
        rows_html.append(row(cells, S_INJ))
    head = ["Flag", "Irregularity", "What was found and what is left blank", "Severity", "State", "Source"]
    return f"""
<p class="eyebrow">Non-blocking · for review</p>
<h1>Flagged for review</h1>
<p class="lead">Irregularities found while reading the Week 11 report. None blocks the desk. Each
item says what was found, what was left blank, and which official page to check.</p>
{table("Flags W11-F01 to W11-F07", head, rows_html)}
"""


def page_sources(d: dict, hashes: dict) -> str:
    srcs = [
        (S_INJ, "NFL.com · Official NFL injury report, Week 11 2026",
         "Read 2026-11-18, about 06:20 to 06:24 UTC. Chunks 0 to 2 of 3 read in full. Rendered text.",
         "evidence/injury-report-week11-2026-11-18.md", hashes["evidence"]),
        (S_SCHED, "NFL.com · Week 11 schedule (by-week page)",
         "Read on 2026-11-18 by the fresh-reads desk; used only for the 13-fixture and 6-bye cross-check.",
         "nfl-results/evidence/week-11.schedule.md", hashes["schedule"]),
        (S_TERMS, "NFL.com · Terms and Conditions (updated May 16, 2024)",
         "Section 1.3 read verbatim on 2026-11-18 (chunk 0 of 9). It prohibits systematic retrieval to compile a collection without express prior written consent.",
         "not retained (quoted in this page)", "—"),
    ]
    rows_html = []
    for sid, title, scope, file_name, digest in srcs:
        cells = [cell(title), cell(scope), cell(file_name), cell(digest), f'<td>{link(sid)}</td>']
        rows_html.append(row(cells, sid))
    head = ["Source", "What was read", "Retained evidence", "SHA-256", "Official link"]
    return f"""
<p class="eyebrow">Registered official sources</p>
<h1>Sources and evidence hashes</h1>
<p class="lead">Each source is registered in research/sources.json with its read date and access
boundary. The hashes let a reviewer confirm that the retained transcript has not changed.</p>
{table("Official sources used on this desk", head, rows_html)}
<h2>Gates these reads bear on</h2>
<div class="panel"><ul>
<li><strong>DR-54</strong> (Wed/Thu/Fri dated history): still Blocked. The terms gate (section 1.3,
verified on {READ_ON}) prohibits systematic retrieval, and no scheduled capture is run.</li>
<li><strong>DR-64</strong> (reserve list): still Open on the register. This report does not list reserve players.</li>
<li><strong>DR-53 and DR-55</strong> (designation reliability, timestamped series): this read adds one
Wednesday row set. It is not a series and is not used as a designation-reliability sample.</li>
</ul></div>
"""


def render(name: str, title: str, body: str, eyebrow: str) -> str:
    nav = "".join(
        f'<a href="{n}"{" aria-current=" + chr(34) + "page" + chr(34) if n == name else ""}>{esc(label)}</a>'
        for n, label in PAGES)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {SITE_TITLE}</title>
<meta name="description" content="Week 11 NFL injury report, first Wednesday read (2026-11-18): every printed row, the slate, flags and sources, each linked to the official page.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="brand"><strong>{SITE_TITLE}</strong><span>{esc(eyebrow)}</span></div><nav aria-label="Desk pages">{nav}<a href="../../index.html">← NFL workspace</a></nav></header>
<main id="main">{body}</main>
<footer>NFL.com is the source of every injury value on these pages. Not affiliated with or endorsed by the NFL.
Generated deterministically by nfl-w11-injuries-3e61/build.py from the committed evidence on {READ_ON}.</footer>
</body>
</html>
"""


PAGE_META = {
    "index.html": ("Overview", "Week 11 · first Wednesday read"),
    "injuries.html": ("Injury rows", "Week 11 · 26 printed rows"),
    "slate.html": ("Slate and byes", "Week 11 · 13 games · 6 byes"),
    "flagged.html": ("Flagged for review", "Non-blocking · for review"),
    "sources.html": ("Sources", "Registered official sources"),
}


def build_outputs() -> tuple[dict[str, str], dict]:
    evidence_text = EVIDENCE.read_text(encoding="utf-8")
    schedule_text = SCHEDULE_EVIDENCE.read_text(encoding="utf-8")
    d = derive(evidence_text, schedule_text)
    t = {"checks": d["checks"]}
    hashes = {"evidence": hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(),
              "schedule": hashlib.sha256(SCHEDULE_EVIDENCE.read_bytes()).hexdigest()}
    tables = build_tables(d)
    bodies = {
        "index.html": page_index(d, t),
        "injuries.html": page_injuries(d),
        "slate.html": page_slate(d),
        "flagged.html": page_flagged(d),
        "sources.html": page_sources(d, hashes),
    }
    outputs = {}
    for name, body in bodies.items():
        title, eyebrow = PAGE_META[name]
        outputs[name] = render(name, title, body, eyebrow)
    checks_json = json.dumps({"desk": "nfl-w11-injuries-3e61", "read_on": READ_ON,
                              "report_url": REPORT_URL, "evidence_file": EVIDENCE_NAME,
                              "evidence_sha256": hashes["evidence"],
                              "schedule_evidence_sha256": hashes["schedule"],
                              "checks": d["checks"]}, indent=1) + "\n"
    manifest = {
        "desk": "nfl-w11-injuries-3e61", "session": "arena/3e6166df-own7", "read_on": READ_ON,
        "pages": [n for n, _ in PAGES] + ["style.css"],
        "evidence_sha256": hashes["evidence"],
        "source_ids": sorted(REG_URLS),
    }
    files = {}
    files.update({f"data/{k}": v for k, v in tables.items()})
    files["data/checks.json"] = checks_json
    files.update({f"site/{k}": v for k, v in outputs.items()})
    files["site/manifest.json"] = json.dumps(manifest, indent=1) + "\n"
    return files, d


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    files, _ = build_outputs()
    if arg == "--check":
        stale = []
        for rel, content in files.items():
            path = HERE / rel
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(rel)
        style_src = ROOT / "nfl-fresh-1118" / "site" / "style.css"
        if not (SITE / "style.css").exists() or (SITE / "style.css").read_bytes() != style_src.read_bytes():
            stale.append("site/style.css")
        if stale:
            fail("stale desk outputs: " + ", ".join(stale))
        n_checks = len(json.loads(files["data/checks.json"])["checks"])
        print(f"OK: nfl-w11-injuries-3e61 reproduces byte-identically "
              f"({len(files)} generated files, 5 pages, 26 rows, {n_checks} checks).")
        return 0
    for rel, content in files.items():
        path = HERE / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    style_src = ROOT / "nfl-fresh-1118" / "site" / "style.css"
    (SITE / "style.css").write_bytes(style_src.read_bytes())
    print(f"Built {len(files)} files: 5 pages, 3 CSV tables, checks.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
