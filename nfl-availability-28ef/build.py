#!/usr/bin/env python3
"""Deterministic generator for the NFL availability & depletion desk.

Every table row carries data-source-ids and a link to the official page it came from. Unknown
values are printed as an empty cell with data-empty, never filled in. No market price, no
performance deficit, no probability and no wager recommendation is produced anywhere.
"""
from __future__ import annotations

import csv
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "nfl-availability-28ef"
SITE = HERE / "site"
DATA = HERE / "data"
sys.path.insert(0, str(HERE))

CHECKED = "2026-11-13"
PAGES = [
    ("index.html", "Overview"),
    ("summary.html", "Executive summary"),
    ("availability.html", "Injury ledger"),
    ("depth.html", "Printed depth chains"),
    ("depletion.html", "Starter depletion"),
    ("clubs.html", "Club summary"),
    ("questions.html", "Questions & answers"),
    ("suggestions.html", "Suggestions for review"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Source register"),
]


# --------------------------------------------------------------------------- helpers
def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def load_csv(name):
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def registry():
    return {s["id"]: s for s in json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))}


REG = registry()


def _normalise(url):
    text = (url or "").strip().rstrip("/").lower()
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text.replace("www.", "", 1)


# Map a page URL to the registry id that already covers it, so a chart read in an earlier session
# keeps pointing at the source that was actually read rather than at a newly minted id.
BY_URL = {}
for _s in REG.values():
    BY_URL.setdefault(_normalise(_s["url"]), _s["id"])


def source_id_for(url, club_abbr):
    return BY_URL.get(_normalise(url), f"X28-{club_abbr}-DEPTH")


def source_links(ids):
    return " ".join(
        f'<a href="{esc(REG[i]["url"])}" target="_blank" rel="noopener noreferrer">{esc(i)}</a>'
        for i in ids if i in REG
    )


def blank():
    return '<td data-empty="true"></td>'


def cell(value, cls=None):
    if value is None or str(value).strip() == "":
        return blank()
    attr = f' class="{esc(cls)}"' if cls else ""
    return f"<td{attr}>{esc(value)}</td>"


def row(cells, ids, attrs=""):
    ids = [i for i in ids if i in REG]
    return (f'<tr data-source-ids="{esc(" ".join(ids))}"{attrs}>' + "".join(cells)
            + f'<td class="src">{source_links(ids)}</td></tr>')


def table(table_id, caption, headers, rows, *, note=None, filters=None, extra_class=""):
    controls = ""
    if filters is not None:
        controls += (f'<div class="controls"><label>Search <input type="search" '
                     f'data-search="{table_id}" placeholder="Filter rows…"></label>')
        for key, label, options in filters:
            controls += (f'<label>{esc(label)} <select data-filter="{table_id}" '
                         f'data-filter-key="{esc(key)}"><option value="">All</option>'
                         + "".join(f'<option value="{esc(o)}">{esc(o)}</option>' for o in options)
                         + "</select></label>")
        controls += (f'<button type="button" data-export="{table_id}">Export visible CSV</button>'
                     f'<span class="count" data-count="{table_id}"></span></div>')
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers) + '<th scope="col">Official source</th>'
    note_html = f'<p class="note">{note}</p>' if note else ""
    return (
        f'{controls}{note_html}<div class="table-wrap" tabindex="0" role="region" '
        f'aria-label="{esc(caption)}"><table id="{table_id}" class="{esc(extra_class)}">'
        f'<caption>{esc(caption)}</caption><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
        f'<p class="empty-state" data-empty-for="{table_id}" hidden>No rows match the current filters.</p>'
    )


def kpis(items):
    out = '<div class="kpis">'
    for value, label in items:
        out += f'<div class="kpi"><span class="kpi-value">{esc(value)}</span><span class="kpi-label">{esc(label)}</span></div>'
    return out + "</div>"


def cards(items):
    return ('<div class="cards">'
            + "".join(f'<a class="card" href="{esc(href)}"><h2>{esc(title)}</h2><p>{esc(text)}</p></a>'
                      for href, title, text in items)
            + "</div>")


def panel(title, body, source_ids=()):
    refs = f'<p class="src-line">{source_links(source_ids)}</p>' if source_ids else ""
    return f'<section class="panel"><h2>{esc(title)}</h2>{body}{refs}</section>'


