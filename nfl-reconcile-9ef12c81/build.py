#!/usr/bin/env python3
"""Deterministic site generator for the decision-readiness reconciliation desk.

Session arena/9ef12c81-own7 (read-only over the shared register).

Inputs (all committed in this repository):
  research/nfl-decision-readiness.json   the shared 70-row register (NOT edited here)
  research/sources.json                  registered official sources
  nfl-reconcile-9ef12c81/adjudications.json  this session's re-grades and flags
  the evidence files the adjudications cite (hashed at build time)

The build aborts (non-zero exit) if:
  * an adjudication cites a register row that is missing, or whose register status differs
    from the status the adjudication was written against;
  * a cited evidence file does not exist, or a cited source id is not registered;
  * a live check of a number quoted in the reasons no longer holds on the committed files.

--check re-renders every page and compares bytes; it writes nothing.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
SITE = HERE / "site"

READ_ON = "2026-11-18"
SESSION = "arena/9ef12c81-own7"
TITLE = "OWN7 · Decision-readiness reconciliation"

PAGES = [
    ("index.html", "Reconciliation"),
    ("questions.html", "Decisions and information needed"),
    ("flagged.html", "Flagged for review"),
]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def read_csv(rel: str) -> list[dict]:
    with (ROOT / rel).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


# --------------------------------------------------------------------------------------------
# Live checks: every number quoted in an adjudication reason is recomputed here.
# --------------------------------------------------------------------------------------------
def live_checks(errors: list[str]) -> dict:
    facts: dict = {}

    snap = read_csv("nfl-snapcount-e5e4/data/snap-records.csv")
    facts["snap_rows"] = len(snap)
    facts["snap_teams"] = len({r["team"] for r in snap})
    facts["snap_games"] = len({r["game_id"] for r in snap})
    facts["snap_unofficial_rows"] = sum(1 for r in snap if r["table_label"] == "Unofficial")
    facts["snap_official_rows"] = sum(1 for r in snap if r["table_label"] == "Official")
    if (facts["snap_rows"], facts["snap_teams"], facts["snap_games"]) != (1217, 26, 13):
        errors.append(f"snap-count capture changed: {facts['snap_rows']} rows, "
                      f"{facts['snap_teams']} teams, {facts['snap_games']} games")
    if facts["snap_unofficial_rows"] != 371:
        errors.append(f"unofficial-labelled rows changed: {facts['snap_unofficial_rows']}")

    w10 = read_csv("nfl-results/data/games-2026-w1-10-complete.csv")
    facts["w10_fixtures"] = sum(1 for r in w10 if r["week"] == "10")
    if facts["w10_fixtures"] != 14:
        errors.append(f"week 10 fixture count changed: {facts['w10_fixtures']}")

    byes = read_csv("nfl-results/data/byes-2026-w1-10-complete.csv")
    facts["w10_byes"] = sorted(r["team_code"] for r in byes if r["week"] == "10")
    if facts["w10_byes"] != ["CHI", "DEN", "PHI", "TB"]:
        errors.append(f"week 10 bye clubs changed: {facts['w10_byes']}")

    a = {r["club_abbr"] for r in read_csv("nfl-availability-28ef/data/depth-slots-week10-2026.csv")}
    b = {r["club_abbr"] for r in read_csv("nfl-skill-cfdd/data/depth-slots-2026-11-14.csv")}
    facts["depth_clubs_union"] = len(a | b)
    facts["depth_clubs_a"] = len(a)
    facts["depth_clubs_b"] = len(b)
    if len(a | b) != 31 or "HOU" in (a | b):
        errors.append(f"depth-chart union changed: {len(a | b)} clubs")

    depth_header = (ROOT / "nfl-availability-28ef/data/depth-slots-week10-2026.csv").read_text(
        encoding="utf-8").splitlines()[0].split(",")
    facts["depth_has_version_column"] = any("version" in c.lower() for c in depth_header)
    if facts["depth_has_version_column"]:
        errors.append("a depth file now carries a version column: DR-34 gate text must be re-read")

    wc = load_json("nfl-week11-6c72a9fa/data/whatchanged.json")
    facts["whatchanged_keys"] = sorted(wc.keys())
    facts["whatchanged_changed_standings"] = sorted(
        x["code"] for x in wc["standings_2026_11_17_to_2026_11_18"] if x["changed"])
    if facts["whatchanged_changed_standings"] != ["BAL", "LAC"]:
        errors.append("what-changed standings delta changed")
    if any("rating" in k.lower() for k in wc.keys()):
        errors.append("what-changed ledger now has a rating key: DR-61 gate text must be re-read")

    nov = (ROOT / "nfl-week11-6c72a9fa/evidence/reserve-list-nov-2026-11-18.md").read_text(encoding="utf-8")
    facts["willis_nov_row"] = "| Dolphins | Dolphins | 11/10 | Malik Willis |" in nov
    if not facts["willis_nov_row"]:
        errors.append("Malik Willis reserve row not found in the November capture")

    rules = load_json("nfl-integration-c815/data/rules-2026.json")
    facts["rules_restraining_line"] = rules["values"]["onside_restraining_line"]
    if facts["rules_restraining_line"] != 35 or rules["values"]["legal_at_any_time"] is not True:
        errors.append("transcribed 2026 onside-kick rule values changed")

    facts["week10_fixture_summary_claim"] = load_json(
        "nfl-snapcount-e5e4/data/capture-summary.json")["playing_clubs_in_week10"]
    if facts["week10_fixture_summary_claim"] != 26:
        errors.append("snap-count capture-summary playing_clubs value changed")

    return facts


# --------------------------------------------------------------------------------------------
# Validation of the adjudications against the register and registry.
# --------------------------------------------------------------------------------------------
def validate(register: dict, sources: list[dict], adj: dict, errors: list[str]):
    rows = {r["id"]: r for r in register["requirements"]}
    src_ids = {s["id"] for s in sources}
    allowed = set(adj["allowed_statuses"])
    seen = set()
    for a in adj["adjudications"]:
        rid = a["id"]
        if rid in seen:
            errors.append(f"{rid}: duplicate adjudication")
        seen.add(rid)
        if rid not in rows:
            errors.append(f"{rid}: not in the register")
            continue
        if rows[rid]["status"] != a["register_status"]:
            errors.append(f"{rid}: register status is {rows[rid]['status']}, adjudication written "
                          f"against {a['register_status']}; re-grade before publishing")
        if a["proposed_status"] not in allowed or a["register_status"] not in allowed:
            errors.append(f"{rid}: status outside the register vocabulary")
        for ev in a["evidence"]:
            if not (ROOT / ev).is_file():
                errors.append(f"{rid}: evidence file missing: {ev}")
        for sid in a.get("source_ids_extra", []):
            if sid not in src_ids:
                errors.append(f"{rid}: unregistered source id {sid}")
        if not a["reason"].strip():
            errors.append(f"{rid}: empty reason")
    ids = [i["id"] for i in adj["irregularities"]]
    if len(ids) != len(set(ids)):
        errors.append("duplicate irregularity ids")
    for item in adj["irregularities"]:
        for ev in item["evidence"]:
            if not (ROOT / ev).is_file():
                errors.append(f"{item['id']}: evidence file missing: {ev}")
        for sid in item.get("source_ids_extra", []):
            if sid not in src_ids:
                errors.append(f"{item['id']}: unregistered source id {sid}")
    for row in register["requirements"]:
        for sid in row.get("source_ids", []):
            if sid not in src_ids:
                errors.append(f"{row['id']}: register cites unregistered source {sid}")
        art = row.get("artifact")
        if art and not (ROOT / art).exists():
            errors.append(f"{row['id']}: register artifact missing: {art}")
    return rows, {a["id"]: a for a in adj["adjudications"]}


# --------------------------------------------------------------------------------------------
# Rendering helpers.
# --------------------------------------------------------------------------------------------
def src_link(url: str, label: str = "official page ↗") -> str:
    return (f'<a href="{esc(url)}" rel="noopener noreferrer" target="_blank">'
            f'{esc(label)}</a>')


def file_link(rel: str) -> str:
    href = "../../" + rel
    return f'<a href="{esc(href)}">{esc(rel)}</a>'


def badge(text: str) -> str:
    kind = {"Implemented": "badge-ok", "Partial": "badge-warn", "Open": "badge-warn",
            "Blocked": "badge-bad", "Rejected": "badge"}.get(text, "badge")
    return f'<span class="badge {kind}">{esc(text)}</span>'


def source_cell(ids: list[str], registry: dict[str, str]) -> tuple[str, str]:
    links = []
    for sid in ids:
        links.append(f'{esc(sid)} {src_link(registry[sid])}')
    return " · ".join(links), " ".join(ids)


def table(table_id: str, caption: str, columns: list[str], rows_html: list[str]) -> str:
    head = "".join(f'<th scope="col">{esc(c)}</th>' for c in columns)
    body = "".join(rows_html)
    return (f'<div class="table-wrap" role="region" tabindex="0" aria-label="{esc(caption)}">'
            f'<table id="{esc(table_id)}"><caption>{esc(caption)}</caption>'
            f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


def page(name: str, title: str, lead: str, body: str, active: str) -> str:
    links = []
    for p, label in PAGES:
        current = ' aria-current="page"' if p == active else ""
        links.append(f'<a href="{esc(p)}"{current}>{esc(label)}</a>')
    nav = "".join(links)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OWN7 · Decision-readiness reconciliation</title>
<meta name="description" content="Re-grade of the decision-readiness register against the 2026-11-18 tree. Every row links its official source and its evidence file.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="brand"><strong>OWN7 · Decision-readiness reconciliation</strong><span>read {READ_ON} · session {esc(SESSION)} · shared register not edited</span></div><nav aria-label="Desk pages">{nav}<a href="../../index.html">← NFL workspace</a></nav></header>
<main id="main">
<p class="eyebrow">OWN7 · Reconciliation desk</p>
<h1>{esc(title)}</h1>
<p class="lead">{lead}</p>
{body}
</main>
</body>
</html>
"""


