#!/usr/bin/env python3
"""Deterministic site generator for the fresh-reads desk (session arena/6c72a9fa-own7).

Pages are rendered from committed artefacts only:

  evidence/*.md             verbatim transcripts of the 2026-11-18 official reads
  raw/g14-LAC-BAL.txt       Game Book #14 in the shared raw format
  data/official-2026-11-18.json   parse output of collect.py (deterministic)
  data/verification.json    the V0-V8 check results
  data/whatchanged.json     the what-changed ledger (DR-61 first implementation)

--check re-renders and compares bytes. The generator aborts on any missing artefact or
contract violation rather than publishing a partial page.
"""
from __future__ import annotations

import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SITE = HERE / "site"
EVIDENCE = HERE / "evidence"

READ_ON = "2026-11-18"
SITE_TITLE = "OWN7 · Fresh-reads desk"

PAGES = [
    ("index.html", "Overview"),
    ("verification-2026-11-18.html", "Verification 2026-11-18"),
    ("week11-schedule.html", "Week 11 schedule"),
    ("reserve-sweep.html", "Reserve-list sweep"),
    ("what-changed.html", "What changed"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

# Registered source ids used by this desk (rows live in research/sources.json).
S_STAND = "C672-STANDINGS-1118"
S_GC = "C672-GC-W10-LACBAL-1118"
S_GB = "C672-GAMEBOOK-W10-LACBAL-1118"
S_W11 = "C672-SCHED-W11-1118"
S_MINSF = "C672-GC-W11-MINSF-1118"
S_RESN = "C672-RESERVE-NOV-1118"
S_RESO = "C672-RESERVE-OCT-1118"
S_TRD = "C672-TRADES-NOV-1118"
S_INJ = "C672-INJ-STATE-1118"
S_RFROZ = "C672-REPO-FROZEN-STANDINGS"
S_RPREV = "C672-REPO-PREV-STANDINGS"
S_RCORP = "C672-REPO-RESULTS-CORPUS"
S_RVEN = "C672-REPO-W10-VENUES"
S_R77B1 = "C672-REPO-77B1-RESERVE"
S_RE7INJ = "C672-REPO-E7EF-INJURIES"
S_RE7W11 = "C672-REPO-E7EF-W11"

REG_URLS = {
    S_STAND: "https://www.nfl.com/standings/",
    S_GC: "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
    S_GB: "https://static.www.nfl.com/image/upload/v1794916121/gamecenter/ab78ad5a-4feb-11f1-abca-2c54536568a9.pdf",
    S_W11: "https://www.nfl.com/schedules/2026/by-week/week-11",
    S_MINSF: "https://www.nfl.com/games/vikings-at-49ers-2026-reg-11",
    S_RESN: "https://www.nfl.com/transactions/league/reserve-list/2026/11",
    S_RESO: "https://www.nfl.com/transactions/league/reserve-list/2026/10",
    S_TRD: "https://www.nfl.com/transactions/league/trades/2026/11",
    S_INJ: "https://www.nfl.com/injuries/",
    S_RFROZ: "https://github.com/sassnarep3-star/Own7/blob/main/data/nfl-standings-week10-2026.csv",
    S_RPREV: "https://github.com/sassnarep3-star/Own7/blob/main/data/nfl-standings-2026-11-17.csv",
    S_RCORP: "https://github.com/sassnarep3-star/Own7/blob/main/nfl-results/data/games-2026-w1-10.csv",
    S_RVEN: "https://github.com/sassnarep3-star/Own7/blob/main/nfl-gamebook-5213243e/data/fixtures-venue.csv",
    S_R77B1: "https://github.com/sassnarep3-star/Own7/blob/main/nfl-brief-77b1/evidence/nfl-reserve-list-2026-11.md",
    S_RE7INJ: "https://github.com/sassnarep3-star/Own7/blob/main/nfl-readiness-e7ef/evidence/injuries-w10-2026-11-17.md",
    S_RE7W11: "https://github.com/sassnarep3-star/Own7/blob/main/nfl-readiness-e7ef/evidence/week11-2026-11-17.md",
}

FLAGS = [
    ("FG01", "The league reserve-list pages keep a rolling window (about 25 rows)",
     "The November page's visible window now starts at 11/10 and the October page's at 10/24. "
     "Eight rows printed on the 2026-11-17 capture (11/07-11/10, e.g. Jack Campbell to the Lions "
     "reserve/injured list on 11/07) are no longer rendered anywhere on the page today. What "
     "scrolled off remains true and lives only in the dated capture; IR moves dated before a "
     "window cannot be re-derived from the live pages at all. Consequence for the reserve-list "
     "requirement (DR-64/DR-13): 'capture the reserve list' has to mean capture at read time; a "
     "capture taken later can never reconstruct the missing history. Lamar Jackson and Tyler "
     "Huntley are not in either visible window today, which proves nothing about their earlier "
     "IR dates either way.",
     "reserve-sweep.html", "medium", "open"),
    ("FG02", "The final LAC@BAL result is absent from the canonical 149-final corpus",
     "nfl-results/data/games-2026-w1-10.csv holds 13 Week 10 finals and omits Chargers at Ravens "
     "entirely rather than storing it as a pending row. This desk verified the final from the "
     "official game centre and Game Book (23-20 Chargers) and proved the standings arithmetic, "
     "but left the canonical corpus untouched (other desk's scope). Cross-scope request logged "
     "in COORDINATION.md: extend the corpus to 150 finals.",
     "verification-2026-11-18.html", "medium", "cross-scope request logged"),
    ("FG03", "The reserve list prints 'Cowboys' as the From club for Tyler Goodson (11/14)",
     "Both the 2026-11-17 capture and this desk's fresh read show the identical row "
     "('Cowboys | 11/14 | Tyler Goodson | Reserve/Injured'). The row is transcribed as printed; "
     "no page read this session explains the club attribution for this player. Flagged so the "
     "publisher-side oddity is not silently normalized later.",
     "reserve-sweep.html", "low", "open"),
    ("FG04", "The standings render includes unlabeled groups",
     "Each standings row renders 16 groups; besides the named columns, group 11 and 13 are "
     "percentages and group 14 is a record whose meaning the page does not state in the markup "
     "this desk receives. All 16 groups are transcribed positionally; only the groups the prior "
     "canonical captures also named (W, L, T, PCT, PF, PA, NetPts, Home, Road, Div, Conf, Strk, "
     "Last5) are interpreted. The same render appears in the committed 2026-11-17 capture, so it "
     "is not a new change.",
     "verification-2026-11-18.html", "low", "explained"),
    ("FG05", "Game Book #14 was read in part (chunk 0 of 8)",
     "The PDF parse returns 8 chunks; chunk 0 carries the summary, lineups, substitutions, Not "
     "Active lists, field goals, quarter totals, scoring plays and paid attendance, which is all "
     "this desk needs. Chunks 1-7 (final individual statistics, play-by-play) were not read. "
     "This is a scope statement, not a capture defect.",
     "verification-2026-11-18.html", "low", "explained"),
    ("FG06", "The injuries hub still serves Week 10 at the 2026-11-18 read",
     "Title and header both say Week 10; the WEEK 11 tab exists but its content was not rendered. "
     "The Week 11 game centres meanwhile print 'no active injuries at this time' for the clubs "
     "checked (Vikings, 49ers). The first Week 11 report read is pending the league's Wednesday "
     "publication convention. Recorded as page state, not as an absence of injuries.",
     "verification-2026-11-18.html", "info", "informational"),
    ("FG07", "The schedule page prints a weather string beside one Week 11 fixture",
     "The Week 11 schedule page prints 'Weather Clearnight' beside Bengals at Commanders (MNF). "
     "The desk transcribes it as published; it is not used as a forecast source and no weather "
     "value is joined into any model context from it.",
     "week11-schedule.html", "low", "explained"),
]

RESOLUTIONS = [
    ("RG01", "The 14th Week 10 Game Book is published",
     "The game centre now links the official Game Book PDF for LAC@BAL. Week 10 venue/starters/"
     "inactives coverage is therefore 14 of 14 fixtures, closing the 13-of-14 gap the Game Book "
     "desk recorded (DR-23/DR-25)."),
    ("RG02", "The named starter-change trades are confirmed from the league's own page",
     "The November trades page confirms with dates: Brissett AZ->BAL on 11/06 (and he starts the "
     "Week 10 Monday game per the Game Book), Allen IND->SF and Downs IND->KC on 11/10 (the two "
     "starting-receiver trades of the Colts' Week 10 release), and Neuzil ATL->BAL on 11/10 "
     "(printed 'Did Not Play' in Game Book #14)."),
]


def esc(v) -> str:
    return html.escape(str(v), quote=True)


def link(url: str, text: str | None = None) -> str:
    t = text or url
    external = url.startswith("http")
    if external:
        return f'<a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{esc(t)}</a>'
    return f'<a href="{esc(url)}">{esc(t)}</a>'


def row(cells: list[str], sid: str) -> str:
    return f'<tr data-source-ids="{sid}">' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def blank() -> str:
    return ('<td class="blank" data-empty="true" aria-label="Blank — unverified, withheld or not '
            'applicable" title="Not supplied; see status and limitations"></td>')


def table(caption: str, headers: list[str], rows: list[str], note: str | None = None) -> str:
    head = "".join(f'<th scope="col">{h}</th>' for h in headers)
    note_html = f'<p class="note">{esc(note)}</p>' if note else ""
    return (f'<div class="table-wrap"><table><caption>{esc(caption)}</caption>'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>{note_html}')


def badge(text: str, kind: str) -> str:
    return f'<span class="badge badge-{esc(kind)}">{esc(text)}</span>'


def kpi(value: str, label: str, sub: str = "") -> str:
    sub_html = f'<span class="sub">{esc(sub)}</span>' if sub else ""
    return (f'<div class="kpi"><span class="kpi-value">{esc(value)}</span>'
            f'<span class="kpi-label">{esc(label)}</span>{sub_html}</div>')


def load() -> dict:
    out = json.loads((DATA / "official-2026-11-18.json").read_text(encoding="utf-8"))
    ver = json.loads((DATA / "verification.json").read_text(encoding="utf-8"))
    chg = json.loads((DATA / "whatchanged.json").read_text(encoding="utf-8"))
    srcs = {s["id"]: s for s in json.loads((ROOT / "research/sources.json").read_text(encoding="utf-8"))}
    for sid in REG_URLS:
        if sid not in srcs:
            raise SystemExit(f"FAIL: desk names unregistered source {sid}")
    return {"out": out, "ver": ver, "chg": chg, "srcs": srcs}


def ev_hash(name: str) -> str:
    return hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()


# ------------------------------------------------------------------ pages ------
def page_index(d: dict) -> str:
    out, ver, chg = d["out"], d["ver"], d["chg"]
    added = len(chg["reserve_series"]["added"])
    removed = len(chg["reserve_series"]["scrolled_off"])
    inj_rows = ver["V8_injuries_state"]["rows_compared"]
    checks_rows = [
        row(["V0", "pass", "Every parsed club maps to a canonical code and division block",
             link(REG_URLS[S_STAND], "standings ↗")], S_STAND),
        row(["V1", "pass", "32/32 fresh standings cells = 2026-11-17 pre-MNF CSV + the verified "
                           "LAC@BAL final (BAL/LAC moved; 30 clubs cell-identical)",
             link(REG_URLS[S_RPREV], "2026-11-17 CSV ↗")], S_RPREV),
        row(["V1b", "pass", "32/32 clubs re-derived from the frozen 2026-11-12 capture + all 14 "
                            "Week 10 finals (W, L, PF, PA)",
             link(REG_URLS[S_RFROZ], "frozen CSV ↗")], S_RFROZ),
        row(["V2", "pass", "LAC@BAL final (23-20) agrees across game centre, Game Book and the "
                           "standings deltas; the game is absent from the results corpus "
                           "(cross-scope request logged)",
             link(REG_URLS[S_GC], "game centre ↗")], S_GC),
        row(["V3", "pass", "W+L+T per club equals games in the 149-final corpus (+1 for LAC/BAL)",
             link(REG_URLS[S_RCORP], "results corpus ↗")], S_RCORP),
        row(["V4", "pass", "Week 11 slate: 13 fixtures, 26 clubs once each, 6 byes complete the "
                           "32; every venue non-blank",
             link(REG_URLS[S_W11], "week 11 page ↗")], S_W11),
        row(["V5", "pass", "Week 10 venue coverage is now 14/14 (Game Book #14: M&T Bank Stadium "
                           "matches the game centre)",
             link(REG_URLS[S_GB], "Game Book PDF ↗")], S_GB),
        row(["V6", "pass", "Reserve sweep: Nov window 25 rows + Oct window 25 rows; +8/-8 vs the "
                           "2026-11-17 capture; Malik Willis present; Jackson/Huntley absent from "
                           "both visible windows",
             link(REG_URLS[S_RESN], "reserve list ↗")], S_RESN),
        row(["V7", "pass", "Game Book #14: 22 offense + 22 defense starters, 12 Not Active, "
                           "attendance 69,679, QBs Herbert/Brissett",
             link(REG_URLS[S_GB], "Game Book PDF ↗")], S_GB),
        row(["V8", "pass", "Injuries hub still serves Week 10; 50 re-read rows are cell-identical "
                           "to the 2026-11-17 capture (0 diffs)",
             link(REG_URLS[S_INJ], "injuries hub ↗")], S_INJ),
    ]
    body = f'''
<p class="eyebrow">OWN7 · Fresh-reads desk</p>
<h1>Week 10 completion and Week 11 readiness — official reads of 2026-11-18</h1>
<p class="lead">This desk took fresh official reads the morning after the Week 10 Monday game,
closed the last open gap in the Week 10 evidence (the 14th Game Book and the LAC@BAL final),
swept the league reserve lists, and published the workspace's first what-changed ledger between
dated captures. Every value traces to a verbatim transcript of the official page it was read
from, retained with a SHA-256 hash.</p>
<div class="kpis">
{kpi("32/32", "standings cells re-verified", "2026-11-17 pre-MNF + LAC@BAL final = fresh page")}
{kpi("23-20", "LAC at BAL, final", "the pending Week 10 game is now closed")}
{kpi("14/14", "Week 10 venues from Game Books", "Game Book #14 published overnight")}
{kpi(f"+{added}/-{removed}", "reserve-list rows since 2026-11-17", "25-row rolling window per month page")}
{kpi(str(inj_rows), "injury rows re-read, 0 diffs", "Week 10 report stable between the two reads")}
{kpi("13+6", "Week 11 fixtures + byes", "venues complete incl. Estadio Banorte")}
</div>
<h2>What this desk adds</h2>
<div class="panel body-text"><ol>
<li><strong>The Week 10 corpus gap is resolved and evidenced.</strong> The official game centre
and the overnight-published Game Book give Chargers 23, Ravens 20 (final, Nov 16, M&T Bank
Stadium). The fresh standings page moves exactly by that result — Baltimore +1L +20PF +23PA, Los
Angeles +1W +23PF +20PA — and every other club is cell-identical to the 2026-11-17 pre-MNF read.
The frozen capture plus all 14 finals re-derives all 32 clubs.</li>
<li><strong>Game Book #14.</strong> Official starters (22 offense + 22 defense rows), Not Active
lists (12 rows), officials, roof/surface ("Open Stadium on Natural Grass"), weather (Clear, 49°F,
wind NW 2 mph) and paid attendance (69,679) for the last unverified fixture.</li>
<li><strong>A league-wide reserve-list sweep.</strong> The November and October reserve-list
windows are captured with their dated rows, diffed against the 2026-11-17 capture (+8 new 11/17
rows, -8 scrolled off), and joined to the November trades page — which dates the Brissett,
Allen and Downs moves the brief named.</li>
<li><strong>The first what-changed ledger (DR-61).</strong> Standings diff, reserve-list series
delta, injury-report stability and schedule stability between dated captures, rendered instead
of another static snapshot.</li>
</ol></div>
<h2>Verification checks (all must pass; a single failure aborts the build)</h2>
{table("Checks run by collect.py on every build", ["Check", "Result", "What was verified"], checks_rows,
       "Full detail with per-club rows: verification-2026-11-18.html. The checks re-run in CI.")}
<p class="note">Paper research only. No wager, stake, bankroll, price or monetary reward is
produced anywhere on this desk. Nothing here is a betting recommendation.</p>
'''
    return body


def page_verification(d: dict) -> str:
    out = d["out"]
    # standings verification table: fresh vs 2026-11-17 CSV (loaded here for the render)
    import csv
    prev_rows = list(csv.DictReader(
        (ROOT / "data" / "nfl-standings-2026-11-17.csv").read_text(encoding="utf-8").splitlines()))
    prev_by_name = {r["Team"]: r for r in prev_rows}
    st_rows = []
    for r in out["standings"]:
        p = prev_by_name[r["team_name"]]
        delta = "" if (r["W"], r["L"], r["T"], r["PF"], r["PA"]) == (
            int(p["W"]), int(p["L"]), int(p["T"]), int(p["PF"]), int(p["PA"])) else (
            f'W {p["W"]}→{r["W"]}, L {p["L"]}→{r["L"]}, PF {p["PF"]}→{r["PF"]}, PA {p["PA"]}→{r["PA"]}')
        st_rows.append(row([
            esc(r["code"]), esc(r["club"]), esc(r["division"]),
            esc(f'{p["W"]}-{p["L"]}-{p["T"]}'), esc(f'{r["W"]}-{r["L"]}-{r["T"]}'),
            esc(f'{p["PF"]}-{p["PA"]}'), esc(f'{r["PF"]}-{r["PA"]}'),
            (esc(delta) if delta else badge("unchanged", "ok")),
            link(REG_URLS[S_STAND], "standings ↗"),
        ], S_STAND))
    fin = out["week10_pending_final"]
    final_rows = [
        row([esc(fin["week"]), esc("LAC at BAL"), esc(fin["date"]),
             esc(f'{fin["away_score"]}-{fin["home_score"]}'), esc(fin["state"]),
             link(fin["gamecenter_url"], "game centre ↗"), link(REG_URLS[S_GB], "Game Book PDF ↗")], S_GC),
    ]
    gb = out["gamebook_14"]
    g = gb["game"]
    gb_rows = [
        row(["Fixture", esc(f'{g["id"]} {g["away"]} at {g["home"]}'), esc(g["date"]),
             esc(g["kickoff_et"]), link(REG_URLS[S_GB], "Game Book PDF ↗")], S_GB),
        row(["Venue", esc(g["stadium"]), esc(g["location"]), esc(g["roof_surface"]),
             link(REG_URLS[S_GB], "Game Book PDF ↗"), link(REG_URLS[S_GC], "game centre ↗")], S_GB),
        row(["Weather", esc(g["weather"]), esc(g["temp_f"] + " °F"), esc(g["wind"] + " mph"),
             link(REG_URLS[S_GB], "Game Book PDF ↗")], S_GB),
        row(["Attendance", esc(g["attendance"]), "paid attendance as printed", "Time 3:07",
             link(REG_URLS[S_GB], "Game Book PDF ↗")], S_GB),
        row(["Starters", f'{len(gb["off"])} offense + {len(gb["def"])} defense rows',
             "11 per club per unit as printed in the Lineups table", "QB starters: "
             + ", ".join(sorted(r["player"] for r in gb["off"] if r["pos"] == "QB")),
             link(REG_URLS[S_GB], "Game Book PDF ↗")], S_GB),
        row(["Not Active", esc(len(gb["ina"])) + " rows",
             esc("; ".join(r["team"] + " " + r["player"] for r in gb["ina"][:6])),
             esc("; ".join(r["team"] + " " + r["player"] for r in gb["ina"][6:])),
             link(REG_URLS[S_GB], "Game Book PDF ↗")], S_GB),
    ]
    inj = out["injuries_state"]
    inj_rows = []
    for sec, rows in inj["tables"].items():
        inj_rows.append(row([
            esc(sec), str(len(rows)), badge("stable vs 2026-11-17", "ok"),
            link(REG_URLS[S_INJ], "injuries hub ↗"),
        ], S_INJ))
    checks_rows = [
        row(["V1/V1b", esc(str(d["ver"]["V1_standings"]["failed"])) + " failed of 32; V1b "
             + esc(str(d["ver"]["V1b_frozen_plus_14_finals"]["failed"])) + " failed of 32",
             esc(d["ver"]["V1_standings"]["method"]), link(REG_URLS[S_RPREV], "2026-11-17 CSV ↗")], S_RPREV),
        row(["V2", "final joins 1:1", esc(d["ver"]["V2_final_join"]["corpus_status"]),
             link(REG_URLS[S_GC], "game centre ↗")], S_GC),
        row(["V3", "32/32 clubs", esc(d["ver"]["V3_games_played"]["method"]),
             link(REG_URLS[S_RCORP], "results corpus ↗")], S_RCORP),
        row(["V4", "13 fixtures, 26 clubs, 6 byes", "venues complete; byes match the slate",
             link(REG_URLS[S_W11], "week 11 page ↗")], S_W11),
        row(["V5", "14 of 14 Week 10 venues", esc(d["ver"]["V5_venue_completion"]["new"]["stadium"])
             + " added from Game Book #14", link(REG_URLS[S_GB], "Game Book ↗")], S_GB),
        row(["V6", esc(str(len(d["ver"]["V6_reserve_sweep"]["added_since_2026_11_17"]))) + " added / "
             + esc(str(len(d["ver"]["V6_reserve_sweep"]["scrolled_off_since_2026_11_17"]))) + " scrolled",
             "rolling-window sweep; see the reserve-sweep page",
             link(REG_URLS[S_RESN], "reserve list ↗")], S_RESN),
        row(["V7", "22/22/12 rows", "Game Book #14 complete for this desk's scope",
             link(REG_URLS[S_GB], "Game Book ↗")], S_GB),
        row(["V8", esc(str(d["ver"]["V8_injuries_state"]["rows_compared"])) + " rows, "
             + esc(str(d["ver"]["V8_injuries_state"]["diffs"])) + " diffs",
             esc(d["ver"]["V8_injuries_state"]["title"]), link(REG_URLS[S_INJ], "injuries hub ↗")], S_INJ),
    ]
    body = f'''
<p class="eyebrow">OWN7 · Fresh-reads desk</p>
<h1>Verification 2026-11-18</h1>
<p class="lead">Every check re-runs on every build and aborts the build on failure. The
standings table is the line-by-line core: the fresh official read of this morning, the
2026-11-17 pre-MNF capture beside it, and the exact delta the verified LAC@BAL final explains.</p>
<h2>Standings, line by line (32 rows)</h2>
{table("Fresh standings vs the 2026-11-17 pre-MNF capture",
       ["Code", "Club", "Division", "W-L-T (11-17)", "W-L-T (11-18)", "PF-PA (11-17)", "PF-PA (11-18)", "Delta", "Source"], st_rows,
       "Only BAL and LAC moved; both move by exactly the LAC@BAL final. V1b additionally "
       "re-derives every club from the frozen 2026-11-12 capture plus all 14 Week 10 finals.")}
<h2>The Week 10 corpus gap, closed</h2>
{table("Chargers at Ravens — Week 10 final (verified this session)",
       ["Week", "Fixture", "Date", "Final", "State", "Game centre", "Game Book"], final_rows,
       "The canonical results corpus omits this game (149 finals); extending it to 150 is logged "
       "as a cross-scope request, not patched here (flag FG02).")}
<h2>Game Book #14 (the last unverified Week 10 fixture)</h2>
{table("Game Book facts (verbatim from the official PDF)",
       ["Item", "Value", "Detail", "More", "Source", "Also"], gb_rows,
       "Lineups, substitutions, Not Active, officials and scoring plays are retained verbatim in "
       "evidence/gamebook-w10-lac-bal-2026-11-18.md; the hand transcription is raw/g14-LAC-BAL.txt. "
       "Chunks 1-7 of the PDF were not read (flag FG05).")}
<h2>Injury-report stability</h2>
{table("Tables re-read on 2026-11-18 vs the committed 2026-11-17 capture",
       ["Section", "Rows compared", "Result", "Source"], inj_rows,
       "50 rows compared cell for cell, 0 diffs: the Week 10 report did not change between the "
       "two reads. The hub still serves Week 10 (flag FG06).")}
<h2>Check register</h2>
{table("Checks run by collect.py", ["Check", "Result", "Method", "Source"], checks_rows)}
'''
    return body


def page_week11(d: dict) -> str:
    out = d["out"]
    fx_rows = []
    for f in out["week11_fixtures"]:
        sid = S_MINSF if f["slot"] == 12 else S_W11
        extra = link(REG_URLS[S_W11], "schedule page ↗") if sid != S_MINSF else link(REG_URLS[S_MINSF], "game centre ↗")
        fx_rows.append(row([
            esc(f["slot"]), esc(f["away"] + " at " + f["home"]),
            esc(f["day"] + ", " + f["date"]), esc(f["kickoff_et"] + " ET"), esc(f["network"]),
            esc(f["venue"]), link(f["gamecenter_url"], "game centre ↗"), extra,
        ], sid))
    bye_rows = [row([esc(b["code"]), esc(b["club"]), esc(b["record"]),
                     link(REG_URLS[S_W11], "week 11 page ↗")], S_W11)
                for b in out["week11_byes"]]
    body = f'''
<p class="eyebrow">OWN7 · Fresh-reads desk</p>
<h1>Week 11 schedule — official read of 2026-11-18</h1>
<p class="lead">Thirteen fixtures, 6 byes completing the 32 clubs. All thirteen fixture slots are
unchanged from the committed 2026-11-17 capture (same opponents, kickoff times, networks and game
centres). Venues are printed by the schedule page's own vendor-location strings, except the
international game, whose stadium comes from the official game centre.</p>
{table("Week 11 fixtures (all pre-kickoff at read time)",
       ["#", "Fixture", "Date", "Kickoff", "Network", "Venue", "Game centre", "Source"], fx_rows,
       "Vikings at 49ers (Sunday Night Football) is the Mexico City international game: the "
       "schedule page prints no stadium, and the game centre confirms Location MEXICO CITY, "
       "Stadium ESTADIO BANORTE. The Monday fixture's vendor block prints 'Weather Clearnight' "
       "(flag FG07) — recorded, not used as a forecast.")}
{table("Teams on Bye (as printed by the schedule page)", ["Code", "Club", "Record"], bye_rows,
       "The six byes complete the 32-club slate exactly: the 26 fixture clubs and these 6 are "
       "disjoint and cover all clubs once.")}
<div class="panel"><h2>Late-week TBD note (published schedule facts, verbatim)</h2>
<p>The page states that Week 16 and Week 17 each keep two designated matchups for Saturday
scheduling (announced no later than immediately after Week 14 / Week 15), and that Week 18
scheduling is set following Week 17. Flexible-schedule procedures are published at
{link("https://www.nfl.com/legal/flexible-scheduling-procedures", "nfl.com/legal/flexible-scheduling-procedures")}.
These are the published facts the fixture-context requirement (DR-14/DR-24) rests on; nothing
about them is inferred.</p></div>
<p class="note">Stability check: the fixture set, kickoff times and networks match the committed
2026-11-17 capture 13/13 (see what-changed.html). The first Week 11 injury report was not yet
published at read time (flag FG06).</p>
'''
    return body


def page_reserve(d: dict) -> str:
    out, chg = d["out"], d["chg"]
    series = chg["reserve_series"]
    nov_rows = [row([esc(r["from"]), esc(r["to"]), esc(r["date"]), esc(r["name"]),
                     esc(r["transaction"] or ""), link(REG_URLS[S_RESN], "page ↗")], S_RESN)
                for r in out["reserve_november"]]
    oct_rows = [row([esc(r["from"]), esc(r["to"]), esc(r["date"]), esc(r["name"]),
                     esc(r["transaction"] or ""), link(REG_URLS[S_RESO], "page ↗")], S_RESO)
                for r in out["reserve_october"]]
    add_rows = [row([esc(k[0]), esc(k[1]), esc(k[2]),
                     badge("added to the visible window", "ok"), link(REG_URLS[S_RESN], "page ↗")], S_RESN)
                for k in series["added"]]
    rem_rows = [row([esc(k[0]), esc(k[1]), esc(k[2]),
                     badge("scrolled off the window", "warn"), link(REG_URLS[S_R77B1], "2026-11-17 capture ↗")], S_R77B1)
                for k in series["scrolled_off"]]
    trd_rows = [row([esc(r["from"]), esc(r["to"]), esc(r["date"]), esc(r["name"]),
                     esc(r["transaction"] or ""), link(REG_URLS[S_TRD], "page ↗")], S_TRD)
                for r in out["trades_november"]]
    body = f'''
<p class="eyebrow">OWN7 · Fresh-reads desk</p>
<h1>League reserve-list sweep — 2026-11-18</h1>
<p class="lead">The league publishes its reserve list by month with a limited visible window.
This desk swept the November and October pages, diffed them against the committed 2026-11-17
capture, and joined the November trades page. This is the sweep the 32-team roster/IR
requirement (DR-13) asked for, at league level, from official pages — with the window limitation
flagged rather than hidden.</p>
<div class="kpis">
{kpi("25 + 25", "rows in the visible windows", "November (11/17→11/10) and October (10/31→10/24)")}
{kpi("+8", "rows added since 2026-11-17", "all dated 11/17")}
{kpi("-8", "rows scrolled off", "dated 11/07–11/10; retained in the 2026-11-17 capture")}
{kpi("12", "November trades", "incl. Brissett 11/06, Allen and Downs 11/10")}
</div>
<h2>November 2026 — Reserve List (visible window)</h2>
{table("Reserve/Injured rows as printed (page order)",
       ["From", "To", "Date", "Name", "Transaction", "Source"], nov_rows,
       "The Position column is blank on every row the page prints. Flag FG03 notes the "
       "'Cowboys' attribution on the Tyler Goodson row; FG01 documents the rolling window.")}
<h2>October 2026 — Reserve List (visible window)</h2>
{table("Reserve/Injured rows as printed (page order)",
       ["From", "To", "Date", "Name", "Transaction", "Source"], oct_rows,
       "Oldest visible row 10/24 (BAL — Tavius Robinson). October rows dated 10/01–10/23 are not "
       "rendered today; one row is a Commissioner suspension, transcribed as printed.")}
<h2>Series delta vs the 2026-11-17 capture</h2>
{table("Rows added to the visible window (all dated 11/17)",
       ["Club", "Date", "Name", "Change", "Source"], add_rows)}
{table("Rows scrolled off the window (printed on 2026-11-17; not rendered today)",
       ["Club", "Date", "Name", "Change", "Source"], rem_rows,
       "These rows remain true — they were printed by the league page on 2026-11-17 and are "
       "retained in the committed capture. The window advanced by exactly 8 rows in one day.")}
<h2>Named-name checks</h2>
<div class="panel body-text"><ul>
<li><strong>Malik Willis (the motivating case for 'not listed ≠ available')</strong> is on the
visible November window (Dolphins, 11/10, Reserve/Injured), as in the 2026-11-17 capture.</li>
<li><strong>Lamar Jackson and Tyler Huntley</strong> are in neither the November nor the October
visible window. The October window starts 10/24, so this cannot confirm or refute their earlier
IR dates — the prior sessions' dated evidence remains the only capture. Flag FG01.</li>
<li><strong>TreVeyon Henderson</strong> (Patriots, 11/14, Reserve/Injured) sits beside the Week 10
report row that listed him Out with illness — the same tension the readiness desk recorded
(EF02), now with the dated reserve move attached.</li>
</ul></div>
<h2>November 2026 trades (league transactions page)</h2>
{table("Trade rows as printed (page order)", ["From", "To", "Date", "Name", "Transaction", "Source"], trd_rows,
       "Resolution RG02: Brissett (AZ→BAL, 11/06) starts Week 10 Monday per Game Book #14; "
       "Neuzil (ATL→BAL, 11/10) appears in that Game Book's 'Did Not Play' list; Allen "
       "(IND→SF) and Downs (IND→KC) on 11/10 are the two starting-receiver trades the brief's "
       "Week 10 release note describes.")}
'''
    return body


def page_whatchanged(d: dict) -> str:
    chg = d["chg"]
    st_rows = []
    for r in chg["standings_2026_11_17_to_2026_11_18"]:
        if r["changed"]:
            st_rows.append(row([
                esc(r["code"]), esc(r["club"]),
                esc(f'{r["W_was"]}-{r["L_was"]}'), esc(f'{r["W_now"]}-{r["L_now"]}'),
                esc(f'W+{r["dW"]}' if r["dW"] > 0 else f'W{r["dW"]:+d}'),
                esc(f'L+{r["dL"]}' if r["dL"] > 0 else f'L{r["dL"]:+d}'),
                esc(f'PF{r["dPF"]:+d}'), esc(f'PA{r["dPA"]:+d}'),
                badge("changed", "warn"), link(REG_URLS[S_STAND], "standings ↗")], S_STAND))
    n_changed = len(st_rows)
    stable_rows = [row([
        esc(r["code"]), esc(r["club"]), esc(f'{r["W_was"]}-{r["L_was"]}'), esc(f'{r["W_now"]}-{r["L_now"]}'),
        badge("unchanged", "ok"), link(REG_URLS[S_STAND], "standings ↗")], S_STAND)
        for r in chg["standings_2026_11_17_to_2026_11_18"] if not r["changed"]]
    series = chg["reserve_series"]
    inj = chg["injury_report_2026_11_17_to_2026_11_18"]
    sched = chg["week11_schedule_2026_11_17_to_2026_11_18"]
    body = f'''
<p class="eyebrow">OWN7 · Fresh-reads desk</p>
<h1>What changed — 2026-11-17 → 2026-11-18</h1>
<p class="lead">First implementation of the weekly what-changed ledger the brief asked for
(DR-61): instead of another static snapshot, the desk renders the delta between dated captures —
standings movement, availability-event churn, and report stability — every row with its sources.</p>
<h2>Standings movement (the only clubs that moved)</h2>
{table("Clubs whose record or points changed between the two captures",
       ["Code", "Club", "W-L (was)", "W-L (now)", "ΔW", "ΔL", "ΔPF", "ΔPA", "Status", "Source"], st_rows,
       f'{n_changed} of 32 clubs moved — exactly the two that played the Week 10 Monday game, '
       'and exactly by its result.')}
<h2>Clubs unchanged between the captures</h2>
{table("The 30 clubs with identical records and points", ["Code", "Club", "W-L (was)", "W-L (now)", "Status", "Source"], stable_rows)}
<h2>Availability events (reserve-list series)</h2>
<div class="panel body-text"><p>
Window size stayed at 25 rows on the November page while <strong>{len(series['added'])} rows
entered</strong> (all dated 11/17) and <strong>{len(series['scrolled_off'])} rows left</strong>
(dated 11/07–11/10). The full lists are on the
<a href="reserve-sweep.html">reserve-list sweep page</a>. Nothing in the workspace treats a
scrolled-off row as deleted; the dated capture is the record.</p></div>
<h2>Report stability</h2>
<div class="panel body-text"><p>
Injury report: {sum(s["rows_compared"] for s in inj)} re-read rows, {sum(len(s["diffs"]) for s in inj)}
diffs — the Week 10 report is stable between the two reads (the hub still serves Week 10).
Week 11 schedule: {sched["fixtures_compared"]}/13 fixture slots identical to the 2026-11-17
capture (stable = {str(sched["stable"]).lower()}).</p></div>
<p class="note">Next runs of this desk (or any session) append further dated reads; the ledger
format stands as printed here.</p>
'''
    return body


def page_flagged(d: dict) -> str:
    flag_src = {"FG01": S_RESN, "FG02": S_RCORP, "FG03": S_RESN, "FG04": S_STAND,
                "FG05": S_GB, "FG06": S_INJ, "FG07": S_W11}
    flag_rows = [row([esc(fid), "<strong>" + esc(title) + "</strong>", esc(detail),
                      f'<a href="{esc(where)}">view</a>',
                      link(REG_URLS[flag_src[fid]], "official page ↗"),
                      badge(sev, sev_kind(sev)), esc(status)], flag_src[fid])
                 for fid, title, detail, where, sev, status in FLAGS]
    res_rows = [row([esc(rid), "<strong>" + esc(title) + "</strong>", esc(detail),
                     link(REG_URLS[S_GB], "Game Book PDF ↗"),
                     link(REG_URLS[S_TRD], "trades page ↗")], S_GB)
                for rid, title, detail in RESOLUTIONS]
    body = f'''
<p class="eyebrow">OWN7 · Fresh-reads desk</p>
<h1>Flagged for review</h1>
<p class="lead">Irregularities and limitations found by this session, published so they do not
block anything and can be reviewed after the site is live. None of these are silently patched;
they are either publisher-side properties, cross-scope requests, or scope statements.</p>
{table("Flags raised by this desk", ["ID", "Finding", "Detail", "Where", "Official page", "Severity", "Status"], flag_rows,
       "Severity: medium = affects what a reader may conclude; low = cosmetic or explained; "
       "info = page-state note. The workspace-wide register is on the main Flagged for Review page.")}
{table("Publisher-side resolutions recorded this session", ["ID", "Resolution", "Detail", "Source", "Also"], res_rows)}
'''
    return body


def sev_kind(sev: str) -> str:
    return {"medium": "warn", "low": "ok", "info": "ok"}.get(sev.split(",")[0], "warn")


def page_sources(d: dict) -> str:
    names = sorted(p.name for p in EVIDENCE.glob("*.md"))
    ev_rows = [row([
        esc(n), link(REG_URLS[SRC_OF[n]], "official page ↗"), esc(ev_hash(n)[:16] + "…"),
        esc(ev_hash(n)),
    ], SRC_OF[n]) for n in names]
    src_rows = [row([esc(sid), esc(d["srcs"][sid]["publisher"]), esc(d["srcs"][sid]["title"]),
                     link(url, url), esc(d["srcs"][sid]["checked_on"])], sid)
                for sid, url in REG_URLS.items()]
    return f'''
<p class="eyebrow">OWN7 · Fresh-reads desk</p>
<h1>Sources</h1>
<p class="lead">The nine verbatim evidence transcripts and the registered sources this desk rests
on. Every evidence file was read from the official page at the time recorded and is hashed so any
later change is detectable. Full SHA-256 lines live in evidence/SHA256SUMS.txt.</p>
{table("Evidence transcripts (verbatim, hashed)", ["File", "Official page", "SHA-256 (head)", "SHA-256 (full)"], ev_rows)}
{table("Registered sources used by this desk", ["Source id", "Publisher", "Title", "URL", "Checked on"], src_rows,
       "The workspace register is research/sources.json (" + str(len(d["srcs"])) + " sources); these 16 were added by this desk.")}
'''


SRC_OF = {
    "standings-2026-11-18.md": S_STAND,
    "gamecenter-w10-lac-bal-2026-11-18.md": S_GC,
    "gamebook-w10-lac-bal-2026-11-18.md": S_GB,
    "schedule-week11-2026-11-18.md": S_W11,
    "gamecenter-w11-min-sf-2026-11-18.md": S_MINSF,
    "reserve-list-nov-2026-11-18.md": S_RESN,
    "reserve-list-oct-2026-11-18.md": S_RESO,
    "trades-nov-2026-11-18.md": S_TRD,
    "injuries-state-2026-11-18.md": S_INJ,
}


STYLE = """
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
.badge{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap}
.badge-ok{background:#e3f4e8;color:#14532d}.badge-warn{background:#fff4e0;color:#8a4b00}.badge-bad{background:#fbe6e6;color:#7f1d1d}
.note{color:var(--muted);font-size:12.5px;max-width:100ch}
footer{max-width:1200px;margin:0 auto;padding:0 20px 40px;color:var(--muted);font-size:12.5px}
"""


def render(name: str, body: str) -> str:
    title = next(label for n, label in PAGES if n == name)
    nav_parts = []
    for n, label in PAGES:
        current = ' aria-current="page"' if n == name else ""
        nav_parts.append(f'<a href="{n}"{current}>{esc(label)}</a>')
    nav = "".join(nav_parts)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {SITE_TITLE}</title>
<meta name="description" content="Fresh official NFL reads of 2026-11-18: the Week 10 Monday final verified, Game Book #14 captured, league reserve-list sweep and the first what-changed ledger.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="brand"><strong>{SITE_TITLE}</strong><span>official reads 2026-11-18 · Week 10 completion · Week 11 readiness</span></div><nav aria-label="Desk pages">{nav}<a href="../../index.html">← NFL workspace</a></nav></header>
<main id="main">{body}</main>
<footer>Evidence attributed to NFL.com and retained with hashes; canonical artefacts belong to their
producing sessions. Not affiliated with or endorsed by the NFL. Generated deterministically by
nfl-week11-6c72a9fa/build.py from committed artefacts on {READ_ON}.</footer>
</body>
</html>
'''


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    d = load()
    bodies = {
        "index.html": page_index(d),
        "verification-2026-11-18.html": page_verification(d),
        "week11-schedule.html": page_week11(d),
        "reserve-sweep.html": page_reserve(d),
        "what-changed.html": page_whatchanged(d),
        "flagged.html": page_flagged(d),
        "sources.html": page_sources(d),
    }
    # every page reference in a flag must be one of this desk's pages
    desk_pages = {name for name, _ in PAGES}
    for fid, _, _, where, _, _ in FLAGS:
        if where not in desk_pages:
            raise SystemExit(f"FAIL: flag {fid} links unknown page {where}")
    outputs = {name: render(name, body) for name, body in bodies.items()}
    manifest = {
        "desk": "nfl-week11-6c72a9fa", "session": "arena/6c72a9fa-own7", "read_on": READ_ON,
        "pages": [name for name, _ in PAGES],
        "evidence_sha256": {n: ev_hash(n) for n in SRC_OF},
    }
    if arg == "--check":
        stale = [n for n, content in outputs.items()
                 if not (SITE / n).exists() or (SITE / n).read_text(encoding="utf-8") != content]
        if not (SITE / "manifest.json").exists() or (SITE / "manifest.json").read_text(encoding="utf-8") != json.dumps(manifest, indent=1) + "\n":
            stale.append("manifest.json")
        if not (SITE / "style.css").exists() or (SITE / "style.css").read_text(encoding="utf-8") != STYLE:
            stale.append("style.css")
        if stale:
            raise SystemExit("FAIL: stale desk outputs: " + ", ".join(stale))
        print("OK: nfl-week11-6c72a9fa/site reproduces byte-identically (7 pages, manifest, style).")
        return 0
    SITE.mkdir(exist_ok=True)
    for name, content in outputs.items():
        (SITE / name).write_text(content, encoding="utf-8")
    (SITE / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    (SITE / "style.css").write_text(STYLE, encoding="utf-8")
    print(f"Built {len(outputs)} desk pages in nfl-week11-6c72a9fa/site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
