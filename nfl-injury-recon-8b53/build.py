#!/usr/bin/env python3
"""Reconcile the official Patriots-Lions injury block against two desk CSVs.

Inputs (read-only):
  evidence/official-REG10-SUN-NE-at-DET-2026-11-18.md   verbatim official table rows
  nfl-availability-28ef/data/injuries-week10-2026.csv   desk A (checked_on 2026-11-13)
  nfl-assurance-9580ac3f/data/injuries.csv               desk B (no per-read clock time)

Outputs (written by default, compared byte-for-byte with --check):
  data/summary.json, site/index.html, site/manifest.json
No row-level CSV is written: the repo's rights gate keeps row-level NFL data out of new public CSV files.

No value is inferred: a field either matches the official text exactly or is reported as a difference.
"""
import csv
import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
EVIDENCE = ROOT / "evidence" / "official-REG10-SUN-NE-at-DET-2026-11-18.md"
DESK_A = REPO / "nfl-availability-28ef" / "data" / "injuries-week10-2026.csv"
DESK_B = REPO / "nfl-assurance-9580ac3f" / "data" / "injuries.csv"
OFFICIAL_URL = "https://www.nfl.com/injuries/league/2026/REG10"
TEAMS = {"Patriots": "NE", "Lions": "DET"}
FIELDS = ("position", "injury", "practice", "game")

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def parse_official():
    rows, team = [], None
    for line in EVIDENCE.read_text(encoding="utf-8").splitlines():
        if line.strip() in TEAMS:
            team = TEAMS[line.strip()]
            continue
        if not line.startswith("| ["):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        name_m = LINK.match(cells[0])
        name, player_url = name_m.group(1), name_m.group(2)
        rows.append({
            "club": team, "player": name, "player_url": player_url,
            "position": cells[1], "injury": cells[2],
            "practice": cells[3], "game": cells[4],
        })
    return rows


def load_desk_a():
    out = {}
    with DESK_A.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["club_abbr"] in ("NE", "DET"):
                out.setdefault((r["club_abbr"], r["player"]), []).append({
                    "position": r["position"], "injury": r["injury"],
                    "practice": r["practice_status"], "game": r["game_status"],
                    "checked_on": r["checked_on"],
                })
    return out


def load_desk_b():
    out = {}
    with DESK_B.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["team"] in ("NE", "DET"):
                out.setdefault((r["team"], r["player"]), []).append({
                    "position": r["position"], "injury": r["injury"],
                    "practice": r["practice_status"], "game": r["game_status"],
                })
    return out


def compare(official, desk):
    """Return (verdict, differing_fields) for one official row against one desk."""
    hits = desk.get((official["club"], official["player"]), [])
    if not hits:
        return "missing", []
    if len(hits) > 1:
        return "duplicate", []
    d = hits[0]
    diffs = [f for f in FIELDS if official[f] != d[f]]
    return ("agree" if not diffs else "differs"), diffs


def build_rows():
    official = parse_official()
    a, b = load_desk_a(), load_desk_b()
    out = []
    for o in official:
        va, fa = compare(o, a)
        vb, fb = compare(o, b)
        ra = a.get((o["club"], o["player"]), [{}])[0]
        rb = b.get((o["club"], o["player"]), [{}])[0]
        out.append({
            **o,
            "a_verdict": va, "a_diff_fields": ";".join(fa),
            "a_practice": ra.get("practice", ""), "a_game": ra.get("game", ""), "a_injury": ra.get("injury", ""),
            "a_checked_on": ra.get("checked_on", ""),
            "b_verdict": vb, "b_diff_fields": ";".join(fb),
            "b_practice": rb.get("practice", ""), "b_game": rb.get("game", ""), "b_injury": rb.get("injury", ""),
        })
    return out


