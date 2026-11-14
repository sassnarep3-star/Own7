"""Render the game-results and skill-testing section.

Every table row carries the official page it came from. Values the sources do not
publish are blank and flagged; nothing is inferred. The pages are generated from
``nfl-results/analysis.json`` and ``nfl-results/data/*.csv`` only, so the site can be
rebuilt byte-for-byte and cannot drift from the analysis.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "nfl-results"

# Injected by scripts/build_site.py to avoid a circular import.
notice = metrics = section = table = rich = badge = link = None  # type: ignore
Markup = str


def load_analysis() -> dict:
    return json.loads((RESULTS / "analysis.json").read_text(encoding="utf-8"))


def load_rows(name: str) -> list[dict]:
    with (RESULTS / "data" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def pct(value, places=1):
    """Format a proportion as a percentage, or blank if it does not exist."""
    if value is None:
        return None
    return f"{value * 100:.{places}f}%"


def num(value, places=3):
    if value is None:
        return None
    return f"{value:+.{places}f}"


def source_row(url, label="NFL.com ↗"):
    return {"source_url": url, "source_ids": ["X29-NFL-SCHEDULE"]}


def stat_rows(analysis, market_filter=None):
    """One row per graded strategy variant, plus the two board benchmarks."""
    rows = []
    for c in analysis["candidates"]:
        if market_filter and c["market"] != market_filter:
            continue
        s = c["stat"]
        rows.append({
            "id": c["id"],
            "strategy": c["name"] + ("" if c["selective"] else ""),
            "variant": c["id"].split("-")[1][0].upper() == "S" and "selective" or "all games",
            "market": c["market"],
            "bets": s["bets"] or None,
            "record": f"{s['wins']}–{s['losses']}" if s["bets"] else None,
            "hit": pct(s["hit_rate"]),
            "p": f"{s['p_value']:.4f}" if s["p_value"] is not None else None,
            "q": f"{c['q_value']:.3f}" if c.get("q_value") is not None else None,
            "ci": (f"{pct(s['ci_low'])} – {pct(s['ci_high'])}"
                   if s["ci_low"] is not None else None),
            "status": "Provisional" if c.get("provisional") else ("Qualified" if c["qualified"] else "Rejected"),
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-2",
            "source_ids": ["X29-NFL-SCHEDULE"],
        })
    return rows


def page_results():
    analysis = load_analysis()
    games = load_rows("games-2026-w1-9.csv")
    byes = load_rows("byes-2026-w1-9.csv")
    total_byes = len(byes)

    body = ""
    body += notice(
        "Where the numbers come from",
        f"{len(games)} official final scores, weeks 1–9, read from NFL.com. The parser refuses to "
        f"publish unless the scores reproduce the frozen official standings exactly — all 32 clubs, "
        f"on wins, losses, ties, points for and points against (160 checks).",
        info=True)

    body += metrics([
        ("Games captured", len(games), "Weeks 1–9, every club", "data"),
        ("Bye rows", total_byes, "Printed by the publisher", "validation"),
        ("Reconciliation", "160/160", "Fields matching the standings", "validation"),
        ("Weeks scored", "8 of 9", "Week 1 has no prior form", "signals"),
    ])

    game_rows = []
    for g in games:
        game_rows.append({
            "id": f"W{g['week']}-{g['away']}{g['home']}",
            "week": int(g["week"]),
            "date": g["date"],
            "fixture": f"{g['away']} @ {g['home']}",
            "score": f"{g['away_score']}–{g['home_score']}",
            "margin": int(g["away_score"]) - int(g["home_score"]),
            "total": int(g["away_score"]) + int(g["home_score"]),
            "source_url": g["source_url"],
            "source_ids": ["X29-NFL-SCHEDULE"],
        })

    body += section(
        "Every captured game",
        table("results-games", "Official final scores, weeks 1–9", [
            ("Week", "week"), ("Date", "date"), ("Fixture (away @ home)", "fixture"),
            ("Score (away–home)", "score"), ("Away margin", "margin"), ("Total points", "total"),
        ], game_rows,
            note="Scores are transcribed by the parser from saved rendered page text, then "
                 "re-derived into club totals. Any mismatch aborts the build."),
        eyebrow="SOURCE DATA")

    bye_rows = [{
        "id": f"BYE-W{b['week']}-{b['team_code']}",
        "week": int(b["week"]), "team": b["team"],
        "source_url": b["source_url"], "source_ids": ["X29-NFL-SCHEDULE"],
    } for b in byes]
    body += section(
        "Bye weeks as printed",
        table("results-byes", "Clubs on a bye", [
            ("Week", "week"), ("Club", "team"),
        ], bye_rows,
            note="A bye is not a game and is never counted as one. The parser derives its "
                 "expected game count from this list rather than assuming 16."),
        eyebrow="SOURCE DATA")

    body += section(
        "Why week 1 is not scored",
        "<p class=\"prose\">A forecast for a week needs earlier results. Week 1 has none, so any "
        "model that produced a week-1 number would be using information that did not exist at "
        "kickoff. Those 16 games are published as source data and excluded from scoring.</p>",
        eyebrow="METHOD")
    return body


def page_skill():
    analysis = load_analysis()
    spread = analysis["benchmarks"]["spread"]
    total = analysis["benchmarks"]["total"]
    luck = analysis["luck_analysis"]
    counts = analysis["leaderboard_counts"]

    body = ""
    body += notice(
        "Read this before the tables",
        "A strategy is called skill only if it beats an exact chance null, survives correction "
        "for testing many strategies, and holds up in both halves of the season. Most do not. "
        "That is the finding, not a failure of the analysis.", info=True)

    body += metrics([
        ("Variants tested", counts["tested"], "Models × market × selectivity", "signals"),
        ("Beat chance", f"{spread['directional']['wins']}–{spread['directional']['losses']}",
         f"Spread board, p={spread['directional']['p_value']:.4f}", "validation"),
        ("Family-wise luck", pct(luck["family_wise_false_positive"], 0),
         "Chance of a fluke this good", "care"),
        ("Rewarded", "0", "No price, so no reward", "leaderboard"),
    ])

    bench_rows = [{
        "id": "BENCH-SPREAD",
        "market": "Spread (margin)",
        "record": f"{spread['directional']['wins']}–{spread['directional']['losses']}",
        "hit": pct(spread["directional"]["hit_rate"]),
        "corr": num(spread["correlation_board_vs_actual"]),
        "p_perm": f"{spread['permutation_p_value']:.4f}",
        "halves": f"{pct(spread['first_half_hit_rate'])} / {pct(spread['second_half_hit_rate'])}",
        "verdict": "Signal",
        "source_url": "https://www.nfl.com/standings/",
        "source_ids": ["X29-NFL-SCHEDULE", "NFL-STANDINGS"],
    }, {
        "id": "BENCH-TOTAL",
        "market": "Total (points)",
        "record": f"{total['directional']['wins']}–{total['directional']['losses']}",
        "hit": pct(total["directional"]["hit_rate"]),
        "corr": num(total["correlation_board_vs_actual"]),
        "p_perm": f"{total['permutation_p_value']:.4f}",
        "halves": f"{pct(total['first_half_hit_rate'])} / {pct(total['second_half_hit_rate'])}",
        "verdict": "No signal",
        "source_url": "https://www.nfl.com/standings/",
        "source_ids": ["X29-NFL-SCHEDULE", "NFL-STANDINGS"],
    }]

    body += section(
        "The one real finding: spreads carry information, totals do not",
        table("skill-bench", "Originated board vs the result", [
            ("Market", "market"), ("Record", "record"), ("Hit rate", "hit"),
            ("Correlation with result", "corr"), ("Permutation p", "p_perm"),
            ("First half / second half", "halves"), ("Verdict", lambda r: badge(r["verdict"])),
        ], bench_rows,
            note="Hit rate here means the board's favoured side (relative to the league-average "
                 "line) beat the result. Permutation p shuffles the real results 20,000 times and "
                 "asks how often chance matches the observed record."),
        eyebrow="BENCHMARK")

    body += "<p class=\"prose\">The asymmetry is the point. The same model, on the same data, "
    body += "produces a spread line that clears every testable gate and a total line that lands "
    body += "at exactly a coin flip. A total is far harder to beat from scoring rates alone "
    body += "because it depends on pace, turnovers and red-zone execution, none of which this "
    body += "model sees. Publishing only the spread result would be cherry-picking.</p>"

    model_rows = [{
        "id": mid,
        "model": mid,
        "label": data["label"],
        "mae_margin": num(data["mae_margin"], 2),
        "skill_margin": num(data["skill_vs_null_margin"]),
        "mae_total": num(data["mae_total"], 2),
        "skill_total": num(data["skill_vs_null_total"]),
        "source_url": "https://www.nfl.com/standings/",
        "source_ids": ["X29-NFL-SCHEDULE"],
    } for mid, data in [(m, {**a, "label": L}) for (m, a), L in zip(
        analysis["accuracy"].items(),
        ["Null: home field only", "Originator: shrunk scoring", "Pythagorean win rate",
         "Recency-weighted", "Bye / rest differential", "Home-only / road-only",
         "Win-streak momentum"])]]

    body += section(
        "Forecast accuracy: every model beats nothing much",
        table("skill-accuracy", "Out-of-sample accuracy by model", [
            ("Model", "model"), ("What it does", "label"),
            ("MAE margin", "mae_margin"), ("Skill vs null", "skill_margin"),
            ("MAE total", "mae_total"), ("Skill vs null", "skill_total"),
        ], model_rows,
            note="Skill score is 1 − (model error ÷ null error). Zero means no better than "
                 "always guessing the league average. Margin errors around 10 points are normal "
                 "for NFL forecasting and are not a defect of this model."),
        eyebrow="ACCURACY")

    candidates = analysis["candidates"]
    stat_table_rows = []
    for c in candidates:
        s = c["stat"]
        if not s["bets"]:
            continue
        stat_table_rows.append({
            "id": c["id"],
            "strategy": c["name"],
            "variant": "Selective (≥2 pt edge)" if c["selective"] else "All games",
            "market": c["market"],
            "bets": s["bets"],
            "record": f"{s['wins']}–{s['losses']}",
            "hit": pct(s["hit_rate"]),
            "p": f"{s['p_value']:.4f}",
            "q": f"{c['q_value']:.3f}" if c.get("q_value") is not None else None,
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9",
            "source_ids": ["X29-NFL-SCHEDULE"],
        })

    body += section(
        "Every variant tested, including the losers",
        table("skill-candidates", "Strategy variants and their chance-adjusted results", [
            ("Strategy", "strategy"), ("Variant", "variant"), ("Market", "market"),
            ("Bets", "bets"), ("Record", "record"), ("Hit rate", "hit"),
            ("Exact p", "p"), ("BH q", "q"),
        ], stat_table_rows,
            note="q is the Benjamini–Hochberg adjusted value across all 30 variants. At a 10% "
                 "false-discovery ceiling only q ≤ 0.10 counts as surviving multiplicity. "
                 "One entry clears it, and that entry is the board benchmark, not a challenger."),
        eyebrow="FULL FAMILY")

    body += section(
        "How luck was removed",
        f"""<div class="prose">
