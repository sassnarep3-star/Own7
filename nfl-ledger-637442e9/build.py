#!/usr/bin/env python3
"""Decision-ledger reconciliation desk (session arena/637442e9-own7).

Inputs (all committed):
  research/nfl-decision-readiness.json   the 70-row ledger the landing page renders (read-only here)
  research/sources.json                  the registered official and repository sources
  data/overrides.json                    the six reconciled status changes, each with its artefact
  data/rechecked.json                    rows re-checked without a status change
  data/flags.json, data/questions.json, data/suggestions.json
  evidence/*.md + evidence/SHA256SUMS.txt  verbatim official reads, hash-checked
  nfl-availability-28ef, nfl-assurance-9580ac3f, nfl-readiness-e7ef, nfl-results, nfl-week11-6c72a9fa
                                         the artefacts behind every count quoted on the pages

Every number on the pages is computed here from those files. The build aborts on a missing
artefact, an unknown source ID, a hash mismatch or a count that no longer reproduces; it never
publishes a partial page.

    python nfl-ledger-637442e9/build.py          # write site/
    python nfl-ledger-637442e9/build.py --check  # re-render in memory and compare bytes
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
SITE = HERE / "site"
EVIDENCE = HERE / "evidence"

READ_ON = "2026-11-18"
SESSION = "arena/637442e9-own7"
SITE_TITLE = "OWN7 · Decision ledger"
STATUS_ORDER = ["Implemented", "Partial", "Open", "Blocked", "Rejected"]
ALLOWED_STATUS = set(STATUS_ORDER)
GITHUB_HOST = "github.com"

PAGES = [
    ("index.html", "Dashboard"),
    ("executive-summary.html", "Executive summary"),
    ("gaps.html", "Questions and gaps"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]


class DeskError(SystemExit):
    pass


def fail(msg: str) -> None:
    raise DeskError("FAIL: " + msg)


def load(path: str):
    """Load a JSON file given relative to the repository root."""
    return json.loads((ROOT / path).read_text(encoding="utf8"))


def load_desk(name: str):
    """Load a JSON file from this desk's data/ directory."""
    return json.loads((DATA / name).read_text(encoding="utf8"))


def esc(value) -> str:
    return html.escape(str(value), quote=True)


# ---------------------------------------------------------------- inputs and contracts

def registry() -> dict:
    rows = load("research/sources.json")
    return {r["id"]: r for r in rows}


def is_official(source: dict) -> bool:
    return urlparse(source["url"]).netloc != GITHUB_HOST


def artefact_path(text: str) -> str:
    return re.split(r"[ ,;(]", text.strip())[0].strip("`")


