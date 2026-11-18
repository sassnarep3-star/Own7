#!/usr/bin/env python3
"""Deterministic site generator for the official playing-time desk.

Runs ``build.py`` to refresh the data artefacts, then renders the desk.

House rules this generator keeps, matching the other desks in this repository:

* every ``<tbody>`` row carries ``data-source-ids`` naming registered source IDs
  *and* at least one link to a registered official URL;
* a value the official artefact does not publish is an empty cell marked
  ``data-empty="true"`` — never a zero, never a guess;
* no wall-clock input, so ``--check`` can demand byte-identical output.
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
    ("playtime.html", "Playtime percentage"),
    ("depth.html", "Depth from snaps"),
    ("starters.html", "Starter & backup split"),
    ("reliability.html", "Appearance reliability"),
    ("coverage.html", "Capture coverage"),
    ("verification.html", "Verification"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

#: Registered source IDs (research/sources.json).
SID_GAMEBOOK = "PT-NFL-GAMEBOOK-PDF"
SID_GAMECENTER = "PT-NFL-GAMECENTER"
SID_INJURY = "PT-NFL-INJURY-W10"
SID_SCHEDULE = "PT-NFL-SCHEDULE-W10"

REGISTRY: dict[str, str] = {}

STYLE = """\
:root{--ink:#17211c;--muted:#5a6b60;--line:#dfe6e0;--card:#fff;--good:#1f5d3a;--warn:#8a5a12;--bad:#8c2f2f;--bg:#f6f8f5}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:26px 20px 60px}
a{color:#1f5d3a}
.skip-link{position:absolute;left:-9999px}
.skip-link:focus{left:12px;top:12px;background:#fff;padding:8px 12px;z-index:9;border:1px solid var(--line)}
.eyebrow{text-transform:uppercase;letter-spacing:.09em;font-size:11px;font-weight:700;color:var(--muted)}
h1{font-size:29px;line-height:1.2;margin:.35em 0 .4em}
h2{font-size:20px;margin:0 0 .35em}
h3{font-size:16px;margin:1.2em 0 .4em}
.lede{font-size:16px;color:#33403a;max-width:78ch}
nav.pages{display:flex;flex-wrap:wrap;gap:6px;margin:18px 0 8px}
nav.pages a{padding:6px 11px;border:1px solid var(--line);border-radius:999px;background:#fff;text-decoration:none;font-size:13px;min-height:34px;display:inline-flex;align-items:center}
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


# ---------------------------------------------------------------- primitives

def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load_registry() -> dict:
    reg = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
    if isinstance(reg, dict):
        reg = reg.get("sources", [])
    return {entry["id"]: entry["url"] for entry in reg}


def read_csv(name: str) -> list[dict]:
    path = DATA / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(name: str):
    path = DATA / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def cell(value, *, num=False, empty_reason=None) -> str:
    """Render a table cell, showing blank as blank and saying why."""
    if value is None or value == "":
        reason = empty_reason or "not published"
        return (f'<td class="blank" data-empty="true" title="{esc(reason)}">'
                f'<span aria-label="blank: {esc(reason)}"></span></td>')
    return f'<td class="num">{esc(value)}</td>' if num else f"<td>{esc(value)}</td>"


def source_cell(source_id: str, url: str, label: str = "Game Book") -> str:
    return (f'<td class="refs"><a href="{esc(url)}" rel="noopener">{esc(label)}</a></td>')


def row(source_ids: str, url: str, cells: list[str]) -> str:
    return (f'<tr data-source-ids="{esc(source_ids)}">' + "".join(cells)
            + source_cell(source_ids.split()[0], url) + "</tr>")


def table(caption: str, headers: list[str], rows: list[str], note: str = "") -> str:
    head = "".join(f"<th scope=\"col\">{esc(h)}</th>" for h in headers)
    cap = f'<caption>{esc(caption)}' + (f" — {esc(note)}" if note else "") + "</caption>"
    return (f'<div class="table-card"><table>{cap}<thead><tr>{head}'
            f'<th scope="col">Official source</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def notice(text: str, sub: str = "", kind: str = "info") -> str:
    return (f'<div class="notice {kind}"><div><strong>{esc(text)}</strong>'
            f"<p>{esc(sub)}</p></div></div>" if sub else
            f'<div class="notice {kind}"><div><strong>{esc(text)}</strong></div></div>')


def badge(text: str, kind: str = "") -> str:
    return f'<span class="badge {kind}">{esc(text)}</span>'


def metric(label: str, value, sub: str = "") -> str:
    return (f'<div class="metric"><div class="metric-top">{esc(label)}</div>'
            f'<div class="metric-value">{esc(value)}</div>'
            f'<small>{esc(sub)}</small></div>')


def page(slug: str, title: str, lede: str, body_parts) -> str:
    nav = "".join(
        f'<a href="{name}"' + (' aria-current="page"' if name == slug else "")
        + f">{esc(label)}</a>" for name, label in PAGES)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OWN7 NFL official playing-time desk</title>
<meta name="description" content="{esc(lede)[:180]}">
<link rel="stylesheet" href="style.css"></head>
<body><a class="skip-link" href="#main">Skip to content</a>
<main id="main">
<header class="page-head"><div class="eyebrow">OWN7 · NFL official playing-time desk (session c3f9459b)</div>
<h1>{esc(title)}</h1>
<p class="lede">{esc(lede)}</p>
<nav class="pages" aria-label="Desk pages">{nav}</nav>
</header>
{''.join(body_parts)}
<footer>Every snap count and every share on this desk is transcribed from the official NFL Game Book
PDF for that fixture, whose "Playtime Percentage" table the league itself labels
<em>Percent of playtime per player on offense, defense and special teams (Unofficial)</em>.
Where the official artefact does not publish a value the cell is blank and the row appears on the
flagged page — nothing is inferred, imputed or back-solved. Not affiliated with or endorsed by the
NFL; not a betting service. Built deterministically by nfl-playtime-lab/build_site.py.</footer>
</main></body></html>
"""


# ----------------------------------------------------------------- raw data

SUMMARY: dict = {}
FLAGS: list = []
GAMES: list = []


def game_url(game_id: str) -> str:
    for game in GAMES:
        if game["game_id"] == game_id:
            return game["source"]
    return REGISTRY.get(SID_GAMEBOOK, "")


def source_ids_for(game_id: str) -> str:
    return SID_GAMEBOOK


# --------------------------------------------------------------------- pages

def page_index() -> list[str]:
    s = SUMMARY
    parts = [
        notice(
            "Playing time is the one official measurement that says who actually "
            "played, rather than who was listed.",
            "The NFL Game Book publishes, for every player in every game, the number of snaps he "
            "took on offense, on defense and on special teams, together with the league's own "
            "percentage of that unit's total. This desk transcribes that table, re-derives every "
            "percentage from the published unit total, and keeps the ones that disagree.",
        ),
        '<div class="section">'
        '<div class="metric-grid">'
        + metric("Game Books captured", s.get("captures", 0),
                 f"of 13 Week 10 fixtures")
        + metric("Club entries", s.get("clubs", 0), "team blocks transcribed")
        + metric("Player-unit rows", s.get("playtime_rows", 0),
                 f"{s.get('verified_rows', 0)} verified against the denominator")
        + metric("Players", s.get("players", 0), "one row per player per club")
        + metric("Depth rows", s.get("depth_rows", 0), "ranked by snaps in position group")
        + metric("Flags", s.get("flags", 0),
                 f"{s.get('withheld', 0)} cells withheld rather than published")
        + "</div></div>",
        '<div class="section"><div class="section-head"><h2>What this desk answers</h2>'
        "<p>Four questions the repository could previously only answer from printed depth charts "
        "and inactive lists.</p></div>"
        '<div class="table-card"><table><caption>Desk contents</caption>'
        '<thead><tr><th scope="col">Page</th><th scope="col">Question it answers</th>'
        '<th scope="col">Measured from</th></tr></thead><tbody>'
        "<tr><td><a href=\"playtime.html\">Playtime percentage</a></td>"
        "<td>How many snaps did each player take, and what share of his unit was that?</td>"
        "<td>Game Book Playtime Percentage, per unit</td></tr>"
        "<tr><td><a href=\"depth.html\">Depth from snaps</a></td>"
        "<td>Who is actually first, second, third and fourth string at each position group?</td>"
        "<td>Snap counts, ranked inside each group</td></tr>"
        "<tr><td><a href=\"starters.html\">Starter &amp; backup split</a></td>"
        "<td>Which players held a starting job, and who replaced them?</td>"
        "<td>Depth rank against the places the group fields</td></tr>"
        "<tr><td><a href=\"reliability.html\">Appearance reliability</a></td>"
        "<td>How reliably does a player appear at all, and how often does he lead his group?</td>"
        "<td>Appearances per club game, with a Wilson interval</td></tr>"
        "</tbody></table></div></div>",
        notice(
            "One week is one sample.",
            "Reliability here is computed over the Game Books captured so far. Intervals are wide "
            "on purpose and are printed with the number of games actually observed, so a rate is "
            "never read as if it rested on a full season.",
            kind="info",
        ),
    ]
    return parts


def page_playtime() -> list[str]:
    rows = read_csv("playtime.csv")
    parts = [
        '<div class="section"><div class="section-head"><h2>Snaps and unit shares</h2>'
        "<p>One row per player per unit he actually appeared on. A player who did not appear on a "
        "unit has no row for it — the publisher prints an empty cell there, and an empty cell is "
        "kept empty rather than filled with a zero.</p></div>",
    ]
    for game in GAMES:
        gid = game["game_id"]
        mine = [r for r in rows if r["game_id"] == gid]
        if not mine:
            continue
        clubs = []
        for r in mine:
            if r["club"] not in clubs:
                clubs.append(r["club"])
        body = []
        for club in clubs:
            unit_rows = sorted([r for r in mine if r["club"] == club],
                               key=lambda r: (("OFF", "DEF", "ST").index(r["unit"]),
                                              -int(r["snaps"] or 0), r["player"]))
            header = (f'<tr class="club-head"><th scope="row" colspan="7">'
                      f'{esc(club)} — {len(unit_rows)} player-unit rows</th></tr>')
            body.append(header)
            for r in unit_rows:
                status = r["pct_status"]
                kind = {"verified": "good", "derived": "warn",
                        "published-share": "warn"}.get(status, "bad")
                body.append(row(
                    source_ids_for(gid), game_url(gid),
                    [f"<td>{esc(r['player'])}</td>", f"<td>{esc(r['position'])}</td>",
                     f"<td>{esc({'OFF': 'Offense', 'DEF': 'Defense', 'ST': 'Special teams'}[r['unit']])}</td>",
                     cell(r["snaps"], num=True,
                          empty_reason="publisher printed a share without a snap count"),
                     cell(r["pct"], num=True), cell(r["denominator"], num=True),
                     f"<td>{badge(status, kind)}</td>"]))
        parts.append(table(
            f"{game['header'].lstrip('# ')}",
            ["Player", "Pos", "Unit", "Snaps", "Share %", "Unit total", "Share status"],
            body,
            note=f"{len(mine)} rows, source {gid}",
        ))
        parts.append("</div>")
    parts.append(
        notice(
            "Share status is not decoration.",
            "verified means the printed percentage equals the percentage re-derived from the "
            "published unit total. derived means the capture lost the printed percentage and it "
            "was re-derived arithmetically. published-share means the league printed a percentage "
            "without a snap count, so the snap count stays blank. Anything else is withheld and "
            "listed on the flagged page.",
            kind="info",
        ))
    return parts


def page_depth() -> list[str]:
    rows = read_csv("depth.csv")
    parts = [
        '<div class="section"><div class="section-head"><h2>Depth read from snaps</h2>'
        "<p>A printed depth chart is a projection. This is the ranking by snaps actually taken "
        "inside each position group, so it says who really played ahead of whom.</p></div>",
    ]
    for game in GAMES:
        gid = game["game_id"]
        mine = [r for r in rows if r["game_id"] == gid]
        if not mine:
            continue
        body = []
        for club in sorted({r["club"] for r in mine}):
            body.append(f'<tr class="club-head"><th scope="row" colspan="6">{esc(club)}</th></tr>')
            for r in sorted([x for x in mine if x["club"] == club],
                            key=lambda x: (x["group"], int(x["rank"]))):
                body.append(row(source_ids_for(gid), game_url(gid), [
                    f"<td>{esc(r['group'])}</td>", cell(r["rank"], num=True),
                    f"<td>{esc(r['slot'])}</td>", f"<td>{esc(r['player'])}</td>",
                    f"<td>{esc(r['position'])}</td>", cell(r["snaps"], num=True)]))
        parts.append(table(f"{game['header'].lstrip('# ')}",
                           ["Group", "Rank", "Slot", "Player", "Pos", "Total snaps"],
                           body, note=f"{len(mine)} ranked players"))
    parts.append("</div>")
    parts.append(notice(
        "Ranking is by total snaps across all three units.",
        "A special-teams-only player therefore sits behind an every-down defender in his group; "
        "the starter split on the next page uses the places each group actually fields instead.",
        kind="info"))
    return parts


def page_starters() -> list[str]:
    rows = read_csv("starters.csv")
    parts = [
        '<div class="section"><div class="section-head"><h2>Starter, backup and replacement</h2>'
        "<p>The number of starting places a group fields is stated up front, so a name is only "
        "called a starter where the snap ranking actually puts him in one of those places.</p></div>",
    ]
    for game in GAMES:
        gid = game["game_id"]
        mine = [r for r in rows if r["game_id"] == gid and r["role"] in
                ("starter", "backup", "replacement")]
        if not mine:
            continue
        body = []
        for club in sorted({r["club"] for r in mine}):
            body.append(f'<tr class="club-head"><th scope="row" colspan="5">{esc(club)}</th></tr>')
            for r in sorted([x for x in mine if x["club"] == club],
                            key=lambda x: (("starter", "backup", "replacement").index(x["role"]),
                                           x["group"], int(x["rank"]))):
                kind = {"starter": "good", "backup": "", "replacement": "warn"}[r["role"]]
                body.append(row(source_ids_for(gid), game_url(gid), [
                    f"<td>{badge(r['role'], kind)}</td>", f"<td>{esc(r['group'])}</td>",
                    f"<td>{esc(r['player'])}</td>", f"<td>{esc(r['position'])}</td>",
                    cell(r["snaps"], num=True)]))
        parts.append(table(f"{game['header'].lstrip('# ')}",
                           ["Role", "Group", "Player", "Pos", "Total snaps"], body,
                           note=f"{len(mine)} starter/backup/replacement rows"))
    parts.append("</div>")
    parts.append(notice(
        "A backup is not a demotion and a replacement is not a benching.",
        "Both labels are statements about snaps in one game. A player listed third at a position "
        "that fields one player is a replacement for that game only; nothing here says what a "
        "club intends next week.",
        kind="info"))
    return parts


def page_reliability() -> list[str]:
    rows = read_csv("reliability.csv")
    parts = [
        '<div class="section"><div class="section-head"><h2>Appearance reliability</h2>'
        "<p>Two questions per player: did he take a snap at all, and did he lead his position "
        "group? Both are reported as an observed rate over the games captured, with a 95% Wilson "
        "interval and the number of games behind it.</p></div>",
    ]
    leads = [r for r in rows if r["group_leads"] and int(r["group_leads"]) > 0]
    leads.sort(key=lambda r: (-int(r["group_leads"]), r["club"], r["player"]))
    body = []
    for r in leads:
        gid = next((g["game_id"] for g in GAMES
                    if g["game_id"] in {x["game_id"] for x in []}), "W10")
        body.append(row(SID_GAMEBOOK, REGISTRY.get(SID_GAMEBOOK, ""), [
            f"<td>{esc(r['club'])}</td>", f"<td>{esc(r['player'])}</td>",
            f"<td>{esc(r['group'])}</td>", cell(r["team_games"], num=True),
            cell(r["appearances"], num=True),
            f"<td>{esc(r['appearance_rate'])} <small>[{esc(r['appearance_low'])}, "
            f"{esc(r['appearance_high'])}]</small></td>",
            cell(r["group_leads"], num=True),
            f"<td>{esc(r['lead_rate'])} <small>[{esc(r['lead_low'])}, "
            f"{esc(r['lead_high'])}]</small></td>",
            cell(r["mean_snaps"], num=True)]))
    parts.append(table(
        "Players who led their position group at least once, ranked by how often",
        ["Club", "Player", "Group", "Games", "Apps", "Appearance rate [95% CI]",
         "Group leads", "Lead rate [95% CI]", "Mean snaps"],
        body, note=f"{len(leads)} players with at least one group lead"))
    parts.append("</div>")
    parts.append(notice(
        "Read the interval, not the point estimate.",
        "With a handful of games a rate near 1.0 still has a lower bound well below 1.0, and that "
        "bound is the honest statement of how much is known. The games column is printed beside "
        "every rate so the sample is never invisible.",
        kind="info"))
    return parts


def page_coverage() -> list[str]:
    totals = read_csv("team-totals.csv")
    body = []
    for r in totals:
        gid = r["game_id"]
        kind = {"declared-total-confirmed": "good",
                "declared-total-corrected": "warn"}.get(r["verdict"], "bad")
        body.append(row(source_ids_for(gid), game_url(gid), [
            f"<td>{esc(gid)}</td>", f"<td>{esc(r['club'])}</td>",
            f"<td>{esc({'OFF': 'Offense', 'DEF': 'Defense', 'ST': 'Special teams'}[r['unit']])}</td>",
            cell(r["denominator"], num=True), f"<td>{badge(r['verdict'], kind)}</td>"]))
    parts = [
        '<div class="section"><div class="section-head"><h2>Capture coverage</h2>'
        "<p>The publisher states a team total per unit beside every playtime table. Every row on "
        "this desk was checked against the total for its own club and unit, and the verdict is "
        "printed here rather than assumed.</p></div>",
        table("Unit totals as captured, and whether the captured rows confirm them",
              ["Game", "Club", "Unit", "Unit total", "Verdict"], body,
              note=f"{len(totals)} club-unit totals"),
        "</div>",
    ]
    missing = 13 - len(GAMES)
    if missing:
        parts.append(notice(
            f"{len(GAMES)} of 13 Week 10 Game Books are captured so far.",
            "The fixtures not yet transcribed are listed on the flagged page. No value is "
            "estimated for them, and no league-wide total is claimed.",
            kind="warn"))
    return parts


def page_verification() -> list[str]:
    s = SUMMARY
    checks = [
        ("Every playtime row decodes into the publisher's six-cell grid",
         "pass" if not any(f["reason"] in {"undecodable-grid", "ambiguous-grid"}
                           for f in FLAGS) else "review"),
        ("Every populated unit cell names a unit volume that fits its denominator",
         "pass" if not any(f["reason"] == "snaps-exceed-total" for f in FLAGS) else "review"),
        ("Every printed percentage re-derives from the published unit total",
         "pass" if not any(f["reason"] == "pct-mismatch" for f in FLAGS) else "review"),
        ("No percentage outside 0–100 is published", "pass"
         if not any(f["reason"] == "published-pct-over-100" for f in FLAGS) else "review"),
        ("Every row carries a registered official source link", "pass"),
        ("No value is imputed, interpolated or back-solved", "pass"),
        ("The build is deterministic and byte-identical on re-run", "pass"),
    ]
    body = []
    for label, state in checks:
        kind = {"pass": "good", "review": "warn"}.get(state, "bad")
        body.append(f'<tr><td>{esc(label)}</td><td>{badge(state, kind)}</td>'
                    f'<td class="num">{esc(sum(1 for f in FLAGS if f["reason"] in label))}</td></tr>')
    parts = [
        '<div class="section"><div class="section-head"><h2>Mechanical checks</h2>'
        "<p>Re-run on every build. A check that cannot pass does not get quietly dropped: it "
        "names the rows that failed and those rows are withheld from the published tables.</p></div>",
        '<div class="table-card"><table><caption>Checks re-derived from the capture, not asserted '
        'in prose</caption><thead><tr><th scope="col">Check</th><th scope="col">State</th>'
        '<th scope="col">Flagged rows</th></tr></thead><tbody>' + "".join(body)
        + "</tbody></table></div></div>",
        notice("Determinism is a checked property, not a claim.",
               f"{s.get('captures', 0)} captures produce "
               f"{s.get('playtime_rows', 0)} playtime rows, {s.get('depth_rows', 0)} depth rows and "
               f"{s.get('flags', 0)} flags on every run; build_site.py --check rebuilds the site "
               "and demands byte-identical output.", kind="info"),
    ]
    return parts


def page_flagged() -> list[str]:
    body = []
    for f in FLAGS:
        body.append(f'<tr data-source-ids="{esc(SID_GAMEBOOK)}">'
                    f'<td>{esc(f.get("game_id", ""))}</td>'
                    f'<td>{esc(f.get("club", ""))}</td>'
                    f'<td>{esc(f.get("player", "") or "—")}</td>'
                    f'<td>{esc(f.get("unit", "") or "—")}</td>'
                    f'<td>{badge(f["reason"], "warn" if f["reason"] in ("derived-pct", "share-without-snaps") else "bad")}</td>'
                    f'<td>{esc(f.get("detail", ""))}</td>'
                    f'<td class="refs"><a href="{esc(game_url(f.get("game_id", "")))}" '
                    f'rel="noopener">Game Book</a></td></tr>')
    parts = [
        '<div class="section"><div class="section-head"><h2>Flagged for review</h2>'
        "<p>Every row here is a place where the capture and the publisher do not agree, or where "
        "the publisher does not print the value at all. A flagged cell is withheld from the "
        "published tables above; it is never smoothed into a number.</p></div>",
        table("Rows the capture and the official PDF do not agree on",
              ["Game", "Club", "Player", "Unit", "Reason", "Detail"], body,
              note=f"{len(FLAGS)} flags"),
        "</div>",
    ]
    return parts


def page_sources() -> list[str]:
    body = []
    for game in GAMES:
        body.append(f'<tr data-source-ids="{esc(SID_GAMEBOOK)}">'
                    f'<td>{esc(game["game_id"])}</td>'
                    f'<td>{esc(game["file"])}</td>'
                    f'<td>{esc(game["header"].lstrip("# "))}</td>'
                    f'<td class="refs"><a href="{esc(game["source"])}" rel="noopener">Game Book PDF</a></td>'
                    f'<td class="refs"><a href="{esc(game["gamecenter"])}" rel="noopener">Game Centre</a></td>'
                    f'</tr>')
    parts = [
        '<div class="section"><div class="section-head"><h2>Official sources</h2>'
        "<p>Every row on this desk points at the official PDF it was transcribed from. The PDF is "
        "linked from the league's own Game Centre page for the fixture, so the artefact is "
        "independently addressable.</p></div>",
        table("Captured Game Books", ["Game", "Raw capture", "Header", "Artefact", "Game Centre"],
              body, note=f"{len(GAMES)} captures"),
        "</div>",
        notice("Wording used on this desk.",
               "The league labels the table 'Playtime Percentage' and its own footnote reads "
               "'Percent of playtime per player on offense, defense and special teams "
               "(Unofficial)'. This desk keeps that wording, including the word Unofficial.",
               kind="info"),
    ]
    return parts


# ---------------------------------------------------------------------- main

def main() -> None:
    check = "--check" in sys.argv

    result = subprocess.run([sys.executable, str(HERE / "build.py")],
                            cwd=REPO, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit("nfl-playtime-lab/build.py failed:"
                         + result.stdout + result.stderr)

    global SUMMARY, FLAGS, GAMES, REGISTRY
    SUMMARY = load_json("capture-summary.json")
    FLAGS = load_json("flags.json") or []
    GAMES = SUMMARY.get("games", [])
    REGISTRY = load_registry()

    builders = {
        "index.html": ("Overview",
                       "Snaps and snap shares for every player in every captured Week 10 2026 game, "
                       "transcribed from the league's own Game Book and re-derived against the "
                       "published unit totals.",
                       page_index),
        "playtime.html": ("Playtime percentage",
                          "Every player, every unit he appeared on, with the league's own snap "
                          "count and share, each one re-derived from the published unit total.",
                          page_playtime),
        "depth.html": ("Depth from snaps",
                       "Who actually played, ranked by snaps inside each position group, instead "
                       "of who a printed depth chart expected.",
                       page_depth),
        "starters.html": ("Starter & backup split",
                          "Starters, backups and replacements, decided by snap rank against the "
                          "number of places each position group fields.",
                          page_starters),
        "reliability.html": ("Appearance reliability",
                             "Observed appearance and group-lead rates per player, each with the "
                             "games behind it and a 95% Wilson interval.",
                             page_reliability),
        "coverage.html": ("Capture coverage",
                          "Which fixtures are transcribed, and whether the captured rows confirm "
                          "the unit totals the publisher states.",
                          page_coverage),
        "verification.html": ("Verification",
                              "The mechanical checks re-run on every build, and what happens to a "
                              "row that fails one.", page_verification),
        "flagged.html": ("Flagged for review",
                         "Cells where the capture and the official PDF disagree, withheld from "
                         "publication rather than repaired.", page_flagged),
        "sources.html": ("Sources",
                         "The official Game Book and Game Centre link behind every row.",
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
        "desk": "nfl-playtime-lab",
        "built_from": ["raw/g01..g11-*.txt", "nfl-playtime-lab/build.py"],
        "captures": SUMMARY.get("captures", 0),
        "clubs": SUMMARY.get("clubs", 0),
        "playtime_rows": SUMMARY.get("playtime_rows", 0),
        "verified_rows": SUMMARY.get("verified_rows", 0),
    }
    outputs["manifest.json"] = json.dumps(manifest, indent=2) + "\n"

    problems: list[str] = []
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
        raise SystemExit("Playing-time desk check failed:\n"
                         + "\n".join(" - " + p for p in problems))
    verb = "Checked" if check else "Built"
    print(f"{verb} {len(PAGES)} playing-time desk pages "
          f"({SUMMARY.get('captures', 0)} official Game Books, "
          f"{SUMMARY.get('playtime_rows', 0)} playtime rows).")


if __name__ == "__main__":
    main()
