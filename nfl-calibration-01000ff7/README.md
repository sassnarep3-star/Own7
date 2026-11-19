# Walk-forward probability calibration audit

Run `python nfl-calibration-01000ff7/build.py` to reproduce the JSON/CSV analysis and dashboard;
run it with `--check` to verify committed outputs byte-for-byte. Run tests with
`python -m unittest discover -s nfl-calibration-01000ff7/tests -v`.

This is a focused audit of probability quality, not a new strategy, price feed, or recommendation.
It evaluates the existing three-stage model on all 134 games in target weeks 2–10, with each
forecast trained only on prior weeks. The three-outcome Brier score retains the tie; binary Brier
and reliability bins score the 133 non-ties using p(home | no tie). Model probabilities and their
margin, spread and prior-tie-rate inputs are stored per game. Official result links appear on every
game row. A small positive skill estimate is not treated as qualification: week-cluster uncertainty,
sparse calibration bins, absent prices and single-season holdout limitations are published beside it.
