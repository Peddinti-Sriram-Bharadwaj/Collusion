"""Confirmatory estimators for H1-H5 (protocol strategic_deviation_v1, amendment A1).

Every estimate is a mean over independent units (distinct pre-play histories, column ``history_cluster``);
CIs are cluster-bootstrap percentiles; p-values are two-sided centred cluster-bootstrap p-values, Holm-adjusted
across H1-H5. Replicate reruns are excluded. Only units from batches with the requested designation are used.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.research import stats as S

HYPOTHESES = [
    ("H1", "punishment-like response", "immediate(B one-shot) = E_B - E_A at t_d+1, no steering", "negative"),
    ("H2a", "recovery after the rival returns", "recovery_gap(B) over the 3 rounds after the return is observed", "near_zero"),
    ("H2b", "persistent vs one-shot after the return", "[E_C - E_A] - [E_B - E_A] over the same 3 rounds", "negative"),
    ("H3", "expectation violation", "E(H_sudden) - E(H_gradual), same final rival price", "negative"),
    ("H4", "steering specificity", "learned level shift (alpha=+1) minus mean of 3 random directions (alpha=+1)", "negative"),
    ("H5", "steering x deviation", "DiD of immediate(B): steered (learned +1) minus unsteered", "nonzero"),
]


def _base(df: pd.DataFrame, designation: str | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    d = df
    if designation and "designation" in d:
        d = d[d.designation == designation]
    if "replicate" in d:
        d = d[d.replicate == 0]
    if "block" in d and d.block.isin(["primary", "fixed_history"]).any():
        d = d[d.block.isin(["primary", "fixed_history"])]   # main settings only; sweeps are robustness evidence
    return d


def _validity(d: pd.DataFrame) -> float | None:
    if d.empty or "prefixed_audits" not in d:
        return None
    a = pd.to_numeric(d["prefixed_audits"], errors="coerce").sum()
    return float(pd.to_numeric(d["prefixed_valid"], errors="coerce").sum() / a) if a else None


def _per_cluster(values: pd.Series, clusters: pd.Series) -> pd.Series:
    return pd.Series(values.values, index=clusters.values).groupby(level=0).mean()


def estimates(T: dict[str, pd.DataFrame], designation: str | None = "confirmatory", seed: int = 0) -> pd.DataFrame:
    pairs = _base(T.get("pairs"), designation)
    pt = _base(T.get("pair_traj"), designation)
    lvl = _base(T.get("steer_level"), designation)
    did = _base(T.get("did"), designation)
    fh = _base(T.get("fixed_history"), designation)
    rows = {}

    def put(h, vals: pd.Series, d: pd.DataFrame, extra=None):
        vals = vals.dropna()
        s = S.summarize(vals.tolist(), list(vals.index), seed=seed) if len(vals) else {"n_clusters": 0}
        p = S.bootstrap_p_two_sided(vals.tolist(), list(vals.index), seed=seed) if len(vals) >= 3 else None
        rows[h] = {**s, "p_two_sided": p, "validity_rate": _validity(d), "n_runs": int(len(d)),
                   "evidence_runs": ";".join(d["run_id"].astype(str).tolist()[:40]) if "run_id" in d else "", **(extra or {})}

    none = lambda d: d[d.steer_kind == "none"] if not d.empty else d
    if not pairs.empty:
        b = none(pairs)[lambda x: x.condition == "B_one_shot"]
        put("H1", _per_cluster(b["immediate"].astype(float), b["history_cluster"]), b,
            {"frac_histories_negative": float((_per_cluster(b["immediate"].astype(float), b["history_cluster"]) < 0).mean()) if len(b) else None})
        put("H2a", _per_cluster(b["recovery_gap"].astype(float), b["history_cluster"]), b)
    if not pt.empty:
        p0 = none(pt)
        out = {}
        for cl, g in p0.groupby("history_cluster"):
            gb, gc = g[g.condition == "B_one_shot"], g[g.condition == "C_persistent"]
            if gb.empty or gc.empty:
                continue
            td = int(gb["deviation_round"].iloc[0]); ra = td + 1  # B returns one round after t_d
            w = list(range(ra + 1, ra + 4))
            db = gb.groupby("t")["delta"].mean().reindex(w); dc = gc.groupby("t")["delta"].mean().reindex(w)
            out[cl] = float((dc - db).mean())
        d2 = p0[p0.condition.isin(["B_one_shot", "C_persistent"])]
        put("H2b", pd.Series(out, dtype=float), d2.drop_duplicates("run_id"))
    if not fh.empty:
        f0 = none(fh)
        put("H3", _per_cluster(f0["H_sudden-H_gradual"].astype(float), f0["history_cluster"]), f0)
    if not lvl.empty:
        L = lvl[(lvl.steer_timing == "all")]
        le = L[(L.steer_kind == "learned") & (L.alpha == 1.0)]
        ra = L[(L.steer_kind == "random") & (L.alpha == 1.0)]
        ge = L[(L.steer_kind == "generic_price") & (L.alpha == 1.0)]
        lc, rc, gc = (_per_cluster(x["level_shift"].astype(float), x["history_cluster"]) for x in (le, ra, ge))
        diff = (lc - rc).dropna()
        put("H4", diff, pd.concat([le, ra]),
            {"learned_level": float(lc.mean()) if len(lc) else None, "random_level": float(rc.mean()) if len(rc) else None,
             "generic_level": float(gc.mean()) if len(gc) else None,
             "learned_minus_generic": float((lc - gc).dropna().mean()) if len(gc) else None,
             "learned_vs_random_ratio": float(abs(lc.mean()) / max(abs(rc.mean()), 1e-9)) if len(rc) else None})
    if not did.empty:
        dd = did[(did.steer_kind == "learned") & (did.alpha == 1.0) & (did.steer_timing == "all") & (did.condition == "B_one_shot")]
        put("H5", _per_cluster(dd["did_immediate"].astype(float), dd["history_cluster"]), dd)
    res = []
    for h, name, est, pred in HYPOTHESES:
        r = rows.get(h, {"n_clusters": 0})
        res.append({"hypothesis": h, "name": name, "estimator": est, "predicted": pred, **r,
                    "status": S.cell_status(r, pred)})
    df = pd.DataFrame(res)
    for c in ("mean", "ci_low", "ci_high", "p_two_sided", "p_holm", "validity_rate"):
        if c not in df:
            df[c] = np.nan
    ok = df["p_two_sided"].notna()
    if ok.any():
        df.loc[ok, "p_holm"] = S.holm(df.loc[ok, "p_two_sided"].astype(float).tolist())
    df["verdict"] = df.apply(verdict, axis=1)
    return df


def verdict(r) -> str:
    """Plain-language verdict from the pre-declared status (never 'absent' from a non-significant p alone)."""
    st = r.get("status")
    if st == "insufficient":
        return "insufficient evidence"
    if r["predicted"] == "near_zero":
        return {"supported": "supported (equivalent to zero within 0.25)", "opposite": "not supported (gap exceeds 0.25)"}.get(st, "inconclusive")
    return {"supported": "supported", "opposite": "not supported: significant effect in the opposite direction",
            "absent": "not supported: whole CI within +-0.25 steps of zero"}.get(st, "inconclusive")


EXPLORATORY = [
    ("X1", "direction specificity of the delayed response", "post_mean(B undercut) - post_mean(G raise), per history",
     "negative", "punishment-specific behaviour predicts a lower price after an undercut than after a raise"),
    ("X2", "response to an unexpected rival price rise", "post_mean(G raise): E_G - E_A after t_d", "nonzero", ""),
    ("X3", "delayed response to a one-shot undercut", "peak(B): most negative gap in t_d+1..t_d+4", "negative", ""),
    ("X4", "end-of-game price jump", "E at the final round minus mean E over rounds 0..T-3, stable rival", "nonzero",
     "the v1 prompt states the horizon"),
    ("X5", "initial price rise after a one-shot undercut (smoke observation)", "share of histories with immediate(B) > 0",
     "descriptive", "smoke batch: +0.23 with 2 histories"),
    ("X6", "interaction specificity: persistent undercut", "DiD post_mean(C) learned +1 minus mean of random +1", "nonzero",
     "is the steering x deviation interaction specific to the learned direction?"),
    ("X7", "interaction specificity: recovery", "DiD recovery_gap(F delayed) learned +1 minus mean of random +1", "nonzero", ""),
    ("X8", "interaction specificity: immediate response", "DiD immediate(B) learned +1 minus mean of random +1", "nonzero", ""),
    ("X9", "direction dependence of H5", "DiD immediate(B) learned +1 minus learned -1", "nonzero",
     "a direction-specific interaction should change sign with alpha"),
]


def exploratory(T: dict[str, pd.DataFrame], designation: str | None = "confirmatory", seed: int = 0) -> pd.DataFrame:
    """Exploratory (not pre-registered, not multiplicity-adjusted) contrasts on the same confirmatory data."""
    pairs = _base(T.get("pairs"), designation)
    tr = _base(T.get("trajectories"), designation)
    rows = []

    def add(code, vals: pd.Series, extra=None):
        vals = vals.dropna()
        s = S.summarize(vals.tolist(), list(vals.index), seed=seed) if len(vals) else {"n_clusters": 0}
        meta = next(e for e in EXPLORATORY if e[0] == code)
        rows.append({"code": code, "name": meta[1], "estimator": meta[2], "predicted": meta[3], "note": meta[4], **s,
                     "status": S.cell_status(s, meta[3]) if meta[3] != "descriptive" else "descriptive", **(extra or {})})

    if pairs is not None and not pairs.empty:
        p0 = pairs[pairs.steer_kind == "none"]
        pc = lambda c, m: _per_cluster(p0[p0.condition == c][m].astype(float), p0[p0.condition == c]["history_cluster"])
        add("X1", (pc("B_one_shot", "post_mean") - pc("G_raise", "post_mean")).dropna())
        add("X2", pc("G_raise", "post_mean"))
        add("X3", pc("B_one_shot", "peak"))
        imm = pc("B_one_shot", "immediate")
        add("X5", imm, {"share_positive": float((imm > 0).mean()), "share_negative": float((imm < 0).mean())})
    did = _base(T.get("did"), designation)
    if did is not None and not did.empty:
        dd = did[did.steer_timing == "all"]
        def dc(kind, alpha, cond, m):
            x = dd[(dd.steer_kind == kind) & (dd.alpha == alpha) & (dd.condition == cond)]
            return _per_cluster(x[m].astype(float), x["history_cluster"])
        add("X6", (dc("learned", 1.0, "C_persistent", "did_post_mean") - dc("random", 1.0, "C_persistent", "did_post_mean")).dropna())
        add("X7", (dc("learned", 1.0, "F_delayed", "did_recovery_gap") - dc("random", 1.0, "F_delayed", "did_recovery_gap")).dropna())
        add("X8", (dc("learned", 1.0, "B_one_shot", "did_immediate") - dc("random", 1.0, "B_one_shot", "did_immediate")).dropna())
        add("X9", (dc("learned", 1.0, "B_one_shot", "did_immediate") - dc("learned", -1.0, "B_one_shot", "did_immediate")).dropna())
    if tr is not None and not tr.empty:
        a = tr[(tr.steer_kind == "none") & (tr.condition == "A_stable") & (tr.experiment == "deviation_game")]
        if not a.empty:
            T_ = int(a.t.max())
            v = a.groupby("history_cluster").apply(lambda g: g[g.t == T_].E.mean() - g[g.t <= T_ - 2].E.mean(), include_groups=False)
            add("X4", v)
    return pd.DataFrame(rows)
