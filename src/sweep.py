"""Track 1.1 sweep harness: run the pricing game across configs x seeds and
collect collusion-index outcomes for causal/variable-importance analysis.
"""
from __future__ import annotations

import itertools
import os
import resource
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field

import pandas as pd
import psutil

from src.run_baseline import run_episode
from src.agents import state_space_size

# --- Resource limits -------------------------------------------------------
# Defense in depth against the RAM-exhaustion crash: (1) cap each worker
# process's address space at the OS level, (2) cap parallelism so at most
# a bounded number of runs execute concurrently, (3) refuse to launch a
# sweep whose *estimated* peak memory would exceed a safe fraction of the
# machine's currently available RAM.
PER_WORKER_MEM_BYTES = 1_500_000_000  # 1.5 GB hard cap per worker process
MAX_SAFE_MEMORY_FRACTION = 0.5  # never plan to use more than 50% of available RAM
DEFAULT_MAX_WORKERS = max(1, min(4, (os.cpu_count() or 4) - 1))


def _limit_worker_memory():
    """Runs once in each worker process (ProcessPoolExecutor initializer)."""
    try:
        resource.setrlimit(resource.RLIMIT_AS, (PER_WORKER_MEM_BYTES, PER_WORKER_MEM_BYTES))
    except (ValueError, OSError):
        # Some platforms (notably macOS) don't fully enforce RLIMIT_AS; the
        # Q-float cap in run_episode is the primary guard in that case.
        pass


def estimate_run_memory_bytes(config: "SweepConfig") -> int:
    """Rough upper bound on one run's resident memory: Q-tables (8 bytes/float)
    plus profit/price history arrays, with a fixed overhead allowance."""
    n_states = state_space_size(config.n_prices, config.n_agents, config.memory)
    q_table_bytes = n_states * config.n_prices * config.n_agents * 8
    history_bytes = config.n_steps * config.n_agents * 2 * 8  # profit + price history
    overhead = 50_000_000  # interpreter + numpy/pandas import overhead per process
    return q_table_bytes + history_bytes + overhead


class ResourceBudgetError(RuntimeError):
    pass


@dataclass(frozen=True)
class SweepConfig:
    n_agents: int = 2
    n_prices: int = 15
    memory: int = 1
    n_steps: int = 200_000
    convergence_check_window: int = 20_000
    alpha: float = 0.15
    gamma: float = 0.95
    beta: float = 4e-6

    def as_run_kwargs(self, seed: int) -> dict:
        d = asdict(self)
        d["seed"] = seed
        return d


def _run_one(config: SweepConfig, seed: int) -> dict:
    kwargs = config.as_run_kwargs(seed)
    result = run_episode(**kwargs)
    row = asdict(config)
    row["seed"] = seed
    row["delta"] = result["delta"]
    row["avg_profit_mean"] = sum(result["avg_profit"]) / len(result["avg_profit"])
    row["p_nash"] = result["p_nash"]
    row["p_monop"] = result["p_monop"]
    return row


def run_sweep(
    configs: list[SweepConfig],
    n_seeds: int = 20,
    seed_offset: int = 0,
    max_workers: int | None = None,
) -> pd.DataFrame:
    """Run every config across n_seeds seeds, in parallel across processes.

    Before launching, checks that max_workers concurrent runs of the largest
    config would fit within MAX_SAFE_MEMORY_FRACTION of currently available
    RAM, and caps max_workers to DEFAULT_MAX_WORKERS unless the caller
    explicitly overrides it.
    """
    max_workers = max_workers or DEFAULT_MAX_WORKERS

    worst_case_bytes = max(estimate_run_memory_bytes(cfg) for cfg in configs)
    available = psutil.virtual_memory().available
    planned_peak = worst_case_bytes * max_workers
    if planned_peak > available * MAX_SAFE_MEMORY_FRACTION:
        raise ResourceBudgetError(
            f"Refusing to launch: {max_workers} workers x worst-case "
            f"{worst_case_bytes / 1e9:.2f} GB/run = {planned_peak / 1e9:.2f} GB planned, "
            f"exceeding {MAX_SAFE_MEMORY_FRACTION:.0%} of the "
            f"{available / 1e9:.2f} GB currently available. "
            f"Reduce max_workers, n_steps, n_prices, n_agents, or memory."
        )

    jobs = list(itertools.product(configs, range(seed_offset, seed_offset + n_seeds)))
    rows = []
    with ProcessPoolExecutor(max_workers=max_workers, initializer=_limit_worker_memory) as ex:
        futures = {ex.submit(_run_one, cfg, seed): (cfg, seed) for cfg, seed in jobs}
        for fut in as_completed(futures):
            rows.append(fut.result())
    df = pd.DataFrame(rows)
    return df


def variable_sweep_1d(
    base: SweepConfig,
    variable: str,
    values: list,
    n_seeds: int = 20,
    **run_sweep_kwargs,
) -> pd.DataFrame:
    """One-variable-at-a-time sweep: vary `variable` over `values`, hold rest at base."""
    configs = []
    for v in values:
        d = asdict(base)
        d[variable] = v
        configs.append(SweepConfig(**d))
    df = run_sweep(configs, n_seeds=n_seeds, **run_sweep_kwargs)
    return df


def summarize(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Aggregate delta across seeds: mean, std, 95% CI half-width, n."""
    g = df.groupby(group_cols)["delta"]
    summary = g.agg(["mean", "std", "count"]).reset_index()
    summary["ci95"] = 1.96 * summary["std"] / summary["count"] ** 0.5
    return summary.sort_values(group_cols)


if __name__ == "__main__":
    base = SweepConfig(n_prices=8, n_steps=50_000, convergence_check_window=10_000)
    df = variable_sweep_1d(base, "n_agents", [2, 3, 4], n_seeds=5)
    print(summarize(df, ["n_agents"]))
    df.to_csv("results/smoke_sweep_n_agents.csv", index=False)
