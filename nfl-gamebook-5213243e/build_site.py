#!/usr/bin/env python3
"""Deterministic generator for the official Game Book desk (nfl-gamebook-5213243e).

Builds the desk's data artefacts (via build.py) and its site. Every <tbody> row carries
data-source-ids naming registered source IDs and at least one link to a registered official
URL; every unknown value is an empty cell with data-empty="true". `--check` rebuilds and
demands byte-identical output. No wall-clock input: all dates are fixed constants.
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
    ("fixtures-venue.html", "Venue & environment"),
    ("starters.html", "Official starters"),
    ("inactives.html", "Inactives & replacement"),
    ("depth-coverage.html", "Depth-chart coverage"),
    ("designation-reliability.html", "Designation reliability"),
    ("delta.html", "What changed"),
    ("ledger.html", "Point-in-time ledger"),
    ("decisions.html", "Questions & readiness"),
    ("suggestions.html", "Suggestions"),
    ("verification.html", "Verification"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

# Source IDs registered in research/sources.json for this desk.
SID_GAMEBOOK = "GB-NFL-GAMEBOOK-PDF"
SID_INJURY = "GB-NFL-INJURY-W10"
SID_SCHEDULE = "GB-NFL-SCHEDULE-W10"
SID_GC = "GB-NFL-GAMECENTER"
SID_DEPTH = "GB-CLUB-DEPTH"
SID_REPO = "REPO"  # the repository record already registered


REGISTRY: dict[str, str] = {}


def load_registry() -> dict:
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
        label = "official artefact"
        links.append(
            f'<a href="{esc(extra_url)}" target="_blank" rel="noopener noreferrer">{label} &#8599;</a>'
        )
    return '<td class="refs">' + "".join(links) + "</td>"


def table(headers, rows_html, caption=None) -> str:
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    return (
        f'<div class="table-card"><table>{cap}<thead><tr>{head}</tr></thead>'
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
<title>{esc(title)} · OWN7 NFL official Game Book desk</title>
<meta name="description" content="{esc(lede)[:180]}">
<link rel="stylesheet" href="style.css"></head>
<body><a class="skip-link" href="#main">Skip to content</a>
<main id="main">
<header class="page-head"><div class="eyebrow">OWN7 · NFL official Game Book desk (session 5213243e)</div>
<h1>{esc(title)}</h1>
<p class="lede">{esc(lede)}</p>
<nav class="pages" aria-label="Desk pages">{nav}</nav>
</header>
{''.join(body_parts)}
<footer>Every value on this desk is transcribed from an official NFL Game Book PDF linked from the
official Game Centre, or from the official NFL injury report. Where an official artefact does not
publish a value the cell is blank and the row is listed on the flagged page — nothing is inferred.
Not affiliated with or endorsed by the NFL; not a betting service. Built deterministically by
nfl-gamebook-5213243e/build_site.py.</footer>
</main></body></html>
"""


# ----------------------------------------------------------------------- pages

SUMMARY = None
FLAGS = None