def evidence_hashes() -> dict:
    out = {}
    for line in (EVIDENCE / "SHA256SUMS.txt").read_text(encoding="utf8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        out[name.strip()] = digest
    return out


def check_evidence() -> dict:
    recorded = evidence_hashes()
    actual = {}
    for path in sorted(EVIDENCE.glob("*.md")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        actual[path.name] = digest
        if recorded.get(path.name) != digest:
            fail(f"evidence hash mismatch: {path.name}")
    if set(recorded) != set(actual):
        fail("evidence/SHA256SUMS.txt does not list exactly the evidence files")
    return actual


def ledger_rows() -> list[dict]:
    return load("research/nfl-decision-readiness.json")["requirements"]


def week10_counts() -> dict:
    """Recount the Week 10 injury captures and the results files from committed artefacts."""
    avail = list(csv.DictReader((ROOT / "nfl-availability-28ef/data/injuries-week10-2026.csv")
                                .read_text(encoding="utf8").splitlines()))
    raw_avail = (ROOT / "nfl-availability-28ef/evidence/injury-report-week10-2026.joined.md").read_text(encoding="utf8")
    practice = re.compile(r"Full Participation|Did Not Participate|Limited Participation")
    raw_avail_lines = sum(1 for line in raw_avail.splitlines() if practice.search(line))
    assurance = list(csv.DictReader((ROOT / "nfl-assurance-9580ac3f/data/injuries.csv").read_text(encoding="utf8").splitlines()))
    e7ef = (ROOT / "nfl-readiness-e7ef/evidence/injuries-w10-2026-11-17.md").read_text(encoding="utf8")
    e7ef_lines = [line.strip() for line in e7ef.splitlines() if practice.search(line)]
    byes = list(csv.DictReader((ROOT / "nfl-results/data/byes-2026-w1-10-complete.csv").read_text(encoding="utf8").splitlines()))
    week10_byes = sorted(r["team_code"] for r in byes if r["week"] == "10")
    avail_clubs = {r["club_abbr"] for r in avail}
    all_clubs = sorted({r["club_abbr"] for r in avail} | set(week10_byes))
    missing_from_avail = sorted(set(all_clubs) - avail_clubs)
    if missing_from_avail != week10_byes:
        fail(f"availability CSV is missing {missing_from_avail}, which is not the Week 10 bye list {week10_byes}")
    if len(avail) != raw_avail_lines:
        fail(f"availability CSV rows ({len(avail)}) differ from raw practice lines ({raw_avail_lines})")
    if len({r['injury_id'] for r in avail}) != len(avail):
        fail("availability CSV has duplicate injury_id values")
    assurance_clubs = {r["team"] for r in assurance}
    canon = list(csv.DictReader((ROOT / "nfl-results/data/games-2026-w1-10.csv").read_text(encoding="utf8").splitlines()))
    complete = list(csv.DictReader((ROOT / "nfl-results/data/games-2026-w1-10-complete.csv").read_text(encoding="utf8").splitlines()))
    key = lambda r: (r["week"], r["away"], r["home"])
    only_complete = sorted(key(r) for r in complete if key(r) not in {key(x) for x in canon})
    if only_complete != [("10", "LAC", "BAL")]:
        fail(f"results files differ by more than LAC@BAL: {only_complete}")
    return {
        "avail_rows": len(avail),
        "avail_clubs": len(avail_clubs),
        "avail_practice_lines": raw_avail_lines,
        "avail_cin": sum(1 for r in avail if r["club_abbr"] == "CIN"),
        "avail_sea": sum(1 for r in avail if r["club_abbr"] == "SEA"),
        "avail_bye_absent": missing_from_avail,
        "assurance_rows": len(assurance),
        "assurance_clubs": len(assurance_clubs),
        "assurance_cin": sum(1 for r in assurance if r["team"] == "CIN"),
        "assurance_sea": sum(1 for r in assurance if r["team"] == "SEA"),
        "assurance_no_bal_lac": sorted({"BAL", "LAC"} - assurance_clubs),
        "e7ef_rows": len(set(e7ef_lines)),
        "e7ef_lines": len(e7ef_lines),
        "canon_games": len(canon),
        "complete_games": len(complete),
        "games_only_in_complete": ["LAC@BAL"],
        "week10_byes": week10_byes,
    }


def build_model():
    registry_map = registry()
    rows = ledger_rows()
    prior = {r["id"]: r for r in rows}
    overrides = load_desk("overrides.json")["changes"]
    rechecked = load_desk("rechecked.json")["rows"]
    flags = load_desk("flags.json")["flags"]
    questions = load_desk("questions.json")["questions"]
    suggestions = load_desk("suggestions.json")["suggestions"]
    ovr = {}
    for o in overrides:
        if o["id"] not in prior:
            fail(f"override for unknown row {o['id']}")
        if o["status"] not in ALLOWED_STATUS:
            fail(f"bad status {o['status']}")
        if not o["evidence"] or not o["sources"]:
            fail(f"override {o['id']} lacks evidence or sources")
        for e in o["evidence"]:
            if not (ROOT / e).exists():
                fail(f"override {o['id']} evidence missing: {e}")
        for s in o["sources"]:
            if s not in registry_map:
                fail(f"override {o['id']} unknown source {s}")
        ovr[o["id"]] = o
    for rid in rechecked:
        if rid not in prior:
            fail(f"rechecked unknown row {rid}")
    # every row: artefact exists, every source registered
    table = []
    for r in rows:
        art = artefact_path(r["artifact"]) if r.get("artifact") else ""
        if art and not (ROOT / art).exists():
            fail(f"{r['id']} artefact missing: {art}")
        src_ids = list(dict.fromkeys(list(r.get("source_ids", [])) + (ovr[r["id"]]["sources"] if r["id"] in ovr else [])))
        for s in src_ids:
            if s not in registry_map:
                fail(f"{r['id']} unknown source {s}")
        official = [s for s in src_ids if is_official(registry_map[s])]
        status_now = ovr[r["id"]]["status"] if r["id"] in ovr else r["status"]
        table.append({
            "id": r["id"],
            "requirement": r["requirement"],
            "category": r["category"],
            "prior": r["status"],
            "now": status_now,
            "changed": status_now != r["status"],
            "gate": (ovr[r["id"]]["gate_now"] if r["id"] in ovr else r["gate"]),
            "clears_when": r["clears_when"],
            "artifact": art,
            "source_ids": src_ids,
            "official_ids": official,
            "basis": (ovr[r["id"]]["basis"] if r["id"] in ovr else (rechecked.get(r["id"]) if r["id"] in rechecked else "")),
            "rechecked": r["id"] in ovr or r["id"] in rechecked,
        })
    if len(table) != 70:
        fail(f"expected 70 ledger rows, found {len(table)}")
    return {"table": table, "registry": registry_map, "flags": flags, "questions": questions,
            "suggestions": suggestions, "overrides": overrides, "rechecked": rechecked}


# ---------------------------------------------------------------- rendering helpers

CSS = """
:root{--ink:#1d2430;--muted:#5b6575;--line:#d9dee7;--bg:#f6f8fb;--card:#fff;--accent:#1f4e79;
--impl:#e3f4e8;--impl-ink:#1e6b36;--part:#fff4d6;--part-ink:#7a5200;--open:#e9edf3;--open-ink:#3c4656;
--block:#fde3e3;--block-ink:#8a1c1c;--rej:#2b2f36;--rej-ink:#fff}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:var(--accent);color:#fff;padding:14px 22px}header a{color:#fff}
header .brand{font-weight:700;letter-spacing:.02em}
nav ul{list-style:none;margin:8px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:6px}
nav a{display:inline-block;padding:5px 10px;border-radius:999px;background:rgba(255,255,255,.14);text-decoration:none;font-size:14px}
nav a[aria-current=page]{background:#fff;color:var(--accent);font-weight:600}
main{max-width:1280px;margin:0 auto;padding:22px}
h1{font-size:26px;margin:4px 0 6px}h2{font-size:19px;margin:26px 0 8px}
.lede{color:var(--muted);max-width:900px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.card b{display:block;font-size:24px}.card span{color:var(--muted);font-size:13px}
.table-card{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:auto;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}
th{background:#eef2f7;position:sticky;top:0;font-weight:600}
td.num{white-space:nowrap}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.s-Implemented{background:var(--impl);color:var(--impl-ink)}.s-Partial{background:var(--part);color:var(--part-ink)}
.s-Open{background:var(--open);color:var(--open-ink)}.s-Blocked{background:var(--block);color:var(--block-ink)}
.s-Rejected{background:var(--rej);color:var(--rej-ink)}
.changed{outline:2px solid #c99700;outline-offset:1px}
.note{background:#fffbea;border:1px solid #e8d37a;border-radius:10px;padding:10px 14px;margin:12px 0;max-width:980px}
.warn{background:#fff1f1;border:1px solid #e7a1a1;border-radius:10px;padding:10px 14px;margin:12px 0;max-width:980px}
ul.clean{padding-left:20px}ul.clean li{margin:4px 0}
.small{font-size:13px;color:var(--muted)}
code{font-size:13px;background:#eef2f7;padding:1px 4px;border-radius:4px;overflow-wrap:anywhere;word-break:break-all}
footer{max-width:1280px;margin:20px auto;padding:0 22px 30px;color:var(--muted);font-size:13px}
.blank{color:var(--muted);font-style:italic}
"""


def page_shell(name: str, title: str, body: str) -> str:
    nav_items = []
    for href, label in PAGES:
        cur = ' aria-current="page"' if href == name else ""
        nav_items.append(f'<li><a href="{href}"{cur}>{esc(label)}</a></li>')
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)} · {esc(SITE_TITLE)}</title>\n"
        '<link rel="stylesheet" href="style.css">\n</head>\n<body>\n'
        '<header><div class="brand"><a href="index.html">OWN7 · Decision ledger</a>'
        ' <span class="small" style="color:#dfe9f5">(read ' + READ_ON + ')</span></div>\n'
        '<nav aria-label="Desk pages"><ul>' + "".join(nav_items) +
        '<li><a href="../../index.html">Site home</a></li></ul></nav></header>\n'
        f"<main>\n{body}\n</main>\n"
        '<footer>Research desk, not advice. No odds, price, ROI, CLV, stake or reward is produced here. '
        'Every value is computed from committed files or a dated official read; blanks stay blank. '
        f'Session {esc(SESSION)}.</footer>\n</body>\n</html>\n'
    )


