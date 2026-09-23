"""Track 1.1: Which variables are necessary for collusion to emerge?

Stage 1: one-variable-at-a-time sweeps (cheap, gives marginal effects + CIs).
Stage 2: random multi-variable sample -> random-forest permutation importance
         (ranks variables, captures that marginal sweeps might miss interactions).
Stage 3: necessity check on the top-ranked variables (does delta collapse to
         ~Nash when the variable is fixed at its "disabled" extreme?).

Usage: python -m src.track_1_1
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.sweep import SweepConfig, run_sweep, variable_sweep_1d, summarize
from src.analyze import variable_importance, necessity_check
from src.agents import state_space_size

# Hard cap on Q-table size (states x actions x agents) to avoid memory blowups.
# state_space_size grows as n_prices**(n_agents*memory), which explodes fast:
# e.g. n_agents=6, n_prices=20, memory=1 -> 64,000,000 states x 20 actions x 8
# bytes x 6 agents ~= 60+ GB RAM. Cap total floats across all agents' Q-tables.
MAX_TOTAL_Q_FLOATS = 2_000_000  # ~16MB per agent table at float64, times n_agents

RESULTS_DIR = "results"

# Base config: moderate scale, fast enough for a full sweep but long enough
# to reach convergence (validated against the Calvano baseline in run_baseline.py).
BASE = SweepConfig(n_agents=2, n_prices=10, memory=1, n_steps=100_000, convergence_check_window=15_000)

N_SEEDS_1D = 10


def stage1_marginal_sweeps():
    print("=== Stage 1: one-variable-at-a-time sweeps ===")
    sweeps = {
        "n_agents": [2, 3, 4, 5, 6],
        "memory": [1, 2],
        "n_prices": [5, 10, 15, 20],
        "beta": [1e-6, 4e-6, 2e-5, 1e-4],  # exploration decay: lower = slower decay = more exploration
        "alpha": [0.05, 0.15, 0.3, 0.5],   # learning rate
    }
    all_results = {}
    for var, values in sweeps.items():
        print(f"-- sweeping {var} over {values}")
        df = variable_sweep_1d(BASE, var, values, n_seeds=N_SEEDS_1D, max_workers=8)
        df.to_csv(f"{RESULTS_DIR}/track1_1_1d_{var}.csv", index=False)
        summary = summarize(df, [var])
        print(summary.to_string(index=False))
        all_results[var] = summary
    return all_results


def stage2_random_multiway_sample(n_samples: int = 150, n_seeds: int = 5, seed: int = 0):
    print("\n=== Stage 2: random multi-variable sample + importance ranking ===")
    rng = np.random.default_rng(seed)
    domains = {
        "n_agents": [2, 3, 4, 5, 6],
        "memory": [1, 2],
        "n_prices": [5, 10, 15, 20],
        "beta": [1e-6, 4e-6, 2e-5, 1e-4],
        "alpha": [0.05, 0.15, 0.3, 0.5],
    }
    def q_table_floats(n_agents: int, n_prices: int, memory: int) -> int:
        return state_space_size(n_prices, n_agents, memory) * n_prices * n_agents

    configs = []
    attempts = 0
    max_attempts = n_samples * 50
    while len(configs) < n_samples and attempts < max_attempts:
        attempts += 1
        kwargs = {k: rng.choice(v).item() if not isinstance(v[0], int) else int(rng.choice(v)) for k, v in domains.items()}
        if q_table_floats(kwargs["n_agents"], kwargs["n_prices"], kwargs["memory"]) > MAX_TOTAL_Q_FLOATS:
            continue  # reject configs whose Q-tables would blow up memory
        kwargs["n_steps"] = BASE.n_steps
        kwargs["convergence_check_window"] = BASE.convergence_check_window
        configs.append(SweepConfig(**kwargs))
    if len(configs) < n_samples:
        print(f"WARNING: only found {len(configs)}/{n_samples} configs under the memory cap after {attempts} attempts")

    df = run_sweep(configs, n_seeds=n_seeds, max_workers=8)
    df.to_csv(f"{RESULTS_DIR}/track1_1_random_sample.csv", index=False)

    feature_cols = list(domains.keys())
    importance = variable_importance(df, feature_cols)
    print(f"Holdout R^2 of random-forest surrogate: {importance.attrs['holdout_r2']:.3f}")
    print(importance.to_string(index=False))
    importance.to_csv(f"{RESULTS_DIR}/track1_1_variable_importance.csv", index=False)
    return df, importance


def stage3_necessity_checks(df: pd.DataFrame):
    print("\n=== Stage 3: necessity checks (delta collapse under ablation) ===")
    checks = {
        "memory": 0 if 0 in df["memory"].unique() else None,  # memory>=1 always in our design; see note below
        "n_agents": None,
    }
    # For memory we didn't sample memory=0 (no state at all = fully myopic/no
    # coordination signal) in stage 2, so run a small targeted ablation instead.
    ablation_cfgs = [
        SweepConfig(n_agents=2, n_prices=10, memory=1, n_steps=BASE.n_steps,
                    convergence_check_window=BASE.convergence_check_window, beta=1.0),  # beta huge => near-zero exploration decay time => almost no learning signal variety
    ]
    print("(memory=0 is not representable in this env -- min memory is 1 round of history;")
    print(" treating 'beta very high' (agents stop exploring almost immediately) as the ")
    print(" closest ablation of the coordination-relevant learning process.)")
    df_ablation = run_sweep(ablation_cfgs, n_seeds=N_SEEDS_1D, max_workers=8)
    print(f"Mean delta with near-zero exploration time (beta=1.0): {df_ablation['delta'].mean():.4f}")
    df_ablation.to_csv(f"{RESULTS_DIR}/track1_1_beta_ablation.csv", index=False)


if __name__ == "__main__":
    import os
    os.makedirs(RESULTS_DIR, exist_ok=True)
    stage1_marginal_sweeps()
    df, importance = stage2_random_multiway_sample()
    stage3_necessity_checks(df)
