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
            "insufficient": "#dddddd", "untested": "#ffffff"}


def _main(d: pd.DataFrame | None, primary_block: bool = True) -> pd.DataFrame | None:
    """Main-analysis subset: confirmatory batch if one exists (else everything), replicate reruns excluded."""
    if d is None or d.empty:
        return d
    if "designation" in d and (d.designation == "confirmatory").any():
        d = d[d.designation == "confirmatory"]
    if "replicate" in d:
        d = d[d.replicate == 0]
    if primary_block and "block" in d and (d.block == "primary").any() and not (d.experiment == "fixed_history").all():
        d = d[(d.block == "primary") | (d.experiment == "fixed_history")]
    return d


def _nh(d) -> int:
    return int(d["history_cluster"].nunique()) if d is not None and "history_cluster" in d else 0


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
    tr = _main(T.get("trajectories"))
    if tr is None or tr.empty:
        return W.skip("01_trajectories", "no game runs")
    d = tr[(tr.steer_kind == "none") & (tr.experiment == "deviation_game") & (tr.block == "primary")]
    if d.empty:
        d = tr[(tr.steer_kind == "none") & (tr.experiment == "deviation_game")]
    conds = [c for c in COND_C if c in d.condition.unique()]
    fig, axs = plt.subplots(2, (len(conds) + 1) // 2, figsize=(3.2 * ((len(conds) + 1) // 2), 5.4), sharey=True, squeeze=False)
    for ax, c in zip(axs.flat, conds):
        g = d[d.condition == c]
        _ci_band(ax, g, "t", "E", "history_cluster", "#2a6fdb", "agent (expected price)")
        r = g.groupby("t")["rival"].mean(); ax.plot(r.index, r.values, color="#e07b39", ls="--", lw=1.2, label="rival")
        b = g.groupby("t")["br"].mean(); ax.plot(b.index, b.values, color="#3a9d5d", ls=":", lw=1, label="best response")
        ax.axvline(g.deviation_round.iloc[0], color="#ccc", lw=0.8)
        ax.set_title(f"{c} (n={_nh(g)} histories)", fontsize=8.5); ax.set_ylim(-0.3, 9.3); ax.set_xlabel("live round")
    for ax in axs.flat[len(conds):]:
        ax.axis("off")
    axs[0, 0].set_ylabel("price index"); axs[0, 0].legend(frameon=False, fontsize=7)
    fig.suptitle("Agent and rival price trajectories by rival condition (no steering; band = 95% CI over histories)", x=0.01, ha="left", fontweight="bold")
    W.save(fig, "01_trajectories", fig_trajectories, ["trajectories"], d.run_id, "Mean expected price per live round; vertical line = deviation round.", f"{_nh(d)} histories")


def fig_deviation_response(W, T):
    pt = _main(T.get("pair_traj"))
    if pt is None or pt.empty:
        return W.skip("02_deviation_response", "no matched pairs")
    d = pt[pt.steer_kind == "none"]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for c in [c for c in COND_C if c in d.condition.unique()]:
        _ci_band(ax, d[d.condition == c], "t", "delta", "history_cluster", COND_C[c], c)
    ax.axhline(0, color="#999", lw=0.8); ax.axvline(d.deviation_round.iloc[0], color="#ccc", lw=0.8)
    ax.set_xlabel("live round"); ax.set_ylabel("Δ expected price vs stable control")
    ax.set_title("Deviation-response curves (matched to the stable-rival control)"); ax.legend(frameon=False, fontsize=7, ncol=2)
    W.save(fig, "02_deviation_response", fig_deviation_response, ["pair_traj"], d.run_id, "Per-round matched difference with 95% cluster-bootstrap CI.")


def fig_punish_recover(W, T):
    pt = _main(T.get("pair_traj"))
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
            _ci_band(ax, gg, "t", "delta", "history_cluster", COND_C[c], f"delay {rd}" if c == "F_delayed" else c,
                     ls="-" if rd == 3 else "--")
        td = g.deviation_round.iloc[0]
        ax.axvspan(td - 0.5, td + 0.5, color="#f2d0d0", alpha=0.6)
        ax.axhline(0, color="#999", lw=0.8); ax.set_title(c, fontsize=9); ax.set_xlabel("live round")
        ax.legend(frameon=False, fontsize=7)
    axs[0].set_ylabel("Δ expected price vs stable")
    fig.suptitle("Punishment-like response and recovery (shaded = rival deviation round)", x=0.01, ha="left", fontweight="bold")
    W.save(fig, "03_punishment_recovery", fig_punish_recover, ["pair_traj"], d.run_id, "One-shot, delayed-return and persistent deviations.")


def fig_steer_traj(W, T):
    tr = _main(T.get("trajectories"))
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
                _ci_band(ax, g, "t", "E", "history_cluster", col, f"{l.split(':')[0]} α={a:+g}", ls="-" if a >= 0 else "--")
        ax.set_title(c); ax.set_xlabel("live round"); ax.axvline(d.deviation_round.iloc[0], color="#ccc", lw=0.8)
    axs[0].set_ylabel("expected price"); axs[0].legend(frameon=False, fontsize=6.5)
    fig.suptitle("Steered vs unsteered trajectories", x=0.01, ha="left", fontweight="bold")
    W.save(fig, "04_steering_trajectories", fig_steer_traj, ["trajectories"], d.run_id, "Learned direction vs random control and baseline.")


def _effect_bars(ax, df, value, by, cluster="history_cluster"):
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
    lv = _main(T.get("steer_level"))
    if lv is None or lv.empty:
        return W.skip("05_steering_vs_random", "no steered runs")
    d = lv.copy()
    d["arm"] = d.apply(lambda r: f"{r.steer_kind}{'' if r.steer_timing == 'all' else ' (post-dev)'}", axis=1)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    _effect_bars(ax, d, "level_shift", ["arm", "alpha"])
    ax.set_ylabel("steered - unsteered expected price\n(price-index steps)")
    ax.set_title(f"Price-level effect of each steering arm (mean over all rounds and rival scripts; n={_nh(d)} histories, 95% CI)")
    W.save(fig, "05_steering_vs_random", fig_steer_vs_random, ["steer_level"], d.run_id, "Mean per-round shift with 95% CI.")


def fig_level_vs_interaction(W, T):
    lv, did = _main(T.get("steer_level")), _main(T.get("did"))
    if lv is None or lv.empty or did is None or did.empty:
        return W.skip("06_level_vs_interaction", "need steered pairs")
    lv, did = lv[lv.steer_timing == "all"], did[did.steer_timing == "all"]
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
    p = _main(T.get("pairs"))
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
    if g.empty or g["level"].nunique() < 2:
        return W.skip(name, f"no variation in {view}")
    behs = list(dict.fromkeys(g.behaviour))
    levels = sorted(g["level"].unique(), key=lambda x: (len(x), x))
    ncol = min(4, len(behs)); nrow = int(np.ceil(len(behs) / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(3.4 * ncol, 0.32 * len(levels) * nrow + 1.2 * nrow + 0.6), squeeze=False, sharey=True)
    short = {"supported": "sup", "opposite": "opp", "absent": "abs", "inconclusive": "inc", "insufficient": "ins"}
    for k, (ax, b) in enumerate(zip(axs.flat, behs)):
        gg = g[g.behaviour == b].set_index("level").reindex(levels)
        y = np.arange(len(levels))
        ok = gg["mean"].notna().values
        ax.errorbar(gg["mean"][ok], y[ok], xerr=[(gg["mean"] - gg["ci_low"])[ok], (gg["ci_high"] - gg["mean"])[ok]], fmt="none", ecolor="#888", lw=1)
        for yy, (_, r) in zip(y, gg.iterrows()):
            if pd.notna(r["mean"]):
                ax.scatter(r["mean"], yy, color=STATUS_C.get(r.status, "#000"), s=28, zorder=3, edgecolor="black", lw=0.4)
                ax.annotate(f"{short.get(r.status, r.status)} n={int(r.n_clusters)}", (r["mean"], yy), xytext=(0, 5),
                            textcoords="offset points", ha="center", fontsize=5.5, color="#333")
        ax.axvline(0, color="#999", lw=0.8); ax.set_title(b.replace("_", " "), fontsize=8)
        ax.set_yticks(y, levels, fontsize=7); ax.set_ylim(-0.6, len(levels) - 0.4)
    for ax in list(axs.flat)[len(behs):]:
        ax.axis("off")
    fig.suptitle(f"{title}: estimate and 95% CI per level (colour = status; other factors at main settings)", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
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
    g = grid[~grid.view.isin(["overall", "history_cluster", "batch_id", "steering", "condition"])]
    if g.empty:
        return W.skip("14_consistency_heatmap", "no factor views yet")
    g = g.assign(col=g.view + "=" + g.level)
    behs, cols = list(dict.fromkeys(grid.behaviour)), list(dict.fromkeys(g.col))
    status_code = {k: i for i, k in enumerate(STATUS_C)}
    M = np.full((len(behs), len(cols)), status_code["untested"])
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
    tr = _main(T.get("trajectories"))
    if tr is None or tr.empty:
        return W.skip("17_best_response", "no games")
    d = tr[tr.steer_kind == "none"].copy()
    d["rival_prev"] = d.groupby("run_id")["rival"].shift(1)
    d = d.dropna(subset=["rival_prev"])
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for m, g in d.groupby("model"):
        _ci_band(ax, g, "rival_prev", "E", "history_cluster", "#2a6fdb", f"Qwen2.5-{m.upper()} (expected price, 95% CI)")
    s = d.groupby("rival_prev")["br"].mean(); ax.plot(s.index, s.values, color="black", ls="--", label="one-shot best response")
    ax.set_xlabel("rival price last round (index)"); ax.set_ylabel("agent price (index)"); ax.legend(frameon=False, fontsize=7)
    ax.set_title(f"Observed price vs one-round best response (no steering, n={_nh(d)} histories)")
    W.save(fig, "17_best_response", fig_br, ["trajectories"], d.run_id, "Mean expected price conditional on the rival's previous price.")


def fig_collusion(W, T):
    u = _main(T.get("units"))
    if u is None or u.empty or "sum_collusion_index_joint" not in u:
        return W.skip("18_collusion_index", "no games")
    d = u[(u.experiment == "deviation_game") & (u.steer_timing == "all") &
          (u.steering.isin(["none", "sham"]) | u.steer_kind.isin(["learned", "random"]))]
    d = d[(d.steer_kind == "none") | (d.alpha == 1.0)]
    arms = [("none", "#555555", "no steering"), ("learned", "#7b4fbf", "learned α=+1"), ("random", "#9aa0a6", "random α=+1 (3 seeds)")]
    conds = [c for c in COND_C if c in d.condition.unique()]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for k, (kind, col, lab) in enumerate(arms):
        for i, c in enumerate(conds):
            g = d[(d.condition == c) & (d.steer_kind == kind)]
            if g.empty:
                continue
            v = g.groupby("history_cluster")["sum_collusion_index_joint"].mean()
            x = i + (k - 1) * 0.25
            ax.scatter(np.full(len(v), x) + np.random.default_rng(i + 10 * k).uniform(-0.06, 0.06, len(v)), v, s=8, color=col, alpha=0.5)
            s_ = S.summarize(v.tolist(), list(v.index), n_boot=1500)
            ax.errorbar(x, s_["mean"], yerr=[[s_["mean"] - s_["ci_low"]], [s_["ci_high"] - s_["mean"]]], fmt="o", color=col, ms=6,
                        mec="black", mew=0.5, label=lab if i == 0 else None, zorder=3)
    ax.axhline(0, color="#999", lw=0.8, ls=":"); ax.axhline(1, color="#999", lw=0.8, ls=":")
    ax.text(len(conds) - 0.5, 0.02, "Nash", fontsize=7, color="#777", ha="right"); ax.text(len(conds) - 0.5, 1.01, "monopoly", fontsize=7, color="#777", ha="right")
    ax.set_xticks(range(len(conds)), [c.replace("_", " ") for c in conds], fontsize=8)
    ax.set_ylabel("joint collusion index"); ax.set_ylim(-0.05, 1.08); ax.legend(frameon=False, fontsize=7, loc="lower left")
    ax.set_title(f"Joint profits relative to Nash (0) and monopoly (1) by rival script (dots = histories, n={_nh(d)}; 95% CI)")
    W.save(fig, "18_collusion_index", fig_collusion, ["units"], d.run_id, "Per-history joint collusion index; scripted rival prices drive most of the variation between scripts.")


def fig_direction(W, T):
    pt, pr = _main(T.get("pair_traj")), _main(T.get("pairs"))
    if pt is None or pt.empty or pr is None or pr.empty:
        return W.skip("23_direction_specificity", "no matched pairs")
    pt, pr = pt[pt.steer_kind == "none"], pr[pr.steer_kind == "none"]
    if not {"B_one_shot", "G_raise"} <= set(pr.condition):
        return W.skip("23_direction_specificity", "needs B_one_shot and G_raise")
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"width_ratios": [1.4, 1]})
    lab = {"B_one_shot": "one-off undercut (7→2→7)", "G_raise": "one-off raise (7→9→7)", "C_persistent": "persistent undercut (7→2)",
           "D_gradual": "gradual decline (7→2)"}
    for c in ["B_one_shot", "G_raise", "C_persistent", "D_gradual"]:
        g = pt[pt.condition == c]
        if not g.empty:
            _ci_band(axs[0], g, "t", "delta", "history_cluster", COND_C[c], lab[c], ls="-" if c in ("B_one_shot", "G_raise") else ":")
    td = int(pt.deviation_round.iloc[0])
    axs[0].axvspan(td - 0.5, td + 0.5, color="#f2d0d0", alpha=0.6); axs[0].axhline(0, color="#999", lw=0.8)
    axs[0].set_xlabel("live round (shaded = rival's deviation round)"); axs[0].set_ylabel("Δ expected price vs stable rival (steps)")
    axs[0].legend(frameon=False, fontsize=7); axs[0].set_title("Matched price response by rival script")
    conds = [c for c in COND_C if c in pr.condition.unique()]
    ms, lo, hi = [], [], []
    for c in conds:
        g = pr[pr.condition == c]
        s_ = S.summarize(g["post_mean"].tolist(), g["history_cluster"].tolist(), n_boot=2000)
        ms.append(s_["mean"]); lo.append(s_["ci_low"]); hi.append(s_["ci_high"])
    y = np.arange(len(conds))[::-1]
    axs[1].errorbar(ms, y, xerr=[np.array(ms) - lo, np.array(hi) - ms], fmt="none", ecolor="#666")
    axs[1].scatter(ms, y, c=[COND_C[c] for c in conds], s=40, zorder=3, edgecolor="black", lw=0.4)
    axs[1].set_yticks(y, [c.replace("_", " ") for c in conds], fontsize=8); axs[1].axvline(0, color="#999", lw=0.8)
    axs[1].set_xlabel("mean Δ after the deviation (steps, 95% CI)"); axs[1].set_title(f"Post-deviation shift (n={_nh(pr)} histories)")
    fig.suptitle("The delayed price fall follows any change in the rival's pattern, including a price increase", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    W.save(fig, "23_direction_specificity", fig_direction, ["pair_traj", "pairs"], pr.run_id,
           "Undercut and raise produce the same delayed fall; a gradual decline produces a rise.")


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
    keep = lambda d: d[(d.replicate == 0) & (d.steer_timing == "all") & (d.template_id == "v1") & (d.decoding_mode == "greedy")
                       & (d.econ_id == "base") & (d.prefix_rounds == 4) & (d.window == 10) & (d.low == 2) & (d.rounds == 16)
                       & (d.steer_kind.isin(["learned", "random"]))]
    lv = keep(lv); did = keep(did) if did is not None and not did.empty else did
    if lv.empty:
        return W.skip("12_dose_response", "no matched steered runs")
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    for k, g in lv[lv.condition == "A_stable"].groupby("steer_kind"):
        _ci_band(axs[0], g, "alpha", "level_shift", "history_cluster", STEER_C.get(k, "#555"), k)
    axs[0].set_xlabel("α"); axs[0].set_ylabel("price-level shift"); axs[0].axhline(0, color="#999", lw=0.8); axs[0].legend(frameon=False, fontsize=7)
    axs[0].set_title("Dose-response: price level (stable rival)")
    if did is not None and not did.empty:
        for k, g in did[did.condition == "B_one_shot"].groupby("steer_kind"):
            _ci_band(axs[1], g, "alpha", "did_immediate", "history_cluster", STEER_C.get(k, "#555"), k)
    axs[1].set_xlabel("α"); axs[1].set_ylabel("DiD immediate response"); axs[1].axhline(0, color="#999", lw=0.8)
    axs[1].set_title("Dose-response: change in deviation response")
    W.save(fig, "12_dose_response", fig_dose, ["steer_level", "did"], lv.run_id, "Means with 95% CI across histories.")


def fig_fixed_history(W, T):
    fh = _main(T.get("fixed_history"))
    if fh is None or fh.empty:
        return W.skip("02b_fixed_history", "no fixed-history runs")
    fh = fh[fh.fixed_history_own == "prefix_random"] if (fh.fixed_history_own == "prefix_random").any() else fh
    cols = ["H_sudden-H_gradual", "H_sudden-H_always_low", "H_gradual-H_always_low", "H_always_low-H_stable_high"]
    long = fh.melt(id_vars=["history_cluster", "steering", "run_id"], value_vars=[c for c in cols if c in fh], var_name="contrast", value_name="v").dropna()
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    labs, x0 = [], 0
    for i, (c, g) in enumerate(long.groupby("contrast", sort=False)):
        for j, (st, gg) in enumerate(g.groupby("steering")):
            s_ = S.summarize(gg.v.tolist(), gg.history_cluster.tolist(), n_boot=1500)
            col = STEER_C.get(st.split(":")[0].rstrip("0123456789"), "#555")
            ax.errorbar(x0, s_["mean"], yerr=[[s_["mean"] - s_["ci_low"]], [s_["ci_high"] - s_["mean"]]], fmt="o", color=col, ms=5)
            labs.append((x0, f"{c}\n{st.split(':')[0]}")); x0 += 1
        x0 += 0.6
    ax.set_xticks([l[0] for l in labs], [l[1] for l in labs], rotation=60, ha="right", fontsize=6.5); ax.axhline(0, color="#999", lw=0.8)
    ax.set_ylabel("difference in expected price"); ax.set_title(f"Fixed-history contrasts (single decision, n={_nh(fh)} histories, 95% CI)")
    W.save(fig, "02b_fixed_history", fig_fixed_history, ["fixed_history"], long.run_id,
           "H3: sudden vs gradual at the same final rival price; absolute response: always-low vs always-high.")


def fig_hypotheses(W, T):
    h = T.get("hypotheses")
    if h is None or h.empty or h["mean"].isna().all():
        return W.skip("21_hypotheses", "no confirmatory estimates")
    h = h[h["mean"].notna()]
    fig, ax = plt.subplots(figsize=(8, 0.5 * len(h) + 1.2))
    y = np.arange(len(h))[::-1]
    for yy, (_, r) in zip(y, h.iterrows()):
        ax.errorbar(r["mean"], yy, xerr=[[r["mean"] - r["ci_low"]], [r["ci_high"] - r["mean"]]], fmt="o", color=STATUS_C.get(r.status, "#000"), ms=6)
        p = "" if pd.isna(r.get("p_holm")) else f", Holm p={r['p_holm']:.3g}"
        ax.text(1.01, yy, f"{r.verdict} (n={int(r.n_clusters)}{p})", transform=ax.get_yaxis_transform(), fontsize=7)
    ax.set_yticks(y, [f"{r.hypothesis} {r['name']}" for _, r in h.iterrows()], fontsize=7.5)
    ax.axvline(0, color="#999", lw=0.8); ax.axvspan(-0.25, 0.25, color="#eee", zorder=0)
    ax.set_xlabel("estimate (price-index steps; grey band = equivalence margin ±0.25)")
    ax.set_title("Pre-registered hypotheses H1-H5 (confirmatory batch, 95% cluster-bootstrap CI)")
    runs = ";".join(h["evidence_runs"].fillna("")).split(";")
    W.save(fig, "21_hypotheses", fig_hypotheses, ["hypotheses"], [r for r in runs if r], "Colour = pre-declared status.")


def fig_dimensions(W, T):
    d = T.get("consistency_by_dimension")
    if d is None or d.empty:
        return W.skip("22_consistency_dimensions", "no dimension summary")
    d = d[d.status != "untested"]
    if d.empty:
        return W.skip("22_consistency_dimensions", "no tested dimensions")
    RC = {"robust": "#3a9d5d", "mixed": "#e8c547", "not replicated": "#c44e52", "inconclusive": "#f0e3a0",
          "insufficient evidence": "#dddddd", "untested": "#ffffff"}
    behs, dims = list(dict.fromkeys(d.behaviour)), list(dict.fromkeys(d.dimension))
    code = {k: i for i, k in enumerate(RC)}
    M = np.full((len(behs), len(dims)), code["untested"]); txt = [["" for _ in dims] for _ in behs]
    for _, r in d.iterrows():
        i, j = behs.index(r.behaviour), dims.index(r.dimension)
        M[i, j] = code.get(r.status, code["untested"])
        if pd.notna(r.get("level_mean_min")):
            txt[i][j] = f"{r.level_mean_min:.2f}..{r.level_mean_max:.2f}"
    from matplotlib.colors import ListedColormap
    fig, ax = plt.subplots(figsize=(1.1 * len(dims) + 3, 0.42 * len(behs) + 1.6))
    ax.imshow(M, cmap=ListedColormap(list(RC.values())), vmin=0, vmax=len(RC) - 1, aspect="auto")
    for i in range(len(behs)):
        for j in range(len(dims)):
            ax.text(j, i, txt[i][j], ha="center", va="center", fontsize=5.5)
    ax.set_yticks(range(len(behs)), behs, fontsize=7); ax.set_xticks(range(len(dims)), dims, rotation=45, ha="right", fontsize=7)
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in RC.values()], RC.keys(), bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=7, frameon=False)
    ax.set_title("Consistency of each behaviour across each parameter dimension (cell text = range of level means)")
    W.save(fig, "22_consistency_dimensions", fig_dimensions, ["consistency_by_dimension"], [], "Replication label across the levels of one dimension.")