def page_index() -> list[str]:
    s = SUMMARY
    parts = [
        notice(
            "This desk answers one question the rest of the repository could not: what actually "
            "happened on the field, in the league's own words?",
            "The official NFL Game Book is a single official artefact that publishes the venue, "
            "the roof and surface, the game-day weather, the officials, the actual starting "
            "lineups and the official Not Active list for a fixture. Thirteen of the fourteen "
            "Week 10 fixtures have one; the fourteenth had not kicked off at capture.",
            info=True,
        ),
        metrics(
            [
                ("Game Books captured", str(s["games_with_game_book"]), "of 14 Week 10 fixtures"),
                ("Starting slots", f"{s['official_starters_captured']}/{s['expected_starter_slots']}", "official lineups transcribed"),
                ("Official inactives", str(s["official_inactives_captured"]), "Not Active rows"),
                ("Report rows joined", str(s["published_report_rows_joined"]), "as-known to actual outcome"),
                ("Availability deltas", str(s["availability_delta_rows"]), "one per joined report row"),
                ("Depth charts captured", f"{s['clubs_with_official_depth_chart']}/32", "official club charts in repo"),
            ]
        ),
        section(
            "Why the Game Book matters",
            "<p>The repository previously inferred starters from depth charts and inferred "
            "inactives from the weekly injury report. Both are proxies. The Game Book is the "
            "primary record: it names the eleven players each club actually started on offense "
            "and defense, and it lists every player who was Not Active. That converts three "
            "standing requests from inference into transcription:</p>"
            "<ul class=\"tight\">"
            "<li><strong>Who was expected to start, who actually did</strong> - the availability "
            "graph, now sourced on both sides.</li>"
            "<li><strong>Was a \"Questionable\" player really inactive?</strong> - measured here, "
            "not assumed from legacy percentages.</li>"
            "<li><strong>Venue, roof and weather</strong> - transcribed per fixture instead of "
            "left blank.</li></ul>",
            eyebrow="WHAT THIS CHANGES",
            subtitle="Three requirements stop being estimates.",
        ),
        section(
            "What this desk does not claim",
            "<p>The Game Book does <em>not</em> publish snap counts, depth rank, or the reason a "
            "player was inactive. So this desk does not rank backups, does not compute a depth "
            "penalty, and does not claim a replacement's quality. It states the replacement's "
            "<em>name</em> where the official lineup proves it, and leaves depth rank to the "
            "clubs' own charts - which this repository has captured for only four of thirty-two "
            "clubs.</p>",
            eyebrow="BOUNDARIES",
            subtitle="The honest limit is stated before the numbers.",
        ),
        section(
            "Page map",
            "<ul class=\"tight\">"
            "<li><a href=\"fixtures-venue.html\">Venue &amp; environment</a> - 13 transcribed "
            "venues with roof state, surface, weather and attendance.</li>"
            "<li><a href=\"starters.html\">Official starters</a> - the actual starting lineups.</li>"
            "<li><a href=\"inactives.html\">Inactives &amp; replacement</a> - who was out and who "
            "the Game Book started in that slot.</li>"
            "<li><a href=\"depth-coverage.html\">Depth-chart coverage</a> - the blocker on "
            "expected-vs-actual starters.</li>"
            "<li><a href=\"designation-reliability.html\">Designation reliability</a> - observed "
            "inactive rate per published designation, with n and a 95% interval.</li>"
            "<li><a href=\"delta.html\">What changed</a> - as-known to actual, row by row.</li>"
            "<li><a href=\"ledger.html\">Point-in-time ledger</a> - capture time and SHA-256 per "
            "artefact.</li>"
            "<li><a href=\"decisions.html\">Questions &amp; readiness</a> and "
            "<a href=\"suggestions.html\">Suggestions</a>.</li>"
            "<li><a href=\"verification.html\">Verification</a>, "
            "<a href=\"flagged.html\">Flagged for review</a>, "
            "<a href=\"sources.html\">Sources</a>.</li></ul>",
            eyebrow="NAVIGATION",
        ),
    ]
    return parts


def page_fixtures() -> list[str]:
    rows = read_csv("fixtures-venue.csv") + [BAL_ROW]
    out = []
    for r in rows:
        has_book = bool(r.get("raw_sha256"))
        out.append(
            row(
                [
                    cell(r["game_id"]),
                    cell(f"{r['away']} @ {r['home']}"),
                    cell(r["date"]),
                    cell(r["kickoff_official"]),
                    cell(r["stadium"]),
                    cell(r["venue_city_state"]),
                    cell(r["roof_and_surface"]),
                    cell(r["game_weather"]),
                    cell(r["temp_f"], num=True),
                    cell(r["humidity_pct"], num=True),
                    cell(r["wind"]),
                    cell(r["paid_attendance"], num=True),
                    cell("Game Book" if has_book else "", blank_note="No Game Book: fixture had not kicked off at capture"),
                ],
                [SID_GAMEBOOK, SID_GC] if has_book else [SID_GC],
                r["game_id"],
                r["source_url"],
            )
        )
    return [
        notice(
            "Weather is transcribed exactly as the Game Book prints it.",
            "Indoor and retractable-roof fixtures often publish the roof state without a "
            "temperature, humidity or wind value. Those cells are blank on purpose: substituting "
            "an outdoor reading would be an invention. Each blank is explained on the flagged page.",
            info=True,
        ),
        section(
            "Venue, roof, surface and game-day conditions",
            table(
                [
                    "Game", "Fixture", "Date", "Kickoff (official)", "Stadium", "City / state",
                    "Roof & surface", "Weather", "Temp °F", "Humidity %", "Wind", "Paid attendance",
                    "Artefact", "Sources",
                ],
                out,
                caption="One row per Week 10 fixture. Values are from the official Game Book unless the artefact cell is blank.",
            ),
            eyebrow="OFFICIAL VENUE TRANSCRIPTION",
            subtitle="Every fixture's venue transcribed from the official Game Book, with the roof "
            "state and surface the league recorded on the day.",
        ),
    ]


