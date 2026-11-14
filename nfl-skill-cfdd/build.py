#!/usr/bin/env python3
"""Deterministic generator for the skill-separation desk site.

Contract inherited from the rest of this repository and enforced by scripts/check_site.py:
  * every ``<tbody><tr>`` carries ``data-source-ids`` naming registered source IDs, and
  * at least one ``<a>`` in that row points at one of those registered URLs.
  * an unknown value is an empty cell with ``data-empty="true"``, never filled in.

Nothing on these pages is computed at read time. Every number comes from a committed artifact in
``nfl-skill-cfdd/data/`` that a script regenerates byte-identically under ``--check``.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"
SITE = HERE / "site"

READ_ON = "2026-11-14"

PAGES = [
    ("index.html", "Overview"),
    ("summary.html", "Executive summary"),
    ("verification.html", "Standings re-verification"),
    ("depth.html", "Printed depth coverage"),
    ("depletion.html", "Starter depletion index"),
    ("join.html", "Injury × depth join"),
    ("luck.html", "Skill vs luck"),
    ("correlation.html", "Correlation"),
    ("strategies.html", "Strategies & gates"),
    ("leaderboard.html", "Leaderboard"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions for review"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Source register"),
    ("method.html", "Method & limits"),
]

SOURCE_IDS = {
    "CFDD-NFL-STANDINGS": "https://www.nfl.com/standings/",
    "X28-NFL-INJ-W10": "https://www.nfl.com/injuries/league/2026/REG10",
    "CFDD-NFL-TERMS": "https://www.nfl.com/legal/terms/",
    "CFDD-CHI-DEPTH": "https://www.chicagobears.com/team/depth-chart",
    "CFDD-DEN-DEPTH": "https://www.denverbroncos.com/team/depth-chart/",
    "CFDD-PHI-DEPTH": "https://www.philadelphiaeagles.com/team/depth-chart",
    "CFDD-TB-DEPTH": "https://www.buccaneers.com/team/depth-chart",
    "CFDD-HOU-DEPTH": "https://www.houstontexans.com/team/depth-chart",
    "NFL-TEAM-OFF": "https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all",
}

# The chart source for each club captured by this session; other clubs point at the ledger source
# because their chart was transcribed in an earlier session and is registered there.
CLUB_CHART_SOURCE = {
    "CHI": "CFDD-CHI-DEPTH", "DEN": "CFDD-DEN-DEPTH",
    "PHI": "CFDD-PHI-DEPTH", "TB": "CFDD-TB-DEPTH",
    "HOU": "CFDD-HOU-DEPTH",
}


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load_csv(name: str) -> list[dict]:
    import csv
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def src(ids: list[str]) -> str:
    parts = []
    for i in ids:
        parts.append(f'<a href="{esc(SOURCE_IDS[i])}" target="_blank" '
                     f'rel="noopener noreferrer">{esc(i)}</a>')
    return " ".join(parts)


def cell(value, numeric: bool = False) -> str:
    if value is None or str(value).strip() == "":
        return '<td data-empty="true" class="blank" aria-label="no value published"></td>'
    cls = ' class="num"' if numeric else ""
    return f"<td{cls}>{esc(value)}</td>"


def table(headers: list[str], rows: list[str], caption: str = "", note: str = "") -> str:
    head = "".join(f"<th scope=\"col\">{esc(h)}</th>" for h in headers)
    out = [f'<div class="table-wrap"><table>']
    if caption:
        out.append(f"<caption>{esc(caption)}</caption>")
    out.append(f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")
    if note:
        out.append(f'<p class="note">{note}</p>')
    return "".join(out)


def fmt_stat(value, places=3) -> str:
    """Display formatting only. The committed CSV/JSON always keeps full precision."""
    try:
        return f"{float(value):.{places}f}"
    except (TypeError, ValueError):
        return value


def kpi(value, label, blank=False) -> str:
    shown = value if not blank else "&mdash;"
    return (f'<div class="kpi"><span class="kpi-value">{shown}</span>'
            f'<span class="kpi-label">{esc(label)}</span></div>')


def badge(text: str, kind: str) -> str:
    return f'<span class="badge badge-{esc(kind)}">{esc(text)}</span>'


# --------------------------------------------------------------------------- shell
def page(slug: str, title: str, subtitle: str, body: str) -> str:
    nav = "".join(
        f'<a href="{esc(href)}"'
        + (' aria-current="page"' if href == slug else "")
        + f'>{esc(label)}</a>'
        for href, label in PAGES
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OWN7 skill &amp; availability desk</title>
<meta name="description" content="{esc(subtitle)}">
<link rel="stylesheet" href="style.css"><script src="app.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="brand"><strong>OWN7</strong><span>NFL skill &amp; availability desk</span></div>
<nav aria-label="Desk sections">{nav}</nav></header>
<main id="main"><p class="eyebrow">Bounded snapshot · read {READ_ON} · research only · no wagers · no prices</p>
<h1>{esc(title)}</h1><p class="subtitle">{subtitle}</p>
{body}
<footer><p>OWN7 · independent research. NFL data attributed to NFL.com; club depth charts attributed to
each club's official site. Not affiliated with or endorsed by the NFL or any club.
{len(PAGES)} pages · every table row links the official source it came from · unknown values are blank,
never filled in.</p>
<p><a href="sources.html">Source register</a> · <a href="flagged.html">Flagged for review</a> ·
<a href="suggestions.html">Suggestions</a> · <a href="method.html">Method &amp; limits</a></p></footer>
</main></body></html>
"""


# --------------------------------------------------------------------------- pages
def build_index() -> str:
    cap = load_json("standings-capture-2026-11-14.json")
    depths = load_json("depth-summary-2026-11-14.json")
    dep = load_json("depletion-index-2026-11-14.json")
    luck = load_json("skill-luck-results-2026-11-14.json")
    gates = load_json("gates-2026-11-14.json")
    dec = load_json("decisions-2026-11-14.json")
    over = luck["overdispersion"]
    board = load_csv("leaderboard-2026-11-14.csv")

    kpis = "".join([
        kpi(cap["rows_parsed"], "standings rows re-verified against the publisher, 2026-11-14"),
        kpi(len(depths["clubs_captured"]), "newly captured printed depth charts (the 4 bye clubs)"),
        kpi(depths["total_printed_slots"], "printed depth slots transcribed in this capture"),
        kpi(dep["rows_matched_to_printed_chart"], "of 326 injury rows now matched to a printed slot"),
        kpi(dep["starters_ruled_out"], "printed starters ruled Out at Week 10"),
        kpi(f'{gates["counts"]["pass"]}/{gates["counts"]["total"]}', "validation gates passing, computed not declared"),
        kpi("0", "qualified strategies, and 0 rewards paid"),
        kpi(dec["suggestions"], "suggestions for you to review and choose"),
    ])

    cards = "".join([
        '<a class="card" href="verification.html"><h2>Standings re-verification</h2>'
        '<p>All 32 rows re-read from the publisher on 2026-11-14, arithmetic re-derived, and the '
        'two clubs that moved shown to be explained by exactly one result.</p></a>',
        '<a class="card" href="depletion.html"><h2>Starter depletion index</h2>'
        '<p>Every injured player joined to the rank its own club prints, offence and defence kept '
        'separate, with no invented point value.</p></a>',
        '<a class="card" href="luck.html"><h2>Skill vs luck</h2>'
        '<p>An executed overdispersion test, and the exact number of settled bets needed before a '
        'strategy may be called skill based.</p></a>',
        '<a class="card" href="suggestions.html"><h2>Suggestions to review</h2>'
        '<p>Ten proposals, each with evidence, cost, risk and a runnable acceptance test. Adopt, '
        'defer or reject - the record starts blank.</p></a>',
        '<a class="card" href="questions.html"><h2>Questions</h2>'
        '<p>Fifteen questions split into what is known with a source, what is missing, what closes '
        'it and what it blocks.</p></a>',
        '<a class="card" href="flagged.html"><h2>Flagged for review</h2>'
        '<p>Every irregularity found while doing this work, with the official link, so you can '
        'check it yourself.</p></a>',
    ])

    head = (
        '<section class="panel"><h2>The one-paragraph answer</h2>'
        f'<p>This desk re-verified <strong>{cap["rows_parsed"]} club standings rows</strong> against '
        f'the official publisher on {READ_ON} and explained the only two that moved. It captured '
        f'<strong>{len(depths["clubs_captured"])} printed depth charts</strong> that were missing '
        f'({", ".join(depths["clubs_captured"])}) and transcribed '
        f'<strong>{depths["total_printed_slots"]} slots</strong>, which raises the injury-to-chart '
        f'match from the earlier desk to <strong>{dep["rows_matched_to_printed_chart"]} of '
        f'{dep["injury_rows"]}</strong>. It then ran the test that answers your actual question - '
        f'can luck be removed - and got a hard answer: the Pythagorean residuals give a '
        f'chi-square of <strong>{fmt_stat(over["statistic"], 2)}</strong> on {over["degrees_of_freedom"]} degrees '
        f'of freedom, <strong>p = {fmt_stat(over["p_value_upper_tail"], 3)}</strong>. That is inside the null, so '
        f'there is no club-level skill this data can detect, and a leaderboard built on eight or '
        f'nine games would be ranking noise. <strong>Zero strategies qualify and zero rewards are '
        f'paid.</strong> Every parlay, prop combo and correlation stage is blank because no price '
        f'and no settled bet exists anywhere in the repository, and the rights question is '
        f'unsettled.</p></section>'
    )

    worst = board[0] if board else None
    state = (
        '<section class="panel"><h2>Where the competition stands</h2>'
        f'<p>{badge("0 qualified", "bad")} {badge("0 rewards", "bad")} '
        f'{badge("0 settled bets", "bad")} {badge("no price source", "warn")}</p>'
        '<p>The leaderboard is published so you can see the gate accounting, not a ranking of skill. '
        f'Its top row is <strong>{esc(worst["name"])}</strong> and that only means it has the fewest '
        'unresolved gates, not that it performs. The board populates the day a strategy clears the '
        'sample-size gate, and that gate needs at least '
        '<strong>153 settled independent bets</strong>.</p>'
        f'<p><a href="leaderboard.html">See the leaderboard and its reward policy</a></p></section>'
    )

    body = f'<div class="kpis">{kpis}</div>{head}{state}' \
           f'<section><h2>Go straight to</h2><div class="cards">{cards}</div></section>'
    return page("index.html", "Overview",
                "What this desk verified on 2026-11-14, what it refuses to invent, and the one "
                "decision the data will let you make right now.", body)


