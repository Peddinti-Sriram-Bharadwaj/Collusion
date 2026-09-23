"""Q-learning agent for the repeated pricing game."""
from __future__ import annotations

import numpy as np


class QLearningAgent:
    def __init__(
        self,
        n_actions: int,
        state_space_size: int,
        alpha: float = 0.15,
        gamma: float = 0.95,
        beta: float = 4e-6,  # exploration decay rate (Calvano-style)
        min_epsilon: float = 0.0,  # regulatory exploration floor (Track 1.5)
        seed: int | None = None,
    ):
        self.n_actions = n_actions
        self.alpha = alpha
        self.gamma = gamma
        self.beta = beta
        self.min_epsilon = min_epsilon
        self.rng = np.random.default_rng(seed)
        # optimistic init at mid-range profit helps stabilize early exploration
        self.Q = np.zeros((state_space_size, n_actions))
        self.t = 0

    def epsilon(self) -> float:
        return max(self.min_epsilon, np.exp(-self.beta * self.t))

    def act(self, state_idx: int) -> int:
        self.t += 1
        if self.rng.random() < self.epsilon():
            return int(self.rng.integers(0, self.n_actions))
        return int(np.argmax(self.Q[state_idx]))

    def update(self, state_idx: int, action: int, reward: float, next_state_idx: int):
        best_next = np.max(self.Q[next_state_idx])
        td_target = reward + self.gamma * best_next
        self.Q[state_idx, action] += self.alpha * (td_target - self.Q[state_idx, action])

    def reset_exploration(self):
        self.t = 0


class FixedIndexAgent:
    """A non-learning agent that always plays the same fixed action index.

    Used as a 'competitive regulator plant' (fixed at the Nash price index)
    or any other fixed-strategy stand-in for replacement experiments.
    """

    def __init__(self, action_index: int):
        self.action_index = action_index
        self.t = 0

    def epsilon(self) -> float:
        return 0.0

    def act(self, state_idx: int) -> int:
        self.t += 1
        return self.action_index

    def update(self, state_idx: int, action: int, reward: float, next_state_idx: int):
        pass  # fixed policy, no learning

    def reset_exploration(self):
        self.t = 0


def state_to_index(state: tuple, n_prices: int, n_agents: int) -> int:
    """Flatten a state (tuple of joint-action tuples) into a single index."""
    idx = 0
    for joint_action in state:
        for a in joint_action:
            idx = idx * n_prices + a
    return idx


def state_space_size(n_prices: int, n_agents: int, memory: int) -> int:
    return (n_prices ** n_agents) ** memory
