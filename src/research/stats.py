"""Statistics: paired / clustered bootstrap, sign consistency, influence, multiplicity, replication labels."""
from __future__ import annotations

from typing import Sequence

import numpy as np

DELTA_EQUIV = 0.25  # equivalence margin in price-index steps (pre-declared)


def summarize(values: Sequence[float], clusters: Sequence | None = None, n_boot: int = 4000, seed: int = 0,
              alpha: float = 0.05) -> dict:
    """Mean effect with a cluster bootstrap CI (clusters = independent units, e.g. history seeds)."""
    x = np.asarray([v for v in values if v is not None and np.isfinite(v)], float)
    if clusters is None:
        cl = np.arange(len(x))
    else:
        cl = np.asarray([c for c, v in zip(clusters, values) if v is not None and np.isfinite(v)])
    n = len(x)
    if n == 0:
        return {"n": 0, "n_clusters": 0, "mean": None, "median": None, "sd": None, "ci_low": None, "ci_high": None,
                "frac_negative": None, "frac_positive": None, "loo_max_shift": None}
    ids = np.unique(cl)
    groups = [x[cl == c] for c in ids]
    g = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot if len(ids) > 1 else 0):
        pick = g.integers(0, len(ids), len(ids))
        boots.append(np.concatenate([groups[i] for i in pick]).mean())
    lo, hi = (np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)]) if boots else (np.nan, np.nan))
    loo = [abs(np.concatenate([groups[j] for j in range(len(ids)) if j != i]).mean() - x.mean())
           for i in range(len(ids))] if len(ids) > 2 else [np.nan]
    return {"n": int(n), "n_clusters": int(len(ids)), "mean": float(x.mean()), "median": float(np.median(x)),
            "sd": float(x.std(ddof=1)) if n > 1 else None, "ci_low": float(lo), "ci_high": float(hi),
            "frac_negative": float((x < 0).mean()), "frac_positive": float((x > 0).mean()),
            "loo_max_shift": None if all(np.isnan(loo)) else float(np.nanmax(loo))}


def cell_status(s: dict, predicted: str, delta: float = DELTA_EQUIV, min_clusters: int = 4) -> str:
    """Pre-declared per-cell label: supported | opposite | absent | inconclusive | insufficient."""
    if not s or s.get("n_clusters", 0) < min_clusters or s.get("ci_low") is None or not np.isfinite(s["ci_low"]):
        return "insufficient"
    lo, hi = s["ci_low"], s["ci_high"]
    if predicted == "negative":
        if hi < 0:
            return "supported"
        if lo > 0:
            return "opposite"
    elif predicted == "positive":
        if lo > 0:
            return "supported"
        if hi < 0:
            return "opposite"
    elif predicted == "nonzero":
        if hi < 0 or lo > 0:
            return "supported"
    elif predicted == "near_zero":
        if -delta < lo and hi < delta:
            return "supported"
        if hi < -delta or lo > delta:
            return "opposite"
        return "inconclusive"
    if -delta < lo and hi < delta:
        return "absent"
    return "inconclusive"


def replication_status(statuses: Sequence[str]) -> str:
    """Behaviour-level label across cells (pre-declared)."""
    s = [x for x in statuses if x != "insufficient"]
    if not s:
        return "insufficient evidence"
    sup = sum(x == "supported" for x in s) / len(s)
    bad = sum(x in ("absent", "opposite") for x in s) / len(s)
    if sup >= 0.8 and "opposite" not in s:
        return "robust"
    if bad > 0.5:
        return "not replicated"
    if sup > 0:
        return "mixed"
    return "inconclusive"


def holm(pvals: Sequence[float]) -> list[float]:
    p = np.asarray(pvals, float); order = np.argsort(p); m = len(p)
    adj = np.empty(m); run = 0.0
    for i, j in enumerate(order):
        run = max(run, (m - i) * p[j]); adj[j] = min(1.0, run)
    return adj.tolist()


def bootstrap_p_two_sided(values: Sequence[float], clusters: Sequence | None = None, n_boot: int = 4000, seed: int = 0) -> float | None:
    """Two-sided p for mean != 0 via a centred cluster bootstrap."""
    x = np.asarray(values, float)
    if len(x) < 3:
        return None
    cl = np.arange(len(x)) if clusters is None else np.asarray(clusters)
    ids = np.unique(cl); groups = [x[cl == c] - x.mean() for c in ids]
    g = np.random.default_rng(seed); obs = abs(x.mean()); cnt = 0
    for _ in range(n_boot):
        pick = g.integers(0, len(ids), len(ids))
        cnt += abs(np.concatenate([groups[i] for i in pick]).mean()) >= obs
    return (cnt + 1) / (n_boot + 1)
