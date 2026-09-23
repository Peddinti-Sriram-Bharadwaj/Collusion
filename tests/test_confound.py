import numpy as np

from src.confound import generate_shared_shock_competitive_series


def test_confound_series_shapes():
    r = generate_shared_shock_competitive_series(n_agents=3, n_periods=200, seed=0)
    assert r["price_history"].shape == (200, 3)
    assert r["profit_history"].shape == (200, 3)


def test_confound_prices_within_grid_bounds():
    r = generate_shared_shock_competitive_series(n_agents=2, n_periods=200, grid_lo=1.2, grid_hi=2.2, seed=0)
    assert r["price_history"].min() >= 1.2 - 1e-9
    assert r["price_history"].max() <= 2.2 + 1e-9


def test_confound_prices_are_correlated_via_shared_shock():
    """The whole point of this generator: cross-agent price correlation
    should be clearly positive (driven by the shared shock) even though
    agents never observe each other's strategy/history beyond last price."""
    r = generate_shared_shock_competitive_series(n_agents=2, n_periods=3000, shock_std=0.08, seed=0)
    corr = np.corrcoef(r["price_history"][:, 0], r["price_history"][:, 1])[0, 1]
    assert corr > 0.3


def test_confound_reproducible_with_same_seed():
    r1 = generate_shared_shock_competitive_series(n_agents=2, n_periods=200, seed=5)
    r2 = generate_shared_shock_competitive_series(n_agents=2, n_periods=200, seed=5)
    assert np.array_equal(r1["price_history"], r2["price_history"])


def test_confound_zero_shock_std_gives_constant_prices():
    """With no shock at all, symmetric best-response should settle at a fixed
    point and stay there (a degenerate but useful sanity check)."""
    r = generate_shared_shock_competitive_series(n_agents=2, n_periods=50, shock_std=0.0, seed=0)
    tail = r["price_history"][-10:]
    assert np.allclose(tail, tail[0], atol=1e-6)