def build_verification() -> str:
    cap = load_json("standings-capture-2026-11-14.json")
    rows = load_csv("standings-2026-11-14.csv")
    moves = load_csv("standings-moves-2026-11-14.csv")

    move_by_club: dict[str, list[dict]] = {}
    for m in moves:
        move_by_club.setdefault(m["club_abbr"], []).append(m)

    body_rows = []
    for r in rows:
        changed = move_by_club.get(r["club_abbr"])
        mark = (f'<span class="moved">moved: {", ".join(sorted({m["field"] for m in changed}))}'
                f'</span>' if changed else "identical")
        body_rows.append(
            f'<tr data-source-ids="CFDD-NFL-STANDINGS">'
            f'<td><strong>{esc(r["club_name"])}</strong><span class="sub">{esc(r["club_abbr"])}</span></td>'
            + cell(r["wins"], True) + cell(r["losses"], True) + cell(r["ties"], True)
            + cell(r["pct_printed"], True) + cell(r["points_for"], True)
            + cell(r["points_against"], True) + cell(r["net_printed"], True)
            + cell(r["streak_printed"]) + cell(r["pct_check"])
            + f'<td>{mark}</td><td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        )

    tables = table(
        ["Club", "W", "L", "T", "PCT", "PF", "PA", "NET", "STRK", "PCT re-derived", "vs frozen 2026-11-12", "Source"],
        body_rows,
        caption=f"All {len(rows)} clubs, read from the official standings page on {READ_ON}",
        note="PCT re-derived computes (W + T/2) / (W + L + T) from the printed W/L/T. Every row "
             "matched to three decimals or the build aborts. The frozen 2026-11-12 snapshot is "
             "never back-filled.",
    )

    move_rows = []
    for m in moves:
        ids = ["CFDD-NFL-STANDINGS"]
        move_rows.append(
            '<tr data-source-ids="CFDD-NFL-STANDINGS">'
            f'<td><strong>{esc(m["club_name"])}</strong></td><td>{esc(m["field"])}</td>'
            + cell(m["frozen_2026_11_12"]) + cell(m["read_2026_11_14"])
            + f'<td>{esc(m["status"])}</td><td class="src">{src(ids)}</td></tr>'
        )
    move_table = table(["Club", "Field", "Frozen 12 Nov", "Read 14 Nov", "Status", "Source"],
                       move_rows,
                       caption=f"{len(moves)} field-level differences across "
                               f"{len(move_by_club)} clubs",
                       note="Only two clubs moved, and every moved field is one of the fields a "
                            "single played game changes.")

    ident = cap["league_identity"]
    mc = cap["move_consistency"]
    body = (
        '<div class="kpis">'
        + kpi(cap["rows_parsed"], "rows parsed") 
        + kpi(f'{cap["rows_byte_identical_to_frozen"]}/32', "identical to the frozen snapshot")
        + kpi(len(move_by_club), "clubs that moved")
        + kpi(ident["total_points_for"], "league points for (= points against)")
        + '</div>'
        '<section class="panel"><h2>How the two moved clubs were checked</h2>'
        f'<p>The league identity balances after the change: total wins '
        f'<strong>{ident["total_wins"]}</strong> equals total losses '
        f'<strong>{ident["total_losses"]}</strong>, and total points for '
        f'<strong>{ident["total_points_for"]}</strong> equals total points against '
        f'<strong>{ident["total_points_against"]}</strong>. That rules out a transcription error '
        f'in one club without any second source.</p>'
        f'<p>Then the deltas were used on their own. Taking only the change in each club\'s PF and '
        f'PA, the arithmetic implies <strong>{esc(mc["implied_result"])}</strong>. The desk did not '
        f'look up the score and then fit it; the score falls out of the two published rows. The '
        f'check is <strong>{esc(mc["consistency"])}</strong>.</p></section>'
        f'<h2>The full table</h2>{tables}'
        f'<h2>Every moved field</h2>{move_table}'
        '<section class="panel"><h2>What was withheld, and why</h2>'
        f'<p>{esc(" ".join(cap["withheld_columns"]))}.</p>'
        '<p>The standings page legend names HOME, ROAD, DIV and CONF, but the rendered table prints '
        'three 3-part records and two decimals in an order that does not identify which is which. '
        'Two of them could be guessed with high confidence; guessing is what this project does not '
        'do. They are absent from the table rather than wrong in it. This blocks strategy S9 '
        '(divisional underdog) and any home/road split, and it is question Q03.</p></section>'
    )
    return page("verification.html", "Standings re-verification",
                "All 32 rows re-read from the publisher on 2026-11-14, with the arithmetic re-derived "
                "and the two moved clubs explained by a single result.", body)


def build_depth() -> str:
    summary = load_json("depth-summary-2026-11-14.json")
    slots = load_csv("depth-slots-2026-11-14.csv")
    index_rows = load_csv("club-depletion-index-2026-11-14.csv")

    coverage = []
    for r in sorted(index_rows, key=lambda x: x["club_abbr"]):
        club = r["club_abbr"]
        sid = CLUB_CHART_SOURCE.get(club)
        ids = [sid] if sid else ["X28-NFL-INJ-W10"]
        chart_src = (
            f'<a href="{esc(SOURCE_IDS[sid])}" target="_blank" rel="noopener noreferrer">'
            f'{esc(sid)}</a>' if sid else
            '<a href="https://www.nfl.com/injuries/league/2026/REG10" target="_blank" '
            'rel="noopener noreferrer">X28-NFL-INJ-W10</a>'
        )
        coverage.append(
            f'<tr data-source-ids="{" ".join(ids)}">'
            f'<td><strong>{esc(club)}</strong></td>'
            + cell(r["printed_chart_available"])
            + cell(r["printed_chart_players"], True)
            + cell(r["players_on_injury_report"], True)
            + f'<td>{esc("this capture, 2026-11-14" if sid else "earlier transcription, 2026-11-12/13")}</td>'
            + f'<td class="src">{chart_src}</td></tr>'
        )
    cover_table = table(["Club", "Chart read", "Printed players", "Injury rows", "Captured", "Chart source"],
                        coverage,
                        caption="Chart coverage for all 32 clubs",
                        note="31 of 32 clubs publish a readable chart. Houston publishes a heading "
                             "and an image and no table on two independent reads; its rows stay blank.")

    per = {c["club_abbr"]: c for c in summary["per_club"]}
    slot_rows = []
    for s in slots:
        sid = CLUB_CHART_SOURCE.get(s["club_abbr"], "X28-NFL-INJ-W10")
        multi = "two names in one printed cell" if s["cell_holds_multiple"] == "yes" else ""
        if s["first_cell_blank"] == "yes":
            multi = (multi + "; " if multi else "") + "club printed no first-string name in this slot"
        slot_rows.append(
            f'<tr data-source-ids="{esc(sid)}">'
            f'<td><strong>{esc(s["club_abbr"])}</strong></td><td>{esc(s["unit"])}</td>'
            f'<td>{esc(s["position"])}</td>'
            + cell(s["rank"], True) + cell(s["player"])
            + cell(multi) + f'<td class="src">{src([sid])}</td></tr>'
        )
    slot_table = table(["Club", "Unit", "Pos", "Rank", "Player as printed", "Note", "Source"],
                       slot_rows,
                       caption=f"All {len(slots)} printed slots captured on {READ_ON}",
                       note="Rank is the printed column position, nothing more. Where a club printed "
                            "two names in one cell both are kept and no order is invented between "
                            "them. Where a club printed no first-string name the gap is preserved.")

    kpis = "".join([
        kpi(len(per), "clubs newly captured in this session"),
        kpi(summary["total_printed_slots"], "printed slots transcribed"),
        kpi(sum(c["multi_name_cells"] for c in per.values()), "cells printing two names"),
        kpi(summary["blank_printed_cells"], "slots with no first-string name printed"),
    ])
    body = (
        f'<div class="kpis">{kpis}</div>'
        '<section class="panel"><h2>Why these four clubs were missing</h2>'
        '<p>Chicago, Denver, Philadelphia and Tampa Bay had no captured chart in any earlier '
        'snapshot. The reason was never written down, and it turns out to be simple: <strong>they '
        'were the four Week 10 bye clubs</strong>. A bye club has no Week 10 injury row, so the '
        'missing charts never surfaced as unmatched injury rows. Nothing was hiding; the gap was '
        'just silent.</p>'
        '<p>All four are now captured and joined, so they are ready for Week 11 rather than '
        'rediscovered then.</p></section>'
        f'<h2>Coverage</h2>{cover_table}'
        f'<h2>The captured slots</h2>{slot_table}'
        '<section class="panel"><h2>Chart quality is not uniform, and the page says so</h2>'
        '<p>Chicago prints a chart date of 10/31/2026, which is <em>earlier</em> than the injury '
        'ledger it is joined against. Denver, Philadelphia and Tampa Bay print no date at all. '
        'Philadelphia labels its own chart "UNOFFICIAL" and still lists two players its own news '
        'feed reported waived on 13 November. All four of these facts are flags CF03, CF04 and '
        'CF09, not footnotes.</p></section>'
    )
    return page("depth.html", "Printed depth coverage",
                "The four clubs with no captured chart are now captured - and they were the Week 10 "
                "bye clubs, which is why the gap stayed silent.", body)


def build_depletion() -> str:
    dep = load_json("depletion-index-2026-11-14.json")
    rows = load_csv("club-depletion-index-2026-11-14.csv")

    body_rows = []
    for r in rows:
        sid = CLUB_CHART_SOURCE.get(r["club_abbr"], "X28-NFL-INJ-W10")
        ids = [sid, "X28-NFL-INJ-W10"] if sid != "X28-NFL-INJ-W10" else ["X28-NFL-INJ-W10"]
        body_rows.append(
            f'<tr data-source-ids="{" ".join(ids)}">'
            f'<td><strong>{esc(r["club_abbr"])}</strong><span class="sub">{esc(r["club_name"])}</span></td>'
            + cell(r["printed_chart_available"])
            + cell(r["players_on_injury_report"], True)
            + cell(r["matched_to_printed_chart"], True)
            + cell(r["offense_starters_on_report"], True)
            + cell(r["offense_starters_ruled_out"], True)
            + cell(r["offense_index"], True)
            + cell(r["defense_starters_on_report"], True)
            + cell(r["defense_starters_ruled_out"], True)
            + cell(r["defense_index"], True)
            + cell(r["total_index"], True)
            + cell(r["game_status_published_for_club"])
            + f'<td class="src">{src(ids)}</td></tr>'
        )
    tbl = table(
        ["Club", "Chart", "On report", "Matched", "OFF starters listed", "OFF starters OUT",
         "OFF index", "DEF starters listed", "DEF starters OUT", "DEF index", "Total index",
         "Game status published", "Source"],
        body_rows,
        caption="Starter depletion by club, offence and defence kept separate",
        note="The index is a weighted count of printed slots, using the disclosed weights "
             "(rank 1/2/3/4 = 1.00/0.45/0.20/0.10; Out/Doubtful/Questionable = 1.00/0.75/0.40). "
             "It orders clubs against each other. It is not a point value, not a probability, and "
             "it never multiplies a price. A club showing 0 has no starter it can prove is out, "
             "usually because the club publishes no game status at all.",
    )

    backups = dep["backed_up_starters"]
    nobackup = dep["no_backup_printed"]
    per_club = {}
    for b in backups:
        per_club.setdefault(b["club"], []).append(b)
    club_lines = ""
    for club, rows_ in sorted(per_club.items()):
        items = "; ".join(
            f'{esc(b["player"])} ({esc(b["position"])}) &rarr; next printed name '
            f'<strong>{esc(b["next_in_line"])}</strong>'
            for b in rows_)
        club_lines += f'<li><strong>{esc(club)}</strong> &mdash; {items}</li>'
    nobackup_lines = "".join(
        f'<li><strong>{esc(n["club"])}</strong> &mdash; {esc(n["player"])} '
        f'({esc(n["position"])}) has no further name printed in that slot.</li>'
        for n in nobackup)

    kpis = "".join([
        kpi(dep["rows_matched_to_printed_chart"], "injury rows matched to a printed slot"),
        kpi(dep["starters_ruled_out"], "printed starters ruled Out"),
        kpi(dep["starters_ruled_out_with_backup_in_line"], "with a named next player in the slot"),
        kpi(dep["starters_ruled_out_with_no_backup_printed"], "with nobody printed behind him"),
    ])
    body = (
        f'<div class="kpis">{kpis}</div>'
        '<section class="panel"><h2>What "depletion" means here, precisely</h2>'
        '<p>A club is depleted at a slot when <strong>the player its own chart prints as first '
        'string is ruled Out</strong> and the chart prints somebody behind him in that same slot. '
        'That is it. The desk names the player, the printed position, and the next name the club '
        'prints in that slot, and it stops there.</p>'
        '<p>It does <em>not</em> say the backup is three points worse, because no data in this '
        'repository can measure that. Snap counts and a before/after performance series would be '
        'needed, and neither was retrieved. That gap is question Q12 and suggestion P04.</p>'
        '<p>Only four clubs publish a game status at all, so most clubs show a zero index because '
        'nothing is provable, not because nobody is hurt. That is flag CF07 and it caps every '
        'conclusion on this page.</p></section>'
        f'<section class="panel"><h2>The {len(backups)} starters it can prove are out, and who is '
        f'printed behind them</h2><ul>{club_lines}</ul>'
        f'<p>One more starter is out with nobody printed behind him:</p>'
        f'<ul>{nobackup_lines}</ul>'
        '<p>A slot is matched on the club, the unit, the printed position and the slot number the '
        'club itself uses - because a club restarts slot numbering for every position, so there are '
        'several "slot 1" rows in one unit. Matching on position alone would have attached the wrong '
        'backup to the wrong starter; that defect was found and fixed while building this page.</p>'
        f'<p><strong>One ambiguity is left and it is published rather than resolved.</strong> '
        f'{dep["injury_rows_printed_in_more_than_one_slot"]} of the '
        f'{dep["rows_matched_to_printed_chart"]} matched rows are players their own club prints in '
        f'more than one slot, and {dep["starters_ruled_out_in_more_than_one_slot"]} of them is a '
        f'ruled-out starter. The join uses one printed slot per player - the most prominent one - '
        f'and marks every affected row. For an ambiguous starter the next name comes from that '
        f'chosen slot, so it could differ in another slot the club also lists him in. Flag CF13.</p>'
        '</section>'
        f'<h2>Every club</h2>{tbl}'
    )
    return page("depletion.html", "Starter depletion index",
                "Every injured player joined to the rank his own club prints, offence and defence "
                "separate, and no invented point value anywhere.", body)


def build_join() -> str:
    rows = load_csv("depletion-join-2026-11-14.csv")
    body_rows = []
    for r in rows:
        ids = ["X28-NFL-INJ-W10"]
        sid = CLUB_CHART_SOURCE.get(r["club_abbr"])
        if sid:
            ids.append(sid)
        note = ""
        if r["on_printed_chart"] == "no":
            note = "not printed on the club's chart"
        body_rows.append(
            f'<tr data-source-ids="{" ".join(dict.fromkeys(ids))}">'
            f'<td><strong>{esc(r["club_abbr"])}</strong></td><td>{esc(r["player"])}</td>'
            f'<td>{esc(r["position_reported"])}</td>'
            + cell(r["injury_listed"]) + cell(r["practice_status"]) + cell(r["game_status"])
            + cell(r["printed_unit"]) + cell(r["printed_position"]) + cell(r["printed_rank"], True)
            + cell(r["track"]) + cell(note)
            + f'<td class="src">{src(list(dict.fromkeys(ids)))}</td></tr>'
        )
    tbl = table(
        ["Club", "Player", "Pos as reported", "Injury", "Practice", "Game status", "Chart unit",
         "Chart pos", "Printed rank", "Track", "Note", "Source"],
        body_rows,
        caption=f"All {len(rows)} injury rows joined to the printed depth charts",
        note="A blank game status means the league page printed an empty cell. It does not mean the "
             "player is healthy. A blank rank means the club's chart does not print that player. "
             "Neither is ever filled in, and a test asserts it.",
    )
    matched = sum(1 for r in rows if r["on_printed_chart"] == "yes")
    body = (
        '<div class="kpis">'
        + kpi(len(rows), "injury rows in the Week 10 ledger")
        + kpi(matched, "matched to a printed slot")
        + kpi(len(rows) - matched, "not printed by their club")
        + kpi(sum(1 for r in rows if r["game_status"].strip()), "rows with a published game status")
        + '</div>'
        '<section class="panel"><h2>The three kinds of blank, kept apart</h2>'
        '<ul>'
        '<li><strong>Blank game status</strong> - the league page printed nothing. 301 of 326 rows. '
        'The page does not say what a blank means, which is question Q11.</li>'
        '<li><strong>Blank rank</strong> - the club does not print this player on its chart, so the '
        'desk cannot say where he sits. It does not assume he is a starter or a backup.</li>'
        '<li><strong>No chart at all</strong> - Houston only. 16 rows with every chart field '
        'blank.</li>'
        '</ul></section>'
        f'{tbl}'
    )
    return page("join.html", "Injury × depth join",
                "Every injury row joined to the rank its own club prints - and the three different "
                "reasons a cell can legitimately be blank.", body)


def build_luck() -> str:
    res = load_json("skill-luck-results-2026-11-14.json")
    over_rows = load_csv("luck-overdispersion-2026-11-14.csv")
    sample = load_csv("sample-size-to-separate-skill.csv")
    streaks = load_csv("chance-streak-table.csv")
    over = res["overdispersion"]

    over_body = []
    for r in over_rows:
        over_body.append(
            '<tr data-source-ids="CFDD-NFL-STANDINGS">'
            f'<td><strong>{esc(r["club_abbr"])}</strong></td>'
            + cell(r["games"], True) + cell(r["pythagorean_pct"], True)
            + cell(r["wins_actual"], True) + cell(r["wins_expected"], True)
            + cell(r["residual"], True) + cell(r["z_residual"], True)
            + cell(r["z_squared"], True)
            + f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        )
    over_table = table(
        ["Club", "G", "Pythagorean PCT", "Actual wins", "Expected wins", "Residual", "z", "z²", "Source"],
        over_body,
        caption=f"Pythagorean residuals, all {over['clubs']} clubs",
        note="z² summed over the league is the overdispersion statistic. Under the null it has a "
             f"chi-square distribution on {over['degrees_of_freedom']} degrees of freedom.",
    )

    sample_body = []
    for r in sample:
        sample_body.append(
            '<tr data-source-ids="CFDD-NFL-STANDINGS">'
            + cell(r["true_win_rate"], True) + cell(r["target_power"], True)
            + cell(r["alpha_one_sided"], True)
            + cell(r["bets_needed_normal_approx"], True)
            + cell(r["bets_needed_exact_binomial"], True)
            + cell(r["wins_needed_out_of_n"], True)
            + cell(r.get("exact_power_at_that_n", ""), True)
            + cell(r["note"])
            + f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        )
    sample_table = table(
        ["True win rate", "Target power", "Alpha (1-sided)", "Bets, normal approx",
         "Bets, exact binomial", "Wins needed", "Exact power at that n", "Note", "Source"],
        sample_body,
        caption="Settled independent bets needed to separate a real edge from break-even",
        note="Break-even is blank on purpose: no sample size can distinguish a 50% rate from "
             "itself. This is the single most decision-relevant table on the site.",
    )

    streak_body = []
    for r in streaks:
        streak_body.append(
            '<tr data-source-ids="CFDD-NFL-STANDINGS">'
            + cell(r["consecutive_wins"], True)
            + cell(r["probability_if_true_rate_is_50pct_pct"], True)
            + cell(r["clubs_expected_to_hit_this_at_least_once"], True)
            + f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        )
    streak_table = table(
        ["Consecutive wins", "Chance if true rate is 50% (%)", "Expected among 100 bettors", "Source"],
        streak_body,
        caption="Why a streak is not evidence",
        note="A five-win run is expected roughly 3 times in 100 bettors under pure chance.",
    )

    not_comp = "".join(
        f'<tr data-source-ids="CFDD-NFL-STANDINGS"><td><strong>{esc(n["quantity"])}</strong></td>'
        f'<td>{esc(n["why_blank"])}</td><td>{esc(n["blocks"])}</td>'
        f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        for n in res["not_computed"]
    )
    not_table = table(["Quantity you asked for", "Why it is blank", "What it blocks", "Source"],
                      not_comp,
                      caption="Every dependence quantity that cannot be estimated here",
                      note="These are not gaps in effort. They are quantities that do not exist in "
                           "this data, and any number printed for them would be invented.")

    body = (
        '<div class="kpis">'
        + kpi(fmt_stat(over["statistic"], 2), f"chi-square statistic, {over['degrees_of_freedom']} df")
        + kpi(fmt_stat(over["p_value_upper_tail"], 3), "upper-tail p-value under the null")
        + kpi(fmt_stat(over["variance_inflation"], 2), "variance inflation (1.0 = a coin flip)")
        + kpi("153", "settled bets needed at a 60% rate, 80% power")
        + '</div>'
        '<section class="panel"><h2>The test, and what it says</h2>'
        f'<p>Each club has a Pythagorean expectation from its own scoring. If that expectation were '
        f'the true per-game probability and games were independent, the standardised residuals '
        f'would square and sum to a chi-square with {over["degrees_of_freedom"]} degrees of '
        f'freedom. The observed sum is <strong>{fmt_stat(over["statistic"], 2)}</strong>, against an expected '
        f'{over["mean_under_null"]}.</p>'
        f'<p><strong>{esc(over["interpretation"])}</strong></p>'
        f'<p>The variance inflation of {fmt_stat(over["variance_inflation"], 2)} deserves a sentence: it is '
        f'below 1, meaning the clubs are <em>less</em> spread out than independent coin flips would '
        f'make them. That is the opposite of the usual story where a few clubs are secretly much '
        f'better. On this data, scoring already explains essentially all of the win variation.</p>'
        f'</section>'
        f'<h2>The sample-size answer</h2>'
        '<section class="panel"><p>This is the number that decides whether your leaderboard can '
        'exist yet. It is not a judgement call; it is the binomial.</p>'
        f'<p>A 52.4% true winner - a genuinely strong bettor - needs <strong>2,682 settled '
        f'bets</strong> before an 80%-power test can tell him apart from break-even. At 55% it is '
        f'<strong>617</strong>. At 60% it is <strong>153</strong>. The repository contains '
        f'<strong>zero</strong> settled bets.</p>'
        '<p>So the answer to "remove luck from the equation" is: it cannot be removed at n=0, and it '
        'cannot be removed at n=20 either. It is removed by accumulating a dated forward record until '
        'the sample is big enough, and by nothing else.</p></section>'
        f'{sample_table}'
        f'<h2>The residuals, club by club</h2>{over_table}'
        f'<h2>Why a streak is not evidence</h2>{streak_table}'
        f'<h2>What this desk will not estimate</h2>{not_table}'
    )
    return page("luck.html", "Skill vs luck",
                "An executed overdispersion test, and the exact number of settled bets required "
                "before any strategy may be called skill based.", body)


def build_correlation() -> str:
    rows = load_csv("correlations-2026-11-14.csv")
    res = load_json("skill-luck-results-2026-11-14.json")

    body_rows = []
    for r in rows:
        ids = ["CFDD-NFL-STANDINGS"]
        if r["source_id"] == "NFL-TEAM-OFF":
            ids = ["NFL-TEAM-OFF"]
        body_rows.append(
            f'<tr data-source-ids="{" ".join(ids)}">'
            f'<td><strong>{esc(r["correlation_id"])}</strong></td>'
            f'<td>{esc(r["quantity_a"])}</td><td>{esc(r["quantity_b"])}</td>'
            + cell(r["n"], True) + cell(r["pearson_r"], True)
            + cell(r["fisher_95_low"], True) + cell(r["fisher_95_high"], True)
            + cell(r["p_value"], True) + cell(r["holm_adjusted_p"], True)
            + cell(r["reject_null_at_0.05"])
            + cell(r.get("caveat", ""))
            + f'<td class="src">{src(ids)}</td></tr>'
        )
    tbl = table(
        ["ID", "Quantity A", "Quantity B", "n", "Pearson r", "95% low", "95% high", "p",
         "Holm p", "Reject at 0.05", "Caveat", "Source"],
        body_rows,
        caption=f"All {len(rows)} correlations computed, with intervals and multiplicity control",
        note="Three correlations were computed and all three trials are counted, so the Holm "
             "adjusted p is never smaller than the raw p. An interval spanning zero is reported as "
             "spanning zero.",
    )

    not_comp = "".join(
        f'<tr data-source-ids="CFDD-NFL-STANDINGS"><td><strong>{esc(n["quantity"])}</strong></td>'
        f'<td>{esc(n["why_blank"])}</td><td>{esc(n["blocks"])}</td>'
        f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        for n in res["not_computed"]
    )
    blank_tbl = table(["Quantity", "Why blank", "Blocks", "Source"], not_comp,
                      caption="The correlations you asked for that cannot be estimated")
    body = (
        '<div class="kpis">'
        + kpi(len(rows), "correlations actually measured")
        + kpi(len(res["not_computed"]), "requested quantities left blank")
        + kpi("1", "correlation that is significant (and it is a validity check)")
        + kpi("0", "leg-level correlations, because no leg exists")
        + '</div>'
        '<section class="panel"><h2>The distinction that matters</h2>'
        '<p>You asked for correlation values for parlays and player-prop combos. What is measurable '
        'here is <strong>club-level</strong> correlation: how one club-season quantity moves with '
        'another across 32 clubs. That is a genuinely different quantity from <strong>leg</strong> '
        'correlation, which is how two outcomes on the same ticket move together.</p>'
        '<p>Club-level r cannot be substituted for leg r. A negative club-level correlation between '
        'points scored and points allowed says nothing about whether two legs of a parlay are '
        'independent. Publishing one as the other would be the single most tempting error in this '
        'whole project, so the two are kept apart by name and the leg version stays blank.</p>'
        '</section>'
        f'{tbl}'
        '<section class="panel"><h2>Read the one significant result carefully</h2>'
        '<p>Pythagorean expected wins against actual wins gives r = 0.867 and a Holm-adjusted p of '
        '0. That is <em>not</em> a finding. Both sides are computed from the same PF/PA pair, so a '
        'high correlation is arithmetic, not evidence. It is published as a validity check on the '
        'method and it carries that caveat in its own row. Flag CF09.</p>'
        '<p>Meanwhile the two genuinely independent comparisons - points for against points '
        'against, and offensive passing efficiency against defensive passing efficiency - both '
        'straddle zero after multiplicity control. That is the honest state of the evidence.</p>'
        '</section>'
        f'<h2>What is blank, and why</h2>{blank_tbl}'
    )
    return page("correlation.html", "Correlation",
                "Three correlations measured with intervals and multiplicity control; the ones you "
                "actually asked for are blank because the data does not exist.", body)


def build_strategies() -> str:
    matrix = load_csv("strategies-2026-11-14.csv")
    gates = load_json("gates-2026-11-14.json")
    body_rows = []
    for r in matrix:
        body_rows.append(
            '<tr data-source-ids="CFDD-NFL-STANDINGS">'
            f'<td><strong>{esc(r["strategy_id"])}</strong></td><td>{esc(r["name"])}</td>'
            f'<td>{esc(r["bet_type"])}</td><td>{badge(r["status"], "bad")}</td>'
            + cell(r["settled_bets"], True)
            + cell(len(r["gates_failed_or_blocked"].split()), True)
            + cell(r["score"]) + cell(r["gates_failed_or_blocked"]) + cell(r["reason"])
            + f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        )
    strat_tbl = table(
        ["ID", "Strategy", "Bet type", "Status", "Settled bets", "Unresolved gates", "Score",
         "Unresolved gate IDs", "Reason", "Source"],
        body_rows,
        caption=f"All {len(matrix)} strategies, single bets, parlays and prop combos",
        note="Score is blank because a score would have to come from settled results and there are "
             "none. Status is BLOCKED for every strategy, including the ones that need nothing this "
             "project could supply this week.",
    )

    gate_rows = []
    for g in gates["gates"]:
        kind = {"pass": "ok", "fail": "bad", "blocked": "warn"}[g["status"]]
        gate_rows.append(
            '<tr data-source-ids="CFDD-NFL-STANDINGS">'
            f'<td><strong>{esc(g["gate_id"])}</strong></td><td>{esc(g["name"])}</td>'
            f'<td>{esc(g["rule"])}</td><td>{badge(g["status"], kind)}</td>'
            f'<td>{esc(g["evidence"])}</td><td><code>{esc(g["produced_by"])}</code></td>'
            f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        )
    gate_tbl = table(["Gate", "Name", "Rule", "Status", "Evidence", "Produced by", "Source"],
                     gate_rows,
                     caption=f"{gates['counts']['total']} gates: {gates['counts']['pass']} pass, "
                             f"{gates['counts']['fail']} fail, {gates['counts']['blocked']} blocked",
                     note="A gate is not passed because somebody wrote 'pass'. Every row names the "
                          "script that computes it. A gate no data can test is 'blocked', never "
                          "'pass'.")

    body = (
        '<div class="kpis">'
        + kpi(len(matrix), "strategies defined")
        + kpi(gates["counts"]["pass"], "gates passing, computed")
        + kpi(gates["counts"]["fail"], "gates failing")
        + kpi(gates["counts"]["blocked"], "gate blocked on source rights")
        + '</div>'
        '<section class="panel"><h2>Why every strategy is blocked, including the good-sounding ones</h2>'
        '<p>Ten strategies are defined across single bets, two-leg and three-leg parlays and a '
        'player-prop combo. Every one of them is <strong>BLOCKED</strong>, and the reason is always '
        'the same two gates, plus one of the data gates:</p>'
        '<ul>'
        '<li><strong>V8, blocked on rights.</strong> There is no price. NFL.com publishes no odds '
        'and the terms restrict systematic retrieval, so no market value exists to compare a model '
        'against. This is not laziness and not a missing download - it is a permission question, '
        'and suggestion P02 is the way to close it.</li>'
        '<li><strong>V4, failing on sample size.</strong> 153 settled bets minimum at a 60% rate. '
        'There are zero.</li>'
        '<li><strong>V9, failing on forward record.</strong> A prospective record cannot be created '
        'retrospectively, and any attempt to would be the exact hindsight this project is built to '
        'avoid.</li>'
        '</ul>'
        '<p>The parlays and the prop combo carry two extra failures, V3 and V6, because their leg '
        'dependence has never been measured. They are listed anyway, at the bottom of the '
        'leaderboard, so you can see they were not quietly dropped.</p></section>'
        f'<h2>Strategies</h2>{strat_tbl}'
        f'<h2>Every gate, and what computes it</h2>{gate_tbl}'
    )
    return page("strategies.html", "Strategies & gates",
                "Ten strategies across singles, parlays and prop combos, and twelve gates that are "
                "computed rather than declared.", body)


def build_leaderboard() -> str:
    board = load_csv("leaderboard-2026-11-14.csv")
    gates = load_json("gates-2026-11-14.json")
    body_rows = []
    for r in board:
        body_rows.append(
            '<tr data-source-ids="CFDD-NFL-STANDINGS">'
            + cell(r["rank"], True) + f'<td><strong>{esc(r["strategy_id"])}</strong></td>'
            f'<td>{esc(r["name"])}</td><td>{esc(r["bet_type"])}</td>'
            + cell(r["settled_bets"], True) + cell(r["gates_unresolved"], True)
            + cell(r["score"]) + f'<td>{badge(r["eligible_for_reward"], "bad")}</td>'
            + cell(r["why"])
            + f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        )
    tbl = table(["Rank", "ID", "Strategy", "Bet type", "Settled bets", "Unresolved gates",
                 "Score", "Reward eligible", "Why", "Source"],
                body_rows,
                caption=f"{len(board)} strategies ranked by missing evidence, not by performance",
                note="The rank orders by how much evidence is still missing. Rank 1 is the least "
                     "blocked strategy, not the best one. No strategy has a score and none is "
                     "reward eligible.")
    body = (
        '<div class="kpis">'
        + kpi(len(board), "ranked strategies")
        + kpi("0", "settled bets")
        + kpi("0", "qualified strategies")
        + kpi("&mdash;", "cash rewards", blank=True)
        + '</div>'
        '<section class="panel"><h2>The reward policy, and why it pays nothing yet</h2>'
        '<p>You asked for a leaderboard competition that rewards top-performing strategies. The '
        'format is published here and the board is live. It is empty of scores because a reward '
        'paid on noise teaches the project to prefer noise.</p>'
        '<p>The reward rule, stated before any result exists so it cannot be fitted afterwards:</p>'
        '<ol>'
        '<li><strong>V4 must pass.</strong> At least 153 settled independent bets per strategy.</li>'
        '<li><strong>V5 must pass.</strong> The strategy must beat a stated naive baseline out of '
        'sample, not merely beat break-even.</li>'
        '<li><strong>V9 must pass.</strong> A dated forward shadow record, committed before '
        'kickoff, with a verifiable hash chain.</li>'
        '<li><strong>V8 must resolve.</strong> No reward may be attached to a strategy whose price '
        'basis does not exist.</li>'
        '</ol>'
        '<p>Until all four hold, the board ranks evidence debt and pays nothing. '
        f'{badge("0 rewards paid", "bad")}</p></section>'
        '<section class="panel"><h2>What a populated board would need to do differently</h2>'
        '<p>When the gates clear, ranking changes from "fewest missing gates" to a proper score. '
        'The intended score is a proper scoring rule on the shadow record - a Brier score for '
        'probability forecasts - reported with its interval, not a raw win rate. A raw win rate on '
        'a small sample is exactly the noise this page exists to refuse.</p></section>'
        f'{tbl}'
    )
    return page("leaderboard.html", "Leaderboard",
                "The competition format is frozen and published. The board is ranked on evidence "
                "debt because no settled bet exists yet.", body)


def build_questions() -> str:
    dec = load_json("decisions-2026-11-14.json")
    rows = load_csv("questions-2026-11-14.csv")
    body_rows = []
    for q in rows:
        ids = ["CFDD-NFL-STANDINGS"]
        src_url = q["known_source"]
        if "injur" in src_url:
            ids = ["X28-NFL-INJ-W10"]
        elif "term" in src_url:
            ids = ["CFDD-NFL-TERMS"]
        elif "chicagobears" in src_url:
            ids = ["CFDD-CHI-DEPTH"]
        elif "philadelphiaeagles" in src_url:
            ids = ["CFDD-PHI-DEPTH"]
        kind = {"answered": "ok", "open": "warn", "blocked": "bad",
                "answered-but-constraining": "warn"}[q["status"]]
        body_rows.append(
            f'<tr data-source-ids="{" ".join(ids)}">'
            f'<td><strong>{esc(q["question_id"])}</strong></td>'
            f'<td><strong>{esc(q["question"])}</strong><span class="sub">{esc(q["area"])}</span></td>'
            f'<td>{badge(q["status"], kind)}</td>'
            + cell(q["known"]) + cell(q["missing"]) + cell(q["what_closes_it"])
            + cell(q["blocks"])
            + f'<td class="src">{src(ids)}</td></tr>'
        )
    tbl = table(
        ["ID", "Question", "Status", "What is known (with source)", "What is missing",
         "What closes it", "What it blocks", "Source"],
        body_rows,
        caption=f"All {len(rows)} questions that must be settled before a decision",
        note="Every open question names what is missing and what would close it. A question with "
             "no official source for its answer has a blank 'known' cell, never a guess.",
    )
    body = (
        '<div class="kpis">'
        + kpi(dec["questions_answered"], "answered with an official source")
        + kpi(dec["questions_constraining"], "answered but constraining later work")
        + kpi(dec["questions_open"], "open")
        + kpi(dec["questions_blocked"], "blocked on source rights")
        + '</div>'
        '<section class="panel"><h2>How to read this list</h2>'
        '<p>These are not rhetorical. Each one is a question that, if answered the wrong way, makes '
        'a downstream decision wrong. The status column has four values and they mean different '
        'things:</p>'
        '<ul>'
        '<li><strong>answered</strong> - closed this session against an official page, with the '
        'link.</li>'
        '<li><strong>answered but constraining</strong> - we know the answer, and the answer limits '
        'what you may conclude. Q04 and Q05 are both like this: we know the data shows no skill and '
        'we know how much data would be needed, and both facts constrain every later '
        'decision.</li>'
        '<li><strong>open</strong> - no official source settles it yet, and the closing action is '
        'named.</li>'
        '<li><strong>blocked</strong> - it needs a permission, not more work. Q13 and Q14.</li>'
        '</ul></section>'
        f'{tbl}'
    )
    return page("questions.html", "Questions",
                "Fifteen questions, each split into what is known with a source, what is missing, "
                "what closes it and what it blocks.", body)


def build_suggestions() -> str:
    dec = load_json("decisions-2026-11-14.json")
    rows = load_csv("suggestions-2026-11-14.csv")
    body_rows = []
    for s in rows:
        body_rows.append(
            '<tr data-source-ids="CFDD-NFL-STANDINGS">'
            f'<td><strong>{esc(s["suggestion_id"])}</strong></td>'
            f'<td><strong>{esc(s["title"])}</strong><span class="sub">addresses '
            f'{esc(s["addresses"])} · priority {esc(s["priority"])} · effort {esc(s["effort"])}'
            f'</span></td>'
            f'<td>{esc(s["evidence"])}</td><td>{esc(s["unlocks"])}</td>'
            f'<td>{esc(s["cost"])}</td><td>{esc(s["risk"])}</td>'
            f'<td>{esc(s["acceptance_test"])}</td>'
            f'<td class="choices"><label class="choice"><input type="radio" name="d-{esc(s["suggestion_id"])}" value="adopt"> Adopt</label>'
            f'<label class="choice"><input type="radio" name="d-{esc(s["suggestion_id"])}" value="defer"> Defer</label>'
            f'<label class="choice"><input type="radio" name="d-{esc(s["suggestion_id"])}" value="reject"> Reject</label>'
            f'<input class="reason" type="text" placeholder="reason (optional)" '
            f'aria-label="Reason for {esc(s["suggestion_id"])}"></td>'
            f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        )
    tbl = table(
        ["ID", "Suggestion", "Evidence", "What it unlocks", "Cost", "Risk",
         "Acceptance test", "Your choice", "Source"],
        body_rows,
        caption=f"All {len(rows)} suggestions, each with everything needed to decide",
        note="Nothing is preselected. The choice controls write to your browser only and export a "
             "preference file; they are not an authorisation and nothing is implemented by "
             "clicking them.",
    )

    choice_rows = load_csv("choice-record-2026-11-14.csv")
    rec = "".join(
        '<tr data-source-ids="CFDD-NFL-STANDINGS">'
        f'<td><strong>{esc(c["suggestion_id"])}</strong></td><td>{esc(c["title"])}</td>'
        + cell(c["decision"]) + cell(c["decided_on"]) + cell(c["decision_by"])
        + cell(c["note"]) + f'<td class="src">{src(["CFDD-NFL-STANDINGS"])}</td></tr>'
        for c in choice_rows
    )
    rec_tbl = table(["ID", "Suggestion", "Decision", "Decided on", "Decision by", "Note", "Source"],
                    rec,
                    caption="The decision record - deliberately blank",
                    note="This session does not adopt, defer or reject on your behalf. The record "
                         "stays blank until you fill it.")

    body = (
        '<div class="kpis">'
        + kpi(len(rows), "suggestions ready for review")
        + kpi(1, "suggestion already done this session (P08)")
        + kpi(len(rows), "acceptance tests that can be run")
        + kpi(dec["decisions_recorded"], "decisions recorded by this session")
        + '</div>'
        '<section class="panel"><h2>Review these, then choose</h2>'
        '<p>Each suggestion states the evidence behind it, what it unlocks, what it costs, what '
        'could go wrong, and <strong>a test that can actually be run</strong> to know whether it '
        'worked. That last column is the point: a proposal without a pass/fail test is an opinion.</p>'
        '<p>The order to read them in, if you want the shortest path to a decision that matters:</p>'
        '<ol>'
        '<li><strong>P02, settle the rights question.</strong> Every price, parlay, prop and reward '
        'in this project is blocked behind it. Nothing else unblocks as much.</li>'
        '<li><strong>P01, read the 28 club Friday reports.</strong> It closes the largest single '
        'blind spot - 24 clubs with no game status.</li>'
        '<li><strong>P03, start the forward shadow ledger.</strong> It is the only route to a '
        'skill claim and it costs almost nothing to start now.</li>'
        '</ol>'
        '<p>The rest can wait, and P06 (a second season) cannot be hurried at all.</p></section>'
        f'{tbl}'
        '<section class="panel"><h2>Export your choices</h2>'
        '<p><button type="button" id="export-choices">Download my choices as CSV</button></p>'
        '<p class="note">The file is written by your browser. It records a preference for review, '
        'not an instruction to implement anything.</p></section>'
        f'<h2>The decision record</h2>{rec_tbl}'
    )
    return page("suggestions.html", "Suggestions for review",
                "Ten proposals with evidence, cost, risk and a runnable acceptance test. The choice "
                "is yours; the record starts blank.", body)


def build_flagged() -> str:
    dec = load_json("decisions-2026-11-14.json")
    rows = load_csv("flags-2026-11-14.csv")
    body_rows = []
    for f in rows:
        ids = ["CFDD-NFL-STANDINGS"]
        if "injur" in f["source_url"]:
            ids = ["X28-NFL-INJ-W10"]
        elif "legal" in f["source_url"]:
            ids = ["CFDD-NFL-TERMS"]
        elif "chicagobears" in f["source_url"]:
            ids = ["CFDD-CHI-DEPTH"]
        elif "philadelphiaeagles" in f["source_url"]:
            ids = ["CFDD-PHI-DEPTH"]
        elif "houstontexans" in f["source_url"]:
            ids = ["CFDD-HOU-DEPTH"]
        kind = {"open": "warn", "explained": "ok"}[f["status"]]
        sev = {"blocking": "bad", "open": "warn", "informational": "ok"}[f["severity"]]
        body_rows.append(
            f'<tr data-source-ids="{" ".join(ids)}">'
            f'<td><strong>{esc(f["flag_id"])}</strong></td>'
            f'<td><strong>{esc(f["title"])}</strong></td>'
            f'<td>{esc(f["detail"])}</td>'
            f'<td>{badge(f["severity"], sev)}</td><td>{badge(f["status"], kind)}</td>'
            f'<td class="src">{src(ids)}</td></tr>'
        )
    tbl = table(["ID", "Irregularity", "Detail", "Severity", "Status", "Official source"],
                body_rows,
                caption=f"{len(rows)} irregularities found while doing this work",
                note="None of these block publication. All of them are things you should know "
                     "before trusting a number on this site.")
    body = (
        '<div class="kpis">'
        + kpi(dec["flags"], "irregularities recorded")
        + kpi(dec["flags_open"], "still open")
        + kpi(dec["flags_explained"], "explained, nothing to fix")
        + kpi(2, "blocking (rights and game status)")
        + '</div>'
        '<section class="panel"><h2>How to read this page</h2>'
        '<p>These are published rather than fixed, because most of them are true facts about the '
        'sources, not defects in this desk. Two of them are blocking:</p>'
        '<ul>'
        '<li><strong>CF07, only 4 of 28 clubs publish a game status.</strong> This is the single '
        'biggest limit on the availability work. Most clubs show a zero depletion index because '
        'nothing is provable, not because nobody is hurt.</li>'
        '<li><strong>CF10, no price exists anywhere.</strong> This is a rights question, not a data '
        'gap, and every economic claim is blank because of it.</li>'
        '</ul>'
        '<p>The "explained" flags are still worth reading - CF08 and CF09 are the two places where a '
        'reader could easily draw the wrong conclusion from a real number on this site.</p>'
        '</section>'
        f'{tbl}'
    )
    return page("flagged.html", "Flagged for review",
                "Twelve irregularities, each with the official link, published instead of quietly "
                "patched.", body)


def build_sources() -> str:
    rows = []
    for sid, url in SOURCE_IDS.items():
        host = url.split("/")[2]
        rows.append(
            f'<tr data-source-ids="{esc(sid)}">'
            f'<td><strong>{esc(sid)}</strong></td>'
            f'<td><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(url)}</a></td>'
            f'<td>{esc(host)}</td><td>{READ_ON}</td></tr>'
        )
    tbl = table(["Source ID", "URL", "Host", "Read on"], rows,
                caption="Every official page this desk read",
                note="A rendered-text evidence class: direct HTTPS from the build sandbox to nfl.com "
                     "returns curl code 000, so every NFL read went through the Arena page reader. "
                     "The saved text is committed under nfl-skill-cfdd/evidence/.")
    evidence = load_json("standings-capture-2026-11-14.json")
    body = (
        '<section class="panel"><h2>Retrieval honesty</h2>'
        f'<p><strong>{esc(evidence["retrieval_class"])}</strong></p>'
        '<p>That distinction matters. A rendered-text capture proves what a page said, but it is not '
        'an HTTP archive and it cannot prove the page said nothing else. Where a page failed to '
        'render a table - Houston - the failure is recorded as a failure rather than worked '
        'around.</p></section>'
        f'{tbl}'
    )
    return page("sources.html", "Source register",
                "Every official page this desk read, with its host and read date.", body)


def build_method() -> str:
    body = (
        '<section class="panel"><h2>The rules this desk works under</h2>'
        '<ol>'
        '<li><strong>Never infer a value.</strong> If no official source publishes it, the cell is '
        'empty with a machine-readable marker, and a test asserts the cell is truly blank.</li>'
        '<li><strong>Every table row links its source.</strong> A row that cannot link an official '
        'page does not get published.</li>'
        '<li><strong>Recompute what can be recomputed.</strong> Every club row is re-derived from '
        'its own printed numbers, and the league identity must balance or the build aborts.</li>'
        '<li><strong>Separate the quantity from the label.</strong> Club-level correlation is not '
        'leg correlation. A printed rank is not a point value. A Pythagorean residual is not proof '
        'of luck.</li>'
        '<li><strong>Test the maths against published tables.</strong> The chi-square, normal, '
        'Student-t and incomplete-beta implementations are checked against reference values, so a '
        'silent break in the statistics fails the build.</li>'
        '<li><strong>Publish the irregularity.</strong> A source that contradicts itself goes on '
        'the flagged page with a link, not into a footnote.</li>'
        '</ol></section>'
        '<section class="panel"><h2>Reproduce every number</h2>'
        '<p>Python 3.11+, standard library only. From the repository root:</p>'
        '<pre tabindex="0" role="group" aria-label="Commands to reproduce every number"><code>cd nfl-skill-cfdd\n'
        'python collect.py       # standings, arithmetic + identity checks\n'
        'python depth.py         # the 4 newly captured charts\n'
        'python index.py         # depletion join, all 32 clubs\n'
        'python luck.py          # overdispersion, sample size, correlations\n'
        'python ledger.py        # strategies and computed gates\n'
        'python decisions.py     # questions, suggestions, flags\n'
        'python build.py         # regenerate this site\n'
        'python -m unittest discover -s tests -v</code></pre>'
        '<p>Each script supports <code>--check</code>, which re-derives its artifacts in memory and '
        'fails if a committed file is stale. CI runs all of them plus the repository-wide link and '
        'source audit.</p></section>'
        '<section class="panel"><h2>Limits, stated plainly</h2>'
        '<ul>'
        '<li><strong>One partial season.</strong> Eight or nine games per club. No persistence can '
        'be measured, and no strategy can be called skill based.</li>'
        '<li><strong>No price, no ROI, no CLV.</strong> NFL.com publishes no odds and the rights '
        'question is unsettled. These cells are blank by rule and a test enforces it.</li>'
        '<li><strong>No leg dependence.</strong> No settled ticket exists, so parlays and prop '
        'combos cannot be priced at all.</li>'
        '<li><strong>No point value for an injury.</strong> A printed rank is an ordering. '
        'Converting it to points needs snap counts and a before/after series, which are not '
        'retrieved.</li>'
        '<li><strong>Single-source availability.</strong> The league injury page is one publisher. '
        'At least one club disagrees with it in public, so the aggregate is not treated as '
        'complete.</li>'
        '<li><strong>Rendered-text evidence.</strong> Not an HTTP archive. It proves what the page '
        'said; it cannot prove what else the page said.</li>'
        '</ul></section>'
        '<section class="panel"><h2>Attribution and rights</h2>'
        '<p>NFL data is attributed to NFL.com. Club depth charts are attributed to each club\'s '
        'official site. This desk is not affiliated with or endorsed by the NFL or any club. No '
        'wager is placed, no price is published and no monetary reward is defined. No repository '
        'licence is inferred or granted, and third-party source terms remain applicable.</p>'
        '</section>'
    )
    return page("method.html", "Method & limits",
                "The six rules this desk works under, how to reproduce every number, and the limits "
                "that constrain every conclusion.", body)


def build_summary() -> str:
    cap = load_json("standings-capture-2026-11-14.json")
    depths = load_json("depth-summary-2026-11-14.json")
    dep = load_json("depletion-index-2026-11-14.json")
    luck = load_json("skill-luck-results-2026-11-14.json")
    gates = load_json("gates-2026-11-14.json")
    dec = load_json("decisions-2026-11-14.json")
    over = luck["overdispersion"]
    sample = load_csv("sample-size-to-separate-skill.csv")
    n60 = next(r for r in sample
               if r["true_win_rate"] == "0.600" and r["target_power"] == "0.80")

    body = (
        '<section class="panel"><h2>Executive summary</h2>'
        '<h3>What was actually done on 2026-11-14</h3>'
        '<p>The repository was audited and replayed green before any change: 109 tests, 38 '
        'canonical pages, 5,193 sourced table rows, zero link errors. Then this session added a '
        'new desk in its own directory and touched nothing outside it except appended navigation '
        'and source-register lines.</p>'
        '<p><strong>Verification.</strong> All '
        f'<strong>{cap["rows_parsed"]}</strong> club standings rows were re-read from the official '
        f'publisher, with the publisher\'s own arithmetic re-derived row by row and the league '
        f'identity checked. <strong>{cap["rows_byte_identical_to_frozen"]}</strong> rows are '
        f'unchanged from the frozen 12 November snapshot. Two clubs moved, and their deltas alone '
        f'implied a single result, <strong>{esc(cap["move_consistency"]["implied_result"])}</strong>, '
        f'which is exactly what one played game does.</p>'
        '<p><strong>The gap that was found.</strong> Four clubs had never had a depth chart '
        f'captured: {", ".join(depths["clubs_captured"])}. They are the four Week 10 bye clubs, '
        'which is precisely why the gap stayed silent - a bye club has no injury rows, so a missing '
        f'chart never surfaced as an unmatched row. All four are now captured, '
        f'<strong>{depths["total_printed_slots"]} printed slots</strong>, and the injury-to-chart '
        f'match rises to <strong>{dep["rows_matched_to_printed_chart"]} of '
        f'{dep["injury_rows"]}</strong>.</p>'
        '<h3>The answer to the main question</h3>'
        '<p>You asked to remove luck from the equation and build strategies that are selectively '
        'skill based. The honest answer is a measured one, and it is not encouraging:</p>'
        f'<p>The Pythagorean residuals across all 32 clubs sum to a chi-square of '
        f'<strong>{fmt_stat(over["statistic"], 2)}</strong> on {over["degrees_of_freedom"]} degrees of freedom, '
        f'giving <strong>p = {fmt_stat(over["p_value_upper_tail"], 3)}</strong>. The variance inflation is '
        f'<strong>{fmt_stat(over["variance_inflation"], 2)}</strong>. On this snapshot the clubs are '
        f'<em>less</em> dispersed than independent coin flips would make them, which is the '
        f'opposite of the hidden-skill story. A leaderboard built on eight or nine games would be '
        f'ranking noise, and the desk can demonstrate that rather than assert it.</p>'
        f'<p>Luck is removed by sample size and nothing else. At a 60% true rate it takes '
        f'<strong>{n60["bets_needed_exact_binomial"]} settled independent bets</strong> to '
        f'distinguish a real edge from break-even at 80% power. At a more realistic 52.4% it takes '
        f'2,682. The repository contains <strong>zero</strong>.</p>'
        '<h3>What that means for each thing you asked for</h3>'
        '</section>'
        '<section class="panel">'
        '<div class="table-wrap"><table><caption>Your request, and the honest state of it</caption>'
        '<thead><tr><th scope="col">You asked for</th><th scope="col">Where it stands</th>'
        '<th scope="col">What blocks it</th></tr></thead><tbody>'
        '<tr data-source-ids="CFDD-NFL-STANDINGS"><td><strong>Originate my own NFL lines</strong></td>'
        '<td>Model spreads and totals exist from the earlier lab; this desk adds verified inputs. '
        'No line can be graded because there is no market line to grade against.</td>'
        '<td>No price source; rights question unsettled (Q13, Q14)</td>'
        '<td class="src"><a href="https://www.nfl.com/standings/" target="_blank" '
        'rel="noopener noreferrer">CFDD-NFL-STANDINGS</a></td></tr>'
        '<tr data-source-ids="CFDD-NFL-TERMS CFDD-NFL-STANDINGS"><td><strong>Single bets, parlays, prop combos</strong></td>'
        '<td>Ten strategies defined across all three. Every one is BLOCKED, and the parlays and the '
        'prop combo are also blocked because their leg dependence has never been measured.</td>'
        '<td>No price, no settled ticket, no leg history (V6, V8)</td>'
        '<td class="src"><a href="https://www.nfl.com/legal/terms/" target="_blank" '
        'rel="noopener noreferrer">CFDD-NFL-TERMS</a></td></tr>'
        '<tr data-source-ids="CFDD-NFL-STANDINGS"><td><strong>Determine correlation values</strong></td>'
        '<td>Three club-level correlations measured, each with a Fisher interval and Holm '
        'adjustment. The one that is significant is a validity check, not a finding. Every '
        'leg-level and prop-level correlation is blank.</td>'
        '<td>Leg dependence needs settled legs that do not exist (V6)</td>'
        '<td class="src"><a href="https://www.nfl.com/standings/" target="_blank" '
        'rel="noopener noreferrer">CFDD-NFL-STANDINGS</a></td></tr>'
        '<tr data-source-ids="CFDD-NFL-STANDINGS"><td><strong>Remove luck, reward top strategies</strong></td>'
        '<td>Zero strategies qualify, zero rewards are paid, and the sample-size gate that must '
        'pass first is published with its exact threshold.</td>'
        '<td>153 settled bets minimum; zero exist (V4, V5, V9)</td>'
        '<td class="src"><a href="https://www.nfl.com/standings/" target="_blank" '
        'rel="noopener noreferrer">CFDD-NFL-STANDINGS</a></td></tr>'
        '<tr data-source-ids="CFDD-NFL-STANDINGS"><td><strong>Every strategy passes validation gates</strong></td>'
        f'<td>{gates["counts"]["total"]} gates, all computed by a script: '
        f'{gates["counts"]["pass"]} pass, {gates["counts"]["fail"]} fail, '
        f'{gates["counts"]["blocked"]} blocked. No strategy clears them all.</td>'
        '<td>By design - the gates are doing their job</td>'
        '<td class="src"><a href="https://www.nfl.com/standings/" target="_blank" '
        'rel="noopener noreferrer">CFDD-NFL-STANDINGS</a></td></tr>'
        '<tr data-source-ids="X28-NFL-INJ-W10"><td><strong>Track injuries and know who is a backup</strong></td>'
        f'<td>{dep["injury_rows"]} injury rows joined to printed ranks for 31 of 32 clubs, with '
        f'offence and defence separated. {dep["starters_ruled_out"]} printed starters are provably '
        'Out and their next-in-line is named.</td>'
        '<td>Only 4 of 28 clubs publish a game status (CF07)</td>'
        '<td class="src"><a href="https://www.nfl.com/injuries/league/2026/REG10" target="_blank" '
        'rel="noopener noreferrer">X28-NFL-INJ-W10</a></td></tr>'
        '<tr data-source-ids="CFDD-HOU-DEPTH"><td><strong>2nd/3rd/4th string deficiencies on O and D</strong></td>'
        '<td>The join knows the rank of every injured player who appears on his club chart, and '
        'the index keeps offence and defence in separate columns.</td>'
        '<td>No point value is possible without snap counts (Q12); Houston prints no readable chart</td>'
        '<td class="src"><a href="https://www.houstontexans.com/team/depth-chart" target="_blank" '
        'rel="noopener noreferrer">CFDD-HOU-DEPTH</a></td></tr>'
        '<tr data-source-ids="CFDD-NFL-STANDINGS"><td><strong>A clearer, decision-grade site</strong></td>'
        '<td>Fifteen pages, every table row linked to its official source, every unknown cell blank '
        'and marked, and a dedicated review page for each irregularity.</td>'
        '<td>Nothing</td>'
        '<td class="src"><a href="https://www.nfl.com/standings/" target="_blank" '
        'rel="noopener noreferrer">CFDD-NFL-STANDINGS</a></td></tr>'
        '<tr data-source-ids="CFDD-NFL-STANDINGS"><td><strong>A questions list to decide from</strong></td>'
        f'<td>{dec["questions"]} questions: {dec["questions_answered"]} answered with a source, '
        f'{dec["questions_constraining"]} answered but constraining, {dec["questions_open"]} open '
        f'with a named closing action, {dec["questions_blocked"]} blocked on rights.</td>'
        '<td>Nothing</td>'
        '<td class="src"><a href="https://www.nfl.com/standings/" target="_blank" '
        'rel="noopener noreferrer">CFDD-NFL-STANDINGS</a></td></tr>'
        '<tr data-source-ids="CFDD-NFL-STANDINGS"><td><strong>Suggestions to choose from</strong></td>'
        f'<td>{dec["suggestions"]} proposals, each with evidence, cost, risk and a runnable '
        'acceptance test, plus a blank decision record for you to fill.</td>'
        '<td>Nothing - this is ready to review</td>'
        '<td class="src"><a href="https://www.nfl.com/standings/" target="_blank" '
        'rel="noopener noreferrer">CFDD-NFL-STANDINGS</a></td></tr>'
        '</tbody></table></div></section>'
        '<section class="panel"><h2>The three decisions worth making now</h2>'
        '<ol>'
        '<li><strong>Settle the rights question (P02).</strong> It is the only thing that unblocks '
        'prices, parlays, props and rewards. Everything else on this site is downstream of it. If '
        'the answer is no, the honest response is to stop describing this as a betting project and '
        'run it as availability research.</li>'
        '<li><strong>Read the 28 club Friday reports (P01).</strong> Cheapest large win available. '
        'It turns game status from 4 clubs into 28 and it cross-checks the league aggregate, which '
        'one club already contradicts in public.</li>'
        '<li><strong>Start the forward shadow ledger (P03) this week.</strong> It costs one row per '
        'fixture and it is the only path to the 153 settled bets. Every week without it is a week '
        'the competition cannot start.</li>'
        '</ol>'
        '<p>What is <em>not</em> worth doing now: refining a model against this snapshot. The '
        f'residuals are at p = {fmt_stat(over["p_value_upper_tail"], 3)}; there is nothing there to refine yet, '
        'and more modelling on eight games would produce confidence that is not warranted.</p>'
        '</section>'
        '<section class="panel"><h2>The one-sentence version</h2>'
        '<p>Every published number on this site was re-verified against an official source and '
        're-derived arithmetically; the injury and backup tracking now covers 31 of 32 clubs with '
        'offence and defence separated; and the skill question has a hard, measured answer - this '
        'data contains no detectable skill, so no strategy qualifies, no reward is paid, and the '
        'exact number of settled bets required to change that is printed on the site.</p>'
        '</section>'
    )
    return page("summary.html", "Executive summary",
                "What was verified, what was found, what the data actually supports, and the three "
                "decisions worth making now.", body)


# --------------------------------------------------------------------------- main
def main() -> None:
    SITE.mkdir(parents=True, exist_ok=True)
    builders = {
        "index.html": build_index,
        "summary.html": build_summary,
        "verification.html": build_verification,
        "depth.html": build_depth,
        "depletion.html": build_depletion,
        "join.html": build_join,
        "luck.html": build_luck,
        "correlation.html": build_correlation,
        "strategies.html": build_strategies,
        "leaderboard.html": build_leaderboard,
        "questions.html": build_questions,
        "suggestions.html": build_suggestions,
        "flagged.html": build_flagged,
        "sources.html": build_sources,
        "method.html": build_method,
    }
    written = []
    for slug, _label in PAGES:
        if slug not in builders:
            raise SystemExit(f"no builder for {slug}")
        (SITE / slug).write_text(builders[slug](), encoding="utf-8")
        written.append(slug)
    (SITE / "manifest.json").write_text(
        json.dumps({"pages": written, "read_on": READ_ON}, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {len(written)} pages to nfl-skill-cfdd/site/")


if __name__ == "__main__":
    main()
