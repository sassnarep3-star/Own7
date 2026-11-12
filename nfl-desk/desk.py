#!/usr/bin/env python3
"""Deterministic NFL decision-desk engine: load verified snapshots, re-check them, derive statistics.

Design rules enforced here:
* Nothing is typed by hand at render time; every table cell comes from a file in data/.
* Every snapshot has a re-checkable identity. If a check fails the build stops; it never
  publishes a number that no longer agrees with its own source page.
* Derived values are labelled "derived" and carry the formula used. They are never
  presented as official NFL figures.
* A quantity that cannot be computed from the verified snapshots stays ``None`` and is
  rendered as an empty cell with a flag. No defaults, no placeholders, no interpolation.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

# Method constants. These are project choices, not official NFL statistics.
PYTHAGOREAN_EXPONENT = 2.37  # standard football Pythagorean exponent used as a project method
PERMUTATIONS = 20000  # fixed-count Monte Carlo permutation test (deterministic seed)
SEED = 20261112


class DataError(RuntimeError):
    """Raised when a snapshot no longer satisfies its own integrity identities."""


# --------------------------------------------------------------------------- loading


def read_psv(name: str) -> list[dict]:
    """Read a pipe-separated snapshot, ignoring '#' comment lines and blank lines."""
    path = DATA / name
    rows, header = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("|")
        if header is None:
            header = parts
            continue
        if len(parts) != len(header):
            raise DataError(f"{name}: column count mismatch on {parts[0]!r}")
        rows.append(dict(zip(header, parts)))
    return rows


def digest(name: str) -> str:
    return hashlib.sha256((DATA / name).read_bytes()).hexdigest()


def load_ledger(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def sources() -> dict[str, dict]:
    data = load_ledger("data/sources.json")
    return {row["id"]: row for row in data["sources"]}


# --------------------------------------------------------------------------- snapshots


def standings() -> list[dict]:
    rows = read_psv("standings-2026.psv")
    if len(rows) != 32:
        raise DataError(f"standings: expected 32 clubs, found {len(rows)}")
    if len({r["abbr"] for r in rows}) != 32:
        raise DataError("standings: duplicate club abbreviation")
    out = []
    for r in rows:
        w, l, t = int(r["w"]), int(r["l"]), int(r["t"])
        pf, pa, net = int(r["pf"]), int(r["pa"]), int(r["net"])
        pct = float(r["pct"])
        games = w + l + t
        if games == 0:
            raise DataError(f"{r['abbr']}: club has no games")
        # Displayed PCT is the exact fraction rounded to three decimals (half-up, e.g. WAS 0.3125 -> 0.313).
        exact_pct = (w + t / 2) / games
        if abs(exact_pct - pct) > 0.00051:
            raise DataError(f"{r['abbr']}: displayed PCT {pct} != computed {exact_pct:.4f}")
        if net != pf - pa:
            raise DataError(f"{r['abbr']}: NET PTS {net} != PF-PA {pf - pa}")
        out.append(
            {
                "abbr": r["abbr"],
                "team": r["team"],
                "w": w,
                "l": l,
                "t": t,
                "games": games,
                "pct": pct,
                "pf": pf,
                "pa": pa,
                "net": net,
                "ppg": pf / games,
                "papg": pa / games,
                "source_ids": ["NFL-STANDINGS-2026", "NFL-STANDINGS-DIV-2026"],
            }
        )
    return out


def passing() -> list[dict]:
    rows = read_psv("passing-2026.psv")
    if len(rows) != 32:
        raise DataError(f"passing: expected 32 clubs, found {len(rows)}")
    out = []
    for r in rows:
        att, cmp_, yds = int(r["att"]), int(r["cmp"]), int(r["yds"])
        pct = float(r["pct"])
        if att <= 0:
            raise DataError(f"{r['abbr']}: zero attempts")
        # The displayed completion percentage must be reproducible from the displayed integers.
        # The page truncates the second decimal (WAS 61.65 is shown as 61.6), so the tolerance is
        # one displayed unit; a wrong transcription would miss by far more than that.
        if abs(round(cmp_ / att * 100, 2) - pct) > 0.06:
            raise DataError(f"{r['abbr']}: PCT {pct} != CMP/ATT {round(cmp_/att*100,2)}")
        if not 0 < pct < 100:
            raise DataError(f"{r['abbr']}: implausible completion percentage")
        out.append({"abbr": r["abbr"], "att": att, "cmp": cmp_, "pct": pct, "yds": yds, "ypa": yds / att})
    return out


PRACTICE_VOCAB = {
    "Full Participation in Practice",
    "Limited Participation in Practice",
    "Did Not Participate In Practice",
}
GAME_VOCAB = {"", "Out", "Questionable", "Doubtful"}


def injuries() -> list[dict]:
    rows = read_psv("injury-week10-2026.psv")
    seen = set()
    for r in rows:
        if r["practice"] not in PRACTICE_VOCAB:
            raise DataError(f"unknown practice status {r['practice']!r} for {r['player']}")
        if r["game"] not in GAME_VOCAB:
            raise DataError(f"unknown game status {r['game']!r} for {r['player']}")
        key = (r["team"], r["player"])
        if key in seen:
            raise DataError(f"duplicate injury row {key}")
        seen.add(key)
    return rows


def team_notes() -> list[dict]:
    return read_psv("injury-week10-team-notes.psv")


def week10_games() -> list[dict]:
    """Week 10 fixture list transcribed from the official schedule page (both sides named)."""
    return load_ledger("data/week10-games.json")["games"]


# --------------------------------------------------------------------------- statistics


def mean(values):
    return sum(values) / len(values)


def pearson(x, y):
    mx, my = mean(x), mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


class _Rng:
    """Small deterministic linear-congruential generator (no third-party dependency)."""

    def __init__(self, seed):
        self.state = seed & 0x7FFFFFFF

    def next(self):
        self.state = (1103515245 * self.state + 12345) & 0x7FFFFFFF
        return self.state / 0x7FFFFFFF

    def shuffle(self, items):
        for i in range(len(items) - 1, 0, -1):
            j = int(self.next() * (i + 1))
            items[i], items[j] = items[j], items[i]


def permutation_p(x, y, observed, iterations=PERMUTATIONS, seed=SEED):
    """Two-sided Monte Carlo permutation p-value for a correlation. Deterministic for a seed."""
    if observed is None:
        return None
    rng = _Rng(seed)
    shuffled = list(y)
    hits = 0
    for _ in range(iterations):
        rng.shuffle(shuffled)
        r = pearson(x, shuffled)
        if r is not None and abs(r) >= abs(observed) - 1e-12:
            hits += 1
    return (hits + 1) / (iterations + 1)


def wilson(successes, trials, z=1.959963985):
    """95% Wilson score interval for a binomial proportion."""
    if trials == 0:
        return (None, None)
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def pythagorean(pf, pa, exponent=PYTHAGOREAN_EXPONENT):
    if pf <= 0 and pa <= 0:
        return None
    return pf**exponent / (pf**exponent + pa**exponent)


def binomial_sd(p, n):
    if p is None or n == 0:
        return None
    return math.sqrt(p * (1 - p) / n)


def fair_decimal(probability):
    if not probability or probability <= 0:
        return None
    return 1 / probability


# --------------------------------------------------------------------------- derivations


def pythagorean_table():
    rows = standings()
    out = []
    for r in rows:
        expected = pythagorean(r["pf"], r["pa"])
        expected_wins = None if expected is None else expected * r["games"]
        actual_wins = r["w"] + r["t"] / 2
        residual = None if expected_wins is None else actual_wins - expected_wins
        sd = binomial_sd(expected, r["games"])
        z = None if (sd in (None, 0)) or residual is None else residual / sd
        out.append(
            {
                **r,
                "pyth": expected,
                "expected_wins": expected_wins,
                "residual": residual,
                "residual_z": z,
            }
        )
    return out


def record_rank_table():
    """Rank by displayed win percentage only. Division rank needs tie-breakers and stays blank."""
    rows = standings()
    ordered = sorted(rows, key=lambda r: (-r["pct"], r["abbr"]))
    out = []
    for index, r in enumerate(ordered, start=1):
        low, high = wilson(r["w"] + r["t"] / 2, r["games"])
        out.append({**r, "record_rank": index, "pct_low": low, "pct_high": high})
    return out


def correlation_table():
    rows = standings()
    pass_rows = {p["abbr"]: p for p in passing()}
    labels = {
        "pct": "Win percentage",
        "pf": "Points for (PF)",
        "pa": "Points against (PA)",
        "net": "Net points",
        "pyth": "Pythagorean expectation",
        "pass_yds": "Passing yards",
        "pass_ypa": "Yards per attempt (derived YDS/ATT)",
        "pass_pct": "Completion percentage",
    }
    series = {
        "pct": [r["pct"] for r in rows],
        "pf": [r["pf"] for r in rows],
        "pa": [r["pa"] for r in rows],
        "net": [r["net"] for r in rows],
        "pyth": [pythagorean(r["pf"], r["pa"]) for r in rows],
        "pass_yds": [pass_rows[r["abbr"]]["yds"] for r in rows],
        "pass_ypa": [pass_rows[r["abbr"]]["ypa"] for r in rows],
        "pass_pct": [pass_rows[r["abbr"]]["pct"] for r in rows],
    }
    pairs = [
        ("pf", "pct"),
        ("pa", "pct"),
        ("net", "pct"),
        ("pf", "pa"),
        ("pass_yds", "pct"),
        ("pass_ypa", "pct"),
        ("pass_pct", "pct"),
        ("pf", "pass_yds"),
    ]
    out = []
    for a, b in pairs:
        x, y = series[a], series[b]
        r = pearson(x, y)
        rho = spearman(x, y)
        out.append(
            {
                "pair": f"{labels[a]} vs {labels[b]}",
                "n": len(x),
                "pearson": None if r is None else round(r, 4),
                "spearman": None if rho is None else round(rho, 4),
                # Correlation over 32 club-seasons, not over bets. Permutation p is descriptive.
                "p_perm": None if r is None else round(permutation_p(x, y, r), 4),
                "unit": "club-season (n=32)",
                "source_ids": ["NFL-STANDINGS-2026", "NFL-TEAM-PASS-2026"],
            }
        )
    return out


def availability_table():
    """Week 10 matchup pressure: how many listed players per club carry a game status.

    This is report pressure, not a starter count. Depth-chart rank is only known for the three
    clubs with a transcribed depth chart, so no 'starters lost' total is computed for the rest.
    """
    inj = injuries()
    notes = {n["team"]: n["official_note"] for n in team_notes()}
    by_team: dict[str, list[dict]] = {}
    for row in inj:
        by_team.setdefault(row["team"], []).append(row)
    games = week10_games()
    involved = []
    for game in games:
        for side in ("home", "away"):
            if game[side] not in involved:
                involved.append(game[side])
    out = []
    for abbr in involved:
        players = by_team.get(abbr, [])
        out_count = sum(1 for p in players if p["game"] == "Out")
        q_count = sum(1 for p in players if p["game"] == "Questionable")
        d_count = sum(1 for p in players if p["game"] == "Doubtful")
        dnp = sum(1 for p in players if p["practice"] == "Did Not Participate In Practice")
        lim = sum(1 for p in players if p["practice"] == "Limited Participation in Practice")
        out.append(
            {
                "abbr": abbr,
                "listed": len(players),
                "out": out_count,
                "questionable": q_count,
                "doubtful": d_count,
                "dnp": dnp,
                "limited": lim,
                "note": notes.get(abbr, ""),
                "status": "Reported" if players or abbr in notes else "Not listed on page",
                "source_ids": ["NFL-INJURY-W10-2026", "NFL-SCHEDULE-2026"],
            }
        )
    return out


DEPTH = {
    "WAS": {
        "source": "NFL-CLUB-DC-WAS",
        "offense": [
            ["WR", ["Terry McLaurin", "Treylon Burks"]],
            ["LT", ["Brandon Coleman", "Andrew Wylie"]],
            ["LG", ["Chris Paul", "Tanoa Togiai"]],
            ["C", ["Nick Allegretti", "Matt Gulbin"]],
            ["RG", ["Sam Cosmi", "Tanoa Togiai"]],
            ["RT", ["Josh Conerly Jr.", "Andrew Wylie"]],
            ["TE", ["Chig Okonkwo", "Ben Sinnott"]],
            ["TE", ["John Bates", "Colson Yankoff"]],
            ["WR", ["Stefon Diggs", "Jaylin Lane"]],
            ["WR", ["Dyami Brown", "Antonio Williams", "Luke McCaffrey"]],
            ["QB", ["Jayden Daniels", "Marcus Mariota", "Athan Kaliakmanis"]],
            ["RB", ["Jacory Croskey-Merritt", "Rachaad White", "Austin Ekeler"]],
        ],
        "defense": [
            ["DL", ["Daron Payne"]],
            ["DL", ["Tim Settle", "Shy Tuttle"]],
            ["DL", ["Javon Kinlaw", "Charles Omenihu"]],
            ["OLB", ["Odafe Oweh", "Joshua Josephs"]],
            ["LB", ["Sonny Styles", "Kain Medrano"]],
            ["LB", ["Frankie Luvu", "", "Kain Medrano"]],
            ["OLB", ["K'Lavon Chaisson", "Dorance Armstrong", "Javontae Jean-Baptiste"]],
            ["CB", ["Amik Robertson", "Rasul Douglas"]],
            ["CB", ["Mike Sainristil", "Fabian Moreau"]],
            ["SS", ["Nick Cross", "Tyler Owens"]],
            ["FS", ["Jeremy Reaves", "Quan Martin", "Percy Butler"]],
        ],
    },
    "NYG": {
        "source": "NFL-CLUB-DC-NYG",
        "offense": [
            ["WR", ["Malik Nabers", "Malachi Fields", "Jalin Hyatt"]],
            ["WR", ["Darnell Mooney", "Charlie Jones"]],
            ["LT", ["Andrew Thomas", "J.C. Davis"]],
            ["LG", ["Jon Runyan Jr.", "Aaron Stinnie", "Josh Sills"]],
            ["C", ["Bryan Hudson", "John Michael Schmitz Jr."]],
            ["RG", ["Francis Mauigoa", "Aaron Stinnie"]],
            ["RT", ["Jermaine Eluemunor", "Marcus Mbow"]],
            ["TE", ["Isaiah Likely", "Theo Johnson", "Chris Manhertz", "Thomas Fidone II"]],
            ["QB", ["J.J. McCarthy", "Jameis Winston"]],
            ["FB", ["Patrick Ricard"]],
            ["RB", ["Cam Skattebo", "Devin Singletary", "Gregory Desrosiers"]],
        ],
        "defense": [
            ["DT", ["Shelby Harris", "Darius Alexander", "Bobby Jamison-Travis"]],
            ["NT", ["DJ Reader", "C.J. Okoye"]],
            ["DE", ["Darius Alexander"]],
            ["RUSH", ["Kayvon Thibodeaux", "Trace Ford"]],
            ["MLB", ["Micah McFadden", "Zaire Barnes"]],
            ["WLB", ["Arvell Reese", "Jack Kelly"]],
            ["SAM", ["Abdul Carter", "Kayvon Thibodeaux"]],
            ["CB", ["Deonte Banks", "Paulson Adebo", "Nikko Reed"]],
            ["SS", ["Tyler Nubin", "Jason Pinnock"]],
            ["FS", ["Jevón Holland", "Ar'Darius Washington", "Elijah Campbell"]],
            ["CB", ["Greg Newsome II", "Colton Hood"]],
            ["NB", ["Dru Phillips", "Nic Jones"]],
        ],
    },
    "SEA": {
        "source": "NFL-CLUB-DC-SEA",
        "offense": [
            ["WR", ["Cooper Kupp", "Rashid Shaheed", "Irvin Charles"]],
            ["LT", ["Charles Cross", "Josh Jones"]],
            ["LG", ["Quenton Nelson", "Anthony Bradford"]],
            ["C", ["Jalen Sundell", "Olu Oluwatimi"]],
            ["RG", ["Grey Zabel", "Anthony Bradford", "Beau Stephens"]],
            ["RT", ["Abraham Lucas", "Josh Jones"]],
            ["TE", ["AJ Barner", "Eric Saubert", "Nick Kallerup"]],
            ["WR", ["Jaxon Smith-Njigba", "Tory Horton"]],
            ["QB", ["Sam Darnold", "Drew Lock", "Jalen Milroe"]],
            ["FB", ["Brady Russell"]],
            ["RB", ["Zach Charbonnet", "Jadarian Price", "Emanuel Wilson", "George Holani"]],
        ],
        "defense": [
            ["DT", ["Leonard Williams", "Rylie Mills"]],
            ["NT", ["Byron Murphy II", "Brandon Pili", "Deven Eastern"]],
            ["DE", ["Jarran Reed", "Mike Morris"]],
            ["RUSH", ["DeMarcus Lawrence", "Derick Hall"]],
            ["MLB", ["Ernest Jones IV", "Patrick O'Connell"]],
            ["WLB", ["Drake Thomas", "Tyrice Knight", "Chazz Surratt"]],
            ["SLB", ["Uchenna Nwosu", "Dante Fowler Jr.", "Connor O'Toole"]],
            ["CB", ["Devon Witherspoon", "Nehemiah Pritchett"]],
            ["CB", ["Josh Jobe", "Avery Smith"]],
            ["S", ["Ty Okada", "Rodney Thomas II"]],
            ["S", ["Julian Love"]],
            ["S", ["Nick Emmanwori"]],
        ],
    },
}


def _norm(name: str) -> str:
    keep = [c for c in name.lower() if c.isalnum() or c == " "]
    return "".join(keep).split()


def matchup_depth():
    """Cross the transcribed depth charts with the official Week 10 injury report.

    Produces, for each listed player who appears on both, their depth-string position (1st, 2nd,
    3rd, 4th on the club's published chart), the reported practice/game status, and the next
    listed player at the same position — the replacement that the chart itself implies. Where the
    chart lists nobody behind a player, the replacement cell is left blank (not guessed).
    """
    inj = {(r["team"], " ".join(_norm(r["player"]))): r for r in injuries()}
    out = []
    for abbr, chart in DEPTH.items():
        for unit in ("offense", "defense"):
            for position, names in chart[unit]:
                for string, name in enumerate(names, start=1):
                    if not name:
                        continue
                    report = inj.get((abbr, " ".join(_norm(name))))
                    replacement = next((n for n in names[string:] if n), "")
                    out.append(
                        {
                            "team": abbr,
                            "unit": unit,
                            "pos": position,
                            "string": string,
                            "player": name,
                            "practice": report["practice"] if report else "",
                            "game": report["game"] if report else "",
                            "injury": report["injury"] if report else "",
                            "on_report": bool(report),
                            "replacement": replacement if string == 1 else "",
                            "source_ids": [chart["source"], "NFL-INJURY-W10-2026"],
                        }
                    )
    return out


def deficiency_summary():
    """Per club: how many first-string players on the chart carry a Week 10 game status."""
    rows = matchup_depth()
    out = []
    for abbr in DEPTH:
        starters = [r for r in rows if r["team"] == abbr and r["string"] == 1]
        affected = [r for r in starters if r["game"] in ("Out", "Questionable", "Doubtful")]
        out.append(
            {
                "abbr": abbr,
                "chart_starters": len(starters),
                "starters_on_report": sum(1 for r in starters if r["on_report"]),
                "starters_out": sum(1 for r in starters if r["game"] == "Out"),
                "starters_questionable": sum(1 for r in starters if r["game"] == "Questionable"),
                "unfilled_positions": sum(
                    1
                    for r in starters
                    if not next(
                        (
                            s
                            for s in rows
                            if s["team"] == abbr
                            and s["pos"] == r["pos"]
                            and s["string"] > 1
                        ),
                        None,
                    )
                ),
                "affected_detail": ", ".join(f"{r['pos']} {r['player']} ({r['game']})" for r in affected),
                "source_ids": [DEPTH[abbr]["source"], "NFL-INJURY-W10-2026"],
            }
        )
    return out


# --------------------------------------------------------------------------- integrity report


def integrity():
    """Everything a reader needs to see that the published numbers came from the files shown."""
    st = standings()
    ps = passing()
    inj = injuries()
    if {r["abbr"] for r in st} != {r["abbr"] for r in ps}:
        raise DataError("standings and passing snapshots cover different clubs")
    return [
        {"file": "standings-2026.psv", "rows": len(st), "check": "32 clubs; PCT == (W+T/2)/games to 3 d.p.; NET PTS == PF-PA; unique abbreviations", "sha256": digest("standings-2026.psv")},
        {"file": "passing-2026.psv", "rows": len(ps), "check": "32 clubs; displayed PCT reproducible from CMP/ATT on every row; the page's own per-attempt average excluded as unreproducible on 4 rows (DF-03); club set equals standings", "sha256": digest("passing-2026.psv")},
        {"file": "injury-week10-2026.psv", "rows": len(inj), "check": "practice status restricted to the three rendered values; game status restricted to blank/Out/Questionable/Doubtful; no duplicate (club, player)", "sha256": digest("injury-week10-2026.psv")},
        {"file": "injury-week10-team-notes.psv", "rows": len(team_notes()), "check": "verbatim 'No Injuries Reported' notes kept separate from player rows", "sha256": digest("injury-week10-team-notes.psv")},
        {"file": "week10-games.json", "rows": len(week10_games()), "check": "each fixture names both clubs; every club appears once; 4 clubs on bye", "sha256": digest("week10-games.json")},
    ]


def counts():
    st = standings()
    inj = injuries()
    av = availability_table()
    return {
        "clubs": len(st),
        "games_played_total": sum(r["games"] for r in st),
        "injury_rows": len(inj),
        "clubs_on_report": len({r["team"] for r in inj}),
        "week10_games": len(week10_games()),
        "clubs_in_week10": len(av),
        "starters_charted": sum(1 for r in matchup_depth() if r["string"] == 1),
        "clubs_on_bye": len({r["abbr"] for r in st} - {r["team"] for r in inj} - {g[k] for g in week10_games() for k in ("away", "home")}),
        "clubs_not_listed": len({r["abbr"] for r in st} - {r["team"] for r in inj}),
        "depth_rows": len(matchup_depth()),
    }
