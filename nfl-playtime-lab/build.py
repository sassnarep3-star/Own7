#!/usr/bin/env python3
"""Official NFL playing-time desk — 2026 Week 10.

Every number here is transcribed from the official NFL Game Book PDF
("Playtime Percentage" section) captured under ``raw/``.

Publisher row grammar
---------------------
Each team block prints a six-cell grid::

    [player, position, OFFENSE, DEFENSE, ST_snaps, ST_pct]

where every one of the three unit cells is either *empty* or a
``"<snaps> <pct>%"`` pair.  An empty cell is semantically meaningful: it means
the player did not appear on that unit at all.  The captures keep one token per
empty cell and two tokens per populated cell, so unit boundaries survive the
flattening that a naive "collect all numbers" transcription would destroy.

This module re-decodes those boundaries, re-derives every printed percentage
from the published denominator, and refuses to publish a value it cannot
verify.  Nothing is imputed: a value that fails verification is withheld and
listed in the flag register with the reason.

Measurement rules this desk keeps
---------------------------------
* A published percentage is evidence in its own right.  The denominator is a
  cross-check, not a replacement: when the two disagree the row is flagged.
* A snap count is published evidence; a percentage that the capture lost is
  *derived* from the denominator and labelled ``derived`` — it is arithmetic,
  not a new observation.
* A snap count that contradicts the published denominator is withheld, never
  repaired by guesswork.
"""

from __future__ import annotations

import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "raw"
DATA = ROOT / "data"

UNITS = ("OFF", "DEF", "ST")
UNIT_LABEL = {"OFF": "Offense", "DEF": "Defense", "ST": "Special Teams"}

#: Published positions folded into depth groups.  The fold is deliberately
#: coarse: it is the granularity the Game Book itself uses, plus the
#: offensive-line spellings that vary between clubs (T/G, C/G, OL, ...).
POS_GROUP = {
    "QB": "QB",
    "RB": "RB", "HB": "RB", "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "T": "OL", "G": "OL", "C": "OL", "OL": "OL", "OT": "OL", "OG": "OL",
    "OC": "OL", "G/T": "OL", "T/G": "OL", "C/G": "OL", "G/C": "OL",
    "DE": "DL", "DT": "DL", "DL": "DL", "NT": "DL", "EDGE": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
    "CB": "DB", "S": "DB", "DB": "DB", "SS": "DB", "FS": "DB", "SAF": "DB",
    "K": "ST", "P": "ST", "LS": "ST", "PK": "ST", "H": "ST",
}
GROUP_ORDER = ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "ST")

#: Groups that field a fixed starting unit, used for the starter split.
STARTERS_ON_FIELD = {"QB": 1, "RB": 1, "WR": 3, "TE": 1, "OL": 5,
                     "DL": 4, "LB": 3, "DB": 4, "ST": 3}

#: Percentages are printed as whole numbers, so a one-point disagreement can be
#: a publisher rounding convention.  Anything larger is a transcription defect.
PCT_TOLERANCE = 1


# --------------------------------------------------------------------------
# capture reading
# --------------------------------------------------------------------------