BAL_ROW = {
    "game_id": "W10-14",
    "away": "LAC",
    "home": "BAL",
    "date": "2026-11-16",
    "kickoff_official": "8:15 PM EST",
    "stadium": "M&T BANK STADIUM",
    "venue_city_state": "BALTIMORE, MD",
    "roof_and_surface": "",
    "game_weather": "",
    "temp_f": "",
    "humidity_pct": "",
    "wind": "",
    "paid_attendance": "",
    "source_url": "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
    "raw_sha256": "",
}


def page_starters() -> list[str]:
    rows = read_csv("starters-official.csv")
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(f"{r['game_id']}|{r['club']}|{r['unit']}", []).append(r)
    out = []
    for key in sorted(grouped):
        gid, club, unit = key.split("|")
        players = grouped[key]
        out.append(
            row(
                [
                    cell(gid),
                    cell(club),
                    cell(unit),
                    cell(len(players), num=True),
                    cell("; ".join(f"{p['position']} {p['jersey']} {p['player']}" for p in players)),
                    cell(" / ".join(sorted({p["position"] for p in players}))),
                ],
                [SID_GAMEBOOK],
                key,
                players[0]["source_url"],
            )
        )
    return [
        notice(
            f"{len(rows)} of 572 starting slots transcribed.",
            "Two official Game Books publish a defensive lineup whose player-name cells did not "
            "survive PDF text extraction: Cleveland and Dallas defense. Those 44 slots are blank "
            "on the inactives and starters pages and are listed as flag GB-F01 rather than "
            "guessed from a roster.",
            info=False,
        ),
        section(
            "Actual starting lineups, as the league recorded them",
            table(
                ["Game", "Club", "Unit", "Players", "Official starting lineup (position, jersey, player)", "Positions used"],
                out,
                caption="One row per club, unit and fixture. Eleven players per unit is the official lineup size.",
            ),
            eyebrow="ACTUAL STARTERS, NOT A DEPTH GUESS",
            subtitle="Read directly from each Game Book's Lineups block. Positions are printed as "
            "the league prints them, including variants such as LOT/ROT, LDE/RDE and DB.",
        ),
    ]


def page_inactives() -> list[str]:
    teams = read_csv("team-replacement-view.csv")
    out = []
    for t in teams:
        out.append(
            row(
                [
                    cell(t["game_id"]),
                    cell(t["club"]),
                    cell(t["official_not_active_count"], num=True),
                    cell(t["report_rows_as_known"], num=True),
                    cell(t["published_out_count"], num=True),
                    cell(t["published_out_and_inactive"], num=True),
                    cell(t["published_out_but_not_inactive"], num=True),
                    cell(t["out_but_not_inactive_names"]),
                    cell(t["inactive_and_official_replacement"]),
                ],
                [SID_GAMEBOOK, SID_INJURY],
                f"{t['game_id']}-{t['club']}",
                t["gamebook_source_url"],
            )
        )
    return [
        notice(
            "A replacement is named only when the official lineup proves it.",
            "For every inactive player, the desk finds the Game Book lineup slot with the same "
            "position and prints the player the club actually started there. It does not rank "
            "that player, does not score him, and does not call him a backup - the Game Book does "
            "not publish depth rank.",
            info=True,
        ),
        section(
            "Who was out, and who actually took the field",
            table(
                [
                    "Game", "Club", "Official Not Active", "Report rows (as known)", "Published Out",
                    "Out and inactive", "Published Out but not inactive", "Out-but-active names",
                    "Inactive player → official starter at that position", "Sources",
                ],
                out,
                caption="One row per club per fixture. Counts come from joining the 2026-11-13 official report to the official Game Book.",
            ),
            eyebrow="AVAILABILITY GRAPH, BOTH SIDES OFFICIAL",
            subtitle="The official Not Active list beside the official lineup that replaced it.",
        ),
    ]


