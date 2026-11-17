"""Deterministic line-by-line checks for the brief tracker (session arena/77b177da-own7).

Everything here is read-only over files already in the repository plus the four evidence
extracts in ./evidence. No network access, no wall-clock input, no value is inferred: a check either
matches a row by exact normalised name or it does not. Any missing expected column raises, so a
renamed source fails the build instead of producing blank counts.
"""
from __future__ import annotations

import csv
import hashlib
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# Repository files read (read-only). Paths are relative to the repository root.
AVAIL_DEPTH = "nfl-availability-28ef/data/depth-slots-week10-2026.csv"
SKILL_DEPTH = "nfl-skill-cfdd/data/depth-slots-2026-11-14.csv"
INJURY_FILES = {
    # desk: (path, team column, player column, game-status column or None, rows label)
    "nfl-availability-28ef (Week 10, 14 games)": ("nfl-availability-28ef/data/injuries-week10-2026.csv", "club_abbr", "player", "game_status"),
    "nfl-assurance-9580ac3f (Week 10)": ("nfl-assurance-9580ac3f/data/injuries.csv", "team", "player", "game_status"),
    "nfl/origination (Week 10)": ("nfl/origination/data/injuries-2026-w10.csv", "club", "player", "designation"),
    "data/ Week 10 (Thursday listing only)": ("data/nfl-injuries-2026-w10.csv", "Team", "Player", "GameStatus"),
    "data/ Week 7": ("data/nfl-injuries-week7-2026.csv", "Team", "Player", "GameStatus"),
}
LIONS_THREE = ("Kerby Joseph", "Cade Mays", "D.J. Reed")
OFFICIAL_LIONS_STATUS = {"Kerby Joseph": "Out", "Cade Mays": "Out", "D.J. Reed": "Out"}  # nfl.com/injuries, read 2026-11-17

# Nickname as printed on NFL.com transactions -> club abbreviation used in the depth CSVs.
NICK_TO_ABBR = {
    "Cardinals": "AZ", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF", "Panthers": "CAR",
    "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE", "Cowboys": "DAL", "Broncos": "DEN",
    "Lions": "DET", "Packers": "GB", "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX",
    "Chiefs": "KC", "Raiders": "LV", "Chargers": "LAC", "Rams": "LAR", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG", "Jets": "NYJ",
    "Eagles": "PHI", "Steelers": "PIT", "49ers": "SF", "Seahawks": "SEA", "Buccaneers": "TB",
    "Titans": "TEN", "Commanders": "WAS",
}
BALL = "BAL"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_md_table(path: Path) -> list[dict]:
    """Parse the first pipe table in an evidence file. Header row defines the keys."""
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("|")]
    if len(lines) < 3:
        raise ValueError(f"{path.name}: no table found")
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) != len(header):
            raise ValueError(f"{path.name}: row has {len(cells)} cells, header has {len(header)}: {ln[:80]}")
        rows.append(dict(zip(header, cells)))
    return rows


def norm(name: str) -> str:
    s = name.lower().replace(".", "").replace("'", "")
    return re.sub(r"\s+", " ", s).strip()


def load_csv(rel: str) -> list[dict]:
    with (REPO / rel).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def need(row: dict, key: str, rel: str) -> str:
    if key not in row:
        raise KeyError(f"{rel}: expected column '{key}' is missing (source schema changed)")
    return row[key]


def depth_rows() -> list[dict]:
    """All printed-chart slot rows from both depth desks, with the desk and the chart date kept."""
    out = []
    for rel in (AVAIL_DEPTH, SKILL_DEPTH):
        for r in load_csv(rel):
            club = need(r, "club_abbr", rel)
            names = [n.strip() for n in need(r, "player", rel).split(" / ") if n.strip()]
            out.append({
                "club": club, "unit": need(r, "unit", rel), "position": need(r, "position", rel),
                "slot": need(r, "slot", rel), "rank": need(r, "rank", rel), "names": names,
                "checked_on": need(r, "checked_on", rel), "source_url": need(r, "source_url", rel),
                "desk": rel.split("/")[0], "multi": need(r, "cell_holds_multiple", rel) == "yes",
            })
    return out