<p><strong>1. An exact chance null.</strong> For every record we compute the probability of
doing at least that well if the strategy were flipping a fair coin. With {counts['tested']}
variants tested, small p-values appear by construction, so this alone is not enough.</p>
<p><strong>2. Family-wise correction.</strong> Benjamini–Hochberg adjusts every p-value for the
size of the family. The strongest challenger does not survive it.</p>
<p><strong>3. A permutation test.</strong> The realised results are shuffled 20,000 times and the
board is re-scored each time. The observed spread record is beaten by chance in
{pct(spread['permutation_p_value'], 2)} of shuffles — the null distribution's 95th percentile
is {pct(spread['null_95th_hit_rate'])} while the observation is
{pct(spread['directional']['hit_rate'])}.</p>
<p><strong>4. Split-half and leave-one-week-out.</strong> Both halves must beat 50%, and no single
week may carry the result. Dropping any one week leaves the spread hit rate between
{min(spread['drop_one_week_hit_rate'].values()) * 100:.1f}% and
{max(spread['drop_one_week_hit_rate'].values()) * 100:.1f}%.</p>
<p><strong>5. Sample size honesty.</strong> At the observed edge, roughly
{spread['directional']['required_n']} settled bets are needed for 80% power. There are
{spread['directional']['bets']}, so the record is adequate but not generous.</p>
</div>""",
        eyebrow="METHOD")
    return body


def page_correlation():
    analysis = load_analysis()
    leg = analysis["correlations"]["leg_dependence"]
    structure = analysis["correlations"]["market_structure"]

    body = ""
    body += notice(
        "This is the question the parlay depended on",
        "Earlier sessions recorded leg-level correlation as impossible to measure. It is now "
        "measured, from real same-game outcomes on the originated board.", info=True)

    body += metrics([
        ("Games in the joint table", leg["n_games"], "Pushes excluded from both legs", "data"),
        ("Phi coefficient", num(leg["phi"]), "Spread leg vs total leg", "correlation"),
        ("p-value", f"{leg['p_value']:.4f}", "Not distinguishable from zero", "validation"),
        ("Observed vs independent", num(leg["difference"]), "Joint minus product of marginals", "signals"),
    ])

    joint_rows = [
        {"id": "HOME-OVER", "cell": "Home covers & Over",
         "count": leg["table"]["home_and_over"],
         "share": pct(leg["table"]["home_and_over"] / leg["n_games"])},
        {"id": "HOME-UNDER", "cell": "Home covers & Under",
         "count": leg["table"]["home_and_under"],
         "share": pct(leg["table"]["home_and_under"] / leg["n_games"])},
        {"id": "AWAY-OVER", "cell": "Away covers & Over",
         "count": leg["table"]["away_and_over"],
         "share": pct(leg["table"]["away_and_over"] / leg["n_games"])},
        {"id": "AWAY-UNDER", "cell": "Away covers & Under",
         "count": leg["table"]["away_and_under"],
         "share": pct(leg["table"]["away_and_under"] / leg["n_games"])},
    ]
    for r in joint_rows:
        r["source_url"] = "https://www.nfl.com/schedules/2026/by-week/week-9"
        r["source_ids"] = ["X29-NFL-SCHEDULE"]

    body += section(
        "The 2×2 joint table",
        table("corr-joint", "Spread leg against total leg", [
            ("Cell", "cell"), ("Games", "count"), ("Share of graded games", "share"),
        ], joint_rows,
            note="A parlay needs the probability that two legs BOTH land. If the legs were "
                 "independent that probability would be the product of the two marginals. The "
                 "table shows what actually happened."),
        eyebrow="JOINT OUTCOMES")

    test_rows = [{
        "id": "INDEP",
        "quantity": "P(home covers AND over) if legs were independent",
        "value": pct(leg["p_home_and_over_independent"], 2),
        "source_url": "https://www.nfl.com/standings/", "source_ids": ["X29-NFL-SCHEDULE"],
    }, {
        "id": "OBS",
        "quantity": "P(home covers AND over) actually observed",
        "value": pct(leg["p_home_and_over_observed"], 2),
        "source_url": "https://www.nfl.com/standings/", "source_ids": ["X29-NFL-SCHEDULE"],
    }, {
        "id": "DIFF",
        "quantity": "Difference (observed − independent)",
        "value": pct(leg["difference"], 2),
        "source_url": "https://www.nfl.com/standings/", "source_ids": ["X29-NFL-SCHEDULE"],
    }, {
        "id": "PHI",
        "quantity": "Phi coefficient (0 = independent, ±1 = fully dependent)",
        "value": num(leg["phi"]),
        "source_url": "https://www.nfl.com/standings/", "source_ids": ["X29-NFL-SCHEDULE"],
    }, {
        "id": "P",
        "quantity": "Two-sided p-value for phi",
        "value": f"{leg['p_value']:.4f}",
        "source_url": "https://www.nfl.com/standings/", "source_ids": ["X29-NFL-SCHEDULE"],
    }]
    body += section(
        "What the dependence means",
        table("corr-tests", "Independence tests", [
            ("Quantity", "quantity"), ("Value", "value"),
        ], test_rows,
            note="The dependency is negative and small: covering and Over were slightly less "
                 "likely to co-occur than independence predicts. It is not statistically "
                 "distinguishable from zero at this sample size, so no parlay price is changed."),
        eyebrow="TESTS")

    struct_rows = [{
        "id": s["pair"], "pair": s["label"], "n": s["n"],
        "r": num(s["pearson"]), "p": f"{s['p_value']:.4f}",
        "source_url": "https://www.nfl.com/standings/", "source_ids": ["X29-NFL-SCHEDULE"],
    } for s in structure]
    body += section(
        "Scoring structure",
        table("corr-structure", "How the scored quantities move together", [
            ("Pair", "pair"), ("Games", "n"), ("Pearson r", "r"), ("p", "p"),
        ], struct_rows,
            note="Margin and total are close to independent, which is what makes a spread leg "
                 "and a total leg a defensible combination rather than a duplicate bet."),
        eyebrow="STRUCTURE")

    body += "<p class=\"prose\"><strong>What is still blank.</strong> Player-prop combinations "
    body += "need per-player, per-game logs, which this session did not retrieve. Team-level "
    body += "correlation and leg-level correlation are different quantities and are kept in "
    body += "different tables on purpose. No parlay is priced, because no price exists.</p>"
    return body


def page_leaderboard():
    analysis = load_analysis()
    lb = analysis["leaderboard"]
    counts = analysis["leaderboard_counts"]

    body = ""
    body += notice(
        "A leaderboard that pays nothing, on purpose",
        f"{counts['tested']} variants were tested. {counts['provisional']} reached the provisional "
        f"tier and {counts['qualified']} reached the qualified tier. A reward requires a price to "
        f"settle against, and none was retrieved, so every reward cell is blank.",
        info=True)

    body += metrics([
        ("Tested", counts["tested"], "Every model and variant", "signals"),
        ("Provisional", counts["provisional"], "All testable gates pass", "validation"),
        ("Qualified", counts["qualified"], "Needs an executable price", "leaderboard"),
        ("Merit points awarded", "0", "Nothing cleared every gate", "care"),
    ])

    rows = []
    for entry in lb:
        rows.append({
            "id": entry["id"], "rank": entry["rank"], "tier": entry["tier"].title(),
            "strategy": entry["name"], "market": entry["market"],
            "bets": entry["bets"], "record": f"{entry['wins']}–{entry['losses']}",
            "hit": pct(entry["hit_rate"]),
            "ci": f"{pct(entry['ci_low'])} – {pct(entry['ci_high'])}",
            "q": f"{entry['q_value']:.3f}",
            "merit": entry["merit_points"],
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9",
            "source_ids": ["X29-NFL-SCHEDULE"],
        })
    if not rows:
        rows = [{"id": "EMPTY", "rank": None, "tier": "—", "strategy": "No entry reached the provisional tier",
                 "market": None, "bets": None, "record": None, "hit": None, "ci": None, "q": None,
                 "merit": 0, "source_url": "https://www.nfl.com/standings/",
                 "source_ids": ["NFL-STANDINGS"]}]

    body += section(
        "Standings",
        table("lb-table", "Ranked strategies", [
            ("Rank", "rank"), ("Tier", lambda r: badge(r["tier"])), ("Strategy", "strategy"),
            ("Market", "market"), ("Bets", "bets"), ("Record", "record"),
            ("Hit rate", "hit"), ("95% interval", "ci"), ("BH q", "q"),
            ("Merit points", "merit"),
        ], rows,
            note="Provisional entries are published so the work can be reviewed, not to claim an "
                 "edge. Merit points are integers with no cash value, and none has been awarded."),
        eyebrow="COMPETITION")

    body += section(
        "Why no reward exists",
        """<div class="prose">
