"""Track 1.5: which single restriction removes the most collusion at the
least cost?

Baseline: the Track-1.1 reference collusive config (n_agents=2, n_prices=10,
memory=1, beta=4e-6). For each candidate restriction, measure:
  - delta_reduction  = Delta_baseline - Delta_restricted (collusion removed)
  - cs_gain          = CS_restricted - CS_baseline (consumer welfare gained;
                        positive = restriction helps consumers)
  - overshoot        = max(0, -Delta_restricted) (how far below Nash pricing
                        falls -- a "predatory pricing" style cost signal
                        distinct from ordinary welfare cost)
  - implementation_cost: qualitative tag (regulators can't cost most of
                          these numerically without real-market data; this
                          is a transparent, labeled judgment call, not a
                          computed figure)

Restrictions drawn from Track 1.1's causal ranking (n_agents, beta/exploration
dominate; memory, n_prices, alpha matter much less) and Track 1.2's finding
that a fixed competitive "regulator plant" collapses collusion cheaply:

  R1 structural:        n_agents 2 -> 4        (implementation_cost=high)
  R2 price-grid cap:     n_prices 10 -> 5        (implementation_cost=low)
  R3 exploration floor:  min_epsilon 0 -> 0.2    (implementation_cost=low)
  R4 heterogeneity mandate: per-agent alpha/beta forced apart (implementation_cost=low)
  R5 regulator plant (from Track 1.2): replace 1 of 2 agents with a fixed
     competitive agent at 70% of training (implementation_cost=moderate)

Usage: python -m src.track_1_5
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from src.run_baseline import run_episode
from src.replacement import run_with_replacement

RESULTS_DIR = "results"
# beta=2e-5 (not the 4e-6 default) so that natural exploration decays to
# ~0.135 by step 100k, letting the R3 exploration-floor restriction actually
# bind within this run length instead of being a no-op (validated in Track
# 1.1's 1D beta sweep as still producing supra-competitive pricing).
BASE = dict(n_agents=2, n_prices=10, memory=1, n_steps=100_000, convergence_check_window=15_000, beta=2e-5)
N_SEEDS = 10


def _aggregate(deltas: list[float], css: list[float]) -> tuple[float, float]:
    return float(np.mean(deltas)), float(np.mean(css))


def run_baseline_and_restrictions() -> pd.DataFrame:
    rows = []

    print("Running baseline...")
    deltas, css = [], []
    for s in range(N_SEEDS):
        r = run_episode(seed=s, **BASE)
        deltas.append(r["delta"])
        css.append(r["consumer_surplus"])
    delta_base, cs_base = _aggregate(deltas, css)
    rows.append(dict(restriction="baseline (none)", implementation_cost="n/a", delta=delta_base, cs=cs_base, n=N_SEEDS))
    print(f"  baseline delta={delta_base:.4f} cs={cs_base:.4f}")

    print("R1: structural (n_agents 2 -> 4)...")
    deltas, css = [], []
    for s in range(N_SEEDS):
        kwargs = dict(BASE)
        kwargs["n_agents"] = 4
        r = run_episode(seed=s, **kwargs)
        deltas.append(r["delta"])
        css.append(r["consumer_surplus"])
    d, c = _aggregate(deltas, css)
    rows.append(dict(restriction="R1 structural: n_agents=4", implementation_cost="high", delta=d, cs=c, n=N_SEEDS))
    print(f"  delta={d:.4f} cs={c:.4f}")

    print("R2: price-grid cap (n_prices 10 -> 5)...")
    deltas, css = [], []
    for s in range(N_SEEDS):
        kwargs = dict(BASE)
        kwargs["n_prices"] = 5
        r = run_episode(seed=s, **kwargs)
        deltas.append(r["delta"])
        css.append(r["consumer_surplus"])
    d, c = _aggregate(deltas, css)
    rows.append(dict(restriction="R2 price-grid cap: n_prices=5", implementation_cost="low", delta=d, cs=c, n=N_SEEDS))
    print(f"  delta={d:.4f} cs={c:.4f}")

    print("R3: exploration floor (min_epsilon=0.2)...")
    deltas, css = [], []
    for s in range(N_SEEDS):
        r = run_episode(min_epsilon=0.2, seed=s, **BASE)
        deltas.append(r["delta"])
        css.append(r["consumer_surplus"])
    d, c = _aggregate(deltas, css)
    rows.append(dict(restriction="R3 exploration floor: min_epsilon=0.2", implementation_cost="low", delta=d, cs=c, n=N_SEEDS))
    print(f"  delta={d:.4f} cs={c:.4f}")

    print("R4: heterogeneity mandate (forced alpha/beta apart)...")
    deltas, css = [], []
    for s in range(N_SEEDS):
        kwargs = dict(BASE)
        kwargs.pop("beta")
        r = run_episode(
            per_agent_alpha=[0.05, 0.5], per_agent_beta=[1e-6, 2e-5],
            seed=s, **kwargs,
        )
        deltas.append(r["delta"])
        css.append(r["consumer_surplus"])
    d, c = _aggregate(deltas, css)
    rows.append(dict(restriction="R4 heterogeneity mandate", implementation_cost="low", delta=d, cs=c, n=N_SEEDS))
    print(f"  delta={d:.4f} cs={c:.4f}")

    print("R5: regulator plant (1 of 2 replaced w/ fixed competitive agent at 70%)...")
    deltas = []
    p_nash_list = []
    for s in range(N_SEEDS):
        r = run_with_replacement(
            n_agents=2, n_prices=10, memory=1,
            n_steps_pre=70_000, n_steps_post=30_000, window=15_000,
            replace_fraction=0.5, replace_type="competitive", beta=BASE["beta"], seed=s,
        )
        deltas.append(r["final_delta"])
    d = float(np.mean(deltas))
    # CS for this restriction: approximate using the baseline env's CS formula
    # at the Nash price (the fixed agent's price) averaged with the surviving
    # learner's typical price is not directly available here; report delta
    # only and flag CS as not computed for this restriction to avoid a
    # spurious number -- final Track output documents this explicitly.
    rows.append(dict(restriction="R5 regulator plant: replace 1/2 @70% w/ fixed-Nash agent", implementation_cost="moderate", delta=d, cs=np.nan, n=N_SEEDS))
    print(f"  delta={d:.4f}")

    df = pd.DataFrame(rows)
    df["delta_reduction"] = delta_base - df["delta"]
    df["cs_gain"] = df["cs"] - cs_base
    df["overshoot"] = (-df["delta"]).clip(lower=0)
    return df


if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    df = run_baseline_and_restrictions()
    df.to_csv(f"{RESULTS_DIR}/track1_5_restrictions.csv", index=False)
    print("\n=== Track 1.5 summary ===")
    print(df.to_string(index=False))
