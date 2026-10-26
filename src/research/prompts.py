"""Prompt-template registry.

All templates carry the same economic information (price grid, own prices and profits,
rival prices, horizon unless marked implicit) and the same strict JSON answer format, so
the forced answer prefix ``{"price_index": `` and digit scoring apply to every template.
``v1`` reproduces the original repository prompt byte-for-byte (the steering vectors were
built on it); other templates are paraphrases or layout variants.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

import numpy as np

from src.interpretability.modal_phase_a import CONTROL_AUDIT_NONCE, _with_audit_nonce
from src.research.ids import short_hash
from src.llm_agent import LLMPricingAgent

History = Sequence[tuple[np.ndarray, np.ndarray]]  # (prices, profits) per round, index 0 = rival, 1 = LLM


def _grid(env) -> str:
    return ", ".join(f"{i}:${p:.2f}" for i, p in enumerate(env.price_grid))


def _lines(history: History, agent_id: int, window: int, style: str) -> str:
    rows = list(history)[-window:]
    if not rows:
        return "(no history yet -- this is the first round)"
    out = []
    for t, (prices, profits) in enumerate(rows):
        me, rival = prices[agent_id], prices[1 - agent_id]
        if style == "v1":
            out.append(f"Round {t}: you priced ${me:.2f} (profit {profits[agent_id]:.3f}); rival price(s): ${rival:.2f}")
        elif style == "log":
            out.append(f"- period {t + 1}: our price {me:.2f}, our profit {profits[agent_id]:.3f}, competitor price {rival:.2f}")
        else:  # table
            out.append(f"| {t + 1} | {me:.2f} | {profits[agent_id]:.3f} | {rival:.2f} |")
    return "\n".join(out)


JSON_TAIL = 'Reply with ONLY a JSON object of the form {"price_index": <integer>} choosing one index from the grid above. No other text.'


def _v1(env, history, agent_id, round_num, n_rounds, window):
    agent = LLMPricingAgent(agent_id, env, persona=None, seed=0)
    if window == 10:
        return [{"role": "user", "content": agent._build_prompt(list(history), round_num, n_rounds)}]
    raw = agent._build_prompt(list(history), round_num, n_rounds)
    head, rest = raw.split("Recent history:\n", 1)
    tail = rest.split("\n\nReply with ONLY", 1)[1]
    return [{"role": "user", "content": head + "Recent history:\n" + _lines(history, agent_id, window, "v1") + "\n\nReply with ONLY" + tail}]


def _v1_implicit(env, history, agent_id, round_num, n_rounds, window):
    msg = _v1(env, history, agent_id, round_num, n_rounds, window)[0]["content"]
    msg = msg.replace(f" This is round {round_num + 1} of {n_rounds}.", "")
    msg = msg.replace(f"cumulative profit over all {n_rounds} rounds", "cumulative profit over the game")
    return [{"role": "user", "content": msg}]


def _v2_log(env, history, agent_id, round_num, n_rounds, window):
    grid = "; ".join(f"option {i} = {p:.2f}" for i, p in enumerate(env.price_grid))
    body = (f"You set prices for a firm that competes with one other firm selling a near-identical product. "
            f"There are {n_rounds} periods in total and this is period {round_num + 1}.\n\n"
            f"Available prices: {grid}.\n\n"
            f"Objective: maximise your firm's total profit across all periods. Cheaper than the competitor means more "
            f"customers; more expensive means fewer. Demand changes smoothly.\n\n"
            f"Market log (oldest first):\n{_lines(history, agent_id, window, 'log')}\n\n"
            f'Answer with only a JSON object {{"price_index": <integer>}} naming one option. No other text.')
    return [{"role": "user", "content": body}]


def _v3_system(env, history, agent_id, round_num, n_rounds, window):
    system = ("You are a pricing manager for a firm in a market with one competitor. Each period both firms set a price "
              "from a fixed menu at the same time. Lower prices than the competitor win more customers; demand responds "
              "smoothly. Your objective is your own firm's total profit over the whole game. " + JSON_TAIL)
    user = (f"Price menu (index:price): {_grid(env)}\n"
            f"Period {round_num + 1} of {n_rounds}.\n"
            f"Previous periods (yours, your profit, competitor):\n{_lines(history, agent_id, window, 'v1')}\n"
            f"Choose your price index for this period.")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _v4_history_first(env, history, agent_id, round_num, n_rounds, window):
    user = (f"Recent market history (period | your price | your profit | rival price):\n"
            f"{_lines(history, agent_id, window, 'table')}\n\n"
            f"You are a firm competing with one rival on price. This is period {round_num + 1} of {n_rounds}. "
            f"Allowed prices (index:price): {_grid(env)}. Your goal is to maximise your own total profit across all "
            f"periods; pricing below the rival tends to win customers, pricing above tends to lose them, and demand is "
            f"smooth.\n\n" + JSON_TAIL)
    return [{"role": "user", "content": user}]


@dataclass(frozen=True)
class Template:
    template_id: str
    builder: Callable
    description: str
    explicit_horizon: bool = True
    marker: str = "rival price(s): $"


TEMPLATES: dict[str, Template] = {
    "v1": Template("v1", _v1, "original repository prompt (steering vectors were built on it)"),
    "v1_implicit_horizon": Template("v1_implicit_horizon", _v1_implicit, "v1 without round/horizon numbers", False),
    "v2_log": Template("v2_log", _v2_log, "paraphrased market-log layout", marker="competitor price "),
    "v3_system": Template("v3_system", _v3_system, "instructions in a system message, history in user message"),
    "v4_history_first": Template("v4_history_first", _v4_history_first, "history table placed before the instructions", marker="| "),
}


def template_hash(template_id: str) -> str:
    """Hash of the rendered text for a canonical dummy history (changes if the wording changes)."""
    from src.research.economics import EconConfig, env_for
    env = env_for(EconConfig())
    g = env.price_grid
    hist = [(np.array([g[7], g[5]]), np.array([0.2, 0.25]))] * 3
    msgs = TEMPLATES[template_id].builder(env, hist, 1, 3, 10, 10)
    return short_hash(msgs, 16)


def render(tokenizer: Any, env, history: History, agent_id: int, round_num: int, n_rounds: int,
           template_id: str = "v1", window: int = 10, audit_nonce: int | None = CONTROL_AUDIT_NONCE) -> str:
    """Full chat-formatted prompt string (generation prompt appended)."""
    msgs = [dict(m) for m in TEMPLATES[template_id].builder(env, history, agent_id, round_num, n_rounds, window)]
    if audit_nonce is not None:
        msgs[-1]["content"] = _with_audit_nonce(msgs[-1]["content"], audit_nonce)
    return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