def layout(slug, title, body, subtitle=""):
    nav = "".join(
        f'<a href="{esc(name)}"' + (' aria-current="page"' if name == slug else "") + f">{esc(label)}</a>"
        for name, label in PAGES
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · NFL availability desk</title><link rel="stylesheet" href="style.css"></head>
<body><a class="skip" href="#main">Skip to content</a><header class="top"><div class="brand"><strong>OWN7</strong><span>NFL availability &amp; depletion desk</span></div><nav aria-label="Desk sections">{nav}</nav></header>
<main id="main"><p class="eyebrow">Bounded snapshot · read {esc(CHECKED)} · informational only · no wagers</p><h1>{esc(title)}</h1>{f'<p class="subtitle">{esc(subtitle)}</p>' if subtitle else ''}{body}</main>
<footer><p>Unknown values stay blank; nothing is inferred. <a href="../../index.html">Canonical dashboard</a> · <a href="../../nfl-injuries.html">NFL injuries &amp; availability</a> · <a href="../../nfl/origination/depth.html">Origination depth page</a> · <a href="../../nfl-assurance-9580ac3f/site/depth.html">Assurance depth chains</a> · <a href="sources.html">Sources</a> · <a href="flagged.html">Flagged for review</a></p></footer>
<script src="app.js"></script></body></html>'''


# --------------------------------------------------------------------------- content
def overview():
    capture = load_json("capture-summary.json")
    depth = load_json("depth-summary.json")
    depl = load_json("depletion-summary.json")
    body = kpis([
        (capture["injury_rows"], "player rows on the official Week 10 injury report"),
        (capture["clubs_listed"], "clubs listed on the report (14 games, 4 byes)"),
        (depth["clubs"], "clubs with a printed depth chart obtained"),
        (depth["slots"], "printed depth slots transcribed"),
        (depl["starters_ruled_out"], "printed starters ruled out"),
        (depl["starters_questionable"], "printed starters questionable"),
        (depl["second_string_in_line_for_out_starter"], "second strings next in line for an out starter"),
        (depl["no_name_printed_behind_out_starter"], "out starters with no further name printed"),
    ])
    body += panel("What this desk answers",
                  "<p>When the league lists a player as Out, Doubtful or Questionable, what does the "
                  "club's own printed chart say about who is behind him? That is the whole question. "
                  "The answer is published per player, with the printed chain, the next name in line "
                  "and the source of both.</p>"
                  "<p>It deliberately does <strong>not</strong> produce a point value, a win "
                  "probability, a price or a bet. No performance deficit is estimated, because no "
                  "official source publishes one and inventing one would be fabrication.</p>")
    body += cards([
        ("availability.html", "Injury ledger",
         f"{capture['injury_rows']} rows read from nfl.com on {CHECKED}: practice status, game status "
         f"and listed injury for every player on every Week 10 game."),
        ("depth.html", "Printed depth chains",
         f"{depth['slots']} printed slots across {depth['clubs']} clubs, in the order each club prints "
         f"them. First name listed is the printed starter."),
        ("depletion.html", "Starter depletion",
         "The join: who is out, what rank the printed chart gives him, and the next name printed "
         "behind him."),
        ("clubs.html", "Club summary",
         "One row per club: chart availability, chart date, out / questionable / blank counts, and "
         "how many of them are printed starters."),
        ("questions.html", "Questions & answers",
         "What we know with a source, what is still missing, and what would close each gap."),
        ("suggestions.html", "Suggestions for review",
         "Ranked proposals with evidence, acceptance tests and a choose-a-path control. Nothing is "
         "implemented until a path is chosen."),
        ("flagged.html", "Flagged for review",
         "Every irregularity found while reading the sources, with the official link for each."),
        ("summary.html", "Executive summary",
         "The five findings that matter and the four gaps that still block a decision."),
    ])
    body += panel("How to read a blank",
                  "<p>An empty cell marked with a pale background is a value an official source did "
                  "not publish. It is not a zero, not a guess and not a pending calculation. On the "
                  "league injury report, 301 of 326 rows carry no game status at all - that blank is "
                  "the finding, not an omission.</p>",
                  ("X28-NFL-INJ-W10",))
    return body


def summary_page():
    depl = load_json("depletion-summary.json")
    capture = load_json("capture-summary.json")
    depth = load_json("depth-summary.json")
    rows = load_csv("depletion-week10-2026.csv")
    affected = [r for r in rows if r["game_status"] in ("Out", "Questionable") and r["depth_rank"]]
    body = '<p class="lead">Read on 2026-11-13. Everything below is either printed by an official ' \
           'source or left blank.</p>'
    body += panel("Five findings",
                  "<ol>"
                  "<li>The official injury report lists <strong>326 players</strong> across 28 clubs "
                  "for Week 10. Only <strong>25 rows carry a game status</strong> (14 Out, 11 "
                  "Questionable). The other 301 are blank on the page itself.</li>"
                  "<li><strong>10 printed starters</strong> carry a game status: 7 ruled out, 3 "
                  "questionable. Four of the seven are defenders, two are offensive players and one "
                  "is a long snapper.</li>"
                  "<li>In <strong>six of seven</strong> cases the printed chart names a second string "
                  "as the next man in. In one case - the Colts long snapper - the chart prints no "
                  "further name at all.</li>"
                  "<li>One chain is already two deep: New England's printed starting running back is "
                  "questionable and the printed second string is out, which leaves the "
                  "<strong>third</strong> string as the next available name.</li>"
                  "<li>Twenty-seven of the 28 clubs playing this week have a printed chart. "
                  "Houston's page returned no chart, so its 16 injury rows have no rank and no "
                  "replacement - they are published blank.</li>"
                  "</ol>",
                  ("X28-NFL-INJ-W10", "A958-NE-DEPTH", "X28-IND-DEPTH", "X28-HOU-DEPTH"))
    body += panel("Four gaps that block a decision",
                  "<ol>"
                  "<li><strong>Game status is published for 5 clubs only.</strong> Until a club or "
                  "the league publishes Friday statuses for the rest, no depletion count can be "
                  "league-wide.</li>"
                  "<li><strong>Club charts are 'unofficial'.</strong> Several publishers say so on "
                  "the page. They are printed opinions, not confirmed game-day personnel.</li>"
                  "<li><strong>No market price exists in the record.</strong> So no depletion finding "
                  "can be turned into an edge, a stake or a reward yet.</li>"
                  "<li><strong>No results and no inactives.</strong> The only list that decides who "
                  "plays is the official inactives list issued shortly before kickoff; it has not "
                  "been read.</li>"
                  "</ol>",
                  ("X28-NFL-INJ-W10", "X28-KC-DEPTH", "X28-DAL-DEPTH"))
    body += table(
        "tbl-summary", "Players with a game status who appear on their club's printed chart",
        ["Club", "Player", "Position", "Status", "Printed rank", "Next name printed in line",
         "Also out behind him", "Classification"],
        [row([
            cell(r["club_abbr"]), cell(r["player"]), cell(r["position_reported"]),
            cell(r["game_status"], "status-" + r["game_status"].lower()),
            cell(r["depth_rank_label"]), cell(r["next_in_line"] or "no further name printed"),
            cell(r["backups_also_out"]), cell(r["classification"]),
        ], ["X28-NFL-INJ-W10", source_id_for(r["depth_source_url"], r["club_abbr"])])
            for r in sorted(affected, key=lambda r: (r["club_abbr"], int(r["depth_rank"] or 99)))],
        note="Sorted by club. 'Next name printed in line' skips anyone the league report lists as Out.",
        filters=[("club", "Club", sorted({r["club_abbr"] for r in affected})),
                 ("status", "Status", sorted({r["game_status"] for r in affected}))])
    body += panel("Counts",
                  f'<p>{capture["injury_rows"]} injury rows · {depth["slots"]} printed slots · '
                  f'{depl["matched_to_chart"]} injury rows matched to a printed chart · '
                  f'{depl["matched_but_unnamed"]} not named on the chart · '
                  f'{depl["no_chart"]} rows with no chart at all.</p>',
                  ("X28-NFL-INJ-W10",))
    return body


def availability_page():
    rows = load_csv("injuries-week10-2026.csv")
    games = load_csv("games-week10-2026.csv")
    body = ('<p class="lead">Every player the league listed for Week 10, read from '
            '<a href="https://www.nfl.com/injuries/league/2026/REG10" target="_blank" '
            'rel="noopener noreferrer">nfl.com/injuries/league/2026/REG10</a> on 2026-11-13 (all '
            'eight rendered chunks saved under <code>evidence/</code>).</p>')
    body += kpis([
        (len(rows), "rows"), (len({r["club_abbr"] for r in rows}), "clubs"),
        (sum(1 for r in rows if r["game_status"] == "Out"), "ruled out"),
        (sum(1 for r in rows if r["game_status"] == "Questionable"), "questionable"),
        (sum(1 for r in rows if r["game_status"] == ""), "no game status published"),
    ])
    body += table(
        "tbl-injuries", "Official Week 10 injury report",
        ["ID", "Club", "Opponent", "Player", "Pos", "Injury listed", "Practice status", "Game status"],
        [row([
            cell(r["injury_id"]), cell(r["club_abbr"]), cell(r["opponent_abbr"]), cell(r["player"]),
            cell(r["position"]), cell(r["injury"]), cell(r["practice_status"]),
            cell(r["game_status"], "status-" + r["game_status"].lower() if r["game_status"] else None),
        ], ["X28-NFL-INJ-W10"], attrs=f' data-club="{esc(r["club_abbr"])}"') for r in rows],
        note="A blank game status means the page published nothing for that player. It is not read as "
             "available, and it is not read as unavailable.",
        filters=[("club", "Club", sorted({r["club_abbr"] for r in rows})),
                 ("status", "Game status", ["Out", "Questionable", "Doubtful", "none published"]),
                 ("practice", "Practice", ["Did Not Participate In Practice",
                                           "Limited Participation in Practice",
                                           "Full Participation in Practice"])])
    body += table(
        "tbl-games", "Week 10 fixtures as printed on the injury report",
        ["ID", "Day", "Kickoff (ET)", "TV", "Away", "Home"],
        [row([cell(g["game_id"]), cell(g["day"]), cell(g["kickoff_et"]), cell(g["tv"]),
              cell(g["away_abbr"]), cell(g["home_abbr"])], ["X28-NFL-INJ-W10"]) for g in games],
        note="Four clubs are on byes and therefore absent from the report: the clubs not listed in "
             "any row above.")
    return body


def depth_page():
    slots = load_csv("depth-slots-week10-2026.csv")
    summary = load_json("depth-summary.json")
    body = ('<p class="lead">The printed order on each club\'s own depth-chart page, transcribed '
            'exactly. Rank 1 is the first name the club prints. Where a club printed two names in a '
            'single cell, both are shown and the cell is marked - the club does not publish an order '
            'inside that cell, so none is invented.</p>')
    body += kpis([
        (summary["slots"], "printed slots"), (summary["clubs"], "clubs"),
        (summary["multi_name_cells"], "cells printed with two names"),
        (summary["blank_slots"], "blank printed cells kept blank"),
        (len(summary["failures"]), "clubs whose chart did not render"),
    ])
    body += table(
        "tbl-depth", "Printed depth chains, all clubs obtained",
        ["Club", "Unit", "Position", "Rank", "Player", "Note", "Chart read on"],
        [row([
            cell(s["club_abbr"]), cell(s["unit"]), cell(s["position"]), cell(s["rank"]),
            cell(s["player"]),
            cell((s["note"] or "") + (" · two names printed in one cell"
                                      if s["cell_holds_multiple"] == "yes" else "")),
            cell(s["checked_on"]),
        ], [source_id_for(s["source_url"], s["club_abbr"])],
            attrs=f' data-club="{esc(s["club_abbr"])}"')
            for s in slots],
        note="Trailing empty columns on a club's chart are dropped; a blank the club printed before a "
             "named player is kept and labelled in the note column.",
        filters=[("club", "Club", sorted({s["club_abbr"] for s in slots})),
                 ("unit", "Unit", ["Offense", "Defense", "Special Teams"])])
    body += panel("Pages that returned no chart",
                  "".join(f'<p><strong>{esc(f["club_abbr"])}</strong> — {esc(f["reason"])} on '
                          f'{esc(f["read_on"])}: <a href="{esc(f["url"])}" target="_blank" '
                          f'rel="noopener noreferrer">{esc(f["url"])}</a>. Nothing was substituted '
                          f'from another source.</p>' for f in summary["failures"]),
                  tuple(f'X28-{f["club_abbr"]}-DEPTH' for f in summary["failures"]))
    return body


def depletion_page():
    rows = load_csv("depletion-week10-2026.csv")
    key = [r for r in rows if r["game_status"] in ("Out", "Questionable", "Doubtful")]
    body = ('<p class="lead">The join. Left side: the league injury report. Right side: the club\'s '
            'printed chart. The classification column states only what the two official sources '
            'print. No points, no probabilities, no recommendations.</p>')
    body += table(
        "tbl-depletion-key", "Players with a published game status",
        ["Club", "Player", "Pos", "Status", "Unit", "Chart position", "Printed rank",
         "Printed chain", "Next in line", "Also out behind him", "Classification"],
        [row([
            cell(r["club_abbr"]), cell(r["player"]), cell(r["position_reported"]),
            cell(r["game_status"], "status-" + r["game_status"].lower()),
            cell(r["unit"]), cell(r["position_on_chart"]), cell(r["depth_rank_label"]),
            cell(r["printed_chain"]), cell(r["next_in_line"] or "no further name printed"),
            cell(r["backups_also_out"]), cell(r["classification"]),
        ], ["X28-NFL-INJ-W10", source_id_for(r["depth_source_url"], r["club_abbr"])],
            attrs=f' data-club="{esc(r["club_abbr"])}" data-status="{esc(r["game_status"])}"')
            for r in sorted(key, key=lambda r: (r["club_abbr"], r["player"]))],
        note="'Next in line' skips any player the league lists as Out. Where the chain runs out, the "
             "cell says so instead of guessing.",
        filters=[("club", "Club", sorted({r["club_abbr"] for r in key})),
                 ("status", "Status", sorted({r["game_status"] for r in key}))])
    body += table(
        "tbl-depletion-all", "Every injury row, with its chart match",
        ["Club", "Player", "Pos", "Practice", "Status", "Chart", "Rank", "Replacement",
         "Classification"],
        [row([
            cell(r["club_abbr"]), cell(r["player"]), cell(r["position_reported"]),
            cell(r["practice_status"]), cell(r["game_status"]), cell(r["chart_available"]),
            cell(r["depth_rank_label"]), cell(r["next_in_line"]), cell(r["classification"]),
        ], ["X28-NFL-INJ-W10"]
            + ([source_id_for(r["depth_source_url"], r["club_abbr"])]
               if r["chart_available"] == "yes" else []),
            attrs=f' data-club="{esc(r["club_abbr"])}"') for r in rows],
        note=f"{len(rows)} rows. Rows for clubs with no chart, and rows for players a club does not "
             f"print, keep the rank and replacement blank.",
        filters=[("club", "Club", sorted({r["club_abbr"] for r in rows}))])
    return body


def clubs_page():
    rows = load_csv("club-summary-week10-2026.csv")
    body = ('<p class="lead">One row per club on the Week 10 report. The four bye clubs are absent '
            'from the injury report and therefore have no row here.</p>')
    body += table(
        "tbl-clubs", "Club summary",
        ["Club", "Chart?", "Chart read on", "Injury rows", "Out", "Questionable", "Doubtful",
         "No status published", "Starters out", "Defence out", "Offence out", "ST out",
         "Named on chart?"],
        [row([
            cell(r["club_abbr"]), cell(r["chart_available"]), cell(r["chart_checked_on"]),
            cell(r["injury_rows"]), cell(r["ruled_out"]), cell(r["questionable"]),
            cell(r["doubtful"]), cell(r["blank_game_status"]), cell(r["starters_ruled_out"]),
            cell(r["defence_ruled_out"]), cell(r["offence_ruled_out"]),
            cell(r["special_teams_ruled_out"]), cell(r["not_named_on_chart"]),
        ], ["X28-NFL-INJ-W10"]
            + ([source_id_for(r["chart_source_url"], r["club_abbr"])]
               if r["chart_available"] == "yes" else []),
            attrs=f' data-club="{esc(r["club_abbr"])}"') for r in rows],
        note="'Named on chart?' counts injury-listed players this club does not print on its chart. "
             "Those rows keep rank and replacement blank.")
    return body


QUESTIONS = [
    ("XQ01", "Which clubs are actually starting backups this week?",
     "Seven printed starters are ruled out and three are questionable, across five clubs. Six have "
     "a second string printed behind them; one prints no further name.",
     "The league page publishes a game status for only 5 of the 28 clubs on it, so 23 clubs cannot "
     "be assessed at all from this source.",
     "Read each club's own Friday game-status report, or the official inactives list before kickoff.",
     "Any league-wide availability claim"),
    ("XQ02", "Does a blank game status on the league page mean the player is available?",
     "No. The page publishes nothing for 301 of 326 rows and does not define the blank. The league's "
     "own policy defines only Out, Doubtful and Questionable.",
     "An official statement of what a blank means.",
     "A league policy page or the club's own report covering the same player.",
     "Treating a blank as available anywhere in a model"),
    ("XQ03", "Are these depth charts official?",
     "They are published by the clubs on their own official domains - and most are labelled "
     "'unofficial' by the publisher. Kansas City, Dallas and the Los Angeles Rams say so on the page.",
     "Any league-published starter designation. None was found.",
     "A league source that designates starters, or an explicit decision to treat club charts as "
     "opinion.",
     "Any claim that rank 1 is the confirmed game-day starter"),
    ("XQ04", "How much is a backup worth in points?",
     "Nothing. No official source publishes a replacement value, and no market price was retrieved, "
     "so no number is produced here.",
     "A price series and a results series, both licensed or otherwise lawful to use.",
     "Recording market prices and final scores for the same games over enough weeks to estimate "
     "anything.",
     "Every economic claim: edge, ROI, CLV, stake, reward"),
    ("XQ05", "Why does Houston have no chain?",
     "The Texans' depth-chart page returned its heading but no table to the reader on 2026-11-13.",
     "A working read of that page, or another official Texans publication of the same information.",
     "Retrying the page, or reading the club's weekly game release.",
     "Any availability statement about the 16 Texans injury rows"),
    ("XQ06", "Can a player on the injury report be matched to a chart reliably?",
     "270 of 326 rows matched on a normalised name within the same club. Six of the players who "
     "carry a game status are not printed on their club's chart at all.",
     "A stable shared player identifier: the league page links to nfl.com player URLs and the clubs "
     "link to their own roster URLs, and the two are not reconciled.",
     "Storing both URLs per player and joining on the identifier rather than on spelling.",
     "Automated scaling of this join"),
    ("XQ07", "Is the information current?",
     "The injury report is a 2026-11-13 read. Seventeen club charts are 2026-11-13 reads; ten are "
     "2026-11-12 reads already in this repository and reused as such.",
     "Same-day reads of the ten clubs whose charts are one day older.",
     "Re-reading those ten pages, or accepting and publishing the date difference as is done here.",
     "Any statement that one snapshot describes a single moment"),
    ("XQ08", "What would let a strategy qualify at all?",
     "Nothing here qualifies. A depletion signal needs a price to beat and a result to score against; "
     "neither is in the record.",
     "A licensed or otherwise lawful price source, plus recorded results for the same games.",
     "Obtaining both and re-running the gates before any 'skill' language is used.",
     "Leaderboard entries, rewards and any skill claim"),
]


def questions_page():
    body = ('<p class="lead">Each question is split into the part answered by an official source, '
            'the part still missing, and what would close it. A question with no source-backed part '
            'is listed as unknown rather than answered.</p>')
    body += table(
        "tbl-questions", "Questions, known and unknown",
        ["ID", "Question", "Known (with a source)", "Still missing", "What would close it",
         "What it blocks"],
        [row([cell(q[0]), cell(q[1]), cell(q[2]), cell(q[3]), cell(q[4]), cell(q[5])],
             ["X28-NFL-INJ-W10", "X28-KC-DEPTH"]) for q in QUESTIONS],
        filters=[])
    body += panel("Unknowns that are not answerable from the sources read",
                  "<p>Whether a club's printed order will match its game-day personnel; whether a "
                  "player ruled out on Friday would have played anyway; what a backup is worth; and "
                  "whether any of this beats a price. Each is left unanswered rather than estimated."
                  "</p>",
                  ("X28-NFL-INJ-W10",))
    return body


SUGGESTIONS = [
    ("XS01", "Read club-published Friday game-status reports for all 28 clubs",
     "The league page shows a game status for 5 clubs; a Saints club article headline read today "
     "says four Saints are out and two questionable while the league page shows blank for all twelve "
     "Saints rows.",
     "Turns 25 usable status rows into a league-wide count, which is the difference between an "
     "anecdote and a coverage claim.",
     "Low - 28 pages, one read each", "Club reports are not standardised; wording varies",
     "At least 20 of the 28 clubs publish a game status for every player the league page lists, and "
     "the counts reconcile row by row.",
     "X28-NFL-INJ-W10"),
    ("XS02", "Read the official inactives list instead of the Friday estimate",
     "The Friday report is an estimate; the only list that decides who plays is issued shortly "
     "before kickoff.",
     "Replaces an estimate with the actual pre-game list, which is what any model would need to "
     "score against.",
     "Medium - timing-dependent and must be captured per game",
     "Timing is easy to miss; a missed capture silently degrades the record",
     "Every Week 10 game has an inactives list captured with its publication timestamp.",
     "X28-NFL-INJ-W10"),
    ("XS03", "Join players on a stable identifier, not on spelling",
     "This join normalises names. Six players with a game status are not printed on their club's "
     "chart, and 40 of 326 rows could not be matched at all.",
     "Removes a silent failure mode: a missed match currently looks exactly like 'not on the chart'.",
     "Medium - store both the nfl.com player URL and the club roster URL per player",
     "The two publishers use different URL slugs for the same person",
     "Match rate rises and every unmatched row carries an explicit reason code.",
     "X28-NFL-INJ-W10"),
    ("XS04", "Re-read the ten clubs whose charts are one day older",
     "Ten of the 27 charts are 2026-11-12 reads already in this repository; seventeen are "
     "2026-11-13 reads.",
     "One snapshot instead of two dates mixed in one table.",
     "Low", "None beyond the reads themselves",
     "Every row in the depth table carries the same read date.",
     "A958-NE-DEPTH"),
    ("XS05", "Retry Houston through a second official path",
     "The Texans' depth-chart page returned a heading and no table.",
     "Restores coverage of the 16 Texans injury rows that currently have no rank or replacement.",
     "Low", "The page may simply not render to this reader",
     "Either a full Texans chain is published from a club source, or the failure is recorded with "
     "the second attempt.",
     "X28-HOU-DEPTH"),
    ("XS06", "Publish a 'what changed since the last read' diff on every table",
     "The same league page grew from 276 rows to 326 rows between 2026-11-12 and 2026-11-13.",
     "Makes staleness visible instead of something a reader has to infer from a date.",
     "Medium - needs a retained previous snapshot per source",
     "Diffs can look like data errors if a club edits a page",
     "Each table shows added, removed and changed rows against the previous read.",
     "X28-NFL-INJ-W10"),
    ("XS07", "Keep one canonical availability view instead of four",
     "The site now carries nfl-injuries.html, nfl/origination/depth.html, the assurance depth page "
     "and this desk, each with its own scope and date.",
     "A reader currently has to reconcile four pages to answer one question.",
     "High - touches pages owned by completed sessions",
     "Merging could overwrite another session's values",
     "One availability page, with the other three reduced to dated supplements that link to it.",
     "X28-NFL-INJ-W10"),
    ("XS08", "Stamp every table with its evidence file and a verification badge",
     "This desk already links each row to the saved rendered text; the older pages do not.",
     "Lets a reviewer re-check any row without re-reading the whole page.",
     "Low", "None",
     "Every table on the site links to the saved evidence for its rows.",
     "X28-NFL-INJ-W10"),
    ("XS09", "Do not add a price feed until source rights are settled",
     "NFL.com terms restrict systematic retrieval and prohibit use of the services to wager; no "
     "licence is evidenced anywhere in this repository.",
     "Prevents a rights problem from being created while chasing a metric.",
     "None", "None - this is a standing constraint",
     "A written licence, or a source whose terms permit the intended use, is filed before any price "
     "is stored.",
     "X28-NFL-INJ-W10"),
    ("XS10", "Record Week 10 results after the games, without prices, to build the first labelled row",
     "Nothing in the record connects an availability observation to an outcome.",
     "Creates the first observation that could eventually be scored - still not proof of anything on "
     "its own.",
     "Low", "Invites over-reading a single week",
     "Final scores for all 14 games are recorded with their source, and the page states plainly that "
     "one week proves nothing.",
     "X28-NFL-INJ-W10"),
]


def suggestions_page():
    body = ('<p class="lead">Proposals, ranked by the decision they unlock. Nothing on this page has '
            'been implemented, and nothing will be until a path is chosen below. Choosing a path '
            'here records a local preference only - it does not authorise work, spend money or '
            'change the published data.</p>')
    body += panel("How the review workflow works",
                  "<ol><li>Each proposal states its evidence, what it unlocks, its cost, its risk "
                  "and an acceptance test.</li>"
                  "<li>A reviewer chooses <strong>Adopt</strong>, <strong>Defer</strong> or "
                  "<strong>Reject</strong> for each row, with a reason.</li>"
                  "<li>The choices are saved in this browser only and can be exported as JSON, so a "
                  "decision can be carried to the person who implements it.</li>"
                  "<li>Nothing changes on the site until an adopted proposal has been implemented and "
                  "re-verified against official sources.</li></ol>"
                  '<p id="decision-status" role="status"></p>'
                  '<p><button type="button" id="export-decisions">Export my choices (JSON)</button> '
                  '<button type="button" id="clear-decisions">Clear my choices</button></p>')
    rows = []
    for sid, title, evidence, unlocks, cost, risk, test, source in SUGGESTIONS:
        choices = "".join(
            f'<label class="choice"><input type="radio" name="choice-{esc(sid)}" '
            f'value="{esc(opt)}" data-choice="{esc(sid)}"> {esc(opt)}</label>' for opt in
            ("Adopt", "Defer", "Reject"))
        rows.append(row([
            cell(sid), cell(title), cell(evidence), cell(unlocks), cell(cost), cell(risk),
            cell(test),
            f'<td class="choices">{choices}'
            f'<label class="reason">Reason <input type="text" data-reason="{esc(sid)}" '
            f'placeholder="optional"></label></td>',
        ], [source, "X28-NFL-INJ-W10"]))
    body += table(
        "tbl-suggestions", "Suggestions for review",
        ["ID", "Proposal", "Evidence", "What it unlocks", "Cost", "Risk", "Acceptance test",
         "Choose a path"],
        rows,
        note="Default state is 'no choice recorded'. The recommendations above are proposals, not "
             "decisions.",
        filters=[("status", "Path", ["Adopt", "Defer", "Reject", "no choice recorded"])])
    return body


FLAGS = [
    ("XF01", "Game status published for 5 of 28 clubs",
     "The league injury report carries a game status on 25 of 326 rows. The other 301 are blank on "
     "the page itself, and the page does not say what a blank means.",
     "Any availability count is limited to those five clubs. No club outside them is assessed.",
     "Needs review", "X28-NFL-INJ-W10"),
    ("XF02", "Houston Texans depth chart not rendered",
     "The club page returned its title and heading but no depth-chart table to the reader on "
     "2026-11-13.",
     "Sixteen Texans injury rows have no printed rank and no replacement. Nothing was substituted.",
     "Needs review", "X28-HOU-DEPTH"),
    ("XF03", "Two different read dates in one table",
     "Seventeen club charts were read on 2026-11-13; ten were already in this repository from a "
     "2026-11-12 read and are reused as such.",
     "The depth table mixes two dates. Each row carries its own date, but the table is not a single "
     "snapshot.",
     "Needs review", "A958-NE-DEPTH"),
    ("XF04", "Publishers call their own charts unofficial",
     "Kansas City, Dallas, the Los Angeles Rams, Minnesota, New Orleans, the New York Jets and "
     "Tennessee label the chart unofficial, or compile it in the communications department.",
     "Rank 1 is the club's printed opinion, not a confirmed game-day starter.",
     "Needs review", "X28-KC-DEPTH"),
    ("XF05", "Players with a status who are not printed on their club's chart",
     "Six players carry a game status but do not appear on the club's own printed chart: Lucas "
     "Patrick (WAS), Malik Harrison (NYG), Reggie Gilliam (NE), Greg Van Roten (NE), Kerby Joseph "
     "(DET) and Arden Key (IND).",
     "Their rank and replacement are blank. Either the chart is stale or the player is not in the "
     "printed rotation; the sources read do not say which.",
     "Needs review", "X28-NFL-INJ-W10"),
    ("XF06", "Two official publishers disagree on New Orleans",
     "A New Orleans Saints article headline visible on the club's own depth-chart page states four "
     "Saints are out and two questionable on Friday, while the league page shows a blank game status "
     "for all twelve Saints rows.",
     "The league page is not a complete source of Friday statuses. This is a publisher disagreement, "
     "not a transcription error, and no reconciliation is asserted.",
     "Needs review", "X28-NFL-INJ-W10"),
    ("XF07", "Two clubs print an empty cell inside a chain",
     "The New York Jets print a defensive-line row whose first cell is empty and whose second names "
     "Jack Heflin; Washington prints a linebacker row whose second-string cell is empty and whose "
     "third names Kain Medrano.",
     "Both blanks are preserved rather than filled. Neither chart says who occupies the empty rank.",
     "Needs review", ("X28-NYJ-DEPTH", "A958-WAS-DEPTH")),
    ("XF08", "Twenty cells print two players in one slot",
     "Clubs including Minnesota, Jacksonville, Tennessee, Las Vegas, the Los Angeles Rams and New "
     "Orleans print two names in a single depth cell.",
     "No order inside the cell is published, so none is recorded. Both names are shown.",
     "Needs review", "X28-MIN-DEPTH"),
    ("XF09", "Name-based matching, not identifier-based",
     "Rows are joined by normalised player name within a club. 40 of 326 rows did not match.",
     "A missed match and a genuine absence look identical in the output. Reason codes are not yet "
     "stored.",
     "Needs review", "X28-NFL-INJ-W10"),
    ("XF10", "No price, no result, no value - by design",
     "No sportsbook price and no final score for these games was retrieved, and no replacement value "
     "is estimated.",
     "Nothing here can be turned into an edge, a stake, a ranking or a reward. That limitation is "
     "the honest output, not a gap to be filled by guessing.",
     "Standing", "X28-NFL-INJ-W10"),
]


def flagged_page():
    body = ('<p class="lead">Every irregularity found while reading the official sources, with the '
            'link that produced it. None of these blocks publication; several block a claim.</p>')
    body += table(
        "tbl-flagged", "Flagged for review",
        ["ID", "Item", "What was found", "What it means for the numbers", "Status"],
        [row([cell(f[0]), cell(f[1]), cell(f[2]), cell(f[3]), cell(f[4])],
             f[5] if isinstance(f[5], tuple) else (f[5],)) for f in FLAGS],
        filters=[("status", "Status", ["Needs review", "Standing"])])
    return body


def sources_page():
    local = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    body = ('<p class="lead">Every source this desk read, with the date, the exact scope and the '
            'boundary of the read. A link is a reference; it is not blanket verification of the '
            'page\'s content.</p>')
    body += table(
        "tbl-sources", "Source register for this desk",
        ["ID", "Publisher", "Page", "URL", "Scope actually read", "Read on", "Status"],
        [row([cell(s["id"]), cell(s["publisher"]), cell(s["title"]),
              f'<td><a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">'
              f'{esc(s["url"])}</a></td>',
              cell(s["scope"]), cell(s["checked_on"]), cell(s.get("status", ""))],
             [s["id"]]) for s in local],
        filters=[])
    body += panel("Boundary of every read",
                  "<p>Each page was read through the Arena page reader, which returns rendered text. "
                  "That is not an HTTP-status attestation, not an archive and not a licence. "
                  "NFL.com's terms restrict systematic retrieval and prohibit use of the services to "
                  "wager, so nothing here is automated against the league site and no dataset is "
                  "redistributed.</p>",
                  ("X28-NFL-INJ-W10",))
    return body


def build_pages():
    return {
        "index.html": ("Overview", "What the availability and depletion desk publishes, and what it "
                                   "refuses to invent.", overview()),
        "summary.html": ("Executive summary", "The findings that matter and the gaps that still "
                                              "block a decision.", summary_page()),
        "availability.html": ("Injury ledger", "Every player on the official Week 10 injury report.",
                              availability_page()),
        "depth.html": ("Printed depth chains", "Each club's own chart, in the order it prints it.",
                       depth_page()),
        "depletion.html": ("Starter depletion", "Who is out, what rank the club prints, and who is "
                                                "printed behind him.", depletion_page()),
        "clubs.html": ("Club summary", "One row per club.", clubs_page()),
        "questions.html": ("Questions & answers", "Known with a source, still missing, and what "
                                                  "would close it.", questions_page()),
        "suggestions.html": ("Suggestions for review", "Choose a path before anything is "
                                                       "implemented.", suggestions_page()),
        "flagged.html": ("Flagged for review", "Irregularities with their official links.",
                         flagged_page()),
        "sources.html": ("Source register", "What was read, when, and how far.", sources_page()),
    }


CSS = """:root{color-scheme:light;--bg:#f7f8fb;--panel:#fff;--ink:#172033;--muted:#51607a;--line:#d8deea;--accent:#164e8a;--accent-ink:#fff;--warn:#8a4b00;--ok:#14532d;--bad:#7f1d1d}*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5}.skip{position:absolute;left:-9999px;top:0;background:var(--accent);color:#fff;padding:.5rem;z-index:10}.skip:focus{left:0}.top{background:#101a2e;color:#fff;padding:1rem}.brand{display:flex;gap:.75rem;align-items:baseline;flex-wrap:wrap}.brand strong{font-size:1.25rem}.brand span{color:#c7d2e6}nav{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.75rem}nav a{color:#e6edf7;text-decoration:none;padding:.35rem .55rem;border-radius:.375rem;font-size:.9rem;min-height:2rem;display:inline-flex;align-items:center}nav a:hover,nav a:focus{background:#243452}nav a[aria-current=page]{background:var(--accent);color:var(--accent-ink);font-weight:600}main{max-width:1200px;margin:0 auto;padding:1.25rem}.eyebrow{color:var(--muted);font-size:.85rem;text-transform:uppercase;letter-spacing:.04em}h1{margin:.25rem 0 .5rem;font-size:1.9rem}h2{font-size:1.25rem;margin:1rem 0 .5rem}.subtitle,.lead{color:var(--muted);max-width:75ch}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.75rem;margin:1rem 0}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:.75rem;padding:.9rem}.kpi-value{display:block;font-size:1.6rem;font-weight:700;color:var(--accent)}.kpi-label{color:var(--muted);font-size:.85rem}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.75rem;margin:1rem 0}.card{display:block;background:var(--panel);border:1px solid var(--line);border-radius:.75rem;padding:1rem;text-decoration:none;color:inherit}.card:hover,.card:focus{border-color:var(--accent)}.card h2{margin:0 0 .35rem;font-size:1.05rem;color:var(--accent)}.card p{margin:0;color:var(--muted);font-size:.9rem}.panel{background:var(--panel);border:1px solid var(--line);border-radius:.75rem;padding:1rem;margin:1rem 0}.panel ol,.panel ul{padding-left:1.2rem}.src-line{margin:.5rem 0 0;font-size:.85rem}.controls{display:flex;flex-wrap:wrap;gap:.75rem;align-items:end;margin:.75rem 0}.controls label{display:flex;flex-direction:column;font-size:.85rem;color:var(--muted)}input[type=search],input[type=text],select,button{font:inherit;padding:.4rem .55rem;border:1px solid var(--line);border-radius:.375rem;background:#fff;color:var(--ink);min-height:2rem}button{cursor:pointer;background:var(--accent);color:#fff;border-color:var(--accent)}button:focus,input:focus,select:focus,a:focus{outline:3px solid #f0b429;outline-offset:2px}.count{color:var(--muted);font-size:.85rem}.table-wrap{overflow-x:auto;max-width:100%;border:1px solid var(--line);border-radius:.5rem;background:var(--panel)}table{border-collapse:collapse;width:100%;min-width:720px;font-size:.88rem}caption{text-align:left;padding:.6rem;font-weight:600;color:var(--muted)}th,td{border-top:1px solid var(--line);padding:.45rem .55rem;text-align:left;vertical-align:top}thead th{background:#eef2f8;position:sticky;top:0}tbody tr:nth-child(even){background:#fafbfe}td.src{white-space:nowrap}td.src a{margin-right:.35rem}td[data-empty]{background:#fff7e6}.note,.empty-state{color:var(--muted);font-size:.9rem}a{color:var(--accent);overflow-wrap:anywhere}.status-out{color:var(--bad);font-weight:600}.status-questionable{color:var(--warn);font-weight:600}.status-doubtful{color:var(--warn);font-weight:600}.choices{white-space:nowrap}.choice{display:inline-flex;align-items:center;gap:.2rem;margin-right:.35rem;font-size:.85rem}.reason{display:block;margin-top:.35rem;font-size:.8rem;color:var(--muted)}.reason input{width:100%;min-width:9rem}footer{max-width:1200px;margin:0 auto;padding:1rem 1.25rem 2rem;color:var(--muted);font-size:.85rem}code{background:#eef2f8;padding:.1rem .3rem;border-radius:.25rem}@media(max-width:640px){h1{font-size:1.5rem}main{padding:1rem}.controls{flex-direction:column;align-items:stretch}}"""

JS = r"""
(function(){
  function rows(table){return Array.from(table.tBodies[0]?table.tBodies[0].rows:[]);}
  function apply(table){
    var search=document.querySelector('[data-search="'+table.id+'"]');
    var filters=Array.from(document.querySelectorAll('[data-filter="'+table.id+'"]'));
    var q=search?search.value.trim().toLowerCase():'';
    var visible=0;
    rows(table).forEach(function(tr){
      var ok=!q||tr.textContent.toLowerCase().indexOf(q)>=0;
      filters.forEach(function(sel){
        var key=sel.getAttribute('data-filter-key');var val=sel.value;
        if(!val)return;
        if(key==='status'&&val==='none published'){if((tr.getAttribute('data-status')||'')!=='')ok=false;return;}
        if(key==='status'&&tr.hasAttribute('data-choice')){
          if((tr.getAttribute('data-path')||'no choice recorded')!==val)ok=false;return;
        }
        if(tr.getAttribute('data-'+key)!==val)ok=false;
      });
      tr.hidden=!ok;if(ok)visible++;
    });
    var count=document.querySelector('[data-count="'+table.id+'"]');
    if(count)count.textContent=visible+' / '+rows(table).length+' rows';
    var empty=document.querySelector('[data-empty-for="'+table.id+'"]');
    if(empty)empty.hidden=visible!==0;
  }
  document.querySelectorAll('table[id]').forEach(function(table){
    var search=document.querySelector('[data-search="'+table.id+'"]');
    if(search)search.addEventListener('input',function(){apply(table);});
    document.querySelectorAll('[data-filter="'+table.id+'"]').forEach(function(sel){
      sel.addEventListener('change',function(){apply(table);});});
    var exportBtn=document.querySelector('[data-export="'+table.id+'"]');
    if(exportBtn)exportBtn.addEventListener('click',function(){
      var headers=Array.from(table.tHead.rows[0].cells).map(function(th){return th.textContent.trim();});
      var lines=[headers.map(csv).join(',')];
      rows(table).filter(function(tr){return !tr.hidden;}).forEach(function(tr){
        lines.push(Array.from(tr.cells).map(function(td){return csv(td.textContent.trim());}).join(','));});
      download(table.id+'-visible.csv',lines.join('\r\n'),'text/csv');
    });
    apply(table);
  });
  function csv(value){return '"'+value.replace(/"/g,'""')+'"';}
  function download(name,text,type){var blob=new Blob([text],{type:type});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);}

  // ---- suggestion review workflow (local preference only) -------------------
  var key='nfl-availability-28ef-decisions-v1';
  var choices=Array.from(document.querySelectorAll('[data-choice]'));
  var reasons=Array.from(document.querySelectorAll('[data-reason]'));
  function load(){try{return JSON.parse(localStorage.getItem(key)||'{}');}catch(e){return {};}}
  function save(state){try{localStorage.setItem(key,JSON.stringify(state));}catch(e){}}
  function pathOf(id){var state=load();return (state[id]&&state[id].path)||'';}
  function status(){
    var el=document.getElementById('decision-status');if(!el)return;
    var state=load();var n=Object.keys(state).filter(function(k){return state[k]&&state[k].path;}).length;
    el.textContent=n+' of '+choices.length+' proposals have a path recorded in this browser. '
      +'Local preference only: this does not implement anything or change published data.';
  }
  function paint(){
    choices.forEach(function(input){
      var id=input.getAttribute('data-choice');
      input.checked=pathOf(id)===input.value;
    });
    reasons.forEach(function(input){
      var id=input.getAttribute('data-reason');var state=load();
      input.value=(state[id]&&state[id].reason)||'';
    });
    document.querySelectorAll('tr[data-source-ids]').forEach(function(tr){
      var input=tr.querySelector('[data-choice]');
      if(!input)return;
      var path=pathOf(input.getAttribute('data-choice'))||'no choice recorded';
      tr.setAttribute('data-path',path);
    });
    status();
    var table=document.getElementById('tbl-suggestions');
    if(table)apply(table);
  }
  choices.forEach(function(input){
    input.addEventListener('change',function(){
      var id=input.getAttribute('data-choice');var state=load();
      state[id]=Object.assign({},state[id],{path:input.value});
      save(state);paint();
    });
  });
  reasons.forEach(function(input){
    input.addEventListener('input',function(){
      var id=input.getAttribute('data-reason');var state=load();
      state[id]=Object.assign({},state[id],{reason:input.value});
      save(state);
    });
  });
  var exportBtn=document.getElementById('export-decisions');
  if(exportBtn)exportBtn.addEventListener('click',function(){
    download('availability-desk-decisions.json',JSON.stringify({
      desk:'nfl-availability-28ef',checked_on:'2026-11-13',decisions:load(),
      note:'Local review preference only. Not approval, not authorisation, not an implementation record.'
    },null,2),'application/json');
  });
  var clearBtn=document.getElementById('clear-decisions');
  if(clearBtn)clearBtn.addEventListener('click',function(){save({});paint();});
  paint();
})();
"""


def write_all(check=False):
    pages = build_pages()
    SITE.mkdir(parents=True, exist_ok=True)
    outputs = {f"site/{name}": layout(name, title, body, subtitle)
               for name, (title, subtitle, body) in pages.items()}
    outputs["site/style.css"] = CSS
    outputs["site/app.js"] = JS
    outputs["site/manifest.json"] = json.dumps(
        {"pages": [name for name, _ in PAGES], "generated": True,
         "boundary": "Static desk; no network calls, no inferred values, no prices."},
        indent=2) + "\n"
    for rel, content in outputs.items():
        path = ROOT / "nfl-availability-28ef" / rel
        if check and (not path.exists() or path.read_text(encoding="utf-8") != content):
            raise SystemExit(f"stale or missing generated file: {rel}")
        path.write_text(content, encoding="utf-8")
    return outputs


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the generated files are current")
    args = parser.parse_args()
    out = write_all(check=args.check)
    print(f"built {len(out)} files"
          + (" (check: byte-identical)" if args.check else ""))
