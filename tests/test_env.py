import numpy as np
import pytest

from src.env import LogitBertrandEnv


@pytest.fixture
def env():
    return LogitBertrandEnv(n_agents=2, n_prices=15)


def test_nash_below_monopoly(env):
    """Bertrand-Nash price must be strictly below the collusive/monopoly price."""
    assert env.p_nash < env.p_monop
    assert env.pi_nash < env.pi_monop


def test_price_grid_spans_nash_and_monopoly(env):
    assert env.price_grid.min() <= env.p_nash
    assert env.price_grid.max() >= env.p_monop
    assert len(env.price_grid) == env.n_prices


def test_quantities_sum_less_than_one(env):
    """Logit demand shares (incl. outside good) must not exceed 1."""
    prices = np.full(env.n_agents, env.p_nash)
    q = env._quantities(prices)
    assert q.sum() <= 1.0
    assert np.all(q >= 0)


def test_symmetric_prices_give_symmetric_profits(env):
    prices = np.full(env.n_agents, 1.5)
    pi = env._profits(prices)
    assert np.allclose(pi, pi[0])


def test_higher_own_price_with_rivals_fixed_can_reduce_profit_near_monopoly(env):
    """Near the monopoly price, unilaterally raising further should not increase profit
    (monopoly price is the joint-profit maximizer, so it's at least a local optimum
    for a symmetric deviation check on the demand side)."""
    base = np.full(env.n_agents, env.p_monop)
    base_pi = env._profits(base)[0]
    higher = base.copy()
    higher[0] += 0.05
    higher_pi = env._profits(higher)[0]
    # Not a strict global claim, but the monopoly price should be near a local
    # maximum of *total* profit; individual profit can still rise due to business
    # stealing incentives, so we only check total profit doesn't increase.
    assert env._profits(higher).sum() <= env._profits(base).sum() + 1e-9


def test_step_updates_state_and_returns_profits(env):
    env.reset(np.random.default_rng(0))
    actions = (0, env.n_prices - 1)
    next_state, profits, info = env.step(actions)
    assert next_state == (actions,)
    assert profits.shape == (env.n_agents,)
    assert "prices" in info and "profits" in info


def test_collusion_index_zero_at_nash(env):
    nash_profits = np.full(env.n_agents, env.pi_nash)
    assert env.collusion_index(nash_profits) == pytest.approx(0.0, abs=1e-6)


def test_collusion_index_one_at_monopoly(env):
    monop_profits = np.full(env.n_agents, env.pi_monop)
    assert env.collusion_index(monop_profits) == pytest.approx(1.0, abs=1e-6)


def test_collusion_index_can_exceed_bounds_for_out_of_range_profit(env):
    """Delta isn't clipped -- profits above monopoly (shouldn't happen with real
    joint-max, but agents could still individually be pushed there) map to >1,
    and below-Nash (price wars) map to <0."""
    assert env.collusion_index(np.full(env.n_agents, env.pi_nash - 0.1)) < 0
    assert env.collusion_index(np.full(env.n_agents, env.pi_monop + 0.1)) > 1


def test_memory_greater_than_one_tracks_multiple_rounds():
    env = LogitBertrandEnv(n_agents=2, n_prices=5, memory=2)
    env.reset(np.random.default_rng(0))
    s1, _, _ = env.step((0, 1))
    s2, _, _ = env.step((2, 3))
    assert len(s2) == 2
    assert s2[0] == (0, 1)
    assert s2[1] == (2, 3)


def test_consumer_surplus_decreases_with_higher_prices(env):
    low = np.full(env.n_agents, env.p_nash)
    high = np.full(env.n_agents, env.p_monop)
    assert env.consumer_surplus(low) > env.consumer_surplus(high)


def test_consumer_surplus_finite(env):
    prices = np.full(env.n_agents, env.p_nash)
    assert np.isfinite(env.consumer_surplus(prices))


def test_more_agents_lowers_nash_price():
    """More competitors should drive the Bertrand-Nash price down (textbook result)."""
    env2 = LogitBertrandEnv(n_agents=2, n_prices=10)
    env4 = LogitBertrandEnv(n_agents=4, n_prices=10)
    assert env4.p_nash <= env2.p_nash
