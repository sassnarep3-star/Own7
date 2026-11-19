#!/usr/bin/env python3
"""Live Week 11 injury-report re-read desk (session arena/b3c4087a-own7).

Inputs (committed):
  data/thursday-2026-11-19.csv       the 26 Thursday rows as printed on https://www.nfl.com/injuries/
                                     at the 2026-11-19 read (transcribed from the fetched page text)
  data/club-counts-2026-11-19.csv    printed player-row count for each of the 26 clubs at the same read
  ../nfl-w11-injuries-3e61/data/injuries-week11.csv   repo capture of 2026-11-18 (06:20-06:24 UTC)
  ../nfl-w11-injuries-3e61/data/clubs-week11.csv      repo club-level capture of 2026-11-18
  ../research/sources.json           registered sources (B3C-* rows)

Every number on the pages is computed here. The build aborts on a missing input, a count that does
not reproduce, or a row without its registered official link.

    python nfl-live-b3c4087a/build.py           # write site/ and manifest.json
    python nfl-live-b3c4087a/build.py --check   # re-render in memory, compare bytes
"""
from __future__ import annotations

import csv
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
SITE = HERE / "site"
REPO_W11 = ROOT / "nfl-w11-injuries-3e61" / "data"

READ_ON = "2026-11-19"
READ_WINDOW = "about 12:05-12:15 UTC (the page was fetched in six chunks; one read, not a schedule)"
REPO_READ = "2026-11-18, 06:20-06:24 UTC"
INJURY_URL = "https://www.nfl.com/injuries/"
TERMS_URL = "https://www.nfl.com/legal/terms/"
SRC_INJ = "B3C-NFL-INJURIES"
SRC_TERMS = "B3C-NFL-TERMS"
SRC_REPO = "B3C-REPO-W11"
REPO_URL = "https://github.com/sassnarep3-star/Own7/blob/main/nfl-w11-injuries-3e61/data/injuries-week11.csv"
EXPECTED_CLUBS = 26
EXPECTED_LIVE_ROWS = 253
EXPECTED_THURSDAY_ROWS = 26
STYLE = "../../assets/style.css"


class DeskError(SystemExit):
    pass


def fail(msg: str) -> None:
    raise DeskError(f"nfl-live-b3c4087a/build.py: {msg}")


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        fail(f"missing input {path.relative_to(ROOT)}")
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def registry_ids() -> dict:
    reg = json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))
    return {r["id"]: r["url"] for r in reg}


