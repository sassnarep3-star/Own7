#!/usr/bin/env python3
"""Deterministic builder for the OWN7 NFL sub-site (standard library only).

No network access. Everything comes from ``nfl/data.json``, ``nfl/content.json``,
``nfl/model.py`` and the CSV snapshots in ``nfl/data/``. Every table body row
carries registered official source IDs and a link to the registered URL; blank
cells are emitted empty with a status label and are never filled in.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path

from model import compute, load_games, load_standings

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.json"
CONTENT = ROOT / "content.json"
MANIFEST = ROOT / "manifest.json"

PAGES = [
    "index.html",
    "executive-summary.html",
    "model.html",
    "injuries.html",
    "depth.html",
    "strategies.html",
    "validation.html",
    "correlation.html",
    "leaderboard.html",
    "suggestions.html",
    "questions.html",
    "sources.html",
    "flagged.html",
    "repo-review.html",
]

NAV = [
    ("Lab", [
        ("index.html", "Dashboard"),
        ("executive-summary.html", "Executive summary"),
        ("model.html", "Model & lines"),
        ("injuries.html", "Injuries"),
        ("depth.html", "Depth & deficiencies"),
    ]),
    ("Protocol", [
        ("strategies.html", "Strategies"),
        ("validation.html", "Validation gates"),
        ("correlation.html", "Correlations"),
        ("leaderboard.html", "Leaderboard"),
    ]),
    ("Decisions", [
        ("suggestions.html", "Suggestions"),
        ("questions.html", "Open questions"),
    ]),
    ("Transparency", [
        ("sources.html", "Sources"),
        ("flagged.html", "Flagged for review"),
        ("repo-review.html", "Repository review"),
    ]),
]


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(name: str) -> list[dict]:
    with (ROOT / "data" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def badge(text: str) -> str:
    key = (text or "").lower()
    if any(word in key for word in ("pass", "answered", "control")):
        css = "good" if "control" not in key else "blue"
    elif any(word in key for word in ("fail", "blocked", "unverified", "open", "partial", "gap")):
        css = "warn"
    elif "procedural" in key:
        css = "neutral"
    else:
        css = "neutral"
    return f'<span class="badge {css}"><span class="tiny-dot"></span>{esc(text)}</span>'


def table(table_id, title, columns, rows, *, note="", filter_options=None, export=True):
    """Same contract as the rest of the site: sources on every row, blanks empty."""
    header_cells = "".join(
        f'<th scope="col" aria-sort="none"><button type="button" data-sort="{i}">{esc(label)}'
        f'<span class="sort-mark" aria-hidden="true">&#8597;</span></button></th>'
        for i, (label, _) in enumerate(list(columns) + [("Sources / references", "__refs")])
    )
    body = []
    for index, row in enumerate(rows):
        cells = []
        for _, field in columns:
            value = field(row) if callable(field) else row.get(field)
            if value is None or value == "":
                cells.append('<td class="blank" data-empty="true" '
                             'aria-label="Blank - unverified, withheld or not applicable" '
                             'title="Not supplied; see the flagged page"></td>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                text = str(value) if isinstance(value, int) else f"{value:.3f}".rstrip("0").rstrip(".")
                cells.append(f'<td class="num" data-value="{value}">{esc(text)}</td>')
            else:
                cells.append(f"<td>{value}</td>")
        cells.append(f'<td class="refs">{refs(row.get("source_ids", []), SOURCE_URLS)}</td>')
        status = row.get("status") or row.get("state") or ""
        body.append(
            f'<tr data-row-id="{esc(row.get("id", index))}" '
            f'data-source-ids="{esc(" ".join(row.get("source_ids", [])))}" '
            f'data-status="{esc(status)}">' + "".join(cells) + "</tr>"
        )
    select = ""
    if filter_options:
        select = ('<label><span class="sr-only">Filter by status</span>'
                  f'<select data-status-filter="{table_id}"><option value="">All statuses</option>'
                  + "".join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in filter_options)
                  + "</select></label>")
    exporting = (f'<button class="export-button" type="button" data-export="{table_id}">CSV'
                 f'<span class="sr-only">: download {esc(title)}</span></button>') if export else ""
    markup = f'''<div class="table-card" data-table-card="{table_id}">
<div class="table-toolbar"><span class="row-count" data-count-for="{table_id}" aria-live="polite">{len(rows)} entries</span><div class="table-tools">{select}<label class="table-search"><span class="sr-only">Search {esc(title)}</span><input type="search" placeholder="Filter rows&hellip;" data-search-for="{table_id}" autocomplete="off"></label>{exporting}</div></div>
<div class="table-scroll" role="region" aria-label="{esc(title)} table, scroll horizontally for more columns" tabindex="0"><table id="{table_id}" data-research-table><caption class="sr-only">{esc(title)}. Blank cells are intentional; a source is linked on every row.</caption><thead><tr>{header_cells}</tr></thead><tbody>{"".join(body)}</tbody></table></div>
<p class="table-empty" data-empty-for="{table_id}" hidden>No matching entries. Clear the filters to see all rows.</p>
</div>'''
    if note:
        markup += f'<p class="table-note">{note}</p>'
    return markup


SOURCE_URLS: dict[str, str] = {}
SOURCE_META: dict[str, dict] = {}


def refs(source_ids, urls) -> str:
    out = []
    for sid in source_ids:
        url = urls.get(sid, "")
        meta = SOURCE_META.get(sid, {})
        title = meta.get("title", sid)
        out.append(f'<a href="{esc(url)}" title="{esc(title)}" target="_blank" '
                   f'rel="noopener noreferrer">{esc(sid)} &#8599;</a>')
    return "".join(out)


def shell(slug, title, lead, body, eyebrow):
    groups = []
    for label, entries in NAV:
        links = []
        for href, text in entries:
            current = ' aria-current="page"' if href == slug else ""
            links.append(f'<a href="{href}"{current}>{esc(text)}</a>')
        groups.append(f'<div class="nav-group"><div class="nav-label">{esc(label)}</div>{"".join(links)}</div>')
    nav = "".join(groups)
    project = PROJECT
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(project["title"])}: {esc(lead)}"><meta name="referrer" content="strict-origin-when-cross-origin">
<title>{esc(title)} &middot; OWN7 NFL Line Lab</title>
<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../assets/style.css"><link rel="stylesheet" href="style.css">
<script src="../js/app.js" defer></script></head>
<body><a class="skip-link" href="#main-content">Skip to content</a>
<aside class="sidebar" id="sidebar" aria-label="NFL workspace"><a class="brand" href="index.html" aria-label="OWN7 NFL Line Lab home"><span class="brand-mark" aria-hidden="true">7</span><span class="brand-name">OWN7<small>NFL LINE LAB</small></span></a>
<nav aria-label="NFL sections">{nav}</nav>
<div class="sidebar-bottom"><a href="../index.html">&#8592; Main research site</a><a href="https://github.com/sassnarep3-star/Own7" target="_blank" rel="noopener noreferrer">View repository &#8599;</a><div class="mode"><span class="dot"></span>NON-COMMERCIAL RESEARCH</div><p>No market price. No qualified strategy. No reward paid.</p></div></aside>
<button class="nav-backdrop" aria-label="Close navigation" tabindex="-1" hidden></button>
<div class="layout"><header class="topbar"><button type="button" class="menu-button" aria-label="Open navigation" aria-expanded="false" aria-controls="sidebar">&#9776;</button>
<div class="breadcrumb"><span class="crumb-parent">NFL lab</span><span class="divider">/</span><strong>{esc(title)}</strong></div>
<div class="top-right"><label class="search-field"><span class="sr-only">Search tables on this page</span><input type="search" id="page-search" placeholder="Search this page&hellip;" autocomplete="off"><kbd aria-hidden="true">/</kbd></label><div class="snapshot">SNAPSHOT CHECKED<span>{esc(project["checked_on"])}</span></div></div></header>
<main id="main-content"><div class="content">
<div class="page-heading"><div><p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(title)}</h1><p>{esc(lead)}</p></div></div>
{body}
<footer class="footer"><div><strong>OWN7</strong> / NFL LINE LAB<br>NFL data attributed to NFL.com and the publishing club. Not affiliated with or endorsed by the NFL.</div><div>Dated manual snapshots &middot; not a live feed<br><a href="flagged.html">Limitations</a> &nbsp;&middot;&nbsp; <a href="sources.html">Sources</a> &nbsp;&middot;&nbsp; <a href="../responsible-gambling.html">Responsible use</a></div></footer>
</div></main></div></body></html>'''


def notice(text, kind="warning", action=""):
    css = "notice warning" if kind == "warning" else "notice info"
    link = f'<a href="{action[1]}">{esc(action[0])}</a>' if action else ""
    return f'<div class="{css}"><strong>{esc(text)}</strong>{link}</div>'


def section(title, body, subtitle="", sid=""):
    ident = f' id="{sid}"' if sid else ""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    return f'<section class="section"{ident}><div class="section-head"><div><h2>{esc(title)}</h2>{sub}</div></div>{body}</section>'


def metric_grid(items):
    cards = []
    for label, value, note in items:
        cards.append(f'<div class="metric"><div class="metric-top">{esc(label)}</div>'
                     f'<div class="metric-value">{esc(value)}</div><small>{esc(note)}</small></div>')
    return '<div class="metric-grid">' + "".join(cards) + "</div>"


def path_cards(items):
    cards = []
    for step, title, text, href, link in items:
        cards.append(f'<a class="path-card" href="{href}"><span class="step">{esc(step)}</span>'
                     f'<h3>{esc(title)}</h3><p>{esc(text)}</p>'
                     f'<span class="card-link">{esc(link)} &rarr;</span></a>')
    return '<div class="grid-3">' + "".join(cards) + "</div>"


def render():
    data = load_json(DATA)
    content = load_json(CONTENT)
    model = compute()
    standings = load_standings()
    games = load_games()
    injuries = read_csv("injuries-2026-w10.csv")
    depth = read_csv("depth-2026-w10.csv")
    by_code = {row["code"]: row for row in standings}
    project = data["project"]
    global PROJECT

    PRACTICE_ORDER = {"DNP": 0, "Limited": 1, "Full": 2, "": 3}
    injuries.sort(key=lambda r: (r["club"], PRACTICE_ORDER.get(r["practice"], 4), r["player"]))
    for i, row in enumerate(injuries):
        row["id"] = f"I{ i + 1:03d}"
        row["source_ids"] = row["sources"].split()
    for i, row in enumerate(depth):
        row["id"] = f"D{ i + 1:03d}"
        row["source_ids"] = row["sources"].split()
    for row in standings:
        row["id"] = row["code"]

    pages = {}

    # ---------------------------------------------------------------- dashboard
    qualified = sum(1 for s in data["strategies"] if s["status"] == "Passed")
    gate_fail = sum(1 for g in data["gates"] if g["status"] == "Fail")
    checks = model["checks"]
    dashboard = (
        notice("Read this first: there is no market price anywhere on this site, no strategy has passed validation and no reward is paid. "
               "Those are verified states, not gaps in the text.", "warning", ("Why the leaderboard is empty", "leaderboard.html"))
        + metric_grid([
            ("Week 10 games modelled", str(len(model["projections"])), "model-implied spread and total, each with a range"),
            ("Injury rows checked", str(len(injuries)), "practice status and designations, 28 clubs, dated 12 Nov 2026"),
            ("Strategies qualified", f"{qualified} of {len(data['strategies'])}", "all registered strategies are blocked"),
            ("Validation gates failing", f"{gate_fail} of {len(data['gates'])}", "no price, no sample, no out-of-sample test"),
        ])
        + path_cards([
            ("01 / SUMMARY", "Executive summary", "The twelve questions this project can answer today, with sources, and the ones it cannot.", "executive-summary.html", "Read the summary"),
            ("02 / LINES", "Model & lines", "Spreads and totals derived from official standings, with a sensitivity range and no market column.", "model.html", "See the model"),
            ("03 / INJURIES", "Injuries", "208 player rows, practice status and designations, matched against a second official page.", "injuries.html", "Open the report"),
            ("04 / DEPTH", "Depth & deficiencies", "First string, second string, third string - and the five starters whose club lists no replacement at all.", "depth.html", "Check the gaps"),
            ("05 / SUGGESTIONS", "Suggestions", "Twelve decisions with options, a recommendation and a decision slot. Choose the path before building.", "suggestions.html", "Review suggestions"),
            ("06 / QUESTIONS", "Open questions", "What we have, what is missing, and exactly how to obtain it from an official source.", "questions.html", "See what is missing"),
        ])
        + section("What is verified today", '<div class="panel body-text">'
                  "<p><strong>Standings.</strong> All 32 club rows were read from the official standings page. Three independent arithmetic checks pass on every row: "
                  "win percentage, net points, and the league-wide identity that total points for equal total points against "
                  f"({checks['pf_sum']:,} = {checks['pa_sum']:,}).</p>"
                  "<p><strong>Injuries.</strong> Practice participation for the Week 10 slate was read twice - once from the injury page and once from the official "
                  "Wednesday roundup - and the two agree on every player named in both. Seven players are already ruled out.</p>"
                  "<p><strong>Depth.</strong> Three club depth charts were read in full. One of them prints an update date; the other two do not.</p>"
                  "</div>")
        + section("What is missing", '<div class="panel body-text">'
                  "<p><strong>Prices.</strong> No verified market price exists, so no edge, return or closing-line value can be computed. "
                  "The league odds path returned 404 and no official league price publication was located.</p>"
                  "<p><strong>Sunday designations.</strong> The Game Status Report for a Sunday game is due Friday at 4 p.m. New York time. It does not exist yet, "
                  "so any number published today would be built on Wednesday news.</p>"
                  "<p><strong>Depth coverage.</strong> 25 of the 28 clubs in the slate have no depth evidence in this repository.</p>"
                  "</div>")
        + section("Section status", table("status", "Section status", [
            ("Section", lambda r: f'<a href="{r["href"]}">{esc(r["section"])}</a>'),
            ("State", lambda r: badge(r["status"])),
            ("Why", "why"),
        ], [
            {"id": "S-1", "section": "Model & lines", "href": "model.html", "status": "Derived only", "why": "Model output from official standings; no market column exists.", "source_ids": ["NFL-STANDINGS"]},
            {"id": "S-2", "section": "Injuries", "href": "injuries.html", "status": "Verified, dated", "why": "Two official pages matched on every overlapping player.", "source_ids": ["NFL-INJURIES", "NFL-ROUNDUP"]},
            {"id": "S-3", "section": "Depth & deficiencies", "href": "depth.html", "status": "Partial", "why": "3 of 28 clubs read; no league-wide depth endpoint exists.", "source_ids": ["SF-DEPTH", "NFL-DEPTH-PATH"]},
            {"id": "S-4", "section": "Strategies", "href": "strategies.html", "status": "Blocked", "why": "Eight registered, none qualified; all blocked on the same gates.", "source_ids": ["NFL-ODDS-PATH"]},
            {"id": "S-5", "section": "Correlations", "href": "correlation.html", "status": "Team level only", "why": "Leg-level correlations are blank and flagged.", "source_ids": ["SCIPY-CORR"]},
            {"id": "S-6", "section": "Leaderboard", "href": "leaderboard.html", "status": "Empty", "why": "Ranking blocked strategies would reward luck.", "source_ids": ["SM-HOLM"]},
            {"id": "S-7", "section": "Suggestions", "href": "suggestions.html", "status": "Open - needs decisions", "why": "Twelve suggestions, none implemented pending your choice.", "source_ids": ["NFL-TERMS"]},
            {"id": "S-8", "section": "Open questions", "href": "questions.html", "status": "Open", "why": "Fifteen questions, two fully answered.", "source_ids": ["NFL-DATES"]},
        ], note="Status words are project states. A link on each row resolves to the registered official source for that row's claim."))
    )
    pages["index.html"] = shell("index.html", "NFL line lab", project["subtitle"], dashboard, "WEEK 10 / 2026 SEASON / 12 NOV 2026")

    # -------------------------------------------------------- executive summary
    summary = (
        notice("The short version: the data plumbing is verified, the decision inputs are not. "
               "Two choices unblock almost everything - data rights (S-01) and a timestamped price source (S-02).", "warning",
               ("Open the suggestions", "suggestions.html"))
        + section("Direct answers", table("answers", "Questions and verified answers", [
            ("Question", "question"), ("Answer", "answer"),
        ], content["qa"], note="Answers are limited to what the cited sources support. Where the answer is 'not verified', it says so."))
        + section("Key findings", '<div class="grid-2">'
                  '<div class="panel body-text"><h3>Depth, not injury, is the missing variable</h3>'
                  "<p>Five first-string players in this week's slate have no replacement listed on their club depth chart at all - including San Francisco's left corner and nickel back, "
                  "and Cleveland's WILL linebacker. For those players, 'next man up' cannot be evaluated at any price until someone is actually listed.</p></div>"
                  '<div class="panel body-text"><h3>The injury picture is incomplete by rule</h3>'
                  "<p>Wednesday practice participation is verified for 208 rows. Game designations for Sunday exist for none of them yet, because the policy deadline is Friday. "
                  "Any Sunday price built today is stale by construction.</p></div></div>"
                  '<div class="grid-2"><div class="panel body-text"><h3>Every strategy is blocked for the same reason</h3>'
                  "<p>Six of ten gates fail on the absence of a price. The protocol itself is implemented and specified; the input does not exist.</p></div>"
                  '<div class="panel body-text"><h3>Luck is bounded, not removed</h3>'
                  "<p>Skill will be measured as a Brier skill score against a home-field control model, with a bootstrap interval and Holm adjustment across eight declared strategies. "
                  "None of that has been run, because nothing has been settled.</p></div></div>"
                  '<p class="source-line"><a href="../docs/nfl-executive-summary.md">Markdown executive summary</a> &nbsp;&middot;&nbsp; '
                  '<a href="suggestions.html">Twelve suggestions</a> &nbsp;&middot;&nbsp; <a href="questions.html">Fifteen open questions</a></p>')
        + section("Model snapshot", table("projections-brief", "Week 10 model lines (derived)", [
            ("Game", "game"), ("Model margin (home)", "model_home_margin"), ("Model total", "model_total"),
            ("Market line", "market"), ("Range (margin)", "band"),
        ], [
            {"id": p["game_id"], "game": f'{p["away"]} @ {p["home"]}', "model_home_margin": p["model_home_margin"],
             "model_total": p["model_total"], "market": "", "band": f'{p["margin_range"][0]} to {p["margin_range"][1]}',
             "source_ids": p["source_ids"]} for p in model["projections"]
        ], note="Model outputs are derived from the stated parameters and are not market prices. The market column is blank because no verified price exists."))
    )
    pages["executive-summary.html"] = shell("executive-summary.html", "Executive summary",
                                            "The important details in one place: what is verified, what is missing, and what has to be decided.",
                                            summary, "EXECUTIVE SUMMARY")

    # ------------------------------------------------------------------- model
    params = model["params"]
    grid = model["sensitivity_grid"]
    model_body = (
        notice("Every number on this page is derived from official standings rows, not from a market. "
               "The spread and total are published as a range across the parameter grid, because the parameters are design choices.", "warning",
               ("See the flagged items", "flagged.html"))
        + section("Parameters (design choices, not NFL facts)", table("params", "Model parameters", [
            ("Parameter", "name"), ("Value", "value"), ("Sensitivity grid", "grid"), ("Why", "why"),
        ], [
            {"id": "P-1", "name": "Shrinkage pseudo-games", "value": params["shrink_games"], "grid": ", ".join(str(x) for x in grid["shrink_games"]),
             "why": "Pulls each club's scoring rate toward the league mean; an 8- or 9-game rate is noisy.", "source_ids": ["NFL-STANDINGS"]},
            {"id": "P-2", "name": "Home-field points", "value": params["hfa"], "grid": ", ".join(str(x) for x in grid["hfa"]),
             "why": "A single constant; no venue-specific value is verified here.", "source_ids": ["NFL-STANDINGS"]},
            {"id": "P-3", "name": "Logistic margin scale", "value": params["sigma"], "grid": ", ".join(str(x) for x in grid["sigma"]),
             "why": "Maps a projected margin to a win probability. A convention, not a measured league value.", "source_ids": ["SCIPY-CORR"]},
            {"id": "P-4", "name": "Pythagorean exponent", "value": params["pyth_exp"], "grid": "diagnostic only",
             "why": "Used only for the diagnostic on the correlation page, never for a price.", "source_ids": ["NFL-STANDINGS"]},
            {"id": "P-5", "name": "Market line", "value": "", "grid": "not applicable",
             "why": "No verified price exists; left blank by rule.", "source_ids": ["NFL-ODDS-PATH"]},
        ], note="A value of 4 pseudo-games means a club with 8 games played is weighted two-thirds on its own rate and one-third on the league mean."))
        + section("Formula", '<div class="formula">league_avg = mean(PF/G) over 32 clubs = '
                  + str(model["league_avg_points"]) + '\noff_adj(A) = (PF/G_A * G_A + league_avg * k) / (G_A + k)\ndef_adj(A) = (PA/G_A * G_A + league_avg * k) / (G_A + k)\nexpected_home = off_adj(home) * def_adj(away) / league_avg\nexpected_away = off_adj(away) * def_adj(home) / league_avg\nmodel_margin_home = expected_home - expected_away + hfa\nmodel_total = expected_home + expected_away\nP(home win) = 1 / (1 + exp(-model_margin_home / sigma))</div>'
                  '<p class="table-note">The model is deliberately simple and fully auditable. It is a line-origination baseline, not a claim of edge.</p>')
        + section("Week 10 projections", table("projections", "Week 10 model spread and total", [
            ("Game", "game"), ("Model margin (home)", "model_home_margin"), ("Margin range", "band"),
            ("Model total", "model_total"), ("Total range", "total_band"), ("P(home win)", "p"), ("Market line", "market"),
        ], [
            {"id": p["game_id"], "game": f'<span class="row-title">{esc(p["away"])} @ {esc(p["home"])}</span>'
                                         f'<span class="row-sub">{esc(p["game_id"])}</span>',
             "model_home_margin": p["model_home_margin"],
             "band": f'{p["margin_range"][0]} to {p["margin_range"][1]}',
             "model_total": p["model_total"],
             "total_band": f'{p["total_range"][0]} to {p["total_range"][1]}',
             "p": p["model_home_win_prob"], "market": "", "source_ids": p["source_ids"]}
            for p in model["projections"]
        ], note="Ranges come from nine parameter combinations (3 shrinkage values x 3 home-field values). A positive margin means the home team is projected to win."))
        + section("Team ratings", table("ratings", "Team ratings from official standings", [
            ("Club", "code"), ("Games", "games"), ("PF/G", "pf"), ("PA/G", "pa"), ("Off adj", "off"), ("Def adj", "def"),
        ], [
            {"id": code, "code": f'{esc(by_code[code]["name"])} ({esc(code)})',
             "games": row["games"], "pf": row["pf_pg"], "pa": row["pa_pg"], "off": row["off_adj"], "def": row["def_adj"],
             "source_ids": ["NFL-STANDINGS"]} for code, row in sorted(model["ratings"].items())
        ], note="Adjusted rates apply the shrinkage parameter. Club codes match the official standings rows."))
    )
    pages["model.html"] = shell("model.html", "Model & lines",
                                "Where the numbers come from: official points for and against, turned into spreads and totals with an explicit range.",
                                model_body, "LINE ORIGINATION")

    # --------------------------------------------------------------- injuries
    practice_counts = {"DNP": 0, "Limited": 0, "Full": 0, "": 0}
    for row in injuries:
        practice_counts[row["practice"]] = practice_counts.get(row["practice"], 0) + 1
    injuries_body = (
        notice("208 player rows across 28 clubs, read from two official pages on 12 November 2026. Injury type is blank for 21 rows because neither page publishes it; "
               "the cell stays empty rather than guessed.", "warning", ("Flagged items", "flagged.html"))
        + metric_grid([
            ("Did not participate", str(practice_counts["DNP"]), "official Wednesday practice report"),
            ("Limited", str(practice_counts["Limited"]), "official Wednesday practice report"),
            ("Ruled out", str(sum(1 for r in injuries if r["designation"] == "Out")), "Thursday game and Sunday early designations"),
            ("Rows with no injury type", str(sum(1 for r in injuries if not r["injury"])), "blank, never inferred"),
        ])
        + section("Player report", table("injuries", "Week 10 injury report (practice status and designations)", [
            ("Club", "club"), ("Player", "player"), ("Injury", "injury"),
            ("Practice", lambda r: badge(r["practice"]) if r["practice"] else ""),
            ("Designation", "designation"), ("Note", "note"),
        ], injuries, filter_options=["DNP", "Limited", "Full"],
            note="Practice status is normalised to the three categories the policy uses. 'Designation' is the club's game status where one has been published; Sunday designations are due Friday and are blank today."))
        + section("By club", table("injury-clubs", "Injury rows by club", [
            ("Club", "club"), ("Name", "name"), ("Rows", "rows"), ("DNP", "dnp"), ("Limited", "limited"), ("Full", "full"), ("Ruled out", "out"),
        ], club_summary(injuries, by_code), note="Counts are computed from the rows above, so they cannot drift from the published table."))
    )
    pages["injuries.html"] = shell("injuries.html", "Injuries",
                                   "Who did not practise, who is limited, who is already ruled out - and where the source is silent.",
                                   injuries_body, "INJURY TRACKING")

    # ------------------------------------------------------------------ depth
    gap_rows = [r for r in depth if "no backup" in r["deficiency"] or "no second" in r["deficiency"] or "no third" in r["deficiency"]]
    depth_body = (
        notice("A player listed as out is only half the story. What matters is who replaces him - and for five first-string players this week, "
               "the club depth chart lists nobody.", "warning", ("Questions to resolve", "questions.html"))
        + metric_grid([
            ("Clubs with depth detail", "3", "Arizona, Cleveland, San Francisco"),
            ("Depth rows checked", str(len(depth)), "starter, second string, third string"),
            ("No backup listed", str(sum(1 for r in depth if "no backup" in r["deficiency"])), "first-string player out with nobody behind him"),
            ("Clubs in the slate", "28", "coverage is 3 of 28"),
        ])
        + section("First string, second string, third string", table("depth", "Depth and deficiency by position", [
            ("Club", "club"), ("Pos", "position"), ("First string", "starter"),
            ("Status", lambda r: badge(r["starter_status"]) if r["starter_status"] else ""),
            ("Injury", "starter_injury"), ("Second", "second_string"), ("Third", "third_string"),
            ("Deficiency", "deficiency"), ("Note", "note"),
        ], depth, note="Names and order come from each club's own depth chart; status comes from the official injury pages. Where a chart lists no backup, the cell is genuinely empty on the source."))
        + section("Coverage by club", table("coverage", "Depth and injury coverage by club", [
            ("Club", "club"), ("In the Week 10 slate", "slate"), ("Injury rows", "injuries"), ("Depth chart read", "depth"), ("Deficiency rows", "gaps"),
        ], coverage(injuries, depth, by_code), note="'No' in the depth column is a documented coverage gap, not a claim that the club has no depth."))
    )
    pages["depth.html"] = shell("depth.html", "Depth & deficiencies",
                                "Starters, backups and the holes where a club lists no replacement at all.",
                                depth_body, "ROSTER DEPTH")

    # ------------------------------------------------------------- strategies
    strategy_rows = []
    for s in data["strategies"]:
        strategy_rows.append({
            "id": s["id"], "name": f'<span class="row-title">{esc(s["name"])}</span><span class="row-sub">{esc(s["id"])}</span>',
            "family": s["family"], "hypothesis": s["hypothesis"], "signal": s["signal"],
            "verified": s["verified_today"], "missing": s["missing"],
            "blocking": ", ".join(s["blocking_gates"]), "status": badge(s["status"]), "source_ids": s["source_ids"],
        })
    strategies_body = (
        notice("Eight strategies are registered, including a control that cannot win. All eight are blocked; the leaderboard is therefore empty.",
               "warning", ("Gate detail", "validation.html"))
        + section("Registry", table("strategies", "Registered strategies", [
            ("Strategy", "name"), ("Family", "family"), ("Hypothesis", "hypothesis"), ("Signal", "signal"),
            ("Verified today", "verified"), ("Missing", "missing"), ("Blocking gates", "blocking"), ("Status", "status"),
        ], strategy_rows, note="Failing a gate is not a finding about the market; it is a statement that the evidence needed to judge the strategy does not exist yet."))
        + section("Why a control model is required", '<div class="panel body-text">'
                  "<p>A strategy is only interesting if it beats a model that knows nothing except the league average and home field. "
                  "ST-03 is that model. Publishing a score without it would make an ordinary prediction look like skill.</p>"
                  "<p>The eight strategies form one declared family. That is why the multiple-testing gate is procedural rather than optional: "
                  "testing eight variants and reporting the best one is the classic way to manufacture a winner.</p></div>")
    )
    pages["strategies.html"] = shell("strategies.html", "Strategies",
                                     "Single bets, parlays and player-prop combos - and exactly which gate stops each one.",
                                     strategies_body, "STRATEGY REGISTER")

    # ------------------------------------------------------------- validation
    gate_rows = [{
        "id": g["id"], "name": f'<span class="row-title">{esc(g["name"])}</span><span class="row-sub">{esc(g["id"])}</span>',
        "requirement": g["requirement"], "evidence": g["evidence_today"], "status": badge(g["status"]),
        "source_ids": g["source_ids"],
    } for g in data["gates"]]
    passed = sum(1 for g in data["gates"] if g["status"] in ("Pass", "Procedural"))
    validation_body = (
        notice("Fail-closed by design: an unproven strategy is blocked, not ranked. Today one gate is procedural and the rest fail or only partly pass.",
               "info", ("What would change this", "suggestions.html"))
        + metric_grid([
            ("Gates defined", str(len(data["gates"])), "all ten published with their evidence"),
            ("Not failing", str(passed), "one procedural, the rest fail"),
            ("Failing", str(sum(1 for g in data["gates"] if g["status"] == "Fail")), "mostly for the same missing input"),
            ("Waivers", "0", "no gate can be waived"),
        ])
        + section("The ten gates", table("gates", "Validation gates", [
            ("Gate", "name"), ("Requirement", "requirement"), ("Evidence today", "evidence"), ("Status", "status"),
        ], gate_rows, note="A gate passes only on evidence that exists in this repository today. Nothing is marked complete on the expectation that it soon will be."))
        + section("Skill versus luck", '<div class="panel body-text">'
                  "<p>Three things separate skill from luck here, and none of them can be shortcut:</p>"
                  "<ul><li><strong>A baseline.</strong> The control model, not the market, is the first hurdle.</li>"
                  "<li><strong>A pre-registered test.</strong> The family of eight is declared before any result exists, and Holm adjustment is applied to the whole family.</li>"
                  "<li><strong>An interval, not a point.</strong> A bootstrap interval on both the score and the return, with the sample size published next to it.</li></ul>"
                  "<p>With 14 upcoming games there is nothing to test yet. Any claim of skill today would be a claim about a coin.</p></div>")
    )
    pages["validation.html"] = shell("validation.html", "Validation gates",
                                     "Ten conditions a strategy must satisfy before it can be ranked, and the evidence for each one today.",
                                     validation_body, "VALIDATION")

    # ------------------------------------------------------------ correlation
    corr_rows = [{
        "id": c["id"], "x": c["x"], "y": c["y"], "n": c["n"], "pearson": c["pearson"], "spearman": c["spearman"],
        "ci": f'{c["ci_low"]} to {c["ci_high"]}', "note": c["note"], "source_ids": c["source_ids"],
    } for c in model["correlations"]]
    leg_rows = [{
        "id": leg["id"], "legs": leg["legs"], "r": leg["r"], "n": leg["n"], "status": badge(leg["status"]),
        "source_ids": leg["source_ids"],
    } for leg in data["correlation_method"]["prospective_legs"]]
    correlation_body = (
        notice("These are team-season correlations across 32 clubs. They are not correlations between two bet legs and must never be used to price a parlay.",
               "warning", ("Why the leg cells are blank", "questions.html"))
        + section("Computed today", table("correlations", "Team-level correlations (n = 32 clubs)", [
            ("Measure", "x"), ("Against", "y"), ("n", "n"), ("Pearson r", "pearson"), ("Spearman rho", "spearman"),
            ("Fisher 95% interval", "ci"), ("Reading", "note"),
        ], corr_rows, note="Computed from the 32 official standings rows with a dependency-free implementation of the Pearson and Spearman definitions; the interval is a Fisher z interval and assumes independent pairs, which team rows are not."))
        + section("Leg-level correlations (blank until measured)", table("legs", "Leg-level correlations", [
            ("Legs", "legs"), ("r", "r"), ("n", "n"), ("Status", "status"),
        ], leg_rows, note="A blank correlation is a withheld value, not a zero. Assuming zero for same-game legs is the specific error gate G9 exists to catch."))
        + section("What would make a leg correlation publishable", '<div class="panel body-text">'
                  "<p>One row per settled game containing the final margin, the final total and the result of each leg. From that, a joint rate and a correlation with an interval. "
                  "A minimum of 100 joint observations is proposed before any value is shown.</p>"
                  "<p>Nothing in this repository currently produces that dataset, which is why the cells above are empty.</p></div>")
    )
    pages["correlation.html"] = shell("correlation.html", "Correlations",
                                      "What co-moves with what - measured where possible, blank where not.",
                                      correlation_body, "CORRELATION")

    # ------------------------------------------------------------- leaderboard
    lb = data["leaderboard"]
    leaderboard_body = (
        notice("The competition is defined and closed. No entry exists, because an entry requires a strategy that has passed every gate.", "warning",
               ("Validation gates", "validation.html"))
        + '<div class="panel empty-state"><div class="empty-icon" aria-hidden="true">&#9878;</div><h3>No qualified entries</h3>'
          "<p>Ranking a blocked strategy would produce a leader from noise. This stays empty until at least one strategy passes all ten gates "
          "on a sample of at least 100 settled observations.</p></div>"
        + section("Rules", table("lb-rules", "Competition rules", [
            ("Rule", "rule"), ("Definition", "definition"),
        ], [
            {"id": "L-1", "rule": "Qualifying score", "definition": lb["scoring"], "source_ids": ["SK-CAL"]},
            {"id": "L-2", "rule": "Ranking", "definition": lb["ranking_rule"], "source_ids": ["SM-HOLM"]},
            {"id": "L-3", "rule": "Reward", "definition": lb["reward_rule"], "source_ids": ["NFL-TERMS"]},
            {"id": "L-4", "rule": "Why empty", "definition": lb["why_empty"], "source_ids": ["NFL-ODDS-PATH"]},
        ], note="Rules are fixed before results exist. Changing them afterwards would invalidate every comparison."))
        + section("Standings", table("lb-entries", "Leaderboard entries", [
            ("Rank", "rank"), ("Strategy", "strategy"), ("Brier skill", "skill"), ("Settled bets", "n"), ("Status", "status"),
        ], [], note="Intentionally empty: there are no qualified entries to rank."))
    )
    pages["leaderboard.html"] = shell("leaderboard.html", "Leaderboard",
                                      "A competition with published rules, a control model to beat, and no entries yet.",
                                      leaderboard_body, "COMPETITION")

    # ------------------------------------------------------------- suggestions
    suggestion_cards = []
    for s in content["suggestions"]:
        options = "".join(
            f'<li><strong>{esc(o["key"])}. {esc(o["label"])}</strong> - {esc(o["detail"])}</li>' for o in s["options"]
        )
        suggestion_cards.append(
            f'<div class="panel body-text" id="{esc(s["id"].lower())}"><h3>{esc(s["id"])} &middot; {esc(s["title"])}</h3>'
            f'<p><strong>Problem.</strong> {esc(s["problem"])}</p><p><strong>Options.</strong></p><ul>{options}</ul>'
            f'<p><strong>Recommendation.</strong> {esc(s["recommendation"])}</p>'
            f'<p><small>Effort: {esc(s["effort"])} &middot; Impact: {esc(s["impact"])} &middot; Risk: {esc(s["risk"])}</small></p>'
            f'<p>{badge(s["decision"])} &nbsp; {refs(s["source_ids"], SOURCE_URLS)}</p></div>'
        )
    suggestions_body = (
        notice("Twelve suggestions, each with options and a recommendation, and none implemented. Pick a path here before any of it is built.",
               "info", ("Open questions behind them", "questions.html"))
        + section("Decision table", table("suggestions", "Suggestions for review", [
            ("ID", "id"), ("Suggestion", "title"), ("Recommended path", "recommendation"),
            ("Effort", "effort"), ("Impact", "impact"), ("Decision", lambda r: badge(r["decision"])),
        ], content["suggestions"], note="Every row links to an official source for the constraint that makes the suggestion necessary. The detail cards below repeat each row in full so a choice can be made without a second page."))
        + section("Detail", "".join(suggestion_cards))
    )
    pages["suggestions.html"] = shell("suggestions.html", "Suggestions",
                                      "Options, recommendations and a decision slot for each proposed change - so a path can be chosen before anything is implemented.",
                                      suggestions_body, "DECISION SUPPORT")

    # --------------------------------------------------------------- questions
    question_body = (
        notice("Every decision below is blocked by something specific. This page states what we have, what we do not, and where the missing item would come from.",
               "info", ("Suggestions that address them", "suggestions.html"))
        + section("Register", table("questions", "Questions, information and answers", [
            ("ID", "id"), ("Question", "question"), ("Why it blocks a decision", "why"),
            ("What we have (verified)", "have"), ("Missing", "missing"), ("How to obtain", "discovery"),
            ("Status", "status"),
        ], content["questions"], filter_options=["Answered", "Answered in part", "Partially answered (3 of 28 clubs)",
                                                 "Partially answered (187 of 208 rows)", "Proposed - needs a decision",
                                                 "Open - blocking", "Open - blocked", "Open - process gap", "Open - design gap",
                                                 "Open - unverified reason", "Open - needs a decision"],
            note="'Have' means verified against an official source with a check date. 'Missing' is never filled in from memory or inferred from a neighbouring value."))
    )
    pages["questions.html"] = shell("questions.html", "Open questions",
                                    "What must be answered, by whom, and from which official source, before any decision here is reasonable.",
                                    question_body, "INFORMATION GAPS")

    # ----------------------------------------------------------------- sources
    source_rows = [{
        "id": s["id"], "publisher": s["publisher"], "title": s["title"],
        "url": f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["url"])}</a>',
        "checked": s["checked_on"], "scope": s["scope"], "access": s["access"], "source_ids": [s["id"]],
    } for s in data["sources"]]
    sources_body = (
        notice("A link is a reference for manual review, not a blanket certification. Each row states what was actually read and when.", "info")
        + section("Source register", table("sources", "Official source register", [
            ("ID", "id"), ("Publisher", "publisher"), ("Title", "title"), ("URL", "url"),
            ("Checked", "checked"), ("Scope verified", "scope"), ("Access boundary", "access"),
        ], source_rows, note="Two registered rows document a 404 (the league odds path and the league depth-chart path). They are recorded as scope limits, not as evidence of absence everywhere."))
        + section("Local data files", '<div class="download-list">'
                  '<a class="button" href="data/standings-2026.csv">standings-2026.csv</a>'
                  '<a class="button" href="data/games-2026-w10.csv">games-2026-w10.csv</a>'
                  '<a class="button" href="data/injuries-2026-w10.csv">injuries-2026-w10.csv</a>'
                  '<a class="button" href="data/depth-2026-w10.csv">depth-2026-w10.csv</a>'
                  '<a class="button" href="data.json">data.json</a>'
                  '<a class="button" href="content.json">content.json</a></div>'
                  '<p class="table-note">Every CSV row carries the source IDs used on the page. The build is deterministic and hash-checked in CI.</p>')
    )
    pages["sources.html"] = shell("sources.html", "Sources",
                                  "Every source used, what was read, and when - including the two paths that returned 404.",
                                  sources_body, "SOURCE REGISTER")

    # ----------------------------------------------------------------- flagged
    flagged_body = (
        notice("Flagged for Review: values that could not be confirmed from an official source are blank and listed here. Nothing is inferred, and nothing here blocks publication.",
               "warning", ("Open questions", "questions.html"))
        + section("Flagged items", table("flags", "Flagged for review", [
            ("ID", "id"), ("Item", "item"), ("Detail", "detail"), ("Status", lambda r: badge(r["status"])),
        ], content["flags"], note="Each flag links to the official source that establishes the limit. Where the limit is an absence, the row says what was checked rather than asserting that nothing exists."))
    )
    pages["flagged.html"] = shell("flagged.html", "Flagged for review",
                                  "Unverified, partial and blocked items - published rather than filled in.",
                                  flagged_body, "LIMITATIONS")

    # ------------------------------------------------------------- repo review
    repo_body = (
        notice("Fifteen checks on this repository, run before and after the NFL work. Two produced real catches: a stale README and a position-label mismatch between a club chart and the injury report.",
               "info", ("Coordination board", "../COORDINATION.md"))
        + section("Repository checks", table("repo", "Repository review", [
            ("ID", "id"), ("Check", "check"), ("Finding", "finding"), ("Severity", "severity"), ("Action taken", "action"),
        ], content["repo_review"], note="This is a review of repository consistency and source discipline. It is not a re-verification of the inherited NBA or rental claims."))
        + section("Method", '<div class="panel body-text">'
                  "<p>The existing generator enforces a strict contract: every HTML page must be registered with a hash, every table body row must carry registered source IDs plus a link, "
                  "and every blank cell must be genuinely empty. The NFL pages are built to the same contract, so a violation fails the whole site check.</p>"
                  "<p>The NFL data files were checked by arithmetic where arithmetic exists: win percentage, net points, the league-wide points identity, "
                  "and the count of clubs in the slate against the count in the standings.</p></div>")
    )
    pages["repo-review.html"] = shell("repo-review.html", "Repository review",
                                      "Line-by-line checks on the repository, with irregularities recorded rather than tidied away.",
                                      repo_body, "AUDIT")
    return pages


def club_summary(injuries, by_code):
    out = []
    for code in sorted({r["club"] for r in injuries}):
        rows = [r for r in injuries if r["club"] == code]
        out.append({
            "id": code, "club": code, "name": by_code.get(code, {}).get("name", ""), "rows": len(rows),
            "dnp": sum(1 for r in rows if r["practice"] == "DNP"),
            "limited": sum(1 for r in rows if r["practice"] == "Limited"),
            "full": sum(1 for r in rows if r["practice"] == "Full"),
            "out": sum(1 for r in rows if r["designation"] == "Out"),
            "source_ids": sorted({s for r in rows for s in r["sources"].split()}),
        })
    return out


def coverage(injuries, depth, by_code):
    slate = {t for game in load_games() for t in (game["away"], game["home"])}
    out = []
    for code in sorted(by_code):
        rows = [r for r in injuries if r["club"] == code]
        drows = [r for r in depth if r["club"] == code]
        out.append({
            "id": code, "club": f'{esc(by_code[code]["name"])} ({esc(code)})',
            "slate": "Yes" if code in slate else "No",
            "injuries": len(rows),
            "depth": "Yes" if drows else "No",
            "gaps": sum(1 for r in drows if "listed" in r["deficiency"]),
            "source_ids": sorted({s for r in rows for s in r["sources"].split()} | ({"NFL-STANDINGS"})),
        })
    return out


def build() -> dict:
    global PROJECT, SOURCE_URLS, SOURCE_META
    data = load_json(DATA)
    PROJECT = data["project"]
    SOURCE_URLS = {s["id"]: s["url"] for s in data["sources"]}
    SOURCE_META = {s["id"]: s for s in data["sources"]}
    pages = render()
    for name, markup in pages.items():
        (ROOT / name).write_text(markup, encoding="utf-8")
    MANIFEST.write_text(json.dumps({"pages": PAGES, "checked_on": PROJECT["checked_on"]}, indent=2) + "\n",
                        encoding="utf-8")
    return pages


def check() -> None:
    data = load_json(DATA)
    global PROJECT, SOURCE_URLS, SOURCE_META
    PROJECT = data["project"]
    SOURCE_URLS = {s["id"]: s["url"] for s in data["sources"]}
    SOURCE_META = {s["id"]: s for s in data["sources"]}
    pages = render()
    stale = [n for n, markup in pages.items()
             if not (ROOT / n).is_file() or (ROOT / n).read_text(encoding="utf-8") != markup]
    if stale:
        raise SystemExit("STALE NFL pages (rerun python nfl/build.py): " + ", ".join(stale))
    print(f"OK: {len(pages)} NFL pages match the deterministic build.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify committed pages match the build")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        built = build()
        print(f"Built {len(built)} NFL pages: " + ", ".join(sorted(built)))
