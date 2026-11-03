# Coordination board

| Task | Status | Owner | File scope |
|---|---|---|---|
| Repository review, NBA research, site and final integration | needs review | arena-b0cbee88 | README.md, COORDINATION.md, site files, .github/workflows |

## Log
- 2026-11-03: Claimed integration work. Repository initially contained only README.md; no existing task board. This session uses the Arena-assigned branch, rather than creating a separate session branch.

## Integration notes
- Initial review: README.md contained only `# Own7`; no data, strategies, or existing site were present.
- Official NBA glossary checked for pace and ratings: https://www.nba.com/stats/help/glossary. The NBA 2023–24 survey was checked for the historical league averages displayed: https://www.nba.com/news/2023-24-nba-stats-survey-league-scoring-averages.
- Official NBA injury snapshot checked for its dated nature: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-02_05_30PM.pdf. scikit-learn documentation checked for time-order and calibration: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html and https://scikit-learn.org/stable/modules/calibration.html. NIST source on bootstrap uncertainty: https://nvlpubs.nist.gov/nistpubs/ir/2018/NIST.IR.8218.pdf.
- Irregularities: no historical executable market prices, joint observations, models, backtests, reward funding or competition operator; no actual edge, correlation, ranking or skill claim can be verified. Published on Flagged for Review. Gate thresholds and candidate signals are explicitly proposed, not verified findings. Luck cannot be eliminated.
- Verification: `python3 scripts/check_site.py` verifies local relative links and an HTTPS link in each table body row. It does not verify third-party link availability or support for claims. Sources were reviewed against the specific factual claims; proposals are labeled as such.
- Pull request: https://github.com/sassnarep3-star/Own7/pull/1. Implementation complete; unresolved data and empirical validation are flagged on the site. Merge and deployment pending.