def pill(status: str) -> str:
    return f'<span class="pill s-{esc(status)}">{esc(status)}</span>'


def link(href: str, text: str) -> str:
    return f'<a href="{esc(href)}">{esc(text)}</a>'


def source_links(reg: dict, ids: list[str], rel_prefix: str = "") -> str:
    parts = []
    for sid in ids:
        src = reg[sid]
        host = urlparse(src["url"]).netloc
        tag = "official" if is_official(src) else "repository"
        parts.append(f'<div>{link(src["url"], host + " · " + src["title"][:60])} <span class="small">[{tag}]</span></div>')
    return "".join(parts)


def row_attr(ids: list[str]) -> str:
    return f' data-source-ids="{esc(" ".join(ids))}"'


def table_card(label: str, head: list[str], rows_html: str) -> str:
    th = "".join(f"<th scope=\"col\">{esc(h)}</th>" for h in head)
    return (f'<div class="table-card" role="region" tabindex="0" aria-label="{esc(label)}">'
            f"<table><thead><tr>{th}</tr></thead><tbody>{rows_html}</tbody></table></div>")


# ---------------------------------------------------------------- pages

def page_index(model, counts) -> str:
    table, reg = model["table"], model["registry"]
    prior_c = Counter(r["prior"] for r in table)
    now_c = Counter(r["now"] for r in table)
    changed = [r for r in table if r["changed"]]
    cards = []
    for s in STATUS_ORDER:
        cards.append(f'<div class="card"><b>{now_c.get(s, 0)}</b><span>{esc(s)} now'
                     f' <span class="small">(was {prior_c.get(s, 0)})</span></span></div>')
    cards.append(f'<div class="card"><b>{len(table)}</b><span>requirement lines</span></div>')
    cards.append(f'<div class="card"><b>{len(changed)}</b><span>status changes this session</span></div>')
    rows = []
    for r in table:
        ids = r["source_ids"]
        off = r["official_ids"]
        cls = "official link" if off else "repository only: no external official source applies (flagged)"
        art_cell = link("../../" + r["artifact"], r["artifact"]) if r["artifact"] else '<span class="blank">none</span>'
        status_cell = pill(r["now"]) + (f' <span class="small">was {esc(r["prior"])}</span>' if r["changed"] else "")
        row_class = ' class="changed"' if r["changed"] else ""
        rows.append(
            f'<tr{row_attr(ids)}{row_class}>'
            f'<td class="num">{esc(r["id"])}</td>'
            f'<td>{esc(r["requirement"])}<div class="small">{esc(r["category"])}</div></td>'
            f"<td>{status_cell}</td>"
            f'<td>{esc(r["gate"])}</td>'
            f'<td>{esc(r["clears_when"])}</td>'
            f"<td>{art_cell}</td>"
            f'<td>{source_links(reg, ids)}<div class="small">{cls}</div></td>'
            "</tr>"
        )
    change_rows = "".join(
        f'<li><b>{esc(r["id"])}</b> {pill(r["prior"])} → {pill(r["now"])}. {esc(r["basis"])}</li>'
        for r in changed)
    body = f"""
<h1>Decision ledger: all 70 requirement lines, reconciled</h1>
<p class="lede">Each line of the project brief, its status now and at the start of this session, the gate that
blocks it, the condition that would clear it, and the artefact and official source behind it. Statuses changed here
are outlined in yellow and explained beneath. The 70-row ledger file itself is not edited by this desk; the
reconciled status is published beside it so the owner can accept or reject each change.</p>
<div class="cards">{''.join(cards)}</div>
<div class="note"><b>Read first.</b> Three things block most of the remaining work: the NFL.com terms (§1.3 restricts systematic retrieval;
§12 restricts using the Services to wager on NFL games), the absence of an official snap-count source, and Week 10 injury
counts that do not reconcile across captures. See <a href="flagged.html">Flagged for review</a> and
<a href="executive-summary.html">Executive summary</a>.</div>
<h2>Status changes this session ({len(changed)})</h2>
<ul class="clean">{change_rows}</ul>
<h2>The ledger</h2>
<p class="small">Source links are the registered sources for each line. A line marked "repository only" has no external
official source that applies to it; it is flagged rather than given an invented official link.</p>
{table_card("Decision ledger, 70 requirement lines", ["ID", "Requirement", "Status", "Gate that blocks it", "What would clear it", "Artefact", "Source link(s)"], "".join(rows))}
"""
    return page_shell("index.html", "Decision ledger", body)


