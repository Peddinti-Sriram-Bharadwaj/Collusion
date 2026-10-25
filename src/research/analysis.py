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
BEHAVIOURS = [
    # name, table, filter(df)->df, value column, predicted, unit description
    ("rival_price_responsiveness", "pairs", lambda d: d[(d.condition == "E_nash") & (d.steer_kind == "none")], "post_mean",
     "negative", "E(rival at Nash) - E(rival stable high), live rounds after t_d"),
    ("unexpected_deviation_sensitivity", "fixed_history", lambda d: d[d.steer_kind == "none"], "H_sudden-H_gradual",
     "negative", "same final rival price, sudden vs gradual history"),
    ("absolute_price_response", "fixed_history", lambda d: d[d.steer_kind == "none"], "H_always_low-H_stable_high",
     "negative", "decision under always-low vs always-high rival"),
    ("punishment_like_reduction", "pairs", lambda d: d[(d.condition == "B_one_shot") & (d.steer_kind == "none")], "immediate",
     "negative", "one-shot undercut vs stable, first round after observing it"),
    ("persistent_deviation_response", "pairs", lambda d: d[(d.condition == "C_persistent") & (d.steer_kind == "none")], "post_mean",
     "negative", "persistent undercut vs stable, all post rounds"),
    ("recovery_after_return", "pairs", lambda d: d[(d.condition.isin(["B_one_shot", "F_delayed"])) & (d.steer_kind == "none")],
     "recovery_gap", "near_zero", "price gap 1-3 rounds after the rival returns to the high price"),
    ("raise_response", "pairs", lambda d: d[(d.condition == "G_raise") & (d.steer_kind == "none")], "immediate",
     "nonzero", "unexpected rival price increase vs stable"),
    ("supra_competitive_default", "units", lambda d: d[(d.condition == "A_stable") & (d.steer_kind == "none") &
                                                       (d.experiment == "deviation_game")], "sum_collusion_index_joint",
     "positive", "collusion index under a stable high-price rival (0 = Nash profits)"),
    ("above_best_response", "units", lambda d: d[(d.steer_kind == "none") & (d.experiment == "deviation_game")],
     "sum_br_gap_mean", "positive", "chosen price minus one-shot best response"),
    ("steering_price_level", "steer_level", lambda d: d[(d.steer_kind == "learned") & (d.alpha > 0)], "level_shift",
     "negative", "steered minus unsteered expected price (same rival script)"),
    ("steering_random_level", "steer_level", lambda d: d[(d.steer_kind == "random") & (d.alpha > 0)], "level_shift",
     "near_zero", "norm-matched random direction, same strengths"),
    ("steering_generic_level", "steer_level", lambda d: d[(d.steer_kind == "generic_price") & (d.alpha > 0)], "level_shift",
     "negative", "generic price direction (positive control)"),
    ("steering_sham", "steer_level", lambda d: d[d.steer_kind == "sham"], "level_shift", "near_zero", "zero-vector hook"),
    ("steering_x_deviation", "did", lambda d: d[(d.steer_kind == "learned") & (d.condition == "B_one_shot")], "did_immediate",
     "nonzero", "change in one-shot deviation response caused by steering (DiD)"),
    ("steering_x_persistent", "did", lambda d: d[(d.steer_kind == "learned") & (d.condition == "C_persistent")], "did_post_mean",
     "nonzero", "change in persistent-deviation response caused by steering (DiD)"),
    ("steering_x_recovery", "did", lambda d: d[(d.steer_kind == "learned") & (d.condition.isin(["B_one_shot", "F_delayed"]))],
     "did_recovery_gap", "nonzero", "change in post-return gap caused by steering (DiD)"),
    ("random_x_deviation", "did", lambda d: d[(d.steer_kind == "random") & (d.condition == "B_one_shot")], "did_immediate",
     "near_zero", "random-direction control for the DiD"),
]
VIEWS = ["overall", "model", "history_seed", "template_id", "temperature", "deviation_magnitude", "prefix_rounds",
         "recovery_delay", "alpha", "steer_layer", "econ_id", "steering", "block"]


def behaviour_grid(tables: dict[str, pd.DataFrame], seed: int = 0) -> pd.DataFrame:
    rows = []
    for name, tname, filt, col, pred, desc in BEHAVIOURS:
        df = tables.get(tname)
        if df is None or df.empty or col not in df.columns:
            rows.append({"behaviour": name, "view": "overall", "level": "all", "status": "not tested", "description": desc})
            continue
        d = filt(df)
        d = d[pd.to_numeric(d[col], errors="coerce").notna()]
        if d.empty:
            rows.append({"behaviour": name, "view": "overall", "level": "all", "status": "not tested", "description": desc})
            continue
        for view in VIEWS:
            if view != "overall" and (view not in d.columns or d[view].nunique() < 2):
                continue
            groups = [("all", d)] if view == "overall" else list(d.groupby(view))
            for level, g in groups:
                s = S.summarize(g[col].astype(float).tolist(), g["history_seed"].tolist(), seed=seed)
                valid = g[["prefixed_valid", "prefixed_audits"]].sum(numeric_only=True)
                rows.append({"behaviour": name, "view": view, "level": str(level), "predicted": pred, "metric": col,
                             "description": desc, **s, "status": S.cell_status(s, pred),
                             "validity_rate": float(valid["prefixed_valid"] / valid["prefixed_audits"]) if valid["prefixed_audits"] else None,
                             "models": ",".join(sorted(map(str, g["model"].unique()))),
                             "templates": ",".join(sorted(map(str, g["template_id"].unique()))),
                             "steering": ",".join(sorted(map(str, g["steering"].unique()))) if "steering" in g else "",
                             "designations": ",".join(sorted(map(str, g["designation"].unique()))),
                             "evidence_runs": ";".join(g["run_id"].astype(str).tolist()[:50])})
    grid = pd.DataFrame(rows)
    rep = []
    for name, g in grid.groupby("behaviour", sort=False):
        overall = g[g.view == "overall"]
        views = g[g.view != "overall"]
        rep.append({"behaviour": name, "overall_status": overall["status"].iloc[0] if len(overall) else "not tested",
                    "replication_status": S.replication_status(views["status"].tolist()) if len(views) else
                    ("insufficient evidence" if overall["status"].iloc[0] in ("insufficient", "not tested") else "single setting only")})
    return grid.merge(pd.DataFrame(rep), on="behaviour", how="left")


def write_tables(tables: dict[str, pd.DataFrame], grid: pd.DataFrame, out_dir: Path) -> dict[str, str]:
    t = out_dir / "tables"; t.mkdir(parents=True, exist_ok=True)
    paths = {}
    for k, df in tables.items():
        p = t / f"{k}.csv"; df.to_csv(p, index=False); paths[k] = str(p)
    p = t / "behaviour_cells.csv"; grid.to_csv(p, index=False); paths["behaviour_cells"] = str(p)
    return paths
