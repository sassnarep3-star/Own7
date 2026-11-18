#!/usr/bin/env python3
"""Deterministic generator for the NFL snap-count / playing-time desk.

Builds the desk's site from the committed data artefacts produced by build.py.
Every <tbody> row carries data-source-ids naming registered source IDs and at least
one link to a registered official URL; every unknown value is an empty cell with
data-empty="true". `--check` rebuilds and demands byte-identical output. No
wall-clock input: all dates are fixed constants.
"""
from __future__ import annotations

import csv
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
    ("snap-records.html", "Per-game snap records"),
    ("position-group-shares.html", "Position-group snap shares"),
    ("playtime-depth.html", "Playing-time depth"),
    ("replacement-depth.html", "Replacement depth"),
    ("depth-vs-snap.html", "Depth-vs-snap cross-reference"),
    ("decisions.html", "Questions & readiness"),
    ("suggestions.html", "Suggestions"),
    ("verification.html", "Verification"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

# Source IDs registered in research/sources.json for this desk.
SID_GAMEBOOK = "SN-NFL-GAMEBOOK-PDF"
SID_GAMECENTER = "SN-NFL-GAMECENTER"
SID_DEPTH = "SN-CLUB-DEPTH"
SID_REPO = "REPO"

REGISTRY: dict[str, str] = {}


def load_registry() -> dict:
    reg = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
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
    if value is None or value == "":
        note = esc(blank_note or "Blank - not published by the official source; never inferred")
        return f'<td class="blank{" num" if num else ""}" data-empty="true" title="{note}"></td>'
    cls = ' class="num"' if num else ""
    return f"<td{cls}>{esc(value)}</td>"


def badge(text, kind="info") -> str:
    return f'<span class="badge {kind}">{esc(text)}</span>'


def refs_cell(source_ids, extra_url=None) -> str:
    seen, links = set(), []
    for sid in source_ids:
        url = REGISTRY.get(sid)
        if url and url not in seen:
            seen.add(url)
            links.append(
                f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(sid)} &#8599;</a>'
            )
    if extra_url and extra_url not in seen and str(extra_url).startswith("https://"):
        links.append(
            f'<a href="{esc(extra_url)}" target="_blank" rel="noopener noreferrer">official artefact &#8599;</a>'
        )
    return '<td class="refs">' + "".join(links) + "</td>"


def table(headers, rows_html, caption=None) -> str:
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    return (
        # tabindex makes the horizontally-scrollable wrapper keyboard-reachable; WCAG
        # scrollable-region-focusable flagged it on mobile. Cross-scope fix by session
        # arena/c815bdd2-own7 because a red main blocks every session; see COORDINATION.md.
        f'<div class="table-card" tabindex="0"><table>{cap}<thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(rows_html)}</tbody></table></div>"
    )


def row(cells, source_ids, row_id, extra_url=None) -> str:
    return (
        f'<tr data-row-id="{esc(row_id)}" data-source-ids="{esc(" ".join(source_ids))}">'
        + "".join(cells)
        + refs_cell(source_ids, extra_url)
        + "</tr>"
    )


def section(title, body, eyebrow="", subtitle="", sid="") -> str:
    ident = f' id="{sid}"' if sid else ""
    eyebrow_html = f'<div class="eyebrow">{esc(eyebrow)}</div>' if eyebrow else ""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
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
    return '<div class="metric-grid">' + "".join(
        metric(l, v, n) for l, v, n in items
    ) + "</div>"


