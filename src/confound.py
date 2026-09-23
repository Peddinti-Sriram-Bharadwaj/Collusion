"""Adversarial confound generator for Track 1.3: independent, non-learning,
purely reactive ("myopic best-response") agents facing a *shared* demand
shock. Their prices co-move because they all react to the same common
cause (the shock), NOT because they are coordinating with each other --
this is exactly the "correlated but not collusive" case that naive
parallel-pricing detectors are known to false-positive on.
"""
from __future__ import annotations

import numpy as np


def _quantities(prices: np.ndarray, a_vec: np.ndarray, a0: float, mu: float) -> np.ndarray:
    num = np.exp((a_vec - prices) / mu)
    denom = num.sum() + np.exp(a0 / mu)
    return num / denom


def _profits(prices: np.ndarray, a_vec: np.ndarray, a0: float, mu: float, c: float) -> np.ndarray:
    q = _quantities(prices, a_vec, a0, mu)
    return (prices - c) * q


def generate_shared_shock_competitive_series(
    n_agents: int = 2,
    n_periods: int = 20_000,
    a_base: float = 2.0,
    a0: float = 0.0,
    mu: float = 0.25,
    c: float = 1.0,
    shock_std: float = 0.05,
    shock_ar: float = 0.98,  # AR(1) persistence of the shared demand shock
    grid_n: int = 61,
    grid_lo: float = 1.2,
    grid_hi: float = 2.2,
    seed: int = 0,
) -> dict:
    """Each period, a common AR(1) shock shifts every agent's demand
    intercept identically. Each agent independently best-responds (one-shot
    static Bertrand best response via grid search) to rivals' prices from
    the previous period under the *current* shock -- no memory-based
    strategy, no observation of rivals' identity/history beyond last price,
    so there is no channel for tacit coordination. Any observed price
    correlation is attributable entirely to the shared shock.
    """
    rng = np.random.default_rng(seed)
    grid = np.linspace(grid_lo, grid_hi, grid_n)

    prices = np.full(n_agents, (grid_lo + grid_hi) / 2)
    shock = 0.0

    price_history = np.zeros((n_periods, n_agents))
    profit_history = np.zeros((n_periods, n_agents))

    for t in range(n_periods):
        shock = shock_ar * shock + rng.normal(0, shock_std)
        a_vec = np.full(n_agents, a_base + shock)

        new_prices = prices.copy()
        for i in range(n_agents):
            best_pi, best_p = -np.inf, prices[i]
            for p in grid:
                trial = prices.copy()
                trial[i] = p
                pi = _profits(trial, a_vec, a0, mu, c)[i]
                if pi > best_pi:
                    best_pi, best_p = pi, p
            new_prices[i] = best_p
        prices = new_prices

        price_history[t] = prices
        profit_history[t] = _profits(prices, a_vec, a0, mu, c)

    return {"price_history": price_history, "profit_history": profit_history}
