"""Reproduce the Calvano et al. (2020) baseline: two Q-learning agents in a
repeated Bertrand game converge to supra-competitive (collusive) prices.

Usage: python -m src.run_baseline
"""
from __future__ import annotations

import numpy as np

from src.env import LogitBertrandEnv
from src.agents import QLearningAgent, state_to_index, state_space_size

# Hard cap on total Q-table floats (states x actions x agents) to prevent
# memory blowups: state_space_size grows as n_prices**(n_agents*memory), so
# e.g. n_agents=6, n_prices=20, memory=2 would need ~4e15 states per agent.
# This is a coarse backstop against truly absurd configs; for sweeps, the
# dynamic RAM-aware check in src/sweep.py (which knows currently available
# memory) is the primary, tighter gate. 100M floats ~= 800MB for a single run,
# still comfortably safe on its own.
MAX_TOTAL_Q_FLOATS = 100_000_000


class ConfigTooLargeError(ValueError):
    pass


def run_episode(
    n_agents: int = 2,
    n_prices: int = 15,
    memory: int = 1,
    n_steps: int = 500_000,
    convergence_check_window: int = 100_000,
    alpha: float = 0.15,
    gamma: float = 0.95,
    beta: float = 4e-6,
    min_epsilon: float = 0.0,
    per_agent_alpha: list[float] | None = None,
    per_agent_beta: list[float] | None = None,
    seed: int = 0,
) -> dict:
    n_states = state_space_size(n_prices, n_agents, memory)
    total_floats = n_states * n_prices * n_agents
    if total_floats > MAX_TOTAL_Q_FLOATS:
        raise ConfigTooLargeError(
            f"n_agents={n_agents}, n_prices={n_prices}, memory={memory} implies "
            f"{n_states:,} states -> {total_floats:,} total Q-table floats, "
            f"exceeding the {MAX_TOTAL_Q_FLOATS:,} cap. Reduce n_prices/memory/n_agents."
        )

    rng = np.random.default_rng(seed)
    env = LogitBertrandEnv(n_agents=n_agents, n_prices=n_prices, memory=memory)

    alphas = per_agent_alpha or [alpha] * n_agents
    betas = per_agent_beta or [beta] * n_agents
    agents = [
        QLearningAgent(
            n_actions=n_prices,
            state_space_size=n_states,
            alpha=alphas[i],
            gamma=gamma,
            beta=betas[i],
            min_epsilon=min_epsilon,
            seed=seed + i,
        )
        for i in range(n_agents)
    ]

    state = env.reset(rng)
    state_idx = state_to_index(state, n_prices, n_agents)

    profit_history = np.zeros((n_steps, n_agents))
    price_history = np.zeros((n_steps, n_agents))

    for t in range(n_steps):
        actions = tuple(agent.act(state_idx) for agent in agents)
        next_state, profits, info = env.step(actions)
        next_state_idx = state_to_index(next_state, n_prices, n_agents)

        for i, agent in enumerate(agents):
            agent.update(state_idx, actions[i], profits[i], next_state_idx)

        profit_history[t] = profits
        price_history[t] = info["prices"]
        state_idx = next_state_idx

    tail = profit_history[-convergence_check_window:]
    avg_profit = tail.mean(axis=0)
    delta = env.collusion_index(avg_profit)
    tail_prices = price_history[-convergence_check_window:]
    mean_price = tail_prices.mean(axis=0)
    mean_cs = env.consumer_surplus(mean_price)

    return {
        "delta": delta,
        "avg_profit": avg_profit.tolist(),
        "pi_nash": env.pi_nash,
        "pi_monop": env.pi_monop,
        "p_nash": env.p_nash,
        "p_monop": env.p_monop,
        "final_prices_tail_mean": tail_prices.mean(axis=0).tolist(),
        "consumer_surplus": mean_cs,
        "price_history": price_history,
        "profit_history": profit_history,
    }


if __name__ == "__main__":
    result = run_episode(n_steps=200_000, convergence_check_window=20_000, seed=0)
    print(f"Nash price:     {result['p_nash']:.4f}  (profit {result['pi_nash']:.4f})")
    print(f"Monopoly price: {result['p_monop']:.4f}  (profit {result['pi_monop']:.4f})")
    print(f"Converged avg prices: {result['final_prices_tail_mean']}")
    print(f"Converged avg profit: {result['avg_profit']}")
    print(f"Collusion index (delta): {result['delta']:.4f}")
    if result["delta"] > 0.3:
        print("=> Supra-competitive pricing detected (consistent with Calvano et al. finding of tacit collusion).")
    else:
        print("=> Near-competitive outcome.")
