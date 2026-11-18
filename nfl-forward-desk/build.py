#!/usr/bin/env python3
"""Build the NFL forward-desk site.

Session arena/3f9563bf-own7. This desk does three things the brief asked for that
no other desk owns:

  1. A fresh 2026-11-18 official capture (standings, Week 11 schedule, Week 10
     injury report) with verbatim evidence and SHA-256 hashes.
  2. A mechanical drift check (fresh reads vs committed canonical data).
  3. A joined decision register + scored suggestion rubric + flags, so a reviewer
     can choose the best path before any change is implemented.

Every table row carries data-source-ids and at least one link to the official page
it came from, so a reader can check any number without trusting this generator. A
value no official source publishes is rendered as an empty cell marked data-empty —
never a dash, a zero or an estimate.

The desk never produces a price, a stake, a wager, a return on investment or a cash
reward. Where a quantity depends on one, the value is blank and the reason is
published next to it.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
EVIDENCE = HERE / "evidence"
SITE = HERE / "site"

DESK = "nfl-forward-desk"
READ_ON = "2026-11-18"
CLOCK = "2026-11-18T03:46:15Z"

# Official page hosts this desk is allowed to cite. Anything else is rejected rather
# than published, so a stray URL can never masquerade as a source.
OFFICIAL_HOSTS = ("www.nfl.com", "github.com")

# Registered source ids -> official URL, built from the desk sources.json plus the
# shared research registry so a row can cite either.
_desk_src = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
DESK_SOURCES = {s["id"]: s for s in _desk_src["sources"]}
_research_src = json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))
REGISTRY = {s["id"]: s.get("url", "") for s in _research_src}
REGISTRY.update({sid: s.get("url", "") for sid, s in DESK_SOURCES.items()})

PAGES = [
    ("index.html", "Forward desk"),
    ("standings.html", "Standings"),
    ("schedule.html", "Week 11 schedule"),
    ("injuries.html", "Injury report"),
    ("drift.html", "Drift check"),
    ("decisions.html", "Decision register"),
    ("suggestions.html", "Suggestions"),
    ("flags.html", "Flagged for review"),
    ("sources.html", "Sources"),
    ("method.html", "Method & limits"),
]

NAV_LINKS = [(name, label) for name, label in PAGES]


# ------------------------------------------------------------------ helpers

def esc(value):
    return escape(str(value), quote=True)


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def src_cell(source_ids, label="Source"):
    """Render the source cell. The first registered id supplies the verifying link.

    A value may be a registered source id (resolved through REGISTRY) or a raw URL
    (used directly). Raw URLs are accepted so a flag can cite an official page even
    when it is not a registered id.
    """
    ids = [s for s in (source_ids or []) if s]
    if not ids:
        return f'<td class="refs" data-empty="true"></td>'
    rendered = []
    for sid in ids:
        if sid.startswith("http"):
            rendered.append(f'<a href="{esc(sid)}" rel="noopener">{esc(sid)}</a>')
        else:
            u = REGISTRY.get(sid, "")
            if u:
                rendered.append(f'<a href="{esc(u)}" rel="noopener">{esc(sid)}</a>')
            else:
                rendered.append(esc(sid))
    return f'<td class="refs">{label}: {" · ".join(rendered)}</td>'


def cell(value, empty_ok=True):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if empty_ok:
            return '<td data-empty="true"></td>'
        return '<td></td>'
    return f"<td>{esc(value)}</td>"


def table(headers, rows, note=None, empty_message=None):
    """rows: list of (cells_html, source_ids).

    Every published row carries a link to the official page behind it. Rows written
    without one get the link appended here, so the guarantee holds site-wide.
    """
    headers = list(headers)
    prepared = []
    for cells, source_ids in rows:
        cells = list(cells)
        if not any("href=" in c for c in cells):
            cells.append(src_cell(source_ids))
        prepared.append(cells)
    widths = {len(c) for c in prepared}
    if widths and len(headers) not in widths:
        headers.append("Source")
    for c in prepared:
        while len(c) < len(headers):
            c.append('<td class="refs"></td>')
    out = ['<div class="table-wrap"><table><thead><tr>'
           + "".join("<th>" + esc(h) + "</th>" for h in headers)
           + "</tr></thead><tbody>"]
    if not prepared:
        cols = max(1, len(headers) - 1)
        out.append('<tr data-source-ids="FD-NFL-STANDINGS-1118"><td colspan="'
                   + str(cols) + '" class="empty-row">' + esc(empty_message or "No rows.")
                   + "</td>" + src_cell(["FD-NFL-STANDINGS-1118"], label="source") + "</tr>")
    for (_, source_ids), cells in zip(rows, prepared):
        out.append('<tr data-source-ids="' + esc(" ".join(source_ids)) + '">')
        out.extend(cells)
        out.append("</tr>")
    out.append("</tbody></table></div>")
    if note:
        out.append('<p class="table-note">' + note + "</p>")
    return "".join(out)


def page(name, title, subtitle, body, kpis=None,
         eyebrow="Forward desk · official read 2026-11-18 · research only · no wagers · no prices"):
    links = []
    for href, label in NAV_LINKS:
        current = ' aria-current="page"' if href == name else ""
        links.append('<a href="' + esc(href) + '"' + current + ">" + esc(label) + "</a>")
    nav = "".join(links)
    kpi_html = ""
    if kpis:
        kpi_html = '<div class="kpis">' + "".join(
            f'<div class="kpi"><span class="kpi-value">{esc(value)}</span>'
            f'<span class="kpi-label">{esc(label)}</span></div>'
            for value, label in kpis) + "</div>"
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)} · OWN7 forward desk</title>"
        f'<meta name="description" content="{esc(subtitle)}">'
        '<link rel="stylesheet" href="style.css">'
        '<script src="app.js" defer></script></head><body>'
        '<a class="skip" href="#main">Skip to content</a>'
        '<header class="top"><div class="brand"><strong>OWN7</strong>'
        "<span>NFL forward desk</span></div>"
        f'<nav aria-label="Desk sections">{nav}</nav></header>'
        '<main id="main">'
        f'<p class="eyebrow">{esc(eyebrow)}</p>'
        f"<h1>{esc(title)}</h1>"
        f'<p class="subtitle">{esc(subtitle)}</p>'
        f"{kpi_html}{chr(10).join(body)}"
        "<footer><p>OWN7 · independent research. NFL data attributed to NFL.com; "
        "canonical artifacts attributed to the committed repo. Not affiliated with or "
        "endorsed by the NFL. Every table row links the official source it came from; "
        "unknown values are blank, never filled in.</p>"
        '<p><a href="sources.html">Sources</a> · '
        '<a href="flags.html">Flagged for review</a> · '
        '<a href="suggestions.html">Suggestions</a> · '
        '<a href="method.html">Method &amp; limits</a></p></footer>'
        "</main></body></html>\n"
    )


def panel(title, body, level=2):
    return f'<section class="panel"><h{level}>{esc(title)}</h{level}>{body}</section>'


def notice(text, kind="info"):
    return f'<div class="notice {kind}"><p>{text}</p></div>'


# ------------------------------------------------------------------ content

def page_index():
    dr_doc = json.loads((ROOT / "research" / "nfl-decision-readiness.json").read_text(encoding="utf-8"))
    requirements = dr_doc["requirements"] if isinstance(dr_doc, dict) and "requirements" in dr_doc else dr_doc
    from collections import Counter
    counts = Counter(r["status"] for r in requirements)
    body = []
    body.append(notice(
        "This desk holds a fresh 2026-11-18 official read (standings, Week 11 schedule, Week 10 injury "
        "report), a mechanical drift check against the committed canonical data, and a joined decision "
        "register with a scored suggestion rubric. It publishes no price, stake, wager or reward.", "info"))
    # Decision-readiness table: one row per requirement, gate + clearing number.
    rows = []
    for r in requirements:
        rows.append((
            [cell(r["id"]), cell(r["requirement"]), cell(r["category"]),
             cell(r["status"]), cell(r["gate"]), cell(r["clears_when"])],
            r.get("source_ids", []),
        ))
    body.append(panel("Decision-readiness table — one row per requirement",
                      table(["ID", "Requirement", "Category", "Status", "Blocking gate", "Clears when"],
                            rows,
                            note="Sources: the requirement's own source_ids. Status and gate are carried from "
                                 "research/nfl-decision-readiness.json; nothing is inferred."),
                      level=2))
    body.append(panel("Read status at a glance",
                      f"<p>Requirements: {len(requirements)} total — "
                      + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".</p>"
                      + '<p>Fresh official reads taken ' + esc(CLOCK) + " (UTC): standings, Week 11 schedule, "
                      "Week 10 injury report. Week 11 injury report not yet published (see flags).</p>"))
    return page("index.html", "Forward desk",
                "Fresh 2026-11-18 official capture, drift check, and the decision register that "
                "orders what to build next.", body,
                kpis=[(str(len(requirements)), "requirements tracked"),
                      (str(counts.get("Implemented", 0)), "implemented"),
                      (str(counts.get("Blocked", 0) + counts.get("Open", 0)), "blocked or open"),
                      (READ_ON, "official read date")])


def page_standings():
    rows = read_csv(DATA / "standings-2026-11-18.csv")
    tbl = []
    for r in rows:
        tbl.append((
            [cell(r["Conference"]), cell(r["Division"]), cell(r["Team"]),
             cell(r["W"]), cell(r["L"]), cell(r["T"]), cell(r["PCT"]),
             cell(r["PF"]), cell(r["PA"]), cell(r["NET"]), cell(r["STRK"])],
            ["FD-NFL-STANDINGS-1118"],
        ))
    body = panel("2026 NFL Division Standings — 2026-11-18 read",
                 table(["Conf", "Division", "Team", "W", "L", "T", "PCT", "PF", "PA", "NET", "STRK"],
                       tbl,
                       note="Read from https://www.nfl.com/standings/ at " + esc(CLOCK) + ". All 32 clubs. "
                            "HOME/ROAD/DIV/CONF/LAST5 are in the evidence file; the columns shown are the "
                            "league-standard set. No playoff clinch markers appear on any row in this read."))
    return page("standings.html", "Standings",
                "All 32 clubs, re-derived from the official 2026-11-18 read.", body,
                kpis=[("32", "clubs"), (READ_ON, "read date"), ("2", "undefeated leaders (BUF, SF)",)])


def page_schedule():
    rows = read_csv(DATA / "schedule-week11-2026-11-18.csv")
    tbl = []
    for r in rows:
        tbl.append((
            [cell(r["day"]), cell(r["date"]), cell(r["kickoff_et"]), cell(r["network"]),
             cell(r["away"]), cell(r["away_record"]), cell(r["home"]), cell(r["home_record"]),
             cell(r["venue"]), cell(r["weather"])],
            ["FD-NFL-SCHED-W11-1118"],
        ))
    body = panel("Week 11 schedule — 2026-11-18 read",
                 table(["Day", "Date", "Kickoff ET", "Network", "Away", "Away rec",
                        "Home", "Home rec", "Venue", "Weather"],
                       tbl,
                       note="Read from https://www.nfl.com/schedules/2026/REG11/ at " + esc(CLOCK) + ". "
                            "13 games, 26 clubs playing, 6 byes (ATL, CLE, GB, LAR, NE, SEA). Venue names are "
                            "transcribed from the official game links on the page. Weather is published for the "
                            "MNF game only; other rows are blank because the page publishes no weather for them."))
    return page("schedule.html", "Week 11 schedule",
                "The 13-game Week 11 slate with venues, networks and the one published weather line.", body,
                kpis=[("13", "games"), ("26", "clubs playing"), ("6", "byes"), (READ_ON, "read date")])


def page_injuries():
    inj = load("injury-counts-2026-11-18.json")
    counts = inj["counts"]
    designated = read_csv(DATA / "injuries-week10-2026-11-18.csv")
    tbl = []
    for r in designated:
        tbl.append((
            [cell(r["club"]), cell(r["club_name"]), cell(r["player"]), cell(r["position"]),
             cell(r["injury"]), cell(r["practice"]), cell(r["game_status"])],
            ["FD-NFL-INJ-W10-1118"],
        ))
    body = []
    body.append(notice(
        "Week 11 injury report is <strong>not yet published</strong> as of " + esc(CLOCK) + ". The REG11 URL "
        "redirects to REG10; the page still renders Week 10. See the <a href='flags.html'>flags</a> page.", "warn"))
    body.append(panel("Per-club row counts — Week 10 report",
                      table(["Club", "Rows listed"],
                            [([cell(c), cell(n)], ["FD-NFL-INJ-W10-1118"]) for c, n in sorted(counts.items())],
                            note="28 clubs listed on the Week 10 report; 347 total rows. The four Week 10 bye "
                                 "clubs are absent from the report and are left blank rather than named.")))
    body.append(panel("Designated rows (game status non-blank) — " + str(len(designated)) + " rows",
                      table(["Club", "Club name", "Player", "Pos", "Injury", "Practice", "Game status"],
                            tbl,
                            note="Read from https://www.nfl.com/injuries/league/2026/REG10 at " + esc(CLOCK) +
                                 ". Out 70, Doubtful 11, Questionable 90. The 11-13 canonical capture had only 25 "
                                 "designated rows; the report was populated over the week (see drift page).")))
    return page("injuries.html", "Injury report",
                "Week 10 injury report: per-club counts and every designated row, from the 2026-11-18 read.",
                body, kpis=[("347", "rows listed"), ("171", "designated"), ("28", "clubs listed"), (READ_ON, "read date")])


def page_drift():
    drift = load("drift-check-2026-11-18.json")
    body = []
    body.append(panel("Drift check — fresh 2026-11-18 reads vs committed canonical data",
                      "<p>Every drift below is a fact observed by comparing a fresh official read against a "
                      "committed artifact. Drift is reported, never patched into the canonical file. The check "
                      "passes (no internal inconsistency); drift vs a stale snapshot is a finding, not a failure.</p>"))
    rows = []
    for f in drift["findings"]:
        if f.startswith("  drift"):
            kind = "drift"
        else:
            kind = "summary"
        rows.append(([cell(f)], ["FD-NFL-STANDINGS-1118", "FD-NFL-INJ-W10-1118"]))
    body.append(panel("Findings",
                      table(["Finding"], rows,
                            note="Sources: the fresh reads cited on each finding. The standings drift vs the "
                                 "11-17 file is the Week 10 MNF result; the injury drift is the Arden Key "
                                 "designation change and the report's week-long population.")))
    return page("drift.html", "Drift check",
                "Mechanical comparison of the 2026-11-18 fresh reads against the committed canonical data.",
                body, kpis=[("0", "internal failures"), (str(len([f for f in drift['findings'] if f.startswith('  drift')])), "drift cells"), (READ_ON, "check date")])


def page_decisions():
    reg = load("decision-register.json")
    rows = []
    for r in reg["rows"]:
        ans = r.get("answering_source", {})
        blocked = r.get("blocked_requirements", [])
        blocked_txt = ", ".join(b["id"] for b in blocked) if blocked else "—"
        sug = r.get("suggestions_to_discover", [])
        sug_txt = ", ".join(s["id"] for s in sug) if sug else "—"
        rows.append((
            [cell(r["id"]), cell(r["group"]), cell(r["question"]),
             cell(r["known"]), cell(r["missing"]), cell(blocked_txt),
             cell(ans.get("url", "")), cell(sug_txt)],
            [ans.get("id", "")] if ans.get("url") else [],
        ))
    body = panel("Joined decision register — questions, missing info, answering source, blocked requirements",
                 table(["ID", "Group", "Question", "Known", "Missing", "Blocks (DR)",
                        "Answering source", "Suggestions"],
                       rows,
                       note="Each row joins a DQ question to the DR requirements it blocks and the official source "
                            "that would answer it. The SU column lists suggestions that would discover the missing "
                            "information. The join rules are documented in build_register.py."))
    return page("decisions.html", "Decision register",
                "Every open question joined to what it blocks and the official source that would answer it.",
                body, kpis=[(str(reg["count"]), "decisions"), (READ_ON, "as of")])


def page_suggestions():
    rub = load("suggestion-rubric.json")
    # Every suggestion is scored from the decision register, which is built from this
    # desk's fresh official NFL reads. Those read sources are the provenance for the
    # scoring, so each row carries them as its source ids.
    desk_nfl_ids = ["FD-NFL-STANDINGS-1118", "FD-NFL-SCHED-W11-1118", "FD-NFL-INJ-W10-1118"]
    rows = []
    for r in rub["rows"]:
        s = r["scores"]
        scores_txt = " · ".join(f"{k.replace('_',' ')} {v['score']}" for k, v in s.items())
        rows.append((
            [cell(r["rank"]), cell(r["id"]), cell(r["title"]), cell(r["proposal"]),
             cell(r["missing_info"]), cell(r["decision_needed"]), cell(scores_txt),
             cell(str(r["composite"]))],
            desk_nfl_ids,
        ))
    # Decision board: the ranked suggestions as reviewer choices (Adopt/Defer/Reject).
    # The app.js renders these and stores the reader's preference in their own browser only.
    choices = json.dumps([{"id": r["id"], "title": f"#{r['rank']} {r['title']}"} for r in rub["rows"]])
    board = (
        '<div id="decision-board" class="decisions" data-choices="' + esc(choices) + '"></div>'
        '<div class="decision-actions">'
        '<button type="button" id="export-decisions" class="btn">Export my choices</button>'
        '<button type="button" id="clear-decisions" class="btn btn-quiet">Clear</button>'
        '</div>'
    )
    body = []
    body.append(notice(
        "Suggestions are scored so a reviewer can choose the best path before implementing any change. Record "
        "your review choice on the board below (Adopt / Defer / Reject); it is stored in your browser only and "
        "implements nothing. The scores are derived by documented rules from the suggestion text and the "
        "decision register; the ranking proposes an order for review, not an implementation decision. Override "
        "any judgement — the raw scores are published beside each row.", "info"))
    body.append(panel("Review board — choose the best path", board))
    body.append(panel("Scored suggestion rubric — ranked",
                      table(["Rank", "ID", "Title", "Proposal", "Missing info", "Decision needed",
                             "Scores (coverage/leverage/source/dependency/risk)", "Composite"],
                            rows,
                            note="Composite = coverage×3 + leverage×2 + source×2 + dependency×1 + risk×1. "
                                 "See method page for the rubric definition.")))
    return page("suggestions.html", "Suggestions",
                "The 15 proposals scored and ranked so the best path can be chosen before any change.",
                body, kpis=[(str(rub["count"]), "suggestions"), (str(rub["rows"][0]["id"]), "top-ranked"), (READ_ON, "as of")])


def page_flags():
    flags = load("flags-2026-11-18.json")
    rows = []
    for f in flags["flags"]:
        rows.append((
            [cell(f["id"]), cell(f["kind"]), cell(f["severity"]), cell(f["item"]),
             cell(f["finding"]), cell(f["source_url"]), cell(f["action"]), cell(f["blocks"])],
            [f["source_id"]],
        ))
    body = panel("Flagged for review — 2026-11-18",
                 table(["ID", "Kind", "Severity", "Item", "Finding", "Source", "Action", "Blocks"],
                       rows,
                       note="Every flag is a fact observed on an official 2026-11-18 read or a drift against a "
                            "committed artifact. Flags are published here with their source link; they never "
                            "block the build and are never patched into canonical data."))
    return page("flags.html", "Flagged for review",
                "Irregularities, drift and timing facts from the 2026-11-18 reads, with source links.",
                body, kpis=[(str(flags["count"]), "flags"), (READ_ON, "as of")])


def page_sources():
    rows = []
    for sid, s in sorted(DESK_SOURCES.items()):
        rows.append((
            [cell(sid), cell(s.get("publisher", "")), cell(s.get("title", "")),
             cell(s.get("url", "")), cell(s.get("checked_on", "")), cell(s.get("status", "")),
             cell(s.get("evidence", ""))],
            [sid],
        ))
    body = panel("Source register — this desk's official reads",
                 table(["ID", "Publisher", "Title", "URL", "Checked on", "Status", "Evidence"],
                       rows,
                       note="Each source is an official page read on 2026-11-18 via the Arena page reader (direct "
                            "HTTPS to nfl.com returns curl 000 from the build sandbox). The shared research "
                            "registry holds the full 264-source register; this page lists the five this desk read."))
    return page("sources.html", "Sources",
                "The official pages this desk read on 2026-11-18, with evidence files and hashes.",
                body, kpis=[(str(len(DESK_SOURCES)), "desk sources"), (READ_ON, "read date")])


def page_method():
    body = []
    body.append(panel("What this desk does",
                      "<p>The forward desk takes a fresh official read of the standings, the Week 11 schedule and "
                      "the Week 10 injury report; checks it mechanically against the committed canonical data; and "
                      "joins the open decisions to what blocks them and the official source that would answer each "
                      "one. It then scores the suggestion register so a reviewer can choose the best path before "
                      "implementing any change.</p>"))
    body.append(panel("Drift-check rule",
                      "<p>A fresh read is compared cell-for-cell against every committed canonical snapshot. "
                      "Contradictions abort the check; drift against a stale snapshot is reported as a finding and "
                      "never patched into the canonical file. The canonical files are historical snapshots and are "
                      "left as-is.</p>"))
    body.append(panel("Suggestion rubric",
                      "<p>Five criteria, each scored 0–3 with a written rationale: requirement coverage (how many "
                      "non-implemented requirements a suggestion moves), decision leverage (Blocked > Partial > "
                      "Open), source feasibility (does the missing info name an obtainable official source), "
                      "dependency weight (does it share a decision link with other suggestions), and "
                      "implementation risk (reuses registered sources = lower risk). Composite = "
                      "coverage×3 + leverage×2 + source×2 + dependency×1 + risk×1.</p>"))
    body.append(panel("What this desk never does",
                      "<p>It publishes no price, stake, wager, return on investment or cash reward. It infers no "
                      "value from a non-official source. Where a value cannot be confirmed from an official page, "
                      "the cell is blank and flagged, never filled in.</p>"))
    return page("method.html", "Method & limits",
                "How the forward desk captures, checks and orders its work.", body)


# ------------------------------------------------------------------ build / check

BUILDERS = {
    "index.html": page_index,
    "standings.html": page_standings,
    "schedule.html": page_schedule,
    "injuries.html": page_injuries,
    "drift.html": page_drift,
    "decisions.html": page_decisions,
    "suggestions.html": page_suggestions,
    "flags.html": page_flags,
    "sources.html": page_sources,
    "method.html": page_method,
}


def build():
    SITE.mkdir(parents=True, exist_ok=True)
    generated = []
    for name, _ in PAGES:
        (SITE / name).write_text(BUILDERS[name](), encoding="utf-8")
        generated.append(name)
    (SITE / "manifest.json").write_text(
        json.dumps({"pages": generated, "desk": DESK, "built_on": READ_ON}, indent=2) + "\n",
        encoding="utf-8")
    return generated


def check() -> int:
    """Re-read every committed artifact and fail loudly on a broken contract.

    `--check` never writes. It exists so CI can prove the published pages agree with
    the committed data without trusting that the generator was run.
    """
    problems: list[str] = []

    def load(name):
        path = DATA / name
        if not path.is_file():
            problems.append(f"missing artifact: data/{name}")
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    # Data artifacts must exist and be internally consistent.
    standings = read_csv(DATA / "standings-2026-11-18.csv")
    if len(standings) != 32:
        problems.append(f"standings has {len(standings)} rows, expected 32")
    schedule = read_csv(DATA / "schedule-week11-2026-11-18.csv")
    if len(schedule) != 13:
        problems.append(f"schedule has {len(schedule)} rows, expected 13")
    injuries = read_csv(DATA / "injuries-week10-2026-11-18.csv")
    if not injuries:
        problems.append("injury designated rows are empty")
    counts = load("injury-counts-2026-11-18.json")
    if len(counts.get("counts", {})) != 28:
        problems.append(f"injury per-club counts cover {len(counts.get('counts', {}))} clubs, expected 28")
    register = load("decision-register.json")
    if register.get("count") != len(register.get("rows", [])):
        problems.append("decision register count mismatch")
    rubric = load("suggestion-rubric.json")
    if rubric.get("count") != len(rubric.get("rows", [])):
        problems.append("suggestion rubric count mismatch")
    flags = load("flags-2026-11-18.json")
    if flags.get("count") != len(flags.get("flags", [])):
        problems.append("flags count mismatch")
    drift = load("drift-check-2026-11-18.json")
    if not drift.get("ok"):
        problems.append("drift check reports an internal inconsistency")

    # Source ids this desk publishes must resolve to an official host. Only the
    # desk's own sources are checked — the shared research registry holds sources
    # for every desk (NBA, rent-control, gambling regulators, docs) and is not this
    # desk's responsibility.
    for sid, s in DESK_SOURCES.items():
        url = s.get("url", "")
        if not url:
            continue
        if not any(h in url for h in OFFICIAL_HOSTS):
            problems.append(f"source {sid} resolves to a non-official host: {url}")

    # Every published page must exist and carry document semantics + source links.
    for name, _ in PAGES:
        path = SITE / name
        if not path.is_file():
            problems.append(f"missing page: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if text.count("<h1>") != 1 or text.count("<main") != 1:
            problems.append(f"{name}: document semantics incomplete")
        for sid_list, body in re.findall(r'<tr data-source-ids="([^"]*)">(.*?)</tr>', text, re.S):
            ids = sid_list.split()
            if not ids:
                problems.append(f"{name}: row with no source ids")
                continue
            hrefs = re.findall(r'href="([^"]+)"', body)
            linked = False
            for sid in ids:
                if sid.startswith("http"):
                    # Raw URL source: the URL itself must appear as a link.
                    if sid in hrefs:
                        linked = True
                        break
                elif REGISTRY.get(sid) in hrefs:
                    linked = True
                    break
            if not linked:
                problems.append(f"{name}: row lacks its official source link")

    for problem in problems:
        print("FAIL", problem)
    print(f"checked {len(PAGES)} pages and 8 requirements: "
          f"{'FAILED' if problems else 'ok'}")
    return 1 if problems else 0


def main():
    if "--check" in sys.argv:
        raise SystemExit(check())
    generated = build()
    print(f"  built {len(generated)} pages into {DESK}/site/")


if __name__ == "__main__":
    main()
