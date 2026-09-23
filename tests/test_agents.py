import numpy as np
import pytest

from src.agents import QLearningAgent, state_to_index, state_space_size


def test_epsilon_decays_toward_zero():
    agent = QLearningAgent(n_actions=5, state_space_size=10, beta=1e-3, seed=0)
    eps_start = agent.epsilon()
    agent.t = 10_000
    eps_late = agent.epsilon()
    assert eps_start == pytest.approx(1.0)
    assert eps_late < eps_start
    assert eps_late >= 0


def test_act_returns_valid_action_index():
    agent = QLearningAgent(n_actions=7, state_space_size=3, seed=1)
    for _ in range(50):
        a = agent.act(state_idx=0)
        assert 0 <= a < 7


def test_act_increments_time_step():
    agent = QLearningAgent(n_actions=3, state_space_size=2, seed=0)
    assert agent.t == 0
    agent.act(0)
    assert agent.t == 1
    agent.act(0)
    assert agent.t == 2


def test_greedy_action_after_forcing_low_exploration():
    agent = QLearningAgent(n_actions=4, state_space_size=1, beta=10.0, seed=0)
    agent.Q[0] = np.array([0.0, 0.0, 5.0, 0.0])
    agent.t = 100  # epsilon ~ exp(-1000) ~ 0, should be fully greedy
    for _ in range(20):
        assert agent.act(0) == 2


def test_q_update_moves_toward_target():
    agent = QLearningAgent(n_actions=2, state_space_size=2, alpha=0.5, gamma=0.9, seed=0)
    agent.Q[0, 0] = 0.0
    agent.Q[1] = np.array([1.0, 2.0])  # best_next = 2.0
    agent.update(state_idx=0, action=0, reward=1.0, next_state_idx=1)
    # target = 1.0 + 0.9*2.0 = 2.8; new Q = 0 + 0.5*(2.8 - 0) = 1.4
    assert agent.Q[0, 0] == pytest.approx(1.4)


def test_q_update_only_touches_chosen_state_action():
    agent = QLearningAgent(n_actions=2, state_space_size=2, alpha=0.5, gamma=0.9, seed=0)
    agent.update(state_idx=0, action=1, reward=1.0, next_state_idx=1)
    assert agent.Q[0, 0] == 0.0
    assert agent.Q[1, 0] == 0.0
    assert agent.Q[1, 1] == 0.0
    assert agent.Q[0, 1] != 0.0


def test_min_epsilon_floors_exploration_rate():
    agent = QLearningAgent(n_actions=3, state_space_size=1, beta=1.0, min_epsilon=0.1, seed=0)
    agent.t = 10_000  # decay term would be ~0 without the floor
    assert agent.epsilon() == pytest.approx(0.1)


def test_min_epsilon_zero_allows_full_decay():
    agent = QLearningAgent(n_actions=3, state_space_size=1, beta=1.0, min_epsilon=0.0, seed=0)
    agent.t = 100
    assert agent.epsilon() < 1e-10


def test_reset_exploration():
    agent = QLearningAgent(n_actions=3, state_space_size=2, seed=0)
    agent.t = 500
    agent.reset_exploration()
    assert agent.t == 0


def test_state_to_index_is_deterministic_and_distinct():
    s1 = ((0, 1),)
    s2 = ((1, 0),)
    i1 = state_to_index(s1, n_prices=5, n_agents=2)
    i2 = state_to_index(s2, n_prices=5, n_agents=2)
    assert i1 != i2
    assert state_to_index(s1, n_prices=5, n_agents=2) == i1  # deterministic


def test_state_to_index_within_bounds():
    n_prices, n_agents, memory = 4, 3, 2
    size = state_space_size(n_prices, n_agents, memory)
    rng = np.random.default_rng(0)
    for _ in range(100):
        state = tuple(
            tuple(int(x) for x in rng.integers(0, n_prices, size=n_agents))
            for _ in range(memory)
        )
        idx = state_to_index(state, n_prices, n_agents)
        assert 0 <= idx < size


def test_state_space_size_formula():
    assert state_space_size(n_prices=5, n_agents=2, memory=1) == 25
    assert state_space_size(n_prices=5, n_agents=2, memory=2) == 625
    assert state_space_size(n_prices=3, n_agents=4, memory=1) == 81
