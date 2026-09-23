import numpy as np
import pytest

from src.run_baseline import run_episode, ConfigTooLargeError


def test_run_episode_short_smoke():
    result = run_episode(n_steps=2000, convergence_check_window=500, seed=0)
    assert "delta" in result
    assert result["pi_nash"] < result["pi_monop"]
    assert result["p_nash"] < result["p_monop"]
    assert len(result["avg_profit"]) == 2
    assert np.isfinite(result["delta"])


def test_run_episode_reproducible_with_same_seed():
    r1 = run_episode(n_steps=2000, convergence_check_window=500, seed=42)
    r2 = run_episode(n_steps=2000, convergence_check_window=500, seed=42)
    assert r1["delta"] == r2["delta"]
    assert r1["avg_profit"] == r2["avg_profit"]


def test_run_episode_different_seeds_can_differ():
    r1 = run_episode(n_steps=2000, convergence_check_window=500, seed=1)
    r2 = run_episode(n_steps=2000, convergence_check_window=500, seed=2)
    # Not guaranteed to differ, but with different exploration draws it's
    # overwhelmingly likely across 2000 steps; guards against a seed being ignored.
    assert r1["price_history"].tolist() != r2["price_history"].tolist()


def test_run_episode_scales_to_three_agents():
    result = run_episode(n_agents=3, n_prices=6, n_steps=1500, convergence_check_window=300, seed=0)
    assert len(result["avg_profit"]) == 3
    assert np.isfinite(result["delta"])


def test_run_episode_rejects_configs_that_would_blow_up_memory():
    """Guards against the RAM-exhaustion crash: n_prices**(n_agents*memory) explodes fast."""
    with pytest.raises(ConfigTooLargeError):
        run_episode(n_agents=6, n_prices=20, memory=2, n_steps=10)


def test_run_episode_accepts_config_just_under_the_cap():
    # small config should not raise
    result = run_episode(n_agents=2, n_prices=5, memory=1, n_steps=100, convergence_check_window=50, seed=0)
    assert np.isfinite(result["delta"])


def test_run_episode_returns_consumer_surplus():
    result = run_episode(n_steps=500, convergence_check_window=200, seed=0)
    assert "consumer_surplus" in result
    assert np.isfinite(result["consumer_surplus"])


def test_run_episode_min_epsilon_prevents_full_exploration_decay():
    """A high exploration floor should push the market toward more random
    (lower, noisier) pricing than the zero-floor baseline -- sanity check
    that min_epsilon actually has a behavioral effect."""
    kwargs = dict(n_steps=3000, convergence_check_window=500, beta=1e-3, seed=0)
    baseline = run_episode(min_epsilon=0.0, **kwargs)
    floored = run_episode(min_epsilon=0.3, **kwargs)
    assert baseline["delta"] != floored["delta"]


def test_run_episode_per_agent_heterogeneity():
    result = run_episode(
        n_agents=2, n_steps=500, convergence_check_window=200,
        per_agent_alpha=[0.05, 0.5], per_agent_beta=[1e-6, 1e-4], seed=0,
    )
    assert np.isfinite(result["delta"])
