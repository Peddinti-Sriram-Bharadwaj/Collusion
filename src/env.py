"""Repeated Bertrand pricing game with logit demand (Calvano et al. 2020).

Reference: Calvano, Calzolari, Denicolo, Pastorello (2020), "Artificial
Intelligence, Algorithmic Pricing, and Collusion", American Economic Review.
"""
from __future__ import annotations

import numpy as np


class LogitBertrandEnv:
    """N-firm repeated Bertrand competition with logit demand.

    Demand for firm i given prices p (vector of length n):
        q_i = exp((a_i - p_i) / mu) / (sum_j exp((a_j - p_j) / mu) + exp(a_0 / mu))

    Profit: pi_i = (p_i - c_i) * q_i

    State observed by each agent: the joint action (price index) played by
    all firms in the previous `memory` rounds (default memory=1, i.e. last round).
    """

    def __init__(
        self,
        n_agents: int = 2,
        n_prices: int = 15,
        a: float = 2.0,
        a0: float = 0.0,
        mu: float = 0.25,
        c: float = 1.0,
        memory: int = 1,
        price_low_mult: float = 0.9,
        price_high_mult: float = 1.1,
    ):
        self.n_agents = n_agents
        self.n_prices = n_prices
        self.a = a
        self.a0 = a0
        self.mu = mu
        self.c = c
        self.memory = memory

        # Nash and monopoly reference prices (computed via grid search over a
        # fine price grid), used to set the action grid and to normalize profit.
        self.p_nash, self.pi_nash = self._compute_nash()
        self.p_monop, self.pi_monop = self._compute_monopoly()

        lo = price_low_mult * min(self.p_nash, self.p_monop)
        hi = price_high_mult * max(self.p_nash, self.p_monop)
        self.price_grid = np.linspace(lo, hi, n_prices)

        self.state = None  # tuple of last `memory` joint actions (each a tuple of ints)
        self.reset()

    # ------------------------------------------------------------------
    # Demand / profit
    # ------------------------------------------------------------------
    def _quantities(self, prices: np.ndarray) -> np.ndarray:
        num = np.exp((self.a - prices) / self.mu)
        denom = num.sum() + np.exp(self.a0 / self.mu)
        return num / denom

    def _profits(self, prices: np.ndarray) -> np.ndarray:
        q = self._quantities(prices)
        return (prices - self.c) * q

    def _compute_nash(self, n_grid: int = 1001, iters: int = 200):
        """Best-response iteration to find the symmetric Bertrand-Nash price."""
        grid = np.linspace(self.c, self.a + 3, n_grid)
        prices = np.full(self.n_agents, self.c + 0.5)
        for _ in range(iters):
            new_prices = prices.copy()
            for i in range(self.n_agents):
                best_pi, best_p = -np.inf, prices[i]
                for p in grid:
                    trial = prices.copy()
                    trial[i] = p
                    pi = self._profits(trial)[i]
                    if pi > best_pi:
                        best_pi, best_p = pi, p
                new_prices[i] = best_p
            if np.allclose(new_prices, prices, atol=1e-4):
                prices = new_prices
                break
            prices = new_prices
        pi = self._profits(prices)
        return float(prices[0]), float(pi[0])

    def _compute_monopoly(self, n_grid: int = 1001):
        """Symmetric joint-profit-maximizing (collusive) price."""
        grid = np.linspace(self.c, self.a + 3, n_grid)
        best_total, best_p = -np.inf, grid[0]
        for p in grid:
            prices = np.full(self.n_agents, p)
            total = self._profits(prices).sum()
            if total > best_total:
                best_total, best_p = total, p
        pi = self._profits(np.full(self.n_agents, best_p))
        return float(best_p), float(pi[0])

    # ------------------------------------------------------------------
    # Gym-like API
    # ------------------------------------------------------------------
    def reset(self, rng: np.random.Generator | None = None):
        rng = rng or np.random.default_rng()
        init_actions = tuple(int(x) for x in rng.integers(0, self.n_prices, size=self.n_agents))
        self.state = tuple([init_actions] * self.memory)
        return self.state

    def step(self, actions: tuple[int, ...]):
        prices = self.price_grid[np.array(actions)]
        profits = self._profits(prices)
        next_state = tuple(list(self.state[1:]) + [tuple(int(a) for a in actions)]) if self.memory > 1 else (tuple(int(a) for a in actions),)
        self.state = next_state
        info = {"prices": prices, "profits": profits}
        return next_state, profits, info

    def consumer_surplus(self, prices: np.ndarray) -> float:
        """Standard multinomial-logit inclusive-value consumer surplus proxy:
        CS = mu * ln( sum_j exp((a_j - p_j)/mu) + exp(a0/mu) ).
        Monotonically decreasing in prices; used only for *relative*
        welfare comparisons (e.g. CS under a restriction vs. CS at baseline),
        not as an absolute currency-denominated welfare figure.
        """
        inside = np.exp((self.a - prices) / self.mu).sum()
        outside = np.exp(self.a0 / self.mu)
        return float(self.mu * np.log(inside + outside))

    def collusion_index(self, profits: np.ndarray) -> float:
        """Delta = (avg profit - nash) / (monopoly - nash). 0=competitive, 1=collusive."""
        avg_pi = float(np.mean(profits))
        return (avg_pi - self.pi_nash) / (self.pi_monop - self.pi_nash)
