import numpy as np
import pandas as pd
import pytest

from src.detection import (
    profit_gain_detector,
    parallel_pricing_detector,
    extract_price_features,
    build_feature_dataset,
    train_classifier,
    evaluate_classifier,
    FEATURE_COLS,
    _mean_pairwise_corr,
)


def test_profit_gain_detector_threshold():
    assert profit_gain_detector(0.3, threshold=0.15) is True
    assert profit_gain_detector(0.1, threshold=0.15) is False


def test_mean_pairwise_corr_perfectly_correlated():
    x = np.arange(100)
    ph = np.column_stack([x, x])
    assert _mean_pairwise_corr(ph) == pytest.approx(1.0)


def test_mean_pairwise_corr_uncorrelated_constant_series():
    ph = np.column_stack([np.full(50, 1.0), np.full(50, 2.0)])
    assert _mean_pairwise_corr(ph) == 0.0  # zero-variance guard, not NaN


def test_mean_pairwise_corr_single_agent_is_zero():
    ph = np.ones((10, 1))
    assert _mean_pairwise_corr(ph) == 0.0


def test_parallel_pricing_detector_flags_high_correlation():
    x = np.linspace(0, 1, 100) + np.random.default_rng(0).normal(0, 0.001, 100)
    ph = np.column_stack([x, x])
    assert parallel_pricing_detector(ph, threshold=0.5) is True


def test_parallel_pricing_detector_false_on_independent_noise():
    rng = np.random.default_rng(0)
    ph = rng.normal(0, 1, size=(500, 2))
    assert parallel_pricing_detector(ph, threshold=0.9) is False


def test_extract_price_features_returns_all_keys():
    rng = np.random.default_rng(0)
    ph = rng.uniform(1.4, 1.9, size=(300, 2))
    feats = extract_price_features(ph, price_grid=np.linspace(1.3, 2.0, 10))
    for key in ["price_level_norm", "pairwise_price_corr", "mean_autocorr", "dispersion_ratio"]:
        assert key in feats
        assert np.isfinite(feats[key])


def test_extract_price_features_level_normalization_in_unit_range():
    ph = np.full((100, 2), 1.65)
    grid = np.linspace(1.3, 2.0, 10)
    feats = extract_price_features(ph, price_grid=grid)
    assert 0.0 <= feats["price_level_norm"] <= 1.0


def test_build_feature_dataset_preserves_labels():
    examples = [
        {"price_history": np.random.default_rng(0).uniform(1, 2, (100, 2)), "label": 1},
        {"price_history": np.random.default_rng(1).uniform(1, 2, (100, 2)), "label": 0},
    ]
    df = build_feature_dataset(examples)
    assert list(df["label"]) == [1, 0]
    assert len(df) == 2


def test_classifier_separates_synthetic_collusive_vs_competitive():
    """Collusive: high, tightly correlated prices. Competitive: lower, less
    correlated prices. A classifier trained on these should separate them
    near-perfectly -- sanity check that the pipeline (features -> fit ->
    predict) works end to end."""
    rng = np.random.default_rng(0)
    examples = []
    for _ in range(30):
        base = 1.85 + rng.normal(0, 0.01)
        ph = np.column_stack([base + rng.normal(0, 0.01, 200), base + rng.normal(0, 0.01, 200)])
        examples.append({"price_history": ph, "label": 1})
    for _ in range(30):
        ph = rng.uniform(1.3, 1.6, size=(200, 2))
        examples.append({"price_history": ph, "label": 0})

    df = build_feature_dataset(examples)
    train_df = pd.concat([df.iloc[:24], df.iloc[30:54]])
    test_df = pd.concat([df.iloc[24:30], df.iloc[54:60]])

    clf = train_classifier(train_df)
    metrics = evaluate_classifier(clf, test_df)
    assert metrics["f1"] > 0.8