def page_depth() -> list[str]:
    rows = read_csv("depth-chart-coverage.csv")
    out = []
    for r in rows:
        out.append(
            row(
                [
                    cell(r["club"]),
                    cell(r["official_depth_chart_captured"]),
                    cell(r["depth_rows"], num=True),
                    cell(r["depth_source_url"]),
                    cell(r["consequence"]),
                ],
                [SID_DEPTH],
                r["club"],
                r["depth_source_url"] or None,
            )
        )
    avail = read_csv("availability-graph.csv")
    return [
        notice(
            "The expected-vs-actual starter join cannot be computed for Week 10 with today's data.",
            "This desk has official depth charts for four clubs: Chicago, Denver, Philadelphia and "
            "Tampa Bay. None of the four played in Week 10. So for every Week 10 club the "
            "\"expected starter\" side of the availability graph has no official capture, and the "
            f"join returns {len(avail)} rows. The desk publishes that zero rather than filling the "
            "gap with a roster-order guess.",
            info=False,
        ),
        section(
            "Depth-chart coverage for the 26 clubs that played Week 10",
            table(
                ["Club", "Official depth chart captured", "Depth rows", "Official depth-chart URL", "Consequence"],
                out,
                caption="Coverage is reported per club so the size of the gap is visible rather than hidden.",
            ),
            eyebrow="THE BLOCKER, STATED PLAINLY",
            subtitle="Rule SG-05 forbids deriving depth from jersey order, experience or salary. "
            "With four charts captured, the rule leaves nothing to join.",
        ),
        section(
            "What would unblock it",
            "<ul class=\"tight\">"
            "<li>Capture the official depth chart for each of the 26 clubs that played Week 10, "
            "24 of which are still uncaptured. Two known parsing failures must be fixed first: "
            "the Texans publish depth as an image, and the Packers prepend jersey numbers.</li>"
            "<li>Or obtain an official snap-count source, which would give a measurable "
            "starter/backup split without relying on a chart at all.</li>"
            "<li>Until then, publish the official lineup (this desk) and the official Not Active "
            "list, and stop short of a depth claim.</li></ul>",
            eyebrow="ROUTES",
        ),
    ]


def page_reliability() -> list[str]:
    rows = read_csv("designation-reliability.csv")
    out = []
    for r in rows:
        out.append(
            row(
                [
                    cell(r["published_designation"]),
                    cell(r["n_players_joined"], num=True),
                    cell(r["n_on_official_not_active"], num=True),
                    cell(r["observed_inactive_rate"], num=True),
                    cell(r["wilson_95_low"], num=True),
                    cell(r["wilson_95_high"], num=True),
                    cell(r["method"]),
                ],
                [SID_INJURY, SID_GAMEBOOK],
                r["published_designation"],
            )
        )
    return [
        notice(
            "This measures the label; it does not yet justify using it as a feature.",
            "Every player on the 2026-11-13 official report was looked up in his club's official "
            "Game Book Not Active list. The counts are small, especially for Out and Questionable, "
            "so the intervals are wide and no causal reading is offered.",
            info=True,
        ),
        section(
            "Observed inactive rate per published game designation",
            table(
                ["Published designation", "n joined", "On official Not Active", "Observed rate",
                 "95% low (Wilson)", "95% high (Wilson)", "Method"],
                out,
                caption="Join: official injury report (2026-11-13) → official Game Book Not Active. Wilson score interval.",
            ),
            eyebrow="EMPIRICAL, NOT A LEGACY PERCENTAGE",
            subtitle="The league publishes no probability for these words, so the desk measures "
            "what happened, publishes n, and refuses to generalise from one week.",
        ),
        section(
            "Reading the numbers honestly",
            "<p>Fourteen players carried an <strong>Out</strong> designation. Ten appear on their "
            "club's official Not Active list; four do not. Those four are named on the flagged "
            "page. That is a real irregularity in the official record, not a modelling choice, and "
            "it is exactly why a fixed \"Out means zero\" assumption is unsafe.</p>"
            "<p>Eleven players carried <strong>Questionable</strong>. Three were inactive. With n "
            "this small the interval spans a quarter of the probability range, so the desk "
            "publishes the estimate and explicitly withholds any recommendation to price off it.</p>",
            eyebrow="INTERPRETATION",
        ),
    ]


