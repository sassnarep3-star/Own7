#!/usr/bin/env python3
"""Ordered origination: the side first, then the total, then the moneyline.

Why the order matters and is enforced here:

* The side is originated from the margin distribution. It is the only market whose
  fair price can be derived without assuming a scoring level.
* The total is originated *after* the side, from the same score pair, and its fit is
  reported separately. It is never rescaled to make the side look better.
* The moneyline is originated *last*, from the same score pair, and is explicitly a
  monotone restatement of the side in price space. It is not independent evidence.
  Saying so prevents double-counting one forecast as three signals.

Every board carries three separate columns and never merges them:
    model_*   what our own model says (the fair line / fair price)
    market_*  what the relayed market published at the stated snapshot
    edge_*    the difference, in points or in probability, with its sign convention

If market_* is unavailable, edge_* is blank. It is never computed against zero.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import sources

ND = NormalDist()

# Registered choices. Changing one of these is a strategy change, not a tweak.
PARAMS = {
    "pythagorean_exponent": 2.37,
    "home_field_points": 2.0,
    "shrink_to_league_games": 4.0,
    "margin_sd": 13.5,
    "total_sd": 12.5,
    "league_ppg_prior": 24.71875,
    "history_window": "strictly before the graded week; the graded week is never in the inputs",
    "note": (
        "margin_sd and total_sd are stated priors, not fitted values: 14 or 15 games per week "
        "cannot identify them. They are registered here so a reader can see exactly what "
        "produced each probability, and they are not tuned on the graded weeks."
    ),
}


def american_to_prob(price: float):
    """Implied probability of an American price. Push-free; de-vigged separately."""
    if price is None:
        return None
    p = price
    if p > 0:
        return 100.0 / (p + 100.0)
    return (-p) / ((-p) + 100.0)


def american_from_prob(p):
    if p is None:
        return None
    if not 0.0 < p < 1.0:
        return None
    if p >= 0.5:
        return round(-100.0 * p / (1.0 - p))
    return round(100.0 * (1.0 - p) / p)


def devig(home_price, away_price):
    """Two-way no-vig probability for the home side, or None if a leg is missing."""
    if home_price is None or away_price is None:
        return None
    h = american_to_prob(home_price)
    a = american_to_prob(away_price)
    if h is None or a is None or (h + a) <= 0:
        return None
    return h / (h + a)


def pythagorean_wins(pf: float, pa: float, exponent: float) -> float:
    if pf <= 0 or pa <= 0:
        return 0.5
    return (pf ** exponent) / ((pf ** exponent) + (pa ** exponent))


ALIAS = {"ARI": "AZ", "LAR": "LA", "WSH": "WAS", "JAC": "JAX", "TAM": "TB", "LVR": "LV",
         "NOR": "NO", "SFO": "SF", "KAN": "KC", "GNB": "GB", "NWE": "NE", "SDC": "LAC"}


def canon(abbr: str) -> str:
    """One canonical abbreviation per club, so a club is never silently dropped by spelling."""
    a = abbr.strip().upper()
    return ALIAS.get(a, a)


def build_team_ratings(results: list[dict], before_week: int) -> dict:
    """Rate every club using only games played strictly before `before_week`.

    This is the anti-lookahead rule, and it is the reason ratings are not read from a
    standings page: a standings page is a snapshot of *now*, so rating a Week 9 game
    from it would silently use Week 9's own result. Totals are accumulated from the
    official final scores instead, which carry the week number.

    A club with no prior games gets the league prior and is marked `insufficient_history`.
    """
    pf: dict[str, float] = {}
    pa: dict[str, float] = {}
    gp: dict[str, int] = {}
    for g in results:
        if g["week"] >= before_week:
            continue
        h, a = canon(g["home"]), canon(g["away"])
        pf[h] = pf.get(h, 0.0) + g["home_score"]
        pa[h] = pa.get(h, 0.0) + g["away_score"]
        pf[a] = pf.get(a, 0.0) + g["away_score"]
        pa[a] = pa.get(a, 0.0) + g["home_score"]
        gp[h] = gp.get(h, 0) + 1
        gp[a] = gp.get(a, 0) + 1

    lg_ppg = (sum(pf.values()) / sum(gp.values())) if gp else PARAMS["league_ppg_prior"]
    k = PARAMS["shrink_to_league_games"]
    out = {}
    for club in sorted(set(list(pf) + list(pa))):
        n = gp.get(club, 0)
        if n == 0:
            out[club] = {"games": 0, "off_shrunk": lg_ppg, "def_shrunk": lg_ppg,
                         "off_raw": None, "def_raw": None,
                         "pythagorean_wins": None, "insufficient_history": True,
                         "window": f"weeks 1-{before_week - 1}", "games_used": 0}
            continue
        off = pf[club] / n
        dfn = pa[club] / n
        out[club] = {
            "games": n,
            "points_for": round(pf[club], 1),
            "points_against": round(pa[club], 1),
            "off_raw": round(off, 4),
            "def_raw": round(dfn, 4),
            "off_shrunk": round((k * lg_ppg + n * off) / (k + n), 4),
            "def_shrunk": round((k * lg_ppg + n * dfn) / (k + n), 4),
            "pythagorean_wins": round(pythagorean_wins(pf[club], pa[club], PARAMS["pythagorean_exponent"]), 4),
            "insufficient_history": n < 3,
            "window": f"weeks 1-{before_week - 1}",
            "games_used": n,
        }
    return out


def projected_margin(home: str, away: str, ratings: dict) -> float:
    """Neutral expected margin, before home field. Positive = home wins."""
    h = ratings.get(home)
    a = ratings.get(away)
    if h is None or a is None:
        raise sources.ContractError(f"no rating for {home} or {away}")
    return ((h["off_shrunk"] + a["def_shrunk"]) - (a["off_shrunk"] + h["def_shrunk"])) / 2.0


def projected_total(home: str, away: str, ratings: dict) -> float:
    h = ratings.get(home)
    a = ratings.get(away)
    if h is None or a is None:
        raise sources.ContractError(f"no rating for {home} or {away}")
    return (h["off_shrunk"] + a["def_shrunk"] + a["off_shrunk"] + h["def_shrunk"]) / 2.0


def market_home_margin(market_line: float) -> float:
    """The home margin the market implies.

    `market_line` is the HOME side's own printed spread, so a home favourite prints -9.5 and the
    market's implied home margin is +9.5, not -9.5. Getting this sign wrong inverts every pick on
    the board, which is what happened in the first build: the desk bet the side it rated *worse*
    than the market and went 13-2 for it. This function exists so the conversion lives in one
    place and is tested.
    """
    return -market_line


def prob_home_covers(fair_margin: float, market_line: float) -> float:
    """P(home covers its own spread `market_line`).

    Home covers iff actual home margin > -market_line. With a home spread of -9.5 the club must
    win by more than 9.5; with +9.5 it covers by losing by fewer than 9.5.
    """
    return 1.0 - ND.cdf((market_home_margin(market_line) - fair_margin) / PARAMS["margin_sd"])


def prob_over(fair_total: float, market_total: float) -> float:
    return 1.0 - ND.cdf((market_total - fair_total) / PARAMS["total_sd"])


def prob_home_win(fair_margin: float) -> float:
    return 1.0 - ND.cdf((0.0 - fair_margin) / PARAMS["margin_sd"])


def price_index(prices: list[dict]) -> dict:
    """(event_id, market, side, snapshot) -> observation."""
    idx = {}
    for p in prices:
        idx[(p["event_id"], p["market"], p["team_or_side"], p["snapshot"])] = p
    return idx


def edge_points(fair: float, market: float):
    """Model minus market on the SIDE board, in points.

    Compares like with like: the model's expected home margin against the market's implied home
    margin, which is the negative of the home side's printed spread.
    """
    if market is None:
        return None
    return round(fair - market_home_margin(market), 2)


def edge_total(fair: float, market: float):
    """Model minus market on the TOTAL board, in points.

    A total is not signed the way a spread is: the market's implied total IS the printed number.
    Applying the margin conversion here would add the line to itself and manufacture an
    eighty-point edge, which is exactly the failure this separate function prevents.
    """
    if market is None:
        return None
    return round(fair - market, 2)


def build_board(games: list[dict], prices: list[dict]) -> dict:
    """Produce the three ordered boards for the priced games."""
    idx = price_index(prices)
    priced_events = sorted({p["event_id"] for p in prices})
    by_pair = {}
    for g in games:
        by_pair[(canon(g["away"]), canon(g["home"]))] = g

    # Ratings are rebuilt per week window so no week is ever rated on its own results.
    rating_cache: dict[int, dict] = {}
    def ratings_for(week: int) -> dict:
        if week not in rating_cache:
            rating_cache[week] = build_team_ratings(games, week)
        return rating_cache[week]

    boards = {"side": [], "total": [], "moneyline": []}
    unresolved = []

    for event_id in priced_events:
        obs = [p for p in prices if p["event_id"] == event_id]
        game_label = obs[0]["game"]
        away, home = game_label.split("@")
        # Bind on canonical abbreviations: ESPN says ARI/LAR/WSH, the score file says AZ/LA/WAS.
        home_r, away_r = canon(home), canon(away)
        g = by_pair.get((away_r, home_r))
        if g is None:
            unresolved.append({
                "event_id": event_id, "game": game_label,
                "why": f"no official final score with away={away_r}, home={home_r} in the results capture",
            })
            continue

        ratings = ratings_for(g["week"])
        fair_margin = projected_margin(home_r, away_r, ratings) + PARAMS["home_field_points"]
        fair_total = projected_total(home_r, away_r, ratings)
        fair_ml_home = prob_home_win(fair_margin)

        actual_margin = g["home_score"] - g["away_score"]
        actual_total = g["home_score"] + g["away_score"]

        # --- 1. SIDE --------------------------------------------------------------
        mkt_home = idx.get((event_id, "spread", home, "close"))
        mkt_away = idx.get((event_id, "spread", away, "close"))
        mkt_home_o = idx.get((event_id, "spread", home, "open"))
        mkt_away_o = idx.get((event_id, "spread", away, "open"))
        mkt_line = float(mkt_home["line"]) if mkt_home else None
        mkt_line_o = float(mkt_home_o["line"]) if mkt_home_o else None
        row_side = {
            "order": 1, "event_id": event_id, "game": game_label, "week": g["week"],
            "home": home, "away": away,
            "model_fair_line": round(fair_margin, 2),
            "market_line": mkt_line,
            "edge_points": edge_points(round(fair_margin, 2), mkt_line),
            "model_home_cover_prob": round(prob_home_covers(fair_margin, mkt_line), 4) if mkt_line is not None else None,
            "market_home_price": mkt_home["price_american"] if mkt_home else None,
            "market_away_price": mkt_away["price_american"] if mkt_away else None,
            "market_line_open": mkt_line_o,
            "market_home_price_open": mkt_home_o["price_american"] if mkt_home_o else None,
            "market_away_price_open": mkt_away_o["price_american"] if mkt_away_o else None,
            "open_edge_points": edge_points(round(fair_margin, 2), mkt_line_o),
            "line_movement_points": round(mkt_line - mkt_line_o, 2) if (mkt_line is not None and mkt_line_o is not None) else None,
            "actual_margin": actual_margin,
            "settled": True,
            "source_ids": ["MD-ESPN-ODDS", "CFDD-NFL-STANDINGS"],
            "source_url": mkt_home["source_url"] if mkt_home else None,
            "result_source_url": g["source_url"],
            "rating_window": f"weeks 1-{g['week'] - 1}",
            "rating_games_used": ratings[home_r]["games"] + ratings[away_r]["games"],
            "thin_history": bool(ratings[home_r]["insufficient_history"] or ratings[away_r]["insufficient_history"]),
        }
        boards["side"].append(row_side)

        # --- 2. TOTAL ------------------------------------------------------------
        mkt_over = idx.get((event_id, "total", "OVER", "close"))
        mkt_under = idx.get((event_id, "total", "UNDER", "close"))
        mkt_over_o = idx.get((event_id, "total", "OVER", "open"))
        mkt_under_o = idx.get((event_id, "total", "UNDER", "open"))
        mkt_total = float(mkt_over["line"]) if mkt_over else None
        mkt_total_o = float(mkt_over_o["line"]) if mkt_over_o else None
        row_total = {
            "order": 2, "event_id": event_id, "game": game_label, "week": g["week"],
            "model_fair_total": round(fair_total, 2),
            "market_total": mkt_total,
            "edge_points": edge_total(round(fair_total, 2), mkt_total),
            "model_over_prob": round(prob_over(fair_total, mkt_total), 4) if mkt_total is not None else None,
            "market_over_price": mkt_over["price_american"] if mkt_over else None,
            "market_under_price": mkt_under["price_american"] if mkt_under else None,
            "market_total_open": mkt_total_o,
            "market_over_price_open": mkt_over_o["price_american"] if mkt_over_o else None,
            "market_under_price_open": mkt_under_o["price_american"] if mkt_under_o else None,
            "open_edge_points": edge_total(round(fair_total, 2), mkt_total_o),
            "line_movement_points": round(mkt_total - mkt_total_o, 2) if (mkt_total is not None and mkt_total_o is not None) else None,
            "actual_total": actual_total,
            "settled": True,
            "source_ids": ["MD-ESPN-ODDS", "CFDD-NFL-STANDINGS"],
            "source_url": mkt_over["source_url"] if mkt_over else None,
            "result_source_url": g["source_url"],
        }
        boards["total"].append(row_total)

        # --- 3. MONEYLINE --------------------------------------------------------
        ml_home = idx.get((event_id, "moneyline", home, "close"))
        ml_away = idx.get((event_id, "moneyline", away, "close"))
        mkt_home_p = american_to_prob(float(ml_home["price_american"])) if ml_home else None
        mkt_away_p = american_to_prob(float(ml_away["price_american"])) if ml_away else None
        devig_home = devig(float(ml_home["price_american"]), float(ml_away["price_american"])) if (ml_home and ml_away) else None
        row_ml = {
            "order": 3, "event_id": event_id, "game": game_label, "week": g["week"],
            "home": home, "away": away,
            "model_home_win_prob": round(fair_ml_home, 4),
            "model_fair_price_home": american_from_prob(fair_ml_home),
            "model_fair_price_away": american_from_prob(1 - fair_ml_home),
            "market_home_price": ml_home["price_american"] if ml_home else None,
            "market_away_price": ml_away["price_american"] if ml_away else None,
            "market_implied_home": round(mkt_home_p, 4) if mkt_home_p is not None else None,
            "market_novig_home": round(devig_home, 4) if devig_home is not None else None,
            "edge_prob_home": round(fair_ml_home - devig_home, 4) if devig_home is not None else None,
            "actual_home_win": 1 if actual_margin > 0 else (0 if actual_margin < 0 else None),
            "settled": True,
            "is_restatement_of_side": True,
            "source_ids": ["MD-ESPN-ODDS", "CFDD-NFL-STANDINGS"],
            "source_url": ml_home["source_url"] if ml_home else None,
            "result_source_url": g["source_url"],
        }
        boards["moneyline"].append(row_ml)

    for k in boards:
        boards[k].sort(key=lambda r: r["event_id"])
    return {"params": PARAMS, "boards": boards, "unresolved": unresolved,
            "ratings": {str(w): v for w, v in rating_cache.items()}}
