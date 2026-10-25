"""Rival behaviour: scripted strategic-deviation conditions (A-H) and reactive policies.

Scripted conditions are fixed action sequences, defined independently of the evaluated
agent, so matched conditions share every rival action before the manipulated round.
Reactive policies (tit-for-tat, undercut-by-one, adaptive, self-play) depend on the agent.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable

import numpy as np

from src.interpretability.phase_d import rival_action as legacy_rival_action

SCRIPTED = ("A_stable", "B_one_shot", "C_persistent", "D_gradual", "E_nash", "F_delayed", "G_raise")


@dataclass(frozen=True)
class DeviationDesign:
    """Parameters shared by all scripted conditions of one matched comparison."""
    rounds: int = 16          # live rounds played by the agent
    deviation_round: int = 7  # live round index t_d at which the rival deviates (agent observes it at t_d+1)
    high: int = 7             # cooperative rival price index (default: monopoly index of the economy)
    low: int = 2              # deviation price index (default: Nash index)
    raise_to: int = 9         # condition G target
    recovery_delay: int = 3   # condition F: rounds at `low` before returning to `high`

    def validate(self, n_prices: int) -> None:
        for v in (self.high, self.low, self.raise_to):
            if not 0 <= v < n_prices:
                raise ValueError("rival price index out of range")
        if not 1 <= self.deviation_round < self.rounds - 1:
            raise ValueError("deviation round must leave rounds before and after it")
        if self.low >= self.high:
            raise ValueError("low must be below high")


def scripted_sequence(condition: str, d: DeviationDesign) -> list[int]:
    T, td, H, L = d.rounds, d.deviation_round, d.high, d.low
    if condition == "A_stable":
        return [H] * T
    if condition == "B_one_shot":
        return [L if t == td else H for t in range(T)]
    if condition == "C_persistent":
        return [H if t < td else L for t in range(T)]
    if condition == "D_gradual":  # declines one step per round, reaching L exactly at t_d, then stays
        start = td - (H - L)
        return [H if t <= start else (max(L, H - (t - start)) if t <= td else L) for t in range(T)]
    if condition == "E_nash":
        return [L] * T
    if condition == "F_delayed":
        return [L if td <= t < td + d.recovery_delay else H for t in range(T)]
    if condition == "G_raise":
        return [d.raise_to if t == td else H for t in range(T)]
    raise ValueError(condition)


def returns_at(condition: str, d: DeviationDesign) -> int | None:
    """Live round at which the rival resumes `high` after deviating (None if never)."""
    return {"B_one_shot": d.deviation_round + 1, "F_delayed": d.deviation_round + d.recovery_delay,
            "G_raise": d.deviation_round + 1}.get(condition)


# ---- reactive policies (reuse the legacy implementations; add the missing ones) -------------
REACTIVE = ("fixed_monopoly", "fixed_nash", "tit_for_tat", "undercut_by_one", "one_shot_deviation",
            "rise_then_drop", "random", "llm_selfplay", "persistent_undercut", "gradual_decline", "adaptive_match")


def reactive_action(policy: str, t: int, joint: list[tuple[int, int]], rng: np.random.Generator,
                    n_prices: int, high: int = 7, low: int = 2) -> int | None:
    last_agent = joint[-1][1] if joint else None
    if policy in ("fixed_monopoly", "fixed_nash", "tit_for_tat", "undercut_by_one", "one_shot_deviation",
                  "rise_then_drop", "random", "llm_selfplay"):
        return legacy_rival_action(policy, t, joint, rng, n_prices)
    if policy == "persistent_undercut":
        return high if t < 6 else low
    if policy == "gradual_decline":
        return max(low, high - max(0, t - 3))
    if policy == "adaptive_match":  # moves halfway toward the agent's last price, starting high
        if last_agent is None:
            return high
        prev = joint[-1][0]
        return int(round((prev + last_agent) / 2))
    raise ValueError(policy)
