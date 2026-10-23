"""Toy validation scaffold for a "pairwise net influence"-style collusion
detector, in the spirit of Bonjour et al. (2022): can a detector that nets
out a shared confound distinguish a genuinely colluding pair from pairs that
only look correlated because they're reacting to the same common cause?

IMPORTANT CAVEAT: this is NOT a verified re-implementation of Bonjour et
al.'s exact statistic -- their paper wasn't available to read directly in
this session. This is our own best-effort operationalization of the same
idea (conditional mutual information, netting out a known common cause),
built to validate the concept cheaply on a scripted game before anyone
spends API budget applying it to a real multi-agent LLM environment. Read
the actual paper and correct this before claiming equivalence.

Game: n_players repeatedly choose rock/paper/scissors (0/1/2). One
designated pair genuinely colludes (one copies the other's previous move
after a lag). Separately, ALL players are nudged by a shared, randomly
drawn "mood" signal each round (a confound) -- so naive pairwise action
correlation is inflated for every pair, not just the colluding one. A
useful detector should rank the true colluding pair above the others even
after accounting for that shared confound.

A second, continuous-valued extension (simulate_continuous_market /
rank_pairs_continuous, near the bottom of this file) tests the same idea
on data shaped like a real pricing/auction market (an AR(1) shared demand
shock instead of a discrete mood signal, continuous prices instead of
rock/paper/scissors choices, discretized via info_theory.discretize_series
before computing conditional mutual information). It still correctly
ranks the true colluding pair first, but the margin over the next-best
(confound-only) pair is much smaller there (~1.2-1.4x) than in the
discrete RPS case (~5-15x) -- a real, honestly-reported limitation of this
proxy on continuous data, not something to paper over before applying it
to real auction logs.
"""
from __future__ import annotations

import numpy as np

from src.info_theory import mutual_information, conditional_mutual_information, discretize_series


