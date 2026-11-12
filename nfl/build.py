#!/usr/bin/env python3
"""Deterministic builder for the NFL research sub-site.

No network is used. All content comes from data/nfl-*.csv + research/nfl-*.json;
every table row carries registered official source IDs and links. Blank cells
stay truly blank (unverified values are never filled in). `--check` verifies
committed output.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
MANIFEST = ROOT / "manifest.json"

PAGES = [
    "index.html",
    "executive-summary.html",
    "requirements.html",
    "data.html",
    "signals.html",
    "lines.html",
    "correlation.html",
    "injuries.html",
    "validation.html",
    "leaderboard.html",
    "suggestions.html",
    "questions.html",
    "sources.html",
    "review.html",
    "independent-verification.html",
    "methodology.html",
]

NAV = [
    ("index.html", "Overview"),
    ("executive-summary.html", "Executive summary"),
    ("requirements.html", "Requirements"),
    ("data.html", "Data library"),
    ("signals.html", "Signal library"),
    ("lines.html", "Probability lab"),
    ("correlation.html", "Correlation"),
    ("injuries.html", "Injuries & backups"),
    ("validation.html", "Validation gates"),
    ("leaderboard.html", "Leaderboard"),
    ("suggestions.html", "Suggestions"),
    ("questions.html", "Questions & answers"),
    ("sources.html", "Sources"),
    ("review.html", "Flagged for Review"),
    ("independent-verification.html", "Independent verification"),
    ("methodology.html", "Methodology"),
]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_json_repo(relative: str):
    return json.loads((REPO / relative).read_text(encoding="utf-8"))


def load_csv_repo(relative: str):
    with (REPO / relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def src_urls():
    registry = load_json_repo("research/sources.json")
    return {s["id"]: s["url"] for s in registry}


def refs_cell(source_ids, urls):
    links = " ".join(
        f'<a href="{esc(urls[s])}" title="{esc(s)}" target="_blank" rel="noopener noreferrer">{esc(s)} &#8599;</a>'
        for s in source_ids
    )
    return f'<td class="refs">{links}</td>'


def cell(row, key):
    if key not in row or row[key] is None:
        return "<td></td>"
    value = row[key]
    if value == "":
        status = row.get("status", "")
        label = f"Blank - {status}" if status else "Blank - not supplied"
        return f'<td class="blank" data-empty="true" aria-label="{esc(label)}" title="{esc(label)}"></td>'
    return f"<td>{esc(value)}</td>"


def table(table_id, caption, columns, rows, urls):
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h, _ in columns)
    head += '<th scope="col">Sources / references</th>'
    body = []
    for i, row in enumerate(rows):
        rid = row.get("id", f"row-{i}")
        cells = "".join(cell(row, key) for _, key in columns)
        body.append(
            f'<tr data-row-id="{esc(rid)}" data-source-ids="{esc(" ".join(row["source_ids"]))}">'
            + cells + refs_cell(row["source_ids"], urls) + "</tr>"
        )
    return (
        f'<div class="table-scroll" role="region" aria-label="{esc(caption)}" tabindex="0">'
        f'<table id="{esc(table_id)}"><caption class="sr-only">{esc(caption)}. Blank cells are intentional; sources are supplied per row.</caption>'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def page(slug, title, lead, body):
    nav_items = []
    for href, label in NAV:
        current = ' aria-current="page"' if href == slug else ""
        nav_items.append(f'<a href="{href}"{current}>{esc(label)}</a>')
    nav = "".join(nav_items)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="OWN7 NFL research: source-linked observations, exploratory models, validation and transparent limitations. Checked 2026-11-12.">
<title>{esc(title)} | NFL research</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip-link" href="#main-content">Skip to content</a>
<header class="site-header">
<div class="topline">
<a class="brand" href="index.html">OWN7 · NFL RESEARCH LAB</a>
<nav aria-label="NFL research sections">{nav}<a href="../index.html">Main site &#8599;</a></nav>
</div>
</header>
<main id="main-content">
<div class="page-heading">
<p class="eyebrow">NFL / RESEARCH WORKSPACE</p>
<h1>{esc(title)}</h1>
<p class="lead">{esc(lead)}</p>
</div>
{body}
</main>
<footer class="site-footer">
<p><strong>OWN7</strong> / independent research · checked 2026-11-12 · not legal advice · <a href="review.html">Flagged for Review</a> · <a href="sources.html">Sources</a> · <a href="../index.html">Main site</a></p>
</footer>
</body>
</html>
"""


