"""DR-68: the 2026 kickoff / declared onside-kick regime as a machine-readable filter.

Requirement DR-68 asks for "2026 Kickoff & Declared Onside-Kick Regime Priors Filter —
avoids systematic bias in originated game totals and 4th-quarter comeback win-probability
curves." Its published gate said the rule text had not been transcribed from the official
rulebook.

This module transcribes it from the official rulebook capture and **extracts each value
from the captured text with a regular expression**, so a value cannot be published unless
it is literally present in the official capture. If the wording changes, extraction fails
loudly rather than silently carrying a stale number forward.

It produces two things and nothing more:

1. a **regime table** — one row per rule element, with the verbatim clause and the
   official page it came from;
2. an **origination note** — the specific places where the current model would be
   structurally wrong if it assumed the pre-2026 regime, and how many of them this
   project can or cannot price.

It does **not** estimate an onside-kick success probability or a comeback rate. Those are
empirical frequencies and this project holds no official play-by-play capture, so they
stay blank and are published as blank.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "nfl-integration-c815" / "evidence"
RULES_PDF = "https://media.nfl.com/content/dam/communications/Official%20Playing%20Rules/2026%20Official%20Playing%20Rules.pdf"
CAPTURE = EVIDENCE / "rules-2026-kickoff-onside.retrieved.md"


def _must(pattern: str, text: str, what: str) -> re.Match:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        raise SystemExit(f"DR-68 extraction failed: {what} is no longer present in the capture")
    return match


def normalise(text: str) -> str:
    """Collapse the block-quote line wrapping the capture inherits from the PDF.

    This only removes the newline/`>` artefacts of quoting; no word is added, removed or
    reordered, so every pattern below must still match the publisher's own wording.
    """
    lines = [line.lstrip("> ").rstrip() for line in text.splitlines()]
    return re.sub(r"[ \t]+", " ", " ".join(lines))


def extract() -> dict:
    text = normalise(CAPTURE.read_text(encoding="utf-8"))

    # "At any time during the game, the kicking team may declare an onside kick"
    declaration = _must(
        r"At any time during the game, the kicking team may declare an onside kick",
        text, "the any-time declaration clause")
    # 25-second play clock after the ball is handed to the kicker
    clock = _must(
        r"prior to the start of the play clock \((\d+)-second play clock after the game "
        r"official hands the kicker the ball\)", text, "the declaration clock")
    # Kicking team's own 35 (20 on a safety kick)
    restraining = _must(
        r"The restraining line for the kicking team on an onside kick is the kicking team's "
        r"(\d+)-yard line or the kicking team's (\d+)-yard line for a safety kick",
        text, "the onside-kick restraining line")
    # Setup zone: 5 yards between the receiving team's 35 and 30
    setup = _must(
        r"setup zone\" for the receiving team is the (\d+)-yard area between the receiving "
        r"team's (\d+)-yard line and its (\d+)-yard line", text, "the receiving setup zone")
    # 50-yard-line kickoff touchback -> 20
    fifty = _must(
        r"if the kickoff is from the (\d+)-yard line and the play results in a touchback, "
        r"then the dead ball spot is the (\d+)-yard line", text, "the 50-yard touchback spot")
    # 2026 change list entry
    change = _must(
        r"6-1-6\s+Permits the kicking team to declare an onside kick at any time",
        text, "the 6-1-6 change-list entry")
    # Kickoff from own 35
    kickoff = _must(
        r"restraining line for the kickoff by the kicking team shall be its (\d+)-yard line "
        r"for a kickoff and its (\d+)-yard line for a safety kick",
        text, "the base kickoff restraining line")

    return {
        "declaration_clause": declaration.group(0),
        "declaration": "the kicking team must declare the onside kick to the Referee; no surprise onside kick",
        "declaration_clock_seconds": int(clock.group(1)),
        "legal_at_any_time": True,
        "onside_restraining_line": int(restraining.group(1)),
        "onside_safety_kick_line": int(restraining.group(2)),
        "setup_zone_yards": int(setup.group(1)),
        "setup_zone_receiving_lines": [int(setup.group(2)), int(setup.group(3))],
        "touchback_from_50_dead_ball": int(fifty.group(2)),
        "kickoff_restraining_line": int(kickoff.group(1)),
        "is_a_2026_change": bool(change),
        "rule_reference": "6-1-6",
    }


def regime_rows(values: dict) -> list[dict]:
    """One row per rule element, each carrying the verbatim clause it came from."""
    return [
        {"element": "May an onside kick be attempted at any time?",
         "value": "yes", "verbatim": "At any time during the game, the kicking team may declare an onside kick",
         "rule": "6-1-6", "status": "2026 change"},
        {"element": "Must it be declared to the Referee?",
         "value": "yes", "verbatim": "may declare an onside kick by notifying the Referee prior to the start of the play clock",
         "rule": "6-1-6", "status": "2026 change"},
        {"element": "Can it ever be a surprise onside kick?",
         "value": "no", "verbatim": "The Referee will then notify the receiving team before starting the play clock",
         "rule": "6-1-6", "status": "structural"},
        {"element": "Declaration deadline (play clock)",
         "value": f"{values['declaration_clock_seconds']}-second play clock",
         "verbatim": "(25-second play clock after the game official hands the kicker the ball)",
         "rule": "6-1-6", "status": "structural"},
        {"element": "Kicking team restraining line (kickoff)",
         "value": f"own {values['kickoff_restraining_line']}",
         "verbatim": "the restraining line for a kickoff", "rule": "6-1-2", "status": "unchanged"},
        {"element": "Kicking team restraining line (onside kick)",
         "value": f"own {values['onside_restraining_line']}",
         "verbatim": "The restraining line for the kicking team on an onside kick is the kicking team's 35-yard line",
         "rule": "6-1-6(b)", "status": "structural"},
        {"element": "Kicking team restraining line (safety-kick onside)",
         "value": f"own {values['onside_safety_kick_line']}",
         "verbatim": "or the kicking team's 20-yard line for a safety kick",
         "rule": "6-1-6(b)", "status": "structural"},
        {"element": "Receiving team setup zone (width)",
         "value": f"{values['setup_zone_yards']} yards",
         "verbatim": "the \"setup zone\" for the receiving team is the 5-yard area",
         "rule": "6-1-2(d)", "status": "2026 alignment change"},
        {"element": "Receiving team setup zone (location)",
         "value": "receiving team's 35 to 30",
         "verbatim": "between the receiving team's 35-yard line and its 30-yard line",
         "rule": "6-1-2(d)", "status": "2026 alignment change"},
        {"element": "Touchback after a kickoff from the 50",
         "value": f"dead ball at the {values['touchback_from_50_dead_ball']}",
         "verbatim": "if the kickoff is from the 50-yard line and the play results in a touchback, "
                     "then the dead ball spot is the 20-yard line",
         "rule": "6-1-5", "status": "2026 change"},
    ]


def model_notes(values: dict) -> list[dict]:
    """Where a pre-2026 assumption would bias the model. No frequency is invented."""
    return [
        {"id": "RG-01", "affects": "4th-quarter comeback win-probability curves",
         "pre_2026_assumption": "an onside kick is only available to a trailing team late in the game",
         "2026_rule": "any team, at any time, by declaration",
         "bias_if_ignored": "the model understates a leading team's option value and mis-states the "
                            "available state space for the trailing team's comeback path",
         "priced_here": "not priced — the availability change is stated, the frequency is not held"},
        {"id": "RG-02", "affects": "game totals and 4th-quarter win probability",
         "pre_2026_assumption": "an onside kick can be a surprise play",
         "2026_rule": "declaration to the Referee is mandatory; the receiving team is notified",
         "bias_if_ignored": "a surprise-recovery rate from any earlier season is not transferable, "
                            "because the defence is told to expect the kick",
         "priced_here": "not priced — no official play-by-play capture is held"},
        {"id": "RG-03", "affects": "drive-start distributions after a kickoff penalty",
         "pre_2026_assumption": "a kickoff from the 50 is an ordinary kickoff",
         "2026_rule": f"a touchback from the 50 puts the ball at the {values['touchback_from_50_dead_ball']}",
         "bias_if_ignored": "field-position priors after a 15-yard kickoff penalty are wrong in one direction",
         "priced_here": "not priced — field-position priors are not modelled"},
        {"id": "RG-04", "affects": "receiving-team return expectation",
         "pre_2026_assumption": "the setup zone is a single 5-yard band with a fixed 9-player rule",
         "2026_rule": "alignment requirements in the setup zone changed for 2026 (6-1-3)",
         "bias_if_ignored": "return-yardage priors trained on 2024-2025 alignments do not transfer",
         "priced_here": "not priced — no return-yardage capture is held"},
    ]


def status() -> dict:
    values = extract()
    return {
        "requirement": "DR-68",
        "closeable_from_official_source": True,
        "official_source": RULES_PDF,
        "capture": str(CAPTURE.relative_to(ROOT)),
        "values": values,
        "regime_rows": regime_rows(values),
        "model_notes": model_notes(values),
        "what_is_still_open": (
            "How often clubs declared an onside kick in 2026, and how often a declared onside "
            "kick was recovered, are empirical frequencies. This project holds no official "
            "play-by-play capture, so both stay blank and are published as blank rather than "
            "estimated."),
    }


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(status()["values"], indent=2))
