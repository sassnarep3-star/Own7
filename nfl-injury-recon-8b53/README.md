# Patriots–Lions injury block: official report vs two desks (session arena/8b538c74-own7)

**What this answers:** for the Sunday, November 15 block of the official NFL Week 10 injury report, does each
row (position, injury, practice status, game status) match the official text, and where does each desk differ?

| Item | Where |
|---|---|
| Official source | https://www.nfl.com/injuries/league/2026/REG10 (read 2026-11-18 via fetch_page) |
| Verbatim evidence (24 rows) | `evidence/official-REG10-SUN-NE-at-DET-2026-11-18.md` · SHA-256 in `evidence/SHA256SUMS.txt` |
| Desk A compared | `nfl-availability-28ef/data/injuries-week10-2026.csv` (checked_on 2026-11-13) |
| Desk B compared | `nfl-assurance-9580ac3f/data/injuries.csv` (no clock time in file) |
| Output table | `data/reconciliation.csv` · `data/summary.json` · `site/index.html` |

## Rules applied
- Nothing is edited in either desk. Differences are reported, not fixed (cross-scope; see COORDINATION.md).
- A field "agrees" only on an exact string match with the official cell. A blank desk cell is a difference.
- A difference is **not** called an error when the desk file has no clock time: a later official capture can
  legitimately change practice status. The desk therefore cannot say which read is correct for an earlier time.

## Commands
```sh
python nfl-injury-recon-8b53/build.py            # regenerate data + page
python nfl-injury-recon-8b53/build.py --check    # byte-identical reproduction
python -m unittest discover -s nfl-injury-recon-8b53/tests
```

## Limits
- One official block (24 rows, the Sunday NE/DET game). The rest of the Week 10 report is not covered by this desk.
- The official page was read in one chunk (chunk 0 of 8). The verbatim excerpt is only the Sunday NE/DET block.
- Other blocks were not compared; no claim is made about them here.