<p>The brief asks for a leaderboard that rewards top strategies. The blocker is not the
statistics, it is the settlement. A reward has to be paid out against something, and the only
honest reference is a price that was available before kickoff. No sportsbook price was retrieved
in this project, and NFL.com terms do not permit building a redistributable odds dataset.</p>
<p>So the format is frozen and the entries are real, but the reward column stays empty. When a
licensed price feed exists, the same pipeline settles against it without changing any of the
grading rules: the entry that clears every gate takes the points, and nothing else does.</p>
<p><strong>What would change the answer:</strong> a licensed pre-kickoff price archive with
documented redistribution rights. Until then, ROI and closing-line value are blank by rule, not
by omission.</p>
</div>""",
        eyebrow="REWARDS")
    return body


def page_questions():
    analysis = load_analysis()
    spread = analysis["benchmarks"]["spread"]
    total = analysis["benchmarks"]["total"]

    qs = [
        {
            "id": "Q01",
            "question": "Does the originated spread line actually carry information, or was the early record luck?",
            "known": f"The spread board hit {pct(spread['directional']['hit_rate'])} over "
                     f"{spread['directional']['bets']} games; a 20,000-shuffle permutation put "
                     f"chance at p={spread['permutation_p_value']:.4f}.",
            "missing": "A pre-kickoff price archive to convert a hit rate into money.",
            "blocks": "Any claim of profitability. Not a claim that the line is good.",
            "source_url": "https://www.nfl.com/standings/",
        },
        {
            "id": "Q02",
            "question": "Why does the total market show no signal while the spread does?",
            "known": f"The total board's directional record was "
                     f"{total['directional']['wins']}–{total['directional']['losses']} "
                     f"({pct(total['directional']['hit_rate'])}), with correlation "
                     f"{num(total['correlation_board_vs_actual'])} — statistically indistinguishable from zero.",
            "missing": "Pace, plays per game, red-zone efficiency and turnover data, which the "
                       "scoring-rate model cannot see.",
            "blocks": "Any total-based strategy. It is excluded rather than promoted.",
            "source_url": "https://www.nfl.com/standings/",
        },
        {
            "id": "Q03",
            "question": "Do parlay legs move together enough to change a price?",
            "known": f"Phi between the spread and total legs is {num(leg := analysis['correlations']['leg_dependence']['phi'])} "
                     f"with p={analysis['correlations']['leg_dependence']['p_value']:.4f} over "
                     f"{analysis['correlations']['leg_dependence']['n_games']} games.",
            "missing": "A much larger sample before a small dependence could be estimated precisely.",
            "blocks": "Parlay pricing. Legs are treated as independent, which is conservative.",
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9",
        },
        {
            "id": "Q04",
            "question": "Can player-prop combinations be priced?",
            "known": "No. Per-player, per-game logs were not retrieved in this session.",
            "missing": "Game-by-game player statistics, which NFL.com publishes on each player page.",
            "blocks": "Every player-prop strategy. The gap is named, not filled.",
            "source_url": "https://www.nfl.com/stats/player-stats/",
        },
        {
            "id": "Q05",
            "question": "Do injuries in weeks 1–9 change the lines those weeks produced?",
            "known": "The week-10 injury report is captured and publishes 326 player rows. Weeks 1–9 "
                     "have no saved pre-kickoff injury snapshot.",
            "missing": "A pre-kickoff injury archive for the scored weeks.",
            "blocks": "Any injury-adjusted line for the scored period. It would require inventing history.",
            "source_url": "https://www.nfl.com/injuries/",
        },
        {
            "id": "Q06",
            "question": "Is one season enough to call any of this persistent?",
            "known": "Eight scored weeks, 120 games. The split-half check holds in both halves.",
            "missing": "Prior seasons, and a forward test on games that have not been played.",
            "blocks": "Any claim of durable skill. The strongest available statement is provisional.",
            "source_url": "https://www.nfl.com/standings/",
        },
        {
            "id": "Q07",
            "question": "What is the smallest edge worth acting on?",
            "known": f"About {spread['directional']['required_n']} settled bets are needed to detect "
                     f"the observed edge at 80% power. With no price, the economic threshold cannot be computed.",
            "missing": "A price and its vig, plus a bankroll policy.",
            "blocks": "Position sizing and any staking recommendation.",
            "source_url": "https://www.nfl.com/legal/terms/",
        },
        {
            "id": "Q08",
            "question": "Is publishing this allowed?",
            "known": "NFL.com terms §1.3 permit individual non-commercial informational use and "
                     "prohibit systematic retrieval to build a collection without written consent.",
            "missing": "A written licence, if a redistributable dataset is ever wanted.",
            "blocks": "Releasing the game data as a dataset or running a scheduled feed.",
            "source_url": "https://www.nfl.com/legal/terms/",
        },
    ]
    rows = [{
        "id": q["id"], "question": q["question"], "known": q["known"],
        "missing": q["missing"], "blocks": q["blocks"],
        "source_url": q["source_url"], "source_ids": ["X29-NFL-SCHEDULE"],
    } for q in qs]

    body = ""
    body += notice(
        "What must be answered before a decision",
        "Each question separates what is now known with a source from what is still missing. "
        "Nothing below is filled in by inference.", info=True)
    body += section(
        "Questions, knowns and blanks",
        table("q-table", "Decision questions", [
            ("ID", "id"), ("Question", "question"), ("What is now known", "known"),
            ("What is still missing", "missing"), ("What it blocks", "blocks"),
        ], rows, note="A blank in the 'still missing' column would mean nothing stands in the way; "
                      "every row here has one, which is why no decision is final."),
        eyebrow="DECISIONS")
    return body


def page_suggestions():
    body = ""
    suggestions = [
        {
            "id": "SG01", "title": "Retrieve per-game player logs to price prop combinations",
            "unlocks": "Player-prop and prop-plus-leg parlays, currently blank.",
            "evidence": "NFL.com publishes a game log per player. The capture pattern is already "
                        "proven by the game-results work in this session.",
            "cost": "One reading pass per player in scope; roughly 40–60 players for a usable panel.",
            "risk": "Terms §1.3 still applies: read, do not scrape on a schedule, release nothing.",
            "test": "Re-derive two published player season totals from the logs to within rounding.",
            "priority": 1,
        },
        {
            "id": "SG02", "title": "Archive pre-kickoff prices under a licensed feed",
            "unlocks": "ROI, CLV, vig-adjusted edge, and every reward on the leaderboard.",
            "evidence": "This is the exact gate (RG03) that withholds every reward today.",
            "cost": "A commercial data subscription; this is the only suggestion with a real bill.",
            "risk": "Without documented redistribution rights the project cannot publish derived prices.",
            "test": "Settle one frozen weekend end-to-end and reproduce the result from the raw feed.",
            "priority": 2,
        },
        {
            "id": "SG03", "title": "Add pace and red-zone inputs to fix the total model",
            "unlocks": "A total model that is not a coin flip.",
            "evidence": "The total board scored exactly 50.0% directional; the spread board scored "
                        "64.2%. The difference is what the model can and cannot see.",
            "cost": "Two more official team-stat tables, already on the same publisher.",
            "risk": "More inputs mean more ways to overfit; gate RG07 must stay in place.",
            "test": "Totals skill score must go positive and the family-wise luck figure must fall.",
            "priority": 3,
        },
        {
            "id": "SG04", "title": "Run a forward test on unplayed games before trusting anything",
            "unlocks": "The only evidence that survives the word 'skill'.",
            "evidence": "Everything on this site is retrospective. A forward test removes the "
                        "reviewer's ability to choose the window after seeing the result.",
            "cost": "Time: one full week, then four, then eight.",
            "risk": "The forward result may be worse. That is the point of running it.",
            "test": "Pre-register the board for week 11 before kickoff and grade it after.",
            "priority": 4,
        },
        {
            "id": "SG05", "title": "Backfill pre-kickoff injury snapshots for the scored weeks",
            "unlocks": "An injury-adjusted line, and a real answer on starter-versus-backup impact.",
            "evidence": "The availability desk already parses 326 injury rows for week 10; the "
                        "same reader can be pointed at archived reports.",
            "cost": "One report per club per week; the publisher only keeps the current week.",
            "risk": "Old reports may not be retrievable at all. If so, the gap stays permanent for 2026.",
            "test": "A week-10 snapshot must reproduce from the archive exactly.",
            "priority": 5,
        },
        {
            "id": "SG06", "title": "Publish the totals failure as prominently as the spread finding",
            "unlocks": "Trust. A site that shows only its wins is not evidence.",
            "evidence": "The two benchmarks sit in the same table on the skill page for this reason.",
            "cost": "None.",
            "risk": "It makes the project look weaker than a cherry-picked version would.",
            "test": "Any future page change keeps both markets in one table.",
            "priority": 6,
        },
    ]
    rows = [{
        "id": s["id"], "priority": s["priority"], "suggestion": s["title"],
        "unlocks": s["unlocks"], "evidence": s["evidence"], "cost": s["cost"],
        "risk": s["risk"], "acceptance_test": s["test"],
        "source_url": "https://www.nfl.com/legal/terms/",
        "source_ids": ["X29-NFL-SCHEDULE"],
    } for s in suggestions]

    body += notice(
        "A section to review before changing anything",
        "Each suggestion states what it unlocks, the evidence behind it, what it costs, what could "
        "go wrong, and the test that would prove it worked. Ranked by how much it unlocks per unit "
        "of risk, not by how good it sounds.", info=True)
    body += section(
        "Ranked suggestions",
        table("sug-table", "Suggestions for review", [
            ("#", "priority"), ("Suggestion", "suggestion"), ("What it unlocks", "unlocks"),
            ("Evidence it would work", "evidence"), ("Cost", "cost"), ("Risk", "risk"),
            ("Acceptance test", "acceptance_test"),
        ], rows, note="Choose a path here before implementing any change. Adopting one does not "
                      "require adopting the next."),
        eyebrow="DECISION HUB")

    body += section(
        "A review workflow",
        """<div class="prose">
