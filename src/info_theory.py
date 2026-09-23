"""Information-theoretic estimators for Track 1.4: transfer entropy, mutual
information, and interaction information (co-information), computed on
discretized time series via exact joint histograms (natural for our
finite price-grid actions; also applicable to continuous confound prices
after quantile discretization).

All entropies in bits (log2).
"""
from __future__ import annotations

import numpy as np


def discretize_series(x: np.ndarray, bins: int = 8) -> np.ndarray:
    """Bin a 1D series into integer labels 0..k-1.

    Low-cardinality inputs (e.g. already-discrete price-grid indices, or
    binary variables) are factorized directly by their unique values --
    quantile binning on data with few unique values can produce degenerate
    edges (e.g. an edge equal to the min) that collapse everything into one
    bin. Higher-cardinality/continuous inputs use rank-based quantile
    binning (robust to ties, unlike naive np.quantile edges).
    """
    x = np.asarray(x, dtype=float)
    uniques = np.unique(x)
    if len(uniques) <= bins:
        return np.searchsorted(uniques, x).astype(int)
    if np.std(x) < 1e-12:
        return np.zeros(len(x), dtype=int)
    ranks = np.argsort(np.argsort(x))  # 0..n-1, ties broken by position
    labels = (ranks * bins) // len(x)
    return np.clip(labels, 0, bins - 1).astype(int)


def _joint_probs(*label_arrays: np.ndarray) -> np.ndarray:
    """Exact joint probability table over integer-labeled arrays via
    multi-index counting (no histogram bin-edge ambiguity)."""
    arrays = [np.asarray(a, dtype=int) for a in label_arrays]
    n = len(arrays[0])
    dims = [int(a.max()) + 1 if len(a) else 1 for a in arrays]
    flat_idx = np.zeros(n, dtype=np.int64)
    stride = 1
    for a, d in zip(arrays, dims):
        flat_idx += a * stride
        stride *= d
    counts = np.bincount(flat_idx, minlength=int(np.prod(dims)))
    probs = counts / counts.sum()
    return probs[probs > 0]


def entropy(*label_arrays: np.ndarray) -> float:
    """Joint Shannon entropy (bits) of one or more discrete label arrays."""
    p = _joint_probs(*label_arrays)
    return float(-np.sum(p * np.log2(p)))


def mutual_information(x_labels: np.ndarray, y_labels: np.ndarray) -> float:
    """I(X;Y) = H(X) + H(Y) - H(X,Y)."""
    return entropy(x_labels) + entropy(y_labels) - entropy(x_labels, y_labels)


def conditional_mutual_information(x_labels: np.ndarray, y_labels: np.ndarray, z_labels: np.ndarray) -> float:
    """I(X;Y|Z) = H(X,Z) + H(Y,Z) - H(X,Y,Z) - H(Z)."""
    return (
        entropy(x_labels, z_labels)
        + entropy(y_labels, z_labels)
        - entropy(x_labels, y_labels, z_labels)
        - entropy(z_labels)
    )


def transfer_entropy(source: np.ndarray, target: np.ndarray, bins: int = 8) -> float:
    """TE(source -> target), order-1 Markov: I(target_t ; source_{t-1} | target_{t-1}).

    Measures how much knowing the source's past reduces uncertainty about the
    target's present, beyond what the target's own past already explains --
    a directed, lag-based signature of one series influencing another.
    """
    s = discretize_series(source, bins)
    t = discretize_series(target, bins)
    target_t = t[1:]
    target_lag = t[:-1]
    source_lag = s[:-1]
    return conditional_mutual_information(target_t, source_lag, target_lag)


def interaction_information(x: np.ndarray, y: np.ndarray, z: np.ndarray, bins: int = 8) -> float:
    """II(X;Y;Z) = I(X;Y) - I(X;Y|Z).

    Positive II: Z makes X,Y *more* redundant (shared-cause signature --
    conditioning on Z explains away some of the X-Y correlation).
    Negative II: Z makes X,Y *more* synergistic (X and Y jointly informative
    about/with Z beyond their pairwise link -- a coordination-like signature).
    This is the standard co-information proxy for the redundancy/synergy
    split that full partial information decomposition targets more precisely.
    """
    xl, yl, zl = discretize_series(x, bins), discretize_series(y, bins), discretize_series(z, bins)
    return mutual_information(xl, yl) - conditional_mutual_information(xl, yl, zl)
