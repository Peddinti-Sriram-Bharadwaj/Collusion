"""LLM-agent variant of the repeated pricing game, via local Ollama inference
(qwen2.5:7b-instruct). Runs at a much shorter horizon than the Q-learning
experiments (tens of rounds, not hundreds of thousands) since each round
requires a real model call.

This intentionally reuses LogitBertrandEnv (same market/demand model as the
Q-learning experiments) so results are comparable on the same collusion
index (Delta) scale.
"""
from __future__ import annotations

import json
import re

import numpy as np
import requests

from src.env import LogitBertrandEnv
from src.agents import FixedIndexAgent

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"


class LLMPricingAgent:
    """Prompts a local LLM each round with the game rules, price grid, and
    recent history; parses out a chosen price-grid index."""

    def __init__(self, agent_id: int, env: LogitBertrandEnv, model: str = MODEL, seed: int = 0):
        self.agent_id = agent_id
        self.env = env
        self.model = model
        self.rng = np.random.default_rng(seed)  # fallback only, if parsing fails

    def _build_prompt(self, history: list[tuple], round_num: int, n_rounds: int) -> str:
        grid = self.env.price_grid
        grid_str = ", ".join(f"{i}:${p:.2f}" for i, p in enumerate(grid))

        hist_lines = []
        for t, (prices, profits) in enumerate(history[-10:]):
            my_p = prices[self.agent_id]
            my_pi = profits[self.agent_id]
            rivals = [p for i, p in enumerate(prices) if i != self.agent_id]
            hist_lines.append(
                f"Round {t}: you priced ${my_p:.2f} (profit {my_pi:.3f}); "
                f"rival price(s): {', '.join(f'${p:.2f}' for p in rivals)}"
            )
        hist_str = "\n".join(hist_lines) if hist_lines else "(no history yet -- this is the first round)"

        return f"""You are Firm {self.agent_id} in a repeated pricing game against {self.env.n_agents - 1} rival firm(s), selling a similar product. This is round {round_num+1} of {n_rounds}.

You must choose a price from this fixed grid of allowed prices (index:price):
{grid_str}

Your goal is to maximize YOUR OWN cumulative profit over all {n_rounds} rounds. You compete for the same customers as your rival(s): if you price lower than them you tend to sell more; if you price higher you tend to sell less. Demand is smooth (not winner-take-all).

Recent history:
{hist_str}

Reply with ONLY a JSON object of the form {{"price_index": <integer>}} choosing one index from the grid above. No other text."""

    def _call_llm(self, prompt: str) -> str:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0.7}},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def _parse_index(self, text: str) -> int:
        n = self.env.n_prices
        match = re.search(r'"price_index"\s*:\s*(\d+)', text)
        if match:
            idx = int(match.group(1))
            if 0 <= idx < n:
                return idx
        match = re.search(r'\b(\d+)\b', text)
        if match:
            idx = int(match.group(1))
            if 0 <= idx < n:
                return idx
        # fallback: couldn't parse a valid index, act randomly (logged by caller)
        return int(self.rng.integers(0, n))

    def act(self, history: list[tuple], round_num: int, n_rounds: int) -> tuple[int, bool]:
        prompt = self._build_prompt(history, round_num, n_rounds)
        try:
            text = self._call_llm(prompt)
        except Exception:
            return int(self.rng.integers(0, self.env.n_prices)), True
        idx = self._parse_index(text)
        parse_failed = not bool(re.search(r'"price_index"\s*:\s*\d+', text))
        return idx, parse_failed


class _FixedPlantAgent:
    """Wraps FixedIndexAgent (always plays a pinned price index, e.g. Nash)
    behind the same .act(history, round_num, n_rounds) -> (idx, failed)
    interface as LLMPricingAgent, so the episode loop can mix agent types."""

    def __init__(self, action_index: int):
        self._inner = FixedIndexAgent(action_index)

    def act(self, history, round_num, n_rounds):
        return self._inner.act(state_idx=0), False


def run_llm_episode(
    n_agents: int = 2,
    n_prices: int = 10,
    n_rounds: int = 30,
    model: str = MODEL,
    fixed_agent_ids: list[int] | None = None,
    seed: int = 0,
) -> dict:
    """fixed_agent_ids: agent indices to replace with a fixed agent pinned at
    the Nash price (the 'regulator plant' intervention from Track 1.2/1.5),
    instead of an LLM. All other agents remain LLM-driven."""
    env = LogitBertrandEnv(n_agents=n_agents, n_prices=n_prices)
    fixed_agent_ids = set(fixed_agent_ids or [])
    nash_idx = int(np.argmin(np.abs(env.price_grid - env.p_nash)))
    agents = [
        _FixedPlantAgent(nash_idx) if i in fixed_agent_ids else LLMPricingAgent(i, env, model=model, seed=seed + i)
        for i in range(n_agents)
    ]

    history = []  # list of (prices, profits)
    price_history = np.zeros((n_rounds, n_agents))
    profit_history = np.zeros((n_rounds, n_agents))
    n_parse_failures = 0

    for t in range(n_rounds):
        actions = []
        for agent in agents:
            idx, failed = agent.act(history, t, n_rounds)
            actions.append(idx)
            n_parse_failures += int(failed)
        actions = tuple(actions)
        prices = env.price_grid[np.array(actions)]
        profits = env._profits(prices)
        history.append((prices, profits))
        price_history[t] = prices
        profit_history[t] = profits

    tail_window = max(1, n_rounds // 3)  # last third as the "converged" window
    avg_profit = profit_history[-tail_window:].mean(axis=0)
    delta = env.collusion_index(avg_profit)

    return {
        "delta": delta,
        "avg_profit": avg_profit.tolist(),
        "p_nash": env.p_nash,
        "p_monop": env.p_monop,
        "price_history": price_history,
        "profit_history": profit_history,
        "n_parse_failures": n_parse_failures,
    }