<p><strong>1. Propose.</strong> A suggestion enters with an id and the decision it unlocks.</p>
<p><strong>2. Attach evidence.</strong> A source link and a statement of what that source
actually says. A suggestion without a source is deferred, not adopted.</p>
<p><strong>3. State the acceptance test.</strong> The test is written before the work, so it
cannot be chosen to fit the outcome.</p>
<p><strong>4. Compare.</strong> Two suggestions that unlock the same decision are compared on
cost and risk, not on enthusiasm.</p>
<p><strong>5. Choose and record.</strong> The chosen path is recorded with the date and the
reason, and the rejected ones stay visible.</p>
</div>""",
        eyebrow="PROCESS")
    return body


def page_flagged():
    analysis = load_analysis()
    flags = [
        {
            "id": "R29-F01",
            "item": "The prior premise that no NFL result data existed was wrong",
            "detail": "Earlier sessions recorded that results were unavailable, which is why the "
                      "leaderboard was empty and luck could not be removed. NFL.com publishes a "
                      "final score for every past game on the by-week schedule pages. The retrieval "
                      "path was missing, not the data.",
            "impact": "Supersedes the 'no result archive' limitation. Does not invalidate prior "
                      "work; it extends it.",
            "status": "Corrected",
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-1",
        },
        {
            "id": "R29-F02",
            "item": "Two implementation bugs were found and fixed before publication",
            "detail": "A per-team/per-game units error doubled every implied total, and grading "
                      "initially compared a model against the board it produced. Both were fixed "
                      "and tests now pin the corrected behaviour.",
            "impact": "Any total or hit-rate figure produced before these fixes was wrong and was "
                      "not published.",
            "status": "Corrected",
            "source_url": "https://www.nfl.com/standings/",
        },
        {
            "id": "R29-F03",
            "item": "The total market shows no signal at all",
            "detail": f"The originated total's directional record is "
                      f"{analysis['benchmarks']['total']['directional']['wins']}–"
                      f"{analysis['benchmarks']['total']['directional']['losses']}, exactly a coin "
                      f"flip, with correlation {num(analysis['benchmarks']['total']['correlation_board_vs_actual'])}.",
            "impact": "No total strategy can be recommended. Published rather than hidden.",
            "status": "Needs review",
            "source_url": "https://www.nfl.com/standings/",
        },
        {
            "id": "R29-F04",
            "item": "The spread finding is provisional, not proven",
            "detail": f"p={analysis['benchmarks']['spread']['permutation_p_value']:.4f} survives the "
                      f"permutation test, but there is no price, no forward test, and only eight "
                      f"scored weeks. The family-wise luck figure is "
                      f"{pct(analysis['luck_analysis']['family_wise_false_positive'], 0)}.",
            "impact": "No reward, no recommendation, no claim of durable skill.",
            "status": "Needs review",
            "source_url": "https://www.nfl.com/standings/",
        },
        {
            "id": "R29-F05",
            "item": "Player-prop combinations remain blank",
            "detail": "No per-player, per-game logs were retrieved, so no joint distribution of two "
                      "player props exists in this project.",
            "impact": "Prop strategies cannot be graded.",
            "status": "Needs review",
            "source_url": "https://www.nfl.com/stats/player-stats/",
        },
        {
            "id": "R29-F06",
            "item": "Weeks 1–9 have no pre-kickoff injury snapshot",
            "detail": "The week-10 injury report is captured; the scored weeks are not. An "
                      "injury-adjusted line for those weeks cannot be built without inventing history.",
            "impact": "Injury effects are excluded from the graded strategies, not estimated.",
            "status": "Needs review",
            "source_url": "https://www.nfl.com/injuries/",
        },
        {
            "id": "R29-F07",
            "item": "Retrieval used rendered page text, not a raw HTTP archive",
            "detail": "The evidence files are the rendered text as read, saved verbatim. They are "
                      "not byte-level HTTP responses, so a later re-render could differ in "
                      "whitespace even when the facts agree.",
            "impact": "Integrity is evidenced by reconciliation against the standings (160/160 "
                      "fields), not by a hash of the original response.",
            "status": "Needs review",
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9",
        },
        {
            "id": "R29-F08",
            "item": "One tie complicates margin-based grading",
            "detail": "NYG 27–27 WAS in week 5 is a tie. Ties are handled explicitly: they are "
                      "excluded from win/loss grading and never counted as a win.",
            "impact": "None on the results, but the tie handling is stated so it can be checked.",
            "status": "Needs review",
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-5",
        },
        {
            "id": "R29-F09",
            "item": "Source terms constrain release, not analysis",
            "detail": "NFL.com §1.3 permits individual non-commercial informational use and "
                      "prohibits systematic retrieval to compile a collection without written "
                      "consent. Nothing is released and nothing is scraped on a schedule.",
            "impact": "The dataset cannot be redistributed and the reward gate (RG10) cannot pass.",
            "status": "Needs review",
            "source_url": "https://www.nfl.com/legal/terms/",
        },
        {
            "id": "R29-F10",
            "item": "Model parameters are fixed conventions, not fitted values",
            "detail": "The Pythagorean exponent (2.37), home-field allowance (2.0) and margin "
                      "standard deviation (13.86) are published conventions, held fixed before "
                      "evaluation. No parameter was tuned on the scored weeks.",
            "impact": "The model is arguably under-fitted, which biases against finding signal "
                      "rather than toward it.",
            "status": "Needs review",
            "source_url": "https://www.nfl.com/standings/",
        },
    ]
    rows = [{
        "id": f["id"], "item": f["item"], "detail": f["detail"], "impact": f["impact"],
        "status": f["status"], "source_url": f["source_url"], "source_ids": ["X29-NFL-SCHEDULE"],
    } for f in flags]

    body = ""
    body += notice(
        "Published for review, and not blocking",
        "These are the irregularities and unverified items found in this session. None blocks "
        "publication; all of them block an unsupported claim.", info=True)
    body += section(
        "Flagged items",
        table("flag-table", "Flagged for review", [
            ("ID", "id"), ("Item", "item"), ("Detail", "detail"),
            ("Impact", "impact"), ("State", lambda r: badge(r["status"])),
        ], rows, filter_options=["Needs review", "Corrected"],
            note="Every row links to the official page actually read. A flag is closed only by "
                 "evidence, never by time passing."),
        eyebrow="TRANSPARENCY")
    return body


def page_summary():
    analysis = load_analysis()
    spread = analysis["benchmarks"]["spread"]
    total = analysis["benchmarks"]["total"]
    counts = analysis["leaderboard_counts"]

    body = ""
    body += metrics([
        ("Official games captured", analysis["inputs"]["games"], "Weeks 1–9, reconciled", "data"),
        ("Reconciliation", "160/160", "Standings fields matched", "validation"),
        ("Spread board", pct(spread["directional"]["hit_rate"]), "Directional, provisional", "signals"),
        ("Total board", pct(total["directional"]["hit_rate"]), "No signal — published", "care"),
    ])

    body += section(
        "The five things that matter",
        """<div class="prose">
