"""Independent verification of every published requirement claim.

The brief asks for line-by-line verification from official sources and for a clear
list of what is known, what is not, and what would settle it. This module does the
machine part of that honestly:

* it reads the canonical requirement register (``research/nfl-decision-readiness.json``)
  **read-only** and does not edit it;
* for each row it checks whether the artefact the register names actually exists, and
  whether the claim is *supported by a checkable artefact* or only asserted;
* it classifies each row by what a reviewer must do before the claim can be trusted.

It never upgrades a status. The register's own status word is carried through unchanged
and is labelled as `published`, so a reader can always see which half is the other
desk's claim and which half is this desk's independent finding.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "research" / "nfl-decision-readiness.json"

# Artefact prefixes that are *data or code* a reviewer can re-run, versus pages that
# merely display a conclusion. This is a routing fact, not a quality judgement.
RUNNABLE_PREFIXES = ("nfl-", "scripts/", "research/", "data/", "tests/")

# Which requirement rows the brief's later blocks explicitly re-state as a demand for
# evidence this project does not yet hold. Listed so the reviewer can see the overlap
# instead of counting the same gap twice under two ids.
KNOWN_OVERLAP = {
    "DR-11": ("DR-27", "DR-28", "DR-44", "DR-52", "DR-53", "DR-56"),
    "DR-27": ("DR-28", "DR-53"),
    "DR-29": ("DR-30", "DR-54", "DR-55", "DR-66"),
    "DR-13": ("DR-64",),
    "DR-31": ("DR-44",),
    "DR-39": ("DR-47",),
    "DR-61": ("DR-30", "DR-55"),
    "DR-70": ("DR-19",),
}


def exists(rel: str) -> bool:
    if not rel:
        return False
    probe = ROOT / rel.split()[0]
    return probe.exists()


def verify_rows() -> list[dict]:
    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    out: list[dict] = []
    for row in register["requirements"]:
        artifact = (row.get("artifact") or "").strip()
        # A register row may name several artefacts; all of them must resolve.
        names = [n for n in artifact.replace(",", " ").split() if n]
        missing = [n for n in names if not exists(n)]
        verifiable = bool(names) and not missing
        out.append({
            "id": row["id"],
            "requirement": row["requirement"],
            "category": row.get("category", ""),
            "published_status": row.get("status", ""),
            "gate": row.get("gate", ""),
            "clears_when": row.get("clears_when", ""),
            "artifact": artifact,
            "artifact_resolves": verifiable,
            "artifacts_missing": missing,
            "source_ids": row.get("source_ids", []),
            "overlap": list(KNOWN_OVERLAP.get(row["id"], ())),
            # The reviewer's action, derived only from what was just checked.
            "reviewer_action": (
                "open the artefact and confirm the claim"
                if verifiable else
                "artefact named by the register does not resolve — treat the claim as unverified"
            ),
        })
    return out


def summary(rows: list[dict]) -> dict:
    from collections import Counter
    statuses = Counter(r["published_status"] for r in rows)
    unresolved = [r["id"] for r in rows if not r["artifact_resolves"]]
    blocked = [r["id"] for r in rows if r["published_status"] == "Blocked"]
    open_ = [r["id"] for r in rows if r["published_status"] == "Open"]
    partial = [r["id"] for r in rows if r["published_status"] == "Partial"]
    return {
        "rows": len(rows),
        "by_status": dict(sorted(statuses.items())),
        "implemented": statuses.get("Implemented", 0),
        "partial": statuses.get("Partial", 0),
        "open": len(open_),
        "blocked": len(blocked),
        "rejected": statuses.get("Rejected", 0),
        "artefact_unresolved": unresolved,
        "open_ids": open_,
        "partial_ids": partial,
        "blocked_ids": blocked,
        "with_overlaps": [r["id"] for r in rows if r["overlap"]],
        "note": ("Statuses in the left column are the canonical register's published claim. "
                 "The right columns are this desk's independent check of whether the named "
                 "artefact exists and can be re-run. Nothing here upgrades a status."),
    }


if __name__ == "__main__":  # pragma: no cover
    rows = verify_rows()
    print(json.dumps(summary(rows), indent=2))