def cards():
    items = [
        ("executive-summary.html", "Executive summary", "The important details and decision in one place, with sources."),
        ("requirements.html", "Requirements", "Scope, evidence and remaining work for every NFL requirement."),
        ("data.html", "Data library", "216 verified rows across 7 datasets. Every row source-linked."),
        ("signals.html", "Signal library", "Eight NFL hypotheses: singles, parlays and prop combos. None proven."),
        ("correlation.html", "Correlation", "Descriptive cross-sectional estimates. Bet-leg correlations blank."),
        ("injuries.html", "Injuries & backups", "Official injury tracker with blank replacements/deficiencies."),
        ("validation.html", "Validation gates", "Ten fail-closed gates. No candidate passes."),
        ("leaderboard.html", "Leaderboard", "Empty by design. Non-monetary merit points only."),
        ("suggestions.html", "Suggestions", "Twelve proposals for review. Nothing implemented without approval."),
        ("questions.html", "Questions & answers", "Fifteen questions with have/lack/discover. Answers blank unless verified."),
        ("review.html", "Flagged for Review", "Eleven flags published blank for manual review."),
    ]
    return '<div class="cards">' + "".join(
        f'<a class="card" href="{href}"><h2>{esc(t)}</h2><p>{esc(d)}</p><span class="card-link">Open &rarr;</span></a>'
        for href, t, d in items
    ) + "</div>"


def metrics(urls):
    items = [
        ("Verified NFL rows", "216", "7 datasets, source-linked", "NFL-STANDINGS"),
        ("Research hypotheses", "8", "Singles, parlays & prop combos", "NFL-PASSING"),
        ("Descriptive correlations", "7", "Cross-sectional, not bet-leg", "NFL-TEAM-OFF"),
        ("Strategies approved", "0", "No live lines or cash awards", "NFL-TERMS"),
    ]
    return '<div class="metric-grid">' + "".join(
        f'<div class="metric"><div class="metric-label">{esc(a)}</div><div class="metric-value">{esc(b)}</div>'
        f'<p class="metric-note">{esc(c)} · <a href="{esc(urls[s])}" target="_blank" rel="noopener noreferrer">{esc(s)} &#8599;</a></p></div>'
        for a, b, c, s in items
    ) + "</div>"


