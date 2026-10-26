"""Behavioural metrics for the strategic-deviation protocol (definitions: research/protocols/strategic_deviation_v1.md).

Notation: E_t = model's expected price index at live round t (digit-distribution mean);
a_t = chosen action; t_d = deviation round (the agent first *observes* the deviation at t_d+1);
for a condition X matched to the stable control A (identical config except the rival script),
Delta_t = E^X_t - E^A_t. theta = 0.5 price-index steps is the response threshold.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

THETA = 0.5
K_WINDOW = 4


def traj(rounds: Sequence[dict], key: str = "expected_index") -> np.ndarray:
    return np.array([r[key] for r in rounds], float)


def pair_metrics(x_rounds, a_rounds, td: int, returns_at: int | None, theta: float = THETA, K: int = K_WINDOW) -> dict:
    Ex, Ea = traj(x_rounds), traj(a_rounds)
    d = Ex - Ea
    T = len(d)
    post = list(range(td + 1, min(T, td + 1 + K)))
    pre = list(range(max(0, td - 3), td + 1))
    out = {
        "pre_price": float(Ex[pre].mean()),
        "pre_gap": float(d[pre].mean()),                    # should be ~0 for scripts identical before t_d
        "immediate": float(d[td + 1]) if td + 1 < T else None,
        "peak": float(d[post].min()) if post else None,
        "peak_abs": float(np.abs(d[post]).max()) if post else None,
        "latency": next((k for k in range(1, K + 1) if td + k < T and d[td + k] <= -theta), None),
        "duration": int(sum(1 for t in range(td + 1, T) if d[t] <= -theta)),
        "post_mean": float(d[td + 1:].mean()) if td + 1 < T else None,
        "action_immediate": float(traj(x_rounds, "action")[td + 1] - traj(a_rounds, "action")[td + 1]) if td + 1 < T else None,
    }
    own_x = traj(x_rounds, "own_profit").sum(); own_a = traj(a_rounds, "own_profit").sum()
    riv_x = traj(x_rounds, "rival_profit").sum(); riv_a = traj(a_rounds, "rival_profit").sum()
    out.update(own_profit_diff=float(own_x - own_a), joint_profit_diff=float(own_x + riv_x - own_a - riv_a),
               rival_deviation_gain=float(riv_x - riv_a))
    if returns_at is not None and returns_at + 1 < T:
        w = list(range(returns_at + 1, min(T, returns_at + 4)))
        out["recovery_gap"] = float(d[w].mean())
        out["recovered"] = bool(abs(out["recovery_gap"]) < theta)
        out["recovery_time"] = next((j for j in range(1, T - returns_at) if abs(d[returns_at + j]) < theta), None)
    return out


def did(steer_x: float | None, steer_a: float | None, base_x: float | None, base_a: float | None) -> float | None:
    """(X - A | steered) - (X - A | unsteered); inputs already differences or levels."""
    if None in (steer_x, steer_a, base_x, base_a):
        return None
    return (steer_x - steer_a) - (base_x - base_a)