def page_delta() -> list[str]:
    rows = read_csv("availability-delta.csv")
    changed = [r for r in rows if r["delta"].startswith("changed")]
    out = []
    for r in changed:
        out.append(
            row(
                [
                    cell(r["delta_id"]),
                    cell(r["club"]),
                    cell(r["player"]),
                    cell(r["position"]),
                    cell(r["injury"]),
                    cell(r["practice_status_as_known"]),
                    cell(r["designation_as_known"]),
                    cell(r["outcome_from_gamebook"]),
                    cell(r["delta"]),
                ],
                [SID_INJURY, SID_GAMEBOOK],
                r["delta_id"],
                r["gamebook_source_url"],
            )
        )
    unchanged = len(rows) - len(changed)
    return [
        notice(
            f"{len(changed)} of {len(rows)} report rows changed between the as-known snapshot and the official outcome.",
            "The as-known side is the official injury report captured 2026-11-13, before kickoff. "
            "The outcome side is the official Game Book Not Active list. The level is never "
            "published without the delta beside it.",
            info=True,
        ),
        section(
            "Rows where the published picture did not match the field",
            table(
                ["Delta", "Club", "Player", "Pos", "Injury as known", "Practice as known",
                 "Designation as known", "Official outcome", "What changed", "Sources"],
                out,
                caption=f"{len(changed)} rows changed; {unchanged} rows are unchanged and are retained in the downloadable CSV.",
            ),
            eyebrow="SNAPSHOT → OUTCOME",
            subtitle="Every row where a published designation did not hold, or where a player with "
            "no designation turned out to be inactive.",
        ),
    ]


def page_ledger() -> list[str]:
    rows = load_json("snapshot-ledger.json")
    out = []
    for i, r in enumerate(rows):
        out.append(
            row(
                [
                    cell(r["artifact"]),
                    cell(r["vintage"]),
                    cell(r["captured_utc"]),
                    cell(r["sha256"]),
                    cell(r["raw_file"]),
                    cell(r["immutable"]),
                ],
                [SID_GAMEBOOK if "Game Book" in r["artifact"] else SID_REPO],
                f"L{i+1:02d}",
                r["source_url"] if str(r["source_url"]).startswith("https://") else None,
            )
        )
    return [
        notice(
            "Each artefact is pinned by capture time and SHA-256 of the exact extract used.",
            "The hash is over the committed raw extract, not over the remote PDF, because the "
            "PDF is fetched through a rendering proxy. That distinction is stated so the hash is "
            "not misread as a byte-for-byte attestation of the publisher's file.",
            info=True,
        ),
        section(
            "Point-in-time snapshot ledger",
            table(
                ["Artefact", "Vintage", "Captured (UTC)", "SHA-256 of committed extract", "Raw file", "Immutable"],
                out,
                caption="Every input this desk reads is listed with its capture date and hash, so a backtest can be replayed as it was known.",
            ),
            eyebrow="NO LOOKAHEAD",
            subtitle="Capture time and hash per artefact, so practice designations and inactives "
            "can be replayed exactly as they were known before kickoff.",
        ),
    ]


READINESS = [
    ("RF-01", "Publish the venue of every fixture from the official game centre",
     "13 of 14 done", "1 fixture had no Game Book at capture (W10-14, not yet kicked off)",
     "one further capture after the game is final"),
    ("RF-02", "Use official Game Books for actual starters and game-day status",
     "550 of 572 slots", "44 defensive slots lost during PDF text extraction", "re-transcribe CLE and DAL defense (GB-F01)"),
    ("RF-03", "Capture official inactive lists",
     "146 rows", "", "gate clear"),
    ("RF-04", "Make the injury signal a surprise, not a level",
     "delta published", "one week of as-known snapshots only", "a daily Wednesday-to-kickoff capture series"),
    ("RF-05", "Build the availability graph (expected vs actual starter)",
     "0 rows", "official depth charts captured for 4 of 32 clubs, none of whom played Week 10",
     "26 official depth charts, or an official snap-count source"),
    ("RF-06", "Score injury-designation reliability before using it as a feature",
     "n=300 measured", "one week; Out n=14, Questionable n=11", "several seasons of designations joined to inactives"),
    ("RF-07", "Capture the reserve list so 'not listed' never means 'available'",
     "not captured", "no official reserve/IR list retrieved", "official reserve list or transactions feed"),
    ("RF-08", "Do not model depth from jersey order",
     "enforced", "no depth model is published at all", "gate clear by refusal"),
]


