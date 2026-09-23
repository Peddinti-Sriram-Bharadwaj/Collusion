import numpy as np
import pytest

from src.info_theory import (
    discretize_series,
    entropy,
    mutual_information,
    conditional_mutual_information,
    transfer_entropy,
    interaction_information,
)


def test_discretize_series_constant_input():
    x = np.full(50, 3.0)
    labels = discretize_series(x, bins=8)
    assert np.all(labels == 0)


def test_discretize_series_roughly_balanced_bins():
    rng = np.random.default_rng(0)
    x = rng.uniform(0, 1, 8000)
    labels = discretize_series(x, bins=8)
    counts = np.bincount(labels, minlength=8)
    assert counts.min() > 0
    assert counts.max() / counts.min() < 2.0  # roughly balanced, uniform input


def test_entropy_of_uniform_discrete_matches_log2n():
    rng = np.random.default_rng(0)
    labels = rng.integers(0, 4, size=20000)
    assert entropy(labels) == pytest.approx(2.0, abs=0.02)  # log2(4) = 2 bits


def test_entropy_of_constant_is_zero():
    labels = np.zeros(100, dtype=int)
    assert entropy(labels) == pytest.approx(0.0)


def test_mutual_information_zero_for_independent_series():
    rng = np.random.default_rng(0)
    x = discretize_series(rng.normal(size=20000), bins=6)
    y = discretize_series(rng.normal(size=20000), bins=6)
    mi = mutual_information(x, y)
    assert mi < 0.02  # near zero, small finite-sample bias allowed


def test_mutual_information_high_for_identical_series():
    rng = np.random.default_rng(0)
    x = discretize_series(rng.normal(size=5000), bins=6)
    mi = mutual_information(x, x)
    assert mi == pytest.approx(entropy(x), abs=1e-9)


def test_transfer_entropy_detects_true_causal_coupling():
    """Y drives X with a 1-step lag: X_t = 0.9*Y_{t-1} + noise. TE(Y->X)
    should be clearly larger than TE(X->Y) (no reverse causality)."""
    rng = np.random.default_rng(0)
    n = 20000
    y = rng.normal(size=n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = 0.9 * y[t - 1] + 0.1 * rng.normal()

    te_y_to_x = transfer_entropy(y, x, bins=6)
    te_x_to_y = transfer_entropy(x, y, bins=6)
    assert te_y_to_x > te_x_to_y
    assert te_y_to_x > 0.1


def test_transfer_entropy_near_zero_for_independent_series():
    rng = np.random.default_rng(0)
    x = rng.normal(size=20000)
    y = rng.normal(size=20000)
    te = transfer_entropy(x, y, bins=6)
    assert te < 0.05


def test_transfer_entropy_low_for_shared_driver_no_direct_coupling():
    """X and Y are both driven by a common Z (with different, independent
    noise), but NEITHER directly influences the other. Transfer entropy
    between X and Y (each direction) should stay low despite them being
    correlated -- this is the key property that should make TE more robust
    than raw correlation on the shared-shock confound."""
    rng = np.random.default_rng(0)
    n = 20000
    z = rng.normal(size=n)
    x = z + 0.3 * rng.normal(size=n)
    y = z + 0.3 * rng.normal(size=n)

    te_x_to_y = transfer_entropy(x, y, bins=6)
    te_y_to_x = transfer_entropy(y, x, bins=6)
    corr = np.corrcoef(x, y)[0, 1]

    assert corr > 0.7  # strongly correlated (the confound property)
    assert te_x_to_y < 0.05  # but no directed transfer between them
    assert te_y_to_x < 0.05


def test_interaction_information_positive_for_shared_cause():
    """Classic redundancy case: Z causes both X and Y independently.
    Conditioning on Z should explain away the X-Y correlation, giving
    positive interaction information (redundancy signature)."""
    rng = np.random.default_rng(0)
    n = 20000
    z = rng.integers(0, 4, size=n)
    x = z + rng.integers(0, 2, size=n)
    y = z + rng.integers(0, 2, size=n)
    ii = interaction_information(x, y, z, bins=6)
    assert ii > 0.1


def test_interaction_information_negative_for_synergy():
    """XOR-type synergy: Z tells you nothing about X or Y alone, but X,Y
    jointly determine Z in a way pairwise correlations don't capture --
    classic synergistic construction, should give negative II."""
    rng = np.random.default_rng(0)
    n = 20000
    x = rng.integers(0, 2, size=n)
    y = rng.integers(0, 2, size=n)
    z = x ^ y  # XOR: synergistic, z uncorrelated with x or y individually
    ii = interaction_information(x, y, z, bins=2)
    assert ii < -0.1
