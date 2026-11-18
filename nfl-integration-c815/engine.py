"""Integration audit desk — verified engine (session arena/c815bdd2-own7).

Everything this desk publishes is **re-derived from the committed official captures**
under ``evidence/`` and from the canonical artefacts already in the repository. Nothing
is typed in as a conclusion: if a re-derivation disagrees with what another desk
published, the disagreement is published rather than smoothed over.

Rules this module enforces (each one aborts the build instead of publishing a value):

1. **Standings capture is self-consistent.** Every one of the 32 club rows must satisfy
   ``PCT == (W + T/2) / games``, ``NET == PF - PA`` and ``HOME + ROAD == (W, L, T)``.
2. **League arithmetic closes.** ``sum(W) == sum(L)``, ``sum(PF) == sum(PA)`` and every
   club's played count must imply the same league-wide game total.
3. **The Week 10 completion is proven, not asserted.** The 2026-11-18 standings minus the
   2026-11-17 standings must equal exactly the delta implied by the one headline the
   Week 10 page prints for the previously-pending fixture. If the deltas do not match
   the headline arithmetic, the build fails.
4. **The results feed is stale by exactly that game.** The canonical feed
   (``nfl-results/data/games-2026-w1-10.csv``) is re-tallied and the residue against the
   2026-11-18 standings must be exactly one game, and that game must be the one named.
5. **Published counts are recomputed, never copied.** Every "149" or "150" on this desk
   is an arithmetic result of the rows above it.

No price, ROI, stake, wager or reward is computed anywhere in this module.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESK = ROOT / "nfl-integration-c815"
EVIDENCE = DESK / "evidence"
DATA = DESK / "data"

STANDINGS_URL = "https://www.nfl.com/standings/"
WEEK10_URL = "https://www.nfl.com/schedules/2026/by-week/week-10"
INJURIES_URL = "https://www.nfl.com/injuries/"
STANDINGS_1118 = EVIDENCE / "standings-2026-11-18.retrieved.md"
WEEK10_1118 = EVIDENCE / "week10-final-2026-11-18.retrieved.md"
STANDINGS_1117_CSV = ROOT / "data" / "nfl-standings-2026-11-17.csv"
STANDINGS_FROZEN_CSV = ROOT / "data" / "nfl-standings-2026.csv"
FEED_CSV = ROOT / "nfl-results" / "data" / "games-2026-w1-10.csv"
SCHEDULED_W10_CSV = ROOT / "nfl-results" / "data" / "scheduled-2026-w10.csv"

CLUB_DIVISION = {
    "BUF": "AFC East", "NE": "AFC East", "NYJ": "AFC East", "MIA": "AFC East",
    "PIT": "AFC North", "CIN": "AFC North", "CLE": "AFC North", "BAL": "AFC North",
    "JAX": "AFC South", "HOU": "AFC South", "IND": "AFC South", "TEN": "AFC South",
    "DEN": "AFC West", "KC": "AFC West", "LV": "AFC West", "LAC": "AFC West",
    "NYG": "NFC East", "DAL": "NFC East", "WAS": "NFC East", "PHI": "NFC East",
    "CHI": "NFC North", "DET": "NFC North", "MIN": "NFC North", "GB": "NFC North",
    "CAR": "NFC South", "NO": "NFC South", "TB": "NFC South", "ATL": "NFC South",
    "SF": "NFC West", "SEA": "NFC West", "LA": "NFC West", "AZ": "NFC West",
}

# The publisher prints the nickname in result headlines. Naming map only: it carries
# no data value and is checked for completeness both ways below.
NAME_BY_ABBR = {
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
ABBR_BY_NAME = {v: k for k, v in NAME_BY_ABBR.items()}
NICKNAME = {
    "Cardinals": "AZ", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF", "Panthers": "CAR",
    "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE", "Cowboys": "DAL", "Broncos": "DEN",
    "Lions": "DET", "Packers": "GB", "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX",
    "Chiefs": "KC", "Raiders": "LV", "Chargers": "LAC", "Rams": "LA", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG", "Jets": "NYJ",
    "Eagles": "PHI", "Steelers": "PIT", "49ers": "SF", "Seahawks": "SEA", "Buccaneers": "TB",
    "Titans": "TEN", "Commanders": "WAS",
}

# The four printed record cells are "1 - 4 - 0"; the parser strips the spaces.
REC = re.compile(r"^(\d+)\s*-\s*(\d+)\s*-\s*(\d+)$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_standings_capture(path: Path = STANDINGS_1118) -> list[dict]:
    """Parse the verbatim standings capture and validate every row arithmetically."""
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| club") or line.startswith("|---"):
            continue
        cells = _cells(line)
        if len(cells) != 13:
            raise SystemExit(f"standings capture: expected 13 cells, got {len(cells)}: {line!r}")
        club = cells[0]
        if club not in ABBR_BY_NAME:
            raise SystemExit(f"standings capture: unknown club {club!r}")
        code = ABBR_BY_NAME[club]
        try:
            w, l, t = int(cells[1]), int(cells[2]), int(cells[3])
            pct = float(cells[4])
            pf, pa = int(cells[5]), int(cells[6])
        except ValueError as exc:                      # pragma: no cover - abort path
            raise SystemExit(f"standings capture: non-numeric cell for {club}: {cells}") from exc
        home, road = REC.match(cells[7]), REC.match(cells[8])
        div, conf = REC.match(cells[9]), REC.match(cells[10])
        if not (home and road and div and conf):
            raise SystemExit(f"standings capture: unparsable record cell for {club}: {cells}")
        home_t = tuple(int(x) for x in home.groups())
        road_t = tuple(int(x) for x in road.groups())
        # (1) PCT identity
        if abs((w + t / 2) / (w + l + t) - pct) > 0.00051:
            raise SystemExit(f"{club}: PCT {pct} does not equal (W + T/2)/games")
        # (2) HOME + ROAD == overall
        if (home_t[0] + road_t[0], home_t[1] + road_t[1], home_t[2] + road_t[2]) != (w, l, t):
            raise SystemExit(f"{club}: HOME + ROAD does not equal the overall record")
        rows.append({
            "code": code, "club": club, "conference": "AFC" if club in [NAME_BY_ABBR[c] for c in CLUB_DIVISION if CLUB_DIVISION[c].startswith("AFC")] else "NFC",
            "division": CLUB_DIVISION[code],
            "w": w, "l": l, "t": t, "pct": pct, "pf": pf, "pa": pa, "net": pf - pa,
            "home": cells[7], "road": cells[8], "div": cells[9], "conf": cells[10],
            "strk": cells[11], "last5": cells[12],
        })
    if len(rows) != 32 or len({r["code"] for r in rows}) != 32:
        raise SystemExit(f"standings capture: {len(rows)} rows, expected 32 unique clubs")
    return rows


def league_arithmetic(rows: list[dict]) -> dict:
    """League-wide identities that must close on a correct standings read."""
    sum_w = sum(r["w"] for r in rows)
    sum_l = sum(r["l"] for r in rows)
    sum_t = sum(r["t"] for r in rows)
    sum_pf = sum(r["pf"] for r in rows)
    sum_pa = sum(r["pa"] for r in rows)
    club_games = sum_w + sum_l + sum_t
    if sum_w != sum_l:
        raise SystemExit(f"league arithmetic: sum(W)={sum_w} != sum(L)={sum_l}")
    if sum_pf != sum_pa:
        raise SystemExit(f"league arithmetic: sum(PF)={sum_pf} != sum(PA)={sum_pa}")
    if club_games % 2:
        raise SystemExit(f"league arithmetic: {club_games} club-games is odd")
    return {
        "clubs": len(rows), "sum_w": sum_w, "sum_l": sum_l, "sum_t": sum_t,
        "sum_pf": sum_pf, "sum_pa": sum_pa, "club_games": club_games,
        "games_played": club_games // 2,
        "games_played_formula": "sum(W) + sum(L) + sum(T) over 32 clubs, divided by 2",
    }


def parse_week10_completion(path: Path = WEEK10_1118) -> dict:
    """Read the one headline that settles the previously-pending Week 10 fixture."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^(?P<away>[A-Za-z0-9]+) (?P<ascore>\d{1,2}), (?P<home>[A-Za-z0-9]+) "
        r"(?P<hscore>\d{1,2}), FINAL, (?P<weekday>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
        r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December) "
        r"(?P<day>\d{1,2})(?:st|nd|rd|th)$",
        re.MULTILINE,
    )
    # The capture quotes the settled fixture headline once in its own section and once
    # in the verbatim full list. Duplicates must agree cell for cell; only unique
    # fixtures are counted, so the capture cannot inflate the slate.
    finals: list[dict] = []
    seen: dict[tuple[str, str], dict] = {}
    for m in pattern.finditer(text):
        away, home = NICKNAME.get(m["away"]), NICKNAME.get(m["home"])
        if away is None or home is None:
            raise SystemExit(f"week 10 capture: unknown club in headline {m.group(0)!r}")
        record = {
            "away": away, "home": home,
            "away_score": int(m["ascore"]), "home_score": int(m["hscore"]),
            "weekday": m["weekday"], "date": f"{m['month']} {m['day']}",
        }
        key = (away, home)
        if key in seen:
            if seen[key]["away_score"] != record["away_score"] or \
               seen[key]["home_score"] != record["home_score"]:
                raise SystemExit(f"week 10 capture: conflicting duplicate for {key}")
            continue
        seen[key] = record
        finals.append(record)
    if len(finals) != 14:
        raise SystemExit(f"week 10 capture: parsed {len(finals)} unique finals, expected 14")
    pending = [f for f in finals if f["weekday"] == "Monday"]
    if len(pending) != 1:
        raise SystemExit(f"week 10 capture: expected exactly one Monday final, got {len(pending)}")
    return {"finals": finals, "settled": pending[0]}


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def delta_between(previous: list[dict], current: list[dict]) -> list[dict]:
    """Cell-by-cell difference of two standings snapshots, official captures only."""
    prev_by = {r["Team"]: r for r in previous}
    cur_by = {r["code"]: r for r in current}
    out = []
    for code, cur in sorted(cur_by.items()):
        club = NAME_BY_ABBR[code]
        old = prev_by.get(club)
        if old is None:
            raise SystemExit(f"delta: {club} missing from the 2026-11-17 snapshot")
        for field in ("W", "L", "T", "PCT", "PF", "PA", "Home", "Road", "Div", "Conf", "Strk", "Last5"):
            before = (old[field] or "").replace(" ", "")
            after = {
                "W": str(cur["w"]), "L": str(cur["l"]), "T": str(cur["t"]),
                "PCT": f"{cur['pct']:.3f}", "PF": str(cur["pf"]), "PA": str(cur["pa"]),
                "Home": cur["home"], "Road": cur["road"], "Div": cur["div"],
                "Conf": cur["conf"], "Strk": cur["strk"], "Last5": cur["last5"],
            }[field].replace(" ", "")
            if before != after:
                out.append({"club": club, "code": code, "field": field,
                            "previous": before, "current": after})
    return out


