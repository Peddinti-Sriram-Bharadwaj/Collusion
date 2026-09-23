"""Track 1.2: Once collusion has formed, is it robust to replacing some of
the participants?

Trains agents to convergence, then at a chosen step replaces a subset of
them (with either a freshly-initialized naive Q-learner, or a fixed
"competitive regulator plant" agent pinned at the Nash price), and tracks
the collusion index in windows before/after replacement to see whether the
group re-converges to collusion, stays competitive, or destabilizes.
"""
from __future__ import annotations

import numpy as np

from src.env import LogitBertrandEnv
from src.agents import QLearningAgent, FixedIndexAgent, state_to_index, state_space_size
from src.run_baseline import MAX_TOTAL_Q_FLOATS, ConfigTooLargeError


def _nearest_price_index(env: LogitBertrandEnv, price: float) -> int:
    return int(np.argmin(np.abs(env.price_grid - price)))


def run_with_replacement(
    n_agents: int = 2,
    n_prices: int = 10,
    memory: int = 1,
    n_steps_pre: int = 100_000,
    n_steps_post: int = 100_000,
    replace_fraction: float = 0.5,
    replace_type: str = "naive",  # "naive" | "competitive" | "none"
    alpha: float = 0.15,
    gamma: float = 0.95,
    beta: float = 4e-6,
    window: int = 10_000,
    seed: int = 0,
) -> dict:
    n_states = state_space_size(n_prices, n_agents, memory)
    total_floats = n_states * n_prices * n_agents
    if total_floats > MAX_TOTAL_Q_FLOATS:
        raise ConfigTooLargeError(
            f"n_agents={n_agents}, n_prices={n_prices}, memory={memory} implies "
            f"{n_states:,} states -> {total_floats:,} total Q-table floats, "
            f"exceeding the {MAX_TOTAL_Q_FLOATS:,} cap."
        )

    rng = np.random.default_rng(seed)
    env = LogitBertrandEnv(n_agents=n_agents, n_prices=n_prices, memory=memory)

    agents = [
        QLearningAgent(n_actions=n_prices, state_space_size=n_states, alpha=alpha, gamma=gamma, beta=beta, seed=seed + i)
        for i in range(n_agents)
    ]

    n_total = n_steps_pre + n_steps_post
    profit_history = np.zeros((n_total, n_agents))
    price_history = np.zeros((n_total, n_agents))
    replaced_mask = np.zeros(n_agents, dtype=bool)

    state = env.reset(rng)
    state_idx = state_to_index(state, n_prices, n_agents)

    def step_loop(t_start, t_end):
        nonlocal state_idx
        for t in range(t_start, t_end):
            actions = tuple(agent.act(state_idx) for agent in agents)
            next_state, profits, info = env.step(actions)
            next_state_idx = state_to_index(next_state, n_prices, n_agents)
            for i, agent in enumerate(agents):
                agent.update(state_idx, actions[i], profits[i], next_state_idx)
            profit_history[t] = profits
            price_history[t] = info["prices"]
            state_idx = next_state_idx

    step_loop(0, n_steps_pre)

    pre_replacement_delta = env.collusion_index(profit_history[n_steps_pre - window:n_steps_pre].mean(axis=0))

    if replace_type == "none":
        replace_ids = []
    else:
        n_replace = round(replace_fraction * n_agents)
        replace_ids = list(rng.choice(n_agents, size=n_replace, replace=False)) if n_replace > 0 else []
        for i in replace_ids:
            replaced_mask[i] = True
            if replace_type == "naive":
                agents[i] = QLearningAgent(
                    n_actions=n_prices, state_space_size=n_states, alpha=alpha, gamma=gamma, beta=beta,
                    seed=seed + 1000 + i,
                )
            elif replace_type == "competitive":
                nash_idx = _nearest_price_index(env, env.p_nash)
                agents[i] = FixedIndexAgent(action_index=nash_idx)
            else:
                raise ValueError(f"unknown replace_type {replace_type!r}")

    step_loop(n_steps_pre, n_total)

    # Windowed post-replacement delta trajectory (to see recovery/collapse dynamics)
    n_windows = max(1, n_steps_post // window)
    post_deltas = []
    for w in range(n_windows):
        start = n_steps_pre + w * window
        end = start + window
        post_deltas.append(env.collusion_index(profit_history[start:end].mean(axis=0)))

    final_delta = env.collusion_index(profit_history[-window:].mean(axis=0))

    return {
        "pre_replacement_delta": pre_replacement_delta,
        "post_replacement_deltas": post_deltas,
        "final_delta": final_delta,
        "replaced_agent_ids": replace_ids,
        "replace_type": replace_type,
        "replace_fraction": replace_fraction,
        "n_agents": n_agents,
        "p_nash": env.p_nash,
        "p_monop": env.p_monop,
    }


if __name__ == "__main__":
    for rtype in ["none", "naive", "competitive"]:
        r = run_with_replacement(
            n_agents=2, n_prices=10, n_steps_pre=100_000, n_steps_post=60_000,
            window=10_000, replace_fraction=0.5, replace_type=rtype, seed=0,
        )
        print(f"\nreplace_type={rtype}")
        print(f"  pre-replacement delta:  {r['pre_replacement_delta']:.4f}")
        print(f"  post-replacement trajectory: {[f'{d:.3f}' for d in r['post_replacement_deltas']]}")
        print(f"  final delta: {r['final_delta']:.4f}")