def chart_dates(rows: list[dict]) -> dict[str, str]:
    """Latest checked_on per club (the date of the capture that was actually read)."""
    out: dict[str, str] = {}
    for r in rows:
        out[r["club"]] = max(out.get(r["club"], ""), r["checked_on"])
    return out


def transactions() -> list[dict]:
    rows = parse_md_table(HERE / "evidence" / "nfl-transactions-2026-11.md")
    out = []
    for r in rows:
        if r["From"] not in NICK_TO_ABBR or r["To"] not in NICK_TO_ABBR:
            raise KeyError(f"unmapped club nickname in transactions: {r}")
        mm, dd = r["Date"].split("/")
        out.append({"date": f"2026-{mm}-{dd}", "printed_date": r["Date"], "name": r["Name"],
                    "from": NICK_TO_ABBR[r["From"]], "to": NICK_TO_ABBR[r["To"]],
                    "from_nick": r["From"], "to_nick": r["To"], "transaction": r["Transaction"]})
    return out


def stale_depth_check() -> list[dict]:
    """Classify each official November trade against the printed charts captured in the repository.

    STALE         the player is still printed on the FORMER club's chart (strong evidence of a stale row)
    PRINTED NEW   the player is printed on the NEW club's chart
    NOT PRINTED   the new club's chart was captured on or after the trade date and does not print the player
                  (weak evidence: printed charts show a few names per slot, so this is a review item only)
    NO CHART      the new club has no captured chart on or after the trade date
    """
    rows = depth_rows()
    dates = chart_dates(rows)
    by_club_name: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        for n in r["names"]:
            by_club_name[(r["club"], norm(n))].append(r)
    results = []
    for t in transactions():
        key = norm(t["name"])
        former = by_club_name.get((t["from"], key), [])
        new = by_club_name.get((t["to"], key), [])
        new_chart = dates.get(t["to"], "")
        if former:
            cls = "STALE"
            detail = "; ".join(f"{x['unit']} {x['position']} rank {x['rank']}" for x in former[:2])
            detail = f"still printed on {t['from']} chart ({detail}), chart checked {former[0]['checked_on']}"
        elif new:
            cls = "PRINTED NEW"
            detail = "; ".join(f"{x['unit']} {x['position']} rank {x['rank']}" for x in new[:2])
            detail = f"printed on {t['to']} chart ({detail}), chart checked {new[0]['checked_on']}"
        elif not new_chart or new_chart < t["date"]:
            cls = "NO CHART"
            detail = f"no {t['to']} chart captured on or after {t['date']}"
        else:
            cls = "NOT PRINTED"
            detail = f"{t['to']} chart checked {new_chart} (on/after the trade) does not print the player"
        results.append({**t, "class": cls, "detail": detail,
                        "former_chart_checked": dates.get(t["from"], ""), "new_chart_checked": new_chart})
    return results


def injury_comparison() -> list[dict]:
    out = []
    for desk, (rel, team_col, player_col, status_col) in INJURY_FILES.items():
        rows = load_csv(rel)
        lions = {}
        for r in rows:
            p = need(r, player_col, rel)
            if p in LIONS_THREE and need(r, team_col, rel) in ("DET", "Lions", "Detroit Lions", "DET "):
                lions[p] = need(r, status_col, rel) if status_col else ""
        has_status = status_col is not None
        populated = sum(1 for r in rows if has_status and need(r, status_col, rel).strip())
        out.append({
            "desk": desk, "file": rel, "rows": len(rows),
            "clubs": len({need(r, team_col, rel) for r in rows}),
            "club_codes": sorted({need(r, team_col, rel) for r in rows}),
            "status_column": status_col or "(none)", "status_populated": populated if has_status else None,
            "lions": {p: (lions.get(p, "") if p in lions else "absent") for p in LIONS_THREE},
        })
    return out


