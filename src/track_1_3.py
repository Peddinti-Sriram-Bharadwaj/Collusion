"""Track 1.3: benchmark collusion detectors, including robustness to the
'correlated but not collusive' confound (shared demand shock, src/confound.py).

Labeled dataset:
  label=1 (collusive):   Q-learning runs at configs known from Track 1.1 to
                          converge to high Delta (n_agents=2, moderate beta).
  label=0 (competitive):  (a) Q-learning runs at configs known to converge
                          near/below Nash (n_agents=6, or the beta=1.0
                          "near-zero exploration" ablation), and
                          (b) the shared-shock confound series -- included
                          in the TEST set only, to measure false-positive
                          rate on genuinely non-collusive-but-correlated data.

Usage: python -m src.track_1_3
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from src.run_baseline import run_episode
from src.confound import generate_shared_shock_competitive_series
from src.detection import (
    profit_gain_detector,
    parallel_pricing_detector,
    build_feature_dataset,
    train_classifier,
    evaluate_classifier,
)

RESULTS_DIR = "results"
WINDOW = 15_000  # tail window used for feature extraction, matches convergence_check_window scale


def _collusive_examples(n_seeds: int, seed_offset: int = 0) -> list[dict]:
    examples = []
    for s in range(seed_offset, seed_offset + n_seeds):
        r = run_episode(n_agents=2, n_prices=10, n_steps=100_000, convergence_check_window=WINDOW, beta=4e-6, seed=s)
        ph = r["price_history"][-WINDOW:]
        grid = np.linspace(ph.min(), ph.max(), 10)  # local grid proxy; real grid not returned by run_episode
        examples.append({"price_history": ph, "label": 1, "delta": r["delta"]})
    return examples


def _competitive_examples(n_seeds: int, seed_offset: int = 0) -> list[dict]:
    examples = []
    for s in range(seed_offset, seed_offset + n_seeds):
        r = run_episode(n_agents=6, n_prices=10, n_steps=100_000, convergence_check_window=WINDOW, beta=4e-6, seed=s)
        ph = r["price_history"][-WINDOW:]
        examples.append({"price_history": ph, "label": 0, "delta": r["delta"]})
    return examples


def _confound_examples(n_seeds: int, seed_offset: int = 0) -> list[dict]:
    examples = []
    for s in range(seed_offset, seed_offset + n_seeds):
        r = generate_shared_shock_competitive_series(n_agents=2, n_periods=WINDOW, shock_std=0.06, seed=s)
        examples.append({"price_history": r["price_history"], "label": 0, "delta": None})
    return examples


def run_track_1_3(n_train_seeds: int = 15, n_test_seeds: int = 8, n_confound_seeds: int = 15):
    print("Generating labeled Q-learning trajectories...")
    train_examples = _collusive_examples(n_train_seeds, 0) + _competitive_examples(n_train_seeds, 0)
    test_examples = _collusive_examples(n_test_seeds, 1000) + _competitive_examples(n_test_seeds, 1000)
    confound_examples = _confound_examples(n_confound_seeds, 0)

    train_df = build_feature_dataset(train_examples)
    test_df = build_feature_dataset(test_examples)
    confound_df = build_feature_dataset(confound_examples)

    # --- Baseline 1: profit-gain threshold (uses ground-truth delta directly;
    # included as an oracle upper bound, and to show it can't even be applied
    # to the confound set, which has no profit/delta available in a real deployment).
    print("\n--- Baseline: profit-gain threshold detector ---")
    test_deltas = [ex["delta"] for ex in test_examples]
    test_labels = [ex["label"] for ex in test_examples]
    pg_preds = [int(profit_gain_detector(d, threshold=0.15)) for d in test_deltas]
    pg_acc = np.mean(np.array(pg_preds) == np.array(test_labels))
    print(f"Profit-gain detector accuracy on held-out Q-learning test set: {pg_acc:.3f}")

    # --- Baseline 2: naive parallel-pricing correlation detector ---
    print("\n--- Baseline: parallel-pricing correlation detector ---")
    for name, examples in [("held-out Q-learning test set", test_examples), ("confound (shared shock)", confound_examples)]:
        preds = [int(parallel_pricing_detector(ex["price_history"], threshold=0.5)) for ex in examples]
        labels = [ex["label"] for ex in examples]
        fp_rate = np.mean(np.array(preds) == 1) if all(l == 0 for l in labels) else None
        acc = np.mean(np.array(preds) == np.array(labels))
        print(f"  on {name}: accuracy={acc:.3f}" + (f", FALSE POSITIVE RATE={fp_rate:.3f}" if fp_rate is not None else ""))

    # --- Proposed: trajectory-feature classifier ---
    print("\n--- Proposed: trajectory-feature classifier (random forest) ---")
    clf = train_classifier(train_df)
    metrics_test = evaluate_classifier(clf, test_df)
    print(f"Held-out Q-learning test set: precision={metrics_test['precision']:.3f} recall={metrics_test['recall']:.3f} f1={metrics_test['f1']:.3f}")
    print(f"  confusion matrix [[TN,FP],[FN,TP]]: {metrics_test['confusion_matrix']}")

    metrics_confound = evaluate_classifier(clf, confound_df)
    fp_rate_clf = 1 - metrics_confound["precision"] if metrics_confound["confusion_matrix"][0][1] + metrics_confound["confusion_matrix"][0][0] > 0 else None
    n_fp = metrics_confound["confusion_matrix"][0][1]
    n_tn = metrics_confound["confusion_matrix"][0][0]
    print(f"Confound set (all true label=0): FALSE POSITIVE RATE={n_fp / (n_fp + n_tn):.3f} ({n_fp}/{n_fp+n_tn} flagged as collusive)")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    train_df.to_csv(f"{RESULTS_DIR}/track1_3_train_features.csv", index=False)
    test_df.to_csv(f"{RESULTS_DIR}/track1_3_test_features.csv", index=False)
    confound_df.to_csv(f"{RESULTS_DIR}/track1_3_confound_features.csv", index=False)

    return {
        "profit_gain_accuracy": pg_acc,
        "classifier_test_metrics": metrics_test,
        "classifier_confound_fp_rate": n_fp / (n_fp + n_tn),
    }


if __name__ == "__main__":
    run_track_1_3()