def render():
    urls = src_urls()
    catalog = load_json_repo("research/nfl-catalog.json")
    protocol = load_json_repo("research/nfl-protocol.json")
    results = load_json_repo("research/nfl-results.json")
    requirements = load_json_repo("research/nfl-requirements.json")
    sugg = load_json_repo("research/nfl-suggestions.json")
    ques = load_json_repo("research/nfl-questions.json")

    standings = load_csv_repo("data/nfl-standings-2026.csv")
    passing = load_csv_repo("data/nfl-players-passing-2026.csv")
    rushing = load_csv_repo("data/nfl-players-rushing-2026.csv")
    receiving = load_csv_repo("data/nfl-players-receiving-2026.csv")
    off = load_csv_repo("data/nfl-team-offense-passing-2026.csv")
    dfn = load_csv_repo("data/nfl-team-defense-passing-2026.csv")
    injuries = load_csv_repo("data/nfl-injuries-week7-2026.csv")

    for rows, sid in [(standings, "NFL-STANDINGS"), (passing, "NFL-PASSING"), (rushing, "NFL-RUSHING"), (receiving, "NFL-RECEIVING"), (off, "NFL-TEAM-OFF"), (dfn, "NFL-TEAM-DEF"), (injuries, "NFL-INJURY")]:
        for r in rows:
            r["source_ids"] = [sid]
            r["id"] = r.get("Team") or r.get("Player") or r.get("Game", "") + "-" + r.get("Player", "")

    pages = {}

    # Landing
    landing = (
        '<div class="notice warning"><strong>Evidence is available. A betting edge is not.</strong><p>216 official snapshot rows checked; seven descriptive correlations calculated. No strategy has cleared all validation gates. Source rights and market-data gaps block betting-price release.</p></div>'
        + metrics(urls) + cards()
        + "<section><h2>What this project covers</h2><p>An evidence-first workspace for independent NFL probability research. Observe carefully. Test honestly. Know when not to act.</p>"
        + '<p><strong>Rights:</strong> NFL Terms restrict Services to non-commercial/informational use and prohibit gambling/wagering use. This lab is a frozen, attributed statistical audit only. No executable line, odds, ROI, CLV, cash prize or wagering signal is released.</p></section>'
        + table("landing-strategies", "Research queue", [("Strategy", "name"), ("Category", "category"), ("Status", "status")], catalog["strategies"], urls)
    )
    pages["index.html"] = page("index.html", "NFL research overview", "An evidence-first workspace for independent NFL probability research. Observe carefully. Test honestly. Know when not to act.", landing)

    pages["requirements.html"] = page("requirements.html", "NFL requirements", "A transparent ledger of delivered work, partial features and blocked decisions.", table("requirements", "NFL requirements", [("ID", "id"), ("Requirement", "requirement"), ("Status", "status"), ("Evidence and limitations", "evidence")], requirements["requirements"], urls))

    # Executive summary
    findings = [
        {"id": "E1", "finding": "Decision: no live lines", "detail": "Do not release live NFL betting lines or assert a skill-based edge. No candidate passes all gates.", "status": "Project decision", "source_ids": ["NFL-TERMS"]},
        {"id": "E2", "finding": "Standings leader", "detail": "Buffalo and San Francisco lead at 7-1 (.875); Chargers 0-8 (.000). 32 rows checked.", "status": "Verified · official", "source_ids": ["NFL-STANDINGS"]},
        {"id": "E3", "finding": "Passing leader", "detail": "Jordan Love 2,618 yards leads top-25 passing table. Subset, not universe.", "status": "Verified · official", "source_ids": ["NFL-PASSING"]},
        {"id": "E4", "finding": "Team offense headers", "detail": "Header labels were not rendered. Columns are positional; named team-offense comparisons are withheld (NF11).", "status": "Unverified · review", "source_ids": ["NFL-TEAM-OFF"]},
        {"id": "E5", "finding": "Team defense leader", "detail": "Minnesota allows fewest at 1,495 pass yards (32 teams).", "status": "Verified · official", "source_ids": ["NFL-TEAM-DEF"]},
        {"id": "E6", "finding": "Correlations descriptive", "detail": "Seven cross-sectional estimates (e.g. W vs Net Pts r=0.846). Not bet-leg, not predictive.", "status": "Derived · descriptive", "source_ids": ["NFL-STANDINGS"]},
        {"id": "E7", "finding": "Injuries bounded", "detail": "45 rows (NE, CHI, PIT, NO). Replacements/deficiencies blank.", "status": "Verified · official", "source_ids": ["NFL-INJURY"]},
        {"id": "E8", "finding": "Leaderboard empty", "detail": "No eligible entries. Non-monetary merit points only. Cash blank.", "status": "Project policy", "source_ids": ["NFL-TERMS"]},
    ]
    exec_body = (
        '<div class="notice warning"><strong>Bottom line:</strong> no verified betting edge, executable NFL line, ROI, CLV, cash prize or winning strategy is claimed. Blank values are intentional. Luck cannot be removed.</div>'
        + table("exec-findings", "Executive findings", [("Finding", "finding"), ("Detail", "detail"), ("Evidence class", "status")], findings, urls)
        + '<div class="notice"><strong>What the project does:</strong><p>Preserves source scope, verifies retained observations, calculates descriptive statistics, documents eight model contracts and ten gates, and rejects unsupported leaderboard entries.</p></div>'
        + '<div class="notice"><strong>What it does not establish:</strong><p>No skill-based wagering edge, actual historical pregame availability, operator permission, current offer, correctly priced multi-leg bet or future profit.</p></div>'
    )
    pages["executive-summary.html"] = page("executive-summary.html", "Executive summary", "The important findings, verified observations, research progress and non-negotiable limits — in one place.", exec_body)

    # Data library
    data_body = (
        '<div class="notice"><strong>Snapshot verification is not a data license.</strong><p>These are attributed, frozen statistical-audit observations from NFL.com, checked 2026-11-12. No live prices or gambling-use permission is inferred.</p></div>'
        + table("standings", "Standings 2026 (32 teams)", [("Team", "Team"), ("W", "W"), ("L", "L"), ("T", "T"), ("PCT", "PCT"), ("PF", "PF"), ("PA", "PA"), ("Net", "NetPts"), ("Home", "Home"), ("Road", "Road"), ("Div", "Div"), ("Conf", "Conf"), ("Strk", "Strk"), ("Last 5", "Last5")], standings, urls)
        + table("passing", "Player passing top 25", [("Player", "Player"), ("Pass Yds", "PassYds"), ("Yds/Att", "YdsPerAtt"), ("Att", "Att"), ("Cmp", "Cmp"), ("Cmp %", "CmpPct"), ("TD", "TD"), ("INT", "INT"), ("Rate", "Rate")], passing, urls)
        + table("rushing", "Player rushing top 25 (positional)", [("Player", "Player"), ("C1", "C1"), ("C2", "C2"), ("C3", "C3"), ("C4", "C4"), ("C5", "C5"), ("C6", "C6"), ("C7", "C7"), ("C8", "C8"), ("C9", "C9")], rushing, urls)
        + '<p class="table-note">Rushing/receiving headers were not rendered in the fetched page. C1-C9 are positional only; meanings are not asserted (NF08).</p>'
        + table("receiving", "Player receiving top 25 (positional)", [("Player", "Player"), ("C1", "C1"), ("C2", "C2"), ("C3", "C3"), ("C4", "C4"), ("C5", "C5"), ("C6", "C6"), ("C7", "C7"), ("C8", "C8"), ("C9", "C9")], receiving, urls)
        + table("team-off", "Team offense passing (32 teams; positional)", [("Team", "Team")] + [(f"C{i}", f"C{i}") for i in range(1, 16)], off, urls)
        + table("team-def", "Team defense passing (32 teams)", [("Team", "Team"), ("Att", "Att"), ("Cmp", "Cmp"), ("Cmp %", "CmpPct"), ("Yds/Att", "YdsPerAtt"), ("Yds", "Yds"), ("TD", "TD"), ("INT", "INT"), ("Rate", "Rate")], dfn, urls)
    )
    pages["data.html"] = page("data.html", "Data library", "Seven frozen official-source datasets. Every retained row is attributed, scoped and checked; nothing here is a live market feed.", data_body)

    # Signals
    sig_body = (
        '<div class="notice"><strong>Hypotheses are project research designs.</strong><p>NFL and method links identify inputs/references, not evidence of profitability. No fitted team model or live projection is claimed.</p></div>'
        + table("strategies", "Signal library", [("Strategy", "name"), ("Category", "category"), ("Hypothesis", "hypothesis"), ("Output", "output"), ("Risk", "risk"), ("Status", "status")], catalog["strategies"], urls)
    )
    pages["signals.html"] = page("signals.html", "Signal library", "Eight testable research hypotheses across singles, parlays and player-prop combinations. None is a proven edge.", sig_body)

    # Lines (probability lab — generic math only)
    lines_body = (
        '<div class="notice warning"><strong>No NFL lines are originated here.</strong><p>Generic pricing identities are documented; related mathematical primitives are tested on synthetic inputs. NFL-derived betting prices are withheld under the source-rights gate.</p></div>'
        + "<section><h2>Generic pricing identities</h2><p>For decimal odds <em>d &gt; 1</em>, implied probability is <em>1/d</em>. No-push fair odds are <em>1/p</em>; with push probability <em>q</em>, fair odds are <em>(1-q)/p</em>, undefined when <em>p=0</em>. Per-unit expected net return is <em>p_win*(d-1) - p_lose</em>.</p>"
        + "<p>A proportional de-vig convention normalizes reciprocal odds over a <strong>complete mutually exclusive outcome set</strong> from the same operator, line, timestamp and settlement contract. It is a modeling convention, not true-probability identification.</p>"
        + "<p>A parlay uses the actual joint event probability and actual operator combined quote. Product-of-probabilities requires full independence; product-of-odds is not a universal same-game payout rule.</p></section>"
        + table("lines-empty", "NFL lines (withheld)", [("Market", "market"), ("Line", "line"), ("Model p", "p_model"), ("ROI", "roi"), ("CLV", "clv")], [{"id": "L1", "market": "Single bets", "line": "", "p_model": "", "roi": "", "clv": "", "status": "Withheld · blank", "source_ids": ["NFL-TERMS"]}, {"id": "L2", "market": "Parlays", "line": "", "p_model": "", "roi": "", "clv": "", "status": "Withheld · blank", "source_ids": ["NFL-TERMS"]}, {"id": "L3", "market": "Player props / combos", "line": "", "p_model": "", "roi": "", "clv": "", "status": "Withheld · blank", "source_ids": ["NFL-TERMS"]}], urls)
    )
    pages["lines.html"] = page("lines.html", "Probability lab", "Generic pricing mathematics only. Calculated probabilities — not official forecasts, market lines or evidence of skill.", lines_body)

    # Correlation
    corr_rows = []
    for c in results["correlations"]:
        corr_rows.append({"id": c["pair"], "pair": c["pair"], "n": str(c["n"]) if c["n"] is not None else "", "pearson": f"{c['pearson']:.4f}" if c["pearson"] is not None else "", "spearman": f"{c['spearman']:.4f}" if c["spearman"] is not None else "", "kind": c["kind"], "status": c["status"], "source_ids": c["source_ids"]})
    corr_body = (
        '<div class="notice"><strong>Descriptive only.</strong><p>Cross-sectional correlations describe the snapshot. They are not bet-leg correlations and not predictive. Bet-leg rows are blank — no game logs collected.</p></div>'
        + table("correlations", "Correlations", [("Pair", "pair"), ("n", "n"), ("Pearson r", "pearson"), ("Spearman", "spearman"), ("Kind", "kind"), ("Status", "status")], corr_rows, urls)
    )
    pages["correlation.html"] = page("correlation.html", "Correlation", "Replace correlation stories with paired measurements and honest uncertainty — not assumed dependence.", corr_body)

    # Injuries
    inj_body = (
        '<div class="notice"><strong>Tracker design.</strong><p>Official injury status is recorded verbatim. Replacement players (2nd/3rd/4th string) and quantified deficiencies are <strong>blank</strong> — the injury page does not state them, and rosters were not transcribed. No deficiency is asserted without evidence.</p></div>'
        + "<section><h2>How deficiencies would be measured (once data exist)</h2><ol><li>Map each Out/Doubtful starter to the official depth chart (2nd/3rd/4th string).</li><li>Compare team offense/defense efficiency with vs without the starter (game logs required).</li><li>Quantify with uncertainty; abstain when the replacement is unknown.</li></ol></section>"
        + table("injuries", "Injury tracker — Week 7 bounded (45 rows)", [("Game", "Game"), ("Team", "Team"), ("Player", "Player"), ("Pos", "Position"), ("Injuries", "Injuries"), ("Practice", "PracticeStatus"), ("Game status", "GameStatus"), ("Replacement", "Replacement"), ("Deficiency", "Deficiency")], injuries, urls)
    )
    pages["injuries.html"] = page("injuries.html", "Injuries & backups", "Official injury tracker. Replacements and deficiencies stay blank until officially confirmed.", inj_body)

    # Validation
    val_body = (
        '<div class="notice"><strong>Evidence earns eligibility.</strong><p>Missing data, source restrictions and inconclusive tests never count as a pass. No current candidate passes all applicable gates.</p></div>'
        + table("gates", "Validation gates", [("Gate", "name"), ("Pass rule", "pass_rule"), ("Current", "current"), ("Status", "status")], catalog["gates"], urls)
    )
    pages["validation.html"] = page("validation.html", "Validation gates", "Evidence earns eligibility. Missing data, source restrictions and inconclusive tests never count as a pass.", val_body)

    # Leaderboard
    lb_body = (
        '<div class="notice"><strong>Reward qualified evidence, not a hot streak.</strong><p>Separate divisions, frozen rules and no fictional winners. Current leaderboard: empty.</p></div>'
        + table("leaderboard", "Leaderboard", [("Strategy", "name"), ("Category", "category"), ("Rank", "rank"), ("Merit points", "merit"), ("Cash", "cash")], [{"id": "LB-EMPTY", "name": "No eligible entries", "category": "All", "rank": "", "merit": "", "cash": "", "status": "Empty · blank", "source_ids": ["NFL-TERMS"]}], urls)
        + "<section><h2>Competition rules</h2><p>Primary score: lower 95% date-block-bootstrap bound on net return per unit staked. Tie-breaks: lower log loss, earlier frozen_at, strategy_id. Rewards: non-transferable, non-monetary merit points (3/2/1). Cash pool: blank. Entry fee: 0. Cash payments: disabled.</p></section>"
    )
    pages["leaderboard.html"] = page("leaderboard.html", "Leaderboard", "Reward qualified evidence, not a hot streak. Separate divisions, frozen rules and no fictional winners.", lb_body)

    # Suggestions
    sugg_rows = []
    for s in sugg["suggestions"]:
        sugg_rows.append({"id": s["id"], "title": s["title"], "proposal": s["proposal"], "rationale": s["rationale"], "missing_info": s["missing_info"], "decision_needed": s["decision_needed"], "status": s["status"], "source_ids": s["source_ids"]})
    sugg_body = (
        '<div class="notice"><strong>Review before implementing.</strong><p>No suggestion is implemented until a reviewer records an Approved decision in the ledger. This static page displays the queue; it has no approval control.</p></div>'
        + table("suggestions", "Suggestions for review", [("ID", "id"), ("Title", "title"), ("Proposal", "proposal"), ("Rationale", "rationale"), ("Missing info", "missing_info"), ("Decision needed", "decision_needed"), ("Status", "status")], sugg_rows, urls)
    )
    pages["suggestions.html"] = page("suggestions.html", "Suggestions", "Twelve proposals for review. Nothing is implemented without an Approved decision.", sugg_body)

    # Questions
    ques_rows = []
    for q in ques["questions"]:
        ques_rows.append({"id": q["id"], "question": q["question"], "have": q["have"], "lack": q["lack"], "discover": q["discover"], "answer": q["answer"] if q["answer"] is not None else "", "status": q["status"], "source_ids": q["source_ids"]})
    ques_body = (
        '<div class="notice"><strong>Answers stay blank unless verified.</strong><p>Each question lists what we have, what we lack, and how to discover it. Never infer.</p></div>'
        + table("questions", "Questions, information and answers", [("ID", "id"), ("Question", "question"), ("Have", "have"), ("Lack", "lack"), ("Discover", "discover"), ("Answer", "answer"), ("Status", "status")], ques_rows, urls)
    )
    pages["questions.html"] = page("questions.html", "Questions & answers", "Fifteen questions with have/lack/discover. Answers blank unless verified from an official source.", ques_body)

    # Sources
    registry = load_json_repo("research/sources.json")
    nfl_sources = [s for s in registry if s["id"].startswith("NFL-")]
    src_rows = [{"id": s["id"], "title": s["title"], "url": s["url"], "checked_on": s["checked_on"], "scope": s["scope"], "status": s["status"], "source_ids": [s["id"]]} for s in nfl_sources]
    src_body = table("sources", "NFL source register", [("ID", "id"), ("Title", "title"), ("Checked", "checked_on"), ("Scope", "scope"), ("Status", "status")], src_rows, urls)
    pages["sources.html"] = page("sources.html", "Source register", "Follow every observation to its primary source. A link is a reference — not blanket verification.", src_body)

    # Review
    rev_body = (
        '<div class="notice warning"><strong>Unverified values, confirmed restrictions and corrected irregularities — published plainly for review.</strong><p>Flagged items do not block publishing an honest site, but do block unsupported strategy/price/cash release.</p></div>'
        + table("flags", "Flagged for Review", [("ID", "id"), ("Item", "item"), ("Finding", "finding"), ("Status", "status")], catalog["flags"], urls)
    )
    pages["review.html"] = page("review.html", "Flagged for Review", "Unverified values, confirmed restrictions and corrected irregularities — published plainly for review.", rev_body)

    # Independent verification: a second implementation re-derives the published numbers.
    import subprocess
    verification = []
    verify_status = ""
    try:
        proc = subprocess.run([sys.executable, str(ROOT / "verify_independent.py")],
                              capture_output=True, text=True, timeout=120, cwd=REPO)
        verify_status = "pass" if proc.returncode == 0 else "fail"
        verification = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    except Exception as exc:  # pragma: no cover - defensive
        verify_status = "unavailable"
        verification = [str(exc)]

    # Recompute here too, so the page can show published vs recomputed side by side.
    def _pear(xs, ys):
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
        dy = math.sqrt(sum((b - my) ** 2 for b in ys))
        return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / (dx * dy)

    def _ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        out = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            for k in range(i, j + 1):
                out[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return out

    series = {
        "W vs NetPts (standings)": ([float(r["W"]) for r in standings], [float(r["NetPts"]) for r in standings]),
        "PF vs PA (standings)": ([float(r["PF"]) for r in standings], [float(r["PA"]) for r in standings]),
        "PCT vs NetPts (standings)": ([float(r["PCT"]) for r in standings], [float(r["NetPts"]) for r in standings]),
        "Pass Yds vs TD (QBs)": ([float(r["PassYds"]) for r in passing], [float(r["TD"]) for r in passing]),
        "Pass Yds vs INT (QBs)": ([float(r["PassYds"]) for r in passing], [float(r["INT"]) for r in passing]),
        "Yds/Att vs Rate (QBs)": ([float(r["YdsPerAtt"]) for r in passing], [float(r["Rate"]) for r in passing]),
        "Cmp% vs Rate (QBs)": ([float(r["CmpPct"]) for r in passing], [float(r["Rate"]) for r in passing]),
    }
    verified_rows = []
    for item in results["correlations"]:
        if item["pearson"] is None:
            verified_rows.append({"id": item["pair"], "pair": item["pair"], "n": "",
                                  "published": "", "recomputed": "", "status": "Blank by design",
                                  "source_ids": item["source_ids"]})
            continue
        xs, ys = series[item["pair"]]
        p = _pear(xs, ys)
        s_ = _pear(_ranks(xs), _ranks(ys))
        ok = abs(p - item["pearson"]) < 1e-6 and abs(s_ - item["spearman"]) < 1e-6
        verified_rows.append({
            "id": item["pair"], "pair": item["pair"], "n": str(len(xs)),
            "published": f"{item['pearson']:.6f} · {item['spearman']:.6f}",
            "recomputed": f"{p:.6f} · {s_:.6f}",
            "status": "Reproduced" if ok else "Mismatch",
            "source_ids": item["source_ids"]})

    ypa_issue_rows = []
    for r in passing:
        att, yds = float(r["Att"]), float(r["PassYds"])
        exact = yds / att
        published = float(r["YdsPerAtt"])
        if abs(exact - published) > 0.05 + 1e-9:
            ypa_issue_rows.append({
                "id": r["Player"], "player": r["Player"],
                "printed": f"{yds:.0f} yd / {att:.0f} att = {published:.1f}",
                "actual": f"{exact:.4f}",
                "source_ids": ["NFL-PASSING"]})

    notice_class = "" if verify_status == "pass" else " warning"
    verified_status = esc(verify_status)
    ind_body = (
        '<div class="notice' + notice_class + '">'
        '<strong>A second, independent implementation re-derives every published number.</strong>'
        '<p>Status: <code>' + verified_status + '</code>. Run <code>python nfl/verify_independent.py</code> to repeat it. '
        'Reproduction shows that a published number follows from the published inputs. It does not show that the '
        'inputs match the live official pages, which is a separate dated act.</p></div>'
        '<section><h2>What was recomputed, and how</h2>'
        '<p><code>nfl/verify_independent.py</code> shares no code with the pipeline that produced these figures. '
        'It reimplements Pearson and Spearman correlation, the league standings identities and the NFL passer-rating '
        'formula from the committed CSV snapshots, so a mistake in one implementation cannot silently confirm itself.</p>'
        '<pre class="console" role="region" aria-label="Verifier output" tabindex="0">'
        + esc(chr(10).join(verification)) + '</pre></div></section>'
        + table("independent-correlations", "Published versus independently recomputed correlations (Pearson / Spearman)",
                [("Pair", "pair"), ("n", "n"), ("Published r · rho", "published"),
                 ("Recomputed r · rho", "recomputed"), ("Verdict", "status")],
                verified_rows, urls)
        + '<p class="table-note">A blank row means the coefficient is intentionally absent, not zero. '
          'Blank-by-design rows are listed so that absence is visible rather than implied.</p>'
        + '<section><h2>A real disagreement inside the official table</h2>'
          '<p>Two published yards-per-attempt values cannot be reached by rounding from the same row\'s own '
          'yards and attempts. They were re-fetched on 2026-11-12 and the official page still prints them, so this '
          'is a publisher-side disagreement between columns, not a transcription error. It is recorded as '
          'irregularity NF12 on the <a href="review.html">Flagged for Review</a> page.</p></section>'
        + table("independent-ypa", "Rows where the printed rate disagrees with the row own inputs",
                [("Player", "player"), ("Printed", "printed"), ("Exact from inputs", "actual")],
                ypa_issue_rows, urls)
        + '<section><h2>How much this matters</h2>'
          '<p>The Yds/Att versus Rate coefficient is 0.829085 on the column as printed and 0.831578 if exact '
          'yards per attempt is used instead, a difference of about 0.0025. The published figure is internally '
          'consistent with the column it names, so it stands as a descriptive statistic, but the exposure is '
          'published rather than hidden. No conclusion in this project depends on that coefficient, because no '
          'strategy has cleared a single evaluation gate.</p></section>'
    )
    pages["independent-verification.html"] = page(
        "independent-verification.html", "Independent verification",
        "A second implementation re-derives the published numbers from the committed snapshots and reports what does not reconcile.",
        ind_body)


    # Methodology
    meth_body = (
        "<section><h2>Reproduce without manual entry</h2><div class=\"notice\"><p>python -m nfl_lab run<br>python -m unittest discover -s tests -v<br>python nfl/build.py<br>python scripts/check_site.py</p></div>"
        + "<p>The build is offline and deterministic from committed, receipt-checked snapshots. The analysis manifest contains input/code hashes and a run hash. No accounts, API keys, price entry, real-money wagers or source-data scraping is required.</p></section>"
        + "<section><h2>Boundaries</h2><p>Season aggregates are retrospective. Cross-sectional correlations are descriptive, not predictive. Rushing, receiving and team-offense headers are positional. Schedule/roster not transcribed. Injury replacements/deficiencies blank. NFL-derived betting prices withheld under NFL Terms.</p></section>"
        + table("method-refs", "Method references", [("Reference", "title"), ("Use", "use")], [{"id": "M1", "title": "NFL standings", "use": "Team W/L/PF/PA inputs", "source_ids": ["NFL-STANDINGS"]}, {"id": "M2", "title": "NFL passing", "use": "QB distribution inputs", "source_ids": ["NFL-PASSING"]}, {"id": "M3", "title": "NFL terms", "use": "Rights gate", "source_ids": ["NFL-TERMS"]}], urls)
    )
    pages["methodology.html"] = page("methodology.html", "Methodology", "Clear model contracts, correct pricing mathematics and a reproducible pipeline — with explicit release boundaries.", meth_body)

    return pages


def build(check: bool = False):
    pages = render()
    if set(pages) != set(PAGES):
        raise ValueError(f"page inventory mismatch: {sorted(pages)} vs {PAGES}")
    if check:
        for name in PAGES:
            path = ROOT / name
            if not path.exists():
                raise SystemExit(f"missing {name}; run: python nfl/build.py")
            expected = pages[name].encode("utf-8")
            actual = path.read_bytes()
            if actual != expected:
                raise SystemExit(f"{name} is stale; run: python nfl/build.py")
        print(f"OK: {len(PAGES)} NFL pages reproduce exactly")
        return
    for name, text in pages.items():
        (ROOT / name).write_text(text, encoding="utf-8")
    manifest = {"pages": PAGES, "generated_html": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(PAGES)}, "research_run_hash": load_json_repo("research/nfl-results.json")["run_hash"]}
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built {len(PAGES)} NFL pages; single source of truth.")


if __name__ == "__main__":
    build(check="--check" in __import__("sys").argv)