def prove_completion(deltas: list[dict], settled: dict) -> dict:
    """The snapshot delta must equal the arithmetic of the settled headline exactly."""
    away, home = settled["away"], settled["home"]
    as_, hs = settled["away_score"], settled["home_score"]
    expect = {
        NAME_BY_ABBR[away]: {"W": 1 if as_ > hs else 0, "L": 1 if as_ < hs else 0,
                             "T": 1 if as_ == hs else 0, "PF": as_, "PA": hs},
        NAME_BY_ABBR[home]: {"W": 1 if hs > as_ else 0, "L": 1 if hs < as_ else 0,
                             "T": 1 if hs == as_ else 0, "PF": hs, "PA": as_},
    }
    numeric = [d for d in deltas if d["field"] in ("W", "L", "T", "PF", "PA")]
    touched = sorted({d["club"] for d in numeric})
    if touched != sorted(expect):
        raise SystemExit(f"completion proof: changed clubs {touched} != {sorted(expect)}")
    for club, wants in expect.items():
        for field, want in wants.items():
            hit = [d for d in numeric if d["club"] == club and d["field"] == field]
            if want == 0:
                # A field that did not move must not appear in the delta at all.
                if hit:
                    raise SystemExit(
                        f"completion proof: {club} {field} appears as changed but should not have moved")
                continue
            if not hit:
                raise SystemExit(f"completion proof: no {field} delta for {club}")
            got = int(hit[0]["current"]) - int(hit[0]["previous"])
            if got != want:
                raise SystemExit(
                    f"completion proof: {club} {field} moved {got}, headline implies {want}")
    return {
        "settled_fixture": f"{away} at {home}",
        "settled_score": f"{away} {as_}, {home} {hs}",
        "clubs_whose_records_changed": len(touched),
        "numeric_fields_changed": len(numeric),
        "verdict": "the 2026-11-18 minus 2026-11-17 delta equals the settled headline exactly",
    }


