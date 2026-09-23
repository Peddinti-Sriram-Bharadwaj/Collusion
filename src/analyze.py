"""Variable-importance analysis over a multi-variable sweep (Track 1.1, stage 2)."""
from __future__ import annotations

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split


def variable_importance(df: pd.DataFrame, feature_cols: list[str], target_col: str = "delta") -> pd.DataFrame:
    """Fit a random forest on config -> delta and return permutation importances.

    Permutation importance (rather than raw impurity-based importance) is used
    because it's less biased toward high-cardinality features and directly
    measures the drop in predictive R^2 when a feature is shuffled -- a more
    honest proxy for "how much does this variable actually drive delta."
    """
    X = df[feature_cols]
    y = df[target_col]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)

    model = RandomForestRegressor(n_estimators=300, random_state=0, n_jobs=-1)
    model.fit(X_train, y_train)

    r2 = model.score(X_test, y_test)
    perm = permutation_importance(model, X_test, y_test, n_repeats=20, random_state=0, n_jobs=-1)

    result = pd.DataFrame(
        {
            "variable": feature_cols,
            "importance_mean": perm.importances_mean,
            "importance_std": perm.importances_std,
        }
    ).sort_values("importance_mean", ascending=False).reset_index(drop=True)
    result.attrs["holdout_r2"] = r2
    return result


def necessity_check(df: pd.DataFrame, variable: str, disabled_value, group_cols: list[str] | None = None, threshold: float = 0.1) -> pd.DataFrame:
    """For a candidate necessary variable, compare mean delta at the 'disabled'
    value vs. all other values (holding other config columns fixed via grouping).

    Returns a table with the delta at disabled_value, the delta otherwise, and
    a boolean `collapses` flag (delta at disabled_value < threshold), which is
    the operational definition of necessity used in the experimental plan.
    """
    group_cols = group_cols or [c for c in df.columns if c not in {variable, "seed", "delta", "avg_profit_mean", "p_nash", "p_monop"}]
    rows = []
    for keys, sub in df.groupby(group_cols) if group_cols else [((), df)]:
        disabled = sub[sub[variable] == disabled_value]["delta"]
        enabled = sub[sub[variable] != disabled_value]["delta"]
        if len(disabled) == 0 or len(enabled) == 0:
            continue
        row = dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,))) if group_cols else {}
        row["delta_disabled"] = disabled.mean()
        row["delta_enabled"] = enabled.mean()
        row["collapses"] = disabled.mean() < threshold
        rows.append(row)
    return pd.DataFrame(rows)
