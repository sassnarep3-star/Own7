"""Retrospective demonstration: earlier-game inputs only, no market assertions."""
from __future__ import annotations

from .math import brier_score, log_loss, probability


def beta_probability(hits: int, n: int, alpha: float = 1, beta: float = 1) -> float:
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError("Nonnegative integer n required")
    if not isinstance(hits, int) or isinstance(hits, bool) or not 0 <= hits <= n:
        raise ValueError("Integer hit count in [0,n] required")
    if alpha <= 0 or beta <= 0:
        raise ValueError("Positive prior parameters required")
    return probability((hits + alpha) / (n + alpha + beta))


def walk_forward_demo(games: list[dict], settings: dict) -> dict:
    """Fixed hypothetical thresholds, not archived sportsbook lines.

    This is a counterfactual walk-forward run, NOT genuinely pre-registered or
    timestamped pregame. Window/player/threshold selection is exploratory.
    The joint event is learned from paired hits, never by multiplying marginals.
    """
    if len({g["GameID"] for g in games}) != len(games):
        raise ValueError("Duplicate game ID")
    if any(g["Date"] >= h["Date"] for g, h in zip(games, games[1:])):
        raise ValueError("Games must have strictly increasing dates")
    warmup = settings["minimum_training_games"]
    if not isinstance(warmup, int) or isinstance(warmup, bool) or warmup < 2:
        raise ValueError("At least two warm-up games required")
    thresholds = settings["thresholds"]
    events = [(stat, [(stat, level)]) for stat, level in thresholds.items()]
    combo = settings["combo"]
    events.append(("PTS + AST combo", [(s, thresholds[s]) for s in combo]))
    forecasts, summaries = [], []
    for label, legs in events:
        outcomes, probabilities = [], []
        hit = lambda game: int(all(float(game[s]) > level for s, level in legs))
        for i in range(warmup, len(games)):
            train, target = games[:i], games[i]
            train_hits = sum(hit(g) for g in train)
            p = beta_probability(train_hits, len(train), settings["prior_alpha"], settings["prior_beta"])
            realized = hit(target)
            outcomes.append(realized)
            probabilities.append(p)
            forecasts.append({
                "event": label, "threshold": " & ".join(f"{s} > {v:g}" for s, v in legs),
                "game_id": target["GameID"], "date": target["Date"],
                "train_end": train[-1]["Date"], "training_games": len(train),
                "training_hits": train_hits, "p_model": p,
                "fair_model_decimal": None,
                "price_status": "Withheld: NBA source-rights gate not cleared",
                "outcome": realized,
                "market_decimal": None, "edge": None, "roi": None, "clv": None,
                "status": "Retrospective demonstration", "source_ids": ["NBA-GAMES"],
                "source_url": target["Source"],
            })
        if outcomes:
            summaries.append({"event": label, "forecasts": len(outcomes),
                              "log_loss": log_loss(outcomes, probabilities),
                              "brier": brier_score(outcomes, probabilities),
                              "neutral_log_loss": log_loss(outcomes, [0.5] * len(outcomes)),
                              "neutral_brier": 0.25, "roi": None, "clv": None,
                              "status": "Exploratory; not market-tested", "source_ids": ["NBA-GAMES", "SK-CAL"]})
    return {"forecasts": forecasts, "summaries": summaries}