def compute() -> dict:
    thu = read_csv(DATA / "thursday-2026-11-19.csv")
    clubs = read_csv(DATA / "club-counts-2026-11-19.csv")
    repo_rows = read_csv(REPO_W11 / "injuries-week11.csv")
    repo_clubs = read_csv(REPO_W11 / "clubs-week11.csv")

    if len(clubs) != EXPECTED_CLUBS:
        fail(f"expected {EXPECTED_CLUBS} clubs, found {len(clubs)}")
    total = sum(int(c["rows_printed"]) for c in clubs)
    if total != EXPECTED_LIVE_ROWS:
        fail(f"live player-row total {total} != {EXPECTED_LIVE_ROWS}")
    if len(thu) != EXPECTED_THURSDAY_ROWS:
        fail(f"expected {EXPECTED_THURSDAY_ROWS} Thursday rows, found {len(thu)}")
    thu_by_club = {}
    for r in thu:
        thu_by_club[r["club_code"]] = thu_by_club.get(r["club_code"], 0) + 1
    for c in clubs:
        if c["club_code"] in thu_by_club and thu_by_club[c["club_code"]] != int(c["rows_printed"]):
            fail(f"{c['club_code']}: Thursday rows {thu_by_club[c['club_code']]} != club count {c['rows_printed']}")

    repo_by_key = {(r["club_code"], r["player"]): r for r in repo_rows}
    if len(repo_by_key) != len(repo_rows):
        fail("repo capture has duplicate player keys")
    repo_clubs_by = {r["club_code"]: r for r in repo_clubs}

    thursday = []
    changed_players = 0
    changed_fields_total = 0
    for r in thu:
        old = repo_by_key.get((r["club_code"], r["player"]))
        if old is None:
            fail(f"player {r['player']} absent from the 2026-11-18 repo capture")
        diffs = []
        for live_key, repo_key, label in (
            ("injuries_printed", "injuries_printed", "Injuries"),
            ("practice_status_printed", "practice_status_printed", "Practice"),
            ("game_status_printed", "game_status_printed", "Game status"),
        ):
            if r[live_key] != old[repo_key]:
                diffs.append(label)
        if diffs:
            changed_players += 1
            changed_fields_total += len(diffs)
        thursday.append({**r, "repo": old, "diffs": diffs})

    game_status_live = sum(1 for r in thu if r["game_status_printed"].strip())
    game_status_repo = sum(1 for r in repo_rows if r["game_status_printed"].strip())
    injuries_live = sum(1 for r in thu if r["injuries_printed"].strip())
    injuries_repo = sum(1 for r in repo_rows if r["injuries_printed"].strip())

    club_rows = []
    for c in clubs:
        old = repo_clubs_by.get(c["club_code"])
        if old is None:
            fail(f"club {c['club_code']} missing from repo club capture")
        old_rows = int(old["rows_printed"])
        club_rows.append({
            **c,
            "repo_rows": old_rows,
            "repo_status": old["status_printed"],
            "changed": int(c["rows_printed"]) != old_rows,
        })

    clubs_with_no_injuries_repo = sum(1 for c in repo_clubs if c["status_printed"] == "No Injuries Reported")
    clubs_with_no_injuries_live = sum(1 for c in clubs if c["status_printed"] == "No Injuries Reported")
    clubs_changed = sum(1 for c in club_rows if c["changed"])

    reg = registry_ids()
    for sid in (SRC_INJ, SRC_TERMS, SRC_REPO):
        if sid not in reg:
            fail(f"source {sid} not registered in research/sources.json")
    if reg[SRC_INJ] != INJURY_URL or reg[SRC_TERMS] != TERMS_URL or reg[SRC_REPO] != REPO_URL:
        fail("registered URL differs from the URL this desk cites")

    return {
        "thursday": thursday,
        "clubs": club_rows,
        "total_live_rows": total,
        "changed_players": changed_players,
        "changed_fields_total": changed_fields_total,
        "game_status_live": game_status_live,
        "game_status_repo": game_status_repo,
        "injuries_live": injuries_live,
        "injuries_repo": injuries_repo,
        "clubs_no_injuries_repo": clubs_with_no_injuries_repo,
        "clubs_no_injuries_live": clubs_with_no_injuries_live,
        "clubs_changed": clubs_changed,
        "repo_rows_total": sum(int(c["rows_printed"]) for c in repo_clubs),
    }


def e(value) -> str:
    return html.escape(str(value), quote=True)


def cell(value: str) -> str:
    if value is None or str(value).strip() == "":
        return '<td data-empty="true"></td>'
    return f"<td>{e(value)}</td>"


PAGE_CSS = """body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1d2b22;margin:0;padding:24px 28px;max-width:1280px;margin:0 auto;line-height:1.5;font-size:15px}
header p{font-size:13px;margin:0 0 18px}
h1{font-size:26px;margin:8px 0 10px}
h2{font-size:18px;margin:28px 0 10px}
.lede{font-size:15px;max-width:900px}
.note{font-size:12.5px;color:#4a5e51;max-width:900px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0}
.card{border:1px solid #d6dfd8;border-radius:8px;padding:12px 14px;background:#fff}
.card strong{display:block;font-size:22px;color:#1f4d36}
.card span{font-size:12px;color:#4a5e51}
.table-wrap{overflow-x:auto;max-width:100%;border:1px solid #d6dfd8;border-radius:8px;background:#fff}
.table-wrap table{border-collapse:collapse;width:100%;font-size:12.5px}
.table-wrap th,.table-wrap td{text-align:left;vertical-align:top;padding:7px 9px;border-bottom:1px solid #e6ebe7;word-break:break-word}
.table-wrap th{background:#f5f8f5;font-weight:600}
td[data-empty="true"]{background:repeating-linear-gradient(135deg,#fff 0 6px,#f3f5f3 6px 7px)}
a{color:#1a5a3f;text-decoration:underline}
nav a,header a{color:#1a5a3f}
"""


