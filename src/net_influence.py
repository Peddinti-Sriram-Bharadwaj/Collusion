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
"""
from __future__ import annotations

import numpy as np

from src.info_theory import mutual_information, conditional_mutual_information


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
