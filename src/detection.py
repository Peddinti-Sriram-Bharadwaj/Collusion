"""Track 1.3: collusion detection methods.

Baseline: profit-gain threshold test (the classical Delta > threshold check).
Proposed: a trajectory-feature classifier that uses only *price* dynamics
(no profit/demand-parameter knowledge), which should be more robust to the
"correlated but not collusive" confound (see src/confound.py) than naive
parallel-pricing tests that just threshold on price correlation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix


# ---------------------------------------------------------------------------
# Baseline: profit-gain threshold detector
# ---------------------------------------------------------------------------
def profit_gain_detector(delta: float, threshold: float = 0.15) -> bool:
    """Classical collusion-index threshold test."""
    return delta > threshold


# ---------------------------------------------------------------------------
# Baseline: naive parallel-pricing correlation detector
# ---------------------------------------------------------------------------
def parallel_pricing_detector(price_history: np.ndarray, threshold: float = 0.5) -> bool:
    """Flags collusion whenever cross-agent price correlation exceeds a
    threshold. This is the classic antitrust-econ 'parallel pricing' test,
    known to false-positive on shared-shock confounds (see src/confound.py)."""
    corr = _mean_pairwise_corr(price_history)
    return corr > threshold


def _mean_pairwise_corr(price_history: np.ndarray) -> float:
    n_agents = price_history.shape[1]
    if n_agents < 2:
        return 0.0
    corrs = []
    for i in range(n_agents):
        for j in range(i + 1, n_agents):
            xi, xj = price_history[:, i], price_history[:, j]
            if np.std(xi) < 1e-9 or np.std(xj) < 1e-9:
                corrs.append(0.0)
            else:
                corrs.append(np.corrcoef(xi, xj)[0, 1])
    return float(np.mean(corrs))


# ---------------------------------------------------------------------------
# Trajectory feature extraction (price-only; no profit/demand info used)
# ---------------------------------------------------------------------------
def extract_price_features(price_history: np.ndarray, price_grid: np.ndarray | None = None) -> dict:
    """Features computed purely from the price time series (any window)."""
    n_periods, n_agents = price_history.shape
    mean_price = price_history.mean(axis=0)

    # Normalize price level if a grid is given (so features are comparable
    # across configs with different absolute price scales)
    if price_grid is not None:
        lo, hi = price_grid.min(), price_grid.max()
        norm_level = float(((mean_price - lo) / (hi - lo)).mean()) if hi > lo else 0.0
    else:
        norm_level = float(mean_price.mean())

    pairwise_corr = _mean_pairwise_corr(price_history)

    # Lag-1 autocorrelation of price changes, averaged across agents:
    # collusive reward-punishment dynamics tend to produce more persistent
    # (positively autocorrelated) price-change sequences than i.i.d. noise.
    autocorrs = []
    for i in range(n_agents):
        diffs = np.diff(price_history[:, i])
        if len(diffs) > 1 and np.std(diffs) > 1e-9:
            ac = np.corrcoef(diffs[:-1], diffs[1:])[0, 1]
            autocorrs.append(ac if np.isfinite(ac) else 0.0)
        else:
            autocorrs.append(0.0)
    mean_autocorr = float(np.mean(autocorrs))

    # Price dispersion (within-period spread across agents), normalized by
    # overall price level -- lower dispersion often accompanies collusive
    # "focal point" pricing.
    within_period_std = float(price_history.std(axis=1).mean())
    overall_std = float(price_history.std())
    dispersion_ratio = within_period_std / overall_std if overall_std > 1e-9 else 0.0

    return {
        "price_level_norm": norm_level,
        "pairwise_price_corr": pairwise_corr,
        "mean_autocorr": mean_autocorr,
        "dispersion_ratio": dispersion_ratio,
    }


def build_feature_dataset(examples: list[dict]) -> pd.DataFrame:
    """examples: list of {"price_history": ndarray, "price_grid": ndarray|None, "label": int}"""
    rows = []
    for ex in examples:
        feats = extract_price_features(ex["price_history"], ex.get("price_grid"))
        feats["label"] = ex["label"]
        rows.append(feats)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Classifier training / evaluation
# ---------------------------------------------------------------------------
FEATURE_COLS = ["price_level_norm", "pairwise_price_corr", "mean_autocorr", "dispersion_ratio"]


def train_classifier(df: pd.DataFrame, model="random_forest", seed: int = 0):
    X, y = df[FEATURE_COLS], df["label"]
    if model == "random_forest":
        clf = RandomForestClassifier(n_estimators=200, random_state=seed, max_depth=4)
    elif model == "logistic":
        clf = LogisticRegression(max_iter=1000)
    else:
        raise ValueError(f"unknown model {model!r}")
    clf.fit(X, y)
    return clf


def evaluate_classifier(clf, df: pd.DataFrame) -> dict:
    X, y = df[FEATURE_COLS], df["label"]
    preds = clf.predict(X)
    cm = confusion_matrix(y, preds, labels=[0, 1])
    return {
        "precision": precision_score(y, preds, zero_division=0),
        "recall": recall_score(y, preds, zero_division=0),
        "f1": f1_score(y, preds, zero_division=0),
        "confusion_matrix": cm.tolist(),
        "n": len(df),
    }
