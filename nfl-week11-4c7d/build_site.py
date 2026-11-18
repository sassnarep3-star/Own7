#!/usr/bin/env python3
"""Deterministic site generator for the Week-11 decision desk (nfl-week11-4c7d).

Rules honoured by every page produced here:
  * each <tbody> row carries data-source-ids naming registered source IDs and at least one
    link to that registered official URL;
  * an unknown value is an empty cell with data-empty="true" -- never a guess, never a dash;
  * no price, odds, ROI, CLV, stake, wager or monetary reward appears anywhere;
  * the output is byte-identical on rebuild (`--check` enforces it).

Usage: python nfl-week11-4c7d/build_site.py [--check]
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SITE = HERE / "site"
DATA = HERE / "data"

PAGES = [
    ("index.html", "Overview"),
    ("executive-summary.html", "Executive summary"),
    ("standings.html", "Standings reconciliation"),
    ("gamebooks.html", "Game Book closure"),
    ("availability.html", "Availability join"),
    ("reliability.html", "Designation reliability"),
    ("snap-counts.html", "Snap-count probes"),
    ("fixtures.html", "Week 11 fixtures"),
    ("requirements.html", "Requirement delta"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

SID_STANDINGS = "W4C7D-NFL-STANDINGS"
SID_SCHED = "W4C7D-NFL-SCHED-W11"
SID_INJ = "W4C7D-NFL-INJ-W10"
SID_INJ11 = "W4C7D-NFL-INJ-W11"
SID_GC = "W4C7D-NFL-GAMECENTER-MNF"
SID_GB = "W4C7D-NFL-GAMEBOOK-MNF"
SID_STATS_PLAYER = "W4C7D-NFL-STATS-PLAYER"
SID_STATS_SNAPS = "W4C7D-NFL-STATS-SNAPCOUNTS"
SID_INACTIVES = "W4C7D-NFL-INACTIVES"
SID_REPO = "REPO"

REGISTRY: dict[str, str] = {}


def load_registry() -> dict[str, str]:
    reg = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
    if isinstance(reg, dict):
        reg = reg.get("sources", [])
    return {entry["id"]: entry["url"] for entry in reg}


def read_csv(name: str) -> list[dict]:
    path = DATA / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def cell(value, *, num=False, blank_note=None) -> str:
    if value is None or str(value).strip() == "":
        note = esc(blank_note or "Blank - not published by the official source; never inferred")
        cls = ' class="blank num"' if num else ' class="blank"'
        return f'<td{cls} data-empty="true" title="{note}"></td>'
    cls = ' class="num"' if num else ""
    return f"<td{cls}>{esc(value)}</td>"


def badge(text, kind="info") -> str:
    return f'<span class="badge {kind}">{esc(text)}</span>'


def refs_cell(source_ids) -> str:
    seen, links = set(), []
    for sid in source_ids:
        url = REGISTRY.get(sid)
        if url and url not in seen:
            seen.add(url)
            links.append(
                f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(sid)} &#8599;</a>'
            )
    return '<td class="refs">' + "".join(links) + "</td>"


def table(headers, rows_html, caption=None) -> str:
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    return (
        '<div class="table-card"><table>' + cap + f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table></div>"
    )


def row(cells, source_ids, row_id) -> str:
    ids = esc(" ".join(source_ids))
    return (
        f'<tr data-row-id="{esc(row_id)}" data-source-ids="{ids}">'
        + "".join(cells)
        + refs_cell(source_ids)
        + "</tr>"
    )


def section(title, body, eyebrow="", subtitle="", sid="") -> str:
    ident = f' id="{sid}"' if sid else ""
    eyebrow_html = f'<div class="eyebrow">{esc(eyebrow)}</div>' if eyebrow else ""
    sub = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    return (
        f'<section class="section"{ident}><div class="section-head"><div>'
        f"{eyebrow_html}<h2>{esc(title)}</h2>{sub}</div></div>{body}</section>"
    )


def notice(title, text, info=False) -> str:
    cls = "notice info" if info else "notice"
    return f'<div class="{cls}"><div><strong>{esc(title)}</strong><p>{esc(text)}</p></div></div>'


def metric(label, value, note) -> str:
    return (
        f'<div class="metric"><div class="metric-top">{esc(label)}</div>'
        f'<div class="metric-value">{esc(value)}</div><small>{esc(note)}</small></div>'
    )


def metrics(items) -> str:
    return '<div class="metric-grid">' + "".join(metric(l, v, n) for l, v, n in items) + "</div>"


# ------------------------------------------------------------------ page shell
STYLE = """\
:root{--ink:#16211a;--muted:#5c6b60;--line:#dfe7dc;--bg:#fbfdfa;--card:#fff;--good:#1f6b3f;--warn:#8a5a00;--bad:#8c2f2f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 20px 64px}
a{color:#1f5d3a}
.skip-link{position:absolute;left:-9999px}
.skip-link:focus{left:12px;top:12px;background:#fff;padding:8px 12px;z-index:9;border:1px solid var(--line)}
.eyebrow{text-transform:uppercase;letter-spacing:.09em;font-size:11px;font-weight:700;color:var(--muted)}
h1{font-size:29px;line-height:1.2;margin:.35em 0 .4em}
h2{font-size:20px;margin:0 0 .35em}
h3{font-size:16px;margin:1.2em 0 .4em}
p{max-width:82ch}
.lede{font-size:16px;color:#33403a;max-width:78ch}
nav.pages{display:flex;flex-wrap:wrap;gap:6px;margin:18px 0 8px}
nav.pages a{padding:6px 11px;border:1px solid var(--line);border-radius:999px;background:#fff;text-decoration:none;font-size:13px}
nav.pages a[aria-current=page]{background:#1f5d3a;color:#fff;border-color:#1f5d3a}
.section{margin:30px 0}
.section-head p{color:var(--muted);max-width:82ch;margin:.2em 0 0}
.table-card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:auto;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px}
caption{text-align:left;padding:12px 14px 0;font-weight:600;color:var(--muted);font-size:12.5px}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f3f7f1;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:#44534a;position:sticky;top:0}
tbody tr:hover{background:#f7fbf5}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.blank{background:repeating-linear-gradient(45deg,#fbfbf8,#fbfbf8 5px,#f4f4ef 5px,#f4f4ef 10px)}
td.refs{white-space:nowrap;font-size:12px}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:600;border:1px solid var(--line);background:#f4f7f2}
.badge.good{background:#eaf6ee;border-color:#bfe0cb;color:var(--good)}
.badge.warn{background:#fdf4e3;border-color:#ecd9a8;color:var(--warn)}
.badge.bad{background:#fbeaea;border-color:#ecc4c4;color:var(--bad)}
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:14px 0}
.metric{background:#fff;border:1px solid var(--line);border-radius:12px;padding:13px 15px}
.metric-top{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:700}
.metric-value{font-size:23px;font-weight:700;margin:4px 0 2px}
.metric small{color:var(--muted);font-size:12px}
.notice{border:1px solid var(--line);border-left:4px solid var(--warn);background:#fffdf6;border-radius:10px;padding:12px 14px;margin:14px 0}
.notice.info{border-left-color:#1f5d3a;background:#f6fbf7}
.notice p{margin:.2em 0 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin:14px 0}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 15px}
.card h2{font-size:16px;margin:0 0 .3em}
.card p{margin:0;font-size:13.5px;color:#3b4a41}
a.card-link{text-decoration:none;color:inherit;display:block}
a.card-link:hover{border-color:#1f5d3a}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px}
"""

APP_JS = """\
document.addEventListener('click',function(event){
  var trigger=event.target.closest('[data-sort]');
  if(!trigger)return;
  var table=trigger.closest('table');
  if(!table)return;
  var index=Number(trigger.dataset.sort);
  var body=table.tBodies[0];
  var rows=Array.prototype.slice.call(body.rows);
  var direction=trigger.dataset.direction==='asc'?'desc':'asc';
  trigger.dataset.direction=direction;
  rows.sort(function(a,b){
    var left=a.cells[index]?a.cells[index].textContent.trim():'';
    var right=b.cells[index]?b.cells[index].textContent.trim():'';
    var ln=parseFloat(left.replace(/[^0-9.\\-]/g,'')),rn=parseFloat(right.replace(/[^0-9.\\-]/g,''));
    if(!isNaN(ln)&&!isNaN(rn)&&left!==''&&right!==''&&/[-0-9.]/.test(left)&&/[-0-9.]/.test(right)){
      return direction==='asc'?ln-rn:rn-ln;
    }
    return direction==='asc'?left.localeCompare(right):right.localeCompare(left);
  });
  rows.forEach(function(r){body.appendChild(r);});
});
"""


def page(title, subtitle, body, eyebrow, current) -> str:
    nav = "".join(
        f'<a href="{name}"{" aria-current=page" if name == current else ""}>{esc(label)}</a>'
        for name, label in PAGES
    )
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{esc(title)} · OWN7 Week 11 decision desk</title>"
        "<meta name=\"description\" content=\"Official-source NFL capture and decision desk: Week 10 "
        "closure, standings reconciliation, availability joins, designation reliability and the "
        "gates that still block a backtest.\">"
        f"<style>{STYLE}</style><script defer src=\"app.js\"></script></head><body>"
        '<a class="skip-link" href="#main">Skip to content</a>'
        f"<main id=\"main\"><div class=\"eyebrow\">{esc(eyebrow)}</div>"
        f"<h1>{esc(title)}</h1><p class=\"lede\">{esc(subtitle)}</p>"
        f'<nav class="pages" aria-label="Desk sections">{nav}</nav>'
        f"{body}"
        "<footer><p>OWN7 · independent research. NFL data attributed to NFL.com and to each club's "
        "official site. Not affiliated with or endorsed by the NFL or any club. Every table row links "
        "the official source it came from; unknown values are blank, never filled in. Research only: "
        "no prices, no odds, no stakes, no wagers, no rewards.</p>"
        '<p><a href="sources.html">Source register</a> · <a href="flagged.html">Flagged for review</a>'
        ' · <a href="suggestions.html">Suggestions</a> · <a href="../../index.html">Back to the '
        "OWN7 landing page</a></p></footer></main></body></html>\n"
    )


# ------------------------------------------------------------------ pages
def build_index(summary) -> str:
    c = summary["counts"]
    h = summary["headline"]
    body = metrics(
        [
            ("Week 10 Game Books", f"{c['week10_gamebooks']} of 14", "every game in the slate, including the Monday-night closer"),
            ("Standings rows reconciled", f"{c['standings_rows']} of 32",
             f"{c['standings_mismatches']} mismatches against snapshot + result"),
            ("Availability rows joined", str(c["joined_rows_total"]), "report designation joined to official Not Active lists"),
            ("Inactives missing from the report", f"{c['week10_inactives_absent_from_report']} of {c['week10_inactives']}",
             "the reserve-list gap, measured"),
            ("Official sources probed", str(c["probes"]), "snap counts, inactives, the Week 11 report"),
            ("Questions on the record", str(c["questions"]), "each split into held / missing / closes it"),
            ("Ranked suggestions", str(c["suggestions"]), "each with adopt, defer and reject paths"),
            ("Flagged irregularities", str(c["flags"]), "published for review, non-blocking"),
        ]
    )
    body += section(
        "What this desk is",
        "<p>The brief asks for eight things before any number can be trusted: a price store, a "
        "verified results feed, three-stage origination, a fair-versus-market column, a leaderboard "
        "that separates signal from staking, replacement depth, correlations with n, and a demotion "
        "gate. Those live in the competition and readiness desks. This desk does the narrower job "
        "that was left undone on 2026-11-18: close Week 10 completely, prove the closure "
        "arithmetically, and say precisely which gates are still shut and what number would open "
        "each one.</p>"
        "<p>Everything here was read from an official page on 2026-11-18 and is retained verbatim in "
        "<code>evidence/</code> with a SHA-256. Nothing is inferred. Where an official source prints "
        "nothing, the cell is blank.</p>",
        eyebrow="SCOPE",
    )
    cards = [
        ("executive-summary.html", "Executive summary", "The short version: what changed, what is proven, what is still blocked."),
        ("standings.html", "Standings reconciliation", "32 clubs: snapshot 2026-11-17 plus the Monday-night result equals today's read."),
        ("gamebooks.html", "Game Book closure", "14 of 14 Week 10 games with venue, roof, surface, weather and attendance."),
        ("availability.html", "Availability join", "Report designations joined 1:1 to the official Not Active lists."),
        ("reliability.html", "Designation reliability", "What Out, Doubtful and Questionable actually did, with n and intervals."),
        ("snap-counts.html", "Snap-count probes", "Four official surfaces read; no official snap-count source exists on any of them."),
        ("fixtures.html", "Week 11 fixtures", "The upcoming slate as published, before kickoff, with byes."),
        ("requirements.html", "Requirement delta", "One row per requirement advanced, with the gate and the number that clears it."),
        ("questions.html", "Questions", "What we hold, what is missing, and what would close each gap."),
        ("suggestions.html", "Suggestions", "Eight ranked proposals, each with an adopt, defer and reject path."),
        ("flagged.html", "Flagged for review", "Irregularities found while doing this work, with official links."),
        ("sources.html", "Sources", "The registered official sources behind every row on this desk."),
    ]
    body += '<div class="cards">' + "".join(
        f'<a class="card card-link" href="{href}"><h2>{esc(t)}</h2><p>{esc(d)}</p></a>'
        for href, t, d in cards
    ) + "</div>"
    body += section(
        "The one-paragraph answer",
        f"<p>{esc(h['standings'])}. {esc(h['week10_closure'])}, and the Monday-night result is "
        f"{esc(h['mnf_final'])}. The availability join is now complete for the week: "
        f"{c['joined_rows_total']} rows across 28 clubs. Two facts dominate everything downstream. "
        f"First, {esc(h['reserve_gap'])} - so 'not listed' can never be read as 'available'. Second, "
        f"{esc(h['snap_counts'])}, which is why depth cannot yet be modelled from playing time. And "
        f"{esc(h['week11_report'])}, so no Week 11 personnel feature can honestly be built today.</p>",
        eyebrow="ANSWER",
    )
    return page("Overview", "What this desk did on 2026-11-18, and what it refuses to invent.",
                body, "Bounded snapshot · read 2026-11-18 · research only · no prices · no wagers",
                "index.html")


def build_executive_summary(summary) -> str:
    c = summary["counts"]
    h = summary["headline"]
    reliability = read_csv("designation-reliability.csv")
    req = read_csv("requirements-delta.csv")
    open_after = sum(1 for r in req if "open" in r["status_after"])
    body = section(
        "Executive summary",
        "<p><strong>Week 10 is closed and arithmetically proven.</strong> The Monday-night game that "
        "was still pending when the last capture ran is now final - "
        f"{esc(h['mnf_final'])} - and its official Game Book is captured. Every club's record, points "
        "for, points against, net points and percentage now reconcile from the 2026-11-17 snapshot "
        f"plus that one result: {c['standings_rows']} clubs, seven fields each, "
        f"{c['standings_mismatches']} mismatches.</p>"
        "<p><strong>The availability evidence is complete for the week.</strong> Official starters, "
        "substitutions, Did Not Play and Not Active lists are held for all 14 games and 28 clubs. "
        f"{c['joined_rows_total']} published report rows are joined 1:1 to the official Not Active "
        "lists, matched on club, surname and first initial so that two players with the same surname "
        "on one club cannot be confused.</p>"
        "<p><strong>Two facts constrain every model downstream.</strong> "
        f"{esc(h['reserve_gap'])} - injured reserve, a third quarterback, a practice-squad call-up or "
        "a club decision all produce an inactive who appears nowhere on the weekly report. And "
        f"{esc(h['snap_counts'])}, so depth cannot be modelled from playing time and the Game Book "
        "starter list is the only official playing-participation evidence available.</p>"
        f"<p><strong>{esc(h['week11_report'])}</strong> - on Wednesday 2026-11-18 the Week 11 URL "
        "serves the Week 10 report. This desk records that state rather than passing last week's "
        "report off as this week's baseline.</p>"
        "<p><strong>A new leak surface was found.</strong> The injury report re-renders club records "
        "after kickoff: the identical Monday rows printed LAC (0-8) and BAL (4-5) on 2026-11-17 and "
        "print LAC (1-8) and BAL (4-6) on 2026-11-18. A snapshot taken after kickoff therefore "
        "carries the result. Capture must be pre-kickoff, always.</p>"
        "<p><strong>Nothing here prices anything.</strong> No price, odds, ROI, closing-line value, "
        "stake, wager or reward appears on any page of this desk, because no official source this "
        "project may store publishes one.</p>",
        eyebrow="SUMMARY",
    )
    rel_rows = [
        row(
            [cell(r["published_designation"]), cell(r["n_rows_joined"], num=True),
             cell(r["n_on_official_not_active"], num=True), cell(r["observed_inactive_rate"], num=True),
             cell(f'{r["wilson_95_low"]} to {r["wilson_95_high"]}'), cell(r["usable_as_model_feature"])],
            [SID_INJ, SID_GB],
            f'rel-{r["published_designation"].replace(" ", "-").strip("()")}',
        )
        for r in reliability
    ]
    body += section(
        "What each designation actually did",
        table(
            ["Published designation", "n joined", "Not active", "Rate", "95% Wilson interval",
             "Usable as a feature?", "Source"],
            rel_rows,
            "Joined on club, surname and first initial; Wilson score interval at 95%.",
        )
        + notice("Read the interval, not the rate",
                 "Questionable has 18 rows and an interval from 0.1250 to 0.5087. That is a "
                 "measurement of one week of one season, not a calibration. No legacy percentage is "
                 "used anywhere, because the official text publishes none.", info=True),
        eyebrow="CALIBRATION",
    )
    body += section(
        "Where the gates stand",
        f"<p>{len(req)} requirements were advanced or re-examined by this desk. "
        f"{open_after} remain open, each with the specific gate that blocks it and the number that "
        "would clear it - see the requirement delta. Nothing is blocked by method; everything is "
        "blocked by an absent official source or an absent permission.</p>",
        eyebrow="GATES",
    )
    return page("Executive summary", "The short version of what changed, what is proven and what is still blocked.",
                body, "Executive summary · 2026-11-18", "executive-summary.html")


def build_standings() -> str:
    rows = read_csv("standings-reconciliation.csv")
    body = section(
        "Every club reconciles from the snapshot plus one result",
        "<p>The retained 2026-11-17 snapshot was taken before the Monday-night game. Adding that "
        "game's official score to the two clubs that played it - and to no one else - must reproduce "
        "the standings page read on 2026-11-18. It does, for all 32 clubs and all seven checked "
        "fields: wins, losses, ties, percentage, points for, points against and net points. The "
        "percentage is recomputed as (wins + half the ties) divided by games played and compared to "
        "the figure the page prints.</p>"
        + notice("Why this matters",
                 "A results feed that reconciles to the official standings on every club field cannot "
                 "be silently wrong about a game. It is the cheapest available proof that the corpus "
                 "is complete.", info=True),
        eyebrow="RECONCILIATION",
    )
    body_rows = [
        row(
            [cell(r["club"]), cell(r["conference"]), cell(r["division"]),
             cell(f'{r["snapshot_W"]}-{r["snapshot_L"]}-{r["snapshot_T"]}'),
             cell(f'{r["snapshot_PF"]}-{r["snapshot_PA"]}'), cell(r["mnf_result_applies"]),
             cell(f'{r["expected_W"]}-{r["expected_L"]}-{r["expected_T"]}'),
             cell(f'{r["expected_PF"]}-{r["expected_PA"]}'), cell(r["expected_PCT"], num=True),
             cell(f'{r["read_2026_11_18_W"]}-{r["read_2026_11_18_L"]}-{r["read_2026_11_18_T"]}'),
             cell(f'{r["read_2026_11_18_PF"]}-{r["read_2026_11_18_PA"]}'),
             cell(r["read_2026_11_18_PCT"], num=True),
             cell(r["all_seven_fields_match"]), cell(r["read_2026_11_18_Strk"]),
             cell(r["read_2026_11_18_Last5"])],
            [SID_STANDINGS, SID_GC, SID_GB],
            "std-" + r["club"].lower().replace(" ", "-"),
        )
        for r in rows
    ]
    body += section(
        "The 32 clubs, line by line",
        table(
            ["Club", "Conf", "Division", "Snapshot W-L-T", "Snapshot PF-PA", "Monday result applies?",
             "Expected W-L-T", "Expected PF-PA", "Expected PCT", "Read W-L-T", "Read PF-PA",
             "Read PCT", "All 7 match", "Streak", "Last 5", "Source"],
            body_rows,
            "Snapshot 2026-11-17 (retained) + official Monday-night result = the official standings "
            "read on 2026-11-18.",
        ),
        eyebrow="LINE BY LINE",
    )
    return page("Standings reconciliation", "32 clubs, seven fields each: the snapshot plus one result equals today's read.",
                body, "Verification · 2026-11-18", "standings.html")


def build_gamebooks() -> str:
    closure = read_csv("week10-gamebook-closure.csv")
    people = read_csv("mnf-lineups-and-inactives.csv")
    body = section(
        "Week 10 is closed: 14 of 14 games",
        "<p>The previous capture held 13 of 14 games; the Monday-night game had not finished. It has "
        "now. Every game in the slate carries an official Game Book, and every Game Book prints the "
        "stadium, the city, the roof and surface description, the game weather, temperature, "
        "humidity, wind and paid attendance. Those are the fixture-context fields the brief asks "
        "for, and they come from the league's own document rather than from a third party.</p>"
        + notice("Two games print no weather at all",
                 "Mercedes-Benz Stadium and Caesars Superdome leave the weather, temperature, "
                 "humidity and wind cells empty in the official Game Book, while two other indoor "
                 "games do print weather. Those four cells are blank on this page because the source "
                 "printed nothing - not because the value is zero.", info=True)
        + notice("The weather is only official after the fact",
                 "These weather fields are printed in the post-game Game Book. A pre-kickoff forecast "
                 "for the same venue is a different dataset and is not published on the surfaces this "
                 "desk read, so no pre-game weather cell is filled in.", info=True),
        eyebrow="CLOSURE",
    )
    body_rows = [
        row(
            [cell(r["game_id"]), cell(r["away"]), cell(r["home"]), cell(r["date"]), cell(r["kickoff"]),
             cell(r["stadium"]), cell(r["city"]), cell(r["roof_and_surface"]), cell(r["weather"]),
             cell(r["temp_f"], num=True), cell(r["humidity_pct"], num=True), cell(r["wind"]),
             cell(r["attendance"], num=True), cell(r["captured_by"])],
            [SID_GB if r["gamebook_url"] else SID_GC, SID_GC],
            r["game_id"].lower(),
        )
        for r in closure
    ]
    body += section(
        "Venue, roof, surface and weather for every game",
        table(
            ["Game", "Away", "Home", "Date", "Kickoff", "Stadium", "City", "Roof and surface",
             "Weather", "Temp F", "Humidity %", "Wind", "Attendance", "Captured by", "Source"],
            body_rows,
            "Thirteen rows retained by the Game Book desk (read-only) plus the Monday-night game "
            "captured by this desk on 2026-11-18.",
        ),
        eyebrow="FIXTURE CONTEXT",
    )
    mnf = [p for p in people]
    body_rows = [
        row(
            [cell(p["row_id"]), cell(p["game_id"]), cell(p["club"]), cell(p["position"]),
             cell(p["jersey"], num=True), cell(p["player"]), cell(p["status"]), cell(p["captured_utc"])],
            [SID_GB],
            p["row_id"].lower(),
        )
        for p in mnf
    ]
    body += section(
        "The Monday-night game in full",
        table(
            ["Row", "Game", "Club", "Position", "Jersey", "Player", "Official status", "Captured",
             "Source"],
            body_rows,
            "Official Game Book for Los Angeles Chargers at Baltimore Ravens, 2026 REG 10: 44 "
            "starters, 12 Not Active, 5 dressed but Did Not Play.",
        )
        + notice("Three official statuses, not two",
                 "The Game Book separates 'Not Active' (deactivated) from 'Did Not Play' (dressed and "
                 "available but unused). Conflating them would overstate the injury effect; this desk "
                 "keeps them apart.", info=True),
        eyebrow="MNF CAPTURE",
    )
    return page("Game Book closure", "Every Week 10 game captured, with venue, environment and official statuses.",
                body, "Official Game Books · Week 10 2026", "gamebooks.html")


def build_availability() -> str:
    join = read_csv("availability-delta-mnf.csv")
    coverage = read_csv("inactive-coverage.csv")
    body = section(
        "Report designation against what actually happened",
        "<p>Each row of the weekly injury report is joined to the official Game Book Not Active list "
        "for the same club and game. The join key is club, surname and first initial: New England's "
        "report carries both A.J. Brown and Ben Brown, and the Game Book inactivates B.Brown, so a "
        "surname-only match would name the wrong man. Generational suffixes are stripped for the same "
        "reason - the report prints Carlton Davis III where the Game Book prints C.Davis.</p>",
        eyebrow="JOIN",
    )
    body_rows = [
        row(
            [cell(r["delta_id"]), cell(r["club"]), cell(r["player"]), cell(r["position"]),
             cell(r["injury"]), cell(r["practice_status"]), cell(r["designation"]),
             cell(r["outcome_from_gamebook"]), cell(r["delta"])],
            [SID_INJ, SID_GB],
            r["delta_id"].lower(),
        )
        for r in join
    ]
    body += section(
        "The Monday-night game, row by row",
        table(
            ["Row", "Club", "Player", "Pos", "Injury", "Practice status", "Published designation",
             "Official outcome", "Delta", "Source"],
            body_rows,
            "29 published report rows for the Monday-night game, joined to the official Not Active "
            "list.",
        ),
        eyebrow="MNF JOIN",
    )
    cov_rows = [
        row(
            [cell(r["game_id"]), cell(r["official_not_active_count"], num=True),
             cell(r["matched_to_a_report_row"], num=True), cell(r["absent_from_the_report"], num=True),
             cell(r["share_absent"], num=True)],
            [SID_GB, SID_INJ],
            "cov-" + r["game_id"].lower().replace(" ", "-").replace("(", "").replace(")", ""),
        )
        for r in coverage
    ]
    body += section(
        "The reserve-list gap, measured",
        table(
            ["Game", "Official Not Active", "Matched to a report row", "Absent from the report",
             "Share absent", "Source"],
            cov_rows,
            "For every official inactive: does that player appear anywhere on the weekly report?",
        )
        + notice("'Not listed' is not 'available'",
                 "A majority of official inactives appear nowhere on the weekly injury report. The "
                 "reasons are legion - injured reserve, the emergency third quarterback, a "
                 "practice-squad activation, a club decision - and none of them is printed on the "
                 "report page. Treating an absent row as a healthy player is wrong more often than "
                 "it is right.", info=True),
        eyebrow="RESERVE GAP",
    )
    return page("Availability join", "What the report said, what the Game Book says happened, and the gap between them.",
                body, "Availability · Week 10 2026", "availability.html")


def build_reliability() -> str:
    rows = read_csv("designation-reliability.csv")
    body = section(
        "Do the labels mean anything?",
        "<p>The brief asks for an empirical calibration of 'Questionable' instead of a legacy "
        "percentage. This is the honest version of that answer: a rate per designation, the sample "
        "size behind it, and a 95% Wilson interval that shows how far the truth could still move.</p>"
        + notice("One season is not a calibration",
                 "Out and Questionable each hold 18 joined rows. The interval for Questionable runs "
                 "from 0.1250 to 0.5087 - wide enough to contain both 'rarely' and 'about half'. "
                 "Publishing a point estimate here would be an invention.", info=True),
        eyebrow="RELIABILITY",
    )
    body_rows = [
        row(
            [cell(r["published_designation"]), cell(r["n_rows_joined"], num=True),
             cell(r["n_on_official_not_active"], num=True), cell(r["observed_inactive_rate"], num=True),
             cell(r["wilson_95_low"], num=True), cell(r["wilson_95_high"], num=True),
             cell(r["interval_width"], num=True), cell(r["weeks_joined"]),
             cell(r["usable_as_model_feature"])],
            [SID_INJ, SID_GB],
            "rel-" + r["published_designation"].lower().replace(" ", "-").strip("()"),
        )
        for r in rows
    ]
    body += section(
        "Rate, sample and interval per designation",
        table(
            ["Published designation", "n joined", "Not active", "Observed rate", "Wilson low",
             "Wilson high", "Interval width", "Weeks joined", "Usable as a feature?", "Source"],
            body_rows,
            "2026 REG 10, complete slate: 329 rows joined across 14 games and 28 clubs.",
        ),
        eyebrow="NUMBERS",
    )
    body += section(
        "What would turn this into a calibration",
        "<p>Archived weekly injury reports for at least two further seasons, joined the same way. "
        "That is requirement R66 and it is the only route: no amount of extra current-week data "
        "narrows an interval that is limited by how many times a designation has been published at "
        "all.</p>",
        eyebrow="PATH",
    )
    return page("Designation reliability", "What Out, Doubtful and Questionable actually did, with n and intervals.",
                body, "Calibration · Week 10 2026", "reliability.html")


def build_snap_counts() -> str:
    probes = read_csv("source-probes.csv")
    body = section(
        "Is there an official snap-count source?",
        "<p>The brief asks twice for depth to be modelled from playing time rather than from jersey "
        "order, and once for snap counts to stand in when a club publishes no depth chart. All three "
        "requirements depend on one thing existing: an official source that publishes how much each "
        "player played. This desk read four official surfaces looking for it, and one more for the "
        "inactive-list question, and recorded exactly what each one rendered.</p>",
        eyebrow="QUESTION",
    )
    body_rows = [
        row(
            [cell(p["probe_id"]), cell(p["question"]), cell(p["url"]), cell(p["what_rendered"]),
             cell(p["verdict"]), cell(p["unblocks"]), cell(p["read_utc"])],
            [SID_STATS_PLAYER if "player-stats" in p["url"] else
             SID_STATS_SNAPS if "snapcounts" in p["url"] else
             SID_INACTIVES if "inactives" in p["url"] else
             SID_INJ11 if "REG11" in p["url"] else SID_GB],
            p["probe_id"].lower(),
        )
        for p in probes
    ]
    body += section(
        "Every probe, and what it returned",
        table(
            ["Probe", "Question", "URL read", "What the page rendered", "Verdict", "Unblocks",
             "Read", "Source"],
            body_rows,
            "Read on 2026-11-18. Absence of evidence on these surfaces is not proof that no official "
            "snap product exists anywhere - for example behind a licensed feed - and this desk claims "
            "nothing about products it did not read.",
        ),
        eyebrow="PROBES",
    )
    body += section(
        "What we use instead, and what it cannot do",
        "<p>The official Game Book prints lineups, substitutions, Did Not Play and Not Active. That "
        "is official playing-participation evidence: it tells you who started and who was unavailable. "
        "It does not tell you how much anyone played, so it cannot distinguish a starter who played "
        "every snap from one who left after six. Until an official snap-count source is found, every "
        "playing-time requirement stays open - not for lack of method, but for lack of a source.</p>"
        + notice("Explicitly rejected",
                 "Deriving depth order from jersey number, experience or salary was proposed earlier "
                 "in this project and rejected in the brief. This desk rejects it again: none of "
                 "those three is a measure of playing time.", info=True),
        eyebrow="SUBSTITUTE",
    )
    return page("Snap-count probes", "Four official surfaces read; no official snap-count source exists on any of them.",
                body, "Source resolution · 2026-11-18", "snap-counts.html")


def build_fixtures() -> str:
    games = read_csv("fixtures-week11.csv")
    byes = read_csv("byes-week11.csv")
    body = section(
        "The Week 11 slate as published, before kickoff",
        "<p>Read on Wednesday 2026-11-18, before the first game. The stadium column is transcribed "
        "only where the schedule page itself prints one - the page's own hotel link names the venue "
        "for most fixtures. Where it does not, the cell is blank and flagged rather than filled from "
        "memory.</p>"
        + notice("Kickoff times carry no timezone on the page",
                 "The schedule page prints times without a zone. They are transcribed exactly as "
                 "printed and the timezone is left blank rather than assumed.", info=True),
        eyebrow="SLATE",
    )
    body_rows = [
        row(
            [cell(g["seq"], num=True), cell(g["date"]), cell(g["weekday"]),
             cell(g["kickoff_as_printed"]), cell(g["kickoff_timezone"]), cell(g["network"]),
             cell(g["away"]), cell(g["away_record_on_page"]), cell(g["home"]),
             cell(g["home_record_on_page"]), cell(g["stadium_printed_on_page"]), cell(g["status"])],
            [SID_SCHED],
            f'fix-{g["seq"]}',
        )
        for g in games
    ]
    body += section(
        "Fixtures",
        table(
            ["#", "Date", "Day", "Kickoff (as printed)", "Timezone", "Network", "Away", "Away record",
             "Home", "Home record", "Stadium on the page", "Status", "Source"],
            body_rows,
            "13 fixtures; 26 clubs play and 6 are on bye, which completes the 32.",
        ),
        eyebrow="FIXTURES",
    )
    bye_rows = [
        row([cell(b["club"]), cell(b["record_on_page"]), cell(b["week"], num=True)],
            [SID_SCHED], f'bye-{b["club"].lower()}')
        for b in byes
    ]
    body += section(
        "Clubs on bye",
        table(["Club", "Record on the page", "Week", "Source"], bye_rows,
              "A bye week produces no injury-report table for that club."),
        eyebrow="BYES",
    )
    body += section(
        "What the league has already said about the late season",
        "<p>The same schedule page carries the league's own '2026 TBD Games' note: in Week 16 two "
        "designated matchups move to Saturday and the dates are fixed no later than immediately after "
        "Week 14; in Week 17 the same applies with dates fixed no later than immediately after Week "
        "15; in Week 18 three games move to Saturday with dates fixed after Week 17. Any fixture-"
        "context feature built for those weeks is incomplete by league design until those dates are "
        "announced.</p>",
        eyebrow="KNOWN UNKNOWNS",
    )
    return page("Week 11 fixtures", "The upcoming slate exactly as the official schedule page prints it.",
                body, "Fixture context · Week 11 2026", "fixtures.html")


def build_requirements() -> str:
    rows = read_csv("requirements-delta.csv")
    body = section(
        "Requirement delta: what moved, and what still blocks it",
        "<p>One row per requirement this desk advanced or re-examined. 'Status before' is the "
        "readiness crosswalk as this desk found it; 'status after' is where it stands with this "
        "desk's evidence. Every open row names the gate that blocks it and the concrete number that "
        "would clear it - no row is left with a vague blocker.</p>",
        eyebrow="DELTA",
    )
    body_rows = [
        row(
            [cell(r["req_id"]), cell(r["requirement"]), cell(r["status_before"]),
             cell(r["status_after"]), cell(r["what_this_desk_did"]), cell(r["blocking_gate"]),
             cell(r["gate_meaning"]), cell(r["number_that_would_clear_it"])],
            [SID_GB, SID_INJ if "injuries" in r["source_url"] else SID_GC],
            r["req_id"].lower(),
        )
        for r in rows
    ]
    body += section(
        "The rows",
        table(
            ["Req", "Requirement", "Before", "After", "What this desk did", "Gate", "Gate meaning",
             "Number that would clear it", "Source"],
            body_rows,
            "Ten requirements; each row links the official source behind the work described.",
        ),
        eyebrow="ROWS",
    )
    return page("Requirement delta", "What moved on 2026-11-18, the gate that still blocks it, and the number that clears it.",
                body, "Decision readiness · 2026-11-18", "requirements.html")


def build_questions() -> str:
    rows = read_csv("questions.csv")
    body = section(
        "The questions that must be answered before a decision is reasonable",
        "<p>Each question is split three ways: the information we hold, the information that is "
        "missing, and the specific thing that would close the gap. Nothing here is answered with a "
        "guess - where the official record is silent, the answer says so.</p>",
        eyebrow="QUESTIONS",
    )
    body_rows = [
        row(
            [cell(r["q_id"]), cell(r["question"]), cell(r["information_we_hold"]),
             cell(r["information_missing"]), cell(r["what_would_close_it"]),
             cell(r["decision_it_blocks"]), cell(r["verified"])],
            [SID_INJ if "injuries" in r["source_url"] else
             SID_STANDINGS if "standings" in r["source_url"] else
             SID_SCHED if "by-week" in r["source_url"] else SID_GC],
            r["q_id"].lower(),
        )
        for r in rows
    ]
    body += section(
        "Held, missing, and what closes the gap",
        table(
            ["#", "Question", "Information we hold", "Information missing", "What would close it",
             "Decision it blocks", "Verified", "Source"],
            body_rows,
            "Ten questions. Where a source link was not re-read today this is stated in the "
            "'Verified' column rather than implied.",
        ),
        eyebrow="THE LIST",
    )
    return page("Questions", "What we hold, what is missing, and what would close each gap.",
                body, "Decision questions · 2026-11-18", "questions.html")


def build_suggestions() -> str:
    rows = read_csv("suggestions.csv")
    body = section(
        "Ranked suggestions, each with three paths",
        "<p>Ranked by how much blocked work each one unblocks per unit of effort. Every suggestion "
        "carries an adopt path, a defer path and a reject path, so a reviewer can choose rather than "
        "simply accept. Nothing here has been implemented by this desk: these are proposals, and the "
        "decision record starts empty on purpose.</p>",
        eyebrow="SUGGESTIONS",
    )
    body_rows = [
        row(
            [cell(r["s_id"]), cell(r["rank"], num=True), cell(r["suggestion"]), cell(r["why"]),
             cell(r["cost"]), cell(r["unblocks"]), cell(r["adopt_path"]), cell(r["defer_path"]),
             cell(r["reject_path"])],
            [SID_REPO, SID_GB if "gamecenter" in r["evidence_url"] else SID_INJ],
            r["s_id"].lower(),
        )
        for r in rows
    ]
    body += section(
        "The list",
        table(
            ["#", "Rank", "Suggestion", "Why", "Cost", "Unblocks", "Adopt path", "Defer path",
             "Reject path", "Source"],
            body_rows,
            "Eight proposals in priority order.",
        ),
        eyebrow="THE LIST",
    )
    body += section(
        "How to use this page",
        "<p>Pick the highest-ranked suggestion whose adopt path you are willing to fund, write the "
        "decision into the repository, and the gates it unblocks open. Deferring is a valid answer "
        "and is recorded as such - the only destructive choice is the reject path, and each row says "
        "what it costs.</p>",
        eyebrow="REVIEW",
    )
    return page("Suggestions", "Eight ranked proposals, each with an adopt, defer and reject path.",
                body, "Suggestions · 2026-11-18", "suggestions.html")


def build_flagged() -> str:
    rows = read_csv("flags.csv")
    body = section(
        "Flagged for review",
        "<p>Irregularities found while doing this desk's work. None of them blocks the merge: each is "
        "published here with the official source that produced it so it can be reviewed after the "
        "site is live.</p>"
        + notice("Nothing was silently corrected",
                 "Where two official reads disagree, this desk publishes both and the date of each "
                 "read rather than picking one.", info=True),
        eyebrow="FLAGGED",
    )
    body_rows = [
        row(
            [cell(r["flag_id"]), cell(r["severity"]), cell(r["title"]), cell(r["detail"]),
             cell(r["action"])],
            [SID_INJ if "injuries" in r["source_url"] else
             SID_SCHED if "by-week" in r["source_url"] else
             SID_INACTIVES if "inactives" in r["source_url"] else SID_GB],
            r["flag_id"].lower(),
        )
        for r in rows
    ]
    body += section(
        "The register",
        table(["Flag", "Severity", "Title", "Detail", "Recommended action", "Source"], body_rows,
              f"{len(rows)} flags: "
              + ", ".join(
                  f"{n} {sev}" for sev, n in
                  sorted({(f['severity'], sum(1 for r in rows if r['severity'] == f['severity']))
                          for f in rows}.__iter__())
              ) + "."),
        eyebrow="REGISTER",
    )
    return page("Flagged for review", "Irregularities found on 2026-11-18, published with the official source for each.",
                body, "Flagged for review · 2026-11-18", "flagged.html")


def build_sources(summary) -> str:
    ids = [SID_STANDINGS, SID_SCHED, SID_INJ, SID_INJ11, SID_GC, SID_GB, SID_STATS_PLAYER,
           SID_STATS_SNAPS, SID_INACTIVES, SID_REPO]
    reg = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in reg}
    body = section(
        "Sources behind this desk",
        "<p>Every table row on this desk carries at least one link to a source registered in the "
        "repository's source register. The register records the publisher, the authority, the exact "
        "scope used, the date checked and the access boundary - an Arena-rendered read is not a "
        "direct HTTP-status attestation, and the register says so.</p>",
        eyebrow="REGISTER",
    )
    body_rows = [
        row(
            [cell(i), cell(by_id[i]["publisher"]), cell(by_id[i]["title"]),
             cell(by_id[i].get("kind", "")), cell(by_id[i].get("scope", "")),
             cell(by_id[i].get("checked_on", "")), cell(by_id[i].get("status", ""))],
            [i],
            "src-" + i.lower(),
        )
        for i in ids
    ]
    body += section(
        "The nine sources this desk added, plus the repository record",
        table(["ID", "Publisher", "Title", "Kind", "Scope", "Checked", "Status", "Source"], body_rows,
              "Registered in research/sources.json; hosts are pinned in scripts/check_site.py."),
        eyebrow="SOURCES",
    )
    ev = summary["evidence_sha256"]
    ev_rows = [
        row([cell(name), cell(digest)], [SID_REPO], "ev-" + name.replace(".", "-").replace(" ", "-"))
        for name, digest in ev.items()
    ]
    body += section(
        "Retained evidence and its hashes",
        table(["Evidence file", "SHA-256", "Source"], ev_rows,
              "Verbatim transcripts of the official pages read on 2026-11-18, retained under "
              "nfl-week11-4c7d/evidence/."),
        eyebrow="EVIDENCE",
    )
    body += section(
        "Reuse notice, stated plainly",
        "<p>Every official NFL Game Book carries this notice: 'This summary and play-by-play is for "
        "the express purpose of assisting media in their coverage of the game; any other use of this "
        "material is prohibited without the written permission of the National Football League.' This "
        "desk publishes derived counts and links to the official artefact. It does not republish the "
        "raw document.</p>",
        eyebrow="RIGHTS",
    )
    return page("Sources", "The registered official sources and retained evidence behind every row on this desk.",
                body, "Source register · 2026-11-18", "sources.html")


def build() -> None:
    REGISTRY.update(load_registry())
    result = subprocess.run([sys.executable, str(HERE / "build.py")], cwd=REPO,
                            capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(result.stdout + result.stderr)
    summary = load_json("summary.json")
    SITE.mkdir(exist_ok=True)
    builders = {
        "index.html": lambda: build_index(summary),
        "executive-summary.html": lambda: build_executive_summary(summary),
        "standings.html": build_standings,
        "gamebooks.html": build_gamebooks,
        "availability.html": build_availability,
        "reliability.html": build_reliability,
        "snap-counts.html": build_snap_counts,
        "fixtures.html": build_fixtures,
        "requirements.html": build_requirements,
        "questions.html": build_questions,
        "suggestions.html": build_suggestions,
        "flagged.html": build_flagged,
        "sources.html": lambda: build_sources(summary),
    }
    for name, _label in PAGES:
        (SITE / name).write_text(builders[name](), encoding="utf-8")
    (SITE / "style.css").write_text(STYLE, encoding="utf-8")
    (SITE / "app.js").write_text(APP_JS, encoding="utf-8")
    (SITE / "manifest.json").write_text(
        json.dumps({"pages": [n for n, _ in PAGES]}, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Built {len(PAGES)} pages for nfl-week11-4c7d.")


def check() -> int:
    before = {p: p.read_bytes() for p in sorted(SITE.glob("*.html"))}
    build()
    after = {p: p.read_bytes() for p in sorted(SITE.glob("*.html"))}
    if before and before != after:
        changed = [p.name for p in before if before[p] != after.get(p)]
        raise SystemExit("deterministic rebuild changed files: " + ", ".join(changed))
    print("OK: deterministic rebuild is byte-identical.")
    return 0


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else build())
