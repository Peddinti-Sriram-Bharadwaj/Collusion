import pandas as pd
import pytest

from src.sweep import (
    SweepConfig,
    run_sweep,
    variable_sweep_1d,
    summarize,
    estimate_run_memory_bytes,
    ResourceBudgetError,
    DEFAULT_MAX_WORKERS,
)

FAST = dict(n_prices=5, n_steps=1000, convergence_check_window=300)


def test_sweep_config_as_run_kwargs():
    cfg = SweepConfig(n_agents=3, **FAST)
    kwargs = cfg.as_run_kwargs(seed=7)
    assert kwargs["n_agents"] == 3
    assert kwargs["seed"] == 7
    assert "n_prices" in kwargs


def test_run_sweep_produces_one_row_per_config_seed():
    configs = [SweepConfig(n_agents=2, **FAST), SweepConfig(n_agents=3, **FAST)]
    df = run_sweep(configs, n_seeds=3, max_workers=2)
    assert len(df) == 2 * 3
    assert set(df["n_agents"].unique()) == {2, 3}
    assert "delta" in df.columns


def test_run_sweep_seeds_are_distinct_per_config():
    configs = [SweepConfig(n_agents=2, **FAST)]
    df = run_sweep(configs, n_seeds=4, seed_offset=10, max_workers=2)
    assert sorted(df["seed"].unique()) == [10, 11, 12, 13]


def test_variable_sweep_1d_varies_only_target_variable():
    base = SweepConfig(**FAST)
    df = variable_sweep_1d(base, "n_agents", [2, 3], n_seeds=2, max_workers=2)
    assert set(df["n_agents"]) == {2, 3}
    # every other field should equal the base config's value
    assert set(df["n_prices"]) == {base.n_prices}
    assert set(df["memory"]) == {base.memory}


def test_default_max_workers_leaves_headroom():
    """Should never plan to use all cores -- at least one left for the OS/user."""
    assert DEFAULT_MAX_WORKERS <= max(1, (__import__("os").cpu_count() or 4) - 1)
    assert DEFAULT_MAX_WORKERS >= 1


def test_estimate_run_memory_grows_with_state_space():
    small = SweepConfig(n_agents=2, n_prices=5, memory=1, n_steps=1000)
    large = SweepConfig(n_agents=4, n_prices=15, memory=1, n_steps=1000)
    assert estimate_run_memory_bytes(large) > estimate_run_memory_bytes(small)


def test_estimate_run_memory_nonzero_for_tiny_config():
    cfg = SweepConfig(n_agents=2, n_prices=3, memory=1, n_steps=10)
    assert estimate_run_memory_bytes(cfg) > 0


def test_run_sweep_refuses_when_planned_memory_exceeds_budget(monkeypatch):
    """Simulate a near-empty machine (tiny available RAM) and confirm run_sweep
    refuses to launch rather than risking a crash."""
    import src.sweep as sweep_mod

    class FakeMem:
        available = 100_000_000  # 100 MB "available"

    monkeypatch.setattr(sweep_mod.psutil, "virtual_memory", lambda: FakeMem())

    configs = [SweepConfig(n_agents=2, **FAST)]
    with pytest.raises(ResourceBudgetError):
        run_sweep(configs, n_seeds=1, max_workers=4)


def test_summarize_computes_mean_std_ci():
    df = pd.DataFrame(
        {
            "n_agents": [2, 2, 2, 3, 3, 3],
            "delta": [0.3, 0.32, 0.28, 0.2, 0.22, 0.18],
        }
    )
    summary = summarize(df, ["n_agents"])
    assert list(summary["n_agents"]) == [2, 3]
    assert summary.loc[summary["n_agents"] == 2, "mean"].iloc[0] == pytest.approx(0.3, abs=1e-6)
    assert summary.loc[summary["n_agents"] == 2, "count"].iloc[0] == 3
    assert (summary["ci95"] > 0).all()