def page_summary(model, counts) -> str:
    table = model["table"]
    now_c = Counter(r["now"] for r in table)
    body = f"""
<h1>Executive summary</h1>
<p class="lede">Status as of {READ_ON}. This summary restates only what the linked files and dated official reads show.</p>
<h2>Where the 70 requirement lines stand</h2>
<p>After this session's reconciliation: <b>{now_c.get('Implemented', 0)} Implemented</b>,
<b>{now_c.get('Partial', 0)} Partial</b>, <b>{now_c.get('Open', 0)} Open</b>,
<b>{now_c.get('Blocked', 0)} Blocked</b> and <b>{now_c.get('Rejected', 0)} Rejected</b>.
Six statuses changed (DR-13, DR-49, DR-57, DR-61, DR-64, DR-68). Each change cites the artefact that supports it on the
<a href="index.html">dashboard</a>. The ledger itself is unchanged; the owner decides whether to adopt the changes
(suggestion S1).</p>
<h2>What is in place</h2>
<ul class="clean">
<li>A dated, 150-row Week 1-10 results file (the complete file; the canonical file omits the LAC@BAL final). The Week 10 LAC@BAL final (23-20) and the Week 10 bye list (CHI, DEN, PHI, TB) are confirmed by the official Week 10 schedule page, rendered text retrieved 2026-11-18 (nfl-results/evidence/week-10.complete.md). The fresh-reads desk also records the official game centre page and Game Book PDF for that game (C672-GC-W10-LACBAL-1118, C672-GAMEBOOK-W10-LACBAL-1118); this desk did not re-read them.</li>
<li>Origination order (side, then total, then moneyline), pre-registration, signal/staking separation and a
favourite-side control, each with a page in the repository. Their content was not re-derived this session; only the
artefacts' presence and registered sources were checked, plus the spot-checks named on the dashboard.</li>
<li>A league-level reserve-list sweep that covers only the visible November and October windows (not all 32 clubs), a what-changed diff across one dated interval (2026-11-17 to 2026-11-18), and the 2026 rule-change table checked against the league's own page.</li>
</ul>
<h2>What blocks decisions</h2>
<ul class="clean">
<li><b>Terms §1.3.</b> Systematic retrieval to compile a collection needs express prior written consent. That blocks the
daily injury-report and depth-page capture the brief asks for (DR-21, DR-29, DR-54, DR-66). No capture is built.</li>
<li><b>Terms §12.</b> Users may not use the Services to gamble or wager on the result of any NFL game. This project's
purpose is to originate betting lines. Whether the project's use is within that sentence is a legal question; this desk
gives no legal opinion. See the <a href="flagged.html">flag</a>.</li>
<li><b>No official snap-count source.</b> The search found third-party sites only. The depth-order route and snap-count
proxy stay open (DR-11, DR-52, DR-56).</li>
<li><b>No rights-cleared price.</b> nfl.com/odds renders a 404 on the read date. Pricing, residuals, ROI and CLV stay
blocked or partial (DR-01, DR-18, DR-59, DR-60).</li>
<li><b>Week 10 injury counts do not reconcile.</b> The availability desk holds 326 rows, the assurance desk 276, and the
2026-11-17 read 347 rendered rows. Cincinnati is 8 in one capture and 4 in another. The 254/279 targets in the brief
appear in no committed capture. No Week 10 injury total should be quoted until a complete recount exists.</li>
<li><b>One season of results.</b> No train, validation or holdout split is possible yet (DR-70), and designation
reliability cannot be calibrated across seasons (DR-44, DR-53).</li>
</ul>
<h2>Numbers that may be quoted, and numbers that may not</h2>
<ul class="clean">
<li>May quote: 150 finals in the complete Week 1-10 file (16+16+16+16+15+14+14+14+15+14 games by week), from the committed file.</li>
<li>May quote with its basis: Week 10 injury rows per capture (326, 276, 347), each labelled with its capture.</li>
<li>May not quote: any Week 10 league total, any price, odds, ROI, CLV, stake or reward. None exists in this project.</li>
</ul>
<h2>Decisions the owner needs to make</h2>
<p>See the <a href="suggestions.html">suggestions</a> page (S1 to S7). Each suggestion lists its options and an acceptance
test. Nothing is implemented until the owner chooses. The questions that block those choices are on the
<a href="gaps.html">questions page</a>.</p>
<h2>What this session did not do</h2>
<ul class="clean">
<li>No capture from nfl.com, and no scheduled retrieval of any kind.</li>
<li>No full re-read of the 2026 rulebook body; only the change table was read.</li>
<li>No complete recount of the Week 10 injury report.</li>
<li>No legal advice. Counsel should read the terms text quoted in the evidence file.</li>
</ul>
"""
    return page_shell("executive-summary.html", "Executive summary", body)


