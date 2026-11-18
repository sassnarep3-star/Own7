# nfl-integration-c815 — integration audit desk

Session `arena/c815bdd2-own7`, 2026-11-18. Additive to every existing desk; it edits
nothing another session owns.

| Module | What it does |
|---|---|
| `engine.py` | Re-derives the Week 10 completion and the results-feed residue from official captures. Aborts on any contradiction. |
| `requirements.py` | Independently checks every requirement register row: does the named artefact exist, and what must a reviewer do? |
| `rules.py` | DR-68: extracts the 2026 kickoff/declared-onside-kick rule values from the official rulebook capture. |

Every published number is an arithmetic result of the rows above it, or a literal
extraction from an official capture. Nothing is estimated.
