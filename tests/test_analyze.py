import numpy as np
import pandas as pd
import pytest

from src.analyze import variable_importance, necessity_check


def _synthetic_df(n=300, seed=0):
    """A synthetic config->delta dataset where `x1` linearly drives delta and
    `x2` is pure noise -- used to check that variable_importance ranks x1 above x2."""
    rng = np.random.default_rng(seed)
    x1 = rng.integers(0, 5, size=n)
    x2 = rng.integers(0, 5, size=n)  # irrelevant
    noise = rng.normal(0, 0.01, size=n)
    delta = 0.5 * x1 + noise
    return pd.DataFrame({"x1": x1, "x2": x2, "delta": delta})


def test_variable_importance_ranks_true_driver_first():
    df = _synthetic_df()
    result = variable_importance(df, feature_cols=["x1", "x2"])
    assert result.iloc[0]["variable"] == "x1"
    assert result.iloc[0]["importance_mean"] > result.iloc[1]["importance_mean"]


def test_variable_importance_reports_holdout_r2():
    df = _synthetic_df()
    result = variable_importance(df, feature_cols=["x1", "x2"])
    assert result.attrs["holdout_r2"] > 0.8  # near-deterministic synthetic signal


def test_necessity_check_flags_collapse():
    # variable "memory": memory=0 => delta collapses to ~0; memory=1 => delta high
    df = pd.DataFrame(
        {
            "n_agents": [2] * 6,
            "memory": [0, 0, 0, 1, 1, 1],
            "delta": [0.01, 0.02, 0.0, 0.3, 0.28, 0.32],
        }
    )
    result = necessity_check(df, variable="memory", disabled_value=0, group_cols=["n_agents"], threshold=0.1)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["delta_disabled"] < 0.1
    assert row["delta_enabled"] > 0.1
    assert row["collapses"] == True  # noqa: E712


def test_necessity_check_no_collapse_when_disabled_value_still_high():
    df = pd.DataFrame(
        {
            "n_agents": [2] * 4,
            "memory": [0, 0, 1, 1],
            "delta": [0.3, 0.29, 0.31, 0.28],
        }
    )
    result = necessity_check(df, variable="memory", disabled_value=0, group_cols=["n_agents"], threshold=0.1)
    assert result.iloc[0]["collapses"] == False  # noqa: E712
