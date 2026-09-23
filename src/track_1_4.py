"""Track 1.4: does an information-theoretic detector succeed where Track
1.3's price-trajectory classifier failed -- specifically, does it avoid
flagging the shared-shock confound (correlated but not collusive) as
collusion, while still detecting genuine Q-learning collusion?

Reuses the same labeled example generators as Track 1.3 for a fair
comparison, but replaces price-correlation/level features with:
  - transfer entropy each direction (TE_1->2, TE_2->1)
  - mean pairwise mutual information
  - interaction information (co-information) proxy for redundancy/synergy

Usage: python -m src.track_1_4
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from src.track_1_3 import _collusive_examples, _competitive_examples, _confound_examples, WINDOW
from src.info_theory import transfer_entropy, mutual_information, discretize_series, interaction_information
from src.detection import train_classifier, evaluate_classifier

RESULTS_DIR = "results"
BINS = 6


def extract_info_features(price_history: np.ndarray) -> dict:
    """Only defined for the 2-agent case (this env's replacement/confound
    experiments are 2-agent); TE/II here are pairwise."""
    x, y = price_history[:, 0], price_history[:, 1]
    te_xy = transfer_entropy(x, y, bins=BINS)
    te_yx = transfer_entropy(y, x, bins=BINS)
    xl, yl = discretize_series(x, BINS), discretize_series(y, BINS)
    mi = mutual_information(xl, yl)
    # Use each agent's own lagged price as the conditioning variable Z for a
    # simple synergy/redundancy proxy: does the *joint* (x_t, y_t) relationship
    # look more redundant or synergistic once we account for x's own history?
    x_lag = x[:-1]
    ii = interaction_information(x[1:], y[1:], x_lag, bins=BINS)
    return {
        "te_max": max(te_xy, te_yx),
        "te_asymmetry": abs(te_xy - te_yx),
        "mutual_info": mi,
        "interaction_info": ii,
    }


def build_info_feature_dataset(examples: list[dict]) -> pd.DataFrame:
    rows = []
    for ex in examples:
        feats = extract_info_features(ex["price_history"])
        feats["label"] = ex["label"]
        rows.append(feats)
    return pd.DataFrame(rows)


INFO_FEATURE_COLS = ["te_max", "te_asymmetry", "mutual_info", "interaction_info"]


def run_track_1_4(n_train_seeds: int = 15, n_test_seeds: int = 8, n_confound_seeds: int = 15):
    print("Generating labeled trajectories (reusing Track 1.3 generators)...")
    train_examples = _collusive_examples(n_train_seeds, 0) + _competitive_examples(n_train_seeds, 0)
    test_examples = _collusive_examples(n_test_seeds, 1000) + _competitive_examples(n_test_seeds, 1000)
    confound_examples = _confound_examples(n_confound_seeds, 0)

    print("Extracting information-theoretic features...")
    train_df = build_info_feature_dataset(train_examples)
    test_df = build_info_feature_dataset(test_examples)
    confound_df = build_info_feature_dataset(confound_examples)

    print("\n--- Descriptive: mean feature values by group ---")
    for name, df in [("train (collusive+competitive)", train_df), ("confound (shared shock)", confound_df)]:
        print(f"{name}:")
        print(df[INFO_FEATURE_COLS + ["label"]].groupby("label").mean().to_string() if "label" in df and df["label"].nunique() > 1 else df[INFO_FEATURE_COLS].mean().to_string())

    from src.detection import FEATURE_COLS
    import src.detection as detection_mod
    detection_mod.FEATURE_COLS = INFO_FEATURE_COLS  # reuse train/eval helpers with our feature set

    clf = train_classifier(train_df)
    metrics_test = evaluate_classifier(clf, test_df)
    print(f"\nHeld-out Q-learning test set: precision={metrics_test['precision']:.3f} recall={metrics_test['recall']:.3f} f1={metrics_test['f1']:.3f}")
    print(f"  confusion matrix [[TN,FP],[FN,TP]]: {metrics_test['confusion_matrix']}")

    metrics_confound = evaluate_classifier(clf, confound_df)
    n_fp = metrics_confound["confusion_matrix"][0][1]
    n_tn = metrics_confound["confusion_matrix"][0][0]
    fp_rate = n_fp / (n_fp + n_tn) if (n_fp + n_tn) > 0 else float("nan")
    print(f"Confound set (all true label=0): FALSE POSITIVE RATE={fp_rate:.3f} ({n_fp}/{n_fp+n_tn} flagged as collusive)")

    detection_mod.FEATURE_COLS = FEATURE_COLS  # restore

    os.makedirs(RESULTS_DIR, exist_ok=True)
    train_df.to_csv(f"{RESULTS_DIR}/track1_4_train_features.csv", index=False)
    test_df.to_csv(f"{RESULTS_DIR}/track1_4_test_features.csv", index=False)
    confound_df.to_csv(f"{RESULTS_DIR}/track1_4_confound_features.csv", index=False)

    return {"classifier_test_metrics": metrics_test, "classifier_confound_fp_rate": fp_rate}


if __name__ == "__main__":
    run_track_1_4()
