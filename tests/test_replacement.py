import numpy as np
import pytest

from src.replacement import run_with_replacement, _nearest_price_index
from src.env import LogitBertrandEnv
from src.run_baseline import ConfigTooLargeError

FAST = dict(n_prices=5, n_steps_pre=800, n_steps_post=800, window=200)


def test_nearest_price_index_finds_closest():
    env = LogitBertrandEnv(n_agents=2, n_prices=11)
    idx = _nearest_price_index(env, env.p_nash)
    assert abs(env.price_grid[idx] - env.p_nash) == pytest.approx(np.min(np.abs(env.price_grid - env.p_nash)))


def test_run_with_replacement_none_keeps_same_agents():
    r = run_with_replacement(n_agents=2, replace_fraction=0.5, replace_type="none", seed=0, **FAST)
    assert r["replaced_agent_ids"] == []


def test_run_with_replacement_naive_replaces_expected_count():
    r = run_with_replacement(n_agents=4, replace_fraction=0.5, replace_type="naive", seed=0, **FAST)
    assert len(r["replaced_agent_ids"]) == 2  # round(0.5*4)


def test_run_with_replacement_full_replacement():
    r = run_with_replacement(n_agents=3, replace_fraction=1.0, replace_type="naive", seed=0, **FAST)
    assert len(r["replaced_agent_ids"]) == 3


def test_run_with_replacement_zero_replacement():
    r = run_with_replacement(n_agents=3, replace_fraction=0.0, replace_type="naive", seed=0, **FAST)
    assert r["replaced_agent_ids"] == []


def test_run_with_replacement_returns_windowed_trajectory():
    r = run_with_replacement(n_agents=2, replace_fraction=0.5, replace_type="naive", seed=0, **FAST)
    expected_windows = FAST["n_steps_post"] // FAST["window"]
    assert len(r["post_replacement_deltas"]) == expected_windows
    assert np.isfinite(r["pre_replacement_delta"])
    assert np.isfinite(r["final_delta"])


def test_run_with_replacement_competitive_type_is_valid():
    r = run_with_replacement(n_agents=2, replace_fraction=0.5, replace_type="competitive", seed=0, **FAST)
    assert r["replace_type"] == "competitive"
    assert np.isfinite(r["final_delta"])


def test_run_with_replacement_invalid_type_raises():
    with pytest.raises(ValueError):
        run_with_replacement(n_agents=2, replace_fraction=0.5, replace_type="bogus", seed=0, **FAST)


def test_run_with_replacement_rejects_oversized_config():
    with pytest.raises(ConfigTooLargeError):
        run_with_replacement(n_agents=6, n_prices=20, memory=2, n_steps_pre=10, n_steps_post=10, window=5, seed=0)


def test_run_with_replacement_reproducible_with_same_seed():
    r1 = run_with_replacement(n_agents=2, replace_fraction=0.5, replace_type="naive", seed=7, **FAST)
    r2 = run_with_replacement(n_agents=2, replace_fraction=0.5, replace_type="naive", seed=7, **FAST)
    assert r1["final_delta"] == r2["final_delta"]
    assert r1["replaced_agent_ids"] == r2["replaced_agent_ids"]
