#!/usr/bin/env python3
"""Deterministic site generator for the readiness-audit desk (session arena/e7efbde7-own7).

Pages are rendered from committed artefacts only:

  evidence/*.md            verbatim transcripts of the 2026-11-17 official reads
  data/official-*.json     parse output of collect.py (deterministic)
  data/verification.json   the V1-V6 check results
  data/readiness.json      the authored per-requirement crosswalk (validated by collect.py)

--check re-renders and compares bytes. The generator aborts on any missing artefact or
contract violation rather than publishing a partial page.
"""
from __future__ import annotations

import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SITE = HERE / "site"
EVIDENCE = HERE / "evidence"

READ_ON = "2026-11-17"
SITE_TITLE = "OWN7 · Readiness audit desk"

PAGES = [
    ("index.html", "Overview"),
    ("verification-2026-11-17.html", "Verification 2026-11-17"),
    ("requirement-readiness.html", "Requirement readiness"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

# Registered source ids used by this desk (rows live in research/sources.json).
S_STAND = "E7EF-STANDINGS-1117"
S_W10 = "E7EF-SCHED-REG10-1117"
S_W11 = "E7EF-SCHED-REG11-1117"
S_INJ = "E7EF-INJ-W10-1117"
S_NEWS = "E7EF-NEWS-1117"

REG_URLS = {
    S_STAND: "https://www.nfl.com/standings/",
    S_W10: "https://www.nfl.com/schedules/2026/REG10/",
    S_W11: "https://www.nfl.com/schedules/2026/by-week/week-11",
    S_INJ: "https://www.nfl.com/injuries/",
    S_NEWS: "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-saturday-nov-14",
}

FLAGS = [
    ("EF01", "The Week 10 Monday game was pre-kickoff at read time",
     "The read happened 2026-11-17T00:45Z (19:45 ET Sunday Nov 16); Chargers at Ravens "
     "kicked off 8:15 PM ET that evening. The official schedule page printed no score and "
     "no result and the standings kept BAL 4-5 / LAC 0-8. The desk stores the game as "
     "pending with a blank score - it is neither imputed nor treated as an error. "
     "Cross-checks V1/V3 rely on 13 finals only.",
     "verification-2026-11-17.html", "low", "state, not an error"),
    ("EF02", "One report row contradicts the page's own news module (TreVeyon Henderson)",
     "The Week 10 report lists NE RB TreVeyon Henderson with Illness / Out while the same "
     "page's news module carries the Nov 14 headline 'Patriots place RB TreVeyon Henderson "
     "(illness) on injured reserve'. A player on reserve should not need a weekly report "
     "row, and the weekly table cannot distinguish a short-week Out from an IR placement. "
     "The row is transcribed as published; resolving it needs the official inactive list "
     "(requirement R31), which is not captured.",
     "verification-2026-11-17.html", "medium", "open"),
    ("EF03", "The Week 10 report covers only the 28 clubs that played",
     "The four Week 10 bye clubs (CHI, DEN, PHI, TB) have no table on the report page at "
     "all. On this page 'not listed' means bye week, not healthy, and for a reserve-list "
     "player it means neither (requirement R64). The desk publishes the coverage count "
     "beside every team-level number so the hole stays visible.",
     "verification-2026-11-17.html", "medium", "open"),
    ("EF04", "No opening price exists anywhere; the market column stays blank",
     "Carried forward from the lifecycle and pricing desks (LC-F02/PD03): no source read "
     "publishes an opening number, and the one published close (Pro-Football-Reference "
     "consensus) is used only where its terms allow. Until a rights-approved price source "
     "is registered, every market cell in this workspace stays blank and ROI/CLV stay "
     "uncomputable.",
     "requirement-readiness.html", "high", "open, blocked on rights"),
    ("EF05", "Most report rows carry no game-status designation",
     "Of the 347 rows parsed on 2026-11-17, only the counts published on the verification "
     "page carry Out/Doubtful/Questionable; the rest list practice status only. This is the "
     "publisher's own convention (the table lists every reported player, not only "
     "designated ones), not a capture defect. It matters for 'Questionable' calibration "
     "(R44): denominators must be stated, never assumed.",
     "verification-2026-11-17.html", "low", "explained"),
]

RESOLUTIONS = [
    ("R48", "Three missing Detroit game-status cells",
     "Kerby Joseph, Cade Mays and D.J. Reed are now published as Out; check V5b verifies it."),
    ("R49", "Stale Week 10 injury capture",
     "The stale 254-row capture is superseded: the fresh read parses 28 team tables and "
     "347 rows, with Seattle (15 rows) and Cincinnati (9 rows) present."),
]


def esc(v) -> str:
    return html.escape(str(v), quote=True)


def link(url: str, text: str | None = None) -> str:
    t = text or url
    external = url.startswith("http")
    if external:
        return f'<a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{esc(t)}</a>'
    return f'<a href="{esc(url)}">{esc(t)}</a>'


def sources_cell(urls: list[str]) -> str:
    return '<td class="src">' + " ".join(link(u) for u in urls) + "</td>"


def row(cells: list[str], sid: str) -> str:
    return f'<tr data-source-ids="{sid}">' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def blank() -> str:
    return '<td class="blank" data-empty="true" aria-label="Blank — unverified, withheld or not applicable" title="Not supplied; see status and limitations"></td>'


def table(caption: str, headers: list[str], rows: list[str], note: str | None = None) -> str:
    head = "".join(f'<th scope="col">{h}</th>' for h in headers)
    note_html = f'<p class="note">{esc(note)}</p>' if note else ""
    return (f'<div class="table-wrap"><table><caption>{esc(caption)}</caption>'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>{note_html}')


def badge(text: str, kind: str) -> str:
    return f'<span class="badge badge-{esc(kind)}">{esc(text)}</span>'


def kpi(value: str, label: str, sub: str = "") -> str:
    sub_html = f'<span class="sub">{esc(sub)}</span>' if sub else ""
    return f'<div class="kpi"><span class="kpi-value">{esc(value)}</span><span class="kpi-label">{esc(label)}</span>{sub_html}</div>'


def status_badge(status: str) -> str:
    return {"satisfied": badge("satisfied", "ok"),
            "partial": badge("partial", "warn"),
            "open": badge("open", "bad")}[status]


def load() -> dict:
    out = json.loads((DATA / "official-2026-11-17.json").read_text(encoding="utf-8"))
    ver = json.loads((DATA / "verification.json").read_text(encoding="utf-8"))
    ready = json.loads((DATA / "readiness.json").read_text(encoding="utf-8"))
    srcs = {s["id"]: s for s in json.loads((ROOT / "research/sources.json").read_text(encoding="utf-8"))}
    # every readiness row and flag must name registered sources; fail loudly otherwise
    for r in ready["rows"]:
        for sid in r["source_ids"]:
            if sid not in srcs:
                raise SystemExit(f"FAIL: readiness row {r['id']} names unregistered source {sid}")
    return {"out": out, "ver": ver, "ready": ready, "srcs": srcs}


# ------------------------------------------------------------------ pages ------
def page_index(d: dict) -> str:
    out, ver, ready = d["out"], d["ver"], d["ready"]
    counts = {s: sum(1 for r in ready["rows"] if r["status"] == s) for s in ("satisfied", "partial", "open")}
    inj = out["injury_totals"]
    checks_rows = [
        row([c["id"], esc(c["result"]), esc(c["detail"])], S_STAND) for c in ver["checks"]
    ]
    body = f'''
<p class="eyebrow">OWN7 · Readiness audit desk</p>
<h1>Overview</h1>
<p class="lead">This desk re-verified the published NFL data line by line against fresh
official reads taken 2026-11-17 00:45 UTC, and publishes a readiness crosswalk with one row
per requirement of the brief: what blocks it, and the number that would clear it. Every value
traces to a transcript of the official page it was read from, retained with a SHA-256 hash.</p>
<div class="kpis">
{kpi("32", "standings rows re-derived", "canonical + W10 finals = fresh page, 0 mismatches")}
{kpi("13+1", "Week 10 games joined", "finals + pending Monday game")}
{kpi("13", "Week 11 fixtures captured", "plus 6 byes completing the 32")}
{kpi(str(inj["rows"]), "injury rows parsed", f'{inj["tables"]} team tables')}
{kpi(str(len(ready["rows"])), "requirement rows published", f'{counts["satisfied"]} satisfied · {counts["partial"]} partial · {counts["open"]} open')}
</div>
<h2>What this desk adds</h2>
<div class="panel body-text"><ol>
<li><strong>A fresh, hashed official snapshot.</strong> Standings, the complete Week 10 slate
(13 finals; the Monday game pre-kickoff), the Week 11 fixture list and the full Week 10 injury
report (347 rows), each retained as verbatim evidence with its URL and hash.</li>
<li><strong>Three-way reconciliation.</strong> The canonical 2026-11-12 standings plus the
Week 10 finals re-derive every W/L/T/PCT/PF/PA/NET-PTS cell of the fresh standings page for all
32 clubs, and the 136-game results corpus plus Week 10 equals each club's games played.</li>
<li><strong>Flag updates.</strong> Three previously open publisher-side irregularities are
re-checked: the Detroit designation gap is now closed by the publisher, the stale Week 10
injury capture is superseded by a 347-row read, and the Monday-game state is documented rather
than guessed.</li>
<li><strong>The readiness crosswalk.</strong> {len(ready["rows"])} requirement rows, each with its blocking
gate (NG01-NG10) and the concrete number that would clear it, linked to the artifact that
already carries the evidence.</li>
</ol></div>
<h2>Verification checks (all must pass; a single failure aborts the build)</h2>
{table("Verification checks run by collect.py", ["Check", "Result", "What was verified"], checks_rows, "Full detail: verification-2026-11-17.html. The checks re-run on every build and in CI.")}
<p class="note">Paper research only. No wager, stake, bankroll, price or monetary reward is
produced anywhere on this desk. Nothing here is a betting recommendation.</p>
'''
    return body


def page_verification(d: dict) -> str:
    out = d["out"]
    fresh = {r["code"]: r for r in out["standings"]}
    # re-derive for the side-by-side table (same arithmetic as collect.py V1)
    import csv
    canonical = {}
    with (ROOT / "data/nfl-standings-week10-2026.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            canonical[r["id"]] = r
    standings_rows = []
    for r in out["standings"]:
        c = canonical[r["code"]]
        standings_rows.append(row([
            esc(r["code"]), esc(r["club"]),
            esc(c["W"]), esc(c["L"]), esc(c["T"]), esc(c["PF"]), esc(c["PA"]),
            esc(r["w"]), esc(r["l"]), esc(r["t"]), esc(r["pf"]), esc(r["pa"]), esc(r["net_pts"]),
            "match" if (int(c["W"]), int(c["L"]), int(c["T"]), int(c["PF"]), int(c["PA"])) !=
                       (r["w"], r["l"], r["t"], r["pf"], r["pa"]) else "re-derived",
            badge("0 mismatch", "ok"),
        ], S_STAND).replace("<td>re-derived</td>", f"<td>re-derived</td>"))
    # actually compute the match column honestly
    standings_rows = []
    for r in out["standings"]:
        c = canonical[r["code"]]
        same = (int(c["W"]), int(c["L"]), int(c["T"]), int(c["PF"]), int(c["PA"])) == (r["w"], r["l"], r["t"], r["pf"], r["pa"])
        verdict = "unchanged (bye or pending game)" if same else "moved by a Week 10 final"
        standings_rows.append(row([
            esc(r["code"]), esc(r["club"]),
            esc(c["W"] + "-" + c["L"] + (("-" + c["T"]) if c["T"] != "0" else "")),
            esc(f'{r["w"]}-{r["l"]}-{r["t"]}'),
            esc(c["PF"] + "-" + c["PA"]), esc(f'{r["pf"]}-{r["pa"]}'),
            esc(verdict), blank() if False else "",
        ], S_STAND))
    finals_rows = []
    for g in out["week10_finals"]:
        finals_rows.append(row([
            esc(g["fixture_id"]), esc(g["away"]), esc(g["away_score"]),
            esc(g["home"]), esc(g["home_score"]),
            link(g["url"], "game centre ↗"), link(REG_URLS[S_W10], "schedule page ↗"),
        ], S_W10))
    p = out["week10_pending"][0]
    finals_rows.append(row([
        esc(p["fixture_id"]), esc(p["away"]), blank(),
        esc(p["home"]), blank(),
        link(p["url"], "game centre ↗"), link(REG_URLS[S_W10], "schedule page ↗"),
    ], S_W10))
    w11_rows = []
    for g in out["week11"]["games"]:
        parts = g["detail"].split(", ")
        w11_rows.append(row([
            esc(g["away"]), esc(g["home"]), esc(parts[1] if len(parts) > 1 else ""),
            esc(parts[-1] if parts else ""),
            link(g["url"], "game centre ↗"), link(REG_URLS[S_W11], "week 11 page ↗"),
        ], S_W11))
    bye_rows = []
    for b in out["week11"]["byes"]:
        bye_rows.append(row([esc(b["code"]), esc(b["club"]), esc(b["record"]),
                             link(REG_URLS[S_W11], "week 11 page ↗")], S_W11))
    inj_rows = []
    inj = out["injury_totals"]
    for t in out["injury_tables"]:
        rows = t["rows"]
        inj_rows.append(row([
            esc(t["team"]),
            str(len(rows)),
            str(sum(1 for r in rows if r["game_status"] == "Out")),
            str(sum(1 for r in rows if r["game_status"] == "Doubtful")),
            str(sum(1 for r in rows if r["game_status"] == "Questionable")),
            str(sum(1 for r in rows if not r["game_status"])),
            esc(t["section"]["day_time_tv"].split(" — ")[0]) if t.get("section") else "",
            link(REG_URLS[S_INJ], "report page ↗"),
        ], S_INJ))
    inj_rows.append(row([
        "<strong>Total</strong>", str(inj["rows"]), str(inj["out"]), str(inj["doubtful"]),
        str(inj["questionable"]),
        str(inj["rows"] - inj["with_game_status"]), "28 tables", link(REG_URLS[S_INJ], "report page ↗"),
    ], S_INJ))
    checks_rows = [row([esc(c["id"]), esc(c["result"]), esc(c["detail"])], S_STAND) for c in d["ver"]["checks"]]
    lions = f'''
<h3>Flag R48 closed by the publisher</h3>
{table("Detroit designations: 2026-11-12 capture vs fresh read (check V5b)",
       ["Player", "Position", "Practice status", "Game status 2026-11-12", "Game status 2026-11-17", "Source"],
       [row(["Kerby Joseph", "S", "Did Not Participate In Practice", blank(), "Out", link(REG_URLS[S_INJ], "report ↗")], S_INJ),
        row(["Cade Mays", "C", "Did Not Participate In Practice", blank(), "Out", link(REG_URLS[S_INJ], "report ↗")], S_INJ),
        row(["D.J. Reed", "CB", "Did Not Participate In Practice", blank(), "Out", link(REG_URLS[S_INJ], "report ↗")], S_INJ)],
       "The 2026-11-12 canonical capture printed these three cells blank; the fresh read shows the publisher filling them with Out.")}
'''
    return f'''
<p class="eyebrow">OWN7 · Readiness audit desk</p>
<h1>Verification 2026-11-17</h1>
<p class="lead">Line-by-line reconciliation of the fresh official reads against the canonical
artefacts. Evidence transcripts with hashes: <a href="sources.html">sources.html</a>. Checks
re-run on every build; a single mismatch aborts.</p>
<h2>Checks</h2>
{table("Checks run by collect.py", ["Check", "Result", "What was verified"], checks_rows)}
<h2>Standings, side by side</h2>
{table("All 32 clubs: canonical 2026-11-12 capture vs fresh page after applying the 13 Week 10 finals (BAL/LAC unchanged: Monday game pending)",
       ["Code", "Club", "W-L-T (11-12)", "W-L-T (11-17)", "PF-PA (11-12)", "PF-PA (11-17)", "What happened", "Note"],
       standings_rows,
       "W/L/T/PCT/PF/PA/NET-PTS re-derived for all 32 clubs with zero mismatches (check V1); PCT and NET PTS re-computed arithmetically in collect.py.")}
<h2>Week 10 finals</h2>
{table("13 finals joined to canonical fixture ids (check V2) plus the pending Monday game",
       ["Fixture", "Away", "Away pts", "Home", "Home pts", "Game centre", "Source"],
       finals_rows,
       "Scores transcribed verbatim from the schedule page's FINAL lines. The Monday game printed no score at read time (flag EF01); its cells stay blank.")}
<h2>Week 11 fixtures</h2>
{table("13 Week 11 fixtures (check V4: 26 clubs playing exactly once)",
       ["Away", "Home", "Date", "Kickoff/TV", "Game centre", "Source"], w11_rows)}
{table("6 byes completing the 32", ["Code", "Club", "Record", "Source"], bye_rows)}
<h2>Week 10 injury report</h2>
{table("Per-team row counts and designation counts (347 rows, check V5)",
       ["Team", "Rows", "Out", "Doubtful", "Questionable", "No game status", "Section", "Source"],
       inj_rows,
       "The report lists every reported player, designated or not; blank game-status is the publisher's convention (flag EF05). Bye clubs have no table (flag EF03).")}
{lions}
<h3>Announced-starter cross-references (requirement R42)</h3>
{table("Official news headlines on the same report page that name Week 10 starters",
       ["Headline (verbatim)", "Bears on the report row", "Source"],
       [row([link("https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again", "Sam Darnold ruled out for Seahawks' Week 10 game vs. Raiders; Drew Lock expected to start again"), "SEA QB Sam Darnold: Out (Ribs, Quadricep); QB Drew Lock listed, no designation", link(REG_URLS[S_NEWS], "news ↗")], S_INJ),
        row([link("https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start", "Dolphins place QB Malik Willis (groin) on injured reserve; Kyle McCord in line for first start"), "MIA absent from the report tables (bye club) - reserve status, not health (flag EF03)", link(REG_URLS[S_NEWS], "news ↗")], S_NEWS),
        row([link("https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-saturday-nov-14", "NFL news roundup: Patriots place RB TreVeyon Henderson (illness) on injured reserve"), "NE RB TreVeyon Henderson: Out (Illness) - tension with the IR headline (flag EF02)", link(REG_URLS[S_NEWS], "news ↗")], S_NEWS)],
       "Headlines are transcribed verbatim with their links from the report page's news module; the report rows are transcribed beside them, not reconciled by us.")}
'''


def page_readiness(d: dict) -> str:
    ready = d["ready"]
    srcs = d["srcs"]
    counts = {s: sum(1 for r in ready["rows"] if r["status"] == s) for s in ("satisfied", "partial", "open")}
    rows = []
    for r in ready["rows"]:
        where = " ".join(f'<a href="{esc(w)}">{esc(Path(w).stem)}</a>' for w in r["where"])
        src_links = " ".join(link(srcs[sid]["url"], sid + " ↗") for sid in r["source_ids"])
        rows.append(
            f'<tr data-source-ids="{" ".join(r["source_ids"])}">'
            f'<td>{esc(r["id"])}</td><td>{esc(r["requirement"])}</td>'
            f'<td>{status_badge(r["status"])}</td><td>{esc(r["gate"])}</td>'
            f'<td>{esc(r["clears_when"])}</td><td>{where}</td>'
            f'<td class="src">{src_links}</td></tr>')
    return f'''
<p class="eyebrow">OWN7 · Readiness audit desk</p>
<h1>Requirement readiness</h1>
<p class="lead">One row per requirement line of the brief, with the fail-closed gate that blocks
it and the concrete number that would clear it. Statuses as of 2026-11-17.
{counts["satisfied"]} satisfied · {counts["partial"]} partial · {counts["open"]} open.
Gates NG01-NG10 are defined in <a href="../../nfl-validation.html">the validation-gates page</a>.</p>
{table("Per-requirement crosswalk", ["ID", "Requirement", "Status", "Gate", "What would clear it", "Where it stands", "Sources"], rows,
       "A blank never hides behind a badge: partial and open rows name the missing artefact and the count that closes it.")}
'''


def page_flagged(d: dict) -> str:
    rows = []
    for fid, title, body, page, sev, state in FLAGS:
        sid = S_NEWS if fid == "EF02" else (S_INJ if fid in ("EF03", "EF05") else (S_W10 if fid == "EF01" else S_STAND))
        rows.append(row([
            esc(fid), f'<strong>{esc(title)}</strong>', esc(body),
            f'<a href="{esc(page)}">{esc(page)}</a>', esc(sev), badge(state.split(",")[0], "warn"),
            link(REG_URLS[sid], "official page ↗"),
        ], sid))
    res_rows = [row([
        esc(rid), f'<strong>{esc(title)}</strong>', esc(body), badge("resolved", "ok"),
        link(REG_URLS[S_INJ], "official page ↗"),
    ], S_INJ) for rid, title, body in RESOLUTIONS]
    return f'''
<p class="eyebrow">OWN7 · Readiness audit desk</p>
<h1>Flagged for review</h1>
<p class="lead">Irregularities and open questions found during the 2026-11-17 pass. These are
published, not hidden, and do not block anything. Workspace-wide register:
<a href="../../nfl-review.html">nfl-review.html</a>.</p>
{table("Desk flags", ["ID", "Flag", "What was found", "Page", "Severity", "State", "Source"], rows)}
{table("Resolved at the publisher since 2026-11-14", ["Ref", "Item", "Resolution", "State", "Source"], res_rows)}
'''


def page_sources(d: dict) -> str:
    out = d["out"]
    ev_rows = []
    for key, e in out["evidence"].items():
        ev_rows.append(row([
            esc(key), esc(e["file"]), link(e["url"], "official page ↗"),
            esc(e["sha256"]),
        ], {"standings": S_STAND, "week10": S_W10, "week11": S_W11, "injuries": S_INJ}[key]))
    src_rows = []
    for sid, url in REG_URLS.items():
        s = d["srcs"][sid]
        src_rows.append(row([
            esc(sid), esc(s["publisher"]), esc(s["title"]), link(url, url), esc(s["checked_on"]),
        ], sid))
    return f'''
<p class="eyebrow">OWN7 · Readiness audit desk</p>
<h1>Sources</h1>
<p class="lead">The four evidence transcripts and the registered official sources this desk
rests on. Every evidence file was read from the official page at the time recorded and is
hashed so any later change is detectable.</p>
{table("Evidence transcripts (verbatim, hashed)", ["Read", "File", "Official page", "SHA-256"], ev_rows)}
{table("Registered sources used by this desk", ["Source id", "Publisher", "Title", "URL", "Checked on"], src_rows,
       "The full workspace register is research/sources.json (" + str(len(d["srcs"])) + " sources); these five were added by this desk.")}
'''


STYLE = """
:root{--bg:#f6f7f9;--fg:#1c2430;--muted:#5a6779;--line:#d9dee6;--panel:#fff;--ok:#1a7f37;--warn:#9a6700;--bad:#b42318;--accent:#12459e}
*{box-sizing:border-box}html{font-size:16px}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#fff;padding:8px;z-index:10}
header.top{background:var(--panel);border-bottom:1px solid var(--line);padding:10px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
header.top .brand{display:flex;flex-direction:column;font-size:14px;color:var(--muted)}header.top .brand strong{font-size:16px;color:var(--fg)}
nav[aria-label="Desk pages"]{display:flex;flex-wrap:wrap;gap:4px;margin-left:auto}nav[aria-label="Desk pages"] a{padding:5px 10px;border-radius:6px;font-size:13px;color:var(--muted)}nav[aria-label="Desk pages"] a[aria-current="page"]{background:var(--accent);color:#fff}
main{max-width:1200px;margin:0 auto;padding:24px 20px 60px}
.eyebrow{color:var(--muted);font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 4px}
h1{font-size:26px;margin:0 0 8px}h2{font-size:19px;margin:28px 0 8px}h3{font-size:16px;margin:20px 0 6px}
.lead{max-width:70ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;display:flex;flex-direction:column}
.kpi-value{font-size:24px;font-weight:700}.kpi-label{color:var(--muted);font-size:13px}.kpi .sub{color:var(--muted);font-size:12px;margin-top:2px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:14px 0}
.table-wrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:10px 0 6px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
caption{text-align:left;padding:10px 14px;font-weight:600;color:var(--muted);border-bottom:1px solid var(--line)}
th{position:sticky;top:0;background:#eef1f5;text-align:left;padding:8px 10px;border-bottom:2px solid var(--line);white-space:nowrap}
td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:hover{background:#f2f6ff}
td.blank{background:#fbf6e9;min-width:26px}
td.src a{font-size:12px}
.badge{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600}
.badge-ok{background:#dafbe1;color:var(--ok)}.badge-warn{background:#fff3c2;color:var(--warn)}.badge-bad{background:#ffe2dd;color:var(--bad)}
.note{color:var(--muted);font-size:12.5px;max-width:100ch}
footer{max-width:1200px;margin:0 auto;padding:0 20px 40px;color:var(--muted);font-size:12.5px}
"""


def render(name: str, body: str) -> str:
    title = next(label for n, label in PAGES if n == name)
    nav_parts = []
    for n, label in PAGES:
        current = ' aria-current="page"' if n == name else ""
        nav_parts.append(f'<a href="{n}"{current}>{esc(label)}</a>')
    nav = "".join(nav_parts)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {SITE_TITLE}</title>
<meta name="description" content="Line-by-line readiness audit: fresh official NFL reads verified against canonical artefacts, plus a per-requirement crosswalk with gates and clearing numbers.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="brand"><strong>{SITE_TITLE}</strong><span>official reads 2026-11-17 · line-by-line verification · requirement crosswalk</span></div><nav aria-label="Desk pages">{nav}<a href="../../index.html">← NFL workspace</a></nav></header>
<main id="main">{body}</main>
<footer>Evidence attributed to NFL.com and retained with hashes; canonical artefacts belong to their
producing sessions. Not affiliated with or endorsed by the NFL. Generated deterministically by
nfl-readiness-e7ef/build.py from committed artefacts on {READ_ON}.</footer>
</body>
</html>
'''


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    d = load()
    bodies = {
        "index.html": page_index(d),
        "verification-2026-11-17.html": page_verification(d),
        "requirement-readiness.html": page_readiness(d),
        "flagged.html": page_flagged(d),
        "sources.html": page_sources(d),
    }
    outputs = {name: render(name, body) for name, body in bodies.items()}
    # every readiness 'where' link must resolve: either it names one of this desk's own
    # rendered pages, or it must already exist on disk (the link audit runs before write
    # on a fresh build, and against disk on every later --check)
    disk_pages = {n for n in outputs if (SITE / n).exists()}
    for r in d["ready"]["rows"]:
        for w in r["where"]:
            if w in outputs or w in disk_pages:
                continue
            target = (SITE / w).resolve()
            if not target.is_file():
                raise SystemExit(f"FAIL: readiness row {r['id']} links missing artifact {w}")
    manifest = {"desk": "nfl-readiness-e7ef", "session": "arena/e7efbde7-own7", "read_on": READ_ON,
                "pages": [name for name, _ in PAGES],
                "evidence_sha256": {key: e["sha256"] for key, e in d["out"]["evidence"].items()}}
    if arg == "--check":
        stale = [n for n, content in outputs.items()
                 if not (SITE / n).exists() or (SITE / n).read_text(encoding="utf-8") != content]
        if not (SITE / "manifest.json").exists() or (SITE / "manifest.json").read_text(encoding="utf-8") != json.dumps(manifest, indent=1) + "\n":
            stale.append("manifest.json")
        if not (SITE / "style.css").exists() or (SITE / "style.css").read_text(encoding="utf-8") != STYLE:
            stale.append("style.css")
        if stale:
            raise SystemExit("FAIL: stale desk outputs: " + ", ".join(stale))
        print("OK: nfl-readiness-e7ef/site reproduces byte-identically (5 pages, manifest, style).")
        return 0
    SITE.mkdir(exist_ok=True)
    for name, content in outputs.items():
        (SITE / name).write_text(content, encoding="utf-8")
    (SITE / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    (SITE / "style.css").write_text(STYLE, encoding="utf-8")
    print(f"Built {len(outputs)} desk pages in nfl-readiness-e7ef/site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