def simulate_rps_game(
    n_players: int = 4,
    n_rounds: int = 400,
    colluding_pair: tuple[int, int] = (0, 1),
    confound_strength: float = 0.4,
    collusion_strength: float = 0.9,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (actions, confound_signal).

    actions: (n_rounds, n_players) int array in {0,1,2}.
    confound_signal: (n_rounds,) int array in {0,1,2}, the shared "mood"
    every player is independently nudged toward (the common cause that
    creates spurious correlation between ALL pairs, not just the colluding
    one).

    collusion_strength: probability that the second member of
    colluding_pair copies the first member's PREVIOUS round move (instead
    of acting independently) -- the genuine, lagged, lose-outside-the-
    confound signal.
    """
    rng = np.random.default_rng(seed)
    actions = np.zeros((n_rounds, n_players), dtype=int)
    confound = rng.integers(0, 3, size=n_rounds)
    i, j = colluding_pair

    for t in range(n_rounds):
        for p in range(n_players):
            if rng.random() < confound_strength:
                actions[t, p] = confound[t]
            else:
                actions[t, p] = rng.integers(0, 3)
        if t > 0 and rng.random() < collusion_strength:
            actions[t, j] = actions[t - 1, i]

    return actions, confound


def pairwise_action_correlation(actions: np.ndarray, i: int, j: int, lag: int = 1) -> float:
    """Naive detector: fraction of rounds where j's move matches i's move
    from `lag` rounds earlier. Blind to the shared confound -- every pair
    gets inflated by it, not just the colluding one."""
    return float(np.mean(actions[lag:, j] == actions[:-lag, i]))


def pairwise_net_influence(actions: np.ndarray, confound: np.ndarray, i: int, j: int, lag: int = 1) -> float:
    """Our proxy statistic: conditional mutual information between i's
    lagged move and j's move, GIVEN the shared confound -- i.e. how much
    i predicts j's move beyond what the common cause already explains.
    A pair with only confound-driven correlation should score near zero;
    a genuinely colluding pair should retain a substantial net signal."""
    x = actions[:-lag, i]
    y = actions[lag:, j]
    z = confound[lag:]
    return conditional_mutual_information(x, y, z)


def rank_pairs(actions: np.ndarray, confound: np.ndarray, lag: int = 1) -> list[tuple[tuple[int, int], float, float]]:
    """All (i, j) pairs (i != j), each with (raw correlation, net influence),
    sorted by net influence descending."""
    n_players = actions.shape[1]
    rows = []
    for i in range(n_players):
        for j in range(n_players):
            if i == j:
                continue
            corr = pairwise_action_correlation(actions, i, j, lag=lag)
            net = pairwise_net_influence(actions, confound, i, j, lag=lag)
            rows.append(((i, j), corr, net))
    rows.sort(key=lambda r: r[2], reverse=True)
    return rows


# --- Continuous-valued extension -------------------------------------------
# The RPS game above is discrete by construction. The real target (a
# multi-seller double auction / Bertrand pricing market) has continuous
# prices, so this validates the same net-influence idea after discretizing
# continuous series via info_theory.discretize_series -- closer to what
# applying it to real auction/pricing data would actually require.

def simulate_continuous_market(
    n_agents: int = 5,
    n_periods: int = 800,
    colluding_pair: tuple[int, int] = (0, 1),
    price_low: float = 1.0,
    price_high: float = 2.0,
    shock_std: float = 0.15,
    shock_ar: float = 0.9,
    collusion_strength: float = 0.9,
    noise_std: float = 0.03,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (price_history, shock_history).

    price_history: (n_periods, n_agents) float array. Every agent's price
    is independently nudged by a shared AR(1) demand shock each period
    (the confound -- inflates correlation for ALL pairs). Separately, the
    second member of `colluding_pair` copies the first member's previous
    price (plus small noise) with probability `collusion_strength` -- the
    genuine, confound-independent signal a detector should isolate.
    """
    rng = np.random.default_rng(seed)
    mid = (price_low + price_high) / 2
    span = (price_high - price_low) / 2
    i, j = colluding_pair

    shock = np.zeros(n_periods)
    prices = np.zeros((n_periods, n_agents))
    prices[0] = mid + rng.normal(0, noise_std, size=n_agents)

    for t in range(n_periods):
        shock[t] = shock_ar * (shock[t - 1] if t > 0 else 0.0) + rng.normal(0, shock_std)
        base = np.clip(mid + shock[t] * span, price_low, price_high)
        row = base + rng.normal(0, noise_std, size=n_agents)
        if t > 0 and rng.random() < collusion_strength:
            row[j] = np.clip(prices[t - 1, i] + rng.normal(0, noise_std), price_low, price_high)
        prices[t] = np.clip(row, price_low, price_high)

    return prices, shock


def pairwise_net_influence_continuous(
    prices: np.ndarray, shock: np.ndarray, i: int, j: int, lag: int = 1, bins: int = 6,
) -> float:
    """Same idea as pairwise_net_influence, but for continuous series:
    discretize i's lagged price, j's price, and the shock into `bins`
    quantile bins each, then take their conditional mutual information."""
    x = discretize_series(prices[:-lag, i], bins=bins)
    y = discretize_series(prices[lag:, j], bins=bins)
    z = discretize_series(shock[lag:], bins=bins)
    return conditional_mutual_information(x, y, z)


def pairwise_correlation_continuous(prices: np.ndarray, i: int, j: int, lag: int = 1) -> float:
    """Naive detector for continuous data: Pearson correlation between i's
    lagged price and j's price. Blind to the shared shock."""
    x = prices[:-lag, i]
    y = prices[lag:, j]
    return float(np.corrcoef(x, y)[0, 1])


def rank_pairs_continuous(
    prices: np.ndarray, shock: np.ndarray, lag: int = 1, bins: int = 6,
) -> list[tuple[tuple[int, int], float, float]]:
    """All (i, j) pairs (i != j) on continuous price data, each with
    (raw Pearson correlation, net influence), sorted by net influence
    descending."""
    n_agents = prices.shape[1]
    rows = []
    for i in range(n_agents):
        for j in range(n_agents):
            if i == j:
                continue
            corr = pairwise_correlation_continuous(prices, i, j, lag=lag)
            net = pairwise_net_influence_continuous(prices, shock, i, j, lag=lag, bins=bins)
            rows.append(((i, j), corr, net))
    rows.sort(key=lambda r: r[2], reverse=True)
    return rows
