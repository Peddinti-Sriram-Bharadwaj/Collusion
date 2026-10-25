"""Figures generated only from registry-derived tables, with a manifest (figure -> code, tables, runs)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.research import stats as S
from src.research.ids import short_hash, utc_now

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlelocation": "left", "svg.hashsalt": "research"})
COND_C = {"A_stable": "#555555", "B_one_shot": "#c44e52", "C_persistent": "#2a6fdb", "D_gradual": "#3a9d5d",
          "E_nash": "#9aa0a6", "F_delayed": "#e07b39", "G_raise": "#7b4fbf"}
STEER_C = {"none": "#555555", "sham": "#bbbbbb", "learned": "#7b4fbf", "random": "#9aa0a6", "generic_price": "#3a9d5d"}
STATUS_C = {"supported": "#3a9d5d", "absent": "#c44e52", "opposite": "#7b2d2d", "inconclusive": "#e8c547",
            "insufficient": "#dddddd", "not tested": "#ffffff"}


class FigureWriter:
    def __init__(self, out_dir: Path, registry_hash: str, formats=("png", "svg", "pdf")):
        self.dir = out_dir / "figures"; self.dir.mkdir(parents=True, exist_ok=True)
        self.formats, self.registry_hash, self.manifest = formats, registry_hash, []

    def save(self, fig, name: str, func: Callable, tables: list[str], run_ids, caption: str, n: str = ""):
        files = []
        for fmt in self.formats:
            p = self.dir / f"{name}.{fmt}"
            fig.savefig(p, dpi=200, bbox_inches="tight", metadata={"Date": None} if fmt == "pdf" else None)
            files.append(str(p.name))
        plt.close(fig)
        ids = sorted(set(map(str, run_ids)))
        self.manifest.append({"figure": name, "files": files, "caption": caption, "sample": n,
                              "code": f"src/research/plots.py:{func.__name__}", "tables": tables,
                              "n_source_runs": len(ids), "source_runs_hash": short_hash(ids, 16),
                              "source_runs": ids[:200], "registry_hash": self.registry_hash, "generated_at": utc_now()})

    def skip(self, name: str, reason: str):
        self.manifest.append({"figure": name, "skipped": reason, "registry_hash": self.registry_hash})

    def write_manifest(self):
        (self.dir / "manifest.json").write_text(json.dumps(self.manifest, indent=1))


def _ci_band(ax, df, x, y, cluster, color, label, ls="-"):
    xs, m, lo, hi = [], [], [], []
    for xv, g in df.groupby(x):
        s = S.summarize(g[y].tolist(), g[cluster].tolist(), n_boot=1000)
        xs.append(xv); m.append(s["mean"]); lo.append(s["ci_low"]); hi.append(s["ci_high"])
    ax.plot(xs, m, color=color, lw=1.8, ls=ls, label=label)
    if not all(np.isnan(lo)):
        ax.fill_between(xs, lo, hi, color=color, alpha=0.15, lw=0)


def fig_trajectories(W, T):
    tr = T.get("trajectories")
    if tr is None or tr.empty:
        return W.skip("01_trajectories", "no game runs")
    d = tr[(tr.steer_kind == "none") & (tr.experiment == "deviation_game") & (tr.block == "primary")]
    if d.empty:
        d = tr[(tr.steer_kind == "none") & (tr.experiment == "deviation_game")]
    conds = [c for c in COND_C if c in d.condition.unique()]
    fig, axs = plt.subplots(2, (len(conds) + 1) // 2, figsize=(3.2 * ((len(conds) + 1) // 2), 5.4), sharey=True, squeeze=False)
    for ax, c in zip(axs.flat, conds):
        g = d[d.condition == c]
        _ci_band(ax, g, "t", "E", "history_seed", "#2a6fdb", "agent (expected price)")
        r = g.groupby("t")["rival"].mean(); ax.plot(r.index, r.values, color="#e07b39", ls="--", lw=1.2, label="rival")
        b = g.groupby("t")["br"].mean(); ax.plot(b.index, b.values, color="#3a9d5d", ls=":", lw=1, label="best response")
        ax.axvline(g.deviation_round.iloc[0], color="#ccc", lw=0.8)
        ax.set_title(f"{c} (n={g.history_seed.nunique()} histories)", fontsize=8.5); ax.set_ylim(-0.3, 9.3); ax.set_xlabel("live round")
    for ax in axs.flat[len(conds):]:
        ax.axis("off")
    axs[0, 0].set_ylabel("price index"); axs[0, 0].legend(frameon=False, fontsize=7)
    fig.suptitle("Agent and rival price trajectories by rival condition (no steering; band = 95% CI over histories)", x=0.01, ha="left", fontweight="bold")
    W.save(fig, "01_trajectories", fig_trajectories, ["trajectories"], d.run_id, "Mean expected price per live round; vertical line = deviation round.", f"{d.history_seed.nunique()} histories")


def fig_deviation_response(W, T):
    pt = T.get("pair_traj")
    if pt is None or pt.empty:
        return W.skip("02_deviation_response", "no matched pairs")
    d = pt[pt.steer_kind == "none"]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for c in [c for c in COND_C if c in d.condition.unique()]:
        _ci_band(ax, d[d.condition == c], "t", "delta", "history_seed", COND_C[c], c)
    ax.axhline(0, color="#999", lw=0.8); ax.axvline(d.deviation_round.iloc[0], color="#ccc", lw=0.8)
    ax.set_xlabel("live round"); ax.set_ylabel("Δ expected price vs stable control")
    ax.set_title("Deviation-response curves (matched to the stable-rival control)"); ax.legend(frameon=False, fontsize=7, ncol=2)
    W.save(fig, "02_deviation_response", fig_deviation_response, ["pair_traj"], d.run_id, "Per-round matched difference with 95% cluster-bootstrap CI.")


def fig_punish_recover(W, T):
    pt = T.get("pair_traj")
    if pt is None or pt.empty:
        return W.skip("03_punishment_recovery", "no matched pairs")
    d = pt[(pt.steer_kind == "none") & pt.condition.isin(["B_one_shot", "F_delayed", "C_persistent"])]
    if d.empty:
        return W.skip("03_punishment_recovery", "no B/C/F pairs")
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
    for ax, c in zip(axs, ["B_one_shot", "F_delayed", "C_persistent"]):
        g = d[d.condition == c]
        if g.empty:
            ax.axis("off"); continue
        for rd, gg in g.groupby("recovery_delay"):
            _ci_band(ax, gg, "t", "delta", "history_seed", COND_C[c], f"delay {rd}" if c == "F_delayed" else c,
                     ls="-" if rd == 3 else "--")
        td = g.deviation_round.iloc[0]
        ax.axvspan(td - 0.5, td + 0.5, color="#f2d0d0", alpha=0.6)
        ax.axhline(0, color="#999", lw=0.8); ax.set_title(c, fontsize=9); ax.set_xlabel("live round")
        ax.legend(frameon=False, fontsize=7)
    axs[0].set_ylabel("Δ expected price vs stable")
    fig.suptitle("Punishment-like response and recovery (shaded = rival deviation round)", x=0.01, ha="left", fontweight="bold")
    W.save(fig, "03_punishment_recovery", fig_punish_recover, ["pair_traj"], d.run_id, "One-shot, delayed-return and persistent deviations.")


def fig_steer_traj(W, T):
    tr = T.get("trajectories")
    if tr is None or tr.empty:
        return W.skip("04_steering_trajectories", "no games")
    d = tr[(tr.experiment == "deviation_game") & tr.condition.isin(["A_stable", "B_one_shot"])]
    labels = [l for l in d.steering.unique() if l == "none" or l.startswith("learned") or l == "random0"]
    if len(labels) < 2:
        return W.skip("04_steering_trajectories", "no steered runs")
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, c in zip(axs, ["A_stable", "B_one_shot"]):
        for l in labels:
            for a, g in d[(d.condition == c) & (d.steering == l)].groupby("alpha"):
                col = STEER_C["learned" if l.startswith("learned") else ("random" if l.startswith("random") else "none")]
                _ci_band(ax, g, "t", "E", "history_seed", col, f"{l.split(':')[0]} α={a:+g}", ls="-" if a >= 0 else "--")
        ax.set_title(c); ax.set_xlabel("live round"); ax.axvline(d.deviation_round.iloc[0], color="#ccc", lw=0.8)
    axs[0].set_ylabel("expected price"); axs[0].legend(frameon=False, fontsize=6.5)
    fig.suptitle("Steered vs unsteered trajectories", x=0.01, ha="left", fontweight="bold")
    W.save(fig, "04_steering_trajectories", fig_steer_traj, ["trajectories"], d.run_id, "Learned direction vs random control and baseline.")


def _effect_bars(ax, df, value, by, cluster="history_seed"):
    labs, ms, los, his, cols = [], [], [], [], []
    for key, g in df.groupby(by):
        s = S.summarize(g[value].tolist(), g[cluster].tolist(), n_boot=1500)
        labs.append(" ".join(map(str, key)) if isinstance(key, tuple) else str(key))
        ms.append(s["mean"]); los.append(s["ci_low"]); his.append(s["ci_high"])
        k = key[0] if isinstance(key, tuple) else key
        cols.append(STEER_C.get(str(k).split(":")[0].rstrip("0123456789"), "#7b4fbf"))
    x = np.arange(len(labs))
    ax.bar(x, ms, color=cols)
    ax.errorbar(x, ms, yerr=[np.array(ms) - np.array(los), np.array(his) - np.array(ms)], fmt="none", color="black", lw=0.8)
    ax.set_xticks(x, labs, rotation=35, ha="right", fontsize=7); ax.axhline(0, color="#999", lw=0.8)


def fig_steer_vs_random(W, T):
    lv = T.get("steer_level")
    if lv is None or lv.empty:
        return W.skip("05_steering_vs_random", "no steered runs")
    d = lv.copy(); d["kind_alpha"] = list(zip(d.steer_kind, d.alpha))
    fig, ax = plt.subplots(figsize=(8, 3.6))
    _effect_bars(ax, d, "level_shift", ["steer_kind", "alpha"])
    ax.set_ylabel("steered - unsteered expected price"); ax.set_title("Price-level effect: learned vs generic vs random vs sham")
    W.save(fig, "05_steering_vs_random", fig_steer_vs_random, ["steer_level"], d.run_id, "Mean per-round shift with 95% CI.")


def fig_level_vs_interaction(W, T):
    lv, did = T.get("steer_level"), T.get("did")
    if lv is None or lv.empty or did is None or did.empty:
        return W.skip("06_level_vs_interaction", "need steered pairs")
    a = lv[lv.condition == "A_stable"].groupby(["steer_kind", "alpha"])["level_shift"].mean()
    b = did[did.condition == "B_one_shot"].groupby(["steer_kind", "alpha"])["did_immediate"].mean()
    j = pd.concat([a, b], axis=1).dropna()
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for (k, al), r in j.iterrows():
        ax.scatter(r.level_shift, r.did_immediate, color=STEER_C.get(k, "#555"), s=40)
        ax.annotate(f"{k} {al:+g}", (r.level_shift, r.did_immediate), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.axhline(0, color="#999", lw=0.8); ax.axvline(0, color="#999", lw=0.8)
    ax.set_xlabel("price-level shift (stable rival)"); ax.set_ylabel("change in one-shot deviation response (DiD)")
    ax.set_title("Generic price-level effect vs strategic-interaction effect")
    W.save(fig, "06_level_vs_interaction", fig_level_vs_interaction, ["steer_level", "did"], list(lv.run_id) + list(did.run_id),
           "Points on the x-axis only = generic price shift; off-axis = changes deviation responsiveness.")


def fig_seed_dist(W, T):
    p = T.get("pairs")
    if p is None or p.empty:
        return W.skip("07_seed_distributions", "no pairs")
    d = p[p.steer_kind == "none"]
    fig, ax = plt.subplots(figsize=(7, 3.4))
    conds = [c for c in COND_C if c in d.condition.unique()]
    for i, c in enumerate(conds):
        v = d[d.condition == c]["immediate"].dropna()
        ax.scatter(np.full(len(v), i) + np.random.default_rng(i).uniform(-0.15, 0.15, len(v)), v, color=COND_C[c], s=14, alpha=0.8)
        ax.hlines(v.mean(), i - 0.3, i + 0.3, color="black")
    ax.set_xticks(range(len(conds)), conds, rotation=25, fontsize=7.5); ax.axhline(0, color="#999", lw=0.8)
    ax.set_ylabel("immediate response (Δ at t_d+1)"); ax.set_title("Unit-level distribution of the immediate response (each dot = one history/seed)")
    W.save(fig, "07_seed_distributions", fig_seed_dist, ["pairs"], d.run_id, "Unit-level spread; bar = mean.")


def fig_factor(W, grid, view, name, title):
    g = grid[(grid.view == view) & grid["mean"].notna()]
    if g.empty:
        return W.skip(name, f"no variation in {view}")
    behs = list(dict.fromkeys(g.behaviour))
    fig, axs = plt.subplots(1, len(behs), figsize=(2.6 * len(behs), 3.2), squeeze=False)
    for ax, b in zip(axs[0], behs):
        gg = g[g.behaviour == b]
        y = np.arange(len(gg))
        ax.errorbar(gg["mean"], y, xerr=[gg["mean"] - gg["ci_low"], gg["ci_high"] - gg["mean"]], fmt="o", color="#2a6fdb", ms=4)
        for yy, st in zip(y, gg.status):
            ax.plot([], []); ax.text(1.02, yy, st, transform=ax.get_yaxis_transform(), fontsize=6, color=STATUS_C.get(st, "#000"))
        ax.set_yticks(y, gg["level"], fontsize=7); ax.axvline(0, color="#999", lw=0.8); ax.set_title(b.replace("_", " "), fontsize=7.5)
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold")
    runs = ";".join(g["evidence_runs"].fillna("")).split(";")
    W.save(fig, name, fig_factor, ["behaviour_cells"], [r for r in runs if r], f"Effect estimate (95% CI) by {view}.")


def fig_forest(W, grid):
    g = grid[(grid.view == "overall") & grid["mean"].notna()]
    if g.empty:
        return W.skip("13_forest", "no estimates")
    fig, ax = plt.subplots(figsize=(7.5, 0.35 * len(g) + 1))
    y = np.arange(len(g))[::-1]
    ax.errorbar(g["mean"], y, xerr=[g["mean"] - g["ci_low"], g["ci_high"] - g["mean"]], fmt="o", color="black", ms=4)
    for yy, (_, r) in zip(y, g.iterrows()):
        ax.scatter(r["mean"], yy, color=STATUS_C.get(r.status, "#000"), s=40, zorder=3)
        ax.text(1.01, yy, f"{r.status} (n={r.n_clusters})", transform=ax.get_yaxis_transform(), fontsize=7)
    ax.set_yticks(y, g.behaviour, fontsize=7.5); ax.axvline(0, color="#999", lw=0.8)
    ax.set_xlabel("effect (price-index steps, or index units for collusion index)")
    ax.set_title("Effect-size forest plot (overall, 95% cluster-bootstrap CI)")
    runs = ";".join(g["evidence_runs"].fillna("")).split(";")
    W.save(fig, "13_forest", fig_forest, ["behaviour_cells"], [r for r in runs if r], "Colour = pre-declared cell status.")


def fig_consistency_heatmap(W, grid):
    g = grid[grid.view != "overall"]
    if g.empty:
        return W.skip("14_consistency_heatmap", "no factor views yet")
    g = g.assign(col=g.view + "=" + g.level)
    behs, cols = list(dict.fromkeys(grid.behaviour)), list(dict.fromkeys(g.col))
    status_code = {k: i for i, k in enumerate(STATUS_C)}
    M = np.full((len(behs), len(cols)), status_code["not tested"])
    txt = [["" for _ in cols] for _ in behs]
    for _, r in g.iterrows():
        i, j = behs.index(r.behaviour), cols.index(r.col)
        M[i, j] = status_code.get(r.status, 0)
        txt[i][j] = "" if pd.isna(r["mean"]) else f"{r['mean']:.2f}"
    from matplotlib.colors import ListedColormap
    fig, ax = plt.subplots(figsize=(0.55 * len(cols) + 3, 0.4 * len(behs) + 1.5))
    ax.imshow(M, cmap=ListedColormap(list(STATUS_C.values())), vmin=0, vmax=len(STATUS_C) - 1, aspect="auto")
    for i in range(len(behs)):
        for j in range(len(cols)):
            ax.text(j, i, txt[i][j], ha="center", va="center", fontsize=5.5)
    ax.set_yticks(range(len(behs)), behs, fontsize=7); ax.set_xticks(range(len(cols)), cols, rotation=90, fontsize=6)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in STATUS_C.values()]
    ax.legend(handles, STATUS_C.keys(), bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=7, frameon=False)
    ax.set_title("Behavioural consistency grid (cell = effect estimate; colour = status)")
    runs = ";".join(g["evidence_runs"].fillna("")).split(";")
    W.save(fig, "14_consistency_heatmap", fig_consistency_heatmap, ["behaviour_cells"], [r for r in runs if r], "Status per behaviour and tested parameter level.")


def fig_coverage(W, T):
    u = T.get("units")
    if u is None or u.empty:
        return W.skip("15_coverage", "no runs")
    tab = u.groupby(["block", "condition"]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(0.7 * tab.shape[1] + 3, 0.35 * tab.shape[0] + 1.5))
    ax.imshow(tab.values, cmap="Blues", aspect="auto")
    for i in range(tab.shape[0]):
        for j in range(tab.shape[1]):
            ax.text(j, i, tab.values[i, j], ha="center", va="center", fontsize=7)
    ax.set_xticks(range(tab.shape[1]), tab.columns, rotation=40, ha="right", fontsize=7); ax.set_yticks(range(tab.shape[0]), tab.index, fontsize=7)
    ax.set_title("Parameter coverage: completed units per block and condition")
    W.save(fig, "15_coverage", fig_coverage, ["units"], u.run_id, "Counts of completed run units.")


def fig_br(W, T):
    tr = T.get("trajectories")
    if tr is None or tr.empty:
        return W.skip("17_best_response", "no games")
    d = tr[tr.steer_kind == "none"].copy()
    d["rival_prev"] = d.groupby("run_id")["rival"].shift(1)
    d = d.dropna(subset=["rival_prev"])
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for m, g in d.groupby("model"):
        s = g.groupby("rival_prev").agg(E=("E", "mean"), br=("br", "mean"))
        ax.plot(s.index, s.E, marker="o", label=f"{m} observed")
    s = d.groupby("rival_prev")["br"].mean(); ax.plot(s.index, s.values, color="black", ls="--", label="one-shot best response")
    ax.set_xlabel("rival price last round (index)"); ax.set_ylabel("agent price (index)"); ax.legend(frameon=False, fontsize=7)
    ax.set_title("Observed response vs economic best response")
    W.save(fig, "17_best_response", fig_br, ["trajectories"], d.run_id, "Mean expected price conditional on the rival's previous price.")


def fig_collusion(W, T):
    u = T.get("units")
    if u is None or u.empty or "sum_collusion_index_joint" not in u:
        return W.skip("18_collusion_index", "no games")
    d = u[u.experiment != "fixed_history"]
    groups = [(k, g["sum_collusion_index_joint"].dropna().values) for k, g in d.groupby(["condition", "steering"])]
    groups = [(k, v) for k, v in groups if len(v)]
    fig, ax = plt.subplots(figsize=(max(6, 0.45 * len(groups)), 3.6))
    ax.boxplot([v for _, v in groups], tick_labels=[f"{c}\n{s}" for (c, s), _ in groups], showfliers=True)
    ax.axhline(0, color="#999", lw=0.8, ls=":"); ax.axhline(1, color="#999", lw=0.8, ls=":")
    ax.tick_params(axis="x", labelsize=6, rotation=60); ax.set_ylabel("collusion index (joint)")
    ax.set_title("Collusion-index distribution by condition and steering (0 = Nash, 1 = monopoly profits)")
    W.save(fig, "18_collusion_index", fig_collusion, ["units"], d.run_id, "Per-game joint collusion index.")


def fig_negative(W, grid):
    g = grid[grid.view == "overall"][["behaviour", "status", "replication_status", "mean", "ci_low", "ci_high", "n_clusters"]]
    if g.empty:
        return W.skip("19_negative_results", "no estimates")
    neg = g[g.status.isin(["absent", "opposite", "inconclusive", "insufficient"]) |
            g.replication_status.isin(["not replicated", "mixed", "inconclusive"])]
    fig, ax = plt.subplots(figsize=(8, 0.35 * max(len(neg), 1) + 1)); ax.axis("off")
    rows = [[r.behaviour, r.status, r.replication_status, "" if pd.isna(r["mean"]) else f"{r['mean']:.2f} [{r.ci_low:.2f}, {r.ci_high:.2f}]"]
            for _, r in neg.iterrows()] or [["(none)", "", "", ""]]
    t = ax.table(cellText=rows, colLabels=["behaviour", "overall cell", "replication", "estimate [95% CI]"], loc="center")
    t.auto_set_font_size(False); t.set_fontsize(7)
    ax.set_title("Null, fragile or failed-replication results")
    W.save(fig, "19_negative_results", fig_negative, ["behaviour_cells"], [], "Behaviours whose evidence is absent, inconclusive or mixed.")


def fig_dashboard(W, reg_records):
    df = pd.DataFrame([{"batch": r["batch_id"], "status": r["status"],
                        "valid": (r.get("validity") or {}).get("prefixed_valid"), "aud": (r.get("validity") or {}).get("prefixed_audits"),
                        "fvalid": (r.get("validity") or {}).get("free_valid"), "faud": (r.get("validity") or {}).get("free_audits")}
                       for r in reg_records])
    if df.empty:
        return W.skip("20_run_dashboard", "registry empty")
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
    df.groupby(["batch", "status"]).size().unstack(fill_value=0).plot.barh(stacked=True, ax=axs[0], color={"completed": "#3a9d5d", "failed": "#c44e52"})
    axs[0].set_title("Run status by batch"); axs[0].legend(frameon=False, fontsize=7)
    v = df.groupby("batch")[["valid", "aud", "fvalid", "faud"]].sum()
    axs[1].barh(v.index, v.valid / v.aud.replace(0, np.nan), color="#2a6fdb", alpha=0.6, label="prefixed (steered) audits")
    axs[1].scatter(v.fvalid / v.faud.replace(0, np.nan), v.index, color="black", zorder=3, label="free generation audits")
    axs[1].set_xlim(0, 1.05); axs[1].set_title("Strict-parse validity rate"); axs[1].legend(frameon=False, fontsize=7)
    W.save(fig, "20_run_dashboard", fig_dashboard, ["registry"], [r["run_id"] for r in reg_records], "Completion and validity per batch.")


def fig_cross_model(W, grid):
    fig_factor(W, grid, "model", "16_cross_model", "Behaviour estimates by model")


def fig_dose(W, T):
    lv, did = T.get("steer_level"), T.get("did")
    if lv is None or lv.empty:
        return W.skip("12_dose_response", "no steered runs")
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    for k, g in lv[lv.condition == "A_stable"].groupby("steer_kind"):
        _ci_band(axs[0], g, "alpha", "level_shift", "history_seed", STEER_C.get(k, "#555"), k)
    axs[0].set_xlabel("α"); axs[0].set_ylabel("price-level shift"); axs[0].axhline(0, color="#999", lw=0.8); axs[0].legend(frameon=False, fontsize=7)
    axs[0].set_title("Dose-response: price level (stable rival)")
    if did is not None and not did.empty:
        for k, g in did[did.condition == "B_one_shot"].groupby("steer_kind"):
            _ci_band(axs[1], g, "alpha", "did_immediate", "history_seed", STEER_C.get(k, "#555"), k)
    axs[1].set_xlabel("α"); axs[1].set_ylabel("DiD immediate response"); axs[1].axhline(0, color="#999", lw=0.8)
    axs[1].set_title("Dose-response: change in deviation response")
    W.save(fig, "12_dose_response", fig_dose, ["steer_level", "did"], lv.run_id, "Means with 95% CI across histories.")


def make_all(T: dict, grid: pd.DataFrame, reg_records: list, out_dir: Path, registry_hash: str, formats=("png", "svg", "pdf")) -> list:
    W = FigureWriter(out_dir, registry_hash, formats)
    for f in (fig_trajectories, fig_deviation_response, fig_punish_recover, fig_steer_traj, fig_steer_vs_random,
              fig_level_vs_interaction, fig_seed_dist, fig_coverage, fig_br, fig_collusion, fig_dose):
        try:
            f(W, T)
        except Exception as exc:
            W.skip(f.__name__, f"error: {type(exc).__name__}: {exc}")
    for view, name, title in (("template_id", "08_template_robustness", "Prompt-template robustness"),
                              ("temperature", "09_temperature", "Temperature sensitivity"),
                              ("prefix_rounds", "10_history_length", "History-length sensitivity"),
                              ("deviation_magnitude", "11_deviation_magnitude", "Deviation-magnitude sensitivity")):
        try:
            fig_factor(W, grid, view, name, title)
        except Exception as exc:
            W.skip(name, f"error: {exc}")
    for f in (fig_forest, fig_consistency_heatmap, fig_negative, fig_cross_model):
        try:
            f(W, grid)
        except Exception as exc:
            W.skip(f.__name__, f"error: {type(exc).__name__}: {exc}")
    try:
        fig_dashboard(W, reg_records)
    except Exception as exc:
        W.skip("20_run_dashboard", f"error: {exc}")
    W.write_manifest()
    return W.manifest