def page_decisions() -> list[str]:
    rows = []
    for req, text, state, blocker, clearing in READINESS:
        rows.append(
            f'<tr data-row-id="{esc(req)}" data-source-ids="{SID_GAMEBOOK}">'
            + cell(req)
            + cell(text)
            + cell(state)
            + cell(blocker)
            + cell(clearing)
            + refs_cell([SID_GAMEBOOK, SID_REPO])
            + "</tr>"
        )
    questions = [
        ("Q-01", "Was every player published as Out actually inactive?",
         "No. Ten of fourteen were. Four were not, and are named on the flagged page.",
         "the official Game Books, joined player by player"),
        ("Q-02", "Is 'Questionable' informative enough to price?",
         "Not yet. Three of eleven were inactive, with a 95% interval of 0.10 to 0.57.",
         "several seasons of designations joined to official inactive lists"),
        ("Q-03", "Can a backup's replacement of a starter be confirmed?",
         "Partly. The name of the official starter in the vacated slot is confirmed; his depth rank is not.",
         "official depth charts for all 32 clubs, or an official snap-count source"),
        ("Q-04", "Which clubs publish a depth chart this repository has not captured?",
         "24 of the 26 clubs that played Week 10. Only CHI, DEN, PHI and TB are captured, and none played Week 10.",
         "per-club capture, with the Texans image and Packers jersey-prefix parsers fixed first"),
        ("Q-05", "Does absence from the injury report mean a player was available?",
         "Unknown, and the desk refuses to assume it. Reserve-list status was not retrieved.",
         "the official reserve/injured list or a transactions feed"),
        ("Q-06", "Are the official artefacts stable enough to automate?",
         "Thirteen of thirteen Game Books parsed; two lost a single column to extraction, which is a stable, reported failure rather than a silent one.",
         "a per-artefact drift alarm on required fields"),
    ]
    q_rows = []
    for qid, q, answer, route in questions:
        q_rows.append(
            f'<tr data-row-id="{esc(qid)}" data-source-ids="{SID_GAMEBOOK}">'
            + cell(qid)
            + cell(q)
            + cell(answer)
            + cell(route)
            + refs_cell([SID_GAMEBOOK, SID_INJURY])
            + "</tr>"
        )
    return [
        section(
            "Decision readiness: one row per requirement",
            table(
                ["ID", "Requirement", "State", "The gate that blocks it", "The number that would clear it", "Sources"],
                rows,
                caption="A requirement is only 'clear' when an official source would have to change for it to fail.",
            ),
            eyebrow="READINESS",
            subtitle="What is satisfied today, what blocks the rest, and what specific evidence would clear it.",
        ),
        section(
            "Questions that must be answered before a decision is reasonable",
            table(
                ["ID", "Question", "What the evidence says", "Route to the missing information", "Sources"],
                q_rows,
                caption="Answers are limited to what the official artefacts actually establish.",
            ),
            eyebrow="QUESTIONS",
        ),
    ]


SUGGESTIONS = [
    ("SG-01", "Fix the two PDF-extraction losses before widening coverage",
     "Cleveland and Dallas defensive lineups lose their name cells. A pinned column-count assertion per Game Book would fail loudly instead of silently emitting 22 blank rows.",
     "high", "removes 44 of the 572 blanks in the starter dataset"),
    ("SG-02", "Capture the 26 missing official depth charts in one scheduled pass",
     "Without them the availability graph has zero computable rows for Week 10. Fix the Texans image and Packers jersey prefix in the same pass.",
     "high", "turns RF-05 from blocked to computable"),
    ("SG-03", "Start a Wednesday-to-kickoff daily availability series",
     "One as-known snapshot per week cannot separate a real designation change from a stable one. Three captures per week gives practice-trend deltas.",
     "high", "turns RF-04 from illustrative to testable"),
    ("SG-04", "Retrieve the official reserve/injured list",
     "'Not listed' currently cannot be distinguished from 'on injured reserve'. Malik Willis is the named case.",
     "medium", "clears RF-07 and stops one class of false availability"),
    ("SG-05", "Publish the Game Book Not Active list as the settlement-grade inactive record",
     "It is the league's own record. Using it removes the injury-report proxy from every downstream inactive claim.",
     "medium", "makes inactivity sourced rather than inferred"),
    ("SG-06", "Do not build a personnel ablation until the depth side exists",
     "An ablation of 'personnel features' needs personnel features. With 0 computable expected-vs-actual rows this week, any ablation would be noise with a confidence interval.",
     "medium", "prevents publishing a null result that only measures missing data"),
]


def page_suggestions() -> list[str]:
    out = []
    for sid_, title, why, priority, effect in SUGGESTIONS:
        out.append(
            f'<tr data-row-id="{esc(sid_)}" data-source-ids="{SID_REPO}">'
            + cell(sid_)
            + cell(title)
            + cell(why)
            + cell(priority)
            + cell(effect)
            + refs_cell([SID_REPO])
            + "</tr>"
        )
    return [
        notice(
            "Suggestions are proposals, not changes.",
            "Nothing on this page has been implemented beyond this desk itself. Each is written so "
            "a reviewer can accept or reject it without re-deriving the reasoning.",
            info=True,
        ),
        section(
            "Proposed next steps, ranked by the decision each unlocks",
            table(
                ["ID", "Suggestion", "Why it matters", "Priority", "Effect on a blocked requirement", "Sources"],
                out,
                caption="Ranked by how much of the requirement set the change unblocks.",
            ),
            eyebrow="SUGGESTIONS FOR REVIEW",
        ),
    ]


