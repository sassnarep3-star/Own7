#!/usr/bin/env python3
"""Deterministic generator for the decision-readiness desk (nfl-readiness-1467fdf7).

  python nfl-readiness-1467fdf7/build.py            # run controls + injury check, write data and site
  python nfl-readiness-1467fdf7/build.py --check    # rebuild in memory and demand byte-identical output

Every number on a page is computed from a file in the repo or from the register in requirements.py.
No wall-clock time is used. Standard library only.
"""
from __future__ import annotations

import csv
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

import controls  # noqa: E402
import injury_check  # noqa: E402
import requirements as REQ  # noqa: E402
import strategies as REG  # noqa: E402

SITE = HERE / "site"
DATA = HERE / "data"
READ_ON = "2026-11-17"

NAV = [
    ("index.html", "Decision readiness"),
    ("controls.html", "Controls and luck panel"),
    ("strategies.html", "Strategies and gates"),
    ("injury-check.html", "Injury spot-check"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

OFF_INJ = REQ.OFF_INJ
OFF_TERMS = REQ.OFF_TERMS
OFF_WK5 = REQ.OFF_WK5

FLAGS = [
    {"id": "F01", "severity": "High", "status": "Open: decision", "title": "Scheduled capture conflicts with NFL.com Terms §1.3",
     "finding": "§1.3 allows use 'solely for your own individual non-commercial and informational purposes' and prohibits 'systematic retrieval of data … to create or compile … a collection, compilation, database, or directory … absent our express prior written consent'. The brief's daily and Wednesday-to-Friday captures, immutable archives, reserve lists and point-in-time ledger are that activity. §11(f) also prohibits using robots or spiders to harvest data 'for any commercial purpose'. No scheduled capture was added. The terms page reads 'Updated: May 16, 2024'.",
     "close": "Written consent from NFL Enterprises, or a licensed feed with redistribution rights. Then a rights-reviewed capture plan.",
     "evidence": "nfl-readiness-1467fdf7/requirements.py", "official": [OFF_TERMS]},
    {"id": "F02", "severity": "High", "status": "Open", "title": "Kerby Joseph (DET S): practice status differs",
     "finding": "Availability desk: 'Full Participation in Practice'. Official page read 2026-11-17: 'Did Not Participate In Practice', game status Out. Game status matches.",
     "close": "A dated capture of the report showing which version the desk used, or correction of the desk row after review.",
     "evidence": "nfl-availability-28ef/data/injuries-week10-2026.csv; nfl-readiness-1467fdf7/data/injury-spot-check.json", "official": [OFF_INJ]},
    {"id": "F03", "severity": "High", "status": "Open", "title": "Amon-Ra St. Brown and Sione Vaki (DET): injury and game status blank",
     "finding": "St. Brown: desk injury and game status blank; official 'Rib' and 'Questionable'. Vaki: desk injury blank, practice 'Did Not Participate', game status blank; official 'Ankle', 'Limited Participation in Practice', 'Questionable'.",
     "close": "As F02.", "evidence": "nfl-availability-28ef/data/injuries-week10-2026.csv", "official": [OFF_INJ]},
    {"id": "F04", "severity": "Medium", "status": "Open", "title": "Cause of the DET disagreements cannot be established",
     "finding": "The desk stores a checked-on date, not a clock time, and the official page may have changed after the desk capture. The three mismatches therefore cannot be called capture error or later update. This is the case the brief's timestamped series is meant to resolve.",
     "close": "Clock-time captures (blocked: F01), or the saved text of the earlier version.",
     "evidence": "nfl-readiness-1467fdf7/data/injury-spot-check.json", "official": [OFF_INJ]},
    {"id": "F05", "severity": "High", "status": "Open: unverified", "title": "Cincinnati injury rows: brief says 4, desk shows 8",
     "finding": "The brief states Cincinnati lists 4 players. The availability desk has 8 Cincinnati rows. The official Cincinnati table was not read this session (the saved read covers WAS, NYG, NE, DET, and part of KC). Seattle matches the brief (15).",
     "close": "Read the full official Cincinnati table and record each row with its time.",
     "evidence": "nfl-availability-28ef/data/injuries-week10-2026.csv", "official": [OFF_INJ]},
    {"id": "F06", "severity": "High", "status": "Open", "title": "Row count not reconciled: 279 (brief) vs 326 (desk)",
     "finding": "The brief cites 279 live rows. The availability desk has 326 injury rows across 28 clubs. The legacy file data/nfl-injuries-2026-w10.csv has 20 rows (WAS and NYG only). The full official report was not read in full, so neither total is confirmed.",
     "close": "A full read of all eight official pages, counted club by club, with the count saved.",
     "evidence": "nfl-availability-28ef/data/injuries-week10-2026.csv; data/nfl-injuries-2026-w10.csv", "official": [OFF_INJ]},
    {"id": "F07", "severity": "Medium", "status": "Open", "title": "Availability desk covers 28 clubs, not 32",
     "finding": "The availability club summary has 28 clubs. CHI, DEN, PHI and TB are absent. The nfl-skill-cfdd README says those four were captured in another desk; that claim was not re-verified here.",
     "close": "Verify the four bye clubs against the official depth pages, then merge them into one register.",
     "evidence": "nfl-availability-28ef/data/club-summary-week10-2026.csv; README.md (section: Skill & availability desk)", "official": []},
    {"id": "F08", "severity": "High", "status": "Open", "title": "Backtest figure appears on the results leaderboard",
     "finding": "nfl-results-leaderboard.html shows a 64.2% backtest hit rate for the provisional entry BOARD-SA. The brief forbids backtest numbers on the leaderboard. Not changed here: that desk belongs to another session.",
     "close": "Move the figure to a labelled backtest panel, or remove it from the leaderboard page.",
     "evidence": "nfl-results-leaderboard.html; nfl-results/analysis.json", "official": []},
    {"id": "F09", "severity": "Medium", "status": "Open", "title": "Correlation uses non-official closing prices",
     "finding": "The pricing desk's closing-price correlation (−0.439 with margin, n = 136) uses closing prices sourced from Pro-Football-Reference. The brief requires officially sourced inputs only.",
     "close": "Recompute on official inputs only, or label the figure as non-official and keep it off the leaderboard.",
     "evidence": "nfl-pricing/site/index.html", "official": []},
    {"id": "F10", "severity": "Medium", "status": "Open", "title": "Legacy files disagree with the newer desk",
     "finding": "nfl/origination/data/injuries-2026-w10.csv lists DET Kerby Joseph with practice 'Limited' and a blank designation. The official read shows 'Did Not Participate' and Out. data/nfl-injuries-2026-w10.csv covers two clubs only. Neither file was changed here.",
     "close": "Retire or regenerate the legacy files from the reconciled register.",
     "evidence": "nfl/origination/data/injuries-2026-w10.csv; data/nfl-injuries-2026-w10.csv", "official": [OFF_INJ]},
    {"id": "F11", "severity": "Info", "status": "Closed: verified", "title": "Week 5 tie confirmed: Giants 27, Commanders 27",
     "finding": "The official week-5 schedule page reads 'Giants 27, Commanders 27, FINAL' (Giants 3-1-1). The tie is excluded from straight-up grading (pre-registered rule).",
     "close": "Closed.", "evidence": "nfl-results/data/games-2026-w1-9.csv; nfl-readiness-1467fdf7/data/controls.json", "official": [OFF_WK5]},
    {"id": "F20", "severity": "Info", "status": "Open", "title": "Register rows with no repo artefact yet",
     "finding": f"{sum(1 for r in REQ.R if not r['evidence'].strip())} of {len(REQ.R)} register rows have no repo artefact. Their evidence cell is blank and reads 'No repo artefact yet'; each carries this flag. Their status and gate are stated in the register; no value is measured for them.",
     "close": "Each row gets an artefact (a file in the repo) when its desk produces one; then its evidence is set and this flag is removed for it.",
     "evidence": "nfl-readiness-1467fdf7/requirements.py", "official": []},
    {"id": "F19", "severity": "Low", "status": "Open", "title": "Week 5 schedule page has no row in the source registry",
     "finding": "The week-5 page is cited in this desk and used for the tie check, but research/sources.json has no row whose URL is that page. Adding one would change the nfl-pricing attribution for week pages (its URL-to-ID lookup is last-wins and its pattern covers weeks 1-9), so it was not added. Rows that cite the page are tagged internal to the repository.",
     "close": "Decide with the nfl-pricing desk how week pages are registered, then register the week-5 row once.",
     "evidence": "nfl-results/data/games-2026-w1-9.csv; research/sources.json", "official": [OFF_WK5]},
    {"id": "F12", "severity": "Medium", "status": "Open: disclosed", "title": "The 136-game corpus is retrospective",
     "finding": "The scores were retrieved on 2026-11-14, after the games were final. The corpus cannot be pre-registered. Only rules registered from now on are prospective.",
     "close": "Register future weeks before kickoff, then grade them.",
     "evidence": "nfl-results/data/games-2026-w1-9.csv", "official": [OFF_WK5]},
    {"id": "F13", "severity": "Medium", "status": "Open", "title": "Depth-slot file structure is undocumented",
     "finding": "1586 rows map to 777 unique (club, unit, position, slot) keys. Without a documented row grammar, the brief's 149 multi-rank-1 slots cannot be reproduced.",
     "close": "Document the grammar and reproduce the count from the file.",
     "evidence": "nfl-availability-28ef/data/depth-slots-week10-2026.csv", "official": []},
    {"id": "F14", "severity": "Medium", "status": "Open: unverified", "title": "Depth-parsing claims in the brief not verified",
     "finding": "The brief states the Texans depth chart is an image and the Packers prepend jersey numbers. Neither was verified this session.",
     "close": "Fetch the two official depth pages and record the parse result for each.",
     "evidence": "nfl-readiness-1467fdf7/requirements.py (row C07)", "official": []},
    {"id": "F15", "severity": "High", "status": "Open: decision", "title": "Price-data policy is undecided",
     "finding": "No opening line exists. Closing prices come from a non-official source. No ROI, CLV or residual can be published honestly until a policy names the permitted source.",
     "close": "A written policy, with the source named and its terms read.",
     "evidence": "nfl-lifecycle-3f5c/data/price-snapshots.json", "official": [OFF_TERMS]},
    {"id": "F16", "severity": "High", "status": "Open: decision", "title": "Row-level data is public in the repo",
     "finding": "Row-level CSVs (for example, 326 injury rows) are published in the repo. The brief asks that raw rows stay private until the terms are read.",
     "close": "A recorded decision on which layer each file belongs to.",
     "evidence": "nfl-availability-28ef/data/injuries-week10-2026.csv", "official": [OFF_TERMS]},
    {"id": "F18", "severity": "Medium", "status": "Open", "title": "Registry describes NFL terms §12 as a gambling clause; the page read does not",
     "finding": "research/sources.json entry NFL-TERMS (another desk) says 'Section 12: prohibited from gambling/wagering on gaming features'. On www.nfl.com/legal/terms/ read 2026-11-17, §12 is 'User Content and Communications', and no wagering clause was found in the two chunks read (chunks 0 and 2 of 9). The gambling wording may come from a different terms page. Not changed here.",
     "close": "Read every chunk of the terms page and of the support article the entry cites; correct the registry scope to the exact section.",
     "evidence": "research/sources.json (entry NFL-TERMS); nfl-readiness-1467fdf7/data/flags.json", "official": [OFF_TERMS]},
    {"id": "F17", "severity": "Medium", "status": "Open: decision", "title": "Reward policy is undefined",
     "finding": "No strategy is qualified, so no reward is paid. The brief asks for rewards for top strategies, but gate G7 (executable price) blocks any reward, and the reward rule itself is not written.",
     "close": "Write the reward rule and its gate; decide the amount and eligibility.",
     "evidence": "nfl-readiness-1467fdf7/strategies.py", "official": []},
]


def load_csv(path):
    with (REPO / path).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def facts():
    c = controls.build()
    s = c["summaries"]
    band = c["chance_band"]
    inj = injury_check.build_result()
    analysis = json.loads((REPO / "nfl-results/analysis.json").read_text(encoding="utf-8"))
    sb = analysis["benchmarks"]["spread"]["directional"]
    desk = load_csv("nfl-availability-28ef/data/injuries-week10-2026.csv")
    club = load_csv("nfl-availability-28ef/data/club-summary-week10-2026.csv")
    slots = load_csv("nfl-availability-28ef/data/depth-slots-week10-2026.csv")
    snaps = json.loads((REPO / "nfl-lifecycle-3f5c/data/price-snapshots.json").read_text(encoding="utf-8"))
    lions = {}
    for r in desk:
        if r["club_abbr"] == "DET" and r["player"] in ("Kerby Joseph", "Cade Mays", "D.J. Reed"):
            lions[r["player"]] = r["game_status"] or "blank"
    lions_text = "; ".join(f"{k.split()[-1]} {v}" for k, v in lions.items())
    open_statuses = {"Built", "Built here", "Rejected (per brief)"}
    f = {
        "games": c["universe"]["games"],
        "n_graded": c["universe"]["graded_straight_up"],
        "c_rand_rate": f'{s["C-RAND"]["hit_rate"]*100:.1f}%',
        "c_home_rate": f'{s["C-HOME"]["hit_rate"]*100:.1f}%',
        "c_rec_rate": f'{s["C-REC"]["hit_rate"]*100:.1f}%',
        "band_low": f'{band["rate_p2_5"]*100:.1f}%',
        "band_high": f'{band["rate_p97_5"]*100:.1f}%',
        "snap_records": len(snaps["markets"]),
        "club_summary_rows": len(club),
        "chart_yes": sum(1 for r in club if r["chart_available"] == "yes"),
        "rows_compared": inj["rows_compared"],
        "rows_mismatch": inj["rows_with_mismatch"],
        "evidence_sha": inj["evidence_sha256"][:12],
        "desk_rows": len(desk),
        "sea_rows": sum(1 for r in desk if r["club_abbr"] == "SEA"),
        "cin_rows": sum(1 for r in desk if r["club_abbr"] == "CIN"),
        "lions_game_status": lions_text,
        "slot_rows": len(slots),
        "slot_keys": len({(r["club_abbr"], r["unit"], r["position"], r["slot"]) for r in slots}),
        "multi_flag_rows": sum(1 for r in slots if r["cell_holds_multiple"] == "yes"),
        "blank_slot_rows": sum(1 for r in slots if not r["player"]),
        "singles_entries": sum(1 for x in REG.STRATEGIES if x["division"].startswith("Singles")),
        "mind_entries": sum(1 for x in REG.STRATEGIES if x["confirm"] and x["refute"]),
        "req_rows": len(REQ.R),
        "open_rows": sum(1 for r in REQ.R if r["status"] not in open_statuses),
        "official_rows": sum(1 for r in REQ.R if r["official"]),
        "flags_total": len(FLAGS),
        "flags_open": sum(1 for x in FLAGS if x["status"].startswith("Open")),
        "sb_bets": sb["bets"],
        "sb_rate": f'{sb["hit_rate"]*100:.1f}%',
        "sb_ci": f'{sb["ci_low"]*100:.1f}% to {sb["ci_high"]*100:.1f}%',
        "sb_perm_p": f'{analysis["benchmarks"]["spread"]["permutation_p_value"]:.4f}',
        "sb_fwer": f'{analysis["luck_analysis"]["family_wise_false_positive"]:.3f}',
    }
    return f, c, inj


def fill(text, f):
    return text.format(**f)


def e(v):
    return html.escape(str(v), quote=True)


def rel(path, depth=2):
    """Path from site/ (depth 2 below repo root) to a repo-relative path."""
    return "../" * depth + path


def link(url, label=None):
    label = label or url
    return f'<a href="{e(url)}" rel="noopener">{e(label)}</a>'


def evidence_link(path):
    """Render one or more ';'-separated repo paths. Annotations in parentheses are shown, not linked."""
    if not path:
        return "—"
    parts = []
    for piece in path.split(";"):
        piece = piece.strip()
        target = piece.split(" (")[0].strip()
        label = piece
        if target.startswith("http"):
            parts.append(link(target, label))
        else:
            parts.append(f'<a href="{e(rel(target))}">{e(label)}</a>')
    return "<br>".join(parts)


def official_cell(urls):
    if not urls:
        return '<span class="muted">none (internal)</span>'
    return "<br>".join(link(u) for u in urls)


def page(title, eyebrow, body, active):
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == active else ""
        items.append(f'<a href="{e(href)}"{cur}>{e(label)}</a>')
    nav = "".join(items)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Decision-readiness desk for the NFL origination project: what is built, what blocks it, and the number that would clear it.">
<title>{e(title)} · NFL readiness desk</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="brand"><a href="index.html">NFL readiness desk</a><span>Not a betting service · no reward paid · no price used</span></div>
  <nav aria-label="Desk pages">{nav}</nav>
</header>
<main id="main">
<p class="eyebrow">{e(eyebrow)}</p>
<h1>{e(title)}</h1>
{body}
</main>
<footer class="foot">
  <p>Source data: NFL.com official pages, read {READ_ON}; repo artefacts linked per row. NFL data is attributed to NFL.com. This project is not affiliated with or endorsed by the NFL.</p>
  <p>Regenerate: <code>python nfl-readiness-1467fdf7/build.py</code> · verify: <code>python nfl-readiness-1467fdf7/build.py --check</code></p>
</footer>
</body>
</html>
"""


REGISTRY = {x["id"]: x["url"] for x in json.loads((REPO / "research/sources.json").read_text(encoding="utf-8"))}
REPO_URL = REGISTRY["REPO"]
# Existing registry rows that this desk's official links resolve to. Registry rows are not added here:
# a second row on the same URL changes other desks' attribution (nfl-pricing resolves URL -> ID last-wins).
LINK_IDS = {OFF_INJ: "NFL-INJURIES", OFF_TERMS: "NFL-LEGAL-TERMS", REPO_URL: "REPO"}


def table(headers, rows, cls=""):
    """Every body row carries data-source-ids (registered IDs) and at least one link to its registered URL.

    A row with no official link is internal: it gets the REPO id and a labelled repo link in its last cell.
    """
    head = "".join(f"<th scope=\"col\">{e(h)}</th>" for h in headers)
    body_parts = []
    for r in rows:
        cells = list(r)
        html_row = "".join(cells)
        ids = [sid for url, sid in LINK_IDS.items() if f'href="{url}"' in html_row and sid != "REPO"]
        if not ids:
            ids = ["REPO"]
            cells[-1] = f'{cells[-1]}<br><span class="muted">internal:</span> <a href="{e(REPO_URL)}">repository</a>'
        ids = sorted(set(ids))
        body_parts.append(f'<tr data-source-ids="{e(" ".join(ids))}">' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    body = "".join(body_parts)
    return f'<div class="tablewrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def status_class(status):
    if status.startswith("Blocked"):
        return "st-block"
    if status in ("Built", "Built here", "Closed: verified"):
        return "st-ok"
    if status in ("Resolved in part",):
        return "st-part"
    if status == "Decision needed" or status.startswith("Open: decision"):
        return "st-dec"
    if status.startswith("Rejected"):
        return "st-rej"
    return "st-part" if status == "Partial" else "st-none"


def build_pages(f, c, inj):
    out = {}
    reqs = [dict(r) for r in REQ.R]
    for r in reqs:
        r["current"] = fill(r["current"], f)
        r["clears"] = fill(r["clears"], f)
        r["gate"] = fill(r["gate"], f)

    counts = {}
    for r in reqs:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    order = ["Built", "Built here", "Resolved in part", "Partial", "Not started", "Blocked: data", "Blocked: rights", "Decision needed", "Rejected (per brief)"]
    count_rows = [[e(s), str(counts.get(s, 0))] for s in order if counts.get(s, 0)]
    count_html = table(["Status", "Rows"], count_rows, "compact")

    cards = f"""
<section class="cards" aria-label="Headline numbers">
  <div class="card"><div class="num">{f['req_rows']}</div><div>requirement rows</div></div>
  <div class="card"><div class="num">{f['n_graded']}</div><div>official games graded straight-up (weeks 1-9)</div></div>
  <div class="card"><div class="num">0</div><div>qualified strategies · rewards paid</div></div>
  <div class="card"><div class="num">{f['open_rows']}</div><div>rows still open</div></div>
  <div class="card"><div class="num">{f['flags_open']}</div><div>flags open for review</div></div>
</section>"""

    luck = f"""
<section class="panel" id="luck">
<h2>Removal of luck: the chance band, in one panel</h2>
<p>Each row is a control or a cross-reference, all on the same official results. A value inside the band is what a coin would do. The band is a seeded simulation (10,000 replicates, seed {REG.RANDOM_SEED}).</p>
{table(["Entry", "Division", "Graded n", "Hit rate", "95% interval", "Passes chance band?", "Source"],
  [
    ["C-RAND · random pick", "Control", str(s_n(c, 'C-RAND')), f['c_rand_rate'], ci(c, 'C-RAND'), "is the band", evidence_link("nfl-readiness-1467fdf7/data/controls.json")],
    ["C-HOME · always home", "Control", str(s_n(c, 'C-HOME')), f['c_home_rate'], ci(c, 'C-HOME'), passes(c, 'C-HOME'), evidence_link("nfl-readiness-1467fdf7/data/controls.json")],
    ["C-REC · higher prior win %", "Control (proxy)", str(s_n(c, 'C-REC')), f['c_rec_rate'], ci(c, 'C-REC'), passes(c, 'C-REC'), evidence_link("nfl-readiness-1467fdf7/data/controls.json")],
    ["S-BOARD-SA · spread board (cross-reference, in-sample backtest, not a leaderboard entry)", "Candidate", str(f['sb_bets']), f['sb_rate'], f['sb_ci'], f"in-sample permutation p = {f['sb_perm_p']}; family-wise {f['sb_fwer']}", evidence_link("nfl-results/analysis.json")],
  ], "wide")}
<p class="note">The chance band for n = {c['chance_band']['n']} is {f['band_low']} to {f['band_high']}. Only C-REC's interval and the spread board's permutation test are above chance, and neither clears the sample gate G3 (n &ge; 153) or the executable-price gate G7.</p>
</section>"""

    flagged_cards = ""

    readiness_rows = []
    for g_code, g_name in REQ.GROUPS:
        for r in reqs:
            if r["group"] != g_code:
                continue
            readiness_rows.append([
                e(r["id"]),
                e(r["text"]),
                f'<span class="pill {status_class(r["status"])}">{e(r["status"])}</span>',
                e(r["gate"]),
                e(r["clears"]),
                e(r["current"]),
                evidence_link(r["evidence"]) if r["evidence"] else "No repo artefact yet",
                official_cell(r["official"]),
            ])
    readiness = table(["ID", "Requirement", "Status", "Gate that blocks it", "Number that would clear it", "Measured now", "Repo evidence", "Official source"],
                      readiness_rows, "wide ready")

    index_body = f"""
<p class="lead">This desk answers one question for each requirement in the 2026-11-17 brief: <strong>what is built, what blocks it, and what number would clear it.</strong> Blank or "not started" means nothing verified exists. Nothing here is a betting recommendation.</p>
{cards}
{luck}
<section class="panel">
<h2>Status count</h2>
{count_html}
<p class="note">Built means an earlier desk already contains it and checks it. Built here means this session added it. Rows marked "Blocked: rights" cannot proceed without a decision recorded in flag F01.</p>
</section>
<section class="panel">
<h2>Decision-readiness table</h2>
<p class="note">One row per requirement, grouped. A row with no official link is internal: a method, a decision or a repo state. It is marked, not hidden.</p>
{readiness}
</section>"""
    out["index.html"] = page("Decision readiness", "NFL readiness desk · 2026-11-17", index_body, "index.html")

    # controls page
    ctl_rows = []
    for cid in ("C-RAND", "C-HOME", "C-REC"):
        sm = c["summaries"][cid]
        g = c["gates"][cid]
        ctl_rows.append([
            e(cid), e({"C-RAND": "Random pick (seeded)", "C-HOME": "Always home team", "C-REC": "Higher prior win % (proxy for favourite)"}[cid]),
            str(sm["n_graded"]), str(sm["hits"]), f'{sm["hit_rate"]*100:.1f}%',
            f'{sm["wilson95"][0]*100:.1f}% to {sm["wilson95"][1]*100:.1f}%',
            f'{sm["first_half"]["rate"]*100:.1f}% ({sm["first_half"]["hits"]}/{sm["first_half"]["n"]})',
            f'{sm["second_half"]["rate"]*100:.1f}% ({sm["second_half"]["hits"]}/{sm["second_half"]["n"]})',
            f'{sm["drop_one_week_min"]*100:.1f}% to {sm["drop_one_week_max"]*100:.1f}%',
            "yes" if g["G3_sample"] else "no",
            "yes" if g["G4_beats_chance_band"] else "no",
            "yes" if g["G5_both_halves_above_50"] else "no",
        ])
    ctl_table = table(["ID", "Control", "n", "Hits", "Hit rate", "95% Wilson", "Weeks 1-4", "Weeks 5-9", "Drop one week", "G3 n≥153", "G4 beats band", "G5 halves > 50%"], ctl_rows, "wide")
    cm = c["gates"]["C-REC"]
    tie = c["universe"]["ties_excluded"][0]
    ctl_body = f"""
<p class="lead">Three controls, computed from {c['universe']['games']} official final scores (weeks 1-9). Rules and gates are frozen in <code>strategies.py</code>, committed at <code>{e(c['registration_commit'])}</code> before the control run. Week 1 has no prior record, so week 1 record picks go to the home team.</p>
<section class="panel">
<h2>Control results</h2>
{ctl_table}
<p class="note">Gate G7 (executable price) is blocked for every row. No ROI or CLV is computed. The margin of C-REC over C-HOME is {cm['margin_vs_C-HOME_pp']:.1f} percentage points (pre-registered minimum {REG.HOME_MARGIN_MIN_PP:.0f}).</p>
</section>
<section class="panel">
<h2>Chance band</h2>
{table(["Replicates", "Seed", "n", "2.5th percentile", "Median", "97.5th percentile"],
  [[f'{c["chance_band"]["replicates"]:,}', str(c["chance_band"]["seed"]), str(c["chance_band"]["n"]), f'{c["chance_band"]["rate_p2_5"]*100:.1f}%', f'{c["chance_band"]["rate_median"]*100:.1f}%', f'{c["chance_band"]["rate_p97_5"]*100:.1f}%']], "compact")}
</section>
<section class="panel">
<h2>Ties and exclusions</h2>
<p>One game is excluded from straight-up grading: <strong>{e(tie['score'])}</strong>, week {tie['week']}. Official page: {link(tie['source_url'])}. The page reads "Giants 27, Commanders 27, FINAL" and lists the Giants at 3-1-1 (flag F11).</p>
<p class="note">Universe: <code>nfl-results/data/games-2026-w1-9.csv</code>, retrieved 2026-11-14 (flag F12: retrospective, not pre-registered).</p>
</section>
<section class="panel">
<h2>Game-level rows</h2>
<p class="note">Every graded game with each pick, the winner and its official source. Full JSON: <a href="../data/controls.json">data/controls.json</a>.</p>
{table(["Week", "Date", "Away", "Home", "Final", "Winner", "C-RAND pick", "C-HOME pick", "C-REC pick", "Official source"],
  [[str(r["week"]), e(r["date"]), e(r["away"]), e(r["home"]), f'{r["away_score"]}–{r["home_score"]}', e(r["winner"] or "tie (not graded)"), e(r["C-RAND"]), e(r["C-HOME"]), e(r["C-REC"]), link(r["source_url"], "week page")] for r in c["rows"]], "wide")}
</section>"""
    out["controls.html"] = page("Controls and luck panel", "Pre-registered controls · NR-PREREG-1", ctl_body, "controls.html")

    # strategies page
    srows = []
    for st in REG.STRATEGIES:
        srows.append([
            e(st["id"]), e(st["division"]), e(st["name"]), e(st["definition"]),
            e(st["confirm"]), e(st["refute"]),
        ])
    strat_table = table(["ID", "Division", "Name", "Definition", "What would change our mind: confirm", "What would change our mind: refute (demote)"], srows, "wide")
    gate_rows = [[e(g["id"]), e(g["name"]), e(g["rule"])] for g in REG.GATES]
    div_rows = [[e(d["division"]), e(d["status"]), e(d["blocked_by"])] for d in REG.DIVISIONS]
    strat_body = f"""
<p class="lead">Every strategy entry carries two sides: what would make us take it more seriously, and what would demote it to paper. Registration {e(REG.REGISTRATION_ID)}, frozen {e(REG.FROZEN_ON)}, rule commit <code>813ce25</code>.</p>
<section class="panel">
<h2>Entries</h2>
{strat_table}
</section>
<section class="panel">
<h2>Gates (pre-registered)</h2>
{table(["Gate", "Name", "Rule"], gate_rows, "wide")}
</section>
<section class="panel">
<h2>Divisions and what blocks them</h2>
{table(["Division", "Status", "Blocked by"], div_rows, "wide")}
</section>
<section class="panel">
<h2>Rewards</h2>
<p>No reward is defined or paid. Qualified strategies: <strong>0</strong>. Rule F17 records the reward policy as undecided. A reward needs gates G1–G7 to pass, including an executable price (G7), which does not exist.</p>
</section>"""
    out["strategies.html"] = page("Strategies and gates", "Pre-registered · two-sided", strat_body, "strategies.html")

    # injury check page
    irows = []
    for r in inj["rows"]:
        cls = "mismatch" if r["mismatch_fields"] else ""
        irows.append([
            e(r["club"]), e(r["player"]),
            e(r["official_injury"]) or "—", e(r["desk_injury"]) or "—",
            e(r["official_practice"]), e(r["desk_practice"]),
            e(r["official_game"]) or "—", e(r["desk_game"]) or "—",
            e(", ".join(r["mismatch_fields"])) or "agrees",
            link(OFF_INJ, "official report"),
        ])
    inj_table = table(["Club", "Player", "Official injury", "Desk injury", "Official practice", "Desk practice", "Official game", "Desk game", "Disagrees on", "Official source"], irows, "wide injury")
    inj_body = f"""
<p class="lead">The official Week 10 injury page was read on {READ_ON}. Its saved text covers four complete clubs (WAS, NYG, NE, DET) and part of KC. I compared all {inj['rows_compared']} complete rows with the availability desk. <strong>{inj['rows_with_mismatch']} rows disagree</strong>, all three for Detroit.</p>
<section class="panel">
<h2>What was read and checked</h2>
{table(["Item", "Value"], [
    ["Official source", link(inj["evidence_source_url"])],
    ["Saved text", evidence_link(inj["evidence_file"])],
    ["SHA-256 of saved text", f'<code>{e(inj["evidence_sha256"])}</code>'],
    ["Official rows parsed", str(inj["official_rows_parsed"])],
    ["Complete clubs compared", ", ".join(inj["complete_clubs_compared"])],
    ["Rows compared", str(inj["rows_compared"])],
    ["Rows that disagree", str(inj["rows_with_mismatch"])],
    ["Official rows missing from desk", str(len(inj["official_rows_missing_from_desk"]))],
    ["Not compared", e("; ".join(inj["not_compared"]))],
    ["Desk source", evidence_link(inj["desk_source"])],
], "compact")}
<p class="note">A disagreement is reported, never corrected. The cause is open (flag F04): the desk stores a date and the official page may have changed after the desk capture.</p>
</section>
<section class="panel">
<h2>Row by row</h2>
{inj_table}
</section>"""
    out["injury-check.html"] = page("Injury spot-check", "Official Week 10 report vs availability desk", inj_body, "injury-check.html")

    # flagged page
    frows = []
    for x in FLAGS:
        frows.append([
            e(x["id"]), e(x["severity"]), e(x["status"]), e(x["title"]), e(x["finding"]), e(x["close"]),
            evidence_link(x["evidence"]) if x["evidence"] else "—", official_cell(x["official"]),
        ])
    flagged_body = f"""
<p class="lead">Irregularities found while checking this desk. These do not block the merge. Each is linked to its evidence and to the official source where one applies. Open items need your decision or a source.</p>
<section class="panel">
{table(["ID", "Severity", "Status", "Finding in brief", "What we found", "What closes it", "Evidence", "Official source"], frows, "wide")}
</section>"""
    out["flagged.html"] = page("Flagged for review", "Irregularities · non-blocking · please review", flagged_body, "flagged.html")

    # sources page
    src_rows = [
        ["S1", link(OFF_INJ), "Official NFL injury report, Week 10 2026", READ_ON, "Chunk 0 of 8 read and saved (sha256 in injury-check); the other chunks were not read."],
        ["S2", link(OFF_TERMS), "NFL.com Terms and Conditions (Updated: May 16, 2024)", READ_ON, "§1.3 quoted in flag F01."],
        ["S3", link(OFF_WK5), "NFL 2026 schedule, week 5", READ_ON, "Chunk 0 of 2 read. Tie row (Giants 27, Commanders 27) confirmed."],
        ["S4", link("https://www.nfl.com/games/giants-at-commanders-2026-reg-5"), "Game-centre link printed on the week-5 schedule page", READ_ON, "Link seen on the page; game centre not opened. Used only as the venue example in A14."],
        ["R1", "nfl-results/data/games-2026-w1-9.csv", "Repo: 136 official final scores", "2026-11-14 (file)", "Source URLs per row; the desk's grading uses this file only."],
        ["R2", "nfl-availability-28ef/data/injuries-week10-2026.csv", "Repo: availability desk injury rows", "per row checked_on", "Compared with S1."],
        ["R3", "nfl-results/analysis.json", "Repo: results-desk permutation and family-wise figures", "deterministic run", "Cross-referenced for S-BOARD-SA only."],
    ]
    src_body = f"""
<p class="lead">Every source used by this desk, with the read date and what was actually read. A source that was not opened is marked as such.</p>
<section class="panel">
{table(["ID", "Source", "What it is", "Read or dated", "What was read"], src_rows, "wide")}
</section>"""
    out["sources.html"] = page("Sources", "Official links and repo inputs", src_body, "sources.html")
    return out


def style_css():
    return """:root{--ink:#16202a;--muted:#5b6672;--line:#d7dde4;--bg:#f7f9fb;--ok:#14532d;--okbg:#dcfce7;--part:#7c4a03;--partbg:#fef3c7;--block:#7f1d1d;--blockbg:#fee2e2;--dec:#1e3a8a;--decbg:#dbeafe;--rej:#374151;--rejbg:#e5e7eb}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#fff;padding:6px}
.top{background:#fff;border-bottom:1px solid var(--line);padding:12px 20px;display:flex;flex-wrap:wrap;gap:12px 24px;align-items:center;justify-content:space-between}
.brand a{font-weight:700;color:var(--ink);text-decoration:none;margin-right:12px}.brand span{color:var(--muted);font-size:13px}
nav{display:flex;flex-wrap:wrap;gap:6px}nav a{padding:6px 10px;border-radius:6px;color:var(--ink);text-decoration:none;border:1px solid transparent}
nav a:hover{border-color:var(--line)}nav a[aria-current=page]{background:var(--ink);color:#fff}
main{max-width:1280px;margin:0 auto;padding:20px}
.eyebrow{color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-size:12px;margin:8px 0 0}
h1{font-size:26px;margin:4px 0 12px}h2{font-size:18px;margin:0 0 10px}
.lead{font-size:16px;max-width:900px}.note{color:var(--muted);font-size:13px}
.panel{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px;margin:14px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px}.card .num{font-size:28px;font-weight:700}.card div:last-child{color:var(--muted);font-size:13px}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
th{background:#eef2f6;position:sticky;top:0;font-weight:600}tr:last-child td{border-bottom:0}
table.compact{width:auto}table.wide td{min-width:110px}.ready td:nth-child(2){min-width:260px}
tr.mismatch td{background:#fff7ed}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.st-ok{background:var(--okbg);color:var(--ok)}.st-part{background:var(--partbg);color:var(--part)}.st-block{background:var(--blockbg);color:var(--block)}
.st-dec{background:var(--decbg);color:var(--dec)}.st-rej{background:var(--rejbg);color:var(--rej)}.st-none{background:#f3f4f6;color:var(--muted)}
.muted{color:var(--muted)}a{color:#1d4ed8}code{background:#eef2f6;padding:1px 4px;border-radius:4px;font-size:12px}
.foot{max-width:1280px;margin:20px auto;padding:0 20px 30px;color:var(--muted);font-size:12px}
@media (max-width:640px){main{padding:12px}.top{padding:10px 12px}}
"""


def ci(c, cid):
    lo, hi = c["summaries"][cid]["wilson95"]
    return f"{lo*100:.1f}% to {hi*100:.1f}%"


def passes(c, cid):
    lo = c["summaries"][cid]["wilson95"][0]
    return "yes" if lo > c["chance_band"]["rate_p97_5"] else "no (lower bound below band)"


def s_n(c, cid):
    return c["summaries"][cid]["n_graded"]


def manifest(out):
    return {"pages": sorted(out.keys()), "generated_from": [
        "nfl-readiness-1467fdf7/requirements.py", "nfl-readiness-1467fdf7/strategies.py",
        "nfl-readiness-1467fdf7/controls.py", "nfl-readiness-1467fdf7/injury_check.py",
    ]}


def render():
    f, c, inj = facts()
    out = build_pages(f, c, inj)
    files = {"data/controls.json": controls.to_text(c), "data/injury-spot-check.json": injury_check.to_text(inj)}
    for name, body in out.items():
        files[f"site/{name}"] = body
    files["site/style.css"] = style_css()
    files["site/manifest.json"] = json.dumps(manifest(out), indent=2, sort_keys=True) + "\n"
    filled = []
    for r in REQ.R:
        row = dict(r)
        for k in ("text", "gate", "clears", "current"):
            row[k] = fill(r[k], f)
        filled.append(row)
    files["data/requirements.json"] = json.dumps(
        {"schema": "readiness-v1", "statuses": sorted(REQ.STATUSES), "rows": filled, "facts": f},
        indent=2, sort_keys=True) + "\n"
    files["data/flags.json"] = json.dumps(FLAGS, indent=2, sort_keys=True) + "\n"
    return files, c, inj


def main(argv):
    files, c, inj = render()
    if "--check" in argv:
        bad = []
        for rel_path, text in files.items():
            p = HERE / rel_path
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                bad.append(rel_path)
        if bad:
            print("not byte-identical to a fresh rebuild: " + ", ".join(bad), file=sys.stderr)
            return 1
        print(f"readiness desk reproduces byte-identically ({len(files)} files)")
        return 0
    files, _, _ = render()
    for rel_path, text in files.items():
        p = HERE / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} files under nfl-readiness-1467fdf7/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