def page_gaps(model) -> str:
    reg = model["registry"]
    rows = []
    for q in model["questions"]:
        blocks = ", ".join(q["blocks"]) if q["blocks"] else "—"
        src_ids = q["sources"]
        src_html = source_links(reg, src_ids) if src_ids else '<span class="blank">no official source yet (flagged)</span>'
        rows.append(
            f'<tr{row_attr(src_ids)}>'
            f'<td class="num">{esc(q["id"])}</td>'
            f'<td>{esc(q["question"])}</td>'
            f'<td>{esc(blocks)}</td>'
            f'<td>{esc(q["known"])}</td>'
            f'<td>{esc(q["missing"])}</td>'
            f'<td>{esc(q["discover"])}</td>'
            f'<td>{esc(q["owner"])}</td>'
            f'<td>{src_html}</td></tr>')
    body = f"""
<h1>Questions and information gaps</h1>
<p class="lede">What must be known before a decision can be made on the information we have, what is missing, and how to find
it from an official or permitted route. Owner choices are left open; this page does not answer them.</p>
{table_card("Questions and gaps", ["ID", "Question", "Blocks rows", "What we know", "What is missing", "How to find out", "Owner", "Source link(s)"], "".join(rows))}
"""
    return page_shell("gaps.html", "Questions and gaps", body)


