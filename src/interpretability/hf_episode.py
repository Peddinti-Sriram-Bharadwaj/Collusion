"""Neutral Hugging Face episode runner with the existing market semantics."""
from __future__ import annotations

from typing import Any, Sequence
import json
from pathlib import Path

import numpy as np

from src.env import LogitBertrandEnv

from .activation_extractor import HFActivationExtractor
from .hf_pricing_adapter import HFPricingAgent


def run_hf_neutral_episode(
    extractor: HFActivationExtractor,
    *,
    n_agents: int = 2,
    n_prices: int = 10,
    n_rounds: int = 5,
    seed: int = 0,
    episode_id: str | None = None,
    selected_layers: Sequence[int] | None = None,
    generation_parameters: dict[str, Any] | None = None,
    quantization: str | None = None,
) -> dict[str, Any]:
    """Run a neutral stateless episode without changing existing LLM paths."""
    episode_id = episode_id or f"hf-neutral-{seed}"
    memory_before = extractor.memory_snapshot()
    env = LogitBertrandEnv(n_agents=n_agents, n_prices=n_prices)
    agents = [
        HFPricingAgent(i, env, extractor, persona=None, seed=seed + i,
                       selected_layers=selected_layers, generation_parameters=generation_parameters,
                       quantization=quantization)
        for i in range(n_agents)
    ]
    history: list[tuple] = []
    price_history = np.zeros((n_rounds, n_agents))
    profit_history = np.zeros((n_rounds, n_agents))
    decisions: list[dict[str, Any]] = []
    n_parse_failures = 0

    for round_num in range(n_rounds):
        round_decisions = [agent.act(history, round_num, n_rounds, episode_id=episode_id, market_seed=seed, generation_seed=seed + agent.agent_id) for agent in agents]
        actions = tuple(decision.action_index for decision in round_decisions)
        prices = env.price_grid[np.array(actions)]
        profits = env._profits(prices)
        for i, decision in enumerate(round_decisions):
            n_parse_failures += int(decision.parse_failed)
            entry = decision.activation_record or {
                "episode_id": episode_id, "agent_id": i, "round_id": round_num,
                "persona_id": None, "activation_status": "failed", "error": decision.error,
            }
            entry["activation_status"] = "captured" if decision.activation_record else "failed"
            entry.setdefault("parse_failed", True)
            entry.setdefault("eligible_for_analysis", False)
            entry.setdefault("decision_status", "generation_error")
            entry["executed_action_index"] = actions[i]
            entry["price"] = float(prices[i])
            entry["profit"] = float(profits[i])
            decisions.append(entry)
        history.append((prices, profits))
        price_history[round_num] = prices
        profit_history[round_num] = profits

    tail_window = max(1, n_rounds // 3)
    return {
        "schema_version": "hf-neutral-trajectory-v1",
        "episode_id": episode_id,
        "persona_configuration": [None] * n_agents,
        "delta": env.collusion_index(profit_history[-tail_window:].mean(axis=0)),
        "p_nash": env.p_nash,
        "p_monop": env.p_monop,
        "price_history": price_history,
        "profit_history": profit_history,
        "decisions": decisions,
        "n_parse_failures": n_parse_failures,
        "memory_before_bytes": memory_before,
        "memory_after_bytes": extractor.memory_snapshot(),
    }


def save_hf_trajectory(path: str | Path, trajectory: dict[str, Any]) -> None:
    """Write a local JSON trajectory, converting arrays but never staging it."""
    def default(value: Any):
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(f"Cannot serialize {type(value).__name__}")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(trajectory, default=default, indent=2), encoding="utf-8")