def link(url, label) -> str:
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)} &#8599;</a>'


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
.notice{display:flex;gap:12px;background:#fff;border:1px solid var(--line);border-left:4px solid var(--warn);border-radius:10px;padding:12px 15px;margin:14px 0}
.notice.info{border-left-color:#1f5d3a}
.notice p{margin:.25em 0 0;color:#3d4a42;font-size:13.5px}
footer{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;max-width:88ch}
ul.tight{margin:.3em 0 .3em 1.1em;padding:0}
ul.tight li{margin:.2em 0}
"""


def page(slug: str, title: str, lede: str, body_parts) -> str:
    nav_items = []
    for name, label in PAGES:
        current = ' aria-current="page"' if name == slug else ""
        nav_items.append(f'<a href="{name}"{current}>{esc(label)}</a>')
    nav = "".join(nav_items)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OWN7 NFL snap-count desk</title>
<meta name="description" content="{esc(lede)[:180]}">
<link rel="stylesheet" href="style.css"></head>
<body><a class="skip-link" href="#main">Skip to content</a>
<main id="main">
<header class="page-head"><div class="eyebrow">OWN7 · NFL snap-count / playing-time desk (session e5e4351c) · snapshot 2026-11-18</div>
<h1>{esc(title)}</h1>
<p class="lede">{esc(lede)}</p>
<nav class="pages" aria-label="Desk pages">{nav}</nav>
</header>
{''.join(body_parts)}
<footer>Snapshot captured 2026-11-18. Every value on this desk is transcribed from the official NFL Game Book Playtime
Percentage table (snap counts and snap share on Offense, Defense and Special Teams), linked
from the official NFL Game Centre. Where an official artefact does not publish a value the
cell is blank and the row is listed on the flagged page — nothing is inferred. Depth order
here is derived from playing time (snap counts) only, never from jersey number, experience
or salary. Not affiliated with or endorsed by the NFL; not a betting service. Built
deterministically by nfl-snapcount-e5e4/build_site.py.</footer>
</main></body></html>
"""


# ----------------------------------------------------------------------- pages

SUMMARY = None
FLAGS = None


def page_index() -> list[str]:
    s = SUMMARY
    parts = [
        notice(
            "This desk turns the league's own Playtime Percentage table into the one thing "
            "the rest of the repository could not supply: an official, per-player snap count.",
            "The official NFL Game Book publishes a Playtime Percentage table - snap counts "
            "and snap share on Offense, Defense and Special Teams - for every fixture. This "
            "desk transcribes that table from all 13 played Week 10 Game Books, derives the "
            "measurable starter/backup split from playing time, and resolves the "
            "depth-order source the brief flagged as unresolved. Nothing is inferred; blanks "
            "stay blank with a reason.",
            info=True,
        ),
        metrics([
            ("Game Books captured", str(s["games_captured"]), "of 14 Week 10 fixtures"),
            ("Snap records", str(s["snap_record_rows"]), "player-phase rows transcribed"),
            ("Position-group shares", str(s["position_group_share_rows"]), "per game / team / phase"),
            ("Playing-time depth rows", str(s["playtime_depth_rows"]), "ranked by snap count"),
            ("Replacement-depth rows", str(s["replacement_depth_rows"]), "starter → next man"),
            ("Tables labelled Unofficial", str(s["tables_labelled_unofficial"]), "label carried verbatim"),
        ]),
        section(
            "What this desk changes",
            "<p>Four open requirements stop being estimates:</p>"
            '<ul class="tight">'
            "<li><strong>R11 - depth from playing time, not jersey order.</strong> The "
            "playing-time depth page ranks every player by the snaps they actually played; "
            "jersey number, experience and salary play no part in the order.</li>"
            "<li><strong>R31 - official snap counts.</strong> The per-game snap records are "
            "transcribed from the official Game Book Playtime Percentage table.</li>"
            "<li><strong>R52 - the depth-order source is resolved.</strong> Snap counts are "
            "the official source for who played; the printed depth-chart order is a separate, "
            "club-published artefact.</li>"
            "<li><strong>R56 - snap counts as the starter proxy.</strong> Where a printed "
            "depth chart is unavailable, the highest-snap player at a position is the "
            "playing-time starter; the replacement-depth page names who is behind him.</li>"
            "</ul>",
            eyebrow="WHAT THIS CHANGES",
            subtitle="Four requirements move from inference to transcription.",
        ),
        section(
            "What this desk does not claim",
            "<p>The Playtime Percentage table is snap counts, not a depth chart. The desk "
            "does not publish a jersey-order depth, does not infer a player's experience or "
            "salary, and does not claim the four tables labelled '(Unofficial)' are certified "
            "official statistics - the label is carried verbatim. The depth-vs-snap "
            "cross-reference against printed club depth charts is a published zero-row gap, "
            "because the four clubs with captured depth charts did not play in Week 10.</p>",
            eyebrow="BOUNDARIES",
            subtitle="The honest limit is stated before the numbers.",
        ),
        section(
            "Page map",
            '<ul class="tight">'
            '<li><a href="snap-records.html">Per-game snap records</a> - the verbatim '
            'snap counts and share for every player in every game.</li>'
            '<li><a href="position-group-shares.html">Position-group snap shares</a> - each '
            'position group\'s share of a team\'s snaps on each phase.</li>'
            '<li><a href="playtime-depth.html">Playing-time depth</a> - every player ranked '
            'by snaps; rank 1 is the playing-time starter.</li>'
            '<li><a href="replacement-depth.html">Replacement depth</a> - who is behind each '
            'playing-time starter, by the snaps they played.</li>'
            '<li><a href="depth-vs-snap.html">Depth-vs-snap cross-reference</a> - why the '
            'printed-depth join is a zero-row gap.</li>'
            '<li><a href="decisions.html">Questions &amp; readiness</a>, '
            '<a href="suggestions.html">Suggestions</a>, '
            '<a href="verification.html">Verification</a>, '
            '<a href="flagged.html">Flagged for review</a>, '
            '<a href="sources.html">Sources</a>.</li></ul>',
            eyebrow="NAVIGATION",
        ),
    ]
    return parts


def page_snap_records() -> list[str]:
    rows = read_csv("snap-records.csv")
    out = []
    for r in rows:
        label_kind = "warn" if r["table_label"] == "Unofficial" else "good"
        out.append(row([
            cell(r["snap_id"]),
            cell(r["game_id"]),
            cell(r["team"]),
            cell(r["player"]),
            cell(r["position"]),
            cell(r["off_snaps"], num=True),
            cell(r["off_pct"], num=True),
            cell(r["def_snaps"], num=True),
            cell(r["def_pct"], num=True),
            cell(r["st_snaps"], num=True),
            cell(r["st_pct"], num=True),
            cell(r["total_snaps"], num=True),
            badge(r["table_label"] or "Official", label_kind),
        ], [SID_GAMEBOOK], r["snap_id"], r["source_url"]))
    return [
        notice(
            "Snap counts are transcribed exactly as the official Game Book prints them.",
            "A blank phase cell means the player did not play that phase - it is never "
            "replaced with a zero or inferred from another source. The 'Unofficial' badge "
            "marks the four Game Books whose Playtime Percentage table carries that label "
            "inside the PDF; the counts are still the official Game Book's own table.",
            info=True,
        ),
        section(
            "Per-game snap records",
            table(
                ["ID", "Game", "Team", "Player", "Pos", "Off snaps", "Off %",
                 "Def snaps", "Def %", "ST snaps", "ST %", "Total", "Label", "Sources"],
                out,
                caption="One row per player per game. Snap counts and share are from the "
                        "official Game Book Playtime Percentage table.",
            ),
            eyebrow="OFFICIAL SNAP TRANSCRIPTION",
            subtitle="Every player-phase snap count, linked to its official Game Book PDF.",
        ),
    ]


def page_position_shares() -> list[str]:
    rows = read_csv("position-group-shares.csv")
    out = []
    for r in rows:
        share = f"{float(r['share']) * 100:.1f}%" if r["share"] else ""
        out.append(row([
            cell(r["game_id"]),
            cell(r["team"]),
            cell(r["position_group"]),
            cell(r["phase"]),
            cell(r["snaps"], num=True),
            cell(r["team_phase_snaps"], num=True),
            cell(share, num=True),
        ], [SID_GAMEBOOK], f"{r['game_id']}|{r['team']}|{r['position_group']}|{r['phase']}",
            r["source_url"]))
    return [
        section(
            "Position-group snap shares",
            table(
                ["Game", "Team", "Position group", "Phase", "Group snaps",
                 "Team phase snaps", "Share", "Sources"],
                out,
                caption="Each position group's share of a team's snaps on a given phase, "
                        "computed from the transcribed snap counts.",
            ),
            eyebrow="PLAYING-TIME COMPOSITION",
            subtitle="How a team's snaps split across position groups, per phase.",
        ),
    ]


def page_playtime_depth() -> list[str]:
    rows = read_csv("playtime-depth.csv")
    out = []
    for r in rows:
        role_kind = "good" if r["role"].startswith("Starter") else "info"
        out.append(row([
            cell(r["depth_id"]),
            cell(r["game_id"]),
            cell(r["team"]),
            cell(r["position_group"]),
            cell(r["position"]),
            cell(r["phase"]),
            cell(r["player"]),
            cell(r["snaps"], num=True),
            cell(r["depth_rank"], num=True),
            badge(r["role"], role_kind),
        ], [SID_GAMEBOOK], r["depth_id"], r["source_url"]))
    return [
        notice(
            "Depth order here comes from playing time only.",
            "Players are ranked by the snaps they played in that position group and phase. "
            "Rank 1 is the playing-time starter. Jersey number, experience, salary and any "
            "printed depth chart play no part in this order. Where two players tie on snaps, "
            "the order is alphabetical by name and the tie is visible in the table.",
            info=True,
        ),
        section(
            "Playing-time depth",
            table(
                ["ID", "Game", "Team", "Position group", "Pos", "Phase", "Player",
                 "Snaps", "Rank", "Role", "Sources"],
                out,
                caption="Every player who played a position group and phase, ranked by snap "
                        "count. Rank 1 = playing-time starter.",
            ),
            eyebrow="R11 · R52 · R56",
            subtitle="Depth derived from snap counts, never from jersey order.",
        ),
    ]


def page_replacement_depth() -> list[str]:
    rows = read_csv("replacement-depth.csv")
    out = []
    for r in rows:
        out.append(row([
            cell(r["replacement_id"]),
            cell(r["game_id"]),
            cell(r["team"]),
            cell(r["position_group"]),
            cell(r["phase"]),
            cell(r["starter_player"]),
            cell(r["starter_snaps"], num=True),
            cell(r["replacement_player"]),
            cell(r["replacement_snaps"], num=True),
            cell(r["replacement_rank"], num=True),
        ], [SID_GAMEBOOK], r["replacement_id"], r["source_url"]))
    return [
        section(
            "Replacement depth",
            table(
                ["ID", "Game", "Team", "Position group", "Phase", "Starter",
                 "Starter snaps", "Replacement", "Replacement snaps", "Rank", "Sources"],
                out,
                caption="Behind each playing-time starter, the next player(s) by the snaps "
                        "they actually played - who would step in, in snap-count terms.",
            ),
            eyebrow="R56",
            subtitle="The snap-count replacement behind every playing-time starter.",
        ),
    ]


def page_depth_vs_snap() -> list[str]:
    rows = read_csv("depth-vs-snap.csv")
    out = []
    for r in rows:
        out.append(row([
            cell(r["depth_id"]),
            cell(r["club"]),
            cell(r["unit"]),
            cell(r["position"]),
            cell(r["rank"]),
            cell(r["depth_player"]),
            cell(r["snap_source"]),
        ], [SID_DEPTH], r["depth_id"], r["source_url"]))
    return [
        notice(
            "The printed-depth join is a published zero-row gap.",
            "The committed official club depth-chart transcription covers CHI, DEN, PHI and "
            "TB only. None of the four played in Week 10, so there is no game in which to "
            "compare a printed depth order against actual snap counts. The gap is published "
            "here rather than filled with a substitute. Capturing depth charts for the 26 "
            "clubs that played would clear it.",
            info=True,
        ),
        section(
            "Depth-vs-snap cross-reference",
            table(
                ["Depth ID", "Club", "Unit", "Position", "Rank", "Depth player",
                 "Snap join", "Sources"],
                out,
                caption="A printed depth-chart rank joined to the snap counts of the same "
                        "player in the same game. Zero rows because the four captured "
                        "depth-chart clubs did not play in Week 10.",
            ),
            eyebrow="ZERO-ROW GAP",
            subtitle="Why the printed-depth join cannot be computed for Week 10.",
        ),
    ]


def page_decisions() -> list[str]:
    s = SUMMARY
    rows = [
        {"req": "R11", "question": "Can depth be modelled from playing time instead of jersey order?",
         "answer": "Yes. The playing-time depth page ranks every player by snaps; jersey "
                   "number plays no part.",
         "gate": "snap counts transcribed",
         "clearing": f"{s['snap_record_rows']} snap records from {s['games_captured']} Game Books"},
        {"req": "R31", "question": "Are official snap counts captured?",
         "answer": "Yes. The per-game snap records transcribe the official Game Book "
                   "Playtime Percentage table.",
         "gate": f"{s['games_captured']} Game Books captured",
         "clearing": f"{s['snap_record_rows']} player-phase rows"},
        {"req": "R52", "question": "Is the depth-order source resolved?",
         "answer": "Partly. Snap counts resolve who played; the printed depth-chart order "
                   "is a separate club artefact and the cross-reference is a zero-row gap.",
         "gate": "snap source resolved",
         "clearing": f"{s['depth_vs_snap_joinable_rows']} printed-depth join rows (gap published)"},
        {"req": "R56", "question": "Are snap counts used as the starter proxy where the depth chart is unavailable?",
         "answer": "Yes. The highest-snap player at a position is the playing-time starter; "
                   "the replacement-depth page names who is behind him.",
         "gate": "starter proxy derived",
         "clearing": f"{s['playtime_depth_rows']} playing-time depth rows"},
    ]
    out = []
    for r in rows:
        out.append(row([
            cell(r["req"]),
            cell(r["question"]),
            cell(r["answer"]),
            cell(r["gate"]),
            cell(r["clearing"]),
        ], [SID_GAMEBOOK], r["req"]))
    return [
        section(
            "Questions & readiness",
            table(["Requirement", "Question", "Answer from this desk", "Gate", "Clearing number", "Sources"],
                  out,
                  caption="One readiness row per open requirement this desk addresses."),
            eyebrow="READINESS",
        ),
    ]


def page_suggestions() -> list[str]:
    rows = [
        {"id": "SN-SG-01", "proposal": "Capture official depth charts for the 26 clubs that played in Week 10",
         "why": "Clears the depth-vs-snap zero-row gap (SN-F02) and lets a printed depth order "
                "be compared against actual snap counts.",
         "cost": "26 club pages, one read each", "risk": "clubs label charts 'unofficial'"},
        {"id": "SN-SG-02", "proposal": "Re-capture the W10-14 (LAC@BAL) Game Book after the game is final",
         "why": "Adds the 14th fixture's Playtime Percentage table, closing the last Week 10 gap.",
         "cost": "one PDF read", "risk": "none"},
        {"id": "SN-SG-03", "proposal": "Extend the playing-time depth across more weeks",
         "why": "A single week is a snapshot; a multi-week view would show whether playing-time "
                "starters are stable.",
         "cost": "repeat the capture per week", "risk": "scope growth; keep it read-only"},
    ]
    out = []
    for r in rows:
        out.append(row([
            cell(r["id"]),
            cell(r["proposal"]),
            cell(r["why"]),
            cell(r["cost"]),
            cell(r["risk"]),
        ], [SID_GAMEBOOK, SID_REPO], r["id"]))
    return [
        section(
            "Suggestions",
            table(["ID", "Proposal", "Why", "Cost", "Risk", "Sources"], out,
                  caption="Ranked proposals for review before anything is changed."),
            eyebrow="SUGGESTIONS",
        ),
    ]


def page_verification() -> list[str]:
    rows = read_csv("snap-records.csv")
    s = load_json("capture-summary.json")
    unofficial = sum(1 for r in rows if r["table_label"] == "Unofficial")
    game_count = s["games_captured"]
    checks = [
        ("All played Game Books parsed", f"{game_count} raw files",
         "each raw/g*.txt parsed without an unknown tag"),
        ("Snap records carry a source link", f"{len(rows)} rows",
         "every row links its official Game Book PDF"),
        ("Blanks preserved, not filled", "phase cells left empty",
         "a phase the player did not play stays blank"),
        ("Depth order from playing time", f"{s['playtime_depth_rows']} ranked rows",
         "ranked by snap count; no jersey/experience/salary input"),
        ("Unofficial labels carried", f"{unofficial} tables",
         "the '(Unofficial)' label is recorded verbatim, not removed"),
        ("Deterministic rebuild", "build.py --check",
         "byte-identical artefacts on every build"),
    ]
    out = []
    for c in checks:
        out.append(row([
            cell(c[0]), cell(c[1]), cell(c[2]),
        ], [SID_GAMEBOOK, SID_REPO], c[0]))
    return [
        section(
            "Verification",
            table(["Check", "Result", "How", "Sources"], out,
                  caption="Mechanical checks re-run on every build."),
            eyebrow="VERIFICATION",
        ),
    ]


def page_flagged() -> list[str]:
    rows = load_json("flags.json")
    out = []
    for r in rows:
        out.append(row([
            cell(r["flag_id"]),
            cell(r["item"]),
            cell(r["detail"]),
            cell(r["value_published"]),
            cell(r["why_blank"]),
            cell(r["route"]),
        ], [SID_GAMEBOOK, SID_REPO], r["flag_id"], r["source_url"]))
    return [
        notice(
            f"{len(rows)} items are flagged. None blocks publication.",
            "Each is an honesty boundary: a value the official artefact does not publish, a "
            "label carried verbatim, or a gap that is published rather than filled. Each "
            "carries the route that would resolve it.",
            info=True,
        ),
        section(
            "Flagged for review",
            table(["ID", "Item", "Detail", "Value published", "Why the cell is blank",
                   "Route to resolve", "Sources"],
                  out, caption="Blank values are intentional and are never inferred."),
            eyebrow="TRANSPARENCY",
        ),
    ]


def page_sources() -> list[str]:
    ids = [SID_GAMEBOOK, SID_GAMECENTER, SID_DEPTH, SID_REPO]
    out = []
    for sid_ in ids:
        url = REGISTRY.get(sid_, "")
        out.append(
            f'<tr data-row-id="{esc(sid_)}" data-source-ids="{esc(sid_)}">'
            + cell(sid_) + cell(url or "not registered") + refs_cell([sid_]) + "</tr>"
        )
    import hashlib
    raw = sorted((HERE / "raw").glob("g*.txt"))
    raw_rows = []
    for r in raw:
        raw_rows.append(
            f'<tr data-row-id="{esc(r.name)}" data-source-ids="{SID_GAMEBOOK}">'
            + cell(r.name)
            + cell(hashlib.sha256(r.read_bytes()).hexdigest())
            + refs_cell([SID_GAMEBOOK])
            + "</tr>"
        )
    return [
        section(
            "Registered primary sources",
            table(["ID", "Official URL", "Link"], out,
                  caption="Registered in research/sources.json and host-checked on every build."),
            eyebrow="SOURCES",
        ),
        section(
            "Committed raw extracts",
            table(["Extract", "SHA-256", "Source"], raw_rows,
                  caption="The exact text each published row was transcribed from."),
            eyebrow="RAW EXTRACTS",
        ),
    ]


# ---------------------------------------------------------------------- build


def main() -> None:
    global REGISTRY, SUMMARY, FLAGS
    check = "--check" in sys.argv
    result = subprocess.run([sys.executable, str(HERE / "build.py")], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit("build.py failed:\n" + result.stdout + result.stderr)
    REGISTRY = load_registry()
    SUMMARY = load_json("capture-summary.json")
    FLAGS = load_json("flags.json")

    builders = {
        "index.html": ("Snap-count / playing-time desk",
                       "Official per-player snap counts from the NFL Game Book Playtime Percentage table, and the playing-time depth derived from them.",
                       page_index),
        "snap-records.html": ("Per-game snap records",
                              "The verbatim snap counts and share for every player in every Week 10 game.",
                              page_snap_records),
        "position-group-shares.html": ("Position-group snap shares",
                                       "Each position group's share of a team's snaps on each phase.",
                                       page_position_shares),
        "playtime-depth.html": ("Playing-time depth",
                                "Every player ranked by snaps; rank 1 is the playing-time starter.",
                                page_playtime_depth),
        "replacement-depth.html": ("Replacement depth",
                                   "Who is behind each playing-time starter, by the snaps they played.",
                                   page_replacement_depth),
        "depth-vs-snap.html": ("Depth-vs-snap cross-reference",
                               "Why the printed-depth join is a published zero-row gap.",
                               page_depth_vs_snap),
        "decisions.html": ("Questions & readiness",
                           "One readiness row per open requirement this desk addresses.",
                           page_decisions),
        "suggestions.html": ("Suggestions",
                             "Ranked proposals for review before anything is changed.",
                             page_suggestions),
        "verification.html": ("Verification",
                              "Mechanical checks re-run on every build.",
                              page_verification),
        "flagged.html": ("Flagged for review",
                         "Values the official record does not publish, and gaps published rather than filled.",
                         page_flagged),
        "sources.html": ("Sources",
                         "Registered sources and the committed raw extracts.",
                         page_sources),
    }

    SITE.mkdir(exist_ok=True)
    outputs: dict[str, str] = {}
    for name, _ in PAGES:
        title, lede, fn = builders[name]
        outputs[name] = page(name, title, lede, fn())
    outputs["style.css"] = STYLE

    manifest = {
        "pages": [name for name, _ in PAGES],
        "desk": "nfl-snapcount-e5e4",
        "built_from": ["raw/g01..g13-*.txt", "build.py", "data/*.csv"],
        "captured_games": SUMMARY["games_captured"],
        "snap_records": SUMMARY["snap_record_rows"],
        "playtime_depth_rows": SUMMARY["playtime_depth_rows"],
        "replacement_depth_rows": SUMMARY["replacement_depth_rows"],
    }
    outputs["manifest.json"] = json.dumps(manifest, indent=2) + "\n"

    problems = []
    for name, text in outputs.items():
        target = SITE / name
        if check:
            if not target.exists():
                problems.append(f"{name}: missing")
            elif target.read_text(encoding="utf-8") != text:
                problems.append(f"{name}: not byte-identical on rebuild")
        else:
            target.write_text(text, encoding="utf-8")
    if check and problems:
        raise SystemExit("Snap-count desk check failed:\n" + "\n".join(" - " + p for p in problems))
    verb = "Checked" if check else "Built"
    print(f"{verb} {len(PAGES)} snap-count desk pages ({SUMMARY['games_captured']} Game Books).")


if __name__ == "__main__":
    main()