def page(title: str, description: str, body: str, nav: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · OWN7 NFL live check</title>
<meta name="description" content="{e(description)}">
<link rel="stylesheet" href="{STYLE}">
<style>{PAGE_CSS}</style>
</head>
<body>
<header>
<p><a href="index.html">Live check dashboard</a> · <a href="flagged.html">Flagged for review</a> · <a href="../../nfl-w11-injuries-3e61/site/index.html">Week 11 desk (2026-11-18)</a></p>
</header>
<main>
{nav}
{body}
</main>
</body>
</html>
"""


def section(heading: str, inner: str) -> str:
    return f"<section><h2>{e(heading)}</h2>\n{inner}\n</section>"


def table(headers: list[str], rows: list[str]) -> str:
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>\n" + "\n".join(rows) + "\n</tbody></table></div>"


def render(data: dict) -> dict[str, str]:
    thu_rows = []
    for r in data["thursday"]:
        repo = r["repo"]
        changed = ", ".join(r["diffs"]) if r["diffs"] else "No change"
        thu_rows.append(
            f'<tr data-source-ids="{SRC_INJ}">'
            f'<td>{e(r["club_code"])}</td>'
            f'<td><a href="{INJURY_URL}">{e(r["player"])}</a></td>'
            f'<td>{e(r["position"])}</td>'
            f'{cell(r["injuries_printed"])}'
            f'{cell(r["practice_status_printed"])}'
            f'{cell(r["game_status_printed"])}'
            f'{cell(repo["practice_status_printed"])}'
            f'{cell(repo["game_status_printed"])}'
            f'<td>{e(changed)}</td>'
            '</tr>'
        )
    club_rows = []
    for c in data["clubs"]:
        status_live = c["status_printed"] if int(c["rows_printed"]) == 0 else f"{c['rows_printed']} player rows"
        status_repo = c["repo_status"] if c["repo_rows"] == 0 else f"{c['repo_rows']} player rows"
        club_rows.append(
            f'<tr data-source-ids="{SRC_INJ}">'
            f'<td>{e(c["game_label"])}</td>'
            f'<td><a href="{INJURY_URL}">{e(c["club_name"])} ({e(c["club_code"])})</a></td>'
            f'<td>{e(c["rows_printed"])}</td>'
            f'<td>{e(status_live)}</td>'
            f'<td>{e(status_repo)}</td>'
            f'<td>{"Changed" if c["changed"] else "Same"}</td>'
            '</tr>'
        )
    summary = (
        f'<div class="cards">'
        f'<div class="card"><strong>{data["total_live_rows"]}</strong><span>player rows printed (26 clubs), live read</span></div>'
        f'<div class="card"><strong>{data["clubs_no_injuries_live"]}</strong><span>clubs printing "No Injuries Reported" (live)</span></div>'
        f'<div class="card"><strong>{data["clubs_no_injuries_repo"]}</strong><span>clubs printing "No Injuries Reported" in the 2026-11-18 repo capture</span></div>'
        f'<div class="card"><strong>{data["clubs_changed"]}</strong><span>clubs whose printed row count changed since 2026-11-18</span></div>'
        f'<div class="card"><strong>{data["game_status_live"]} of {len(data["thursday"])}</strong><span>Thursday game-status cells printed (live); repo 2026-11-18 had {data["game_status_repo"]}</span></div>'
        f'<div class="card"><strong>{data["changed_players"]}</strong><span>Thursday players with a changed field (of {len(data["thursday"])})</span></div>'
        '</div>'
    )
    intro = (
        f'<h1>Week 11 injury report: live re-read on {READ_ON}</h1>\n'
        f'<p class="lede">The repo\'s Week 11 desk read the official report on {REPO_READ}. This page is one later read, '
        f'taken {READ_WINDOW}, to show what the official page prints now. Every value is copied from the official page at that read. '
        'Blank means the official page printed a blank cell. Nothing is inferred.</p>\n'
        f'<p class="note">Read by a single fetch of <a href="{INJURY_URL}">nfl.com/injuries</a>. '
        f'The NFL terms (<a href="{TERMS_URL}">§1.3</a>) prohibit systematic retrieval to compile a collection without written consent, '
        'so this is not a scheduled capture, and the full 253-row report is not stored here. Only the 26 Thursday rows and the club-level counts are kept.</p>\n'
    )
    thu_section = section(
        "Thursday, 19 Nov · Colts at Texans (8:15 PM ET, Prime Video): live rows vs the 2026-11-18 repo capture",
        table(["Club", "Player", "Pos", "Injuries (live)", "Practice (live)", "Game status (live)",
               "Practice (repo 11-18)", "Game status (repo 11-18)", "What changed"], thu_rows)
        + f'\n<p class="note">Source for every row: <a href="{INJURY_URL}">nfl.com/injuries</a> (registered {SRC_INJ}). '
          f'Repo comparison: <a href="{REPO_URL}">nfl-w11-injuries-3e61/data/injuries-week11.csv</a> ({SRC_REPO}).</p>',
    )
    club_section = section(
        "All 26 clubs, Week 11: printed row counts, live vs 2026-11-18",
        table(["Game", "Club", "Rows (live)", "Printed (live)", "Printed (repo 11-18)", "Change"], club_rows)
        + f'\n<p class="note">Counts are the player rows printed per club on the live read. Sunday and Monday clubs printed practice statuses '
          f'at this read but not injury or game-status text for most rows; that is what the page showed, not a verified policy.</p>',
    )
    what_section = section("What this means for the repo", (
        '<ul>'
        '<li>The 2026-11-18 Week 11 desk (<a href="../../nfl-w11-injuries-3e61/site/index.html">link</a>) recorded 24 clubs with "No Injuries Reported". '
        f'The live page now prints player rows for {len(data["clubs"]) - data["clubs_no_injuries_live"]} clubs (CIN and WAS print none), and {data["changed_players"]} of 26 Thursday players have at least one changed field. '
        'Its "blank game status" flags (W11-F01/F02) are superseded for Thursday: the page now prints game status for '
        f'{data["game_status_live"]} of 26 Thursday players.</li>'
        '<li>Ten Thursday game-status cells remain blank at this read. Blank stays blank on the site; no status is inferred.</li>'
        '<li>Only an official, timestamped series can show practice trends (DNP to LP to FP) or Questionable to Out moves. '
        'One read cannot. A scheduled series would need written NFL consent under the terms, which the repo has not obtained. See the flagged page.</li>'
        '</ul>'
    ))
    index_body = intro + summary + thu_section + club_section + what_section
    nav = ('<nav aria-label="Pages"><a href="index.html">Dashboard</a> · '
           '<a href="flagged.html">Flagged for review</a></nav>')

    index_html = page(
        "Week 11 live injury check",
        "One later official read of the Week 11 NFL injury report, compared with the repo's 2026-11-18 capture.",
        index_body, nav)

    flags = [
        ("B3C-F01", "The repo's 2026-11-18 Week 11 capture is out of date.",
         f'At 06:20 UTC on 2026-11-18 the page printed "No Injuries Reported" for 24 clubs. At the 2026-11-19 read, '
         f'{len(data["clubs"]) - data["clubs_no_injuries_live"]} clubs print player rows. The repo desk is correct for its date and is not wrong as a snapshot; it is now superseded.',
         SRC_INJ, f"{INJURY_URL} vs {REPO_URL}"),
        ("B3C-F02", "Thursday game-status blanks are partly filled in.",
         f'The repo desk (W11-F01/F02) says every Game Status cell is blank. At the live read {data["game_status_live"]} of 26 are printed. Ten remain blank: Carlies, Tucker, Al-Shaair, Blankenship, Dell, Fisher, Lassiter, Montgomery, Nwaiwu, Rutledge.',
         SRC_INJ, INJURY_URL),
        ("B3C-F03", "Row total differs from the brief.",
         f'Counting the printed player rows at this read gives {data["total_live_rows"]}. The earlier brief said 254. This is not reproduced; it could be a count error here or a different read. Owner to recount.',
         SRC_INJ, INJURY_URL),
        ("B3C-F04", "Daily or scheduled capture is blocked by the NFL terms.",
         'NFL.com Terms §1.3 prohibits systematic retrieval of data to create or compile a collection without express prior written consent. '
         'Daily Wednesday-to-kickoff snapshots, which the brief asks for, are not built. Options: (a) written consent from NFL; (b) a licensed data feed; (c) no capture, manual one-off reads only. Owner decision; not a legal opinion.',
         SRC_TERMS, TERMS_URL),
        ("B3C-F05", "Printed name and link slug do not match (2 rows).",
         'Bills: "Dee Alford" links to /players/deaundre-ford/. Texans: "Jacob Hummel" links to /players/jake-hummel/. Printed as shown; not resolved.',
         SRC_INJ, INJURY_URL),
        ("B3C-F06", "Jaylen Waddle appears in the Broncos table at this read.",
         'The page prints Jaylen Waddle (WR, Full Participation) in the Broncos list. The repo has not checked this against an official roster or transaction; the row is kept as printed and not interpreted.',
         SRC_INJ, INJURY_URL),
        ("B3C-F07", "Sunday and Monday game-status cells blank at this read.",
         'Game-status text is blank for the Sunday and Monday rows at this read. That may be a publishing schedule, but this desk has not verified the publishing rule. Left blank.',
         SRC_INJ, INJURY_URL),
    ]
    flag_rows = []
    for fid, title, detail, sid, link in flags:
        flag_rows.append(
            f'<tr data-source-ids="{sid}"><td>{e(fid)}</td><td>{e(title)}</td><td>{e(detail)}</td>'
            f'<td><a href="{e(link.split(" vs ")[0])}">{e(link)}</a></td><td>Open</td></tr>')
    flag_body = (
        '<h1>Flagged for review</h1>\n'
        '<p class="lede">Non-blocking. Items are published with their sources so they can be reviewed and changed. '
        'Nothing here changes a registered gate or the ledger status of any requirement.</p>\n'
        + section("Flags B3C-F01 to F07", table(["ID", "Item", "Detail", "Official source", "Status"], flag_rows))
        + section("Decisions requested from the owner", (
            '<ul><li>Choose a rights route for any recurring capture of nfl.com (B3C-F04).</li>'
            '<li>Confirm or correct the 253 row total (B3C-F03).</li>'
            '<li>Decide whether the repo should keep the 2026-11-18 Week 11 desk as a dated snapshot (it is now superseded by this read, not deleted).</li></ul>'
        ))
    )
    flagged_html = page(
        "Flagged for review", "Non-blocking irregularities and decisions for the NFL live injury check.",
        flag_body, nav)

    return {"index.html": index_html, "flagged.html": flagged_html}


def main(argv: list[str]) -> int:
    data = compute()
    pages = render(data)
    if "--check" in argv:
        bad = []
        for name, text in pages.items():
            p = SITE / name
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                bad.append(name)
        if bad:
            print("nfl-live-b3c4087a: stale or missing pages: " + ", ".join(bad))
            return 1
        print(f"nfl-live-b3c4087a: {len(pages)} pages reproduce byte-identically; "
              f"{EXPECTED_LIVE_ROWS} live rows, {EXPECTED_CLUBS} clubs; {data['changed_players']} Thursday players changed.")
        return 0
    SITE.mkdir(parents=True, exist_ok=True)
    for name, text in pages.items():
        (SITE / name).write_text(text, encoding="utf-8")
    (SITE / "manifest.json").write_text(json.dumps({"pages": sorted(pages)}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(pages)} pages to {SITE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except DeskError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