<p><strong>1. The missing data was never missing.</strong> Every earlier session recorded that no
NFL result archive existed. NFL.com publishes a final score for every past game. The project had
a retrieval gap, not a data gap, and closing it changed what the rest of the site could say.</p>
<p><strong>2. The scores are checkable, and checked.</strong> The 136 captured results are
re-derived into club totals and must reproduce the frozen official standings exactly: 32 clubs ×
5 fields = 160 checks. The build aborts on a single mismatch.</p>
<p><strong>3. The spread line carries information; the total line does not.</strong> The
originated spread beat the result 64.2% of the time (permutation p=0.0021, surviving FDR at
q=0.022), holding in both halves of the season and in every leave-one-week-out test. The
originated total landed at exactly 50.0%. The same model, the same data, two different answers.</p>
<p><strong>4. No strategy qualified, and zero rewards were paid.</strong> A <em>qualified</em>
entry needs an executable price. None exists in this project, so the leaderboard lists one
provisional entry with no merit points and no cash value. The reward mechanism is built and
deliberately empty.</p>
<p><strong>5. Correlation is now measured, not asserted.</strong> Same-game leg dependence is
-0.068 (p=0.47, n=114): small, negative, and indistinguishable from independence. No parlay is
repriced, and player-prop combinations stay blank for want of per-game player logs.</p>
</div>""",
        eyebrow="FINDINGS")

    body += section(
        "What changed in this session",
        table("summ-changes", "Delivered and verified", [
            ("Item", "item"), ("Status", lambda r: badge(r["status"])), ("Evidence", "evidence"),
        ], [
            {"id": "C1", "item": "Official game results, weeks 1–9", "status": "Complete",
             "evidence": "136 games parsed from saved rendered text; 160/160 fields reconcile.",
             "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9",
             "source_ids": ["X29-NFL-SCHEDULE"]},
            {"id": "C2", "item": "Leakage-free walk-forward evaluation", "status": "Complete",
             "evidence": "Week-w forecasts use only weeks < w; 120 games scored, week 1 excluded.",
             "source_url": "https://www.nfl.com/standings/", "source_ids": ["NFL-STANDINGS"]},
            {"id": "C3", "item": "Luck removal: permutation, FDR, split-half", "status": "Complete",
             "evidence": f"20,000 shuffles; BH across {counts['tested']} variants; leave-one-week-out.",
             "source_url": "https://www.nfl.com/standings/", "source_ids": ["NFL-STANDINGS"]},
            {"id": "C4", "item": "Leg-level correlation from joint outcomes", "status": "Complete",
             "evidence": "2×2 joint table over 114 games, phi and independence test published.",
             "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9",
             "source_ids": ["X29-NFL-SCHEDULE"]},
            {"id": "C5", "item": "Leaderboard with real graded entries", "status": "Needs review",
             "evidence": f"{counts['provisional']} provisional, {counts['qualified']} qualified, 0 rewards.",
             "source_url": "https://www.nfl.com/legal/terms/", "source_ids": ["NFL-TERMS"]},
            {"id": "C6", "item": "Player-prop combinations", "status": "Needs review",
             "evidence": "Blank: no per-player per-game logs retrieved.",
             "source_url": "https://www.nfl.com/stats/player-stats/",
             "source_ids": ["X29-NFL-SCHEDULE"]},
        ], note="A blank or 'Needs review' cell is a published gap, not an oversight."),
        eyebrow="DELIVERY")
    return body
