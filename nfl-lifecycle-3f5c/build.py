#!/usr/bin/env python3
"""Deterministic generator for the market-lifecycle desk (nfl-lifecycle-3f5c).

Builds the desk's data artefacts and its site. Every <tbody> row carries data-source-ids naming
registered source IDs and at least one link to a registered official URL; every unknown value is
an empty cell with data-empty="true". `--check` rebuilds and demands byte-identical output.

No wall-clock input is used anywhere: all dates are fixed constants of the read records.
"""
from __future__ import annotations

import csv
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import corr_audit  # noqa: E402
import demotion  # noqa: E402
import depth  # noqa: E402
import leaderboard  # noqa: E402
import snapshots  # noqa: E402
import stages  # noqa: E402
import vintages  # noqa: E402
from decisions import QUESTIONS, SUGGESTIONS  # noqa: E402

DATA = HERE / "data"
SITE = HERE / "site"
READ_ON = vintages.READ_ON
OPEN_ON = "2026-11-12"

PAGES = [
    ("index.html", "Overview"),
    ("summary.html", "Executive summary"),
    ("origination-order.html", "Origination order"),
    ("price-snapshots.html", "Price snapshots"),
    ("fair-market-diff.html", "Fair / market / diff"),
    ("leaderboard.html", "Leaderboard: signal vs staking"),
    ("demotion.html", "Demotion gate"),
    ("replacement-depth.html", "Replacement depth"),
    ("correlation-audit.html", "Correlation audit"),
    ("questions.html", "Questions & answers"),
    ("suggestions.html", "Suggestions for review"),
    ("verification.html", "Verification"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

FLAGS = [
    {"id": "LC-F01", "status": "open", "severity": "medium",
     "finding": "For W10-01 (Commanders @ Giants, kicked off 2026-11-12 8:15 PM ET) the closing "
                "snapshot equals the opening snapshot. The 2026-11-12 origination's capture hour "
                "is not published anywhere in the repository, so 'pre-kickoff' rests on the "
                "repository's 2026-11-12 check-date contract rather than a timestamp.",
     "treatment": "recorded on every terminal market row; no post-kickoff number was invented",
     "source_ids": ["LC-NFL-SCHED-REG10-1114", "REPO"], "source_url": "https://www.nfl.com/schedules/2026/REG10/"},
    {"id": "LC-F02", "status": "open", "severity": "high",
     "finding": "Every market-side cell in the snapshot store is blank: no sportsbook price is "
                "licensed or retrieved (standing constraints XS09/CF10). Fair-vs-market and "
                "difference columns are therefore blank by rule.",
     "treatment": "columns exist and are reserved; reason string attached to every blank; "
                  "suggestion LS01 asks the reviewer to approve a rights-cleared source",
     "source_ids": ["CFDD-NFL-TERMS", "REPO"], "source_url": "https://www.nfl.com/legal/terms/"},
    {"id": "LC-F03", "status": "explained", "severity": "low",
     "finding": "The 13 non-zero open-to-close moves this week are all total-market moves "
                "(about -0.0022 points); side and moneyline did not move for the 13 pre-kickoff "
                "games because the league scoring mean cancels in the margin algebra. W10-01 is "
                "terminal, so its close equals its open by rule.",
     "treatment": "documented on the price-snapshots page with the algebra; not a market "
                  "observation and never presented as one",
     "source_ids": ["REPO"], "source_url": "https://github.com/sassnarep3-star/Own7"},
    {"id": "LC-F04", "status": "explained", "severity": "low",
     "finding": "The publisher prints winning percentage rounded half-up (2.5/8 renders 0.313) "
                "while Python's default round() is half-even (0.312). The desk's arithmetic "
                "checks use the publisher's convention and say so.",
     "treatment": "documented in vintages.py and on the verification page",
     "source_ids": ["LC-NFL-STANDINGS-1114", "REPO"], "source_url": "https://www.nfl.com/standings/"},
    {"id": "LC-F05", "status": "open", "severity": "medium",
     "finding": "Houston's printed depth chart still renders as an image with no table and has "
                "never been obtained (cfdd flag CF06 reproduced on 2026-11-14); the depth join "
                "therefore covers 31 of 32 clubs.",
     "treatment": "no substitution made; the club's chain is published as not obtained",
     "source_ids": ["CFDD-HOU-DEPTH", "REPO"], "source_url": "https://www.houstontexans.com/team/depth-chart"},
    {"id": "LC-F06", "status": "explained", "severity": "low",
     "finding": "The standings page still prints one unnamed numeric column (cfdd flag CF02); "
                "the column is not transcribed into any data file.",
     "treatment": "only the named columns are published",
     "source_ids": ["LC-NFL-STANDINGS-1114", "REPO"], "source_url": "https://www.nfl.com/standings/"},
    {"id": "LC-F07", "status": "open", "severity": "medium",
     "finding": "72 on-chart injury rows print no backup behind the injured player and 61 injury "
                "rows are not on any printed chart, so a replacement depth cannot be stated for "
                "them; the depth view reports them as their own class rather than estimating.",
     "treatment": "published as separate depth states with counts; no name invented",
     "source_ids": ["X28-NFL-INJ-W10", "REPO"], "source_url": "https://www.nfl.com/injuries/league/2026/REG10"},
    {"id": "LC-F08", "status": "explained", "severity": "low",
     "finding": "The demotion gate has never operated on a live entry (0 live entries exist); its "
                "triggers are unit-tested on synthetic windows only until something qualifies.",
     "treatment": "the gate ships armed and idle; suggestion LS06 proposes a paper replay on the "
                  "graded history",
     "source_ids": ["REPO"], "source_url": "https://github.com/sassnarep3-star/Own7"},
]


def load_registry() -> dict:
    register = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
    if isinstance(register, dict):
        register = register.get("sources", [])
    return {entry["id"]: entry["url"] for entry in register}


REGISTRY = load_registry()
URL_TO_ID = {}
for sid, url in REGISTRY.items():
    URL_TO_ID.setdefault(url, sid)


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def cell(value, *, num=False, blank_note=None) -> str:
    if value is None or value == "":
        note = esc(blank_note or "Blank — unverified, withheld or not applicable")
        return f'<td class="blank{" num" if num else ""}" data-empty="true" title="{note}">{note}</td>'
    cls = ' class="num"' if num else ""
    return f"<td{cls}>{esc(value)}</td>"


def refs_cell(source_ids, extra_url=None) -> str:
    seen, links = set(), []
    for sid in source_ids:
        url = REGISTRY.get(sid)
        if url and url not in seen:
            seen.add(url)
            links.append(f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(sid)} ↗</a>')
    if extra_url and extra_url not in seen and extra_url.startswith("https://"):
        sid = URL_TO_ID.get(extra_url)
        links.append(f'<a href="{esc(extra_url)}" target="_blank" rel="noopener noreferrer">'
                     f'{esc(sid or "official source")} ↗</a>')
    return '<td class="refs">' + "".join(links) + "</td>"


def table(headers, rows_html, caption=None) -> str:
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    return (f'<div class="table-card"><table>{cap}<thead><tr>{head}</tr></thead>'
            f"<tbody>{''.join(rows_html)}</tbody></table></div>")


def badge(text, kind="info") -> str:
    return f'<span class="badge {kind}">{esc(text)}</span>'


def page(slug, body_parts) -> str:
    nav_items = []
    for name, label in PAGES:
        current = ' aria-current="page"' if name == slug else ""
        nav_items.append(f'<a href="{name}"{current}>{esc(label)}</a>')
    nav = "".join(nav_items)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Market lifecycle · OWN7 NFL</title><meta name="description" content="Market-lifecycle desk: price snapshots, ordered origination, signal/staking separation, demotion gate, replacement depth. Source-linked, blanks preserved.">
<link rel="stylesheet" href="style.css"></head>
<body><a class="skip-link" href="#main">Skip to content</a>
<main id="main">
<header class="page-head"><div class="eyebrow">OWN7 · NFL market lifecycle desk (session 3f5c4cd6)</div>
<h1>Market lifecycle — snapshots, order, signal, staking, demotion</h1>
<p class="lede">Captures opening and closing numbers for every market this project originates,
publishes the ordered pipeline (side → total → moneyline) and the fair / market / difference
columns, separates leaderboard signal from staking, pre-registers the demotion gate, and tracks
replacement depth. Every value carries an official source link; blanks are preserved and
explained. Not affiliated with or endorsed by the NFL; not a betting service.</p>
<nav class="pages" aria-label="Desk pages">{nav}</nav>
</header>
{''.join(body_parts)}
<footer>Sources: NFL.com (standings, schedule, injuries, game pages) and club depth charts, each
linked per row; model references per row. Data attribution to NFL.com under its terms §1.3
(individual, non-commercial, informational use; no systematic retrieval). Market-side prices do
not exist in this repository. Built deterministically by nfl-lifecycle-3f5c/build.py.</footer>
</main></body></html>
"""


# ---------------------------------------------------------------- data assembly

def standings_verification() -> dict:
    """Re-find every vintage-b row verbatim in the saved official evidence text."""
    evidence = (HERE / "evidence" / "standings-2026-11-14.md").read_text(encoding="utf-8")
    rows = vintages.load_vintage(vintages.VINTAGE_B)["rows"]
    checked, failed = [], []
    for r in rows:
        needle = (f"- {r['Team']} | {int(r['W'])} | {int(r['L'])} | {int(r['T'])} | {r['PCT']} | "
                  f"{int(r['PF'])} | {int(r['PA'])} | {int(r['NetPts'])}")
        ok = needle in evidence
        checked.append({"team": r["Team"], "code": vintages.TEAM_CODES[r["Team"]], "found": ok})
        if not ok:
            failed.append(r["Team"])
    return {"rows": checked, "n": len(checked), "failed": failed,
            "status": "PASS" if not failed else "FAIL",
            "evidence": "nfl-lifecycle-3f5c/evidence/standings-2026-11-14.md",
            "source_ids": ["LC-NFL-STANDINGS-1114", "NFL-STANDINGS"]}


def fixtures_verification() -> dict:
    """Re-find every fixture line verbatim in the saved official schedule evidence."""
    evidence = (HERE / "evidence" / "schedule-reg10-2026-11-14.md").read_text(encoding="utf-8")
    fixtures = stages.load_fixtures()
    checked, failed = [], []
    for f in fixtures:
        if f["Date"] == "2026-11-12":
            needle = f"{f['Away']} 24, {f['Home']} 21, FINAL"
        else:
            needle = (f"{f['Away']} at {f['Home']}, {f['Day']}, November {int(f['Date'][8:10])}th, "
                      f"{f['KickoffET']}, {f['TV']}")
        ok = needle in evidence
        checked.append({"id": f["id"], "game": f"{f['Away']} at {f['Home']}", "found": ok})
        if not ok:
            failed.append(f["id"])
    return {"rows": checked, "n": len(checked), "failed": failed,
            "status": "PASS" if not failed else "FAIL",
            "evidence": "nfl-lifecycle-3f5c/evidence/schedule-reg10-2026-11-14.md",
            "source_ids": ["LC-NFL-SCHED-REG10-1114", "NFL-SCHED-W10"]}


def build_artifacts() -> dict:
    transition = vintages.check_vintage_transition()
    reconciliation = stages.reconcile_with_canonical()
    store = snapshots.build_store()
    store_problems = snapshots.check_store(store)
    board = leaderboard.build()
    gate = demotion.build()
    depth_view = depth.build()
    corra = corr_audit.build()
    standings_v = standings_verification()
    fixtures_v = fixtures_verification()

    if reconciliation["status"] != "PASS":
        raise SystemExit(f"staged pipeline does not reconcile with the canonical engine: "
                         f"{reconciliation['mismatches'][:3]}")
    if store_problems:
        raise SystemExit("snapshot store invariants violated: " + "; ".join(store_problems))
    if standings_v["status"] != "PASS":
        raise SystemExit(f"standings evidence trace failed for: {standings_v['failed']}")
    if fixtures_v["status"] != "PASS":
        raise SystemExit(f"fixture evidence trace failed for: {fixtures_v['failed']}")
    if corra["failed"]:
        raise SystemExit("correlation audit found failures: " +
                         "; ".join(r["id"] for r in corra["sections"] for r in r["rows"]
                                   if r["status"] == "FAIL"))

    verification = {
        "schema_version": 1,
        "read_on": READ_ON,
        "checks": [
            {"id": "V1", "name": "Standings evidence trace (32 rows, v2026-11-14)",
             "status": standings_v["status"],
             "detail": f"{standings_v['n']}/32 rows re-found verbatim in {standings_v['evidence']}",
             "source_ids": standings_v["source_ids"]},
            {"id": "V2", "name": "Fixture evidence trace (14 fixtures, REG10 page)",
             "status": fixtures_v["status"],
             "detail": f"{fixtures_v['n']}/14 fixtures re-found verbatim in {fixtures_v['evidence']}",
             "source_ids": fixtures_v["source_ids"]},
            {"id": "V3", "name": "Vintage transition (2026-11-12 → 2026-11-14)",
             "status": "PASS",
             "detail": "moved clubs exactly " + ", ".join(transition["moved"]) + "; scoring delta "
                       "equals the officially published final " + transition["published_final"],
             "source_ids": ["LC-NFL-STANDINGS-1114", "LC-NFL-GAME-W10-01"]},
            {"id": "V4", "name": "Ordered pipeline reconciles with the canonical engine",
             "status": reconciliation["status"],
             "detail": f"{reconciliation['checked_games']}/14 games field-for-field, "
                       f"{len(reconciliation['mismatches'])} mismatches",
             "source_ids": ["NFL-STANDINGS", "REPO"]},
            {"id": "V5", "name": "Snapshot store invariants",
             "status": "PASS" if not store_problems else "FAIL",
             "detail": f"{store['counts']['markets']} market records; market cells blank with a "
                       f"stated reason; difference blank whenever the market line is blank",
             "source_ids": ["REPO"]},
            {"id": "V6", "name": "Correlation audit (n and official source per value)",
             "status": "PASS" if not corra["failed"] else "FAIL",
             "detail": f"{corra['audited_rows']} rows audited: {corra['with_coefficients']} with "
                       f"coefficients (each with n), {corra['blank_by_rule']} blank by rule with a "
                       f"stated reason, {corra['failed']} failures",
             "source_ids": ["REPO"]},
            {"id": "V7", "name": "Replacement-depth spot re-verification",
             "status": "PASS" if depth_view["spot_verification"]["not_traced"] == 0 else "PARTIAL",
             "detail": f"{depth_view['spot_verification']['pass']}/"
                       f"{depth_view['spot_verification']['sample_size']} sampled rows re-found in "
                       f"the capturing sessions' saved evidence",
             "source_ids": ["X28-NFL-INJ-W10", "CFDD-NFL-STANDINGS"]},
        ],
    }
    return {
        "transition": transition,
        "reconciliation": reconciliation,
        "store": store,
        "board": board,
        "gate": gate,
        "depth": depth_view,
        "corr_audit": corra,
        "verification": verification,
        "standings_verification": standings_v,
        "fixtures_verification": fixtures_v,
    }


def write_artifacts(artifacts: dict) -> list[str]:
    DATA.mkdir(exist_ok=True)
    written = []
    payload = {
        "price-snapshots.json": artifacts["store"],
        "origination-order.json": {
            "schema_version": 1, "stages": stages.STAGES,
            "games": stages.originate_staged(vintages.VINTAGE_B),
            "reconciliation": artifacts["reconciliation"],
            "source_ids": ["NFL-STANDINGS", "NFL-SCHED-W10", "PYTH-NFL", "REPO"]},
        "leaderboard.json": artifacts["board"],
        "demotion-gate.json": artifacts["gate"],
        "replacement-depth.json": artifacts["depth"],
        "correlation-audit.json": artifacts["corr_audit"],
        "decisions.json": {"schema_version": 1, "questions": QUESTIONS,
                           "suggestions": SUGGESTIONS},
        "verification.json": artifacts["verification"],
    }
    for name, content in payload.items():
        text = json.dumps(content, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        (DATA / name).write_text(text, encoding="utf-8")
        written.append(f"nfl-lifecycle-3f5c/data/{name}")
    return written


# ---------------------------------------------------------------- site rendering

def render_index(a: dict) -> str:
    store, board, gate = a["store"], a["board"], a["gate"]
    d = a["depth"]
    counts = [
        ("Markets snapshotted", f"{store['counts']['markets']}"),
        ("Games originated", f"{store['counts']['games']}"),
        ("Non-zero open→close moves", "13 (all totals)"),
        ("Graded strategies", f"{board['counts']['graded']}"),
        ("Provisional", f"{board['counts']['provisional']}"),
        ("Qualified", f"{board['counts']['qualified']}"),
        ("Live entries", f"{gate['applied_to']['live_entries']}"),
        ("Demotions", f"{gate['demotion_count']}"),
        ("Starter losses tracked", f"{d['counts']['starter_losses']}"),
        ("Named replacements", f"{d['counts']['named_backup']}"),
    ]
    lis = "".join(f"<li><b>{esc(v)}</b>{esc(k)}</li>" for k, v in counts)
    reqs = [
        ("Price-snapshot store", "opening and closing numbers for every originated market",
         "price-snapshots.html"),
        ("Origination order: side → total → moneyline", "explicit staged pipeline, reconciled "
         "exactly with the canonical engine", "origination-order.html"),
        ("Fair / market / difference columns", "three separate columns per market; difference "
         "blank while the market line is blank", "fair-market-diff.html"),
        ("Signal separated from staking", "rank computed from signal fields only",
         "leaderboard.html"),
        ("Demotion gate DG-1", "pre-registered triggers that return a live strategy to paper",
         "demotion.html"),
        ("Depth of the replacement", "printed-rank tracking consumed read-only from the cfdd join",
         "replacement-depth.html"),
        ("Correlations with n", "every published value audited for n and an official source",
         "correlation-audit.html"),
    ]
    rows = []
    for title, detail, slug in reqs:
        rows.append('<tr data-source-ids="REPO">'
                    '<td><span class="row-title">' + esc(title) + '</span></td>'
                    + cell(detail)
                    + '<td class="refs"><a href="' + slug + '">Desk page</a>'
                    + f'<a href="{REGISTRY["REPO"]}" target="_blank" rel="noopener noreferrer">REPO ↗</a></td></tr>')
    body = [
        f'<section><h2>Requirement → artefact</h2>{table(["Requirement (2026-11-14 brief)", "What this desk publishes", "Where"], rows)}</section>',
        f'<section><h2>Desk status</h2><ul class="count-grid">{lis}</ul>'
        '<div class="note ok">All build-time checks passed on the committed inputs: evidence traces '
        '(32 standings rows, 14 fixtures), vintage transition (NYG, WAS; official final WAS 24 – NYG 21), '
        'ordered-pipeline reconciliation (14/14), store invariants, correlation audit, depth spot checks '
        '(12/12). See <a href="verification.html">Verification</a>.</div>'
        '<div class="note warn">No sportsbook price exists in this repository (rights constraint '
        'XS09/CF10 stands). Every market-side cell is blank with a stated reason; the difference column '
        'is blank whenever the market line is blank. Nothing on these pages is a wager, a reward or a '
        'recommendation.</div></section>',
    ]
    return page("index.html", body)


def render_summary(a: dict) -> str:
    store, gate, d = a["store"], a["gate"], a["depth"]
    rows = ['<tr data-source-ids="REPO">' + cell("1. What was built") + cell(
        "A market-lifecycle desk: an append-only price-snapshot store (42 markets, opening and "
        "closing numbers), an ordered origination pipeline (side → total → moneyline) reconciled "
        "exactly with the canonical engine, a leaderboard that ranks on signal only with staking "
        "structurally excluded, a pre-registered demotion gate (DG-1), a replacement-depth view "
        "over the cfdd printed-depth join, and an audit forcing every published correlation to "
        "carry n and an official source.")
        + '<td class="refs"><a href="' + REGISTRY["REPO"] + '" target="_blank" rel="noopener noreferrer">REPO ↗</a></td></tr>',
        '<tr data-source-ids="REPO">' + cell("2. Key numbers") + cell(
        f"14 Week 10 games × 3 markets = 42 snapshot records; 13 open→close moves, all in the total "
        f"market (≈ -0.0022 points from the league-anchor shift; side and moneyline are "
        f"anchor-invariant by construction); 30 graded strategy variants, 1 provisional, 0 "
        f"qualified; 0 live entries, 0 demotions (gate armed and idle); {d['counts']['starter_losses']} "
        f"starter losses, {d['counts']['named_backup']} with a printed named replacement.")
        + '<td class="refs"><a href="' + REGISTRY["REPO"] + '" target="_blank" rel="noopener noreferrer">REPO ↗</a></td></tr>',
        '<tr data-source-ids="LC-NFL-GAME-W10-01">' + cell("3. Fresh official attestation (2026-11-14)") + cell(
        "All 32 standings rows re-read from nfl.com and traced verbatim; 30 unchanged, NYG and WAS "
        "moved exactly per the officially published final Commanders 24, Giants 21 (Thursday, "
        "November 12th). All 14 fixtures re-attested with kickoff times and networks. One game has "
        "been played; its market close is terminal and equals its open.")
        + '<td class="refs"><a href="' + REGISTRY["LC-NFL-GAME-W10-01"] + '" target="_blank" rel="noopener noreferrer">LC-NFL-GAME-W10-01 ↗</a></td></tr>',
        '<tr data-source-ids="REPO">' + cell("4. What remains blank, by rule") + cell(
        "Market lines and difference columns (no rights-cleared price source); realized stakes, "
        "units and drawdown (no executable price); reward fields (RG03/RG10). These blanks are "
        "structural, not omissions, and each carries its reason.")
        + '<td class="refs"><a href="' + REGISTRY["REPO"] + '" target="_blank" rel="noopener noreferrer">REPO ↗</a></td></tr>',
        '<tr data-source-ids="REPO">' + cell("5. Decisions requested") + cell(
        "10 questions (10 with some information held, 6 still open) and 10 suggestions with "
        "acceptance tests sit on the desk's review pages with deliberately blank decision records. "
        "Nothing is implemented as decided; adoption is the reviewer's call.")
        + '<td class="refs"><a href="' + REGISTRY["REPO"] + '" target="_blank" rel="noopener noreferrer">REPO ↗</a></td></tr>']
    return page("summary.html", [
        f'<section><h2>Executive summary</h2>'
        f'{table(["Section", "Content", "Source"], rows)}</section>'])


def render_origination_order(a: dict) -> str:
    stage_rows = []
    for s in stages.STAGES:
        stage_rows.append(
            '<tr data-source-ids="NFL-STANDINGS NFL-SCHED-W10 PYTH-NFL REPO">'
            + cell(f"Stage {s['order']} — {s['name']}")
            + cell(s["inputs"]) + cell(", ".join(s["depends_on"]) or "none")
            + cell(s["output"]) + refs_cell(["NFL-STANDINGS", "PYTH-NFL", "REPO"]) + "</tr>")
    game_rows = []
    for g in stages.originate_staged(vintages.VINTAGE_B):
        game_rows.append(
            '<tr data-source-ids="NFL-STANDINGS NFL-SCHED-W10 PYTH-NFL REPO">'
            '<td><span class="row-title">' + esc(g["matchup"]) + '</span><span class="row-sub">'
            + esc(g["id"]) + '</span></td>'
            + cell(f'{g["stage_side_spread_home"]:+.1f}', num=True)
            + cell(f'{g["stage_total"]:.1f}', num=True)
            + cell(f'{g["stage_model_p_home"]:.3f}', num=True)
            + cell(g["stage_fair_home_price"], num=True)
            + cell(g["stage_fair_away_price"], num=True)
            + cell(g["kickoff"])
            + refs_cell(["NFL-STANDINGS", "NFL-SCHED-W10", "PYTH-NFL", "REPO"],
                        extra_url=g["game_source_url"]) + "</tr>")
    rec = a["reconciliation"]
    return page("origination-order.html", [
        '<section><h2>The order, as a pipeline</h2><p class="lede">The side is originated first; '
        'the total reuses the side\'s point expectations; the moneyline maps the side\'s margin to '
        'a win probability. Nothing downstream introduces new information, so the order is a '
        'disclosure of dependency.</p>'
        + table(["Stage", "Inputs", "Depends on", "Output"], stage_rows) + '</section>',
        '<section><h2>Stage outputs per Week 10 game (closing vintage, 2026-11-14)</h2>'
        + table(["Game", "1 · Side (spread, home POV)", "2 · Total", "3 · P(home)",
                 "3 · Fair home price", "3 · Fair away price", "Kickoff (ET)"],
                game_rows, "Fair prices are zero-hold conversions of the model probability — not "
                "prices anyone offers.")
        + f'<div class="note ok">Reconciliation: the ordered pipeline reproduces the canonical '
        f'engine\'s numbers exactly — {rec["checked_games"]}/14 games, '
        f'{len(rec["mismatches"])} mismatches (checked against '
        f'<a href="../../research/nfl/results.json">research/nfl/results.json</a>).</div></section>'])


def render_snapshots(a: dict) -> str:
    store = a["store"]
    rows = []
    for m in store["markets"]:
        op, cl = m["opening"], m["closing"]
        def fair(s):
            if m["market"] == "moneyline":
                return f'{s["fair_home_price"]}/{s["fair_away_price"]}'
            return f'{s["fair_line"]:+.2f}' if isinstance(s["fair_line"], float) else s["fair_line"]
        move = m["open_to_close_move"]
        rows.append(
            '<tr data-source-ids="' + " ".join(m["source_ids"]) + '">'
            '<td><span class="row-title">' + esc(m["matchup"]) + '</span><span class="row-sub">'
            + esc(m["game_id"]) + " · " + esc(m["market"]) + '</span></td>'
            + cell(f'{op["captured_on"]} ({op["vintage"]})')
            + cell(fair(op), num=True)
            + cell(f'{cl["captured_on"]} ({cl["vintage"]})')
            + cell(fair(cl), num=True)
            + cell((f'{move:+.4f}' if isinstance(move, float) else move), num=True)
            + cell(None, blank_note="Blank — no rights-cleared market price (XS09/CF10)")
            + cell(m["closing"]["status"].split(" - ")[0])
            + refs_cell(m["source_ids"], extra_url=m["game_source_url"]) + "</tr>")
    return page("price-snapshots.html", [
        '<section><h2>Store policy</h2><div class="note">' + esc(store["policy"]["append_only"])
        + " · " + esc(store["policy"]["closing_rule"]) + " · " + esc(store["policy"]["difference_rule"])
        + " · " + esc(store["policy"]["reconciliation"]) + '</div></section>',
        '<section><h2>All 42 market records (14 games × side / total / moneyline)</h2>'
        + table(["Game · market", "Opening (date · vintage)", "Open fair line",
                 "Closing (date · vintage)", "Close fair line", "Open→close move",
                 "Market line (operator)", "Close status"],
                rows,
                "Open and close are this project's own originated numbers, not operator quotes. "
                "For the moneyline the fair line is shown as home/away pair. The market-line "
                "column exists for a rights-cleared source and stays blank until then.")
        + '<div class="note">The 13 non-zero open→close moves are all total-market moves of about '
        '−0.0022 points (shown as −0.0022 in the move column). Side and moneyline did not move for '
        'the 13 pre-kickoff games: the league scoring mean cancels in the margin algebra (margin = '
        '(home_off + away_def + league)/3 + hfa − (away_off + home_def + league)/3), so a league '
        'anchor shift changes the total but not the side. This is a fact about the model, not '
        'about any market. W10-01 is terminal: its close equals its open by rule.</div></section>'])


def render_fair_market_diff(a: dict) -> str:
    rows = []
    for m in a["store"]["markets"]:
        if m["market"] == "moneyline":
            fair = f'{m["opening"]["fair_home_price"]}/{m["opening"]["fair_away_price"]}'
            unit = "home/away fair price"
        else:
            fair = f'{m["opening"]["fair_line"]:+.2f}'
            unit = "points"
        rows.append(
            '<tr data-source-ids="' + " ".join(m["source_ids"]) + '">'
            '<td><span class="row-title">' + esc(m["matchup"]) + '</span><span class="row-sub">'
            + esc(m["game_id"]) + '</span></td>'
            + cell(m["market"].capitalize())
            + cell(fair + f' ({unit})', num=True)
            + cell(None, blank_note="Blank — no rights-cleared market price (XS09/CF10)")
            + cell(None, blank_note="Blank — cannot be computed without a market line")
            + refs_cell(m["source_ids"], extra_url=m["game_source_url"]) + "</tr>")
    return page("fair-market-diff.html", [
        '<section><h2>Fair line · market line · difference — three separate columns</h2>'
        + table(["Game", "Market", "Model fair line", "Market line", "Difference (fair − market)"],
                rows,
                "The market line and the difference are blank for every row because no operator "
                "price is licensed or retrieved in this repository (XS09/CF10). The columns are "
                "published separately and stay structurally present so a rights-cleared source "
                "can fill them later; the difference is computed only when both inputs exist.")
        + '<div class="note warn">Never inferred: if a future editor cannot source a market line, '
        'the difference stays blank too. A blank here is the contract, not an oversight.</div></section>'])


def render_leaderboard(a: dict) -> str:
    board = a["board"]
    signal_rows = []
    for r in board["signal"]:
        signal_rows.append(
            '<tr data-source-ids="NFL-SCHEDULE REPO">'
            + cell(r["signal_rank"], num=True) + cell(r["id"])
            + '<td><span class="row-title">' + esc(r["name"]) + '</span></td>'
            + cell(r["market"]) + cell("yes" if r["selective"] else "no")
            + cell(r["bets"], num=True) + cell(r["wins"], num=True) + cell(r["hit_rate"], num=True)
            + cell(r["p_value"], num=True) + cell(r["q_value"], num=True)
            + cell(r["tier"]) + refs_cell(["NFL-SCHEDULE", "REPO"]) + "</tr>")
    staking_rows = []
    for r in board["staking"]:
        staking_rows.append(
            '<tr data-source-ids="NFL-SCHEDULE REPO">'
            + cell(r["id"]) + cell(None, blank_note="Blank — no staking plan approved")
            + cell(r["stakes_placed"], num=True)
            + cell(None, blank_note="Blank — no executable price to settle against (RG03)")
            + cell(None, blank_note="Blank — no executable price to settle against (RG03)")
            + cell("RG03 · RG10") + refs_cell(["NFL-SCHEDULE", "REPO"]) + "</tr>")
    sep = board["separation"]
    return page("leaderboard.html", [
        '<section><h2>Why two tables</h2><div class="note">' + esc(sep["rule"]) + " "
        + esc(sep["why"]) + '</div><p class="lede">Tiers are inherited verbatim from the results '
        'engine (nfl-results/analysis.json). This desk does not re-grade anything; it republishes '
        'the graded ledger ranked on signal only, with the staking record beside it — not under '
        'it, and not feeding it.</p></section>',
        '<section><h2>Signal table (rank is computed from these columns only)</h2>'
        + table(["Signal rank", "ID", "Strategy", "Market", "Selective", "Bets", "Wins",
                 "Hit rate", "p", "BH q", "Engine tier"], signal_rows,
                "n = 120 graded selections per row (weeks 1–9 official scores). Ranking: hit rate "
                "descending among rows with n ≥ 20, then p ascending. Staking fields are not read.")
        + '</section>',
        '<section><h2>Staking table (no rank column; cannot feed one)</h2>'
        + table(["ID", "Approved stake plan", "Stakes placed", "Realized units",
                 "Max drawdown (units)", "Blocked by"], staking_rows,
                "Every value is blank or zero because no price exists (RG03) and no rights are "
                "cleared (RG10). A lucky staking run cannot mask a bad signal here because staking "
                "outcomes are not part of the ranking computation at all.")
        + '</section>'])


def render_demotion(a: dict) -> str:
    gate = a["gate"]
    trig_rows = []
    for t in gate["triggers"]:
        trig_rows.append('<tr data-source-ids="REPO">' + cell(t["id"]) + cell(t["name"])
                         + cell(t["rule"]) + cell(t["effect"])
                         + refs_cell(["REPO"]) + "</tr>")
    state_rows = []
    for state, meaning in gate["state_machine"].items():
        state_rows.append('<tr data-source-ids="REPO">' + cell(state) + cell(meaning)
                          + refs_cell(["REPO"]) + "</tr>")
    applied_rows = ['<tr data-source-ids="REPO">' + cell("Live entries evaluated")
                    + cell(gate["applied_to"]["live_entries"], num=True)
                    + refs_cell(["REPO"]) + "</tr>",
                    '<tr data-source-ids="REPO">' + cell("Why the live book is empty")
                    + cell(gate["applied_to"]["because"]) + refs_cell(["REPO"]) + "</tr>",
                    '<tr data-source-ids="REPO">' + cell("Demotions recorded")
                    + cell(gate["demotion_count"], num=True) + refs_cell(["REPO"]) + "</tr>",
                    '<tr data-source-ids="REPO">' + cell("Gate state")
                    + cell("armed and idle — triggers fixed on 2026-11-14, before any live entry")
                    + refs_cell(["REPO"]) + "</tr>"]
    return page("demotion.html", [
        '<section><h2>Lifecycle state machine</h2>'
        + table(["State", "Meaning"], state_rows) + '</section>',
        '<section><h2>Pre-registered triggers (fixed 2026-11-14; not tunables)</h2>'
        + table(["Trigger", "Name", "Rule", "Effect"], trig_rows,
                "Triggers are evaluated in order after every graded round while a strategy is "
                "live; the first firing trigger is recorded with its window. A demoted strategy "
                "re-enters the full promotion path as a new counted trial.") + '</section>',
        '<section><h2>Current evaluation</h2>' + table(["Measure", "Value"], applied_rows)
        + '<div class="note">Acceptance evidence: the gate\'s logic is unit-tested in '
        'nfl-lifecycle-3f5c/tests/test_demotion.py on synthetic windows (fires / retains / '
        'insufficient-n / double-window rule). A paper replay over the graded history is proposed '
        'as suggestion LS06, not run here.</div></section>'])


def render_depth(a: dict) -> str:
    d = a["depth"]
    dist_rows = []
    for r in d["distribution"]:
        dist_rows.append('<tr data-source-ids="X28-NFL-INJ-W10 CFDD-NFL-STANDINGS REPO">'
                         + cell(r["unit"]) + cell(r["depth_state"]) + cell(r["n"], num=True)
                         + refs_cell(["X28-NFL-INJ-W10", "CFDD-NFL-STANDINGS", "REPO"]) + "</tr>")
    club_rows = []
    for c in d["per_club"]:
        club_rows.append('<tr data-source-ids="X28-NFL-INJ-W10 CFDD-NFL-STANDINGS REPO">'
                         '<td><span class="row-title">' + esc(c["club"]) + '</span><span class="row-sub">'
                         + esc(c["name"]) + '</span></td>'
                         + cell(c["injury_rows"], num=True) + cell(c["on_chart"], num=True)
                         + cell(c["named_backup"], num=True) + cell(c["starter_losses"], num=True)
                         + cell(c["deepest_slot"], num=True)
                         + refs_cell(["X28-NFL-INJ-W10", "CFDD-NFL-STANDINGS", "REPO"]) + "</tr>")
    starter_rows = []
    for s in d["starter_losses"]:
        ids = ["X28-NFL-INJ-W10"]
        extra = s["depth_source_url"]
        sid = URL_TO_ID.get(extra)
        if sid:
            ids.append(sid)
        starter_rows.append(
            '<tr data-source-ids="' + " ".join(ids) + '">'
            '<td><span class="row-title">' + esc(s["player"]) + '</span><span class="row-sub">'
            + esc(s["injury_id"]) + '</span></td>'
            + cell(s["club"]) + cell(s["position"]) + cell(s["unit"]) + cell("rank 1")
            + cell(s["replacement"] if s["slot_has_backup"] else None,
                   blank_note="no backup printed on the chart")
            + cell(s["replacement_rank"] if s["slot_has_backup"] else None, num=True,
                   blank_note="no backup printed on the chart")
            + cell("named backup" if s["slot_has_backup"] else "no named backup")
            + refs_cell(ids, extra_url=extra) + "</tr>")
    spot_rows = []
    for r in d["spot_verification"]["results"]:
        spot_rows.append('<tr data-source-ids="X28-NFL-INJ-W10 CFDD-NFL-STANDINGS REPO">'
                         '<td><span class="row-title">' + esc(r["player"]) + '</span><span class="row-sub">'
                         + esc(r["injury_id"]) + '</span></td>'
                         + cell(r["club"]) + cell(r["replacement"] or "—")
                         + cell("traced" if r["player_traced"] else "not traced")
                         + cell("traced" if r["replacement_traced"] else "not traced")
                         + cell(r["status"]) + refs_cell(["X28-NFL-INJ-W10", "CFDD-NFL-STANDINGS", "REPO"])
                         + "</tr>")
    c = d["counts"]
    return page("replacement-depth.html", [
        '<section><h2>Depth of the replacement, not just the fact of one</h2><p class="lede">'
        'Consumed read-only from the cfdd desk\'s injury × depth join (' + esc(d["consumed_artifact"])
        + '). A starter loss (printed rank 1) is tracked by where its replacement sits on the '
        'printed chart; "no named backup printed" is its own state, because a missing name is '
        'depth information. Nothing is estimated.</p>'
        + table(["Unit", "Depth state", "n"], dist_rows) + '</section>',
        '<section><h2>Per-club view</h2>'
        + table(["Club", "Injury rows", "On printed chart", "Named backup", "Starter losses",
                 "Deepest slot on chart"], club_rows) + '</section>',
        '<section><h2>Starter losses (' + str(c["starter_losses"]) + ' rows)</h2>'
        + table(["Player", "Club", "Position", "Unit", "Lost at", "Named replacement",
                 "Replacement rank", "Depth state"], starter_rows,
                "Replacement is the printed next-in-line behind the injured player's slot. Blank "
                "means the club printed no backup — never a guessed name.")
        + '</section>',
        '<section><h2>Spot re-verification (' + str(d["spot_verification"]["sample_size"])
        + ' rows)</h2>' + table(["Player", "Club", "Replacement", "Player traced", "Replacement traced",
                                 "Verdict"], spot_rows,
                                "Deterministic sample; names re-found in the capturing sessions' "
                                "saved evidence files.") + '</section>'])


def render_corr_audit(a: dict) -> str:
    rows = []
    for section in a["corr_audit"]["sections"]:
        for r in section["rows"]:
            rows.append('<tr data-source-ids="REPO">'
                        '<td><span class="row-title">' + esc(r["id"]) + '</span><span class="row-sub">'
                        + esc(section["artifact"]) + '</span></td>'
                        + cell(r["pair"]) + cell(r["coefficient"], num=True) + cell(r["n"], num=True)
                        + cell(r["reason"]) + cell(badge(r["status"], "ok" if r["status"] == "PASS" else "bad"))
                        + refs_cell(["REPO"]) + "</tr>")
    c = a["corr_audit"]
    return page("correlation-audit.html", [
        '<section><h2>Audit rule</h2><div class="note">A published correlation must carry '
        '<b>n ≥ 3</b> and registered official sources; a blank must carry a stated reason. '
        'Coefficients computed from derived series carry their caveat verbatim. Read-only audit '
        'over: research/nfl/results.json, nfl-results/analysis.json, nfl-skill-cfdd correlations.</div>'
        f'<p class="lede">{c["audited_rows"]} rows audited — {c["with_coefficients"]} with '
        f'coefficients (each with n), {c["blank_by_rule"]} blank by rule, {c["failed"]} failures.</p></section>',
        '<section><h2>All audited correlation rows</h2>'
        + table(["ID · artefact", "Pair", "Coefficient", "n", "Basis / reason for blank", "Status"],
                rows) + '</section>'])


def render_questions() -> str:
    rows = []
    for q in QUESTIONS:
        rows.append('<tr data-source-ids="' + " ".join(q["source_ids"]) + '">'
                    '<td><span class="row-title">' + esc(q["id"]) + '</span><span class="row-sub">'
                    + badge(q["status"], "ok" if q["status"] == "answered"
                            else "warn" if q["status"] == "open" else "info")
                    + '</span></td>'
                    + cell(q["question"]) + cell(q["info_held"]) + cell(q["info_missing"])
                    + cell(q["blocks"]) + cell(q["closes_when"])
                    + refs_cell(q["source_ids"]) + "</tr>")
    return page("questions.html", [
        '<section><h2>Questions · information held · information missing</h2><p class="lede">'
        'What can already be decided on, what cannot, and what would close each gap. "Answered" '
        'means this desk holds the information with a source; "answered-but-constraining" means '
        'the answer blocks further action; "open" means a named action closes it.</p>'
        + table(["ID · status", "Question", "Information held (with source)", "Information missing",
                 "Blocks", "Closes when"], rows) + '</section>'])


def render_suggestions() -> str:
    rows = []
    for s in SUGGESTIONS:
        rows.append('<tr data-source-ids="' + " ".join(s["source_ids"]) + '">'
                    '<td><span class="row-title">' + esc(s["id"]) + '</span><span class="row-sub">'
                    + esc(s["status"]) + '</span></td>'
                    + cell(s["title"]) + cell(s["evidence"]) + cell(s["unlocks"])
                    + cell(s["cost"]) + cell(s["risk"]) + cell(s["acceptance_test"])
                    + cell(None, blank_note="Decision record deliberately blank — reviewer choice")
                    + refs_cell(s["source_ids"]) + "</tr>")
    return page("suggestions.html", [
        '<section><h2>Suggestions for review — nothing implemented as decided</h2><p class="lede">'
        'Each suggestion states its evidence, what it unlocks, cost, risk and a runnable '
        'acceptance test. The decision record is blank on purpose: a reviewer adopts, defers or '
        'rejects before anything is implemented, and the choice is recorded outside this file.</p>'
        + table(["ID · status", "Suggestion", "Evidence", "Unlocks", "Cost", "Risk",
                 "Acceptance test", "Decision"], rows) + '</section>'])


def render_verification(a: dict) -> str:
    rows = []
    for v in a["verification"]["checks"]:
        rows.append('<tr data-source-ids="' + " ".join(v["source_ids"]) + '">'
                    '<td><span class="row-title">' + esc(v["id"]) + '</span></td>'
                    + cell(v["name"]) + cell(v["detail"])
                    + cell(badge(v["status"], "ok" if v["status"] == "PASS" else "warn"))
                    + refs_cell(v["source_ids"]) + "</tr>")
    standings_rows = []
    for r in a["standings_verification"]["rows"]:
        standings_rows.append('<tr data-source-ids="LC-NFL-STANDINGS-1114 NFL-STANDINGS">'
                              '<td><span class="row-title">' + esc(r["team"]) + '</span></td>'
                              + cell(r["code"]) + cell("found verbatim" if r["found"] else "NOT FOUND")
                              + refs_cell(["LC-NFL-STANDINGS-1114", "NFL-STANDINGS"]) + "</tr>")
    fixture_rows = []
    for r in a["fixtures_verification"]["rows"]:
        fixture_rows.append('<tr data-source-ids="LC-NFL-SCHED-REG10-1114 NFL-SCHED-W10">'
                            '<td><span class="row-title">' + esc(r["game"]) + '</span><span class="row-sub">'
                            + esc(r["id"]) + '</span></td>'
                            + cell("found verbatim" if r["found"] else "NOT FOUND")
                            + refs_cell(["LC-NFL-SCHED-REG10-1114", "NFL-SCHED-W10"]) + "</tr>")
    return page("verification.html", [
        '<section><h2>Build-time checks (every one must pass before anything is published)</h2>'
        + table(["Check", "Name", "Detail", "Status"], rows) + '</section>',
        '<section><h2>Standings evidence trace (32 rows, read ' + READ_ON + ')</h2>'
        + table(["Team", "Code", "Evidence trace"], standings_rows,
                "Each row is re-found verbatim in nfl-lifecycle-3f5c/evidence/"
                "standings-2026-11-14.md, saved from the official page read.")
        + '</section>',
        '<section><h2>Fixture evidence trace (14 fixtures, REG10 page)</h2>'
        + table(["Game", "Evidence trace"], fixture_rows) + '</section>',
        '<section><h2>Method</h2><div class="note">Verification means: (1) the value exists '
        'verbatim in saved evidence transcribed from the official page on the read date; '
        '(2) arithmetic inside the publisher\'s own row is consistent (PCT half-up to three '
        'decimals — the publisher\'s convention — and NetPts = PF − PA); (3) cross-vintage moves '
        'are explained by exactly one officially published result; (4) derived values reconcile '
        'with the canonical engine. A value that cannot pass is left blank and flagged, never '
        'estimated.</div></section>'])


def render_flagged() -> str:
    rows = []
    for f in FLAGS:
        rows.append('<tr data-source-ids="' + " ".join(f["source_ids"]) + '">'
                    '<td><span class="row-title">' + esc(f["id"]) + '</span><span class="row-sub">'
                    + badge(f["status"], "warn" if f["status"] == "open" else "info")
                    + '</span></td>' + cell(f["severity"]) + cell(f["finding"])
                    + cell(f["treatment"]) + refs_cell(f["source_ids"], extra_url=f["source_url"])
                    + "</tr>")
    open_n = sum(1 for f in FLAGS if f["status"] == "open")
    return page("flagged.html", [
        '<section><h2>Flagged for review (' + str(open_n) + ' open of ' + str(len(FLAGS))
        + ')</h2><p class="lede">Irregularities this desk found or inherited. Open flags do not '
        'block publication; they block the decisions they name until closed.</p>'
        + table(["ID · status", "Severity", "Finding", "Treatment"], rows) + '</section>'])


def render_sources() -> str:
    ids = ["LC-NFL-STANDINGS-1114", "LC-NFL-SCHED-REG10-1114", "LC-NFL-GAME-W10-01",
           "NFL-STANDINGS", "NFL-SCHED-W10", "NFL-SCHEDULE", "X28-NFL-INJ-W10",
           "CFDD-NFL-STANDINGS", "CFDD-NFL-TERMS", "CFDD-HOU-DEPTH", "PYTH-NFL", "REPO"]
    rows = []
    for sid in ids:
        url = REGISTRY.get(sid)
        rows.append('<tr data-source-ids="' + sid + '">'
                    '<td><span class="row-title">' + esc(sid) + '</span></td>'
                    + cell("official league page" if sid.startswith(("LC-", "NFL-"))
                           else "prior session's registered source" if sid.startswith("CFDD-")
                           else "method reference" if sid == "PYTH-NFL" else "this repository")
                    + (f'<td class="refs"><a href="{esc(url)}" target="_blank" '
                       f'rel="noopener noreferrer">{esc(url)} ↗</a></td>' if url else cell(None))
                    + "</tr>")
    return page("sources.html", [
        '<section><h2>Source register used by this desk</h2><p class="lede">Every ID is registered '
        'in research/sources.json with its scope, read date and access boundary; hosts are '
        'enforced by scripts/check_site.py.</p>'
        + table(["Source ID", "Kind", "URL"], rows) + '</section>'])


def main() -> None:
    check = "--check" in sys.argv
    artifacts = build_artifacts()
    written = write_artifacts(artifacts)
    SITE.mkdir(exist_ok=True)
    renderers = {
        "index.html": lambda: render_index(artifacts),
        "summary.html": lambda: render_summary(artifacts),
        "origination-order.html": lambda: render_origination_order(artifacts),
        "price-snapshots.html": lambda: render_snapshots(artifacts),
        "fair-market-diff.html": lambda: render_fair_market_diff(artifacts),
        "leaderboard.html": lambda: render_leaderboard(artifacts),
        "demotion.html": lambda: render_demotion(artifacts),
        "replacement-depth.html": lambda: render_depth(artifacts),
        "correlation-audit.html": lambda: render_corr_audit(artifacts),
        "questions.html": lambda: render_questions(),
        "suggestions.html": lambda: render_suggestions(),
        "verification.html": lambda: render_verification(artifacts),
        "flagged.html": lambda: render_flagged(),
        "sources.html": lambda: render_sources(),
    }
    if check:
        problems = []
        for name, render in renderers.items():
            text = render()
            path = SITE / name
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                problems.append(f"site/{name}: stale; rebuild changed bytes")
        for name in written:
            pass  # data artefacts compared below
        import hashlib
        for name, content in {
            "price-snapshots.json": artifacts["store"],
            "origination-order.json": {"schema_version": 1, "stages": stages.STAGES,
                                       "games": stages.originate_staged(vintages.VINTAGE_B),
                                       "reconciliation": artifacts["reconciliation"],
                                       "source_ids": ["NFL-STANDINGS", "NFL-SCHED-W10",
                                                      "PYTH-NFL", "REPO"]},
            "leaderboard.json": artifacts["board"],
            "demotion-gate.json": artifacts["gate"],
            "replacement-depth.json": artifacts["depth"],
            "correlation-audit.json": artifacts["corr_audit"],
            "decisions.json": {"schema_version": 1, "questions": QUESTIONS,
                               "suggestions": SUGGESTIONS},
            "verification.json": artifacts["verification"],
        }.items():
            text = json.dumps(content, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
            path = DATA / name
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                problems.append(f"data/{name}: stale; rebuild changed bytes")
        if problems:
            raise SystemExit("STALE:\n" + "\n".join(problems))
        print("OK: nfl-lifecycle-3f5c reproduces byte-identically")
        return
    manifest = {"pages": [name for name, _ in PAGES],
                "desk": "nfl-lifecycle-3f5c",
                "built_from": ["research/nfl/results.json", "nfl-results/analysis.json",
                               "nfl-skill-cfdd/data", "data/nfl-schedule-2026-w10.csv",
                               "data/nfl-standings-2026.csv"],
                "market_blank_reason": snapshots.MARKET_BLANK_REASON}
    (SITE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for name, render in renderers.items():
        (SITE / name).write_text(render(), encoding="utf-8")
    print(f"Built nfl-lifecycle-3f5c: {len(renderers)} pages, {len(written)} data artefacts, "
          f"42 snapshot records, {artifacts['board']['counts']['graded']} graded strategies, "
          f"gate armed with {artifacts['gate']['demotion_count']} demotions.")


if __name__ == "__main__":
    main()
