"""Economic configurations and benchmarks computed from the actual payoff function.

Every configuration is a LogitBertrandEnv parameterisation. Benchmarks (Nash, monopoly,
one-shot best responses) are recomputed per configuration; collusion indices are only
comparable within a configuration unless explicitly normalised (they are normalised by
that configuration's own Nash and monopoly profits).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

import numpy as np

from src.env import LogitBertrandEnv

MAX_PRICES = 10  # digit scoring requires single-token price indices 0..9


@dataclass(frozen=True)
class EconConfig:
    econ_id: str = "base"
    a: float = 2.0
    a0: float = 0.0
    mu: float = 0.25
    c: float = 1.0
    n_prices: int = 10
    price_low_mult: float = 0.9
    price_high_mult: float = 1.1

    def validate(self) -> None:
        if not 2 <= self.n_prices <= MAX_PRICES:
            raise ValueError("n_prices must be 2..10 (single-digit actions)")
        if self.mu <= 0:
            raise ValueError("mu must be positive")

    def make_env(self) -> LogitBertrandEnv:
        self.validate()
        return LogitBertrandEnv(n_agents=2, n_prices=self.n_prices, a=self.a, a0=self.a0, mu=self.mu, c=self.c,
                                price_low_mult=self.price_low_mult, price_high_mult=self.price_high_mult)


ECON_PRESETS = {
    "base": EconConfig(),
    "low_mu": EconConfig(econ_id="low_mu", mu=0.15),      # more price-sensitive demand
    "high_mu": EconConfig(econ_id="high_mu", mu=0.40),    # less price-sensitive demand
    "high_cost": EconConfig(econ_id="high_cost", c=1.2, a=2.2),
    "grid8": EconConfig(econ_id="grid8", n_prices=8),
}


@lru_cache(maxsize=32)
def env_for(cfg: EconConfig) -> LogitBertrandEnv:
    """Cached environment instance (benchmark computation in the constructor is slow).
    Callers must not rely on its internal state; use step-free helpers or reset it."""
    return cfg.make_env()


@lru_cache(maxsize=32)
def _bench(cfg: EconConfig) -> dict:
    env = env_for(cfg)
    g = env.price_grid
    prof = lambda r, p: float(env._profits(np.array([g[r], g[p]]))[1])
    br = [int(np.argmax([prof(r, p) for p in range(len(g))])) for r in range(len(g))]
    nash_idx = int(np.argmin(abs(g - env.p_nash)))
    mono_idx = int(np.argmin(abs(g - env.p_monop)))
    # deviation incentive: best one-shot gain from undercutting a rival at the monopoly index
    dev_gain = max(prof(mono_idx, p) for p in range(len(g))) - prof(mono_idx, mono_idx)
    return {"econ": asdict(cfg), "grid": g.tolist(), "p_nash": env.p_nash, "p_monop": env.p_monop,
            "pi_nash": env.pi_nash, "pi_monop": env.pi_monop, "nash_index": nash_idx, "monopoly_index": mono_idx,
            "best_response_by_rival_index": br, "deviation_gain_vs_monopoly": dev_gain}


def benchmarks(cfg: EconConfig) -> dict:
    return _bench(cfg)


def profits(cfg: EconConfig, rival_idx: int, own_idx: int) -> tuple[float, float]:
    env = env_for(cfg)
    g = env.price_grid
    p = env._profits(np.array([g[rival_idx], g[own_idx]]))
    return float(p[0]), float(p[1])


def collusion_index(cfg: EconConfig, mean_profit: float) -> float:
    b = benchmarks(cfg)
    return (mean_profit - b["pi_nash"]) / (b["pi_monop"] - b["pi_nash"])
