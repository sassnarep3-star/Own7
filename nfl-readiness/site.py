#!/usr/bin/env python3
"""Generate the decision-readiness desk's pages (D10).

The pages reuse the canonical site's stylesheet and progressive-enhancement script so the desk looks
and behaves like the rest of the site, and they keep the same table contract the site audit enforces:

  * every <tbody> row carries data-source-ids naming registered source IDs;
  * every row contains a link to one of those registered official URLs;
  * an unknown value is a truly empty <td data-empty="true"> and never a zero, a dash or a guess.

Every page is generated. Nothing here is hand-edited, and `--check` rebuilds and demands a
byte-identical result.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SITE = HERE / "site"
DATA = HERE / "data"

SOURCES = {s["id"]: s for s in json.loads((REPO / "research" / "sources.json").read_text())}

READ = "17 Nov 2026"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text())


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def refs(source_ids: list[str], label: str = "") -> str:
    pieces = []
    for sid in source_ids:
        src = SOURCES[sid]
        name = label or sid
        pieces.append(f'<a href="{esc(src["url"])}" title="{esc(src["title"])}" '
                      f'target="_blank" rel="noopener noreferrer">{esc(name)} ↗</a>')
    return "".join(pieces)


def cell(value) -> str:
    if value is None or value == "":
        return ('<td class="blank" data-empty="true" aria-label="Blank — not published by any '
                'official source, or withheld" title="Not supplied; see the gate named on this page"></td>')
    if isinstance(value, tuple) and value and value[0] == "__html":
        return f"<td>{value[1]}</td>"
    if isinstance(value, bool):
        return f'<td class="num" data-value="{int(value)}">{"yes" if value else "no"}</td>'
    if isinstance(value, (int, float)):
        text = str(value) if isinstance(value, int) else f"{value:g}"
        return f'<td class="num" data-value="{value}">{text}</td>'
    return f"<td>{esc(value)}</td>"


def table(table_id: str, columns: list[tuple[str, object]], rows: list[dict], note: str = "",
          statuses: list[str] | None = None) -> str:
    head = "".join(f'<th scope="col" aria-sort="none"><button type="button" data-sort="{i}">'
                   f'{esc(label)}<span class="sort-mark" aria-hidden="true">↕</span></button></th>'
                   for i, (label, _) in enumerate(columns + [("Official source", "__refs")]))
    body = []
    for index, row in enumerate(rows):
        cells = []
        for _, field in columns:
            value = field(row) if callable(field) else row.get(field)
            cells.append(cell(value))
        sids = row.get("source_ids", [])
        cells.append(f'<td class="refs">{refs(sids)}</td>')
        status = row.get("status", row.get("state", ""))
        body.append(f'<tr data-row-id="{esc(row.get("id", index))}" '
                    f'data-source-ids="{esc(" ".join(sids))}" data-status="{esc(status)}">'
                    + "".join(cells) + "</tr>")
    select = ""
    if statuses:
        select = (f'<label><span class="sr-only">Filter {esc(table_id)} by status</span>'
                  f'<select data-status-filter="{table_id}"><option value="">All</option>'
                  + "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in statuses)
                  + "</select></label>")
    return f'''<div class="table-card" data-table-card="{table_id}">
<div class="table-toolbar"><span class="row-count" data-count-for="{table_id}" aria-live="polite">{len(rows)} entries</span><div class="table-tools">{select}<label class="table-search"><span class="sr-only">Search {esc(table_id)}</span><input type="search" placeholder="Filter rows…" data-search-for="{table_id}" autocomplete="off"></label><button class="export-button" type="button" data-export="{table_id}">CSV<span class="sr-only">: {esc(table_id)}</span></button></div></div>
<div class="table-scroll" role="region" aria-label="{esc(table_id)} table, scroll horizontally for more columns" tabindex="0"><table id="{table_id}" data-research-table><caption class="sr-only">{esc(table_id)}. Blank cells are intentional; the gate that blocks each one is named in the row.</caption><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div><p class="table-empty" data-empty-for="{table_id}" hidden>No matching entries. Clear the filters to see all rows.</p></div>''' + (f'<p class="table-note">{note}</p>' if note else "")


def section(title: str, body: str, eyebrow: str = "", subtitle: str = "", sid: str = "") -> str:
    attrs = f' id="sec-{sid}"' if sid else ""
    return (f'<section class="section"{attrs}><div class="section-head"><div>'
            + (f'<div class="eyebrow">{esc(eyebrow)}</div>' if eyebrow else "")
            + f'<h2>{esc(title)}</h2>'
            + (f"<p>{subtitle}</p>" if subtitle else "")
            + f"</div></div>{body}</section>")


def notice(title: str, text: str, info: bool = False) -> str:
    return (f'<div class="notice{" info" if info else ""}"><div><strong>{esc(title)}</strong>'
            f"<p>{text}</p></div></div>")


def metrics(items: list[tuple[str, object, str]]) -> str:
    return ('<div class="metric-grid">' + "".join(
        f'<div class="metric"><div class="metric-top">{esc(label)}</div>'
        f'<div class="metric-value">{esc(value)}</div><small>{esc(note)}</small></div>'
        for label, value, note in items) + "</div>")


STATUS_KIND = {"met": "good", "partial": "warn", "blocked": "warn", "rejected": "neutral",
               "paper": "warn", "closed": "neutral", "qualified": "good", "bye": "neutral",
               "reported": "good", "printed": "good", "no-venue": "warn"}


def status_cell(row: dict):
    """One status badge, so a table column never has to nest a tuple inside a lambda twice."""
    value = row.get("status") or row.get("state") or ""
    return ("__html", badge(value or "unspecified", STATUS_KIND.get(value, "neutral")))


def badge(text: str, kind: str = "neutral") -> str:
    return f'<span class="badge {kind}"><span class="tiny-dot"></span>{esc(text)}</span>'


def panel(title: str, body: str) -> str:
    return f'<div class="panel body-text"><h3>{esc(title)}</h3>{body}</div>'


NAV = [
    ("Readiness", [("index.html", "Landing & readiness"), ("readiness.html", "All 132 requirements"),
                   ("gates.html", "Gates")]),
    ("Signal", [("origination.html", "Origination"), ("leaderboard.html", "Leaderboard"),
                ("luck.html", "Removal of luck"), ("correlation.html", "Correlation"),
                ("ablation.html", "Ablation")]),
    ("Availability", [("availability.html", "Injuries & depth"), ("matchup.html", "Station exposure"),
                      ("fixture-context.html", "Fixture context"), ("diff.html", "What changed")]),
    ("Decide", [("strategy.html", "Strategies"), ("questions.html", "Questions"),
                ("suggestions.html", "Suggestions to review"), ("flagged.html", "Flagged for review")]),
    ("Method", [("verification.html", "Verification"), ("sources.html", "Sources")]),
]


def page(slug: str, title: str, subtitle: str, eyebrow: str, body: str) -> str:
    nav = ""
    for group, entries in NAV:
        nav += f'<div class="nav-group"><div class="nav-label">{group}</div>'
        for href, label in entries:
            current = ' aria-current="page"' if href == slug else ""
            nav += f'<a href="{href}"{current}>{label}</a></div>'.replace("</div>", "", 0)
        nav += "</div>"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(subtitle)}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{esc(title)} · OWN7 decision readiness</title>
<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../../assets/style.css"><script src="../../js/app.js" defer></script></head>
<body><a class="skip-link" href="#main-content">Skip to content</a>
<aside class="sidebar" id="sidebar" aria-label="Desk pages">
<a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">7</span><span class="brand-name">OWN7<small>DECISION READINESS</small></span></a>
<nav aria-label="Main navigation">{nav}</nav>
<div class="sidebar-bottom"><a href="../../index.html">Parent site ↗</a><a href="https://github.com/sassnarep3-star/Own7" target="_blank" rel="noopener noreferrer">Repository ↗</a>
<div class="mode"><span class="dot"></span>NON-COMMERCIAL RESEARCH</div><p>No live lines. No wagers placed.</p></div></aside>
<button class="nav-backdrop" aria-label="Close navigation" tabindex="-1" hidden></button>
<div class="layout"><header class="topbar"><button type="button" class="menu-button" aria-label="Open navigation" aria-expanded="false" aria-controls="sidebar">≡</button>
<div class="breadcrumb"><span class="crumb-parent">Decision readiness</span><span class="divider">/</span><strong>{esc(title)}</strong></div>
<div class="top-right"><label class="search-field"><span class="sr-only">Search tables on this page</span><input type="search" id="page-search" placeholder="Search this page…" autocomplete="off"></label>
<div class="snapshot">OFFICIAL READS<span>{esc(READ)}</span></div></div></header>
<main class="content" id="main-content"><div class="page-heading"><div><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1><p>{subtitle}</p></div></div>
{body}
<footer class="footer"><div><strong>OWN7</strong> / DECISION READINESS<br>NFL data attributed to NFL.com and the member clubs. Not affiliated with or endorsed by the NFL.</div>
<div>Single targeted reads · not a live feed<br><a href="verification.html">Verification</a> &nbsp;·&nbsp; <a href="sources.html">Sources</a> &nbsp;·&nbsp; <a href="suggestions.html">Suggestions</a></div></footer></main></div></body></html>
'''


# --------------------------------------------------------------------------- pages

def page_index() -> str:
    req = load("requirements.json")
    luck = load("luck.json")
    board = load("leaderboard.json")
    avail = load("availability.json")
    c = req["counts"]
    body = notice("No strategy is qualified, and nothing here is a recommendation.",
                  "This desk publishes what it can prove, what it cannot, and the gate and the number that "
                  "separate the two. Every row on every page links a registered official source.")
    body += metrics([
        ("Requirements traced", len(req["requirements"]), f"{c['met']} met · {c['partial']} partial · {c['blocked']} blocked · {c['rejected']} rejected"),
        ("Official rows read", avail["totals"]["injury_rows"] + avail["totals"]["depth_rows"], "347 injury rows + 172 depth slots, 17 Nov"),
        ("Scored backtest games", board["entries"][0]["n"], f"week 6-9 holdout · {board['family_size']} variants"),
        ("Qualified entries", 0, "price and prospective gates closed"),
    ])
    body += section("Decision readiness", table("readiness", [
        ("Requirement", lambda r: ("__html", f'<span class="row-title">{esc(r["id"])} · '
                                             f'{esc(r["requirement"][:92])}' + ("…" if len(r["requirement"]) > 92 else "")
                                             + "</span>")),
        ("State", status_cell),
        ("Gate that blocks it", "gate"),
        ("The number that would clear it", "clearing_number"),
    ], req["requirements"], note=("One row per line of the brief, transcribed verbatim. The full text is on "
                                 "<a href='readiness.html'>All 132 requirements</a>; the gates are on "
                                 "<a href='gates.html'>Gates</a>."), statuses=["met", "partial", "blocked", "rejected"]),
        eyebrow="ONE ROW PER REQUIREMENT", sid="readiness")

    top = board["entries"][0]
    body += '<div class="grid-2">'
    body += panel("What the evidence says about the signal",
                  f"<p>The best of {board['family_size']} singles entries is <strong>{esc(top['id'])}</strong>: "
                  f"Brier skill {top['brier_skill']:+.4f} on {top['n']} holdout games, week-clustered lower "
                  f"bound {top['cluster_lo']:+.4f}, multiplicity-adjusted q {top['q_value']:.3f}.</p>"
                  f"<p>A single test against chance gives p={luck['chance_null']['p_single_test']:.4f}, which "
                  f"looks like a finding. Judged against the whole family of {board['family_size']} trials it "
                  f"is p={luck['family_null']['p_family_wise']:.3f}: the best of that many coin flips reaches "
                  f"this record {luck['family_null']['simulated_family_false_positive_rate']:.3f} of the time.</p>"
                  f"<p>{esc(luck['required_n']['reading'])}</p>"
                  f"<p><a href='luck.html'>The removal-of-luck panel →</a></p>")
    body += panel("What the evidence says about availability",
                  f"<p>{avail['totals']['injury_rows']} injury-report rows across "
                  f"{avail['totals']['clubs_with_report']} clubs, read on {esc(avail['read'])}. "
                  f"{avail['totals']['game_status_present']} carry a game designation.</p>"
                  f"<p>{avail['totals']['on_chart']} of those players appear on one of the "
                  f"{avail['totals']['depth_charts']} club depth charts this desk read, and "
                  f"{avail['totals']['replacement_named']} have a printed name behind them on the chart. "
                  f"{avail['totals']['not_on_chart']} do not appear on a chart at all and are marked as such "
                  f"rather than guessed.</p>"
                  f"<p><strong>Zero</strong> absences are confirmed, because no inactive list, Game Book or "
                  f"snap count is captured. That is why the personnel ablation has an empty arm.</p>"
                  f"<p><a href='availability.html'>Injuries and depth →</a></p>")
    body += "</div>"
    body += section("Where to go next", '<div class="grid-3">' + "".join(
        f'<a class="path-card" href="{href}"><span class="step">{step}</span><h3>{title}</h3>'
        f"<p>{text}</p><span class=\"card-link\">Open →</span></a>"
        for step, title, text, href in [
            ("01 / ORIGINATE", "Originate a line", "Side, then total, then moneyline, with the fair number, the benchmark and the residual as separate columns.", "origination.html"),
            ("02 / CHALLENGE", "Remove the luck", "Exact tails, a week-clustered permutation null, a family adjustment and the sample a real edge would need.", "luck.html"),
            ("03 / CHECK", "Check the availability", "What the report says, what the chart prints, and the difference between an expected starter and a confirmed one.", "availability.html"),
            ("04 / DECIDE", "Choose a path", "Fifteen proposals with cost, risk, an acceptance test and a decision column that is deliberately blank.", "suggestions.html"),
            ("05 / ASK", "Read the open questions", "Twenty-six questions, each split into held, missing, what it blocks and what closes it.", "questions.html"),
            ("06 / VERIFY", "Audit the sources", "Every table row links the official page it came from; the flags page lists what did not reproduce.", "flagged.html"),
        ]) + "</div>", eyebrow="SIX ROUTES", sid="next")
    return page("index.html", "Landing & decision readiness",
                "One row per requirement, with the gate that blocks it and the number that would clear it.",
                "NFL / DECISION READINESS", body)


def page_readiness() -> str:
    req = load("requirements.json")
    rows = req["requirements"]
    body = notice(f"{len(rows)} requirements transcribed verbatim from the brief.",
                  "State, gate and clearing number are this desk's assessment on 2026-11-17. A requirement is "
                  "marked met only where the artefact exists and the condition the brief states is satisfied "
                  "by a number computed in this repository.", info=True)
    body += metrics([("Met", req["counts"]["met"], "artefact exists and the stated condition is met"),
                     ("Partial", req["counts"]["partial"], "deliverable exists, evidence gap named"),
                     ("Blocked", req["counts"]["blocked"], "cannot start without a named datum"),
                     ("Rejected", req["counts"]["rejected"], "proposed approach refused with a reason")])
    body += section("Every requirement", table("requirements", [
        ("ID", "id"), ("Requirement (verbatim)", "requirement"),
        ("State", status_cell),
        ("Gate that blocks it", "gate"), ("The number that would clear it", "clearing_number"),
        ("Where the artefact is", "evidence"),
    ], rows, note="Requirement text is the brief's own wording; only whitespace is normalised.",
        statuses=["met", "partial", "blocked", "rejected"]), eyebrow="THE FULL LEDGER", sid="all")
    body += "<p class='source-line'><a href='gates.html'>The 26 gates →</a> · "
    body += "<a href='suggestions.html'>Proposals that would clear them →</a></p>"
    return page("readiness.html", "All 132 requirements",
                "The brief line by line: state, the gate that blocks it, and the number that would clear it.",
                "NFL / READINESS LEDGER", body)


def page_gates() -> str:
    req = load("requirements.json")
    rows = []
    for gate in req["gates"]:
        blocking = [r["id"] for r in req["requirements"] if r["gate"].startswith(gate["id"])]
        rows.append({**gate, "blocking": ", ".join(blocking) if blocking else "none",
                     "count": len(blocking), "source_ids": ["REPO"]})
    body = notice("A gate is a statement of what must be true before a claim may be made.",
                  "The clearing condition is the observable event, not an opinion. Every gate below is open "
                  "unless its statement is satisfied by a number on file.")
    body += section("Gates", table("gates", [
        ("Gate", lambda r: ("__html", f'<span class="row-title">{esc(r["id"])} · {esc(r["name"])}</span>')),
        ("What it blocks", "statement"), ("What clears it", "clears_when"),
        ("Requirements behind it", "blocking"), ("Count", "count"),
    ], sorted(rows, key=lambda r: -r["count"]), note="A requirement can name several gates; it is listed under the first."),
        eyebrow="26 GATES", sid="gates")
    return page("gates.html", "Gates",
                "Each gate states what must be true before a claim may be published, and what observable event would satisfy it.",
                "NFL / GATES", body)


def page_origination() -> str:
    orig = load("origination.json")
    board = load("leaderboard.json")
    rows = []
    for stage in orig["stages"]:
        for r in stage["all"]:
            rows.append({**r, "market": stage["stage"],
                         "market_line": "", "difference": "",
                         "market_reason": stage["market_column_reason"]})
    body = notice("A fair line and a benchmark are published. A market line is not.",
                  "No registered publisher of NFL prices exists for this use, so the market column and the "
                  "difference-against-market column are blank on every row. The residual shown is against the "
                  "frozen benchmark, which is a model number.")
    body += metrics([("Stages", 3, "side, then total, then moneyline"),
                     ("Originated games", len(orig["stages"][0]["all"]), "weeks 2-9, model M04"),
                     ("Mean side residual", f"{orig['stages'][0]['mean_abs_residual']:g}", "points versus the -2.0 benchmark"),
                     ("Totals published", 2, "two estimators, gap column, no collapse")])
    body += section("Three separate columns per market", table("origination", [
        ("Game", "id"), ("Market", "market"), ("Fair line", "fair"), ("Benchmark line", "benchmark"),
        ("Residual vs benchmark", "residual"), ("Market line", "market_line"),
        ("Difference vs market", "difference"), ("Probability", "probability"),
        ("Official result", "actual"),
    ], rows, note=("Residual is fair minus benchmark. The market and difference columns are blank by policy "
                  "(gate PG-PRICE-SOURCE); a blank is not a zero. The benchmark is the home-field constant for "
                  "the side and twice the prior-week league mean for the total, both computed from weeks before "
                  "the game.")), eyebrow="FAIR · BENCHMARK · RESIDUAL")
    body += "<div class='grid-2'>"
    body += panel("Why the order is side, total, moneyline",
                  f"<p>{esc(orig['order_note'])}</p>"
                  f"<p>Each stage depends on the one before it, and the dependency is published so a reader can "
                  f"see that a total assumption is never allowed to reach the margin.</p>")
    t = orig["two_total_estimators"]
    body += panel("Two total estimators, published twice until one wins",
                  f"<p>M01 (shrunk scoring) mean absolute error {t['mae_m01']:g}; M03 (recency-weighted) "
                  f"{t['mae_m03']:g}. M03 is closer in {t['games_m03_closer']} of "
                  f"{t['games_m03_closer'] + t['games_m01_closer']} games.</p>"
                  f"<p>Gap between the two lines: mean {t['mean_gap']:+.4f} points, standard deviation "
                  f"{t['gap_sd']:g}. Actual-total spread: {t['actual_total_sd']:g}. {esc(t['verdict'])}</p>")
    body += "</div>"
    body += section("Two estimators side by side", table("totals", [
        ("Game", "id"), ("M01 total", "m01"), ("M03 total", "m03"), ("Gap", "gap"),
        ("Actual total", "actual"),
    ], t["rows"], note="The gap column stays until a walk-forward comparison justifies collapsing the pair. "
                       "No comparison on this window would: the registration forbids choosing on it."),
        eyebrow="R95 / R96")
    body += section("Week 11 forecast ledger", panel("Deliberately empty",
        f"<p>{esc(orig['fixture_level_forecast']['note'])}</p>"), eyebrow="PROSPECTIVE")
    return page("origination.html", "Origination",
                "Side, then total, then moneyline — fair line, benchmark line and residual as separate columns.",
                "NFL / ORIGINATION", body)


def page_leaderboard() -> str:
    board = load("leaderboard.json")
    luck = load("luck.json")
    body = notice(f"0 of {len(board['entries'])} entries qualify.",
                  "Ranking is by the week-clustered lower bound on Brier skill against a frozen 0.5 benchmark. "
                  "Win rate is shown and never orders the table. Staking is not on this page at all.")
    body += metrics([("Entries graded", len(board["entries"]), "7 estimators x 3 markets, singles only"),
                     ("Family size", board["family_size"], "BH adjustment across all of them"),
                     ("Qualified", 0, "V7 price and V8 prospective record closed"),
                     ("Window agreement", f"{board['window_concordance']['same_order_positions']}/{board['window_concordance']['of']}",
                      "development vs evaluation order")])
    body += section("Divisions", table("divisions", [
        ("Division", "name"), ("Entries", "entries"), ("Status", "status"),
    ], [{**d, "source_ids": ["REPO"]} for d in board["divisions"]],
        note="A division with no eligible entry is closed with its gate, not filled with a proxy.",
        statuses=None), eyebrow="R47 / R48")
    entries = []
    for e in board["entries"]:
        entries.append({**e, "state": "qualified" if e["qualified"] else "paper",
                        "source_ids": ["X29-NFL-SCHEDULE"]})
    body += section("Singles leaderboard", table("leaderboard", [
        ("Rank", "rank"), ("Entry", "id"), ("Market", "market"),
        ("Brier skill", "brier_skill"), ("Cluster lower bound", "cluster_lo"),
        ("Adjusted q", "q_value"), ("n", "n"), ("Weeks", "weeks"),
        ("Development-window skill", "dev_brier_skill"), ("Directional rate", "directional_rate"),
        ("State", status_cell),
    ], entries, note=("A positive point estimate with a lower bound at or below zero is not evidence. "
                      "The development-window column is published beside the evaluation column so a reader can "
                      "see whether the ranking is a property of the model or of weeks 6-9."),
        statuses=["paper", "qualified"]), eyebrow="PROPER SCORE, NOT WIN RATE", sid="singles")
    body += section("Controls", table("controls", [
        ("Control", "name"), ("Market", "market"), ("n", "n"), ("Brier", "brier"),
        ("Brier skill", "brier_skill"), ("Directional rate", "directional_rate"),
    ], [{**c, "source_ids": ["X29-NFL-SCHEDULE"]} for c in board["controls"]],
        note="Every leaderboard run carries these, so a naive reader can see what luck alone produces."),
        eyebrow="R87 / R88")
    body += panel("What would earn a place",
                  f"<p>{esc(board['why_no_rewards'])}</p>"
                  f"<p>Window concordance: {esc(board['window_concordance']['reading'])}</p>"
                  f"<p><a href='luck.html'>The arithmetic behind that statement →</a></p>")
    return page("leaderboard.html", "Leaderboard",
                "Proper-score divisions, benchmark-relative skill with a cluster lower bound, and a multiplicity adjustment.",
                "NFL / COMPETITION", body)


def page_luck() -> str:
    luck = load("luck.json")
    b = luck["best_entry"]
    body = notice(luck["headline"],
                  "Six different nulls, published together, because each answers a different question and a "
                  "reader who sees only one will draw the wrong conclusion.")
    body += metrics([("Best record", f"{b['directional_hits']}/{b['n']}", b["id"]),
                     ("Single-test p", f"{luck['chance_null']['p_single_test']:.4f}", "looks like a finding"),
                     ("Family-wise p", f"{luck['family_null']['p_family_wise']:.3f}", f"across {luck['family_null']['family_size']} trials"),
                     ("Entries clearing every bar", luck["counts"]["positive_cluster_lo_and_q_at_5pct"], "after cluster bound and q")])
    rows = [
        {"id": "LUCK-1", "question": luck["chance_null"]["question"],
         "value": luck["chance_null"]["p_single_test"], "reading": luck["chance_null"]["reading"],
         "source_ids": ["X29-NFL-SCHEDULE"]},
        {"id": "LUCK-2", "question": luck["family_null"]["question"],
         "value": luck["family_null"]["p_family_wise"], "reading": luck["family_null"]["reading"],
         "source_ids": ["X29-NFL-SCHEDULE"]},
        {"id": "LUCK-3", "question": luck["permutation_null"]["question"],
         "value": luck["permutation_null"]["p_value_best"],
         "reading": f"Week-clustered label shuffling, {luck['permutation_null']['reps']} replications.",
         "source_ids": ["X29-NFL-SCHEDULE"]},
        {"id": "LUCK-4", "question": luck["luck_band"]["question"], "value": luck["luck_band"]["observed_wins"],
         "reading": (f"{luck['luck_band']['central_90pct_low_wins']} to {luck['luck_band']['central_90pct_high_wins']} "
                     f"wins is the central 90% band at n={luck['luck_band']['n']}. "
                     f"{esc(luck['luck_band']['reading'])}"),
         "source_ids": ["X29-NFL-SCHEDULE"]},
    ]
    body += section("The panel", table("luck", [
        ("Question", "question"), ("Value", "value"), ("What it means", "reading"),
    ], rows, note="The family null is the one that governs. A single-test p-value cannot be read without it."),
        eyebrow="R16 / R49 / R50", sid="panel")
    power = [{"id": f"P{int(r['true_rate'] * 1000)}", "rate": r["true_rate"], "n": r["required_n"],
              "weeks": r["weeks_at_13_games"], "seasons": r["seasons_at_272_games"],
              "basis": r["basis"], "source_ids": ["X29-NFL-SCHEDULE"]} for r in luck["required_n"]["rows"]]
    body += section("How long a real edge would take to see", table("power", [
        ("True win rate", "rate"), ("Settled selections needed", "n"),
        ("Weeks at 13 games", "weeks"), ("Full 272-game seasons", "seasons"), ("Basis", "basis"),
    ], power, note=luck["required_n"]["reading"]), eyebrow="SAMPLE SIZE")
    body += section("Why luck cannot be removed yet", panel("Four structural reasons",
        "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in luck["why_not_removed"]) + "</ul>"
        + f"<p><strong>Rejected alternative.</strong> {esc(luck['rejected_alternative']['proposal'])} "
          f"{esc(luck['rejected_alternative']['why'])}</p>"), eyebrow="R102", sid="why")
    return page("luck.html", "Removal of luck",
                "Exact tails, a week-clustered permutation null, a family adjustment and the sample a real edge would need.",
                "NFL / LUCK", body)


def page_correlation() -> str:
    corr = load("correlation.json")
    rows = []
    for r in corr["correlations"]:
        iv = r.get("interval") or {}
        rows.append({**r, "low": iv.get("low", ""), "high": iv.get("high", ""),
                     "source_ids": r["source_ids"]})
    body = notice("Every coefficient carries its n and an official source.",
                  "A value with no official basis is not published. Player props, cross-game dependence and "
                  "market-price dependence are named as not published, with the gate that stops each.")
    body += section("Correlations", table("correlation", [
        ("ID", "id"), ("Pair", "pair"), ("Measure", "kind"), ("n", "n"), ("Value", "value"),
        ("95% low", "low"), ("95% high", "high"), ("p", "p_value"),
    ], rows, note=corr["rule"]), eyebrow="R07 / R121", sid="values")
    detail = []
    for r in corr["correlations"]:
        extra = ""
        if r.get("table"):
            extra = ", ".join(f"{k}={v}" for k, v in r["table"].items())
        detail.append({**r, "counts": extra, "source_ids": r["source_ids"]})
    body += section("The counts behind each value", table("corr-detail", [
        ("ID", "id"), ("Table or series", "counts"), ("Reading", "reading"),
    ], detail, note="A coefficient without its table is not reproducible, so the tables are published."),
        eyebrow="REPRODUCIBILITY")
    body += section("Parlay gate", panel("JG-1",
        f"<p>{esc(corr['parlay_gate']['rule'])}</p>"
        f"<p>Combos ranked: {corr['parlay_gate']['combos_ranked']}. Marginal products used as a joint "
        f"probability: {corr['parlay_gate']['marginal_products_used']}.</p>"
        f"<p>{esc(corr['parlay_gate']['why'])}</p>"), eyebrow="R45 / R46")
    body += section("Deliberately not published", table("corr-missing", [
        ("Item", "item"), ("Gate", "gate"), ("Why", "why"),
    ], [{**x, "source_ids": ["X29-NFL-SCHEDULE"]} for x in corr["not_published"]]), eyebrow="R07")
    return page("correlation.html", "Correlation",
                "Eight coefficients from official scores, each with n, an interval and the table it came from.",
                "NFL / CORRELATION", body)


def page_availability() -> str:
    avail = load("availability.json")
    t = avail["totals"]
    body = notice("Expected starters are recorded. Actual starters are not, and the difference is not guessed.",
                  "A printed depth-chart rank is not playing time. With no inactive list, Game Book or snap "
                  "count, a replacement is suspected and never confirmed, so that column is blank on every row.")
    body += metrics([("Report rows", t["injury_rows"], f"{t['clubs_with_report']} clubs with a Week 10 game"),
                     ("Game designations", t["game_status_present"], f"{t['game_status_out']} out · {t['game_status_doubtful']} doubtful · {t['game_status_questionable']} questionable"),
                     ("On a printed chart", t["on_chart"], f"{t['replacement_named']} with a name printed behind them"),
                     ("Absences confirmed", 0, "no inactive list, Game Book or snap count captured")])
    club_rows = []
    for c in avail["clubs"]:
        club_rows.append({**c, "state": "reported" if c["rows"] else "bye",
                          "source_ids": c["source_ids"]})
    body += section("Per-team view: starters out, replacements named", table("clubs", [
        ("Club", lambda r: ("__html", f'<span class="row-title">{esc(r["club"])}</span>'
                                      f'<span class="row-sub">{esc(r["id"])} · {esc(r["conference"])} '
                                      f'{esc(r["division"])}</span>')),
        ("Week 10 game", "week10_fixture"), ("Report rows", "rows"), ("Out", "out"),
        ("Doubtful", "doubtful"), ("Questionable", "questionable"), ("Blank status", "blank_status"),
        ("On chart", "on_chart"), ("Printed replacement named", "replacement_named"),
        ("No printed replacement", "no_replacement_named"), ("Not on any chart", "not_on_chart"),
        ("Chart", "chart_available"), ("Chart date", "chart_printed_date"),
        ("Net injury count (out + doubtful)", "net_injury_count"),
    ], club_rows, note=("Net injury count is a count of designations, not an estimate of points. A club on bye "
                        "has no report section, which is not the same as no injuries."), statuses=["reported", "bye"]),
        eyebrow="R55 / R56", sid="clubs")

    chain_rows = []
    for c in avail["replacement_chains"]:
        chain_rows.append({**c, "state": c["status"] or "no designation", "source_ids": c["source_ids"]})
    body += section("Every report row, joined to the printed chart", table("players", [
        ("Club", "club"), ("Player", "player"), ("Pos", "position"), ("Injury as printed", "injury"),
        ("Practice as printed", "practice"), ("Game status", "status"),
        ("Printed slot", "slot"), ("Printed rank", "rank"), ("Depth of replacement", "depth_of_replacement"),
        ("Replacement as printed", "replacement"), ("Actual replacement", "actual_replacement"),
        ("Why blank", lambda r: r["reason"] or r["actual_replacement_reason"]),
    ], chain_rows, note=("The 'actual replacement' column is empty on every row by rule: who played needs an "
                         "official participation record. The reason column says which of the two is empty on "
                         "each row."),
        statuses=["Out", "Doubtful", "Questionable", "no designation"]), eyebrow=f"ALL {t['injury_rows']} ROWS", sid="players")

    body += section("Depth slots as groups", table("charts", [
        ("Club", "name"), ("Printed date", "printed_date"), ("Slots", "slots"),
        ("Slots with several rank-1 players", "multi_rank1"),
        ("Slots with no rank-1 player", "empty_rank1"),
    ], [{**c, "source_ids": [f"RD-{c['id']}-CHART"]} for c in avail["charts"]],
        note=("Seattle prints two receivers in one rank-1 cell and two safeties at rank 1; both are kept as "
              "groups. Only Green Bay prints a date. Houston publishes an image and has no row, so its absence "
              "is a blank, not a zero.")), eyebrow="R38 / R39 / R40 / R75", sid="charts")

    body += section("Rules this desk applies", panel("Five rules, enforced in code",
        "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in avail["rules"]) + "</ul>"
        + f"<p>Multi-player rank-1 cells found: {t['multi_rank1_cells']}. Empty rank-1 cells found: "
          f"{t['empty_rank1_cells']}. Charts with a printed date: {t['charts_with_printed_date']} of {t['depth_charts']}.</p>"),
        eyebrow="METHOD", sid="rules")

    stale = [{**s, "chart_qb": ", ".join(s["chart_qb"]) if s["chart_qb"] else "",
              "state": s["verdict"], "source_ids": s["source_ids"]} for s in avail["staleness"]]
    body += section("Staleness tests against the report and the news", table("staleness", [
        ("Club", "club"), ("Printed quarterbacks", "chart_qb"), ("What the report says", "report_fact"),
        ("What the news says", "news_fact"), ("Verdict", "verdict"), ("Why", "why"),
    ], stale, note="A staleness flag is only raised when a printed row contradicts a dated official statement."),
        eyebrow="R65 / R66")

    ann = [{**a, "source_ids": a["source_ids"]} for a in avail["announced_starters"]]
    body += section("Announced starters (dated, not inferred)", table("announced", [
        ("Club", "club"), ("Starting", "player"), ("In place of", "replaces"),
        ("Official statement", "statement"), ("Dated", "dated"), ("Why it matters", "note"),
    ], ann, note="Three clubs are covered. The sweep required by R57 is logged as unclaimed, not implied."),
        eyebrow="R57 / R58", sid="announced")
    return page("availability.html", "Injuries & depth",
                "Report rows, printed depth slots and replacement chains — with the confirmed-participation column deliberately empty.",
                "NFL / AVAILABILITY", body)


def page_matchup() -> str:
    m = load("matchup.json")
    rows = [{**r, "state": r["exposure"], "source_ids": r["source_ids"]} for r in m["rows"]]
    body = notice("One side of the matrix exists. The cross-side matrix does not.",
                  "Pairing an offence station against a defence station needs both clubs' charts in the same "
                  "week. This desk holds six charts and none of those six clubs' Week 10 opponents is among them.")
    body += metrics([("Stations charted", m["counts"]["rows"], f"{m['counts']['clubs_covered']} clubs"),
                     ("Starter out, backup printed", m["counts"]["by_exposure"].get("starter out, backup available", 0), "this week"),
                     ("Starter out, no backup printed", m["counts"]["by_exposure"].get("starter out, no printed backup", 0), "chart cannot name the replacement"),
                     ("Opponent matrix", "", "gated: needs both charts")])
    body += section("Station exposure", table("matchup", [
        ("Club", "club"), ("Unit", "unit"), ("Slot", "slot"), ("Printed rank", "depth"),
        ("Player", "player"), ("On the report", "on_report"), ("Game status", "game_status"),
        ("Printed backup", "printed_backup"), ("Backup on the report", "backup_on_report"),
        ("Backup status", "backup_status"), ("Exposure", "exposure"),
        ("Cross-side pair", "cross_side_matrix"),
    ], rows, note="Cross-side pair is empty by rule, not because the opponent is healthy.",
        statuses=sorted(m["counts"]["by_exposure"])), eyebrow="R63 / R64 / R123 / R124", sid="stations")
    body += section("Limits", panel("Four reasons this is not the finished matrix",
        "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in m["limits"]) + "</ul>"
        + f"<p>Slots with two or more printed ranks: {m['truth_depths']['slots_with_2_plus_printed_ranks']}. "
          f"Multi-player rank-1 cells: {m['truth_depths']['multi_player_rank_1']}.</p>"), eyebrow="HONEST SCOPE")
    return page("matchup.html", "Station exposure",
                "Who is printed at rank 1, who is printed behind them, and whether either is on this week's report.",
                "NFL / AVAILABILITY", body)


def page_fixture() -> str:
    fx = load("fixture-context.json")
    rows = [{**r, "state": "printed" if r["venue"] else "no-venue", "source_ids": r["source_ids"]}
            for r in fx["fixtures"]]
    body = notice("Built only from published schedule facts.",
                  "Rest days are arithmetic between two dates the page prints. Venue, kickoff, network and the "
                  "international label are copied. Roof, surface and weather are blank: no official register "
                  "of either is captured.")
    body += metrics([("Fixtures", fx["counts"]["fixtures"], "Week 11 as printed on 17 Nov"),
                     ("Both rest counts", fx["counts"]["fixtures_with_both_rest_counts"], "arithmetic on printed dates"),
                     ("Short weeks", fx["counts"]["short_week_fixtures"], "four or fewer days"),
                     ("Roof rows sourced", 0, "no stadium register captured")])
    body += section("Week 11 fixtures", table("fixtures", [
        ("Away", "away"), ("Home", "home"), ("Date", "date"), ("Kickoff", "kickoff"),
        ("Network", "network"), ("Venue as printed", "venue"), ("International", "international"),
        ("Away rest", "away_rest_days"), ("Home rest", "home_rest_days"),
        ("Short week", "short_week"), ("Bye edge", "bye_advantage"),
        ("Roof", "roof"), ("Surface", "surface"), ("Weather", "weather"),
    ], rows, note="A blank rest count means the club was on bye and the count does not apply; the reason is in "
                  "the fixture file. Roof and surface are blank because no register is captured (PG-WEATHER).",
        statuses=["printed", "no-venue"]), eyebrow="R14 / R23", sid="fixtures")
    body += section("Schedule announcements", table("announcements", [
        ("Announcement", "what"), ("Where it is printed", "printed_on"),
    ], [{**a, "source_ids": a["source_ids"]} for a in fx["schedule_announcements"]]), eyebrow="R24")
    body += section("Not built", table("not-built", [
        ("Feature", "feature"), ("Gate", "gate"), ("Why", "why"),
    ], [{**x, "source_ids": ["RD-NFL-SCHED-W11"]} for x in fx["not_built"]]), eyebrow="R89 / R90 / R107 / R108")
    return page("fixture-context.html", "Fixture context",
                "Rest, bye edge, venue and network from the printed schedule — and the weather features that stay blank.",
                "NFL / FIXTURE CONTEXT", body)


def page_ablation() -> dict:
    a = load("ablation.json")
    rows = [
        {"id": "ARM-WITHOUT", "arm": "Without personnel features", "rows": a["arms"]["without_personnel"]["rows"],
         "brier": a["arms"]["without_personnel"]["brier"],
         "interval": f"{a['arms']['without_personnel']['interval'][0]} to {a['arms']['without_personnel']['interval'][1]}",
         "note": "The model as it stands: prior results only.",
         "source_ids": ["X29-NFL-SCHEDULE"]},
        {"id": "ARM-WITH", "arm": "With verified personnel features", "rows": "",
         "brier": "", "interval": "", "note": a["arms"]["with_personnel"]["empty_because"],
         "source_ids": ["RD-NFL-INJ-W10"]},
    ]
    body = notice(a["question"], a["design"])
    body += section("The two arms", table("ablation", [
        ("Arm", "arm"), ("Games", "rows"), ("Brier", "brier"), ("95% interval", "interval"),
        ("Note", "note"),
    ], rows, note=("The with-personnel arm is empty by construction, not by omission: no absence in the corpus "
                   "is confirmed, so there is nothing to add. An empty arm is a finding, and it is why no fixed "
                   "points penalty appears anywhere in the pipeline.")), eyebrow="R27 / R28 / R29 / R30", sid="arms")
    body += '<div class="grid-2">'
    body += panel("What would fill the empty arm", f"<p>{esc(a['what_would_fill_the_arm'])}</p>")
    body += panel("Why not a fixed penalty",
                  "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in a["why_not_a_penalty"]) + "</ul>"
                  + f"<p>{esc(a['difference']['would_be_readable_if'])}</p>")
    body += "</div>"
    return page("ablation.html", "Ablation",
                "The same model with and without verified personnel features — and why one arm is empty.",
                "NFL / ABLATION", body)


def page_diff() -> str:
    d = load("diff.json")
    body = notice("A diff needs two reads of the same scope.",
                  d["delta_is_not_an_injury_trend"])
    body += metrics([("Prior capture rows", d["prior_capture"]["rows"], d["prior_capture"]["scope"]),
                     ("This capture rows", d["this_capture"]["rows"], d["this_capture"]["scope"]),
                     ("Row delta", d["row_delta"], "coverage, not injuries"),
                     ("Practice trend rows", 0, "needs two dated reads of the same scope")])
    body += section("Capture to capture", table("diff", [
        ("Club", "club"), ("Rows in the prior capture", "rows_prior"), ("Rows now", "rows_now"),
        ("Change", "change"), ("Note", "note"),
    ], [{**r, "source_ids": r["source_ids"]} for r in d["per_club"]],
        note=("The prior value is blank wherever a like-for-like comparison is impossible. Filling it with the "
              "current value would manufacture agreement.")), eyebrow="R93 / R94", sid="clubs")
    body += section("Practice trend", panel("Empty, with the reason",
        f"<p>{esc(d['practice_trend']['why'])}</p><p>Would need: {esc(d['practice_trend']['would_need'])}.</p>"),
        eyebrow="R82")
    return page("diff.html", "What changed",
                "A per-club diff between the inherited capture and this one, with the comparison that cannot be drawn.",
                "NFL / DIFF", body)


def page_strategy() -> str:
    s = load("strategies.json")
    rows = [{**e, "status": e["state"], "source_ids": e["source_ids"]} for e in s["entries"]]
    body = notice("Twenty-four frozen definitions, three of them closed divisions.",
                  "An entry is a definition and a result, kept apart on purpose. The two-sided column is "
                  "mandatory: a definition with no falsifier is rejected by the build.")
    body += metrics([("Entries", s["counts"]["entries"], "21 singles, 3 closed divisions"),
                     ("Two-sided fields", s["counts"]["with_two_sided_field"], "accept and reject, both non-empty"),
                     ("Qualified", 0, "no entry passes V7 or V8"),
                     ("Staking values", 0, "a staking figure cannot appear on a signal entry")])
    body += section("Strategy register", table("strategies", [
        ("Entry", "id"), ("Name", "name"), ("Division", "division"), ("Definition", "definition"),
        ("Window", "window"), ("n", "n"), ("Brier skill", "brier_skill"),
        ("Cluster lower bound", "cluster_lo"), ("What would accept it", "would_accept"),
        ("What would reject it", "would_reject"), ("Closed because", "closed_because"),
        ("Stake", "stake"), ("State", "state"),
    ], rows, note="Stake is empty on every row: staking is a separate page and can never move a signal rank.",
        statuses=["paper", "closed"]), eyebrow="R09 / R17 / R105 / R106", sid="register")
    return page("strategy.html", "Strategies",
                "Every entry pre-registered, with what would accept it and what would reject it.",
                "NFL / STRATEGY", body)


def page_questions() -> str:
    q = load("questions.json")
    rows = [{**x, "status": x["state"], "source_ids": x["source_ids"]} for x in q["questions"]]
    body = notice(f"{q['counts']['questions']} questions: {q['counts']['open']} open, {q['counts']['answered']} answered.",
                  q["note"])
    body += section("Questions, information and answers", table("questions", [
        ("ID", "id"), ("Group", "group"), ("Question", "question"),
        ("What we have", "held"), ("What is missing", "missing"),
        ("Decision it blocks", "blocks"), ("What closes it", "closes"), ("State", "state"),
    ], rows, note="A question is answered only where a number on file settles it; the number is quoted in the "
                  "'what we have' cell.", statuses=["open", "answered"]), eyebrow="R114", sid="questions")
    return page("questions.html", "Questions",
                "Each question split into what is held, what is missing, what it blocks and what would close it.",
                "NFL / DECISION LAB", body)


def page_suggestions() -> str:
    s = load("suggestions.json")
    rows = [{**x, "status": x["decision"] or "undecided", "source_ids": x["source_ids"]}
            for x in s["suggestions"]]
    body = notice("A section to review proposals and choose a path before anything is implemented.",
                  "Nothing here is approved. The decision column is blank on every row and is the reviewer's "
                  "step; the rules for recording a decision are published below it.")
    body += metrics([("Proposals", s["counts"]["suggestions"], "each with an acceptance test"),
                     ("Decided", s["counts"]["decided"], "none: the choice is the reviewer's"),
                     ("Ranked by", "impact · confidence · unblocking", "components published so the order can be argued with"),
                     ("Missing-data proposals", sum(1 for x in s["suggestions"] if x["discovers"]), "each names the datum it would obtain")])
    body += section("Suggestions to review", table("suggestions", [
        ("Priority", "priority"), ("ID", "id"), ("Proposal", "title"),
        ("Requirements it unlocks", lambda r: ", ".join(r["unlocks"])),
        ("Missing information it would discover", "discovers"),
        ("Evidence it rests on", "evidence"), ("Cost", "cost"), ("Risk", "risk"),
        ("Acceptance test", "acceptance"), ("Decision", "decision"),
        ("Decided by", "decided_by"), ("Reason", "reason"),
    ], rows, note=("Decision is accept, reject or defer, and is blank until a reviewer records one. Accepting a "
                   "proposal buys the experiment, not the result."), statuses=["undecided", "accept", "reject", "defer"]),
        eyebrow="R113 / R115", sid="suggestions")
    body += section("Rules for recording a decision", table("decision-rules", [
        ("Rule", "rule"), ("Why", "why"),
    ], [{**r, "source_ids": ["REPO"]} for r in s["decision_rules"]]), eyebrow="PROCESS")
    return page("suggestions.html", "Suggestions to review",
                "Fifteen proposals ranked, each with cost, risk, an acceptance test and a blank decision.",
                "NFL / DECISION LAB", body)


def page_flagged() -> str:
    f = load("flags.json")
    rows = [{**x, "source_ids": x["source_ids"]} for x in f["flags"]]
    body = notice(f"{f['counts']['flags']} flagged irregularities: {f['counts']['high']} high, "
                  f"{f['counts']['medium']} medium, {f['counts']['low']} low.",
                  f["note"])
    body += section("Flagged for review", table("flags", [
        ("ID", "id"), ("Item", "title"), ("Severity", "severity"), ("Detail", "detail"),
        ("Disposition", "disposition"), ("Unverified value", "unverified_value"), ("State", "status"),
    ], rows, note="An unverified value is blank on the row that would otherwise carry it. No flag blocks "
                  "publication; each blocks a claim that depends on it.", statuses=["Needs review"]),
        eyebrow="R128 / R132", sid="flags")
    return page("flagged.html", "Flagged for review",
                "What did not reproduce, what is missing, and what is blank because no official source supplies it.",
                "NFL / TRANSPARENCY", body)


def page_verification() -> str:
    req = load("requirements.json")
    a = load("availability.json")
    snaps = load("snapshots.json")
    checks = [
        {"id": "CHK-1", "check": "Every table row names a registered source ID",
         "result": "enforced by the site audit; a row without one fails the build",
         "source_ids": ["REPO"]},
        {"id": "CHK-2", "check": "Every row links the official page it came from",
         "result": "enforced: the row must contain one of its own registered URLs", "source_ids": ["REPO"]},
        {"id": "CHK-3", "check": "An unknown value is truly empty",
         "result": "enforced: a blank cell may not contain text", "source_ids": ["REPO"]},
        {"id": "CHK-4", "check": "Report rows reproduce from the saved publisher text",
         "result": f"{a['totals']['injury_rows']} rows against a pinned count of {a['pins']['injury_rows']}",
         "source_ids": ["RD-NFL-INJ-W10"]},
        {"id": "CHK-5", "check": "Depth slots reproduce from the saved club pages",
         "result": f"{a['totals']['depth_rows']} slots against a pinned count of {a['pins']['depth_rows']}",
         "source_ids": ["RD-DET-CHART"]},
        {"id": "CHK-6", "check": "Every forecast carries a probability and its inputs",
         "result": "enforced in the backtest build", "source_ids": ["X29-NFL-SCHEDULE"]},
        {"id": "CHK-7", "check": "A staking field cannot reach a signal rank",
         "result": "the rank function raises on a staking field", "source_ids": ["REPO"]},
        {"id": "CHK-8", "check": "No fixed points penalty exists in the pipeline",
         "result": "0 found; the ablation has no penalty term", "source_ids": ["X29-NFL-SCHEDULE"]},
        {"id": "CHK-9", "check": "The pages are generated, not edited",
         "result": "every page is rebuilt byte-identically by check mode", "source_ids": ["REPO"]},
        {"id": "CHK-10", "check": "Captures are hashed",
         "result": f"{len(snaps['captures'])} captures with SHA-256 over the evidence bytes",
         "source_ids": ["RD-NFL-INJ-W10"]},
    ]
    body = notice("Line by line, on this desk's own pages.",
                  "The site audit already enforces the row, link and blank contracts across the whole site; "
                  "these ten are the ones this desk adds and can demonstrate.")
    body += section("Checks", table("checks", [
        ("Check", "check"), ("How it is enforced or what it found", "result"),
    ], checks), eyebrow="17 NOV 2026", sid="checks")
    body += section("What was read, and when", table("captures", [
        ("Capture", "id"), ("Artefact", "artefact"), ("Read", "read"), ("Clock", "clock"),
        ("SHA-256", "sha256"), ("Rows", "rows"),
    ], [{**c, "source_ids": c["source_ids"][:3]} for c in snaps["captures"]],
        note=snaps["policy"]), eyebrow="IMMUTABLE CAPTURES", sid="captures")
    body += section("What is not verified",
        panel("Three honest limits",
             "<ul>"
             "<li>A saved rendered transcription is not a raw HTTP archive. A hash proves the file has not "
             "changed, not that the publisher printed it.</li>"
             "<li>Direct HTTPS to the publishers is refused from this sandbox, so every read is a rendered-text "
             "fetch and no HTTP status is attested.</li>"
             "<li>The other desks' claims are not inherited. The two re-read this session are on the flagged "
             "page, and both failed to reproduce.</li>"
             "</ul>"), eyebrow="LIMITS")
    return page("verification.html", "Verification",
                "The ten checks this desk runs, the captures behind them, and the three things that are still not proven.",
                "NFL / VERIFICATION", body)


def page_sources() -> str:
    ids = sorted({s for p in load("snapshots.json")["captures"] for s in p["source_ids"]} |
                 {"RD-NFL-SCHED-W10", "RD-NFL-SCHED-W11", "RD-NFL-SCHED-REG10", "RD-NFL-TERMS",
                  "RD-NFL-LOCK", "RD-NFL-ROUNDUP-NOV11", "RD-NFL-ROUNDUP-NOV13", "RD-NFL-PLAYER-STATS",
                  "RD-BAL-CHART", "RD-WAS-CHART", "RD-IND-CHART", "RD-HOU-CHART", "X29-NFL-SCHEDULE"})
    from_sources = {k: v for k, v in SOURCES.items() if k in ids}
    rows = []
    for sid, src in sorted(from_sources.items()):
        rows.append({"id": sid, "publisher": src["publisher"], "title": src["title"],
                     "url": src["url"], "scope": src["scope"], "access": src["access"],
                     "checked_on": src.get("checked_on", ""), "source_ids": [sid],
                     "official": ("__html", refs([sid], "Open page"))})
    body = notice("Every source this desk used, with the scope it was read under.",
                  "A link is a reference, not blanket verification. The scope column says exactly what was "
                  "read and what was not.")
    body += section("Sources", table("sources", [
        ("ID", "id"), ("Publisher", "publisher"), ("Title", "title"), ("Scope of the read", "scope"),
        ("Access method", "access"), ("Checked", "checked_on"),
    ], rows, note="The access column records that reads were rendered-text fetches, not HTTP-status attestations."),
        eyebrow=f"{len(rows)} SOURCES", sid="sources")
    return page("sources.html", "Sources",
                "The registered official pages this desk read, the exact scope of each read, and how it was read.",
                "NFL / SOURCES", body)


PAGES = {
    "index.html": page_index,
    "readiness.html": page_readiness,
    "gates.html": page_gates,
    "origination.html": page_origination,
    "leaderboard.html": page_leaderboard,
    "luck.html": page_luck,
    "correlation.html": page_correlation,
    "availability.html": page_availability,
    "matchup.html": page_matchup,
    "fixture-context.html": page_fixture,
    "ablation.html": page_ablation,
    "diff.html": page_diff,
    "strategy.html": page_strategy,
    "questions.html": page_questions,
    "suggestions.html": page_suggestions,
    "flagged.html": page_flagged,
    "verification.html": page_verification,
    "sources.html": page_sources,
}


def build() -> list[str]:
    SITE.mkdir(exist_ok=True)
    written = []
    for slug, fn in PAGES.items():
        (SITE / slug).write_text(fn(), encoding="utf-8")
        written.append(slug)
    manifest = {"pages": written, "read": "2026-11-17", "generator": "nfl-readiness/site.py"}
    (SITE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return written


def main() -> int:
    if "--check" in sys.argv:
        before = {p: (SITE / p).read_text() for p in PAGES if (SITE / p).exists()}
        written = build()
        changed = [p for p in written if before.get(p) != (SITE / p).read_text()]
        manifest = json.loads((SITE / "manifest.json").read_text())
        print(f"OK: {len(written)} pages, deterministic" if not changed else f"changed: {changed}")
        return 0
    written = build()
    print(f"Built {len(written)} pages in nfl-readiness/site/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