def summary(rows):
    def count(key, val):
        return sum(1 for r in rows if r[key] == val)

    def names(pred):
        return [r["player"] for r in rows if pred(r)]

    return {
        "official_rows": len(rows),
        "official_rows_by_club": {c: sum(1 for r in rows if r["club"] == c) for c in ("NE", "DET")},
        "official_source_url": OFFICIAL_URL,
        "official_evidence_sha256": hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(),
        "desk_a": {
            "file": str(DESK_A.relative_to(REPO)),
            "rows_agree": count("a_verdict", "agree"),
            "rows_differ": count("a_verdict", "differs"),
            "rows_missing": count("a_verdict", "missing"),
            "injury_blank_where_official_lists_one": names(
                lambda r: bool(r["injury"]) and r["a_injury"] == ""),
            "game_blank_where_official_lists_one": names(
                lambda r: bool(r["game"]) and r["a_game"] == ""),
        },
        "desk_b": {
            "file": str(DESK_B.relative_to(REPO)),
            "rows_agree": count("b_verdict", "agree"),
            "rows_differ": count("b_verdict", "differs"),
            "rows_missing": count("b_verdict", "missing"),
            "injury_blank_where_official_lists_one": names(
                lambda r: bool(r["injury"]) and r["b_injury"] == ""),
            "game_blank_where_official_lists_one": names(
                lambda r: bool(r["game"]) and r["b_game"] == ""),
        },
        "desk_b_out_blank_on_official": names(
            lambda r: r["game"] == "Out" and r["b_game"] == ""),
    }


def esc(s):
    return html.escape(s if s else "", quote=True)


def cell(desk_val, official_val):
    if desk_val == "" and official_val == "":
        return '<span class="none">(none)</span>'
    cls = "same" if desk_val == official_val else "diff"
    shown = esc(desk_val) if desk_val else '<span class="blank">blank</span>'
    return f'<span class="{cls}">{shown}</span>'


def blank_or(v):
    return esc(v) if v else '<span class="blank">blank</span>'


def verdict_text(verdict, diff_fields):
    if verdict == "agree":
        return "agrees"
    if verdict == "differs":
        return "differs: " + esc(diff_fields.replace(";", ", "))
    return esc(verdict)


def render_html(rows, summ):
    body = []
    for r in rows:
        body.append(
            '<tr data-source-ids="X28-NFL-INJ-W10">'
            f"<td>{esc(r['club'])}</td>"
            f'<td><a href="{esc(r["player_url"])}" rel="noopener">{esc(r["player"])}</a></td>'
            f"<td>{esc(r['position'])}</td>"
            f"<td>{blank_or(r['injury'])}</td>"
            f"<td>{esc(r['practice'])}</td>"
            f"<td>{blank_or(r['game'])}</td>"
            f"<td>{cell(r['a_practice'], r['practice'])} / {cell(r['a_game'], r['game'])}"
            f"<br><small>{verdict_text(r['a_verdict'], r['a_diff_fields'])}</small></td>"
            f"<td>{cell(r['b_practice'], r['practice'])} / {cell(r['b_game'], r['game'])}"
            f"<br><small>{verdict_text(r['b_verdict'], r['b_diff_fields'])}</small></td>"
            f'<td><a href="{OFFICIAL_URL}" rel="noopener">official report</a></td>'
            "</tr>"
        )
    b = summ["desk_b"]
    a = summ["desk_a"]
    flags = [
        ("R-F1", f"Kerby Joseph's practice status on the official page is \u201cDid Not Participate In Practice\u201d. "
                 f"Desk A reads \u201cFull Participation in Practice\u201d (checked_on 2026-11-13). Desk B reads "
                 f"\u201cLimited Participation in Practice\u201d. Neither desk stores a clock time per read, so the "
                 f"cause (different capture or transcription) cannot be settled from the files."),
        ("R-F2", f"Desk B leaves the game-status cell blank for {len(summ['desk_b_out_blank_on_official'])} rows the "
                 f"official page lists \u201cOut\u201d: {', '.join(summ['desk_b_out_blank_on_official'])}. "
                 f"Desk B has {len(b['game_blank_where_official_lists_one'])} blank game-status cells where the official "
                 f"page lists a status, and {len(b['injury_blank_where_official_lists_one'])} blank injury cells "
                 f"where the official page lists an injury."),
        ("R-F3", f"Desk A (checked_on 2026-11-13) leaves the game status and injury blank for "
                 f"{', '.join(a['game_blank_where_official_lists_one'])}. The official page lists a game status for both."),
        ("R-F4", "The official page title reads \u201cWeek 11 of the 2026 Season\u201d while its section heading reads "
                 "\u201cInjuries - WEEK 10\u201d. The rows in this block belong to the Sunday, November 15 game."),
        ("R-F5", "Practice-status differences from the official page are listed row by row above. Without "
                 "per-read clock times, none can be called an error rather than a later capture; the fix is "
                 "a timestamped series (see the desk README)."),
    ]
    flag_html = "".join(f"<li><strong>{i}</strong> {esc(t)}</li>" for i, t in flags)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Patriots–Lions injury block: official vs desks · OWN7 reconciliation</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1d2330;background:#f7f8fa;line-height:1.5}}