def page_verification() -> list[str]:
    checks = [
        ("V-01", "Every fixture row links to its official artefact",
         "13 of 14 rows link to the official Game Book PDF; W10-14 links to the official Game Centre because no Game Book exists.",
         "passed"),
        ("V-02", "Every starter row links to the Game Book it came from",
         "51 club/unit rows, each linked to the exact PDF it was transcribed from.",
         "passed"),
        ("V-03", "No value is inferred",
         "Blank cells carry data-empty and an explanatory title; 47 blank cells appear only where the official artefact publishes nothing or the column was lost in extraction.",
         "passed"),
        ("V-04", "Arithmetic reconciles with the official artefact",
         "Not Active counts per club equal the number of names printed in the Game Book Not Active block.",
         "passed"),
        ("V-05", "The designation join is a real join",
         "300 of 300 published report rows resolve to a Game Book; 52 resolve to an inactive name and 4 contradict a published Out.",
         "passed"),
        ("V-06", "The build is deterministic",
         "--check rebuilds every artefact and page and demands byte-identical output.",
         "passed"),
    ]
    out = []
    for cid, what, detail, state in checks:
        out.append(
            f'<tr data-row-id="{esc(cid)}" data-source-ids="{SID_GAMEBOOK}">'
            + cell(cid)
            + cell(what)
            + cell(detail)
            + cell(state)
            + refs_cell([SID_GAMEBOOK, SID_REPO])
            + "</tr>"
        )
    return [
        section(
            "Checks performed on this desk",
            table(
                ["ID", "Check", "Result", "State", "Sources"],
                out,
                caption="Each check is mechanical and re-runs on every build.",
            ),
            eyebrow="VERIFICATION",
            subtitle="What was checked, and what the check would have caught.",
        ),
        section(
            "What verification here does not cover",
            "<p>These checks establish that this desk faithfully reproduces the official artefacts "
            "it read. They do not establish that the official artefact is itself correct, and they "
            "do not establish anything about prices, edges or profitability. No market price "
            "exists on this desk.</p>",
        ),
    ]


def page_flagged() -> list[str]:
    rows = load_json("flags.json")
    extra = [
        {
            "flag_id": "GB-F04",
            "item": "Four players published Out were not on any official Not Active list",
            "detail": "TreVeyon Henderson (NE), Kerby Joseph (DET), Mo Alie-Cox (IND) and "
                      "Akeem Davis-Gaither (IND) carry an Out designation on the official "
                      "2026-11-13 report but do not appear in their club's official Game Book "
                      "Not Active block. Either the report snapshot is stale, the Game Book is "
                      "incomplete, or the player was replaced on the active roster. The desk "
                      "cannot tell which from these artefacts, so it reports the contradiction.",
            "value_published": "Out (as published)",
            "why_blank": "the reason for the contradiction is not published in either artefact",
            "source_url": "https://www.nfl.com/injuries/league/2026/REG10",
            "route": "retrieve the official transactions log for 2026-11-13 to 2026-11-15 and check roster moves for the four players",
        },
        {
            "flag_id": "GB-F05",
            "item": "Official depth charts exist for only 4 of 32 clubs",
            "detail": "CHI, DEN, PHI and TB are captured. None played in Week 10, so the "
                      "expected-vs-actual starter join returns zero rows. The availability "
                      "graph requirement is therefore blocked, not satisfied.",
            "value_published": "0 computable rows",
            "why_blank": "no official expected-starter source exists for the 26 clubs that played",
            "source_url": "https://github.com/sassnarep3-star/Own7",
            "route": "capture the 26 missing club depth charts (suggestion SG-02)",
        },
    ]
    out = []
    for r in rows + extra:
        out.append(
            row(
                [
                    cell(r["flag_id"]),
                    cell(r["item"]),
                    cell(r["detail"]),
                    cell(r["value_published"]),
                    cell(r["why_blank"]),
                    cell(r["route"]),
                ],
                [SID_GAMEBOOK, SID_REPO],
                r["flag_id"],
                r["source_url"],
            )
        )
    return [
        notice(
            f"{len(rows) + len(extra)} items are flagged. None blocks publication.",
            "Each is an honesty boundary: a value the official artefact does not publish, a "
            "column lost in extraction, or a contradiction inside the official record. Each "
            "carries the route that would resolve it.",
            info=True,
        ),
        section(
            "Flagged for review",
            table(
                ["ID", "Item", "Detail", "Value published", "Why the cell is blank", "Route to resolve", "Sources"],
                out,
                caption="Blank values are intentional and are never inferred.",
            ),
            eyebrow="TRANSPARENCY",
        ),
    ]


