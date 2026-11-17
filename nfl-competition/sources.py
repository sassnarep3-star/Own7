"""Source register for the competition lab.

A row is published only if every value in it traces to a source registered here.
The register is append-only inside this session and every entry names the page
actually read, the date it was read and the retrieval class.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, check_artifact, read_json, write_json  # noqa: E402

OUT = ROOT / "nfl-competition" / "data" / "sources.json"

READ_ON = "2026-11-14"
RETRIEVAL = ("rendered text via the Arena page reader; direct HTTPS to nfl.com returns "
             "curl code 000 from the build sandbox")

SOURCES = [
    {
        "id": "CP-NFL-STANDINGS",
        "publisher": "NFL.com",
        "title": "2026 NFL Division Standings",
        "url": "https://www.nfl.com/standings/",
        "authority": "Official league publication",
        "checked_on": READ_ON,
        "status": "Verified",
        "scope": "All 32 clubs: W, L, T, PCT, PF, PA, NET PTS, STRK. Read on 2026-11-14, "
                 "after the Week 10 Thursday game. The three unnamed three-part records "
                 "and the two unnamed decimals are withheld, not guessed.",
        "access": "Arena fetch_page; chunks 0 and 1 of 2",
        "retrieval_class": RETRIEVAL,
        "evidence": "nfl-competition/evidence/nfl-standings-2026-11-14.md",
        "used_by": ["results.py", "originate.py", "correlations.py", "depth.py"],
    },
    {
        "id": "CP-NFL-W10-SCHEDULE",
        "publisher": "NFL.com",
        "title": "NFL Week 10 Schedule 2026: Games, Times, Matchups & Tickets",
        "url": "https://www.nfl.com/schedules/2026/by-week/week-10",
        "authority": "Official league publication",
        "checked_on": READ_ON,
        "status": "Verified",
        "scope": "14 Week 10 fixtures with kickoff date, kickoff time and network, four "
                 "bye clubs, and the final score of the one game already played.",
        "access": "Arena fetch_page; chunks 0, 1 and 2 of 3",
        "retrieval_class": RETRIEVAL,
        "evidence": "nfl-competition/evidence/nfl-week-10-schedule-2026-11-14.md",
        "used_by": ["originate.py", "boards.py"],
    },
    {
        "id": "CP-NFL-W10-GAME-WASNYG",
        "publisher": "NFL.com",
        "title": "Washington Commanders at New York Giants 2026 REG 10 - Game Center",
        "url": "https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
        "authority": "Official league publication",
        "checked_on": READ_ON,
        "status": "Verified",
        "scope": "Final score WAS 24, NYG 21; by-quarter table 0-10-7-7 and 0-7-7-7; "
                 "location and stadium; the embedded NFC East standings widget.",
        "access": "Arena fetch_page; chunk 0 of 2",
        "retrieval_class": RETRIEVAL,
        "evidence": "nfl-competition/evidence/nfl-game-commanders-at-giants-2026-reg-10.md",
        "used_by": ["results.py"],
    },
    {
        "id": "CP-NFL-ODDS-ABSENT",
        "publisher": "NFL.com",
        "title": "404 - Flag on the Play. (no odds page at nfl.com/odds/)",
        "url": "https://www.nfl.com/odds/",
        "authority": "Official league publication (negative result)",
        "checked_on": READ_ON,
        "status": "Verified negative",
        "scope": "The URL returns 404 with no odds table, no price, no operator and no "
                 "market list. Establishes that the first URL a reader would try for "
                 "league-published prices does not exist. It does not prove the absence "
                 "of every price page on the domain, and is recorded as such.",
        "access": "Arena fetch_page; full page, 1 of 1 chunks",
        "retrieval_class": RETRIEVAL,
        "evidence": "nfl-competition/evidence/nfl-odds-page-absent-2026-11-14.md",
        "used_by": ["prices.py", "boards.py", "leaderboard.py"],
    },
    {
        "id": "CP-NFL-RESULTS-W1-9",
        "publisher": "NFL.com",
        "title": "2026 by-week schedule pages, weeks 1 to 9",
        "url": "https://www.nfl.com/schedules/2026/by-week/week-1",
        "authority": "Official league publication",
        "checked_on": "2026-11-14",
        "status": "Inherited capture, re-verified this session",
        "scope": "136 settled games and 16 bye rows captured by session "
                 "arena/196424c5-own7 on 2026-11-14. This session re-reads the captured "
                 "CSV and reconciles every club's points and record against the "
                 "standings page read today; the build aborts on any mismatch.",
        "access": "Arena fetch_page by the capturing session; retained under "
                  "nfl-results/evidence/week-*.schedule.md",
        "retrieval_class": RETRIEVAL,
        "evidence": "nfl-results/evidence/",
        "used_by": ["results.py", "backtest.py", "correlations.py"],
    },
    {
        "id": "CP-NFL-INJ-W10",
        "publisher": "NFL.com",
        "title": "2026 NFL Week 10 injury report (league-wide)",
        "url": "https://www.nfl.com/injuries/league/2026/REG10",
        "authority": "Official league publication",
        "checked_on": "2026-11-13",
        "status": "Inherited capture",
        "scope": "326 injury rows for 28 clubs with practice status and, for some rows, a "
                 "game status. Read by session arena/28efbbd0-own7 and reused here "
                 "without modification.",
        "access": "Arena fetch_page by the capturing session; retained under "
                  "nfl-availability-28ef/evidence/injury-report-week10-2026.joined.md",
        "retrieval_class": RETRIEVAL,
        "evidence": "nfl-availability-28ef/evidence/injury-report-week10-2026.joined.md",
        "used_by": ["depth.py", "injuries.py"],
    },
    {
        "id": "CP-NFL-DEPTH-27",
        "publisher": "Club sites (27 of 32 clubs)",
        "title": "Official club depth charts, captured 2026-11-12 and 2026-11-13",
        "url": "https://www.atlantafalcons.com/team/depth-chart",
        "authority": "Official club publication",
        "checked_on": "2026-11-13",
        "status": "Inherited capture",
        "scope": "1,586 printed depth-chart slots for 27 clubs, each with club, unit, "
                 "position, slot, rank and player. Captured by session "
                 "arena/28efbbd0-own7. Houston renders no table and stays a blank.",
        "access": "Arena fetch_page by the capturing session; retained under "
                  "nfl-availability-28ef/evidence/depth-*.md",
        "retrieval_class": RETRIEVAL,
        "evidence": "nfl-availability-28ef/evidence/",
        "used_by": ["depth.py", "injuries.py"],
    },
    {
        "id": "CP-NFL-DEPTH-BYE4",
        "publisher": "Club sites (CHI, DEN, PHI, TB)",
        "title": "Official club depth charts for the four Week 10 bye clubs",
        "url": "https://www.chicagobears.com/team/depth-chart",
        "authority": "Official club publication",
        "checked_on": "2026-11-14",
        "status": "Inherited capture",
        "scope": "231 printed slots for the four clubs that had no Week 10 injury row "
                 "because they were on bye. Captured by session arena/cfdd5580-own7.",
        "access": "Arena fetch_page by the capturing session; retained under "
                  "nfl-skill-cfdd/evidence/",
        "retrieval_class": RETRIEVAL,
        "evidence": "nfl-skill-cfdd/evidence/",
        "used_by": ["depth.py"],
    },
    {
        "id": "CP-NFL-TERMS",
        "publisher": "NFL",
        "title": "NFL.com Terms and Conditions",
        "url": "https://support.nfl.com/hc/en-us/articles/35869743904916-NFL-com-Terms-and-Conditions",
        "authority": "Official league publication",
        "checked_on": "2026-11-12",
        "status": "Constraint",
        "scope": "1.3 individual non-commercial informational use only; systematic "
                 "retrieval prohibited without written consent; gambling and wagering "
                 "provisions. Registered by an earlier session and honoured here.",
        "access": "Arena fetch_page by an earlier session",
        "retrieval_class": RETRIEVAL,
        "evidence": "docs/nfl-sources.md",
        "used_by": ["prices.py", "questions.py", "suggestions.py"],
    },
    {
        "id": "PYTH-NFL",
        "publisher": "Wikipedia contributors",
        "title": "Pythagorean expectation",
        "url": "https://en.wikipedia.org/wiki/Pythagorean_expectation",
        "authority": "Tertiary summary of a published method",
        "checked_on": "2026-11-12",
        "status": "Method reference",
        "scope": "Formula form and the NFL exponent of 2.37 attributed to Football "
                 "Outsiders / Pro-Football-Reference. Method only; never a data source.",
        "access": "Arena fetch_page by an earlier session",
        "retrieval_class": RETRIEVAL,
        "evidence": "research/sources.json",
        "used_by": ["originate.py", "backtest.py"],
    },
]


def build():
    existing = read_json(ROOT / "research" / "sources.json")
    known = {entry["id"] for entry in existing}
    collisions = [entry["id"] for entry in SOURCES if entry["id"] in known and
                  entry["id"] != "PYTH-NFL"]
    payload = {
        "source_register": "nfl-competition (session arena/064da913-own7)",
        "read_on": READ_ON,
        "id_collisions_with_research_sources_json": collisions,
        "count": len(SOURCES),
        "sources": SOURCES,
    }
    return payload


def main():
    if check_artifact(OUT, build()):
        print(f"  {len(SOURCES)} sources registered")


if __name__ == "__main__":
    main()
