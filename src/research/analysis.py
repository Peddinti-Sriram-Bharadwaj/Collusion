"""Registry -> analysis tables (the only input to figures and the report).

Tables (research/outputs/tables/):
  units.csv          one row per completed run unit (flattened config + summary + validity)
  pairs.csv          deviation-game condition X vs matched stable control A (pair metrics)
  did.csv            steering x deviation interactions (steered pair minus unsteered pair)
  steer_level.csv    steering price-level effects (steered vs unsteered, same rival script)
  fixed_history.csv  matched absolute-price contrasts (condition H)
  behaviour_cells.csv / behaviour_grid.json   behavioural consistency grid
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.research import metrics as M, stats as S
from src.research.ids import short_hash
from src.research.registry import Registry
from src.research.rivals import DeviationDesign, returns_at

PROTOCOL = "strategic_deviation_v1"
FACTOR_COLUMNS = {
    "template_id": "template_id", "temperature": "temperature", "decoding_mode": "decoding_mode",
    "deviation_magnitude": "deviation_magnitude", "prefix_rounds": "prefix_rounds", "recovery_delay": "recovery_delay",
    "alpha": "alpha", "steer_layer": "steer_layer", "steer_site": "steer_site", "econ_id": "econ_id", "model": "model",
    "history_seed": "history_seed", "deviation_round": "deviation_round", "window": "window",
}


def _flatten(rec: dict) -> dict:
    c = rec["config"]; s = c["steering"]; dz = c["design"]; v = rec.get("validity", {})
    row = {"run_id": rec["run_id"], "batch_id": rec["batch_id"], "designation": rec["designation"], "block": c.get("block"),
           "experiment": c["experiment"], "condition": c["condition"], "model": c["model"], "template_id": c["template_id"],
           "econ_id": c["econ_id"], "window": c["window"], "prefix_rounds": c["prefix_rounds"],
           "decoding_mode": c["decoding"]["mode"], "temperature": c["decoding"]["temperature"] if c["decoding"]["mode"] == "sample" else 0.0,
           "top_p": c["decoding"]["top_p"], "top_k": c["decoding"]["top_k"],
           "steer_kind": s["kind"], "vector_id": s.get("vector_id"), "alpha": s["alpha"], "steer_layer": s["layer"],
           "steer_site": s["site"], "steer_timing": s["timing"], "random_seed": s.get("random_seed", 0),
           "rounds": dz["rounds"], "deviation_round": dz["deviation_round"], "high": dz["high"], "low": dz["low"],
           "deviation_magnitude": dz["high"] - dz["low"], "recovery_delay": dz["recovery_delay"], "raise_to": dz["raise_to"],
           "replicate": c.get("replicate", 0), **{f"seed_{k}": val for k, val in c["seeds"].items()},
           "history_seed": c["seeds"]["history_seed"], "raw_path": rec.get("raw_path"),
           # independent unit = distinct pre-play history (seed + prefix length + own-price range + economics)
           "history_cluster": f"{c['econ_id']}|p{c['prefix_rounds']}|{c['prefix_own_range'][0]}-{c['prefix_own_range'][1]}|s{c['seeds']['history_seed']}",
           "fixed_history_own": c.get("fixed_history_own", "constant"),
           "model_revision": (rec.get("model") or {}).get("revision"),
           "git_commit": (rec.get("git") or {}).get("commit"),
           "n_decisions": v.get("n_decisions"), "free_audits": v.get("free_audits"), "free_valid": v.get("free_valid"),
           "free_agree": v.get("free_agree"), "prefixed_audits": v.get("prefixed_audits"),
           "prefixed_valid": v.get("prefixed_valid"), "prefixed_agree": v.get("prefixed_agree"),
           "min_digit_mass": v.get("min_digit_mass"), "runtime_seconds": rec.get("runtime_seconds")}
    for k, val in (rec.get("summary") or {}).items():
        row[f"sum_{k}"] = val
    return row


def steering_label(r) -> str:
    if r["steer_kind"] == "none":
        return "none"
    if r["steer_kind"] == "random":
        return f"random{int(r['random_seed'])}"
    return f"{r['steer_kind']}:{r['vector_id']}" if r["steer_kind"] != "sham" else "sham"


def match_key(c: dict, drop=("condition", "unit_id", "block")) -> str:
    return short_hash({k: v for k, v in c.items() if k not in drop}, 16)


def build_tables(reg: Registry, out_dir: Path, protocol: str = PROTOCOL) -> dict[str, pd.DataFrame]:
    recs = [r for r in reg.records() if r.get("protocol_version") == protocol]
    done = [r for r in recs if r["status"] == "completed"]
    units = pd.DataFrame([_flatten(r) for r in done])
    tables = {"units": units}
    if units.empty:
        return tables
    units["steering"] = units.apply(steering_label, axis=1)
    from src.research.economics import ECON_PRESETS, benchmarks
    nash = {e: benchmarks(ECON_PRESETS[e])["nash_index"] for e in units["econ_id"].unique() if e in ECON_PRESETS}
    if "sum_mean_action" in units:
        units["price_above_nash"] = units["sum_mean_action"] - units["econ_id"].map(nash)
    by_id = {r["run_id"]: r for r in done}
    raw_cache: dict[str, list] = {}

    def rounds_of(rid):
        if rid not in raw_cache:
            raw_cache[rid] = reg.read_raw(by_id[rid]["raw_path"])["rounds"]
        return raw_cache[rid]

    # ---- deviation pairs -------------------------------------------------------------------
    dev = [r for r in done if r["config"]["experiment"] == "deviation_game"]
    ctrl = {match_key(r["config"]): r for r in dev if r["config"]["condition"] == "A_stable"}
    pair_rows = []
    for r in dev:
        c = r["config"]
        if c["condition"] == "A_stable":
            continue
        a = ctrl.get(match_key(c))
        if a is None:
            continue
        d = DeviationDesign(**c["design"])
        m = M.pair_metrics(rounds_of(r["run_id"]), rounds_of(a["run_id"]), d.deviation_round, returns_at(c["condition"], d))
        pair_rows.append({"run_id": r["run_id"], "control_run_id": a["run_id"], "pair_key": match_key(c), **m})
    pairs = pd.DataFrame(pair_rows)
    # long-form per-round trajectories (games) and per-round matched differences (pairs)
    tr_rows = []
    for r in done:
        if r["config"]["experiment"] == "fixed_history":
            continue
        for x in rounds_of(r["run_id"]):
            tr_rows.append({"run_id": r["run_id"], "t": x["t"], "E": x["expected_index"], "action": x["action"],
                            "rival": x["rival_action"], "own_profit": x["own_profit"], "rival_profit": x["rival_profit"],
                            "br": x["best_response_to_last_rival"]})
    tables["trajectories"] = pd.DataFrame(tr_rows).merge(units, on="run_id", how="left") if tr_rows else pd.DataFrame()
    pt_rows = []
    for pr in pair_rows:
        X, A = rounds_of(pr["run_id"]), rounds_of(pr["control_run_id"])
        for x, a in zip(X, A):
            pt_rows.append({"run_id": pr["run_id"], "t": x["t"], "delta": x["expected_index"] - a["expected_index"]})
    tables["pair_traj"] = pd.DataFrame(pt_rows).merge(units, on="run_id", how="left") if pt_rows else pd.DataFrame()
    if not pairs.empty:
        pairs = pairs.merge(units, on="run_id", how="left")
    tables["pairs"] = pairs

    # ---- steering x deviation interaction (DiD) -------------------------------------------------
    did_rows = []
    if not pairs.empty:
        def nosteer_key(row):
            c = by_id[row["run_id"]]["config"]
            from src.research.configs import DEFAULT_UNIT
            c2 = {**c, "steering": dict(DEFAULT_UNIT["steering"])}
            return match_key(c2)
        base = {}
        for _, row in pairs[pairs.steer_kind == "none"].iterrows():
            base[(row["condition"], row["pair_key"])] = row
        for _, row in pairs[pairs.steer_kind != "none"].iterrows():
            b = base.get((row["condition"], nosteer_key(row)))
            if b is None:
                continue
            out = {"run_id": row["run_id"], "base_run_id": b["run_id"]}
            for mname in ("immediate", "peak", "post_mean", "recovery_gap", "own_profit_diff", "duration"):
                x, y = row.get(mname), b.get(mname)
                out[f"did_{mname}"] = None if (x is None or y is None or pd.isna(x) or pd.isna(y)) else float(x - y)
            did_rows.append(out)
    did = pd.DataFrame(did_rows)
    if not did.empty:
        did = did.merge(units, on="run_id", how="left")
    tables["did"] = did

    # ---- steering price-level effect (same script, steered - unsteered) ----------------------------
    lvl_rows = []
    games = units[units.experiment.isin(["deviation_game", "reactive_game"])]
    base_lvl = {}
    for r in dev + [x for x in done if x["config"]["experiment"] == "reactive_game"]:
        if r["config"]["steering"]["kind"] == "none":
            base_lvl[match_key(r["config"], drop=("unit_id", "block", "steering"))] = r
    for r in dev + [x for x in done if x["config"]["experiment"] == "reactive_game"]:
        if r["config"]["steering"]["kind"] == "none":
            continue
        b = base_lvl.get(match_key(r["config"], drop=("unit_id", "block", "steering")))
        if b is None:
            continue
        Ex, Eb = M.traj(rounds_of(r["run_id"])), M.traj(rounds_of(b["run_id"]))
        lvl_rows.append({"run_id": r["run_id"], "base_run_id": b["run_id"], "level_shift": float((Ex - Eb).mean()),
                         "level_shift_pre": float((Ex - Eb)[: r["config"]["design"]["deviation_round"] + 1].mean()),
                         "profit_shift": float(r["summary"]["own_cum_profit"] - b["summary"]["own_cum_profit"]),
                         "ci_shift": float(r["summary"]["collusion_index_joint"] - b["summary"]["collusion_index_joint"])})
    lvl = pd.DataFrame(lvl_rows)
    if not lvl.empty:
        lvl = lvl.merge(units, on="run_id", how="left")
    tables["steer_level"] = lvl

    # ---- steering specificity: learned minus mean of random directions, same config / alpha / history ----------
    spec_rows = []
    if not lvl.empty:
        key = lambda r: (r["batch_id"], r["condition"], r["history_cluster"], r["alpha"], r["steer_timing"], r["template_id"],
                         r["temperature"], r["econ_id"], r["seed_model_seed"], r["rounds"], r["low"], r["prefix_rounds"])
        rnd = {}
        for _, r in lvl[lvl.steer_kind == "random"].iterrows():
            rnd.setdefault(key(r), []).append(r["level_shift"])
        gen = {key(r): r["level_shift"] for _, r in lvl[lvl.steer_kind == "generic_price"].iterrows()}
        for _, r in lvl[lvl.steer_kind == "learned"].iterrows():
            k = key(r)
            if k in rnd:
                spec_rows.append({"run_id": r["run_id"], "learned_level": r["level_shift"], "random_level_mean": float(np.mean(rnd[k])),
                                  "n_random": len(rnd[k]), "specificity": float(r["level_shift"] - np.mean(rnd[k])),
                                  "learned_minus_generic": float(r["level_shift"] - gen[k]) if k in gen else None})
    spec = pd.DataFrame(spec_rows)
    if not spec.empty:
        spec = spec.merge(units, on="run_id", how="left")
    tables["specificity"] = spec

    # ---- repeatability: replicate reruns vs their originals ------------------------------------------------
    rep_rows = []
    for r in done:
        if r["config"].get("replicate", 0) == 0:
            continue
        c0 = {**r["config"], "replicate": 0}
        orig = next((x for x in done if x["batch_id"] == r["batch_id"] and match_key(x["config"], drop=("unit_id", "block")) ==
                     match_key(c0, drop=("unit_id", "block"))), None)
        if orig is None:
            continue
        a, b = M.traj(rounds_of(r["run_id"])), M.traj(rounds_of(orig["run_id"]))
        acts_eq = bool((M.traj(rounds_of(r["run_id"]), "action") == M.traj(rounds_of(orig["run_id"]), "action")).all())
        rep_rows.append({"run_id": r["run_id"], "original_run_id": orig["run_id"], "max_abs_dE": float(np.abs(a - b).max()),
                         "actions_identical": acts_eq})
    rep = pd.DataFrame(rep_rows)
    if not rep.empty:
        rep = rep.merge(units, on="run_id", how="left")
    tables["repeatability"] = rep

    # ---- fixed-history matched absolute-price contrasts ----------------------------------------
    fh = [r for r in done if r["config"]["experiment"] == "fixed_history"]
    grp: dict[str, dict] = {}
    for r in fh:
        grp.setdefault(match_key(r["config"]), {})[r["config"]["condition"]] = r
    fh_rows = []
    for k, g in grp.items():
        E = {c: g[c]["summary"]["decision_expected_index"] for c in g}
        any_r = next(iter(g.values()))
        row = {"run_id": any_r["run_id"], "group_key": k}
        for a, b in (("H_sudden", "H_always_low"), ("H_gradual", "H_always_low"), ("H_sudden", "H_gradual"),
                     ("H_sudden", "H_stable_high"), ("H_always_low", "H_stable_high")):
            row[f"{a}-{b}"] = E[a] - E[b] if a in E and b in E else None
        fh_rows.append(row)
    fhd = pd.DataFrame(fh_rows)
    if not fhd.empty:
        fhd = fhd.merge(units.drop(columns=["condition"]), on="run_id", how="left")
    tables["fixed_history"] = fhd
    return tables


# ---------------------------------------------------------------------------------------------
# Behavioural consistency grid
# ---------------------------------------------------------------------------------------------
def _rep0(d):
    return d[d.replicate == 0] if "replicate" in d else d


BEHAVIOURS = [
    # name, table, filter(df)->df, value column, predicted, description, figure
    ("rival_price_responsiveness", "pairs", lambda d: d[(d.condition == "E_nash") & (d.steer_kind == "none")], "post_mean",
     "negative", "E(rival at Nash price throughout) - E(stable high rival), live rounds after t_d", "18_best_response"),
    ("absolute_price_response", "fixed_history", lambda d: d[d.steer_kind == "none"], "H_always_low-H_stable_high",
     "negative", "single decision: always-low vs always-high rival history", "02b_fixed_history"),
    ("unexpected_deviation_sensitivity", "fixed_history", lambda d: d[d.steer_kind == "none"], "H_sudden-H_gradual",
     "negative", "same final rival price: sudden drop vs gradual decline (H3)", "02b_fixed_history"),
    ("punishment_like_reduction", "pairs", lambda d: d[(d.condition == "B_one_shot") & (d.steer_kind == "none")], "immediate",
     "negative", "one-shot undercut vs stable, first round after observing it (H1)", "03_deviation_response"),
    ("delayed_deviation_response", "pairs", lambda d: d[(d.condition == "B_one_shot") & (d.steer_kind == "none")], "peak",
     "negative", "one-shot undercut: most negative gap in the 4 rounds after observing it", "03_deviation_response"),
    ("persistent_deviation_response", "pairs", lambda d: d[(d.condition == "C_persistent") & (d.steer_kind == "none")], "post_mean",
     "negative", "persistent undercut vs stable, all post-deviation rounds", "03_deviation_response"),
    ("gradual_decline_response", "pairs", lambda d: d[(d.condition == "D_gradual") & (d.steer_kind == "none")], "post_mean",
     "negative", "gradual decline vs stable, all post-deviation rounds", "03_deviation_response"),
    ("recovery_after_return", "pairs", lambda d: d[(d.condition.isin(["B_one_shot", "F_delayed"])) & (d.steer_kind == "none")],
     "recovery_gap", "near_zero", "gap 1-3 rounds after the rival's return is observed (H2a, forgiveness-like if ~0)", "04_recovery"),
    ("raise_response", "pairs", lambda d: d[(d.condition == "G_raise") & (d.steer_kind == "none")], "immediate",
     "nonzero", "unexpected rival price increase vs stable", "03_deviation_response"),
    ("raise_delayed_response", "pairs", lambda d: d[(d.condition == "G_raise") & (d.steer_kind == "none")], "post_mean",
     "nonzero", "unexpected rival price increase vs stable, all post-deviation rounds", "03_deviation_response"),
    ("high_price_default", "units", lambda d: d[(d.condition == "A_stable") & (d.steer_kind == "none") &
                                                (d.experiment == "deviation_game")], "price_above_nash",
     "positive", "stable high rival: mean chosen price index minus the Nash index", "01_trajectories"),
    ("supra_competitive_pricing", "units", lambda d: d[(d.condition == "A_stable") & (d.steer_kind == "none") &
                                                       (d.experiment == "deviation_game")], "sum_collusion_index_joint",
     "positive", "collusion index under a stable high-price rival (0 = Nash profits, 1 = monopoly)", "19_collusion_index"),
    ("above_best_response", "units", lambda d: d[(d.steer_kind == "none") & (d.experiment == "deviation_game")],
     "sum_br_gap_mean", "positive", "chosen price minus one-shot best response to the rival's last price (0 = aligned)", "17_best_response"),
    ("self_play_stability", "units", lambda d: d[(d.experiment == "reactive_game") & (d.condition == "self_play")],
     "sum_stability_last5_sd", "near_zero", "SD of the last 5 self-play prices", ""),
    ("steering_price_level", "steer_level", lambda d: d[(d.steer_kind == "learned") & (d.alpha > 0) & (d.steer_timing == "all")], "level_shift",
     "negative", "learned vector: steered minus unsteered expected price (same rival script)", "06_steering_controls"),
    ("steering_specificity", "specificity", lambda d: d[(d.alpha > 0) & (d.steer_timing == "all")], "specificity",
     "negative", "learned level shift minus mean of norm-matched random directions (H4)", "06_steering_controls"),
    ("steering_random_level", "steer_level", lambda d: d[(d.steer_kind == "random") & (d.alpha > 0)], "level_shift",
     "near_zero", "norm-matched random directions, same strengths", "06_steering_controls"),
    ("steering_generic_level", "steer_level", lambda d: d[(d.steer_kind == "generic_price") & (d.alpha > 0)], "level_shift",
     "negative", "generic price direction (positive control)", "06_steering_controls"),
    ("steering_sham", "steer_level", lambda d: d[d.steer_kind == "sham"], "level_shift", "near_zero", "zero-vector hook", "06_steering_controls"),
    ("steering_x_deviation", "did", lambda d: d[(d.steer_kind == "learned") & (d.condition == "B_one_shot") & (d.steer_timing == "all")],
     "did_immediate", "nonzero", "change in the one-shot deviation response caused by steering (H5, DiD)", "08_level_vs_interaction"),
    ("steering_x_persistent", "did", lambda d: d[(d.steer_kind == "learned") & (d.condition == "C_persistent") & (d.steer_timing == "all")],
     "did_post_mean", "nonzero", "change in the persistent-deviation response caused by steering (DiD)", "08_level_vs_interaction"),
    ("steering_x_recovery", "did", lambda d: d[(d.steer_kind == "learned") & (d.condition.isin(["B_one_shot", "F_delayed"])) & (d.steer_timing == "all")],
     "did_recovery_gap", "nonzero", "change in the post-return gap caused by steering (DiD)", "08_level_vs_interaction"),
    ("random_x_deviation", "did", lambda d: d[(d.steer_kind == "random") & (d.condition == "B_one_shot")], "did_immediate",
     "near_zero", "random-direction control for the DiD", "08_level_vs_interaction"),
]
VIEWS = ["overall", "batch_id", "history_cluster", "template_id", "temperature", "seed_model_seed", "deviation_magnitude",
         "prefix_rounds", "recovery_delay", "window", "alpha", "steer_timing", "econ_id", "condition", "rounds", "steering", "model"]
# consistency dimensions reported in the per-behaviour summary (user-facing names)
DIMENSIONS = {"cross_history": "history_cluster", "cross_sampling_seed": "seed_model_seed", "cross_template": "template_id",
              "cross_temperature": "temperature", "cross_economics": "econ_id", "cross_deviation_size": "deviation_magnitude",
              "cross_history_length": "prefix_rounds", "cross_recovery_delay": "recovery_delay", "cross_window": "window",
              "cross_rival_policy": "condition", "cross_steering_strength": "alpha", "cross_batch": "batch_id"}


# main (primary-batch) settings; one-factor views hold every other factor at these values
BASELINE = {"template_id": "v1", "temperature": 0.0, "deviation_magnitude": 5, "prefix_rounds": 4, "recovery_delay": 3,
            "window": 10, "econ_id": "base"}
ONE_FACTOR = {"template_id", "temperature", "deviation_magnitude", "prefix_rounds", "recovery_delay", "window", "econ_id"}


def view_subset(d: pd.DataFrame, view: str) -> pd.DataFrame:
    """Rows admissible for a view: smoke batches only in the batch view; one-factor views vary only their own factor
    (seed_model_seed may also vary temperature); every other view uses the main settings. The overall cell uses the
    confirmatory batch when one exists."""
    if view == "batch_id":
        return d
    d0 = d
    if "designation" in d and (d.designation != "smoke").any():
        d = d[d.designation != "smoke"]   # smoke batches count only when nothing else exists
    free = {view} if view in ONE_FACTOR else ({"temperature"} if view == "seed_model_seed" else set())
    if view == "econ_id":
        free.add("deviation_magnitude")  # grid8 scales the design to its own grid
    for k, v in BASELINE.items():
        if k in free or k not in d:
            continue
        d = d[d[k] == v]
    if view == "overall" and d.empty:
        d = d0   # nothing at the main settings (e.g. a smoke/test design): describe what exists
    if view == "overall" and "designation" in d and (d.designation == "confirmatory").any():
        d = d[d.designation == "confirmatory"]
    if view == "seed_model_seed" and "temperature" in d:
        d = d[d.temperature > 0]
    return d


def _join(g, col):
    return ",".join(sorted(map(str, g[col].dropna().unique()))) if col in g else ""


def behaviour_grid(tables: dict[str, pd.DataFrame], seed: int = 0) -> pd.DataFrame:
    rows = []
    for name, tname, filt, col, pred, desc, fig in BEHAVIOURS:
        df = tables.get(tname)
        if df is None or df.empty or col not in df.columns:
            rows.append({"behaviour": name, "view": "overall", "level": "all", "status": "untested", "description": desc, "figure": fig})
            continue
        d = _rep0(filt(df))
        d = d[pd.to_numeric(d[col], errors="coerce").notna()]
        if d.empty:
            rows.append({"behaviour": name, "view": "overall", "level": "all", "status": "untested", "description": desc, "figure": fig})
            continue
        for view in VIEWS:
            dv = view_subset(d, view)
            if dv.empty or (view != "overall" and (view not in dv.columns or dv[view].nunique() < 2)):
                continue
            groups = [("all", dv)] if view == "overall" else list(dv.groupby(view))
            for level, g in groups:
                vals = g[col].astype(float)
                s = S.summarize(vals.tolist(), g["history_cluster"].tolist(), seed=seed)
                cm = vals.groupby(g["history_cluster"].values).mean()
                valid = g[["prefixed_valid", "prefixed_audits"]].apply(pd.to_numeric, errors="coerce").sum()
                rows.append({"behaviour": name, "view": view, "level": str(level), "predicted": pred, "metric": col,
                             "description": desc, "figure": fig, **s,
                             "between_history_sd": float(cm.std(ddof=1)) if len(cm) > 1 else None,
                             "directional_consistency": float(max((cm < 0).mean(), (cm > 0).mean())) if len(cm) else None,
                             "status": S.cell_status(s, pred),
                             "validity_rate": float(valid["prefixed_valid"] / valid["prefixed_audits"]) if valid["prefixed_audits"] else None,
                             "experiment_ids": _join(g, "batch_id"), "designations": _join(g, "designation"),
                             "models": _join(g, "model"), "model_revisions": _join(g, "model_revision"),
                             "history_seeds": _join(g, "history_seed"), "game_seeds": _join(g, "seed_env_seed"),
                             "sampling_seeds": _join(g, "seed_model_seed"), "templates": _join(g, "template_id"),
                             "temperatures": _join(g, "temperature"), "rival_policies": _join(g, "condition"),
                             "econ_ids": _join(g, "econ_id"), "horizons": _join(g, "rounds"),
                             "steering": _join(g, "steering"), "alphas": _join(g, "alpha"),
                             "evidence_runs": ";".join(g["run_id"].astype(str).tolist()[:60])})
    grid = pd.DataFrame(rows)
    for c in ("mean", "ci_low", "ci_high", "n_clusters", "predicted", "metric"):
        if c not in grid:
            grid[c] = np.nan
    rep = []
    for name, g in grid.groupby("behaviour", sort=False):
        overall = g[g.view == "overall"]
        # replication across robustness settings: one-factor levels and steering strengths (not per-history cells,
        # not batch labels, not the rival-script/steering-arm breakdowns, which are different comparisons)
        views = g[g.view.isin(sorted(ONE_FACTOR) + ["seed_model_seed", "alpha"])]
        st0 = overall["status"].iloc[0] if len(overall) else "untested"
        n_inf = int((views["status"] != "insufficient").sum()) if len(views) else 0
        if st0 == "untested":
            r = "untested"
        elif n_inf >= 2:
            r = S.replication_status(views["status"].tolist())
        else:
            r = "insufficient evidence" if st0 == "insufficient" else "single setting only"
        rep.append({"behaviour": name, "overall_status": st0, "replication_status": r})
    return grid.merge(pd.DataFrame(rep), on="behaviour", how="left")


def dimension_summary(grid: pd.DataFrame) -> pd.DataFrame:
    """Behaviour x consistency dimension: replication label across the levels of one parameter, with spread."""
    rows = []
    for b, g in grid.groupby("behaviour", sort=False):
        for dim, view in DIMENSIONS.items():
            v = g[g.view == view]
            if v.empty:
                rows.append({"behaviour": b, "dimension": dim, "status": "untested"}); continue
            m = pd.to_numeric(v["mean"], errors="coerce")
            sts = v["status"].tolist()
            if view == "history_cluster":  # per-history cells have 1 cluster each -> use sign agreement across histories
                sgn = np.sign(m.dropna())
                if (v["predicted"] == "near_zero").all():   # null prediction: share of histories within the margin
                    agree = float((m.dropna().abs() < S.DELTA_EQUIV).mean()) if len(sgn) else np.nan
                else:
                    agree = float(max((sgn < 0).mean(), (sgn > 0).mean())) if len(sgn) else np.nan
                lab = ("robust" if agree >= 0.8 else "mixed" if agree >= 0.6 else "not replicated") if len(sgn) >= 4 else "insufficient evidence"
                rows.append({"behaviour": b, "dimension": dim, "status": lab, "n_levels": len(v), "sign_agreement": agree,
                             "level_mean_min": float(m.min()), "level_mean_max": float(m.max()), "level_mean_sd": float(m.std(ddof=1)) if len(m) > 1 else None})
                continue
            lab = S.replication_status(sts)
            rows.append({"behaviour": b, "dimension": dim, "status": lab, "n_levels": len(v),
                         "n_supported": int(sum(x == "supported" for x in sts)), "n_opposite": int(sum(x == "opposite" for x in sts)),
                         "n_absent": int(sum(x == "absent" for x in sts)), "n_inconclusive": int(sum(x == "inconclusive" for x in sts)),
                         "n_insufficient": int(sum(x == "insufficient" for x in sts)),
                         "level_mean_min": float(m.min()), "level_mean_max": float(m.max()),
                         "level_mean_sd": float(m.std(ddof=1)) if len(m) > 1 else None,
                         "levels": ";".join(f"{l}={x:.2f}" for l, x in zip(v["level"], m))})
    return pd.DataFrame(rows)


def write_tables(tables: dict[str, pd.DataFrame], grid: pd.DataFrame, out_dir: Path) -> dict[str, str]:
    t = out_dir / "tables"; t.mkdir(parents=True, exist_ok=True)
    paths = {}
    for k, df in tables.items():
        # long per-round tables are large and fully derivable from research/raw: stored gzipped
        p = t / (f"{k}.csv.gz" if k in ("trajectories", "pair_traj") else f"{k}.csv")
        df.to_csv(p, index=False); paths[k] = str(p)
        if p.suffix == ".gz" and (t / f"{k}.csv").exists():
            (t / f"{k}.csv").unlink()
    p = t / "behaviour_cells.csv"; grid.to_csv(p, index=False); paths["behaviour_cells"] = str(p)
    return paths
