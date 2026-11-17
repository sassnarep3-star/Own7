"""Shared helpers for the NFL competition lab.

Everything here is deterministic: no wall-clock values are written into an
artifact, no random draw is unseeded, and every float that reaches a published
file is rounded so that a rebuild on another machine is byte-identical.

The lab never produces a price, a stake, a wager, a return on investment or a
cash reward. Where a quantity depends on one, the value is None and the reason
is published next to it.
"""
from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
EVIDENCE = HERE / "evidence"
SITE = HERE / "site"

READ_ON = "2026-11-14"
SEASON = 2026

# Official page hosts this lab is allowed to cite. Anything else is rejected
# rather than published, so a stray URL can never masquerade as a source.
OFFICIAL_HOSTS = (
    "www.nfl.com",
    "www.nfl.com/standings",
)


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        fields = fields or []
    else:
        fields = fields or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def round_value(value, places=6):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, float):
        return round(value, places)
    if isinstance(value, dict):
        return {k: round_value(v, places) for k, v in value.items()}
    if isinstance(value, list):
        return [round_value(v, places) for v in value]
    return value


def check_artifact(path, payload):
    """Write the artifact, or (with --check) fail if the committed one differs."""
    import sys
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    target = Path(path)
    if "--check" in sys.argv:
        if not target.exists():
            raise SystemExit(f"STALE: {target} is missing; run {Path(sys.argv[0]).name}")
        if target.read_text(encoding="utf-8") != text:
            raise SystemExit(f"STALE: {target} differs from a fresh rebuild")
        print(f"OK: {target.relative_to(ROOT)} reproduces exactly")
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)}")
    return True


# ---------------------------------------------------------------- statistics

def normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def normal_ppf(p):
    """Acklam's inverse normal CDF approximation; used only for intervals."""
    if not 0.0 < p < 1.0:
        raise ValueError("normal_ppf needs 0 < p < 1")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def binom_pmf(k, n, p):
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def binom_sf(k, n, p=0.5):
    """P(X >= k) under the exact binomial. One-sided, no normal approximation."""
    return sum(binom_pmf(i, n, p) for i in range(k, n + 1))


def binom_two_sided(k, n, p=0.5):
    """Exact two-sided binomial p: sum of every outcome no more likely than k."""
    if n == 0:
        return None
    target = binom_pmf(k, n, p)
    return min(1.0, sum(binom_pmf(i, n, p) for i in range(n + 1)
                        if binom_pmf(i, n, p) <= target * (1 + 1e-12)))


def wilson_interval(k, n, z=1.959963985):
    """Wilson score interval for a proportion. Returns (low, high)."""
    if n == 0:
        return (None, None)
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def stdev(values):
    values = list(values)
    if len(values) < 2:
        return None
    mu = mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / (len(values) - 1))


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def pearson_p(r, n):
    """Two-sided p for a Pearson correlation, via the t distribution.

    For T ~ t(df), P(|T| > t) = I_x(df/2, 1/2) with x = df / (df + t^2). That identity
    gives the two-sided p directly, so no separate tail function is needed and the
    result cannot exceed 1.
    """
    if r is None or n is None or n < 3 or abs(r) >= 1:
        return None
    df = n - 2
    t = r * math.sqrt(df / (1 - r * r))
    x = df / (df + t * t)
    return _betainc(df / 2.0, 0.5, x)


def _betainc(a, b, x):
    """Regularised incomplete beta, continued-fraction form (Lentz)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + \
        a * math.log(x) + b * math.log(1 - x)
    front = math.exp(lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 200):
        m = i // 2
        if i == 0:
            numerator = 1.0
        elif i % 2 == 0:
            numerator = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            numerator = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + numerator * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + numerator / c
        if abs(c) < 1e-30:
            c = 1e-30
        f *= c * d
        if abs(1.0 - c * d) < 1e-12:
            break
    return front * (f - 1.0)


def fisher_ci(r, n, z=1.959963985):
    if r is None or n is None or n < 4 or abs(r) >= 1:
        return (None, None)
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    return (math.tanh(zr - z * se), math.tanh(zr + z * se))


def phi_coefficient(a, b, c, d):
    """Phi for a 2x2 table [[a,b],[c,d]]."""
    n = a + b + c + d
    if n == 0:
        return None
    num = a * d - b * c
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    return num / den if den else None


def chi2_phi_p(phi, n):
    """phi * sqrt(n) is a standard normal deviate under independence."""
    if phi is None or not n:
        return None
    z = abs(phi) * math.sqrt(n)
    return 2 * (1 - normal_cdf(z))


def benjamini_hochberg(pvals, level=0.10):
    """Return (adjusted p-values, reject flags) at the given FDR level."""
    indexed = [(i, p) for i, p in enumerate(pvals) if p is not None]
    m = len(indexed)
    adjusted = [None] * len(pvals)
    rejected = [False] * len(pvals)
    if m == 0:
        return adjusted, rejected
    # Step-up from the largest rank downwards, so q is monotone in p. Running this
    # loop forwards drags every later value down to the smallest one, which would
    # report a q of 0 for a p of 1.
    ordered = sorted(indexed, key=lambda pair: pair[1])
    prev = 1.0
    for rank in range(m, 0, -1):
        idx, p = ordered[rank - 1]
        value = min(prev, p * m / rank)
        prev = value
        adjusted[idx] = value
    for idx, p in indexed:
        rejected[idx] = adjusted[idx] is not None and adjusted[idx] <= level
    return adjusted, rejected


def permutation_p(xs, ys, draws=20000, seed=20261114):
    """Two-sided permutation p for a Pearson correlation. Seeded, so stable."""
    r_obs = pearson(xs, ys)
    if r_obs is None:
        return None, r_obs
    rng = random.Random(seed)
    ys_pool = list(ys)
    hits = 0
    for _ in range(draws):
        rng.shuffle(ys_pool)
        r = pearson(xs, ys_pool)
        if r is not None and abs(r) >= abs(r_obs) - 1e-15:
            hits += 1
    return (hits + 1) / (draws + 1), r_obs


def log_loss(outcomes, probs, eps=1e-9):
    """Mean log loss. probs are clipped so a 0/1 forecast cannot return inf."""
    if not outcomes:
        return None
    total = 0.0
    for y, p in zip(outcomes, probs):
        p = min(1 - eps, max(eps, p))
        total += -(math.log(p) if y else math.log(1 - p))
    return total / len(outcomes)


def brier(outcomes, probs):
    if not outcomes:
        return None
    return sum((y - p) ** 2 for y, p in zip(outcomes, probs)) / len(outcomes)


# ------------------------------------------------------------- presentation

BLANK = "Not published by an official source"


def blank(reason=None):
    """A published blank. Never 0, never an estimate, always with a reason."""
    return {"value": None, "display": "—", "reason": reason or BLANK}