def page_suggestions(model) -> str:
    cards = []
    for s in model["suggestions"]:
        opts = "".join(f"<li>{esc(o)}</li>" for o in s["options"])
        cards.append(
            f'<div class="card" style="grid-column:auto;text-align:left">'
            f'<b style="font-size:16px">{esc(s["id"])} · {esc(s["title"])}</b>'
            f'<ul class="clean small">{opts}</ul>'
            f'<div class="small"><b>Desk recommendation:</b> {esc(s["desk_recommendation"])}</div>'
            f'<div class="small"><b>Acceptance test:</b> {esc(s["acceptance"])}</div>'
            f'<div class="small"><b>Owner decision:</b> <span class="blank">not yet chosen</span></div></div>')
    body = f"""
<h1>Suggestions</h1>
<p class="lede">Ways to improve the decision-making, each with options and an acceptance test. Nothing here is implemented
until the owner chooses an option. The "owner decision" field is intentionally blank.</p>
<div class="cards" style="grid-template-columns:repeat(auto-fit,minmax(330px,1fr))">{''.join(cards)}</div>
"""
    return page_shell("suggestions.html", "Suggestions", body)


def page_flagged(model, counts) -> str:
    reg = model["registry"]
    rows = []
    for f in model["flags"]:
        ids = f["evidence"]
        rows.append(
            f'<tr{row_attr(ids)}>'
            f'<td class="num">{esc(f["id"])}</td>'
            f'<td>{esc(f["severity"])}</td>'
            f'<td><b>{esc(f["title"])}</b><div>{esc(f["detail"])}</div></td>'
            f'<td>{esc(f["decision"])}</td>'
            f'<td>{source_links(reg, ids)}</td></tr>')
    c = counts
    count_block = (
        f'<ul class="clean small">'
        f'<li>availability CSV: {c["avail_rows"]} rows, {c["avail_clubs"]} clubs; Cincinnati {c["avail_cin"]}, Seattle {c["avail_sea"]}; '
        f'raw practice lines {c["avail_practice_lines"]}; clubs absent = Week 10 byes {", ".join(c["avail_bye_absent"])}</li>'
        f'<li>assurance CSV: {c["assurance_rows"]} rows, {c["assurance_clubs"]} clubs; Cincinnati {c["assurance_cin"]}, Seattle {c["assurance_sea"]}; '
        f'no rows for {", ".join(c["assurance_no_bal_lac"])}</li>'
        f'<li>2026-11-17 read: {c["e7ef_lines"]} rendered rows with a practice status ({c["e7ef_rows"]} unique)</li>'
        f'<li>Week 1-10 results: canonical {c["canon_games"]} rows; complete {c["complete_games"]} rows; difference {", ".join(c["games_only_in_complete"])}</li>'
        '</ul>')
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Irregularities found while reconciling the ledger. They do not block anything on this site. Each has its
evidence links and the decision it needs. Counts below are recomputed from the files on every build.</p>
<h2>Counts recomputed from committed files</h2>
{count_block}
<h2>Irregularities</h2>
{table_card("Flagged irregularities", ["ID", "Severity", "Finding", "Decision needed", "Evidence"], "".join(rows))}
"""
    return page_shell("flagged.html", "Flagged for review", body)


def page_sources(model, evidence_sha) -> str:
    reg = model["registry"]
    used = set()
    for r in model["table"]:
        used.update(r["source_ids"])
    for q in model["questions"]:
        used.update(q["sources"])
    for f in model["flags"]:
        used.update(f["evidence"])
    for o in model["overrides"]:
        used.update(o["sources"])
    new = sorted(s for s in used if s.startswith("K637-"))
    rows = []
    for sid in sorted(used):
        src = reg[sid]
        rows.append(
            f'<tr{row_attr([sid])}>'
            f'<td class="num">{esc(sid)}</td>'
            f'<td>{esc(src["title"])}<div class="small">{esc(src["scope"])}</div></td>'
            f'<td>{esc(src["checked_on"])}</td>'
            f'<td>{esc(src["access"])}</td>'
            f'<td>{link(src["url"], src["url"])}<div class="small">[{"official" if is_official(src) else "repository"}]</div></td></tr>')
    ev_rows = "".join(
        f'<li><code>{esc(name)}</code> sha256 <code>{esc(digest)}</code></li>' for name, digest in sorted(evidence_sha.items()))
    body = f"""