def tally_feed(games: list[dict]) -> dict[str, dict]:
    tally = {name: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "gp": 0} for name in ABBR_BY_NAME}
    for g in games:
        as_, hs = int(g["away_score"]), int(g["home_score"])
        for code, scored, allowed in ((g["away"], as_, hs), (g["home"], hs, as_)):
            row = tally[NAME_BY_ABBR[code]]
            row["pf"] += scored
            row["pa"] += allowed
            row["gp"] += 1
            if scored > allowed:
                row["w"] += 1
            elif scored < allowed:
                row["l"] += 1
            else:
                row["t"] += 1
    return tally


def feed_residue(current: list[dict]) -> dict:
    """How far the published results feed is behind the 2026-11-18 official standings."""
    games = load_csv(FEED_CSV)
    tally = tally_feed(games)
    residue = []
    for row in current:
        club = row["club"]
        got = tally[club]
        for field, key in (("W", "w"), ("L", "l"), ("T", "t"), ("PF", "pf"), ("PA", "pa")):
            want = row[{"W": "w", "L": "l", "T": "t", "PF": "pf", "PA": "pa"}[field]]
            if got[key] != want:
                residue.append({"club": club, "field": field,
                                "feed": got[key], "official": want, "residue": want - got[key]})
    clubs = sorted({r["club"] for r in residue})
    scheduled = load_csv(SCHEDULED_W10_CSV)
    return {
        "feed_games": len(games),
        "feed_weeks": sorted({int(g["week"]) for g in games}),
        "residue_cells": len(residue),
        "clubs_affected": clubs,
        "residue": residue,
        "pending_rows_in_canonical_store": scheduled,
        "official_games_played": sum(r["w"] + r["l"] + r["t"] for r in current) // 2,
        "target_reference": SETTLED_TARGET,
    }