main{{max-width:1200px;margin:0 auto;padding:24px 16px}}
h1{{font-size:1.6rem;margin:.2rem 0}} h2{{font-size:1.2rem;margin-top:1.8rem}}
.eyebrow{{color:#5b6475;font-size:.85rem;margin:0}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}}
.card{{background:#fff;border:1px solid #dde1e8;border-radius:8px;padding:12px}}
.card b{{font-size:1.4rem;display:block}}
.table-card{{background:#fff;border:1px solid #dde1e8;border-radius:8px;overflow:auto;max-width:100%}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #eef0f4;vertical-align:top}}
th{{background:#f0f3f8;position:sticky;top:0}}
.same{{color:#126b3a}} .diff{{color:#a11d1d;font-weight:600}} .blank{{color:#4f5868;font-style:italic}} .none{{color:#4f5868}}
a{{color:#1f5fbf}} small{{color:#5b6475}}
.note{{background:#fff8e6;border:1px solid #f0d58a;border-radius:8px;padding:12px}}
</style></head>
<body><main id="main">
<p class="eyebrow">Official source read 2026-11-18 · Sunday, November 15 block · informational only · no wagers</p>
<h1>Patriots–Lions injury block: official report vs two desks</h1>
<p>Every official row is compared field by field (position, injury, practice status, game status) with the
two desk CSVs. Green = matches the official text; red = differs; <em>blank</em> = empty in the desk file.
Nothing is filled in.</p>
<div class="cards">
  <div class="card"><b>{summ['official_rows']}</b>official rows (NE {summ['official_rows_by_club']['NE']}, DET {summ['official_rows_by_club']['DET']})</div>
  <div class="card"><b>{summ['desk_a']['rows_agree']}</b>rows agreeing, desk A (availability, 2026-11-13)</div>
  <div class="card"><b>{summ['desk_a']['rows_differ']}</b>rows differing, desk A</div>
  <div class="card"><b>{summ['desk_b']['rows_agree']}</b>rows agreeing, desk B (assurance, no clock time)</div>
  <div class="card"><b>{summ['desk_b']['rows_differ']}</b>rows differing, desk B</div>
</div>
<div class="table-card" role="region" tabindex="0" aria-label="Official rows compared with two desks">
<table>
<thead><tr><th>Club</th><th>Player</th><th>Pos</th><th>Injury (official)</th><th>Practice (official)</th><th>Game status (official)</th><th>Desk A: practice / game</th><th>Desk B: practice / game</th><th>Source</th></tr></thead>
<tbody>
{chr(10).join(body)}
</tbody></table></div>
<h2>Flags (non-blocking, for review)</h2>
<ul class="note">{flag_html}</ul>
<p><small>Evidence: <code>nfl-injury-recon-8b53/evidence/official-REG10-SUN-NE-at-DET-2026-11-18.md</code>
(SHA-256 in <code>evidence/SHA256SUMS.txt</code>). Rebuild: <code>python nfl-injury-recon-8b53/build.py</code>.</small></p>
</main></body></html>
"""


def outputs():
    rows = build_rows()
    summ = summary(rows)
    return {
        ROOT / "data" / "summary.json": json.dumps(summ, indent=2, ensure_ascii=False) + "\n",
        ROOT / "site" / "index.html": render_html(rows, summ),
        ROOT / "site" / "manifest.json": json.dumps({
            "desk": "nfl-injury-recon-8b53",
            "session": "arena/8b538c74-own7",
            "read_on": "2026-11-18",
            "pages": ["index.html"],
        }, indent=2) + "\n",
    }


def main(argv):
    out = outputs()
    if "--check" in argv:
        bad = [str(p.relative_to(ROOT)) for p, txt in out.items()
               if not p.exists() or p.read_text(encoding="utf-8") != txt]
        if bad:
            print("STALE:", *bad, sep="\n  ")
            return 1
        print("OK: byte-identical rebuild")
        return 0
    for p, txt in out.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8", newline="\n")
        print("wrote", p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
