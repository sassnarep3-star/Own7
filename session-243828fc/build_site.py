#!/usr/bin/env python3
"""Render the session 243828fc pages (static HTML, deterministic).

Every table row is produced by row(), which refuses to emit a row without an official or repository
source link. Values that could not be confirmed are written as UNVERIFIED with a blank value.

Usage:  python3 build_site.py          (write pages)
        python3 build_site.py --check  (fail if committed pages differ from a fresh render)

Output goes to site/ (the root scripts/build_site.py registers these pages in the manifest).
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "site"
REGISTRY = HERE.parent / "research" / "sources.json"
REPO_BLOB = "https://github.com/sassnarep3-star/Own7/blob/main/"
LIVE = "https://www.nfl.com/injuries/league/2026/REG10"
LEDGER_PATH = "nfl-availability-28ef/data/injuries-week10-2026.csv"
LEGAL_TERMS = "https://www.nfl.com/legal/terms"
GRA_UNLAWFUL = "https://www.gra.gov.sg/harm-minimisation/unlawful-remote-gambling-activities"
GRA_PROBLEM = "https://www.gra.gov.sg/harm-minimisation/problem-gambling"
GRA_HOME = "https://www.gra.gov.sg/"
DET_CHART = "https://www.detroitlions.com/team/depth-chart"
NFL_STANDINGS = "https://www.nfl.com/standings/"
NFL_INACTIVES_WK9 = "https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season"
RGA_STATUTE = "https://sso.agc.gov.sg/Act/RGA2014"

CSS = """
:root{--ink:#1d2430;--mut:#5b6575;--line:#dfe3ea;--bg:#f6f7f9;--card:#fff;--acc:#1f5fbf;--warn:#9a5b00;--bad:#a1260d;--ok:#1e6b34}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#14213d;color:#fff;padding:14px 22px}header a{color:#fff;margin-right:14px;text-decoration:none;font-size:14px}
header .brand{font-weight:700;margin-right:24px}nav a:hover{text-decoration:underline}
main{max-width:1180px;margin:0 auto;padding:22px}h1{font-size:24px;margin:6px 0 4px}h2{font-size:18px;margin:28px 0 8px}
p.lead{color:var(--mut);margin-top:0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}.card b{display:block;font-size:24px}.card span{color:var(--mut);font-size:13px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);font-size:13.5px;margin:8px 0 18px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#eef1f6;position:sticky;top:0}
td.num{text-align:right;font-variant-numeric:tabular-nums}.tag{display:inline-block;padding:1px 7px;border-radius:999px;font-size:12px;border:1px solid var(--line)}
.unv{color:var(--warn);font-weight:600}.flag{color:var(--bad);font-weight:600}.ok{color:var(--ok);font-weight:600}
.note{background:#fff8e6;border:1px solid #f1d894;border-radius:8px;padding:10px 14px;margin:12px 0}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:10px 0}
input.filter{width:100%;max-width:420px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;margin:6px 0}
footer{color:var(--mut);font-size:12.5px;padding:18px 22px;max-width:1180px;margin:0 auto}
"""

NAV = [("index.html", "Executive summary"), ("live-check.html", "Live check (14 Nov)"),
       ("depletion.html", "Starter & backup depletion"), ("gaps.html", "Questions & suggestions"),
       ("legal.html", "Legal & responsible gambling"), ("repo-audit.html", "Repo audit"),
       ("flagged.html", "Flagged for Review")]


def e(x) -> str:
    return html.escape(str(x), quote=True)


def link(url: str, label: str | None = None) -> str:
    return f'<a href="{e(url)}" rel="noopener">{e(label or url)}</a>'


def _url_ids():
    """URL -> registry ID for this session's X243-* records (research/sources.json, append-only)."""
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    out = {}
    for r in reg:
        if r["id"].startswith("X243-"):
            out[r["url"]] = r["id"]
    return out


URL_IDS = _url_ids()

ALLOWED_SOURCE = re.compile(
    r'href="(https://www\.nfl\.com/|https://www\.gra\.gov\.sg/|https://sso\.agc\.gov\.sg/|'
    r'https://www\.detroitlions\.com/|https://github\.com/sassnarep3-star/Own7/)[^"]*"')


def row(cells: list[str], source_html: str, *, classes: str = "") -> str:
    """One table row. Every link in the source cell must be a registered official or repo source.

    The row carries data-source-ids (the registry IDs of those links), which the repo audit requires.
    A row without a registered link is a build error by design.
    """
    hrefs = re.findall(r'href="([^"]+)"', source_html)
    if not hrefs:
        raise ValueError("row without a source link: %r" % (cells[:2],))
    for h in hrefs:
        if not ALLOWED_SOURCE.search('href="%s"' % h):
            raise ValueError("source link not on an allowed official or repo host: %s" % h)
        if h not in URL_IDS:
            raise ValueError("source link not registered in research/sources.json: %s" % h)
    ids = " ".join(sorted({URL_IDS[h] for h in hrefs}))
    tds = "".join(f"<td>{c}</td>" for c in cells)
    return f'<tr class="{classes}" data-source-ids="{ids}">{tds}<td>{source_html}</td></tr>'


def table(headers: list[str], rows: list[str], *, source_header: str = "Source (official / repo)",
          table_id: str = "", filterable: bool = False) -> str:
    th = "".join(f"<th>{e(h)}</th>" for h in headers + [source_header])
    body = "\n".join(rows)
    tid = f' id="{table_id}"' if table_id else ""
    return f'<table{tid}><thead><tr>{th}</tr></thead><tbody>\n{body}\n</tbody></table>'


def page(title: str, active: str, body: str, lead: str = "") -> str:
    items = []
    for href, lbl in NAV:
        cur = ' aria-current="page"' if href == active else ""
        items.append('<a href="%s"%s>%s</a>' % (href, cur, e(lbl)))
    nav = "".join(items)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · Session 243828fc · NFL Week 10 check</title><style>{CSS}</style></head>
<body><header><span class="brand">NFL Week 10 · 243828fc</span><nav>{nav}</nav></header>
<main><h1>{e(title)}</h1>{('<p class="lead">' + e(lead) + '</p>') if lead else ''}{body}</main>
<footer>Unofficial research page. Not affiliated with or endorsed by the NFL or any club. Data read from the
publishers named in each row on 14 Nov 2026 (Singapore time); statuses change until kickoff. Nothing here is a
betting recommendation. Values not confirmed by an official source are blank or marked UNVERIFIED.</footer>
</body></html>"""


def load_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_csv(name):
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------- pages
UNV = '<span class="unv">UNVERIFIED</span>'
LEDGER_FILE = HERE.parent / LEDGER_PATH


def ledger_facts():
    """Facts that come only from the saved desk ledger file (a repo file, so it can be re-read)."""
    rows = load_csv_path(LEDGER_FILE)
    clubs = sorted({r["club_abbr"] for r in rows})
    gs = [r for r in rows if (r.get("game_status") or "").strip()]
    gs_clubs = sorted({r["club_abbr"] for r in gs})
    return {"rows": len(rows), "clubs": len(clubs), "gs_rows": len(gs), "gs_clubs": gs_clubs}


def load_csv_path(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def page_index(findings):
    lf = ledger_facts()
    cards = [
        (str(lf["rows"]), "rows in the saved desk ledger (repo file, read 14 Nov)"),
        (f'{len(lf["gs_clubs"])} of {lf["clubs"]}', "clubs with any game status in the saved ledger (repo file)"),
        ("UNVERIFIED", "live Week 10 report: row counts withheld until the transcription is checked"),
        ("22 of 24", "team rows spot-checked against NFL.com standings that match (NYG and WAS differ)"),
    ]
    card_html = "".join(f'<div class="card"><b>{e(n)}</b><span>{e(t)}</span></div>' for n, t in cards)
    body = f"""
<div class="note"><b>Bottom line.</b> The Week 10 official injury report was read on 14 Nov 2026 and does not match the
saved desk ledger (13 Nov). Its game-status column also covers more clubs than the ledger does. The row-level values are
<b>not published here</b>: the transcription has not been checked line by line against the report, so every value from it is
UNVERIFIED and withheld. No betting line, price, edge, correlation or strategy can be verified from an official source,
so none is shown.</div>
<div class="cards">{card_html}</div>

<h2>What was checked, and how</h2>
<div class="box"><ul>
<li><b>Live injury report:</b> {link(LIVE)}: read through the fetch tool on 14 Nov 2026 (8 chunks). The rows were
transcribed into a working file, which is <b>not yet verified</b> against the page. Unverified rows are not shown.</li>
<li><b>Saved ledger</b> {e(LEDGER_PATH)}: counts above were taken from the file itself.</li>
<li><b>Standings spot check:</b> 24 of 32 team rows compared with {link(NFL_STANDINGS)}: 22 match on W-L-T, points for and
against, and streak. NYG and WAS differ and the cause is not established (see <a href="flagged.html">Flagged for Review</a>).
Eight teams are not yet checked.</li>
<li><b>Depletion:</b> starter-to-backup analysis is not published. It needs the verified injury data, and the club charts
are labelled unofficial by the clubs that publish them (Detroit: {link(DET_CHART, 'depth chart')}).</li>
<li><b>Rights and law:</b> {link(LEGAL_TERMS, 'NFL.com terms §1.3')} and the Gambling Regulatory Authority pages
(see <a href="legal.html">Legal</a>).</li>
</ul></div>

<h2>Open questions and how to close them</h2>
<p>See <a href="gaps.html">Questions &amp; suggestions</a>. Priority: (1) verify the Week 10 transcription and decide how the injury
data is refreshed; (2) decide whether compiled NFL.com rows may stay in a public repository (<a href="flagged.html">F07</a>);
(3) confirm the legal position for any wagering-linked use from Singapore (<a href="flagged.html">F08</a>); (4) find an
official game-day inactive list to answer "who is out" (<a href="gaps.html">Q02</a>).</p>
"""
    return page("Executive summary", "index.html", body,
                lead="NFL Week 10 (2026): live injury check, depletion status, gaps and flags.")


def page_live():
    body = f"""<div class="note"><b>Row-level values withheld.</b> The live Week 10 report (
{link(LIVE)}) was read on 14 Nov 2026, but the transcription of its rows has not been checked against the source. Every value
from it is UNVERIFIED, so the per-club counts and the row list are not shown. They will be published only after a line-by-line
check. Until then, read the source directly.</div>
<h2>Saved desk ledger (repo file, 13 Nov capture)</h2>
<p>The table below uses only the ledger file. It shows the ledger's own counts by club. Source for every row: the ledger
file in the repo.</p>
{ledger_table()}
<h2>Live report</h2>
<table><thead><tr><th>Measure</th><th>Value</th><th>Source (official)</th></tr></thead><tbody>
{row(["Rows on the live report", UNV], link(LIVE, "nfl.com live report"))}
{row(["Rows different from the saved ledger", UNV], link(LIVE, "nfl.com live report"))}
{row(["Players added on the live page", UNV], link(LIVE, "nfl.com live report"))}
{row(["Clubs with game status on the live page", UNV], link(LIVE, "nfl.com live report"))}
</tbody></table>"""
    return page("Live check, 14 Nov 2026", "live-check.html", body,
                lead="Saved desk ledger compared with the live Week 10 report. Live values withheld until verified.")


def ledger_table():
    rows = load_csv_path(LEDGER_FILE)
    by = {}
    for r in rows:
        d = by.setdefault(r["club_abbr"], [0, 0])
        d[0] += 1
        if (r.get("game_status") or "").strip():
            d[1] += 1
    trs = []
    for c in sorted(by):
        src_url = next(r["source_url"] for r in rows if r["club_abbr"] == c)
        trs.append(row([e(c), str(by[c][0]), str(by[c][1])], link(src_url, "nfl.com injury report (ledger source_url)")))
    return table(["Club", "Ledger rows", "Rows with game status"], trs, source_header="Source")


def page_depletion():
    body = f"""<div class="note"><b>Withheld.</b> Starter and backup depletion is not published yet. It depends on the live
injury values (UNVERIFIED, see <a href="live-check.html">Live check</a>) and on club charts that the clubs label unofficial
(Detroit: {link(DET_CHART, 'depth chart')}). A chart order is not a verified starter, and no snap counts, ratings or
performance data have been collected.</div>
<h2>What is needed before this page can show anything</h2>
<ul>
<li>Verified Week 10 injury values (line-by-line check of the live report).</li>
<li>Official game-day inactive lists for the games (see <a href="gaps.html">Q02</a>).</li>
<li>An official performance source for the backup comparison (see <a href="gaps.html">Q04</a>).</li>
</ul>"""
    return page("Starter & backup depletion", "depletion.html", body,
                lead="Who is out, and who would replace them, will appear here once the inputs are verified.")


def page_gaps():
    qs = load_json("questions.json")
    sg = load_json("suggestions.json")
    qrows = []
    for q in qs:
        src = link(q["source_url"], q["source_label"])
        qrows.append(row([e(q["id"]), e(q["question"]), e(q["have"]), e(q["missing"]), e(q["close_by"]), e(q["blocks"])], src))
    qt = table(["ID", "Question", "What we have (sourced)", "What is missing", "How to close it", "Blocks"], qrows,
               source_header="Source")
    srows = []
    for s_ in sg:
        src = link(s_["source_url"], s_["source_label"])
        srows.append(row([e(s_["id"]), e(s_["suggestion"]), e(s_["evidence"]), e(s_["cost_estimate"]), e(s_["risk"]),
                          e(s_["acceptance_test"]), '<span class="tag">Decision: pending, nothing implemented</span>'], src))
    st = table(["ID", "Suggestion", "Evidence", "Cost (estimate)", "Risk", "Acceptance test", "Decision"], srows,
               source_header="Source")
    body = f"""<p class="lead">Two lists. The first says what the data can and cannot answer. The second is a set of proposals.
Nothing in the second list has been implemented; each needs an owner decision.</p>
<h2>Questions, information we have, information we lack</h2>{qt}
<h2>Suggestions to review and choose from (not implemented)</h2>{st}"""
    return page("Questions & suggestions", "gaps.html", body,
                lead="A decision list. Each suggestion states its evidence, cost, risk and an acceptance test.")

def page_legal():
    rows = [
        row(["Unlicensed remote gambling in or from Singapore", "Unlawful for any person to provide unlicensed remote gambling "
             "services in or from Singapore, or from outside Singapore to persons situated in Singapore. Singapore Pools is the "
             "only operator the GRA has licensed to provide remote gambling services.",
             "Official GRA page, read 14 Nov 2026"], link(GRA_UNLAWFUL)),
        row(["Participating in unlicensed remote gambling (individuals)", "The GRA page states it is an offence for any person in "
             "Singapore to participate in unlicensed remote gambling; on conviction a fine not exceeding $10,000, or up to 6 months' "
             "imprisonment, or both.", "Official GRA page, read 14 Nov 2026. Note: some secondary blogs quote $5,000; the GRA "
             "figure is used here."], link(GRA_UNLAWFUL)),
        row(["Penalties for operators", "Up to $500,000 fine and up to 7 years' imprisonment; repeat offenders up to $700,000 and "
             "10 years, per the GRA page.", "Official GRA page, read 14 Nov 2026"], link(GRA_UNLAWFUL)),
        row(["Reporting and enforcement", "From 1 Jan 2025 the Singapore Police Force handles blocking of unlawful remote "
             "gambling services, their advertising and payment transactions (GRA page).", "Official GRA page, read 14 Nov 2026"],
            link(GRA_UNLAWFUL)),
        row(["Responsible-gambling resources", "GRA links to the National Council on Problem Gambling as part of Singapore's "
             "national framework for problem gambling.", "Official GRA page, read 14 Nov 2026"], link(GRA_PROBLEM)),
        row(["Remote Gambling Act 2014 statute text", '<span class="unv">UNVERIFIED</span> — the statute page returned '
             '"Page Not Found" from this sandbox on 14 Nov 2026. The GRA pages above are used instead.',
             "Attempted: sso.agc.gov.sg"], link(RGA_STATUTE)),
        row(["NFL.com terms §1.3 (permitted use)", "Use is for the user's own individual non-commercial and informational purposes; "
             "systematic retrieval of data to create or compile a collection, compilation, database or directory is prohibited "
             "absent the NFL's express prior written consent. Terms updated May 16, 2024.", "Official NFL.com terms, read 14 Nov 2026"],
            link(LEGAL_TERMS)),
    ]
    t = table(["Topic", "What the source says", "Source note"], rows, source_header="Source (official)")
    body = f"""<div class="note"><b>Not legal advice.</b> This page records what the official sources say. It does not decide
whether any activity is lawful for any person. Before any leaderboard, reward, or wagering-linked use is designed or
run from Singapore, a qualified Singapore lawyer should review it. This project does not recommend or place wagers.</div>
{t}
<p>Practical consequence for this project: the only operator the GRA names as licensed for remote gambling is Singapore
Pools. Any idea that involves placing bets with other operators, or rewarding wagering results, is outside what this
project can verify. It stays blocked until the legal review is done.</p>"""
    return page("Legal & responsible gambling", "legal.html", body,
                lead="What the Singapore regulator and NFL.com say. Sourced, not advice.")


def page_repo_audit(audit):
    rows = []
    for a in audit:
        rows.append(row([e(a["id"]), e(a["file"]), e(a["finding"]), e(a["check_performed"]), e(a["severity"])],
                        link(a["link"], a["link_label"])))
    t = table(["ID", "File / area", "Finding", "Check performed", "Severity"], rows, source_header="Source / file for review")
    body = f"""<p class="lead">A line-by-line look at the parts of the repo this session touched, and what each
check showed. Baseline on this branch: 27 of 27 CI-equivalent commands passed before this session's changes (see COORDINATION.md, P1).</p>{t}"""
    return page("Repo audit", "repo-audit.html", body, lead="Irregularities for review, each with the file or source to check.")

def page_flagged(flags):
    rows = []
    for f_ in flags:
        if not f_["sources"]:
            raise ValueError("flag without a source: " + f_["id"])
        src = " · ".join(link(u, lbl) for lbl, u in f_["sources"])
        rows.append(row([e(f_["id"]), e(f_["title"]), e(f_["detail"]), e(f_["blocks"]), e(f_["owner_action"])], src))
    t = table(["ID", "Flag", "Detail", "Blocks", "Owner action"], rows, source_header="Source (official or repo)")
    body = f"""<div class="note"><b>Flagged for Review.</b> These items are published for your review and do not block the
merge. Each has a source link, so it can be checked without the agent.</div>{t}"""
    return page("Flagged for Review", "flagged.html", body, lead="Irregularities, unverified items and decisions for the owner.")

def build_pages():
    findings = load_json("findings.json")
    return {
        "index.html": page_index(findings),
        "live-check.html": page_live(),
        "depletion.html": page_depletion(),
        "gaps.html": page_gaps(),
        "legal.html": page_legal(),
        "repo-audit.html": page_repo_audit(findings["audit"]),
        "flagged.html": page_flagged(findings["flags"]),
    }


def main(check: bool) -> int:
    pages = build_pages()
    if check:
        stale = [n for n, t in pages.items() if not (OUT / n).exists() or (OUT / n).read_text(encoding="utf-8") != t]
        if stale:
            print("STALE pages:", *stale)
            return 1
        print(f"OK: {len(pages)} pages reproduce exactly.")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for n, t in pages.items():
        (OUT / n).write_text(t, encoding="utf-8", newline="\n")
    (OUT / "manifest.json").write_text(json.dumps({"pages": sorted(pages), "generated": True,
        "boundary": "Static pages; every table row carries a registered source link; unverified values are blank."},
        indent=2) + "\n", encoding="utf-8")
    print("wrote", ", ".join(sorted(pages)))
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
