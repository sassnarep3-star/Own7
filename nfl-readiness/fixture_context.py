#!/usr/bin/env python3
"""Fixture-context feature set built only from published schedule facts (D8b).

Every value on a row is either printed on an official schedule page or is plain arithmetic on two
printed dates (a rest-day count). Nothing is looked up from memory, and the two features this desk
cannot source — roof/surface and weather — are blank with the gate that blocks them.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"

# Week 11 rows, transcribed from evidence/schedule-2026-reg10-reg11-2026-11-17.md.
# (away, home, printed date, kickoff, network, venue string, printed international label)
W11 = [
    ("IND", "HOU", "2026-11-19", "8:15 PM", "PRIME", "NRG Stadium", ""),
    ("MIA", "BUF", "2026-11-22", "1:00 PM", "CBS", "Highmark Stadium", ""),
    ("BAL", "CAR", "2026-11-22", "1:00 PM", "FOX", "Bank of America Stadium", ""),
    ("NO", "CHI", "2026-11-22", "1:00 PM", "FOX", "Soldier Field", ""),
    ("TEN", "DAL", "2026-11-22", "1:00 PM", "FOX", "AT&T Stadium", ""),
    ("TB", "DET", "2026-11-22", "1:00 PM", "FOX", "Ford Field", ""),
    ("AZ", "KC", "2026-11-22", "1:00 PM", "CBS", "GEHA Field at Arrowhead Stadium", ""),
    ("PIT", "PHI", "2026-11-22", "1:00 PM", "CBS", "Lincoln Financial Field", ""),
    ("NYJ", "LAC", "2026-11-22", "4:05 PM", "FOX", "SoFi Stadium", ""),
    ("JAX", "NYG", "2026-11-22", "4:25 PM", "CBS", "MetLife Stadium", ""),
    ("LV", "DEN", "2026-11-22", "4:25 PM", "CBS", "Empower Field at Mile High", ""),
    ("MIN", "SF", "2026-11-22", "8:20 PM", "NBC", "", "Mexico City"),
    ("CIN", "WAS", "2026-11-23", "8:15 PM", "ESPN", "FedEx Field", ""),
]

# Week 10 printed dates per club (only the date the schedule page prints).
W10_DATES = {
    "WAS": "2026-11-12", "NYG": "2026-11-12", "NE": "2026-11-15", "DET": "2026-11-15",
    "KC": "2026-11-15", "ATL": "2026-11-15", "HOU": "2026-11-15", "CLE": "2026-11-15",
    "MIN": "2026-11-15", "GB": "2026-11-15", "MIA": "2026-11-15", "IND": "2026-11-15",
    "CAR": "2026-11-15", "NO": "2026-11-15", "BUF": "2026-11-15", "NYJ": "2026-11-15",
    "JAX": "2026-11-15", "TEN": "2026-11-15", "LAR": "2026-11-15", "AZ": "2026-11-15",
    "SEA": "2026-11-15", "LV": "2026-11-15", "SF": "2026-11-15", "DAL": "2026-11-15",
    "PIT": "2026-11-15", "CIN": "2026-11-15", "LAC": "2026-11-16", "BAL": "2026-11-16",
}
W10_BYES = {"CHI", "DEN", "PHI", "TB"}
W11_BYES = ["ATL", "CLE", "GB", "LA", "NE", "SEA"]


def rest_days(club: str, game_date: str) -> tuple[str, str]:
    """(rest days, basis) — arithmetic between two printed dates, or a stated absence."""
    if club in W10_BYES:
        return "", "Club was on bye in Week 10 per the printed bye list, so a 7-day rest count does not apply."
    prior = W10_DATES.get(club)
    if not prior:
        return "", "No Week 10 date is printed for this club, so rest days are not computable from the page."
    delta = (date.fromisoformat(game_date) - date.fromisoformat(prior)).days
    return str(delta), f"{prior} (Week 10) to {game_date} (Week 11)"


def build() -> dict:
    rows = []
    for away, home, day, kick, net, venue, intl in W11:
        away_rest, away_basis = rest_days(away, day)
        home_rest, home_basis = rest_days(home, day)
        short = ""
        if away_rest and int(away_rest) <= 4:
            short = f"{away} on {away_rest} days"
        elif home_rest and int(home_rest) <= 4:
            short = f"{home} on {home_rest} days"
        rows.append({
            "id": f"{away}-{home}",
            "away": away, "home": home, "date": day, "kickoff": kick, "network": net,
            "venue": venue, "international": intl,
            "away_rest_days": away_rest, "away_rest_basis": away_basis,
            "home_rest_days": home_rest, "home_rest_basis": home_basis,
            "short_week": short,
            "bye_advantage": away if away in W10_BYES else (home if home in W10_BYES else ""),
            "away_bye_w11": "yes" if away in W11_BYES else "",
            "home_bye_w11": "yes" if home in W11_BYES else "",
            "travel_time_zones": "",
            "travel_reason": "Kickoff time zones are not printed on the schedule page, so no travel-time-zone feature is computed.",
            "roof": "",
            "roof_gate": "PG-WEATHER",
            "surface": "",
            "surface_gate": "PG-WEATHER",
            "weather": "",
            "weather_note": "The schedule page prints only a coarse label (e.g. 'Clear') beside a few games; it publishes no forecast grid.",
            "source_ids": ["RD-NFL-SCHED-W11", "RD-NFL-SCHED-W10"],
        })
    by_rest: dict[str, int] = {}
    for row in rows:
        for side in ("away_rest_days", "home_rest_days"):
            if row[side]:
                by_rest[row[side]] = by_rest.get(row[side], 0) + 1
    return {
        "schema_version": 1,
        "read": "2026-11-17",
        "fixtures": rows,
        "counts": {
            "fixtures": len(rows),
            "fixtures_with_both_rest_counts": sum(1 for r in rows if r["away_rest_days"] and r["home_rest_days"]),
            "short_week_fixtures": sum(1 for r in rows if r["short_week"]),
            "bye_advantage_fixtures": sum(1 for r in rows if r["bye_advantage"]),
            "international_fixtures": sum(1 for r in rows if r["international"]),
            "venues_printed": sum(1 for r in rows if r["venue"]),
            "roof_rows_sourced": 0,
            "weather_rows_sourced": 0,
            "rest_day_distribution": dict(sorted(by_rest.items(), key=lambda kv: int(kv[0]))),
        },
        "schedule_announcements": [
            {"what": "Flexible scheduling procedures",
             "url": "https://www.nfl.com/legal/flexible-scheduling-procedures",
             "printed_on": "the Week 10 and Week 11 schedule pages, linked from the page footer",
             "source_ids": ["RD-NFL-SCHED-W11"]},
            {"what": "Dated Week 16, 17 and 18 TBD announcement text (when the four designated matchups will be placed, and the deadline for announcing it)",
             "url": "https://www.nfl.com/schedules/2026/by-week/week-11",
             "printed_on": "the 2026 TBD Games panel rendered on each by-week page",
             "source_ids": ["RD-NFL-SCHED-W11"]},
        ],
        "not_built": [
            {"feature": "Roof and surface", "gate": "PG-WEATHER",
             "why": "No stadium register is captured. The schedule page does not print a roof or a surface."},
            {"feature": "Hourly wind and precipitation", "gate": "PG-WEATHER",
             "why": "No forecast feed is registered. A 'Clear' label beside one game is not a forecast grid."},
            {"feature": "Travel time zones", "gate": "PG-VENUE",
             "why": "Kickoff times are printed in one zone on the page; the club's home zone is not printed there."},
            {"feature": "2026 onside-kick regime prior", "gate": "PG-RULES",
             "why": "The 2026 rule text is not captured, so no regime adjustment is applied to totals."},
        ],
    }


def main() -> int:
    DATA.mkdir(exist_ok=True)
    payload = build()
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    target = DATA / "fixture-context.json"
    if "--check" in sys.argv:
        if not target.exists() or target.read_text() != text:
            raise SystemExit("fixture-context.json is stale")
        print(f"OK: {payload['counts']}")
        return 0
    target.write_text(text)
    print(f"Wrote fixture-context.json: {payload['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
