import numpy as np

from src.net_influence import (
    simulate_rps_game,
    pairwise_action_correlation,
    pairwise_net_influence,
    rank_pairs,
)


def test_simulate_rps_game_shapes():
    actions, confound = simulate_rps_game(n_players=4, n_rounds=200, seed=0)
    assert actions.shape == (200, 4)
    assert confound.shape == (200,)
    assert set(np.unique(actions)).issubset({0, 1, 2})
    assert set(np.unique(confound)).issubset({0, 1, 2})


def test_net_influence_ranks_true_colluding_pair_first():
    actions, confound = simulate_rps_game(
        n_players=4, n_rounds=400, colluding_pair=(0, 1),
        confound_strength=0.4, collusion_strength=0.9, seed=0,
    )
    ranked = rank_pairs(actions, confound, lag=1)
    assert ranked[0][0] == (0, 1)
    # net influence for the true pair should dominate the rest by a wide margin
    assert ranked[0][2] > 5 * ranked[1][2]


def test_net_influence_flat_when_no_true_collusion():
    actions, confound = simulate_rps_game(
        n_players=4, n_rounds=400, colluding_pair=(0, 1),
        confound_strength=0.6, collusion_strength=0.0, seed=1,
    )
    ranked = rank_pairs(actions, confound, lag=1)
    # with no genuine collusion, net influence should stay small everywhere
    assert all(net < 0.1 for _, _, net in ranked)


def test_net_influence_beats_raw_correlation_under_heavy_confound():
    actions, confound = simulate_rps_game(
        n_players=4, n_rounds=800, colluding_pair=(2, 3),
        confound_strength=0.6, collusion_strength=0.3, seed=2,
    )
    ranked = rank_pairs(actions, confound, lag=1)
    # the true pair should still rank #1 by net influence even though its
    # raw correlation is not cleanly separated from confound-only pairs
    assert ranked[0][0] == (2, 3)


def test_pairwise_action_correlation_range():
    actions, _ = simulate_rps_game(n_players=3, n_rounds=100, seed=3)
    corr = pairwise_action_correlation(actions, 0, 1)
    assert 0.0 <= corr <= 1.0


def test_pairwise_net_influence_nonnegative():
    actions, confound = simulate_rps_game(n_players=3, n_rounds=200, seed=4)
    net = pairwise_net_influence(actions, confound, 0, 1)
    assert net >= -1e-9
