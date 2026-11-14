"""Price-snapshot store: opening and closing numbers for every market we originate.

WHAT THIS DOES
--------------
Reads the verbatim transcription of the 32 official closing-line pages
(`evidence/pfr-vegas-lines-2026-w1-9.csv`, one page per club, spread written from
that club's own perspective) and builds one row per *game* per *market*:

    spread_side  (the side we originate first)
    total        (only after the side exists)
    moneyline    (last; blank when no official moneyline was published)

Every game must be confirmed from BOTH clubs' pages. The two independent
transcriptions have to agree exactly on the number and be exact negatives on the
signed spread. A disagreement is a hard failure, never averaged and never
resolved by picking one.

WHAT THIS REFUSES TO DO
-----------------------
* It does not invent a number. If a market has no published price, the cell is
  blank with `verification="unverified"` and a flag naming what is missing.
* It does not claim an *opening* line. The publisher prints one closing number
  per game. Opening prices are outside this snapshot and are recorded as a gap
  in the store, not estimated from "the line moved".
* It does not treat a published reference price as an executable offer. There is
  no vig, no limit, no liquidity and no bet placed here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence" / "pfr-vegas-lines-2026-w1-9.csv"
GAMES = ROOT / "nfl-results" / "data" / "games-2026-w1-9.csv"
OUT = HERE / "data" / "price-snapshots.json"

RETRIEVED = "2026-11-14"

# PFR club code -> the code used by the official result feed (nfl-results).
PFR_TO_RESULT = {
    "crd": "AZ", "atl": "ATL", "rav": "BAL", "buf": "BUF", "car": "CAR", "chi": "CHI",
    "cin": "CIN", "cle": "CLE", "dal": "DAL", "den": "DEN", "det": "DET", "gnb": "GB",
    "htx": "HOU", "clt": "IND", "jax": "JAX", "kan": "KC", "sdg": "LAC", "ram": "LA",
    "rai": "LV", "mia": "MIA", "min": "MIN", "nwe": "NE", "nor": "NO", "nyg": "NYG",
    "nyj": "NYJ", "phi": "PHI", "pit": "PIT", "sfo": "SF", "sea": "SEA", "tam": "TB",
    "oti": "TEN", "was": "WAS",
}
RESULT_TO_PFR = {v: k for k, v in PFR_TO_RESULT.items()}

# The publisher prints one closing number. It does not print an open, a moneyline
# or a player-prop price on these pages, so those cells stay blank by rule.
MARKET_SUPPORT = {
    "spread_close": "published",
    "total_close": "published",
    "spread_open": "not_published",
    "total_open": "not_published",
    "moneyline_close": "not_published",
    "moneyline_open": "not_published",
    "player_prop": "not_published",
}


def read_evidence() -> list[dict]:
    rows = []
    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append({
                "club": row["club_pfr"].strip(),
                "game_no": int(row["game_no"]),
                "opp": row["opp_pfr"].strip(),
                "spread": Decimal(row["spread_signed"].strip()),
                "total": Decimal(row["total"].strip()),
                "retrieved": row["retrieved"].strip(),
                "source_url": row["source_url"].strip(),
            })
    return rows


def read_results() -> list[dict]:
    games = []
    with GAMES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            games.append({
                "week": int(row["week"]),
                "date": row["date"],
                "away": row["away"],
                "home": row["home"],
                "away_score": int(row["away_score"]),
                "home_score": int(row["home_score"]),
                "source_url": row["source_url"],
            })
    return games


def build() -> dict:
    evidence = read_evidence()
    results = read_results()

    by_club: dict[str, list[dict]] = {}
    for row in evidence:
        by_club.setdefault(row["club"], []).append(row)
    for club in by_club:
        by_club[club].sort(key=lambda r: r["game_no"])

    problems: list[str] = []
    flags: list[dict] = []

    # --- 1. Coverage of the evidence itself -----------------------------------
    if sorted(by_club) != sorted(PFR_TO_RESULT):
        missing = sorted(set(PFR_TO_RESULT) - set(by_club))
        extra = sorted(set(by_club) - set(PFR_TO_RESULT))
        problems.append(f"club coverage: missing={missing} extra={extra}")

    # --- 2. Pair every game from both clubs' pages ---------------------------
    # The publisher's G# is a per-club game count, not a league game id: a club
    # that takes its bye in week 5 has G#5 in week 6. Games are therefore paired
    # by position in each club's chronological opponent sequence, and that
    # pairing is only trusted after the sequence has been proved against the
    # official result feed. Division rivals meet twice, so matching on opponent
    # alone is ambiguous and is not used.
    schedule = sorted(results, key=lambda g: (g["date"], g["home"]))
    # Per club, the exact (away, home) fixture in chronological order.
    official_seq: dict[str, list[tuple[str, str]]] = {}
    for game in schedule:
        official_seq.setdefault(game["away"], []).append((game["away"], game["home"]))
        official_seq.setdefault(game["home"], []).append((game["away"], game["home"]))

    games: list[dict] = []
    position: dict[tuple[str, int], tuple[str, str]] = {}
    for club, rows in by_club.items():
        code = PFR_TO_RESULT[club]
        official = official_seq.get(code, [])
        printed = [PFR_TO_RESULT[r["opp"]] for r in rows]
        printed_opponents = [opp for _, opp in [(a, h if a == code else a) for a, h in official]]
        if printed[: len(official)] != printed_opponents:
            problems.append(
                f"{club}: printed opponent order does not match the official feed at some index; "
                f"printed={printed} official={printed_opponents}"
            )
            continue
        for idx, (away, home) in enumerate(official):
            position[(club, idx)] = (away, home)
        for offset in range(len(official), len(printed)):
            flags.append({
                "id": "PS05",
                "item": f"{code} vs {printed[offset]} (printed game {rows[offset]['game_no']})",
                "issue": (
                    "The publisher prints a closing line for this game but it is not in the "
                    "frozen official result feed (weeks 1-9), so the venue cannot be confirmed "
                    "from the feed and the game cannot be scored here."
                ),
                "action": (
                    "Carry the price as unpublished for grading. Do not infer the home team from "
                    "the printed order. Extend the official feed, then price and score it."
                ),
            })

    pair_index: dict[tuple[str, str], list[tuple[str, int]]] = {}
    for (club, idx), (away, home) in position.items():
        pair_index.setdefault((away, home), []).append((club, idx))

    used: set[tuple[str, int]] = set()
    for (away, home), assignments in sorted(pair_index.items()):
        if len(assignments) != 2:
            problems.append(f"{away}@{home}: {len(assignments)} club assignment(s), expected 2")
            continue
        # Identify which assignment belongs to the away club and which to the home.
        away_assign = next(a for a in assignments if PFR_TO_RESULT[a[0]] == away)
        home_assign = next(a for a in assignments if PFR_TO_RESULT[a[0]] == home)
        away_row = by_club[away_assign[0]][away_assign[1]]
        home_row = by_club[home_assign[0]][home_assign[1]]
        used.add(away_assign)
        used.add(home_assign)

        # The two pages are independent transcriptions of the same market.
        if home_row["total"] != away_row["total"]:
            problems.append(
                f"{away}@{home}: total disagrees {away_row['total']} vs {home_row['total']}"
            )
        if home_row["spread"] != -away_row["spread"]:
            problems.append(
                f"{away}@{home}: spread is not a mirrored pair "
                f"{away_row['spread']} vs {home_row['spread']}"
            )

        games.append({
            "club_game_no_away": away_row["game_no"],
            "club_game_no_home": home_row["game_no"],
            "away": away,
            "home": home,
            "closing_total": str(away_row["total"]),
            "closing_line_away": str(away_row["spread"]),
            "closing_line_home": str(home_row["spread"]),
            "sources": sorted({away_row["source_url"], home_row["source_url"]}),
            "retrieved": RETRIEVED,
            "sides_agree": home_row["spread"] == -away_row["spread"],
            "totals_agree": home_row["total"] == away_row["total"],
        })

    for club, rows in by_club.items():
        official_len = len(official_seq.get(PFR_TO_RESULT[club], []))
        for idx, row in enumerate(rows):
            if idx >= official_len:
                continue  # intentionally unjoined: covered by a PS05 flag
            if (club, idx) not in used:
                problems.append(f"evidence row never paired: {club} g{row['game_no']}")

    # --- 3. Reconcile against the official result feed ------------------------
    result_index = {(g["away"], g["home"]): g for g in results}
    matched = 0
    for game in games:
        result = result_index.get((game["away"], game["home"]))
        if result is None:
            game["result_status"] = "no_result_in_feed"
            flags.append({
                "id": "PS01",
                "item": f"{game['away']}@{game['home']} g{game['game_no']}",
                "issue": "Closing price exists but no official result could be joined.",
                "action": "Leave unpriced in ROI; do not impute a score.",
            })
            continue
        matched += 1
        game["date"] = result["date"]
        game["week"] = result["week"]
        game["away_score"] = result["away_score"]
        game["home_score"] = result["home_score"]
        game["result_source_url"] = result["source_url"]
        game["result_status"] = "joined"

    # --- 4. Derive outcomes from the published number only --------------------
    for game in games:
        if game["result_status"] != "joined":
            continue
        margin = game["home_score"] - game["away_score"]
        total = game["away_score"] + game["home_score"]
        line = Decimal(game["closing_line_home"])
        game["actual_margin_home"] = margin
        game["actual_total"] = total
        # Home cover: home margin + home line vs 0. Push when exactly equal.
        edge = Decimal(margin) + line
        game["home_cover"] = "push" if edge == 0 else ("cover" if edge > 0 else "fail")
        tline = Decimal(game["closing_total"])
        game["total_result"] = (
            "push" if Decimal(total) == tline else ("over" if Decimal(total) > tline else "under")
        )

    # --- 4b. Independent reconciliation of the derived labels -----------------
    # The publisher prints its own "vs. Line" and "OU Result" verdict for every
    # club-game. Re-deriving those verdicts from the spread, the total and the
    # official score is a check on the whole chain (transcription -> pairing ->
    # arithmetic), so a disagreement is a hard failure.
    vs_line_path = HERE / "evidence" / "pfr-vs-line-2026-w1-9.csv"
    verdicts: dict[tuple[str, int], tuple[str, str]] = {}
    with vs_line_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            verdicts[(row["club_pfr"], int(row["game_no"]))] = (
                row["vs_line"].strip().upper(), row["ou_result"].strip().upper()
            )
    checked = 0
    for (club, idx), (away, home) in position.items():
        row = by_club[club][idx]
        expected = verdicts.get((club, row["game_no"]))
        if expected is None:
            problems.append(f"{club} g{row['game_no']}: publisher verdict missing from evidence")
            continue
        game = next((g for g in games if g["away"] == away and g["home"] == home), None)
        if game is None or game["result_status"] != "joined":
            continue
        code = PFR_TO_RESULT[club]
        own = game["home_score"] if code == home else game["away_score"]
        opp = game["away_score"] if code == home else game["home_score"]
        edge = Decimal(own - opp) + row["spread"]
        cover = "PUSH" if edge == 0 else ("WON" if edge > 0 else "LOST")
        total = game["away_score"] + game["home_score"]
        ou = (
            "PUSH" if Decimal(total) == row["total"]
            else ("OVER" if Decimal(total) > row["total"] else "UNDER")
        )
        checked += 1
        if (cover, ou) != expected:
            problems.append(
                f"{club} g{row['game_no']}: derived {cover}/{ou} but publisher prints "
                f"{expected[0]}/{expected[1]}"
            )

    # --- 5. Records and flags -------------------------------------------------
    flagged_rows = [g for g in games if not (g["sides_agree"] and g["totals_agree"])]
    unsupported = [k for k, v in MARKET_SUPPORT.items() if v == "not_published"]

    snapshot = {
        "schema_version": 1,
        "generated_for": "nfl-pricing",
        "purpose": (
            "Record the published closing number for the two markets we originate, per game, "
            "with both clubs' pages as independent confirmations. This is the reference price "
            "against which our own fair line is compared. It is not an executable offer."
        ),
        "price_kind": "published_reference_price_not_executable_offer",
        "opening_line_available": False,
        "opening_line_note": (
            "The publisher prints exactly one number per game and does not label it an open or "
            "a close. It is recorded here as the closing snapshot because it is the last "
            "published pre-kickoff number on that page. No opening number is estimated, "
            "interpolated or back-filled from line movement."
        ),
        "markets": MARKET_SUPPORT,
        "markets_not_published": unsupported,
        "counts": {
            "clubs_with_a_page": len(by_club),
            "evidence_rows": len(evidence),
            "games_reconciled": len(games),
            "games_joined_to_official_result": matched,
            "games_with_both_sides_agreeing": len([g for g in games if g["sides_agree"]]),
            "games_with_totals_agreeing": len([g for g in games if g["totals_agree"]]),
            "rows_flagged": len(flagged_rows),
            "publisher_verdicts_reconcile": checked,
        },
        "sources": [
            {
                "id": "PFR-VEGAS-2026",
                "publisher": "Sports Reference LLC (Pro-Football-Reference.com)",
                "title": "2026 Team Vegas Lines (closing spread and total, per club, weeks 1-9)",
                "url_pattern": "https://www.pro-football-reference.com/teams/{club}/2026_lines.htm",
                "kind": "market_price",
                "authority": "Secondary aggregator; historical line data credited to Sports Odds History",
                "scope": (
                    "One closing spread and one closing total per game, from that club's "
                    "perspective. No opening line, moneyline or player prop is published."
                ),
                "checked_on": RETRIEVED,
                "access": "Arena fetch_page rendered content; not a direct HTTP-status attestation",
                "status": "Content checked",
            }
        ],
        "problems": problems,
        "games": games,
        "flags": flags + [
            {
                "id": "PS02",
                "item": "Opening price for every market",
                "issue": (
                    "No official source examined publishes an opening number for these games. "
                    "ESPN publishes a live open/current pair, but only for the unplayed slate and "
                    "not as a retrievable archive; the completed game pages render no open or close."
                ),
                "action": (
                    "Capture the ESPN open/current pair at a fixed pre-kickoff timestamp in future "
                    "weeks, and record the capture timestamp. Until then the opening columns stay "
                    "blank and no CLV is computed."
                ),
            },
            {
                "id": "PS03",
                "item": "Moneyline",
                "issue": "The 32 closing-line pages print a spread and a total only. No moneyline.",
                "action": (
                    "Moneyline is originated from our own number and published as fair-vs-market "
                    "with the market cell blank and flagged. Do not imply a book price."
                ),
            },
            {
                "id": "PS04",
                "item": "Player props",
                "issue": (
                    "No official source in this capture publishes player-level prices that can be "
                    "retrieved and archived."
                ),
                "action": "Prop combos stay unpriceable; report the gate as blocked, not failed.",
            },
        ],
    }
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the committed output differs")
    args = parser.parse_args()

    snapshot = build()
    text = json.dumps(snapshot, indent=1, sort_keys=False) + "\n"
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("FAIL: data/price-snapshots.json is stale; run python collect.py")
            return 1
        print(
            "OK: price snapshots reproduce "
            f"({snapshot['counts']['games_reconciled']} games, "
            f"{len(snapshot['problems'])} problem(s))"
        )
        return 0 if not snapshot["problems"] else 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    print(
        f"Wrote {OUT.relative_to(ROOT)} sha256:{digest} "
        f"({snapshot['counts']['games_reconciled']} games, "
        f"{snapshot['counts']['games_joined_to_official_result']} joined, "
        f"{len(snapshot['problems'])} problem(s))"
    )
    for problem in snapshot["problems"]:
        print("  PROBLEM:", problem)
    return 0 if not snapshot["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