# --------------------------------------------------------------------------------------------
# Build.
# --------------------------------------------------------------------------------------------
def build() -> dict[str, str]:
    errors: list[str] = []
    register = load_json("research/nfl-decision-readiness.json")
    sources = load_json("research/sources.json")
    adj = json.loads((HERE / "adjudications.json").read_text(encoding="utf-8"))
    registry = {s["id"]: s["url"] for s in sources}
    rows, by_id = validate(register, sources, adj, errors)
    facts = live_checks(errors)
    if errors:
        raise SystemExit("reconciliation aborted:\n - " + "\n - ".join(errors))

    counts = {}
    for r in register["requirements"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    changed = [a for a in adj["adjudications"] if a["proposed_status"] != a["register_status"]]
    gate_only = [a for a in adj["adjudications"] if "gate text" in a["outcome"]]

    # Index table: one row per register requirement, in register order.
    index_rows = []
    for r in register["requirements"]:
        a = by_id.get(r["id"])
        src_html, src_ids_attr = source_cell(r.get("source_ids", []), registry)
        if a:
            outcome = a["outcome"]
            reason = a["reason"]
            prop = a["proposed_status"]
            ev_html = "<br>".join(file_link(e) for e in a["evidence"]) or ""
            src_ids = list(dict.fromkeys(r.get("source_ids", []) + a.get("source_ids_extra", [])))
            src_html, src_ids_attr = source_cell(src_ids, registry)
        else:
            outcome = "Carried forward (not re-read)"
            reason = "Not re-read on 2026-11-18; the register row stands as written."
            prop = r["status"]
            ev_html = ""
        index_rows.append(
            f'<tr data-source-ids="{esc(src_ids_attr)}">'
            f'<td><strong>{esc(r["id"])}</strong></td>'
            f'<td>{esc(r["requirement"])}</td>'
            f'<td>{badge(r["status"])}</td>'
            f'<td>{badge(prop)}</td>'
            f'<td>{esc(outcome)}</td>'
            f'<td>{esc(r["clears_when"])}</td>'
            f'<td>{esc(reason)}</td>'
            f'<td>{ev_html}</td>'
            f'<td>{src_html}</td>'
            f'</tr>')

    summary = (
        '<section class="metrics" aria-label="Summary">'
        f'<div class="metric"><span>Register rows</span><strong>{len(register["requirements"])}</strong></div>'
        f'<div class="metric"><span>Re-read this session</span><strong>{len(adj["adjudications"])}</strong></div>'
        f'<div class="metric"><span>Carried forward unchanged</span>'
        f'<strong>{len(register["requirements"]) - len(adj["adjudications"])}</strong></div>'
        f'<div class="metric"><span>Proposed status changes</span><strong>{len(changed)}</strong></div>'
        f'<div class="metric"><span>Gate text proposed for correction</span><strong>{len(gate_only)}</strong></div>'
        f'<div class="metric"><span>Flags</span><strong>{len(adj["irregularities"])}</strong></div>'
        '</section>')
    register_counts = " · ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    lead_index = (
        "This desk re-reads the decision-readiness register (70 rows) against the artefacts committed on "
        f"{READ_ON}. Only the rows those artefacts bear on are re-graded; the rest are carried forward and "
        "labelled as such. The shared register is not edited here: the integration owner applies the "
        "proposed changes. Register as it stands: " + esc(register_counts) + ".")
    index_body = (
        summary +
        '<h2>Proposed changes and gate corrections</h2>'
        '<p>Three rows move from Open to Partial, and one gate text is stale. Each re-grade cites the '
        'artefact that carries the change. Nothing here is a new value; a number is shown only where a '
        'committed file was recomputed by this build.</p>' +
        table("reconciliation", "Decision-readiness register, one row per requirement",
              ["ID", "Requirement", "Register now", "Proposed", "Outcome", "Clears when (register)",
               "Reason", "Evidence files", "Official source(s)"],
              index_rows) +
        '<p class="note">Live checks run at build time: ' +
        esc(f"{facts['snap_rows']} snap-count rows, {facts['snap_teams']} clubs, {facts['snap_games']} games; "
            f"{facts['snap_unofficial_rows']} rows under the printed '(Unofficial)' label; "
            f"depth-chart union {facts['depth_clubs_union']} clubs; {facts['w10_fixtures']} Week 10 fixtures; "
            f"Week 10 byes {', '.join(facts['w10_byes'])}.") + '</p>'
    )

    # Questions page: decisions that only the owner can make, then information still needed.
    decisions = [
        ("Q1", "Do we seek NFL.com's prior written consent, or stop before any systematic retrieval of the Services (DR-29, DR-54, DR-66)?",
         "Section 1.3 prohibits systematic retrieval absent express prior written consent. Without a decision, three rows stay Blocked and the daily injury history cannot start.",
         "Owner (legal review optional)", ["NFL-LEGAL-TERMS"],
         "nfl-reconcile-9ef12c81/evidence/nfl-terms-1-3-2026-11-18.md"),
        ("Q2", "Which price-data policy governs any backtest that uses odds (DR-18, DR-20)?",
         "No official operator price is held, and third-party prices carry rights restrictions. The policy must be written before any backtest is published.",
         "Owner", ["NFL-LEGAL-TERMS"],
         "research/nfl-decision-readiness.json"),
        ("Q3", "May the four '(Unofficial)'-labelled Game Book Playtime tables be used as a starter proxy (DR-31, DR-56)?",
         "371 of 1,217 snap-count rows carry the printed '(Unofficial)' label. The desk keeps the label and treats them as printed.",
         "Owner", ["SN-NFL-GAMEBOOK-PDF"],
         "nfl-snapcount-e5e4/data/flags.json"),
        ("Q4", "Which depth-order route is the default for the 32-club backup feature (DR-52, DR-11)?",
         "Route (a) covers 31 of 32 clubs only as a union of two files; route (b) snap counts cover 26 clubs for one week. HOU is missing from both.",
         "Owner, after DR-34 versioning", ["NFL-DEPTH-PATH"],
         "nfl-availability-28ef/data/depth-slots-week10-2026.csv"),
        ("Q5", "How many seasons of injury designations and inactive lists are needed before 'Questionable' is calibrated (DR-44, DR-53, DR-70)?",
         "Two 2026 injury-report captures exist. Calibration needs a multi-season joined history, which Q1 gates.",
         "Owner", ["NFL-INJURIES"],
         "data/nfl-injuries-2026-w10.csv"),
        ("Q6", "Is a 25-row rolling reserve window acceptable as evidence for 'not listed', or must each reserve capture cover all 32 clubs (DR-64)?",
         "Malik Willis appears in the November window, but not every club's reserve list is in view. 'Not listed' cannot mean 'available' from one window.",
         "Owner and integration owner", ["C672-RESERVE-NOV-1118"],
         "nfl-week11-6c72a9fa/evidence/reserve-list-nov-2026-11-18.md"),
    ]
    dec_rows = []
    for qid, question, why, who, sids, ev in decisions:
        ids_html, ids_attr = source_cell(sids, registry)
        dec_rows.append(
            f'<tr data-source-ids="{esc(ids_attr)}"><td><strong>{esc(qid)}</strong></td>'
            f'<td>{esc(question)}</td><td>{esc(why)}</td><td>{esc(who)}</td>'
            f'<td>{file_link(ev)}</td><td>{ids_html}</td></tr>')
    info_rows = []
    for r in register["requirements"]:
        if r["status"] in ("Implemented", "Rejected"):
            continue
        ids_html, ids_attr = source_cell(r.get("source_ids", []), registry)
        info_rows.append(
            f'<tr data-source-ids="{esc(ids_attr)}"><td><strong>{esc(r["id"])}</strong></td>'
            f'<td>{esc(r["requirement"])}</td><td>{badge(r["status"])}</td>'
            f'<td>{esc(r["gate"])}</td><td>{esc(r["clears_when"])}</td><td>{ids_html}</td></tr>')
    questions_body = (
        '<h2>Decisions only the owner can make</h2>'
        '<p>These cannot be answered from the repository or the public record alone. They are listed '
        'so the choice is visible before any further work is built on it.</p>' +
        table("decisions", "Owner decisions", ["ID", "Question", "Why it matters", "Who decides",
                                               "Evidence", "Official source"], dec_rows) +
        '<h2>Information still needed (every non-Implemented register row)</h2>'
        '<p>Each row gives the gate and the condition that would clear it, copied from the register. '
        'Rows re-read this session are marked on the reconciliation page.</p>' +
        table("info-needed", "Open, Partial and Blocked requirements",
              ["ID", "Requirement", "Status", "Gate (register)", "Clears when (register)", "Official source(s)"],
              info_rows)
    )

    flag_rows = []
    for item in adj["irregularities"]:
        src_ids = list(item.get("source_ids_extra", []))
        if not src_ids:
            raise SystemExit(f"{item['id']}: no registered source to link")
        ids_html, ids_attr = source_cell(src_ids, registry)
        ev_html = "<br>".join(file_link(e) for e in item["evidence"])
        flag_rows.append(
            f'<tr data-source-ids="{esc(ids_attr)}"><td><strong>{esc(item["id"])}</strong></td>'
            f'<td>{esc(item["about"])}</td><td>{esc(item["severity"])}</td>'
            f'<td>{esc(item["item"])}</td><td>{esc(item["detail"])}</td>'
            f'<td>{esc(item["route"])}</td><td>{ev_html}</td><td>{ids_html}</td></tr>')
    flagged_body = (
        '<p class="lead">Irregularities found while re-grading. Flags never block publication: each one stays '
        'visible with its evidence and official source, and no value is changed to hide it.</p>' +
        table("flags", "Flags raised by this desk",
              ["ID", "About", "Severity", "Flag", "Detail", "Route", "Evidence", "Official source"],
              flag_rows)
    )

    pages = {
        "index.html": page("index.html", "Reconciliation", lead_index, index_body, "index.html"),
        "questions.html": page("questions.html", "Decisions and information needed",
                               "Questions that must be answered before any decision can be made on these rows, "
                               "and the information each gate still needs. Answers come from the owner or from "
                               "a named official source; none is assumed here.",
                               questions_body, "questions.html"),
        "flagged.html": page("flagged.html", "Flagged for review", "", flagged_body, "flagged.html"),
    }
    manifest = {
        "desk": "nfl-reconcile-9ef12c81",
        "session": SESSION,
        "read_on": READ_ON,
        "pages": [name for name, _ in PAGES],
        "register_counts": counts,
        "re_read_rows": [a["id"] for a in adj["adjudications"]],
        "proposed_changes": {a["id"]: [a["register_status"], a["proposed_status"]] for a in changed},
        "evidence_sha256": {
            e: sha256_file(e)
            for a in adj["adjudications"] for e in a["evidence"]
        } | {
            e: sha256_file(e) for i in adj["irregularities"] for e in i["evidence"]
        } | {
            "nfl-reconcile-9ef12c81/adjudications.json": sha256_file("nfl-reconcile-9ef12c81/adjudications.json"),
        },
        "source_ids": sorted({s for r in register["requirements"] for s in r.get("source_ids", [])}
                             | {s for a in adj["adjudications"] for s in a.get("source_ids_extra", [])}
                             | {s for i in adj["irregularities"] for s in i.get("source_ids_extra", [])}),
    }
    pages["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return pages


def main(argv: list[str]) -> int:
    check = "--check" in argv
    out = build()
    if check:
        bad = []
        for name, text in out.items():
            path = SITE / name
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                bad.append(name)
        if bad:
            print("stale desk pages (run build.py): " + ", ".join(bad))
            return 1
        print("OK: reconciliation desk pages reproduce byte-for-byte")
        return 0
    SITE.mkdir(parents=True, exist_ok=True)
    for name, text in out.items():
        (SITE / name).write_text(text, encoding="utf-8")
    print(f"Built {len(out) - 1} pages + manifest in {SITE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
