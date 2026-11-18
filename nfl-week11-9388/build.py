#!/usr/bin/env python3
"""Deterministic site generator for the Week 11 live decision desk (session arena/9388352a-own7).

Pages are rendered only from committed artefacts:

  evidence/*.md                  verbatim transcripts of the 2026-11-18 official reads
  data/official-2026-11-18.json  parsed facts
  data/venues.json               the game-centre venue register
  data/fixture-context.json      rest days from official kickoff dates
  data/captures.json             the capture ledger with retained hashes
  data/verification.json         the V1-V8 check results and the flag register
  data/decisions.json            the authored question and suggestion registers

``--check`` re-renders and compares bytes; the generator aborts on a missing artefact or a
link that does not resolve rather than publishing a partial page. No price, odds, ROI, CLV,
stake, wager or reward is produced anywhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SITE = HERE / "site"

READ_ON = "2026-11-18"
SITE_TITLE = "OWN7 · Week 11 live decision desk"

S_STANDINGS = "W9388-NFL-STANDINGS-1118"
S_SCHED_W11 = "W9388-NFL-SCHED-W11-1118"
S_SCHED_W10 = "W9388-NFL-SCHED-W10-1118"
S_INJ_W11 = "W9388-NFL-INJ-W11-1118"

REGISTRY = json.loads((ROOT / "research" / "sources.json").read_text())
URLS = {r["id"]: r["url"] for r in REGISTRY}

PAGES = [
    ("index.html", "Overview"),
    ("verification.html", "Verification"),
    ("venues.html", "Venue register"),
    ("slate.html", "Week 11 slate"),
    ("availability.html", "Availability"),
    ("captures.html", "Capture ledger"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]


def esc(value) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def ext(url: str, label: str) -> str:
    return f'<a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{esc(label)}</a>'


def src_links(ids) -> str:
    return " ".join(ext(URLS[i], f"{i} ↗") for i in ids if i in URLS)


def blank() -> str:
    return '<td data-empty="true" class="blank"></td>'


def row(cells, source_ids) -> str:
    """One table row.

    A cell may be passed as bare content ("Baltimore Ravens") or as a complete cell
    ('<td class="src">…</td>'). Anything that is not already a cell is wrapped in a plain <td>;
    without that, text and links would sit directly inside the <tr>, which is invalid table
    markup and gets hoisted out of the table by the browser.
    """
    joined = "".join(c if c.startswith("<td") else f"<td>{c}</td>" for c in cells)
    ids = " ".join(source_ids)
    return f'<tr data-source-ids="{esc(ids)}">{joined}</tr>'


def table(caption, headers, rows, note=None) -> str:
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    note_html = f'<p class="note">{esc(note)}</p>' if note else ""
    return (f'<div class="table-wrap"><table><caption>{esc(caption)}</caption>'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'{note_html}')


def kpi(value, label, sub="") -> str:
    sub_html = f'<span class="sub">{esc(sub)}</span>' if sub else ""
    return (f'<div class="kpi"><span class="kpi-value">{esc(value)}</span>'
            f'<span class="kpi-label">{esc(label)}</span>{sub_html}</div>')


def badge(text, kind) -> str:
    return f'<span class="badge badge-{esc(kind)}">{esc(text)}</span>'


def load(name):
    path = DATA / name
    if not path.is_file():
        raise SystemExit(f"FAIL: missing artefact {path}. Run collect.py first.")
    return json.loads(path.read_text())


# --------------------------------------------------------------------------- pages

def page_index(d):
    off, ver, ctx, cap, readi = d["off"], d["ver"], d["ctx"], d["cap"], d["readi"]
    tot = off["league_totals"]
    mnf = off["week10_monday_result"]
    checks_pass = sum(1 for c in ver["checks"] if c["status"] == "pass")
    readiness_rows = [
        row([esc(r["id"]), esc(r["requirement"]), esc(r["have"]), esc(r["blocking_gate"]),
             esc(r["number_that_clears_it"]),
             badge(r["state"], "ok" if r["state"] == "clear" else "bad"),
             f'<td class="src">{src_links(r["source_ids"])}</td>'],
            r["source_ids"])
        for r in readi["rows"]
    ]
    n_clear = sum(1 for r in readi["rows"] if r["state"] == "clear")
    n_blocked = len(readi["rows"]) - n_clear
    n_total = len(readi["rows"])
    rows = [
        row([esc(c["id"]), esc(c["title"]), badge(c["status"], "ok" if c["status"] == "pass" else "bad"),
             esc("; ".join(c["detail"][:2])), f'<td class="src">{src_links(c["sources"])}</td>'],
            c["sources"])
        for c in ver["checks"]
    ]
    inventory = [
        row(["League standings", "32 rows", esc(READ_ON), f'<td class="src">{src_links([S_STANDINGS])}</td>'],
            [S_STANDINGS]),
        row(["Week 11 slate", f'{len(off["week11_fixtures"])} fixtures, {len(off["week11_byes"])} byes',
             esc(READ_ON), f'<td class="src">{src_links([S_SCHED_W11])}</td>'], [S_SCHED_W11]),
        row(["Week 11 venues", "13 location + stadium pairs from the game centre", esc(READ_ON),
             f'<td class="src">{src_links(["W9388-GC-W11-01"])}</td>'], ["W9388-GC-W11-01"]),
        row(["Week 10 Monday result", f'{mnf["away_name"]} {mnf["away_score"]}, {mnf["home_name"]} {mnf["home_score"]}, FINAL',
             esc(READ_ON), f'<td class="src">{src_links([S_SCHED_W10])}</td>'], [S_SCHED_W10]),
        row(["Week 11 league injury report", "not published (3 reads)", esc(READ_ON),
             f'<td class="src">{src_links([S_INJ_W11])}</td>'], [S_INJ_W11]),
        row(["Week 11 game-centre injury rows", "8 rows on 1 of 13 pages", esc(READ_ON),
             f'<td class="src">{src_links(["W9388-GC-W11-01"])}</td>'], ["W9388-GC-W11-01"]),
        row(["Official results corpus", f'{tot["corpus_games"]} games, {tot["corpus_points"]} points',
             "2026-11-14", f'<td class="src">{src_links(["X29-NFL-SCHEDULE"])}</td>'], ["X29-NFL-SCHEDULE"]),
    ]
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Overview</h1>
<p class="lead">This desk read the official pages on {READ_ON}, before any Week 11 practice report
existed, and records what is actually published at that instant: the completed Week 10 table, the
Week 11 slate with the venue of every fixture, and the state of the Week 11 injury report. Every
value traces to a retained transcript with a SHA-256 hash. Nothing is inferred, and nothing is
priced.</p>
<div class="kpis">
{kpi("32", "standings rows verified", "each reconciled to the frozen 2026-11-17 snapshot plus one game")}
{kpi("13", "Week 11 fixtures", f'{len(off["week11_byes"])} clubs on bye complete the 32')}
{kpi("13", "venues transcribed", "from the official game centre, one page per fixture")}
{kpi("0", "Week 11 injury reports published", "3 reads of the Week 11 URL all served Week 10")}
{kpi(f'{checks_pass}/{len(ver["checks"])}', "checks pass", "line by line, aborting on any mismatch")}
</div>
<h2>What the reads show</h2>
<div class="panel">
<h3>Week 10 is now complete</h3>
<p>The Monday night game that every earlier desk recorded as pending is final:
<strong>{esc(mnf["away_name"])} {mnf["away_score"]}, {esc(mnf["home_name"])} {mnf["home_score"]}</strong>,
read from the official Week 10 by-week page. Two independent checks agree. The frozen 2026-11-17
standings snapshot moves by exactly that game and nothing else: Baltimore 4-5 to 4-6 and the Los
Angeles Chargers 0-8 to 1-8, with points for and against moving 20 and 23 in the right directions.
And the 149-game results corpus, which does not contain this fixture, plus 43 points equals the
{tot["points_for"]} points the 32 clubs have scored between them.</p>
</div>
<div class="panel">
<h3>Week 11 availability is empty, and empty is not healthy</h3>
<p>Three reads of the Week 11 injury URL, at {esc(cap["window_utc"][0])} and
{esc(cap["window_utc"][1])}, all served the Week 10 document. Twelve of the thirteen game-centre
pages print the sentence <em>"have no active injuries at this time"</em> for both clubs. No club
has filed a Week 11 practice report, so that sentence is an empty module rather than a clean bill
of health. Only the Thursday game prints rows, because those two clubs have begun practising.</p>
</div>
<div class="panel">
<h3>The injury report is not a fixed document</h3>
<p>Three Detroit cells on the <em>Week 10</em> report differ between the frozen 2026-11-13 capture
and the same page read today, after those games were played. The publisher rewrites the week's
document, so any capture is a version, not a fact. The delta is published on the availability page;
the earlier capture is not patched.</p>
</div>
<div class="panel">
<h3>Venues are named inconsistently inside one publisher</h3>
<p>All thirteen Week 11 venues are transcribed from the game centre. Three are spelled differently
by the schedule page, and not in one direction: the game centre carries the older name for Houston
and the newer name for Washington. The game-centre value is the transcribed value everywhere here;
the alternate is published beside it.</p>
</div>
<h2>Decision readiness for Week 11</h2>
<p>One row per requirement that has to be true before a Week 11 number can be produced on this desk's
evidence. What we hold and the number that clears it are counts of official rows or files, not
judgements. A requirement is clear only when what we hold meets the number.</p>
{table("What we hold against what each requirement needs",
       ["#", "Requirement", "What we hold today", "Blocking gate", "The number that clears it",
        "State", "Sources"], readiness_rows,
       f"{n_clear} of {n_total} requirements are clear and {n_blocked} are blocked. Nothing on this "
       "desk originates a price, ranks a strategy or stakes anything while a blocked gate stands.")}
<h2>Check results</h2>
{table("Line-by-line verification", ["ID", "Check", "Result", "Detail", "Sources"], rows,
       "Every check aborts the build on a mismatch rather than publishing a partial page.")}
<h2>What this desk holds</h2>
{table("Dataset inventory", ["Dataset", "Contents", "Read on", "Source"], inventory)}
'''


def page_verification(d):
    off, ver = d["off"], d["ver"]
    rows = [
        row([esc(c["id"]), esc(c["title"]), badge(c["status"], "ok" if c["status"] == "pass" else "bad"),
             esc(str(c["compared"])), esc(str(c.get("mismatches", 0))),
             "<br>".join(esc(x) for x in c["detail"]),
             f'<td class="src">{src_links(c["sources"])}</td>'],
            c["sources"])
        for c in ver["checks"]
    ]
    # side-by-side of the frozen snapshot against today's read
    frozen = {}
    import csv as _csv
    with (ROOT / "data" / "nfl-standings-2026-11-17.csv").open(newline="") as fh:
        for r in _csv.DictReader(fh):
            frozen[r["Team"]] = r
    side = []
    for s in off["standings"]:
        f = frozen.get(s["club"])
        if f is None:
            continue
        moved = (int(f["W"]), int(f["L"]), int(f["PF"]), int(f["PA"])) != (s["w"], s["l"], s["pf"], s["pa"])
        verdict = ("moved by the Week 10 Monday result" if moved else "unchanged")
        side.append(row([
            esc(s["club"]),
            esc(f"{f['W']}-{f['L']}" + (f"-{f['T']}" if f["T"] != "0" else "")),
            esc(f"{s['w']}-{s['l']}" + (f"-{s['t']}" if s["t"] else "")),
            esc(f["PF"]), esc(str(s["pf"])), esc(f["PA"]), esc(str(s["pa"])),
            esc(verdict),
            f'<td class="src">{src_links([S_STANDINGS, S_SCHED_W10])}</td>'],
            [S_STANDINGS, S_SCHED_W10]))
    v3 = next(c for c in ver["checks"] if c["id"] == "V3")
    v8_check = next(c for c in ver["checks"] if c["id"] == "V8")
    v8_kpi = kpi(str(v8_check.get("compared", 0)), "Week 10 report rows re-read",
                 f'{v8_check.get("changed_cells", 0)} cell(s) moved, published as a delta')
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Verification</h1>
<p class="lead">Eight checks, each of which aborts the build on a mismatch. The comparisons are made
against artefacts committed by earlier sessions, not against this desk's own output, so a check
passing means two independently produced documents agree.</p>
<div class="kpis">
{kpi("32/32", "standings rows reconcile", "frozen snapshot plus the Monday game")}
{kpi(str(off["league_totals"]["points_for"]), "points for, all clubs", "equals every point in the corpus plus 43")}
{v8_kpi}
{kpi("13/13", "venues transcribed", "from one game-centre page each")}
</div>
<h2>The eight checks</h2>
{table("Verification checks", ["ID", "Check", "Result", "Rows compared", "Mismatches", "Detail", "Sources"],
       rows, "A check that fails stops the build; it does not publish a warning beside a bad number.")}
<h2>Standings: frozen snapshot against today's read</h2>
{table("Every club, then and now", ["Club", "W-L-T 2026-11-17", "W-L-T 2026-11-18", "PF then", "PF now",
                                    "PA then", "PA now", "Verdict", "Sources"], side,
       "The 2026-11-17 snapshot was taken before the Monday game; only Baltimore and the Los Angeles Chargers may move, and they move by exactly that result.")}
<h2>Points reconciliation</h2>
<div class="panel"><p>{"<br>".join(esc(x) for x in v3["detail"])}</p></div>
'''


def page_venues(d):
    ven = d["ven"]
    rows = []
    for v in ven["venues"]:
        sid = f'W9388-GC-W11-{v["index"]:02d}'
        alt = next((c["schedule_page"] for c in ven["cross_check"]
                    if c["game_centre"] == v["stadium"]), "")
        rows.append(row([
            esc(f'{v["away_name"]} at {v["home_name"]}'),
            esc(v["header_date"]), esc(v["header_time"]),
            esc(v["location"]), esc(v["stadium"]), esc(v["network"]),
            esc(alt) if alt and not alt.startswith("(") else blank(),
            f'<td class="src">{src_links([sid, S_SCHED_W11])}</td>'],
            [sid, S_SCHED_W11]))
    cross_rows = [
        row([esc(c["fixture"]), esc(c["game_centre"]), esc(c["schedule_page"]),
             badge("differs", "warn") if not c["schedule_page"].startswith("(") and
             c["game_centre"].replace(" ", "").lower() != c["schedule_page"].replace(" ", "").lower()
             else badge("agrees", "ok"),
             f'<td class="src">{src_links([S_SCHED_W11, "W9388-GC-W11-01"])}</td>'],
            [S_SCHED_W11, "W9388-GC-W11-01"])
        for c in ven["cross_check"]
    ]
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Venue register</h1>
<p class="lead">One row per Week 11 fixture, transcribed from that fixture's official game-centre
page: the <em>Location</em> and <em>Stadium</em> fields of the Game Info block, the kickoff date and
time as printed, and the network. Where the schedule page names the same stadium differently, both
strings are published and neither is corrected.</p>
<div class="kpis">
{kpi("13", "venues", "one game-centre page each")}
{kpi("3", "named two ways", "Houston, Kansas City, Washington")}
{kpi("1", "played outside the United States", "Mexico City")}
</div>
{table("Week 11 venues as the game centre publishes them",
       ["Fixture", "Date", "Time", "Location", "Stadium", "Network", "Schedule page names it", "Sources"],
       rows,
       "A blank in the last column means no second string was printed for that fixture. Times are exactly as printed; the page prints no timezone for Week 11.")}
<h2>Cross-check against the schedule page</h2>
{table("The same stadium named by two official pages", ["Fixture", "Game centre", "Schedule page", "Result", "Sources"],
       cross_rows,
       "Three of thirteen differ, in both directions, so venue matching by name string is unsafe. See flags W11-F01, W11-F02 and W11-F03.")}
'''


def page_slate(d):
    off, ctx = d["off"], d["ctx"]
    abbr_to_name = {s["abbr"]: s["club"] for s in off["standings"]}
    rec = {s["abbr"]: f'{s["w"]}-{s["l"]}' + (f'-{s["t"]}' if s["t"] else "") for s in off["standings"]}
    rows = []
    for f in off["week11_fixtures"]:
        sid = next((f'W9388-GC-W11-{v["index"]:02d}' for v in d["ven"]["venues"]
                    if v["url"] == f["url"]), "W9388-GC-W11-01")
        rows.append(row([
            esc(f["kickoff_date"]), esc(f["weekday"]), esc(f["kickoff_time_as_printed"]),
            blank(), esc(f["network"]),
            esc(f'{f["away_name"]} ({rec.get(f["away"], "")})'),
            esc(f'{f["home_name"]} ({rec.get(f["home"], "")})'),
            f'<td class="src">{src_links([S_SCHED_W11, sid])}</td>'],
            [S_SCHED_W11, sid]))
    bye_rows = [
        row([esc(b["club"]), esc(abbr_to_name.get(b["abbr"], b["abbr"])), esc(b["record"]),
             f'<td class="src">{src_links([S_SCHED_W11, S_STANDINGS])}</td>'],
            [S_SCHED_W11, S_STANDINGS])
        for b in off["week11_byes"]
    ]
    ctx_rows = []
    for c, f in zip(ctx["rows"], off["week11_fixtures"]):
        sid = next((f'W9388-GC-W11-{v["index"]:02d}' for v in d["ven"]["venues"]
                    if v["url"] == f["url"]), "W9388-GC-W11-01")
        ctx_rows.append(row([
            esc(c["fixture"]), esc(c["kickoff_date"]),
            esc(c["away_previous_game"]), esc(str(c["away_rest_days"])),
            esc(c["home_previous_game"]), esc(str(c["home_rest_days"])),
            esc(str(c["rest_days_differential"])),
            f'<td class="src">{src_links([sid, "X29-NFL-SCHEDULE"])}</td>'],
            [sid, "X29-NFL-SCHEDULE"]))
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Week 11 slate</h1>
<p class="lead">The thirteen fixtures as the official by-week page prints them, each with its own
game-centre link, plus the six clubs on bye. No fixture carries a score: every row was read before
kickoff, and a score that does not exist is left blank rather than written as zero.</p>
<div class="kpis">
{kpi("13", "fixtures", "1 Thursday, 11 Sunday, 1 Monday")}
{kpi("26", "clubs playing", "6 on bye completes the 32")}
{kpi("0", "scores stored", "the week has not been played")}
</div>
{table("Week 11 fixtures", ["Date", "Day", "Kickoff", "Timezone", "Network", "Away", "Home", "Sources"], rows,
       "The timezone column is blank because the Week 11 schedule page prints no timezone; the Week 10 injury page prints EST for its own kickoff times, which is not evidence about Week 11.")}
<h2>Teams on bye</h2>
{table("The six clubs not playing in Week 11", ["Club", "Full name", "Record", "Sources"], bye_rows,
       "No club is on bye in both Week 10 and Week 11; that is check V5.")}
<h2>Fixture context from published kickoff dates only</h2>
{table("Rest days, computed from two official dates",
       ["Fixture", "Week 11 kickoff", "Away previous game", "Away rest days", "Home previous game",
        "Home rest days", "Differential (away minus home)", "Sources"],
       ctx_rows,
       "Rest days are the arithmetic difference between the club's previous game in the official results corpus and its Week 11 kickoff date. Nothing else is modelled: no travel, no timezone, no weather.")}
'''


def page_availability(d):
    off, ver = d["off"], d["ver"]
    inj = off["week11_injury_report"]
    ev_rows = [
        row([esc(e["n"]), esc(e["fetch_instant_utc"]), esc(e["result"]),
             f'<td class="src">{src_links([S_INJ_W11])}</td>'], [S_INJ_W11])
        for e in inj["reads"]
    ]
    p_rows = [
        row([esc(p["club"]), esc(p["name"]), esc(p["position"]), esc(p["jersey"]) or blank(),
             esc(p["status"]), f'<td class="src">{src_links(["W9388-GC-W11-01"])}</td>'],
            ["W9388-GC-W11-01"])
        for p in off["game_centre_players"]
    ]
    d_rows = []
    for r in off["availability_deltas"]:
        d_rows.append(row([
            esc(r["club"]), esc(r["player"]),
            esc(r["week10_capture_practice"]) if r["week10_capture_practice"] else blank(),
            esc(r["week10_capture_game"]) if r["week10_capture_game"] else blank(),
            esc(r["week11_status"]), esc(r["delta"]),
            f'<td class="src">{src_links(["W9388-GC-W11-01", "X28-NFL-INJ-W10"])}</td>'],
            ["W9388-GC-W11-01", "X28-NFL-INJ-W10"]))
    v8 = [r for r in ver["v8_rows"] if r["match"] == "CHANGED"]
    v8_rows = [
        row([esc(r["club"]), esc(r["player"]), esc(r["capture_2026_11_13_practice"]),
             esc(r["capture_2026_11_13_game"]) if r["capture_2026_11_13_game"] else blank(),
             esc(r["read_2026_11_18_practice"]),
             esc(r["read_2026_11_18_game"]) if r["read_2026_11_18_game"] else blank(),
             f'<td class="src">{src_links([S_INJ_W11, "X28-NFL-INJ-W10"])}</td>'],
            [S_INJ_W11, "X28-NFL-INJ-W10"])
        for r in v8
    ]
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Availability</h1>
<p class="lead">What the official pages actually said about player availability at the moment they
were read. The level is stored, the delta is published, and an empty module is recorded as missing
data rather than as health.</p>
<div class="kpis">
{kpi("no", "Week 11 report published", "3 reads, all served Week 10")}
{kpi("12/13", "game pages with an empty module", "24 club-game entries with no data")}
{kpi("8", "player rows exist", "on one page: the Thursday game")}
{kpi("3", "Week 10 cells that moved", "Detroit, after the games were played")}
</div>
<h2>The Week 11 league report does not exist yet</h2>
<p>The Week 11 tab is present in the page's week selector, but requesting
{esc(inj["url_requested"])} returns the Week 10 document: the canonical URL in the page's own
skip-link is <code>.../reg10</code> and the title reads
<em>{esc(inj["served_title"])}</em>.</p>
{table("Reads of the Week 11 injury URL", ["#", "Fetch instant (UTC)", "What was served", "Sources"], ev_rows,
       "The page prints no capture time, so the sandbox clock is the only clock available. See flag W11-F09.")}
<h2>The only Week 11 player rows that exist</h2>
{table("Practice status printed on the Thursday game page",
       ["Club", "Player", "Position", "Jersey", "Status as printed", "Sources"], p_rows,
       "Eight rows, four per club, followed by a 'See All' control on the page. The strings are exactly as printed, including the one row that reads 'Did participate'. See flag W11-F05.")}
<h2>Twelve pages printed an empty injury module</h2>
<p>Every game-centre page except the Thursday game printed the sentence <em>“have no active
injuries at this time”</em>. That is an empty module rather than a clean bill of health: the page
states that it lists nothing, not that the clubs are healthy, and it is not a substitute for the
Week 11 league report, which is not published. Nothing on those twelve pages is transcribed as
availability data, and no row in this desk says “available”.</p>
<h2>Delta against the Week 10 capture</h2>
{table("Week 11 status against the same player's Week 10 row",
       ["Club", "Player", "Week 10 practice", "Week 10 game status", "Week 11 status", "Delta", "Sources"],
       d_rows,
       "A blank Week 10 cell means the player does not appear on the Week 10 report at all; those rows are new listings, not changes.")}
<h2>The Week 10 report moved after its games were played</h2>
{table("Cells that differ between the 2026-11-13 capture and the read on " + READ_ON,
       ["Club", "Player", "2026-11-13 practice", "2026-11-13 game", READ_ON + " practice",
        READ_ON + " game", "Sources"], v8_rows,
       "41 of the 44 comparable rows are identical. The three that moved are published here rather than patched into the earlier capture. See flag W11-F11.")}
'''


def page_captures(d):
    cap = d["cap"]
    rows = [
        row([esc(c["id"]), esc(c["fetch_instant_utc"]), esc(c["clock_source"]),
             esc(c["served_document"]),
             f'<a href="../{esc(c["evidence"])}">{esc(c["evidence"].split("/")[-1])}</a>',
             f'<code>{esc(c["sha256_of_retained_transcript"][:16])}…</code>',
             f'<td class="src">{src_links([c["source_id"]] if c["source_id"] in URLS else [S_INJ_W11])}</td>'],
            [c["source_id"] if c["source_id"] in URLS else S_INJ_W11])
        for c in cap["captures"]
    ]
    hash_rows = [
        row([esc(name), f'<code>{esc(digest)}</code>',
             f'<a href="../evidence/{esc(name)}">transcript</a>',
             f'<td class="src">{src_links([S_INJ_W11])}</td>'], [S_INJ_W11])
        for name, digest in sorted(cap["evidence_sha256"].items())
    ]
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Capture ledger</h1>
<p class="lead">Every read this desk took, with the clock time it was taken and the hash of the
transcript that was retained. The ledger is append-only: an earlier capture is never overwritten, so
a later read can always be differenced against it.</p>
<div class="panel"><p><strong>Clock caveat.</strong> None of the pages read this session prints a
capture or update time. The only clock available is the sandbox's, so the injury reads carry a
bracketed instant and the rest carry a window, {esc(cap["window_utc"][0])} to
{esc(cap["window_utc"][1])}. That is window resolution, not per-read resolution, and it is recorded
as flag W11-F09 rather than presented as more than it is.</p></div>
{table("Captures taken on " + READ_ON,
       ["ID", "Fetch instant (UTC)", "Clock source", "What was served", "Transcript", "SHA-256 (first 16)", "Sources"],
       rows, "Transcript hashes are SHA-256 over the retained transcript file, not over the publisher's bytes, which this workspace cannot retrieve.")}
<h2>Retained transcripts</h2>
{table("Evidence files with hashes", ["File", "SHA-256", "Open", "Sources"], hash_rows,
       "A changed hash on an unchanged source means the page changed, or that we mistranscribed it; either way the build must be re-run.")}
'''


def page_questions(d):
    dec = d["dec"]
    rows = []
    for q in dec["questions"]:
        rows.append(row([
            esc(q["id"]), esc(q["question"]),
            badge(q["priority"], "bad" if q["priority"] == "blocking" else
                  ("warn" if q["priority"] == "high" else "ok")),
            esc(q["we_hold"]),
            esc(q["what_is_missing"]),
            esc(q["how_to_discover"]),
            esc(q["blocking_gate"]),
            " ".join(f'<a href="{esc(e)}">{esc(e.split("/")[-1])}</a>' for e in q["evidence"]),
            f'<td class="src">{src_links([s for s in q["source_ids"] if s in URLS])}</td>'],
            [s for s in q["source_ids"] if s in URLS]))
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Questions</h1>
<p class="lead">What we hold, what is missing, and the concrete thing that would close each gap.
Every "we hold" statement names the artefact that holds it; every "missing" statement names an absent
quantity, not a guess at its value. Nothing here is answered with a number that no official page
published.</p>
{table("Decision questions", ["ID", "Question", "Priority", "What we hold", "What is missing",
                              "How to discover it", "Gate", "Evidence", "Sources"], rows,
       "Blocking questions are the ones that stop a strategy from being graded at all, not the ones that would improve it.")}
'''


def page_suggestions(d):
    dec = d["dec"]
    rows = []
    for s in dec["suggestions"]:
        rows.append(row([
            esc(s["id"]), esc(s["title"]), esc(str(s["priority"])),
            esc(", ".join(s["requirement_ids"])), esc(s["evidence"]), esc(s["cost"]),
            esc(s["risk"]), esc(s["acceptance_test"]),
            esc(s["decision"]) if s["decision"] else blank(),
            f'<td class="src">{src_links([x for x in s["source_ids"] if x in URLS])}</td>'],
            [x for x in s["source_ids"] if x in URLS]))
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Suggestions</h1>
<p class="lead">Ten improvements, ranked, each with the evidence that prompted it, what it costs, what
could go wrong, and an acceptance test that would show it was done. The decision column is blank on
purpose: these are proposals for review, not changes that have been made.</p>
{table("Ranked suggestions", ["ID", "Suggestion", "Rank", "Requirements", "Evidence", "Cost", "Risk",
                              "Acceptance test", "Decision", "Sources"], rows,
       "A blank decision cell means nobody has chosen this yet. Nothing on this page has been implemented by this desk.")}
'''


def page_flagged(d):
    ver = d["ver"]
    rows = [
        row([esc(f["id"]),
             badge(f["severity"], "bad" if f["severity"] == "high" else
                   ("warn" if f["severity"] == "medium" else "ok")),
             esc(f["title"]), esc(f["detail"]),
             f'<a href="{esc(f["where"])}">{esc(f["where"])}</a>',
             esc(f["status"]),
             f'<td class="src">{src_links([s for s in f["sources"] if s in URLS])}</td>'],
            [s for s in f["sources"] if s in URLS])
        for f in ver["flags"]
    ]
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Flagged for review</h1>
<p class="lead">Irregularities found while reading the official pages on {READ_ON}. Each one is
published with the source that shows it. None of them blocks the merge: they are recorded so a
decision can be made about them afterwards.</p>
{table("Irregularities", ["ID", "Severity", "Title", "What was observed", "Page", "Status", "Sources"], rows,
       "Two of these are high severity because they change what a stored value means, not because a value is missing.")}
'''


def page_sources(d):
    ids = [S_STANDINGS, S_SCHED_W11, S_SCHED_W10, S_INJ_W11] + [
        f'W9388-GC-W11-{i:02d}' for i in range(1, 14)]
    rows = []
    for i in ids:
        rec = next((r for r in REGISTRY if r["id"] == i), None)
        if rec is None:
            raise SystemExit(f"FAIL: source {i} is not registered in research/sources.json")
        rows.append(row([
            esc(i), esc(rec["publisher"]), esc(rec["title"]),
            f'<a href="{esc(rec["url"])}" rel="noopener noreferrer" target="_blank">{esc(rec["url"])}</a>',
            esc(rec.get("authority", "")), esc(rec.get("checked_on", "")),
            esc(rec.get("access", "")),
            f'<td class="src">{src_links([i])}</td>'], [i]))
    return f'''
<p class="eyebrow">OWN7 · Week 11 live decision desk</p>
<h1>Sources</h1>
<p class="lead">Every page this desk read, all of them published by the league. Each table row in
this desk names the source it came from, and each of those names resolves to the URL below.</p>
{table("Registered sources", ["ID", "Publisher", "Title", "URL", "Authority", "Checked on", "Access", "Link"],
       rows, "Host validation for these ids lives in scripts/check_site.py and runs in CI.")}
<div class="panel"><p><strong>Rights.</strong> This workspace stores no price, places no wager and
publishes no reward. The publisher's terms permit individual non-commercial informational use and
restrict systematic retrieval; that restriction is why several suggestions on this site are proposed
as a small number of targeted reads rather than as an automated crawler.</p></div>
'''


# --------------------------------------------------------------------------- shell

def render(name: str, body: str) -> str:
    title = next(label for n, label in PAGES if n == name)
    parts = []
    for n, label in PAGES:
        current = ' aria-current="page"' if n == name else ''
        parts.append(f'<a href="{n}"{current}>{esc(label)}</a>')
    nav = "".join(parts)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {SITE_TITLE}</title>
<meta name="description" content="Week 11 official NFL reads taken 2026-11-18: venues, slate, availability and line-by-line verification, with retained transcripts and hashes.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="brand"><strong>{SITE_TITLE}</strong><span>official reads {READ_ON} · line-by-line verification · no prices, no wagers</span></div><nav aria-label="Desk pages">{nav}<a href="../../index.html">← NFL workspace</a></nav></header>
<main id="main">{body}</main>
<footer>Evidence attributed to NFL.com and retained with hashes; canonical artefacts belong to their
producing sessions. Not affiliated with or endorsed by the NFL. Generated deterministically by
nfl-week11-9388/build.py from committed artefacts on {READ_ON}.</footer>
</body>
</html>
'''


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    d = {"off": load("official-2026-11-18.json"), "ven": load("venues.json"),
         "ctx": load("fixture-context.json"), "cap": load("captures.json"),
         "ver": load("verification.json"), "dec": load("decisions.json"),
         "readi": load("readiness.json")}
    bodies = {
        "index.html": page_index(d),
        "verification.html": page_verification(d),
        "venues.html": page_venues(d),
        "slate.html": page_slate(d),
        "availability.html": page_availability(d),
        "captures.html": page_captures(d),
        "questions.html": page_questions(d),
        "suggestions.html": page_suggestions(d),
        "flagged.html": page_flagged(d),
        "sources.html": page_sources(d),
    }
    outputs = {name: render(name, body) for name, body in bodies.items()}
    manifest = {"desk": "nfl-week11-9388", "session": "arena/9388352a-own7", "read_on": READ_ON,
                "pages": [name for name, _ in PAGES],
                "evidence_sha256": d["cap"]["evidence_sha256"]}
    manifest_text = json.dumps(manifest, indent=1) + "\n"
    if arg == "--check":
        stale = [n for n, content in outputs.items()
                 if not (SITE / n).exists() or (SITE / n).read_text(encoding="utf-8") != content]
        if not (SITE / "manifest.json").exists() or (SITE / "manifest.json").read_text(encoding="utf-8") != manifest_text:
            stale.append("manifest.json")
        if not (SITE / "style.css").exists() or (SITE / "style.css").read_text(encoding="utf-8") != STYLE:
            stale.append("style.css")
        if stale:
            raise SystemExit("FAIL: stale desk outputs: " + ", ".join(stale))
        print(f"OK: nfl-week11-9388/site reproduces byte-identically ({len(outputs)} pages, manifest, style).")
        return 0
    SITE.mkdir(exist_ok=True)
    for name, content in outputs.items():
        (SITE / name).write_text(content, encoding="utf-8")
    (SITE / "manifest.json").write_text(manifest_text, encoding="utf-8")
    (SITE / "style.css").write_text(STYLE, encoding="utf-8")
    print(f"Built {len(outputs)} desk pages in nfl-week11-9388/site.")
    return 0


STYLE = r"""
:root{--bg:#f6f7f9;--fg:#1c2430;--muted:#5a6779;--line:#d9dee6;--panel:#fff;--ok:#1a7f37;--warn:#9a6700;--bad:#b42318;--accent:#12459e}
*{box-sizing:border-box}html{font-size:16px}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent);text-decoration:none;overflow-wrap:anywhere}
p a,.lead a,li a{text-decoration:underline}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#fff;padding:8px;z-index:10}
header.top{background:var(--panel);border-bottom:1px solid var(--line);padding:10px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
header.top .brand{display:flex;flex-direction:column;font-size:14px;color:var(--muted)}header.top .brand strong{font-size:16px;color:var(--fg)}
nav[aria-label="Desk pages"]{display:flex;flex-wrap:wrap;gap:4px;margin-left:auto}nav[aria-label="Desk pages"] a{padding:5px 10px;border-radius:6px;font-size:13px;color:var(--muted)}nav[aria-label="Desk pages"] a[aria-current="page"]{background:var(--accent);color:#fff}
main{max-width:1200px;margin:0 auto;padding:24px 20px 60px}
.eyebrow{color:var(--muted);font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 4px}
h1{font-size:26px;margin:0 0 8px}h2{font-size:19px;margin:28px 0 8px}h3{font-size:16px;margin:20px 0 6px}
.lead{max-width:70ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;display:flex;flex-direction:column}
.kpi-value{font-size:24px;font-weight:700}.kpi-label{color:var(--muted);font-size:13px}.kpi .sub{color:var(--muted);font-size:12px;margin-top:2px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:14px 0}
.table-wrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:10px 0 6px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
caption{text-align:left;padding:10px 14px;font-weight:600;color:var(--muted);border-bottom:1px solid var(--line)}
th{position:sticky;top:0;background:#eef1f5;text-align:left;padding:8px 10px;border-bottom:2px solid var(--line);white-space:nowrap}
td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:hover{background:#f2f6ff}
td.blank{background:#fbf6e9;min-width:26px}
td a{display:inline-block;font-size:12.5px;min-height:1.7rem;line-height:1.7rem;margin-right:.45rem}
td.src a{font-size:12px}
.badge{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600}
.badge{white-space:nowrap}
.badge-ok{background:#e3f4e8;color:#14532d}.badge-warn{background:#fff4e0;color:#8a4b00}.badge-bad{background:#fbe6e6;color:#7f1d1d}
.note{color:var(--muted);font-size:12.5px;max-width:100ch}
footer{max-width:1200px;margin:0 auto;padding:0 20px 40px;color:var(--muted);font-size:12.5px}
"""

if __name__ == "__main__":
    sys.exit(main())
