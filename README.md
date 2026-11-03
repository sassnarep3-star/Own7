# Own7 – NBA Lines Research

A verification-first research site for NBA betting strategies. Live site (GitHub Pages, from `/docs` on `main`):
https://sassnarep3-star.github.io/Own7/

**Principle:** every value shown is either confirmed from a linked official source, or left blank and flagged.
No strategy is shown as profitable unless it passes all validation gates.

## Layout

- `docs/` – the published site (generated HTML + `docs/data/*.json`, the single source of truth)
- `docs/data/` – source registry, rules, helplines, strategies, gates, correlation, leaderboard, repo review, flagged items
- `scripts/build_site.py` – regenerates the HTML pages from the JSON
- `scripts/check_site.py` – verification gate: official-source check, blank-value check, link check, rebuild-diff check
- `COORDINATION.md` – shared task board for parallel sessions

## Rebuild and check

```bash
python3 scripts/build_site.py
python3 scripts/check_site.py   # must print OK before merge
```

No dependencies beyond Python 3.

## Not financial or betting advice

Responsible gambling: Alberta helplines and self-exclusion are on the
[Responsible Gambling page](https://sassnarep3-star.github.io/Own7/responsible-gambling.html).