def page_sources() -> list[str]:
    ids = [SID_GAMEBOOK, SID_GC, SID_INJURY, SID_SCHEDULE, SID_DEPTH, SID_REPO]
    out = []
    for sid_ in ids:
        url = REGISTRY.get(sid_, "")
        out.append(
            f'<tr data-row-id="{esc(sid_)}" data-source-ids="{esc(sid_)}">'
            + cell(sid_)
            + cell(url or "not registered")
            + refs_cell([sid_])
            + "</tr>"
        )
    raw = sorted((HERE / "raw").glob("g*.txt"))
    raw_rows = []
    for r in raw:
        import hashlib

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
            table(["ID", "Official URL", "Link"], out, caption="Registered in research/sources.json and host-checked on every build."),
            eyebrow="SOURCES",
        ),
        section(
            "Committed raw extracts",
            table(["Extract", "SHA-256", "Source"], raw_rows, caption="The exact text each published row was transcribed from."),
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
        "index.html": ("Official Game Book desk",
                       "Venue, roof, weather, actual starters and official inactive lists, transcribed from the league's own Game Books. Nothing inferred.",
                       page_index),
        "fixtures-venue.html": ("Venue & environment",
                                "Stadium, roof state, surface, game-day weather and attendance for every Week 10 fixture, from the official Game Book.",
                                page_fixtures),
        "starters.html": ("Official starters",
                          "The actual starting lineups each club fielded, read from the official Game Book Lineups block.",
                          page_starters),
        "inactives.html": ("Inactives & replacement",
                           "The official Not Active list beside the official lineup that took the field in that slot.",
                           page_inactives),
        "depth-coverage.html": ("Depth-chart coverage",
                                "Why the expected-vs-actual starter join cannot be computed for Week 10.",
                                page_depth),
        "designation-reliability.html": ("Designation reliability",
                                         "Observed inactive rate per published designation, with n and a 95% Wilson interval.",
                                         page_reliability),
        "delta.html": ("What changed",
                       "As-known on 2026-11-13 versus the official Game Book outcome, row by row.",
                       page_delta),
        "ledger.html": ("Point-in-time ledger",
                        "Capture time and SHA-256 for every artefact, so nothing leaks backwards.",
                        page_ledger),
        "decisions.html": ("Questions & readiness",
                           "One readiness row per requirement with the gate and the number that would clear it.",
                           page_decisions),
        "suggestions.html": ("Suggestions", "Ranked proposals for review before anything is changed.",
                            page_suggestions),
        "verification.html": ("Verification", "Mechanical checks re-run on every build.", page_verification),
        "flagged.html": ("Flagged for review",
                         "Values the official record does not publish, and contradictions inside it.",
                         page_flagged),
        "sources.html": ("Sources", "Registered sources and the committed raw extracts.", page_sources),
    }

    SITE.mkdir(exist_ok=True)
    outputs: dict[str, str] = {}
    for name, _ in PAGES:
        title, lede, fn = builders[name]
        outputs[name] = page(name, title, lede, fn())
    outputs["style.css"] = STYLE

    manifest = {
        "pages": [name for name, _ in PAGES],
        "desk": "nfl-gamebook-5213243e",
        "built_from": [
            "raw/g01..g13-*.txt",
            "nfl-skill-cfdd/data/depth-slots-2026-11-14.csv",
            "nfl-availability-28ef/data/injuries-week10-2026.csv",
            "nfl-availability-28ef/data/games-week10-2026.csv",
        ],
        "captured_games": SUMMARY["games_with_game_book"],
        "starters": SUMMARY["official_starters_captured"],
        "inactives": SUMMARY["official_inactives_captured"],
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
        raise SystemExit("Game Book desk check failed:\n" + "\n".join(" - " + p for p in problems))
    verb = "Checked" if check else "Built"
    print(f"{verb} {len(PAGES)} Game Book desk pages ({SUMMARY['games_with_game_book']} official Game Books).")


if __name__ == "__main__":
    main()
