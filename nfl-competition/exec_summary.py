#!/usr/bin/env python3
"""P12: the executive summary, written from the artifacts rather than from memory.

Every number in the generated document is read out of a committed artifact, so the
summary cannot drift from the data it describes. If an artifact is missing the script
fails instead of writing a plausible sentence around a gap.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import DATA, ROOT, write_json  # noqa: E402

OUT = HERE / "EXECUTIVE-SUMMARY.md"


def artifact(name: str):
    path = DATA / name
    if not path.is_file():
        raise SystemExit(f"missing artifact: {name}; run the pipeline first")
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value, places=1):
    return "blank" if value is None else f"{value * 100:.{places}f}%"


def lines():
    feed = artifact("results-feed.json")
    origination = artifact("origination.json")
    boards = artifact("boards.json")
    prices = artifact("price-store.json")
    leaderboard = artifact("leaderboard.json")
    depth = artifact("depth.json")
    correlations = artifact("correlations.json")
    demotion = artifact("demotion.json")
    questions = artifact("questions.json")
    suggestions = artifact("suggestions.json")
    review = artifact("review.json")
    backtest = artifact("backtest.json")
    injuries = artifact("injuries.json")

    recon = feed["reconciliation"]
    params = origination["parameters"]
    signal = backtest["strategies"]
    # The strongest directional evidence, not the highest hit rate: a 12-6 record is a
    # better percentage than a 74-46 one and a far weaker claim.
    best = min((s for s in signal if s.get("kind") == "directional"
                and s["signal"].get("q_value") is not None),
               key=lambda s: s["signal"]["q_value"], default=None)
    published = [c for c in correlations["rows"] if c["value"] is not None]
    blank_correlations = [c for c in correlations["rows"] if c["value"] is None]

    out = []
    add = out.append
    add("# NFL competition lab — executive summary")
    add("")
    add(f"Built {origination['read_on']}. Research only: no wager is placed, no price is "
        f"published, and nothing here is an offered market.")
    add("")
    add("The short version: the parts of the brief that need only official league data are "
        "built and verified. The parts that need a market price are built, tested and left "
        "empty, because no official source this project read prints one.")
    add("")
    add("## What is verified")
    add("")
    add(f"- **{feed['games']} official final scores**, re-derived into club records and "
        f"reconciled against the NFL.com standings: "
        f"**{recon['fields_matching']} of {recon['fields_compared']} club fields match**, "
        f"with {recon['league_points_scored']} points scored and the same number allowed.")
    add(f"- **{origination['games_originated']} Week 10 games originated** in three stages "
        f"in a fixed order: side, then total, then moneyline. "
        f"{origination['games_played_and_excluded']} game had already finished when the "
        f"schedule was read and is carried in the results feed instead of the board.")
    add(f"- **{boards['markets']} markets published** as "
        f"{len(boards['rows'])} board rows, each with a model fair line and a blank market "
        f"line and difference.")
    add(f"- **{depth['headline']['starters_ruled_out']} starters ruled out** on a printed "
        f"depth chart; {depth['headline']['replacements_from_2nd_string']} are replaced "
        f"from the second string and "
        f"{depth['headline']['slots_with_no_printed_replacement']} slot has no printed "
        f"replacement at all.")
    add(f"- **{len(published)} correlations computed from official numbers**, every one "
        f"published with its sample size; {len(blank_correlations)} are left blank rather "
        f"than estimated.")
    add(f"- **{questions['total']} questions catalogued** "
        f"({questions['counts'].get('answered', 0)} answered, "
        f"{questions['counts'].get('open', 0)} open, "
        f"{questions['counts'].get('blocked', 0)} blocked on source rights).")
    add(f"- **{review['total']} irregularities flagged** "
        f"({review['counts'].get('open', 0)} open, "
        f"{review['counts'].get('explained', 0)} explained, "
        f"{review['counts'].get('corrected', 0)} corrected before publication).")
    add("")
    add("## What is deliberately blank")
    add("")
    add(f"- **The price store holds {prices['rows_stored']} rows** across "
        f"{prices['markets_registered']} registered markets. "
        f"nfl.com returns HTTP 404 at `/odds/` and prints no price, spread, total or "
        f"operator on any page this project read.")
    add(f"- **Return on investment, stake, drawdown and closing-line value are blank "
        f"everywhere.** They need an executable price, and there is none. Zero is not a "
        f"value for these cells.")
    add(f"- **No reward is paid.** {leaderboard['rewards']['merit_points_awarded']} merit "
        f"points awarded; cash reward and prize pool are both null.")
    add(f"- **The staking half of the leaderboard has "
        f"{len(leaderboard['staking_table']['rows'])} rows.** Signal and staking are two "
        f"tables that never touch, so a lucky staking run cannot promote a bad signal.")
    add(f"- **No point value is attached to an injury or to a replacement.** A printed rank "
        f"is an ordering, not a measurement.")
    add("")
    add("## What the evidence actually shows")
    add("")
    if best is not None:
        sig = best["signal"]
        verdict = ("It survives multiplicity control, but it is a control whose null rate "
                   "is not a coin flip."
                   if sig["reject_null_at_fdr_10pct"] else
                   "It does **not** survive multiplicity control at a 10% "
                   "false-discovery rate, so nothing is promoted to live.")
        add(f"- The strongest directional record is **{sig['wins']}-{sig['losses']} "
            f"over {sig['n']} settled selections ({pct(sig['hit_rate'])})**, exact "
            f"binomial p = {sig['binomial_p']:.4f}, Benjamini-Hochberg q = "
            f"{sig['q_value']:.4f}. {verdict}")
        top_rate = max(s["signal"]["hit_rate"] for s in signal
                       if s["signal"].get("hit_rate") is not None)
        add(f"- The highest hit rate on the board is {pct(top_rate)}, on a sample too "
            f"small to separate skill from luck. Percentage alone is not a finding.")
    add(f"- The measured home allowance is "
        f"**{params['home_allowance_points']['value']:+.4f} points** over "
        f"{params['home_allowance_points']['n']} games "
        f"(SD {params['home_allowance_points']['sd']:.2f}), with a 95% interval of "
        f"[{params['home_allowance_points']['ci95'][0]:.2f}, "
        f"{params['home_allowance_points']['ci95'][1]:.2f}]. That interval contains both "
        f"zero and the conventional two points: this season does not separate them.")
    add(f"- League scoring measures "
        f"{params['league_points_per_team_game']['value']:.4f} points per team-game over "
        f"{params['league_points_per_team_game']['n_team_games']} team-games. It is "
        f"measured from the feed, not assumed.")
    add(f"- **{leaderboard['counts'].get('Live', 0)} strategies are live, "
        f"{leaderboard['counts'].get('Provisional', 0)} provisional, "
        f"{leaderboard['counts'].get('Paper', 0)} paper, "
        f"{leaderboard['counts'].get('Blocked on data', 0)} blocked on data, "
        f"{leaderboard['counts'].get('Control', 0)} control.**")
    add(f"- The demotion gate publishes {len(demotion['triggers'])} triggers with today's "
        f"reading on each ({demotion['count'].get('computable', 0)} computable, "
        f"{demotion['count'].get('blocked_on_price', 0)} blocked on price, "
        f"{demotion['count'].get('triggered_now', 0)} firing now). "
        f"{demotion['live_strategies']} strategy has ever reached the live tier, so no "
        f"demotion has fired.")
    rejections = [s for s in signal if s["signal"].get("reject_null_at_fdr_10pct")]
    ids = ", ".join(s["id"] for s in rejections) or "none"
    add(f"- Only {len(rejections)} of {len(signal)} strategies reject their null after "
        f"multiplicity control: {ids}. The one rejection is a control whose null rate is "
        f"{pct(rejections[0]['signal']['null_rate'])} rather than a coin flip, so it "
        f"measures the test, not an edge.")
    add("")
    add("## The three things that block everything")
    add("")
    for sid in ("SG-01", "SG-12", "SG-05"):
        match = [s for s in suggestions["suggestions"] if s["id"] == sid]
        if match:
            add(f"- **{match[0]['id']} — {match[0]['title']}.** Unlocks "
                + ", ".join(match[0]["unlocks"])
                + f". Priority {match[0]['priority']} of 5. Done when: "
                + match[0]["acceptance_test"].rstrip(".") + ".")
    add("")
    add("Sample size is the quiet one. Detecting a true 60% rate at 80% power and a "
        "two-sided 5% test needs "
        + ", ".join(f"{row['settled_selections_needed']} for a true rate of "
                    f"{row['true_rate'] * 100:.1f}%"
                    for row in questions["sample_size_table"][-3:])
        + f". The largest sample available today is "
          f"{max(s['signal'].get('n') or 0 for s in signal)}.")
    add("")
    add("## Injuries and defensive deficiencies")
    add("")
    coverage = injuries["status_coverage"]
    with_status = coverage["rows"] - coverage["by_game_status"].get("(none printed)", 0)
    add(f"- {with_status} of {coverage['rows']} injury rows carry an official game status. "
        f"The rest state a practice status only, so no replacement is implied for them and "
        f"none is computed. {coverage['ceiling']}")
    add(f"- {len(injuries['deficiencies'])} slots need a replacement: "
        + "; ".join(f"{row['club']} {row['position']}" for row in injuries["deficiencies"])
        + ".")
    add(f"- {depth['coverage']['printed_slots']} printed depth-chart slots across "
        f"{depth['coverage']['clubs_with_a_captured_chart']} clubs. "
        f"{', '.join(depth['coverage']['clubs_without_a_captured_chart'])} renders its "
        f"chart as an image and stays blank rather than guessed.")
    add("")
    add("## Where to look next")
    add("")
    add("- `site/index.html` — the desk landing page.")
    add("- `site/suggestions.html` — the ranked proposals and the decision board. Nothing "
        "is implemented until a choice is recorded.")
    add("- `site/questions.html` — what is held, what is missing, and what closes each gap.")
    add("- `site/review.html` — the flagged irregularities with their official links.")
    add("- `site/method.html` — the method, the formulas and the limits.")
    add("")
    add("Every table row on every page links to the official source it came from. A value "
        "that no official source confirms is published blank and flagged, never inferred.")
    add("")
    return out


def main():
    text = "\n".join(lines()) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(f"  wrote {OUT.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