def make_all(T: dict, grid: pd.DataFrame, reg_records: list, out_dir: Path, registry_hash: str, formats=("png", "svg", "pdf")) -> list:
    W = FigureWriter(out_dir, registry_hash, formats)
    for f in (fig_trajectories, fig_deviation_response, fig_fixed_history, fig_punish_recover, fig_steer_traj, fig_steer_vs_random,
              fig_level_vs_interaction, fig_seed_dist, fig_coverage, fig_br, fig_collusion, fig_dose, fig_hypotheses, fig_dimensions, fig_direction):
        try:
            f(W, T)
        except Exception as exc:
            W.skip(f.__name__, f"error: {type(exc).__name__}: {exc}")
    for view, name, title in (("template_id", "08_template_robustness", "Prompt-template robustness"),
                              ("temperature", "09_temperature", "Temperature sensitivity"),
                              ("prefix_rounds", "10_history_length", "History-length sensitivity"),
                              ("deviation_magnitude", "11_deviation_magnitude", "Deviation-magnitude sensitivity"),
                              ("econ_id", "11b_economics", "Economic-setting sensitivity"),
                              ("recovery_delay", "11c_recovery_delay", "Recovery-delay sensitivity"),
                              ("alpha", "11d_steering_strength", "Steering-strength sensitivity"),
                              ("seed_model_seed", "11e_sampling_seed", "Sampling-seed variation (temperature > 0)")):
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
