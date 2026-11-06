# SF Outer Sunset rent-increase research (anonymized)

Self-contained sub-site published under `/rental/` on the project's GitHub Pages site.

- `data.json` — all content: official source register, anonymized property/unit facts (dates and amounts unchanged; tenant names replaced with placeholders), law rows, process rows, practice rows, Q&A, and flags. Unverified values are empty strings, never inferred.
- `build.py` — deterministic, offline generator for the 8 HTML pages. `python rental/build.py` rebuilds; `python rental/build.py --check` verifies committed output is current (used in CI).
- `test_build.py` — structural tests (official HTTPS hosts, one h1/main per page, every table row linked to a registered official source, internal links resolve, no personal initials present, deterministic build).
- `style.css` — shared accessible stylesheet. `manifest.json` — generated page list consumed by `scripts/build_site.py`.

Every table row carries `data-source-ids` and links to the official source(s) used, enforced by `scripts/check_site.py`. Items that could not be confirmed from an official source are published blank on `flagged.html` (Flagged for Review).

Not legal advice. Free SF tenant resources: Rent Board counseling 415-252-4600; Eviction Defense Collaborative 415-659-9184 (see `sources.html`).