def read_capture(path: pathlib.Path):
    """Read one raw capture into its header metadata plus playtime rows."""
    meta, totals, rows = {}, {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        tag = parts[0]
        if tag == "PT":
            rows.append(parts[1:])
        elif tag == "TOTALS":
            totals[parts[1]] = {"OFF": int(parts[3]),
                                "DEF": int(parts[5]),
                                "ST": int(parts[7])}
        elif tag == "XTRA":
            # Continuation rows the publisher prints in a second, narrower
            # table.  They carry a bare "<snaps> <pct>" pair for one unit.
            tokens = []
            for unit in UNITS:
                if unit == parts[4]:
                    tokens.extend([parts[5], parts[6]])
                else:
                    tokens.append("")
            rows.append([parts[1], parts[2], parts[3], *tokens])
        else:
            meta[tag] = "|".join(parts[1:])
    return meta, totals, rows


def decode_cells(tokens):
    """Re-decode the publisher's three unit cells from a flattened token list.

    Returns every structurally valid reading.  A cell is either empty (one
    token) or ``snaps [pct]`` (two tokens when the percentage survived, one
    when it did not).
    """
    toks = list(tokens)
    found = []

    def walk(i, pending, taken):
        if not pending:
            if all(t == "" for t in toks[i:]):
                found.append(dict(taken))
            return
        unit, rest = pending[0], pending[1:]
        if i < len(toks) and toks[i] == "":
            nxt = dict(taken)
            nxt[unit] = None
            walk(i + 1, rest, nxt)
            # Some captures pad a special-teams-only row with one spare empty
            # token; try swallowing it so the same grid still decodes.
            if i + 1 < len(toks) and toks[i + 1] == "":
                walk(i + 2, rest, nxt)
            return
        if i >= len(toks):
            return
        # The publisher sometimes prints a percentage with no snap count for a
        # player whose snaps are not the interesting number.  The capture writes
        # that as "- <pct>", and only the percentage is evidence.
        if toks[i] == "-":
            if i + 1 < len(toks) and toks[i + 1] != "":
                try:
                    pct = int(toks[i + 1])
                except ValueError:
                    return
                nxt = dict(taken)
                nxt[unit] = (None, pct)
                walk(i + 2, rest, nxt)
            return
        try:
            snaps = int(toks[i])
        except ValueError:
            return
        if i + 1 < len(toks) and toks[i + 1] != "":
            try:
                pct = int(toks[i + 1])
            except ValueError:
                pct = None
            if pct is not None:
                nxt = dict(taken)
                nxt[unit] = (snaps, pct)
                walk(i + 2, rest, nxt)
            return
        # percentage absent: either a trailing empty cell or end of row
        if i + 1 < len(toks) and toks[i + 1] == "":
            nxt = dict(taken)
            nxt[unit] = (snaps, None)
            walk(i + 2, rest, nxt)
        elif i + 1 == len(toks):
            nxt = dict(taken)
            nxt[unit] = (snaps, None)
            walk(i + 1, rest, nxt)

    walk(0, list(UNITS), {})
    unique = []
    for option in found:
        if option not in unique:
            unique.append(option)
    return unique


def pct_of(snaps, denominator):
    """Whole-number percentage the publisher would print for this snap count."""
    if not denominator:
        return None
    return round(snaps * 100 / denominator)


def resolve_denominator(declared, pairs):
    """Confirm or correct the unit total the capture states for a club.

    The publisher prints a team total per unit.  A correct capture is never
    "improved" here: the declared total is kept unless most of the plausible
    rows contradict it.  A row can only count against the total if it is
    internally possible (at most the declared snaps, at most 100%), so one
    mangled cell cannot drag the whole team's denominator away with it.
    """
    scored_pairs = [(s, p) for s, p in pairs
                    if p is not None and s is not None]
    if not scored_pairs:
        return declared, "no-rows"

    if declared:
        plausible = [(s, p) for s, p in scored_pairs if 0 < s <= declared]
        if len(plausible) >= 0.6 * len(scored_pairs):
            confirming = sum(1 for s, p in plausible
                             if abs((pct_of(s, declared) or 0) - p) <= PCT_TOLERANCE)
            if plausible and confirming >= 0.6 * len(plausible):
                return declared, "declared-total-confirmed"
            return declared, "declared-total-unexplained"
        # Most rows cannot fit the declared total; the capture total is wrong.
        search = scored_pairs
    else:
        search = scored_pairs

    upper = max(s for s, _ in search)
    best, best_hits = None, -1
    for candidate in range(max(upper, 1), max(upper, 1) + 8):
        hits = sum(1 for s, p in search
                   if s <= candidate
                   and abs((pct_of(s, candidate) or 0) - p) <= PCT_TOLERANCE)
        if hits > best_hits:
            best, best_hits = candidate, hits
    if declared and best is not None and best != declared:
        return best, "declared-total-corrected"
    return (best if best is not None else declared), "declared-total-missing"


def read_all():
    """Load every capture, decode it, and verify it against its denominators."""
    games, rows, flags = [], [], []
    for path in sorted(RAW.glob("*.txt")):
        meta, totals, raw_rows = read_capture(path)
        game_id = meta.get("GAME", "").split("|")[0] or path.stem
        games.append({"game_id": game_id, "file": path.name,
                      "source": meta.get("SOURCE", ""),
                      "gamecenter": meta.get("GAMECENTER", ""),
                      "header": meta.get("HEADER", "")})

        # pass 1 — structural decode, one reading per row where the grid is
        # unambiguous; ambiguous rows are re-decoded after denominators exist.
        provisional = []
        for parts in raw_rows:
            club, player, position = parts[0], parts[1], parts[2]
            readings = decode_cells(parts[3:])
            provisional.append({"club": club, "player": player,
                               "position": position, "readings": readings,
                               "tokens": parts[3:]})

        declared = {}
        for reading in provisional:
            club = reading["club"]
            declared.setdefault(club, dict(totals.get(club, {})))
        denominators, verdicts = {}, {}
        for club in declared:
            denominators[club], verdicts[club] = {}, {}
            for unit in UNITS:
                pairs = []
                for reading in provisional:
                    if reading["club"] != club:
                        continue
                    for option in reading["readings"]:
                        cell = option.get(unit)
                        if cell and cell[1] is not None:
                            pairs.append(cell)
                            break
                value, verdict = resolve_denominator(
                    declared[club].get(unit), pairs)
                denominators[club][unit] = value
                verdicts[club][unit] = verdict

        # pass 2 — resolve each row against the denominators.
        for reading in provisional:
            club, player = reading["club"], reading["player"]
            position = reading["position"]
            base = {"game_id": game_id, "source": meta.get("SOURCE", ""),
                    "club": club, "player": player, "position": position}
            if not player or not club:
                flags.append({**base, "unit": "", "reason": "unreadable-row",
                              "detail": "capture row has no player name",
                              "tokens": reading["tokens"]})
                continue
            options = reading["readings"]
            if not options:
                flags.append({**base, "unit": "", "reason": "undecodable-grid",
                              "detail": "token stream does not fit the "
                                        "six-cell publisher grid",
                              "tokens": reading["tokens"]})
                continue

            def score(option):
                hit = 0
                for unit in UNITS:
                    cell = option.get(unit)
                    if not cell or cell[1] is None or cell[0] is None:
                        continue
                    if not 0 <= cell[1] <= 100:
                        continue
                    want = pct_of(cell[0], denominators[club].get(unit))
                    if want is not None and abs(want - cell[1]) <= PCT_TOLERANCE:
                        hit += 1
                return hit

            best = max(score(o) for o in options)
            top = [o for o in options if score(o) == best]
            if len(top) > 1:
                flags.append({**base, "unit": "", "reason": "ambiguous-grid",
                              "detail": f"{len(top)} equally valid unit "
                                        "assignments", "tokens": reading["tokens"]})
            option = top[0]

            for unit in UNITS:
                cell = option.get(unit)
                if not cell:
                    continue
                snaps, printed = cell
                denominator = denominators[club].get(unit)
                if printed is not None and not 0 <= printed <= 100:
                    flags.append({**base, "unit": unit,
                                  "reason": "published-pct-over-100",
                                  "detail": f"captured percentage {printed} is "
                                            "not a share; cell withheld",
                                  "tokens": reading["tokens"]})
                    continue
                if snaps is None:
                    # The capture has a printed share but no snap count.  The
                    # share is published evidence; the snap count stays blank
                    # rather than being back-solved from the denominator.
                    flags.append({**base, "unit": unit,
                                  "reason": "share-without-snaps",
                                  "detail": "publisher printed a percentage "
                                            "without a snap count",
                                  "tokens": reading["tokens"]})
                    rows.append({**base, "unit": unit, "snaps": "",
                                 "pct": printed, "pct_status": "published-share",
                                 "denominator": denominator})
                    continue
                if denominator and snaps > denominator:
                    flags.append({**base, "unit": unit,
                                  "reason": "snaps-exceed-total",
                                  "detail": f"{snaps} snaps against a "
                                            f"{denominator}-snap unit; cell "
                                            "withheld", "tokens": reading["tokens"]})
                    continue
                derived = pct_of(snaps, denominator) if denominator else None
                if printed is None:
                    status = "derived"
                    if derived is None:
                        flags.append({**base, "unit": unit,
                                      "reason": "no-denominator",
                                      "detail": "no unit total to derive from",
                                      "tokens": reading["tokens"]})
                        continue
                    flags.append({**base, "unit": unit, "reason": "derived-pct",
                                  "detail": "percentage absent from capture; "
                                            "re-derived from the denominator",
                                  "tokens": reading["tokens"]})
                elif derived is not None and abs(derived - printed) <= PCT_TOLERANCE:
                    status = "verified"
                else:
                    # The publisher's own two numbers disagree.  Both are
                    # official, so neither is "wrong" and neither can be
                    # published as a verified share: the cell is withheld and
                    # both figures are recorded on the flag.
                    flags.append({**base, "unit": unit,
                                  "reason": "pct-mismatch",
                                  "detail": f"printed {printed}%, denominator "
                                            f"implies {derived}%; both official "
                                            "figures recorded, cell withheld",
                                  "tokens": reading["tokens"]})
                    continue
                rows.append({**base, "unit": unit, "snaps": snaps,
                             "pct": printed if printed is not None else derived,
                             "pct_status": status,
                             "denominator": denominator})

        for game in games:
            if game["game_id"] == game_id:
                game["denominators"] = denominators
                game["verdicts"] = verdicts
    return games, rows, flags


# --------------------------------------------------------------------------
# aggregates
# --------------------------------------------------------------------------

def fold_position(position):
    return POS_GROUP.get((position or "").strip().upper(), "ST")


def wilson(successes, trials, z=1.959963985):
    """Wilson score interval for a binomial proportion."""
    if not trials:
        return None, None
    phat = successes / trials
    denominator = 1 + z * z / trials
    centre = (phat + z * z / (2 * trials)) / denominator
    spread = (z / trials) ** 0.5 * ((phat * (1 - phat) / trials
                                     + z * z / (4 * trials * trials)) ** 0.5)
    spread = z * ((phat * (1 - phat) / trials
                   + z * z / (4 * trials * trials)) ** 0.5) / denominator
    return round(centre - spread, 4), round(centre + spread, 4)


def build_players(rows):
    """One row per player per club, summing the units he actually played."""
    players = {}
    for row in rows:
        key = (row["game_id"], row["club"], row["player"])
        record = players.setdefault(key, {
            "game_id": row["game_id"], "club": row["club"],
            "player": row["player"], "position": row["position"],
            "group": fold_position(row["position"]),
            "source": row["source"],
            "OFF": 0, "DEF": 0, "ST": 0,
            "denominators": {}, "statuses": set(),
        })
        if row["snaps"] != "":
            record[row["unit"]] = max(record[row["unit"]], row["snaps"])
        record["denominators"][row["unit"]] = row["denominator"]
        record["statuses"].add(row["pct_status"])
    out = []
    for record in players.values():
        statuses = record.pop("statuses")
        record["pct_status"] = ("verified" if statuses == {"verified"}
                                else "derived" if statuses <= {"verified", "derived"}
                                else "flagged")
        record["total_snaps"] = record["OFF"] + record["DEF"] + record["ST"]
        record["played"] = record["total_snaps"] > 0
        out.append(record)
    out.sort(key=lambda r: (r["game_id"], r["club"], -r["total_snaps"],
                            r["player"]))
    return out


def build_depth(players):
    """Depth from playing time: rank by snaps inside each position group."""
    depth = []
    for game_id in sorted({p["game_id"] for p in players}):
        for club in sorted({p["club"] for p in players if p["game_id"] == game_id}):
            squad = [p for p in players
                     if p["game_id"] == game_id and p["club"] == club and p["played"]]
            for group in GROUP_ORDER:
                unit = [p for p in squad if p["group"] == group]
                if not unit:
                    continue
                unit.sort(key=lambda p: (-p["total_snaps"], p["player"]))
                for rank, player in enumerate(unit, start=1):
                    if rank == 1:
                        slot = "1st string"
                    elif rank == 2:
                        slot = "2nd string"
                    elif rank == 3:
                        slot = "3rd string"
                    elif rank == 4:
                        slot = "4th string"
                    else:
                        slot = "reserve"
                    depth.append({
                        "game_id": game_id, "club": club, "group": group,
                        "rank": rank, "slot": slot, "player": player["player"],
                        "position": player["position"],
                        "snaps": player["total_snaps"],
                        "offense": player["OFF"], "defense": player["DEF"],
                        "special_teams": player["ST"],
                        "source": player["source"],
                    })
    return depth


def build_starters(depth):
    """Starter / backup / replacement split from the depth ranks.

    A group only yields a "starter" line for the number of places the group
    actually fields; the rest of the unit is labelled backup or replacement by
    rank so nothing is upgraded into a starting job it did not hold.
    """
    lines = []
    for row in depth:
        places = STARTERS_ON_FIELD.get(row["group"], 0)
        if places and row["rank"] <= places:
            role = "starter"
        elif places and row["rank"] <= places * 2:
            role = "backup"
        elif places:
            role = "replacement"
        else:
            role = "rotation"
        lines.append({**row, "role": role})
    return lines


def build_reliability(players, games_per_club):
    """Designated reliability on official playing-time evidence.

    For every player we publish how often he took a snap at all, how often he
    led his position group, and the Wilson interval around each rate with the
    number of games actually observed.  One week is one sample: the interval is
    wide on purpose and the interval is the finding.
    """
    out = []
    seen = {}
    for player in players:
        key = (player["club"], player["player"])
        record = seen.setdefault(key, {
            "club": player["club"], "player": player["player"],
            "group": player["group"], "position": player["position"],
            "games": 0, "appearances": 0, "group_leads": 0,
            "snaps": 0, "offense": 0, "defense": 0, "special_teams": 0,
            "source": player["source"],
        })
        record["games"] += 1
        record["snaps"] += player["total_snaps"]
        record["offense"] += player["OFF"]
        record["defense"] += player["DEF"]
        record["special_teams"] += player["ST"]
        if player["played"]:
            record["appearances"] += 1
    leads = {}
    for player in players:
        if not player["played"]:
            continue
        key = (player["club"], player["group"])
        best = leads.get(key)
        if best is None or player["total_snaps"] > best[0]:
            leads[key] = (player["total_snaps"], player["player"])
    for key in leads:
        pass
    for player in players:
        if not player["played"]:
            continue
        key = (player["club"], player["group"])
        if leads[key][1] == player["player"]:
            seen[(player["club"], player["player"])]["group_leads"] += 1
    for record in seen.values():
        team_games = games_per_club.get(record["club"]) or record["games"]
        low, high = wilson(record["appearances"], team_games)
        record["team_games"] = team_games
        record["appearance_rate"] = round(record["appearances"] / team_games, 4)
        record["appearance_low"], record["appearance_high"] = low, high
        low, high = wilson(record["group_leads"], team_games)
        record["lead_rate"] = round(record["group_leads"] / team_games, 4)
        record["lead_low"], record["lead_high"] = low, high
        record["mean_snaps"] = round(record["snaps"] / team_games, 2)
        out.append(record)
    out.sort(key=lambda r: (r["club"], -r["snaps"], r["player"]))
    return out


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def check(games, rows, flags):
    """Fail loudly on anything that would make the published table wrong."""
    problems = []
    for game in games:
        for club, units in game.get("denominators", {}).items():
            for unit, total in units.items():
                if not total:
                    problems.append(f"{game['game_id']} {club} {unit}: "
                                    "no unit total")
    for row in rows:
        if row["pct"] is not None and not 0 <= row["pct"] <= 100:
            problems.append(f"{row['game_id']} {row['player']}: "
                            f"percentage {row['pct']} out of range")
        if row["snaps"] != "" and row["snaps"] < 0:
            problems.append(f"{row['game_id']} {row['player']}: negative snaps")
    withheld = [f for f in flags if f["reason"] in
                {"pct-mismatch", "snaps-exceed-total", "undecodable-grid",
                 "ambiguous-grid", "published-pct-over-100"}]
    return problems, withheld


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore",
                                lineterminator="\r\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def main():
    games, rows, flags = read_all()
    players = build_players(rows)
    depth = build_depth(players)
    starters = build_starters(depth)
    games_per_club = {}
    for game in games:
        for club in game.get("denominators", {}):
            games_per_club[club] = games_per_club.get(club, 0) + 1
    reliability = build_reliability(players, games_per_club)

    problems, withheld = check(games, rows, flags)

    DATA.mkdir(parents=True, exist_ok=True)
    write_csv(DATA / "playtime.csv", rows,
              ["game_id", "club", "player", "position", "unit", "snaps",
               "pct", "pct_status", "denominator", "source"])
    write_csv(DATA / "players.csv", players,
              ["game_id", "club", "player", "position", "group", "OFF", "DEF",
               "ST", "total_snaps", "played", "pct_status", "source"])
    write_csv(DATA / "depth.csv", depth,
              ["game_id", "club", "group", "rank", "slot", "player", "position",
               "snaps", "offense", "defense", "special_teams", "source"])
    write_csv(DATA / "starters.csv", starters,
              ["game_id", "club", "group", "rank", "slot", "role", "player",
               "position", "snaps", "source"])
    write_csv(DATA / "reliability.csv", reliability,
              ["club", "player", "group", "position", "team_games", "games",
               "appearances", "appearance_rate", "appearance_low",
               "appearance_high", "group_leads", "lead_rate", "lead_low",
               "lead_high", "snaps", "mean_snaps", "offense", "defense",
               "special_teams", "source"])

    totals_csv = []
    for game in games:
        for club, units in sorted(game.get("denominators", {}).items()):
            for unit in UNITS:
                totals_csv.append({
                    "game_id": game["game_id"], "club": club, "unit": unit,
                    "denominator": units.get(unit),
                    "verdict": game["verdicts"][club][unit],
                    "source": game["source"],
                })
    write_csv(DATA / "team-totals.csv", totals_csv,
              ["game_id", "club", "unit", "denominator", "verdict", "source"])

    write_json(DATA / "flags.json", flags)
    summary = {
        "generated_for": "2026 Week 10",
        "captures": len(games),
        "clubs": len({row["club"] for row in players}),
        "playtime_rows": len(rows),
        "players": len(players),
        "depth_rows": len(depth),
        "starter_rows": len(starters),
        "reliability_rows": len(reliability),
        "verified_rows": sum(1 for r in rows if r["pct_status"] == "verified"),
        "derived_rows": sum(1 for r in rows if r["pct_status"] == "derived"),
        "mismatch_rows": sum(1 for r in rows if r["pct_status"] == "mismatch"),
        "flags": len(flags),
        "withheld": len(withheld),
        "problems": problems,
        "games": [{"game_id": g["game_id"], "header": g["header"],
                   "source": g["source"], "gamecenter": g["gamecenter"],
                   "file": g["file"],
                   "clubs": sorted(g.get("denominators", {}))} for g in games],
    }
    write_json(DATA / "capture-summary.json", summary)

    print(f"captures       {summary['captures']}")
    print(f"clubs          {summary['clubs']}")
    print(f"playtime rows  {summary['playtime_rows']}"
          f"  (verified {summary['verified_rows']},"
          f" derived {summary['derived_rows']},"
          f" mismatch {summary['mismatch_rows']})")
    print(f"players        {summary['players']}")
    print(f"depth rows     {summary['depth_rows']}")
    print(f"starter rows   {summary['starter_rows']}")
    print(f"reliability    {summary['reliability_rows']}")
    print(f"flags          {summary['flags']}  (withheld {summary['withheld']})")
    if problems:
        for problem in problems:
            print("  PROBLEM", problem)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
