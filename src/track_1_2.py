"""Track 1.2 sweep: robustness of collusion to participant replacement.

Runs run_with_replacement across (n_agents, replace_fraction, replace_type)
combinations x seeds, in parallel, using the same resource-budget guard as
Track 1.1's sweep harness.

Usage: python -m src.track_1_2
"""
from __future__ import annotations

import itertools
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
import psutil

from src.replacement import run_with_replacement
from src.sweep import _limit_worker_memory, DEFAULT_MAX_WORKERS, MAX_SAFE_MEMORY_FRACTION, ResourceBudgetError

RESULTS_DIR = "results"

BASE_KWARGS = dict(n_prices=10, memory=1, n_steps_pre=100_000, n_steps_post=60_000, window=10_000)


def _estimate_bytes(n_agents: int, n_prices: int, n_steps_pre: int, n_steps_post: int) -> int:
    from src.agents import state_space_size
    n_states = state_space_size(n_prices, n_agents, 1)
    q_bytes = n_states * n_prices * n_agents * 8
    hist_bytes = (n_steps_pre + n_steps_post) * n_agents * 2 * 8
    return q_bytes + hist_bytes + 50_000_000


def _run_one(kwargs: dict) -> dict:
    r = run_with_replacement(**kwargs)
    row = {
        "n_agents": kwargs["n_agents"],
        "replace_fraction": kwargs["replace_fraction"],
        "replace_type": kwargs["replace_type"],
        "seed": kwargs["seed"],
        "pre_replacement_delta": r["pre_replacement_delta"],
        "final_delta": r["final_delta"],
    }
    for i, d in enumerate(r["post_replacement_deltas"]):
        row[f"post_delta_w{i}"] = d
    return row


def run_track_1_2_sweep(n_seeds: int = 10, max_workers: int | None = None) -> pd.DataFrame:
    max_workers = max_workers or DEFAULT_MAX_WORKERS

    n_agents_list = [2, 3, 4]
    fractions = [0.0, 0.34, 0.5, 1.0]  # 0=no replacement control, up to full replacement
    types = ["naive", "competitive"]

    jobs = []
    for n_agents, frac, rtype, seed in itertools.product(n_agents_list, fractions, types, range(n_seeds)):
        if frac == 0.0 and rtype == "competitive":
            continue  # identical to naive-with-zero-replacement; skip duplicate
        kwargs = dict(BASE_KWARGS)
        kwargs.update(n_agents=n_agents, replace_fraction=frac, replace_type=rtype, seed=seed)
        jobs.append(kwargs)

    worst_case = max(_estimate_bytes(j["n_agents"], j["n_prices"], j["n_steps_pre"], j["n_steps_post"]) for j in jobs)
    available = psutil.virtual_memory().available
    planned_peak = worst_case * max_workers
    if planned_peak > available * MAX_SAFE_MEMORY_FRACTION:
        raise ResourceBudgetError(
            f"Refusing to launch: {max_workers} workers x worst-case {worst_case/1e9:.2f} GB "
            f"= {planned_peak/1e9:.2f} GB planned, exceeding {MAX_SAFE_MEMORY_FRACTION:.0%} of "
            f"{available/1e9:.2f} GB available."
        )

    rows = []
    with ProcessPoolExecutor(max_workers=max_workers, initializer=_limit_worker_memory) as ex:
        futures = [ex.submit(_run_one, kwargs) for kwargs in jobs]
        for fut in as_completed(futures):
            rows.append(fut.result())
    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    df = run_track_1_2_sweep(n_seeds=10)
    df.to_csv(f"{RESULTS_DIR}/track1_2_replacement_sweep.csv", index=False)

    summary = df.groupby(["n_agents", "replace_fraction", "replace_type"]).agg(
        pre_delta=("pre_replacement_delta", "mean"),
        final_delta=("final_delta", "mean"),
        n=("seed", "count"),
    ).reset_index()
    print(summary.to_string(index=False))
    summary.to_csv(f"{RESULTS_DIR}/track1_2_summary.csv", index=False)