def rank_one_groups() -> dict:
    """Club x unit x position groups that print more than one rank-1 name."""
    def count(rows):
        groups = defaultdict(list)
        for r in rows:
            groups[(r["club"], r["unit"], r["position"])].append(r)
        multi = [k for k, v in groups.items() if sum(1 for x in v if str(x["rank"]) == "1") > 1]
        return len(groups), len(multi)
    rows = depth_rows()
    avail = [r for r in rows if r["desk"] == "nfl-availability-28ef"]
    skill = [r for r in rows if r["desk"] == "nfl-skill-cfdd"]
    g_a, m_a = count(avail)
    g_s, m_s = count(skill)
    g_all, m_all = count(rows)
    return {"availability_groups": g_a, "availability_multi": m_a,
            "skill_groups": g_s, "skill_multi": m_s,
            "combined_groups": g_all, "combined_multi": m_all,
            "clubs_availability": len({r["club"] for r in avail}), "clubs_skill": len({r["club"] for r in skill}),
            "club_list": sorted({r["club"] for r in rows})}


def baltimore_chart_change() -> dict:
    """Offense names: repository chart (checked 2026-11-12) vs club Offense table read 2026-11-17.

    Only the Offense unit is compared, because only the Offense table was transcribed from the 2026-11-17 read.
    """
    repo = {norm(n) for r in depth_rows() if r["club"] == BALL and r["unit"] == "Offense" for n in r["names"]}
    lines = (HERE / "evidence" / "ravens-depth-chart-2026-11-17.md").read_text(encoding="utf-8").splitlines()
    read_names = set()
    for ln in lines:
        if ln.startswith("| ") and not ln.startswith("| Position") and not ln.startswith("| ---"):
            cells = [c.strip() for c in ln.strip("|").split("|")][1:]
            read_names |= {norm(c) for c in cells if c}
    name_of = {}
    for ln in lines:
        if ln.startswith("| ") and not ln.startswith("| Position") and not ln.startswith("| ---"):
            for c in [c.strip() for c in ln.strip("|").split("|")][1:]:
                if c:
                    name_of[norm(c)] = c
    only_read = sorted(name_of[k] for k in read_names - repo)
    repo_name = {}
    for r in depth_rows():
        if r["club"] == BALL and r["unit"] == "Offense":
            for n in r["names"]:
                repo_name[norm(n)] = n
    only_repo = sorted(repo_name[k] for k in repo - read_names)
    qb_repo = [" / ".join(r["names"]) for r in depth_rows() if r["club"] == BALL and r["position"] == "QB" and r["rank"] in ("1", "2", "3")]
    qb_read = [c.strip() for c in next(ln for ln in lines if ln.startswith("| QB |")).strip("|").split("|")][1:]
    return {"repo_checked": "2026-11-12", "read_on": "2026-11-17",
            "only_on_2026_11_17_page": only_read, "only_in_repo_2026_11_12_chart": only_repo,
            "qb_repo": qb_repo, "qb_read": [c for c in qb_read if c]}


def lions_check() -> dict:
    """Per-desk game status for the three Week 10 Lions players, versus the official read.

    A desk whose file does not contain the Detroit Week 10 rows at all is reported as out of scope,
    not as a mismatch.
    """
    result = {}
    for c in injury_comparison():
        values = list(c["lions"].values())
        if all(v == "absent" for v in values):
            result[c["desk"]] = {"lions": c["lions"], "scope": "out of scope (no Detroit Week 10 rows in this file)",
                                 "matches_official": None, "mismatches": []}
            continue
        bad = [p for p in LIONS_THREE if c["lions"][p] != OFFICIAL_LIONS_STATUS[p]]
        result[c["desk"]] = {"lions": c["lions"], "scope": "in scope", "matches_official": not bad, "mismatches": bad}
    return result


def receipts() -> dict:
    out = {}
    for p in sorted((HERE / "evidence").glob("*.md")):
        out[str(p.relative_to(REPO))] = sha256(p)
    return out


def summary() -> dict:
    st = stale_depth_check()
    counts = defaultdict(int)
    for r in st:
        counts[r["class"]] += 1
    return {"transactions": len(st), "classes": dict(sorted(counts.items())),
            "reserve_rows": len(parse_md_table(HERE / "evidence" / "nfl-reserve-list-2026-11.md"))}