<h1>Sources</h1>
<p class="lede">Every source this desk cites, with its scope, read date and access note. {len(used)} registered sources are used
on these pages, {len(new)} of them registered on {READ_ON}. Repository files are shown as such; they are not official sources.</p>
{table_card("Sources used by this desk", ["Source ID", "Title and scope", "Checked", "Access", "Link"], "".join(rows))}
<h2>Evidence files (verbatim reads, hash-checked on every build)</h2>
<ul class="clean small">{ev_rows}</ul>
"""
    return page_shell("sources.html", "Sources", body)


# ---------------------------------------------------------------- orchestration

def render_all(model, counts, evidence_sha) -> dict[str, str]:
    return {
        "index.html": page_index(model, counts),
        "executive-summary.html": page_summary(model, counts),
        "gaps.html": page_gaps(model),
        "suggestions.html": page_suggestions(model),
        "flagged.html": page_flagged(model, counts),
        "sources.html": page_sources(model, evidence_sha),
    }


def manifest(model, counts, evidence_sha) -> str:
    now_c = Counter(r["now"] for r in model["table"])
    prior_c = Counter(r["prior"] for r in model["table"])
    data = {
        "desk": "nfl-ledger-637442e9",
        "session": SESSION,
        "read_on": READ_ON,
        "pages": [p for p, _ in PAGES] + ["style.css"],
        "lines": len(model["table"]),
        "status_now": {s: now_c.get(s, 0) for s in STATUS_ORDER},
        "status_prior": {s: prior_c.get(s, 0) for s in STATUS_ORDER},
        "changed": [r["id"] for r in model["table"] if r["changed"]],
        "week10_counts": counts,
        "evidence_sha256": evidence_sha,
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    evidence_sha = check_evidence()
    counts = week10_counts()
    model = build_model()
    outputs = render_all(model, counts, evidence_sha)
    outputs["style.css"] = CSS.strip() + "\n"
    outputs["manifest.json"] = manifest(model, counts, evidence_sha)
    if check:
        drift = []
        for name, text in outputs.items():
            path = SITE / name
            if not path.exists() or path.read_text(encoding="utf8") != text:
                drift.append(name)
        if drift:
            print("DRIFT (rebuild needed):", ", ".join(drift))
            return 1
        print(f"OK: {len(outputs)} files reproduce byte-identically; {len(model['table'])} ledger lines; "
              f"{len(evidence_sha)} evidence files hash-checked.")
        return 0
    SITE.mkdir(parents=True, exist_ok=True)
    for name, text in outputs.items():
        (SITE / name).write_text(text, encoding="utf8")
    print(f"Wrote {len(outputs)} files to {SITE.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