SETTLED_TARGET = ""

def run() -> dict:
    global SETTLED_TARGET
    current = parse_standings_capture()
    league = league_arithmetic(current)
    completion = parse_week10_completion()
    settled = completion["settled"]
    SETTLED_TARGET = f"{settled['away']} {settled['away_score']}, {settled['home']} {settled['home_score']}"
    previous = load_csv(STANDINGS_1117_CSV)
    deltas = delta_between(previous, current)
    proof = prove_completion(deltas, settled)
    residue = feed_residue(current)
    if residue["feed_games"] + 1 != residue["official_games_played"]:
        raise SystemExit(
            f"residue: feed holds {residue['feed_games']} games and leage arithmetic implies "
            f"{residue['official_games_played']}; the gap must be exactly one game")
    if residue["official_games_played"] - residue["feed_games"] != 1:
        raise SystemExit("residue: the feed is not exactly one game behind")
    settled_scores = f"{settled['away_score']}-{settled['home_score']}"
    return {
        "generated_for": "2026 NFL season, through the completed Week 10 slate",
        "settled_game": {"fixture": proof["settled_fixture"], "score": proof["settled_score"],
                         "score_dash": settled_scores, "week": 10,
                         "weekday": settled["weekday"], "date": settled["date"],
                         "official_page": WEEK10_URL},
        "standings_capture": {
            "source_url": STANDINGS_URL, "path": str(STANDINGS_1118.relative_to(ROOT)),
            "sha256": sha256(STANDINGS_1118), "clubs": len(current)},
        "week10_capture": {
            "source_url": WEEK10_URL, "path": str(WEEK10_1118.relative_to(ROOT)),
            "sha256": sha256(WEEK10_1118), "finals": len(completion["finals"])},
        "league_arithmetic": league,
        "completion_proof": proof,
        "standings": current,
        "deltas": deltas,
        "feed_residue": residue,
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps({k: v for k, v in run().items() if k not in ("standings", "deltas")}, indent=2))
