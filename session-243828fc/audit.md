# Repo irregularity audit (P3), 14 Nov 2026

Full table with file paths and links: [repo-audit.html](repo-audit.html). Flags with owner actions: [flagged.html](flagged.html).

Highest-priority items:
- Saved ledger `nfl-availability-28ef/data/injuries-week10-2026.csv` is out of date against the live report (UNVERIFIED counts; see flagged F01, F02).
- README "no dataset is released" conflicts with the committed compiled tables (rights, F07; NFL.com terms §1.3).
- Two standings files with different column layouts and no canonical note (A03).
- `nfl/verify_independent.py` reports column disagreements but exits 0 (A05).
- Open PRs #27 and #17 are not touched by this session.

Not repeated here: the ledger and standings values. See the linked pages.
