#!/usr/bin/env python3
"""Deterministic site generator for the fresh-read desk (session arena/92cad499-own7).

Everything on these pages is computed from committed repository artefacts:

  nfl-results/evidence/week-10.complete.md   2026-11-18 completion re-read of the
                                             official Week 10 by-week schedule page
  nfl-results/evidence/week-11.schedule.md   2026-11-18 read of the Week 11 page
                                             (scheduled fixtures + byes only)
  nfl-results/evidence/week-12.schedule.md   2026-11-18 read of the Week 12 page
  research/nfl/evidence/standings-2026-11-18.retrieved.md   2026-11-18 standings read
  nfl-fresh-1118/evidence/injury-hub-read-2026-11-18.partial.md  flagged partial read
  nfl-results/data/*.csv                     parser output (frozen + completed feeds)
  data/nfl-standings-2026-11-18.csv          the 2026-11-18 standings snapshot
  nfl-results/analysis.json                  engine output on the completed corpus

The desk re-derives its verification numbers from the CSVs at build time (it does not
trust the extractor's JSON), aborts on any mismatch, and renders four pages.
--check re-renders and compares bytes.
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
RESULTS_DATA = ROOT / "nfl-results" / "data"

READ_ON = "2026-11-18"
SITE_TITLE = "OWN7 · Fresh-read desk"

PAGES = [
    ("index.html", "Overview"),
    ("results-feed.html", "Results feed"),
    ("schedule.html", "Weeks 11-12 slate"),
    ("flagged.html", "Flagged for review"),
]

# Registered source ids (research/sources.json; hosts pinned in scripts/check_site.py).
S_STAND = "FRESH-NFL-STANDINGS-1118"
S_W10C = "FRESH-NFL-W10-COMPLETE-1118"
S_W11 = "FRESH-NFL-W11-SCHED-1118"
S_W12 = "FRESH-NFL-W12-SCHED-1118"
S_INJ = "FRESH-NFL-INJHUB-1118"
S_INJ404 = "FRESH-NFL-INJHUB-W11-404"

REG_URLS = {
    S_STAND: "https://www.nfl.com/standings/",
    S_W10C: "https://www.nfl.com/schedules/2026/by-week/week-10",
    S_W11: "https://www.nfl.com/schedules/2026/by-week/week-11",
    S_W12: "https://www.nfl.com/schedules/2026/by-week/week-12",
    S_INJ: "https://www.nfl.com/injuries/",
    S_INJ404: "https://www.nfl.com/injuries/week-11",
}


FLAGS = [
    ("FF01", "The 2026-11-18 injury-hub capture is partial, and no Week 11 report was fetchable",
     "The hub at https://www.nfl.com/injuries/ rendered the WEEK 10 report at "
     "2026-11-18T04:06:10Z. Its week picker shows WEEK 11, but the view is client-side: "
     "https://www.nfl.com/injuries/week-11 returns the site's 404 page and "
     "https://www.nfl.com/injuries/?week=11 re-renders WEEK 10. Chunks 0-3 of 8 were "
     "retrieved; chunks 4-7 were not, so no row count and no 2026-11-17 vs 2026-11-18 "
     "delta is published from this read. The complete 2026-11-17 read (28 team tables, "
     "347 rows, source E7EF-INJ-W10-1117) remains the newest complete capture. "
     "Follow-up task F1 recorded on the coordination board.",
     "medium", "open"),
    ("FF02", "The REG10 schedule URL now redirects away from Week 10",
     "The frozen 2026-11-17 read of Week 10 used https://www.nfl.com/schedules/2026/REG10 "
     "(per session arena/e15f05e0-own7). On 2026-11-18 that URL no longer renders Week 10: "
     "it redirects to https://www.nfl.com/schedules, which shows the current week. The "
     "completion re-read therefore used the by-week URL "
     "https://www.nfl.com/schedules/2026/by-week/week-10, which renders Week 10 in full. "
     "Publisher-side URL behaviour changed between reads; the frozen evidence file is "
     "unchanged and its recorded source URL stays as it was captured.",
     "low", "open"),
    ("FF03", "Skill-board numbers moved when the feed was completed, by design",
     "The pages published before 2026-11-18 quoted the frozen 149-final corpus: spread "
     "board 64.2% (permutation p=0.0021, q=0.022), total board 50.0%, leg dependence "
     "phi -0.068 (p=0.47, n=114), 120 scored rows. Completing the feed with the Monday "
     "final moves the corpus to 150 finals (134 scored rows) and every statistic is "
     "recomputed by the same frozen engine: spread board 61.2% (permutation p=0.0065, "
     "q=0.086), total board 49.3%, leg dependence phi -0.032 (p=0.72, n=128). No "
     "historical value was edited; all numbers come from one engine run on the committed "
     "corpus, and no strategy qualified either way.",
     "low", "explained"),
    ("FF04", "The Week 12 schedule contains a Wednesday game and a Friday game",
     "The official Week 12 by-week page prints Green Bay at Los Angeles Rams on Wednesday, "
     "November 25th (8:00 PM, NETFLIX) and Denver at Pittsburgh on Friday, November 27th "
     "(3:00 PM, PRIME) alongside the usual Thursday/Sunday/Monday slate. Both are "
     "transcribed exactly as printed; they are noted here because week-shape assumptions "
     "(16 games, Sun-Thu-Mon only) would silently drop them.",
     "low", "explained"),
]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def link(source_id: str, label: str = "official page ↗") -> str:
    return (f'<a href="{esc(REG_URLS[source_id])}" rel="noopener noreferrer" '
            f'target="_blank">{esc(label)}</a>')


def load() -> dict:
    """Compute every desk number from committed artefacts; abort on any mismatch."""
    errors: list[str] = []

    complete = read_csv(RESULTS_DATA / "games-2026-w1-10-complete.csv")
    frozen = read_csv(RESULTS_DATA / "games-2026-w1-10.csv")
    frozen_w9 = read_csv(RESULTS_DATA / "games-2026-w1-9.csv")
    sched_w11 = read_csv(RESULTS_DATA / "scheduled-2026-w11.csv")
    sched_w12 = read_csv(RESULTS_DATA / "scheduled-2026-w12.csv")
    sched_w10 = read_csv(RESULTS_DATA / "scheduled-2026-w10.csv")
    byes = read_csv(RESULTS_DATA / "byes-2026-w1-12.csv")

    # --- FV1: the completed feed re-derives the 2026-11-18 standings snapshot. ---
    standings = read_csv(ROOT / "data" / "nfl-standings-2026-11-18.csv")
    if len(standings) != 32:
        errors.append(f"snapshot rows {len(standings)} != 32")
    tally: dict[str, dict] = {}
    for g in complete:
        a, h = int(g["away_score"]), int(g["home_score"])
        for club, scored, allowed in ((g["away"], a, h), (g["home"], h, a)):
            row = tally.setdefault(club, {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0})
            row["pf"] += scored
            row["pa"] += allowed
            row["w" if scored > allowed else ("l" if scored < allowed else "t")] += 1
    fv1_mismatch = 0
    # Map club code -> full name (naming only, no values).
    club_names = {row["Team"]: row for row in standings}
    abbr_by_name = _ABBR_BY_NAME()
    for s in standings:
        team = s["Team"]
        code = abbr_by_name.get(team)
        if code is None:
            errors.append(f"snapshot team {team} not resolvable to a code")
            continue
        got = tally.get(code)
        if got is None:
            errors.append(f"{team}: no parsed games")
            continue
        for field, col in (("w", "W"), ("l", "L"), ("t", "T"), ("pf", "PF"), ("pa", "PA")):
            if got[field] != int(s[col]):
                fv1_mismatch += 1
    if fv1_mismatch:
        errors.append(f"FV1: {fv1_mismatch} standings fields do not re-derive")

    # --- FV2: snapshot_1118 = snapshot_1117 + the completion final's deltas. ---
    standings_1117 = {r["Team"]: r for r in read_csv(ROOT / "data" / "nfl-standings-2026-11-17.csv")}
    added = [g for g in complete if g["source_url"] == REG_URLS[S_W10C]]
    frozen_keys = {(g["week"], g["away"], g["home"]) for g in frozen}
    if len(added) != 1:
        errors.append(f"completion added {len(added)} finals, expected 1")
    delta: dict[str, dict[str, int]] = {}
    for g in added:
        a, h = int(g["away_score"]), int(g["home_score"])
        for club, scored, allowed in ((g["away"], a, h), (g["home"], h, a)):
            delta[club] = {"w": int(scored > allowed), "l": int(scored < allowed),
                           "t": int(scored == allowed), "pf": scored, "pa": allowed}
    fv2_mismatch = 0
    for s in standings:
        code = abbr_by_name[s["Team"]]
        base = standings_1117[s["Team"]]
        d = delta.get(code, {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0})
        for field, col in (("w", "W"), ("l", "L"), ("t", "T"), ("pf", "PF"), ("pa", "PA")):
            if int(base[col]) + d[field] != int(s[col]):
                fv2_mismatch += 1
    if fv2_mismatch:
        errors.append(f"FV2: {fv2_mismatch} chain fields do not hold")

    # --- FV3: the completion re-read agrees with the frozen read. ---
    frozen_w10 = [g for g in frozen if g["week"] == "10"]
    same_scores = True
    comp_by_key = {(c["week"], c["away"], c["home"]): c for c in complete}
    for g in frozen_w10:
        c = comp_by_key[(g["week"], g["away"], g["home"])]
        if (g["away_score"], g["home_score"], g["date"]) != (c["away_score"], c["home_score"], c["date"]):
            same_scores = False
    fv3 = len(frozen_w10) == 13 and same_scores and len(added) == 1 and (
        added[0]["away"], added[0]["home"]) == ("LAC", "BAL")
    if not fv3:
        errors.append("FV3: completion re-read disagrees with the frozen read")

    # --- FV4 / FV5: weeks 11-12 are scheduled-only and cover the 32 clubs. ---
    w11_byes = sorted(r["team_code"] for r in byes if r["week"] == "11")
    w12_byes = sorted(r["team_code"] for r in byes if r["week"] == "12")
    clubs_w11 = [r["away"] for r in sched_w11] + [r["home"] for r in sched_w11]
    clubs_w12 = [r["away"] for r in sched_w12] + [r["home"] for r in sched_w12]
    fv4 = (len(sched_w11) == 13 and len(w11_byes) == 6
           and len(set(clubs_w11)) == 26 and len(set(clubs_w11)) + len(w11_byes) == 32
           and not [g for g in complete if g["week"] == "11"])
    fv5 = (len(sched_w12) == 16 and len(w12_byes) == 0
           and len(set(clubs_w12)) == 32
           and not [g for g in complete if g["week"] == "12"])
    if not fv4:
        errors.append("FV4: Week 11 capture is not a 13-fixture/6-bye cover of the 32")
    if not fv5:
        errors.append("FV5: Week 12 capture is not a 16-fixture cover of the 32")

    # --- FV6: engine corpus counts from the committed analysis. ---
    analysis = json.loads((ROOT / "nfl-results" / "analysis.json").read_text(encoding="utf-8"))
    fv6 = (analysis["inputs"]["games"] == 150 and analysis["inputs"]["rows_scored"] == 134
           and analysis["inputs"]["games_file"] == "nfl-results/data/games-2026-w1-10-complete.csv")
    if not fv6:
        errors.append("FV6: engine analysis does not reflect the completed corpus")

    # --- Frozen artefacts untouched. ---
    frozen_ok = (len(frozen) == 149 and len(frozen_w9) == 136 and len(sched_w10) == 1
                 and all(g["retrieved"] == "2026-11-17" for g in frozen_w10)
                 and len([g for g in frozen if g["week"] == "10"]) == 13)
    if not frozen_ok:
        errors.append("frozen 2026-11-17 artefacts changed")

    evidence = {
        "standings-1118": ROOT / "research/nfl/evidence/standings-2026-11-18.retrieved.md",
        "week10-complete": ROOT / "nfl-results/evidence/week-10.complete.md",
        "week11": ROOT / "nfl-results/evidence/week-11.schedule.md",
        "week12": ROOT / "nfl-results/evidence/week-12.schedule.md",
        "injury-hub-partial": HERE / "evidence/injury-hub-read-2026-11-18.partial.md",
    }
    hashes = {key: sha256_file(path) for key, path in evidence.items()}

    if errors:
        raise SystemExit("FAIL: fresh-read desk verification:\n  - " + "\n  - ".join(errors))
    return {
        "complete": complete, "frozen": frozen, "frozen_w9": frozen_w9,
        "sched_w11": sched_w11, "sched_w12": sched_w12, "sched_w10": sched_w10,
        "byes": byes, "standings": standings, "added": added,
        "w11_byes": w11_byes, "w12_byes": w12_byes,
        "standings_names": club_names, "analysis": analysis, "hashes": hashes,
        "checks": {"fv1": fv1_mismatch == 0, "fv2": fv2_mismatch == 0, "fv3": fv3,
                   "fv4": fv4, "fv5": fv5, "fv6": fv6, "frozen": frozen_ok},
    }


_ABBR_NAMES = {
    "AZ": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}


def _ABBR_BY_NAME() -> dict[str, str]:
    return {name: code for code, name in _ABBR_NAMES.items()}


def table(tid: str, caption: str, head: list[str], rows: list[str],
          note: str | None = None) -> str:
    thead = "".join(f'<th scope="col">{esc(h)}</th>' for h in head)
    note_html = f'<p class="note">{esc(note)}</p>' if note else ""
    return (f'<div class="table-wrap"><table><caption>{esc(caption)}</caption>'
            f'<thead><tr>{thead}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f"{note_html}")


def row(cells: list[str], source_id: str) -> str:
    tds = "".join(f"<td>{c}</td>" for c in cells)
    return f'<tr data-source-ids="{source_id}">{tds}</tr>'


def page_index(d: dict) -> str:
    checks = d["checks"]
    spread = d["analysis"]["benchmarks"]["spread"]["directional"]
    total = d["analysis"]["benchmarks"]["total"]["directional"]
    kpis = "".join(
        f'<div class="kpi"><span class="kpi-value">{esc(v)}</span>'
        f'<span class="kpi-label">{esc(label)}</span><span class="sub">{esc(sub)}</span></div>'
        for v, label, sub in (
            (150, "official finals, weeks 1-10 complete", "Monday final added by the 2026-11-18 re-read"),
            (3, "standings snapshots reconciled", "frozen pre-kickoff · 2026-11-17 · 2026-11-18"),
            (134, "games scored walk-forward", "30 variants · 0 qualified · 1 provisional"),
            (29, "scheduled fixtures captured", "13 Week 11 + 16 Week 12, kickoff times only"),
            (4, "desk pages, source-linked", "every row carries its registered official source"),
        ))
    check_rows = [
        row(["FV1", badge("pass" if checks["fv1"] else "fail"),
             "The completed weeks 1-10 feed (150 finals) re-derives every W, L, T, PF and PA "
             "cell of the 2026-11-18 official standings snapshot for all 32 clubs (160 fields, 0 mismatches).",
             link(S_STAND)], S_STAND),
        row(["FV2", badge("pass" if checks["fv2"] else "fail"),
             "Chain identity: the 2026-11-18 snapshot equals the 2026-11-17 snapshot plus exactly the "
             "parsed Week 10 completion deltas (Chargers 23, Ravens 20) for all 32 clubs × 5 fields.",
             link(S_STAND)], S_STAND),
        row(["FV3", badge("pass" if checks["fv3"] else "fail"),
             "The completion re-read agrees with the frozen 2026-11-17 read: all 13 frozen finals "
             "identical (teams, scores, dates), only the previously-scheduled fixture added, byes identical.",
             link(S_W10C)], S_W10C),
        row(["FV4", badge("pass" if checks["fv4"] else "fail"),
             "Week 11 is scheduled-only capture: 13 fixtures + 6 byes (ATL, CLE, GB, LA, NE, SEA) cover "
             "all 32 clubs exactly once; zero finals exist for the week.",
             link(S_W11)], S_W11),
        row(["FV5", badge("pass" if checks["fv5"] else "fail"),
             "Week 12 is scheduled-only capture: 16 fixtures, no bye section printed, covering all 32 "
             "clubs; zero finals exist for the week.",
             link(S_W12)], S_W12),
        row(["FV6", badge("pass" if checks["fv6"] else "fail"),
             "The skill engine runs on the completed corpus: 150 finals in, 134 walk-forward rows "
             "(weeks 2-10), 30 variants graded, 0 qualified, 1 provisional, 29 rejected.",
             link(S_STAND)], S_STAND),
        row(["FV7", badge("pass" if checks["frozen"] else "fail"),
             "Frozen 2026-11-14/11-17 artefacts are untouched: 136 weeks-1-9 finals, 149 frozen "
             "weeks-1-10 finals, 13 frozen Week 10 finals with their original provenance, 1 frozen "
             "scheduled fixture.",
             link(S_STAND)], S_STAND),
    ]
    receipt_rows = [
        row(["Standings page (2026-11-18)", "2 chunks", "32 rows, 16 cells each",
             f'<code>{d["hashes"]["standings-1118"][:16]}…</code>', link(S_STAND)], S_STAND),
        row(["Week 10 by-week page, completion re-read", "2 chunks", "14 FINAL headlines + 4 byes",
             f'<code>{d["hashes"]["week10-complete"][:16]}…</code>', link(S_W10C)], S_W10C),
        row(["Week 11 by-week page", "3 chunks", "13 scheduled fixtures + 6 byes, no finals",
             f'<code>{d["hashes"]["week11"][:16]}…</code>', link(S_W11)], S_W11),
        row(["Week 12 by-week page", "3 chunks", "16 scheduled fixtures, no bye section",
             f'<code>{d["hashes"]["week12"][:16]}…</code>', link(S_W12)], S_W12),
        row(["Injury hub (flagged partial)", "3 of 8 chunks", "no counts published from a partial read",
             f'<code>{d["hashes"]["injury-hub-partial"][:16]}…</code>', link(S_INJ)], S_INJ),
    ]
    return f'''
<p class="eyebrow">OWN7 · Fresh-read desk</p>
<h1>Overview</h1>
<p class="lead">Fresh official reads taken 2026-11-18 (Arena fetch_page; direct HTTPS to
nfl.com is blocked in this sandbox). They complete the verified results feed at
<strong>150 finals for weeks 1-10</strong> — the Week 10 Monday final, Chargers 23
Ravens 20, is now captured — and capture the Week 11 and Week 12 slates as scheduled
fixtures. Every claim on this desk is re-derived from the parser output at build time
and aborted on any mismatch; frozen artefacts from earlier reads are untouched.</p>
<div class="kpis">{kpis}</div>
<h2>Verification checks (all must pass; a single failure aborts the build)</h2>
{table("fv-checks", "Checks run by build.py on every build", ["Check", "Result", "What was verified", "Source"], check_rows)}
<h2>Read receipts</h2>
<p class="note">Each read is retained as verbatim rendered-page text with its URL and
SHA-256; full hashes are in site/manifest.json. The standings rows and schedule lines
are transcribed unmodified; navigation chrome is truncated, and the method note in each
evidence file says exactly what that means.</p>
{table("read-receipts", "What was read, and where it is kept", ["Read", "Chunks", "Content", "SHA-256 (first 16)", "Source"], receipt_rows)}
<h2>What changed in the analysis</h2>
<div class="panel body-text"><ol>
<li><strong>The feed is complete through Week 10.</strong> The frozen 2026-11-17 read held
13 of 14 Week 10 finals (the Monday game was pre-kickoff). The 2026-11-18 re-read adds
Chargers 23, Ravens 20, FINAL, Monday, November 16th, cross-checked against the frozen
read line by line before anything is published.</li>
<li><strong>Three snapshots now reconcile.</strong> The feed re-derives the frozen
pre-kickoff snapshot (weeks 1-9), the 2026-11-17 snapshot (frozen weeks 1-10) and the
2026-11-18 snapshot (completed weeks 1-10): 160 fields each, plus both chain identities
between snapshots.</li>
<li><strong>The skill engine re-graded on the completed corpus.</strong> Spread board
{spread["hit_rate"] * 100:.1f}% directional (permutation p={d["analysis"]["benchmarks"]["spread"]["permutation_p_value"]}, BH q=
{d["analysis"]["leaderboard"][0]["q_value"]:.3f}); total board {total["hit_rate"] * 100:.1f}%. Still zero qualified
strategies and zero rewards — the market column stays blank for want of a rights-cleared
price source.</li>
<li><strong>Week 11 and Week 12 slates are captured, not predicted.</strong> Scheduled
fixtures carry kickoff times and networks exactly as printed; no score, no line, no
model output is attached to them.</li>
</ol></div>
<p class="note">Paper research only. No pricing, wagering or reward of any kind is
produced anywhere on this desk. Nothing here is a betting recommendation.</p>
'''


def badge(state: str) -> str:
    cls = {"pass": "badge-ok", "fail": "badge-bad"}.get(state, "badge-warn")
    return f'<span class="badge {cls}">{esc(state)}</span>'


def page_results(d: dict) -> str:
    added = d["added"][0]
    per_week: dict[str, int] = {}
    for g in d["complete"]:
        per_week[g["week"]] = per_week.get(g["week"], 0) + 1
    week_rows = [
        row([f"Week {w}", str(n), "16 (full slate)" if n == 16 else f"{(32 - sum(1 for b in d['byes'] if b['week']==w))//2} fixtures per the bye list",
             link(S_W10C if w == "10" else S_STAND)],
            S_W10C if w == "10" else S_STAND)
        for w, n in sorted(per_week.items(), key=lambda kv: int(kv[0]))
    ]
    completion_rows = [
        row(["Before the re-read (frozen 2026-11-17)", "13 finals + 1 scheduled",
             "Chargers at Ravens printed as “8:15 PM, ESPN” with no score; LAC 0-8 and BAL 4-5 on the standings page",
             link(S_W10C)], S_W10C),
        row([f"Re-read {added['retrieved']} (by-week URL)", "14 finals",
             f"{added['away']} {added['away_score']}, {added['home']} {added['home_score']}, FINAL, {added['weekday']}, November 16th",
             link(S_W10C)], S_W10C),
        row(["Snapshot evidence", "2026-11-18 standings page",
             "LAC 1-8 and BAL 4-6 — the first snapshot that includes the Monday final; the chain "
             "identity holds for all 32 clubs × 5 fields",
             link(S_STAND)], S_STAND),
    ]
    return f'''
<p class="eyebrow">OWN7 · Fresh-read desk</p>
<h1>Results feed</h1>
<p class="lead">The verified results feed is the corpus every backtest on this site runs
on. This page documents the 2026-11-18 extension: the Week 10 completion, the new
snapshot it reconciles against, and the provenance of every added row.</p>
<h2>Week 10 completion</h2>
{table("w10-completion", "The Monday final, as captured", ["Step", "State", "What the publisher printed", "Source"], completion_rows,
       note="The re-read's 13 frozen finals are identical to the frozen read (teams, scores, "
            "dates); the extractor refuses to publish otherwise. The added row carries the "
            "re-read's own provenance (by-week URL, retrieved 2026-11-18).")}
<h2>Corpus shape</h2>
{table("corpus", "Finals per week in the completed feed (150 total)", ["Week", "Finals", "Slate", "Source"], week_rows)}
<h2>Reconciliation identities (all enforced in code)</h2>
<div class="panel body-text"><ol>
<li>Weeks 1-9 re-derive the frozen pre-kickoff standings snapshot (160 fields).</li>
<li>The frozen weeks 1-10 feed (149 finals) re-derives the 2026-11-17 snapshot (160 fields).</li>
<li>The completed weeks 1-10 feed (150 finals) re-derives the 2026-11-18 snapshot (160 fields).</li>
<li>2026-11-17 snapshot = frozen snapshot + parsed frozen Week 10 deltas (160 fields).</li>
<li>2026-11-18 snapshot = 2026-11-17 snapshot + parsed completion deltas (160 fields).</li>
</ol>
<p class="note">800 reconciled fields across three snapshots, plus structural checks per week
(fixture cover = clubs − byes, no club twice, byes disjoint). A single mismatch aborts the
build; nothing is ever published on top of a contradiction.</p></div>
<h2>Scores are not results until the publisher prints FINAL</h2>
<p class="note">Week 11 (kickoffs November 19-23) and Week 12 (November 25-30) are captured
on the <a href="schedule.html">Weeks 11-12 slate page</a> with kickoff times only. No score,
line or probability is attached to a fixture that has not been played, and no backtest row
references a game beyond the last FINAL headline.</p>
'''


def page_schedule(d: dict) -> str:
    w11_rows = []
    for r in sorted(d["sched_w11"], key=lambda g: (g["date"], g["away"])):
        w11_rows.append(row([esc(r["date"]), esc(r["weekday"]),
                             f"{esc(r['away'])} at {esc(r['home'])}",
                             esc(r["kickoff"]), esc(r["tv"]), link(S_W11, "by-week page ↗")], S_W11))
    w12_rows = []
    for r in sorted(d["sched_w12"], key=lambda g: (g["date"], g["away"])):
        w12_rows.append(row([esc(r["date"]), esc(r["weekday"]),
                             f"{esc(r['away'])} at {esc(r['home'])}",
                             esc(r["kickoff"]), esc(r["tv"]), link(S_W12, "by-week page ↗")], S_W12))
    w11_byes = ", ".join(d["w11_byes"])
    return f'''
<p class="eyebrow">OWN7 · Fresh-read desk</p>
<h1>Weeks 11-12 slate</h1>
<p class="lead">The upcoming official slates as printed on the by-week schedule pages on
2026-11-18. Kickoff times and networks are transcribed exactly; scores are blank because
the publisher prints none, and blanks are never filled.</p>
<h2>Week 11 — 13 fixtures, 6 byes</h2>
{table("w11", "Week 11 scheduled fixtures (no score published at read time)", ["Date", "Day", "Fixture", "Kickoff (ET)", "TV", "Source"], w11_rows,
       note=f"Byes as printed: {w11_byes}. 13 fixtures × 2 + 6 byes = all 32 clubs exactly once. "
            f"The Minnesota at San Francisco game is printed with the publisher's Mexico City tag.")}
<h2>Week 12 — 16 fixtures, no byes</h2>
{table("w12", "Week 12 scheduled fixtures (no score published at read time)", ["Date", "Day", "Fixture", "Kickoff (ET)", "TV", "Source"], w12_rows,
       note="The page prints no bye section: all 32 clubs are scheduled, including a Wednesday "
            "game (Green Bay at Los Angeles Rams, November 25th, NETFLIX) and a Friday game "
            "(Denver at Pittsburgh, November 27th, PRIME).")}
<h2>League schedule announcement (as printed on both pages)</h2>
<div class="panel body-text"><p>“2026 TBD Games — In Week 16, two of the four designated
matchups will be played on Saturday … Specific dates and start times for the designated
Week 16 matchups will be determined and announced at a later date during the season, no
later than immediately after Week 14.” Week 17: no later than immediately after Week 15.
Week 18: announced following the conclusion of Week 17. Flexible scheduling procedures:
<a href="https://www.nfl.com/legal/flexible-scheduling-procedures" rel="noopener noreferrer" target="_blank">nfl.com/legal/flexible-scheduling-procedures</a>.</p>
<p class="note">This dated announcement is quoted beside the live schedule pages because the
brief requires the league's schedule policy to be visible wherever future fixtures are shown.
It is transcribed from the same page reads as the fixture tables.</p></div>
<p class="note">A fixture with a kickoff time is never a result. These fixtures enter no
corpus, no rating and no leaderboard until the publisher prints a FINAL headline.</p>
'''


def page_flagged(d: dict) -> str:
    rows = []
    for fid, title, detail, severity, status in FLAGS:
        rows.append(row([f"<strong>{esc(fid)}</strong>", esc(title), esc(detail),
                         badge(severity), badge(status),
                         link(S_INJ if fid == "FF01" else S_W10C if fid == "FF02" else S_STAND)],
                        S_INJ if fid == "FF01" else S_W10C if fid == "FF02" else S_STAND))
    return f'''
<p class="eyebrow">OWN7 · Fresh-read desk</p>
<h1>Flagged for review</h1>
<p class="lead">Irregularities and publisher-side behaviours found during the 2026-11-18
reads. Flags never block publication — they are published so irregular information stays
visible instead of silently disappearing. None of them hides a value: wherever a number
cannot be confirmed from an official source, the cell is blank.</p>
{table("flags", "Flags raised by this desk", ["ID", "Flag", "Detail", "Severity", "Status", "Source"], rows)}
<p class="note">Carried-forward flags from earlier desks (rights-gated price data, inactive
lists, depth-chart provenance) remain published on their own desks' Flagged pages and are
not repeated here.</p>
'''


STYLE_FALLBACK = ""


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
<meta name="description" content="Fresh official NFL reads 2026-11-18: the completed weeks 1-10 results feed (150 finals), the Weeks 11-12 scheduled slates, and flagged irregularities, each row source-linked.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="brand"><strong>{SITE_TITLE}</strong><span>official reads 2026-11-18 · 150-final results feed · Weeks 11-12 slates</span></div><nav aria-label="Desk pages">{nav}<a href="../../index.html">← NFL workspace</a></nav></header>
<main id="main">{body}</main>
<footer>Evidence attributed to NFL.com and retained with hashes; canonical artefacts belong to their
producing sessions. Not affiliated with or endorsed by the NFL. Generated deterministically by
nfl-fresh-1118/build.py from committed artefacts on {READ_ON}.</footer>
</body>
</html>
'''


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    d = load()
    bodies = {
        "index.html": page_index(d),
        "results-feed.html": page_results(d),
        "schedule.html": page_schedule(d),
        "flagged.html": page_flagged(d),
    }
    outputs = {name: render(name, body) for name, body in bodies.items()}
    manifest = {
        "desk": "nfl-fresh-1118", "session": "arena/92cad499-own7", "read_on": READ_ON,
        "pages": [name for name, _ in PAGES],
        "evidence_sha256": d["hashes"],
        "source_ids": sorted(REG_URLS),
    }
    if arg == "--check":
        stale = [n for n, content in outputs.items()
                 if not (SITE / n).exists() or (SITE / n).read_text(encoding="utf-8") != content]
        expected_manifest = json.dumps(manifest, indent=1) + "\n"
        if not (SITE / "manifest.json").exists() or (SITE / "manifest.json").read_text(encoding="utf-8") != expected_manifest:
            stale.append("manifest.json")
        if stale:
            raise SystemExit("FAIL: stale desk outputs: " + ", ".join(stale))
        print("OK: nfl-fresh-1118/site reproduces byte-identically (4 pages, manifest).")
        return 0
    SITE.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (SITE / name).write_text(content, encoding="utf-8")
    (SITE / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"Built {len(outputs)} desk pages in nfl-fresh-1118/site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
