"""Figures for C3 (transfer vector), D (repeated games) and the model-size comparison.

  python analysis/phase_cd_figures.py --c3d c3d_7b.json --d1 d1_7b.json --scaling-dir runs/ --out figs/
"""
from __future__ import annotations

import argparse, glob, json, os
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlelocation": "left"})
COL = {"edit_vector": "#7b4fbf", "nonce_vector": "#3a9d5d", "random": "#9aa0a6"}
NASH, MONO = 2, 7


def ci(x, n=2000, seed=0):
    x = np.asarray(x, float); g = np.random.default_rng(seed)
    m = [g.choice(x, len(x)).mean() for _ in range(n)]
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


def c3_figs(c3, out):
    alphas = np.array(c3["alphas"]); rep = {}
    keys = list(c3["sites"])
    fig, axs = plt.subplots(1, len(keys), figsize=(5.4 * len(keys), 3.9), squeeze=False, sharey=True)
    for ax, key in zip(axs[0], keys):
        s = c3["sites"][key]; tests = s["a1_test"]
        actual = np.mean([np.mean([t["E_edits"][d] - t["E_control"] for d in ("undercut", "raise")]) for t in tests])
        names = list(tests[0]["curves"])
        rep[key] = {"actual_mean_edit_effect": float(actual), "vector_norm": s["vector_norm"],
                    "pair_consistency": s["mean_cos_pair_diff_to_vector"], "curves": {}}
        for n in names:
            M = np.array([t["curves"][n] for t in tests]); m = M.mean(0)
            lohi = np.array([ci(M[:, j]) for j in range(len(alphas))])
            grp = "random" if n.startswith("random") else n
            ax.plot(alphas, m, color=COL[grp], lw=2.2 if grp != "random" else 1,
                    label={"edit_vector": "edit vector (from training histories)", "nonce_vector": "nonce vector (sham)"}.get(n, "random (norm-matched)" if n == "random0" else None))
            if grp != "random":
                ax.fill_between(alphas, lohi[:, 0], lohi[:, 1], color=COL[grp], alpha=0.15, lw=0)
            rep[key]["curves"][n] = m.tolist()
        ax.axhline(actual, color="#c44e52", ls="--", lw=1.2, label="actual edit effect (held-out)")
        ax.axhline(0, color="#999", lw=0.8); ax.axvline(1, color="#ccc", lw=0.8)
        site, layer = key.rsplit("_L", 1)
        ax.set_title(f"{'reply-start token' if site == 'reply_start' else 'answer token'}, layer {layer}\n{len(tests)} held-out histories", fontsize=9)
        ax.set_xlabel("Vector strength (1 = average real edit)")
        # rescue
        res = np.array([[t["rescue"][d]["edit_vector"] / (t["E_edits"][d] - t["E_control"]) for d in ("undercut", "raise")
                         if abs(t["E_edits"][d] - t["E_control"]) > 0.2] for t in tests], dtype=object)
        flat = [x for r in res for x in r]
        rep[key]["rescue_fraction_median"] = float(-np.median(flat)) if flat else None
    axs[0, 0].set_ylabel("Change in expected price index"); axs[0, 0].legend(frameon=False, fontsize=7.5)
    fig.suptitle("One averaged activation vector reproduces the rival-edit effect on unseen histories",
                 fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(out / "fig11_transfer_vector_a1.png", dpi=200); plt.close(fig)

    fig, axs = plt.subplots(1, len(keys), figsize=(5.4 * len(keys), 3.9), squeeze=False, sharey=True)
    for ax, key in zip(axs[0], keys):
        b2 = c3["sites"][key]["b2_test"]; rep[key]["b2"] = {}
        for kind, ls in (("continue", "-"), ("break", "--")):
            for n, grp in (("edit_vector", "edit_vector"), ("random0", "random"), ("nonce_vector", "nonce_vector")):
                M = np.array([t["curves"][n] for t in b2 if t["kind"] == kind]); m = M.mean(0)
                ax.plot(alphas, m, color=COL[grp], ls=ls, lw=2 if grp == "edit_vector" else 1,
                        label=f"{n.replace('_', ' ')}, rival {'kept trend' if kind == 'continue' else 'broke trend'}")
                rep[key]["b2"][f"{kind}_{n}"] = m.tolist()
        gap = np.mean([t["E"] for t in b2 if t["kind"] == "continue"]) - np.mean([t["E"] for t in b2 if t["kind"] == "break"])
        rep[key]["b2"]["natural_gap_continue_minus_break"] = float(gap)
        ax.axhline(0, color="#999", lw=0.8)
        site, layer = key.rsplit("_L", 1)
        ax.set_title(f"{'reply-start' if site == 'reply_start' else 'answer'} token, layer {layer}; fresh histories (n={len(b2)})\n"
                     f"natural price gap kept-vs-broke trend: {gap:.2f}", fontsize=9)
        ax.set_xlabel("Vector strength")
    axs[0, 0].set_ylabel("Change in expected price index"); axs[0, 0].legend(frameon=False, fontsize=6.5)
    fig.suptitle("Same vector on fresh pre-registered histories (both prompt wordings, both horizons)",
                 fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(out / "fig12_transfer_vector_b2.png", dpi=200); plt.close(fig)
    return rep


def d_traj(d1, out, tag, cond="none"):
    games = [g for g in d1["games"] if g["condition"] == cond]
    strategies = d1["strategies"]
    n = len(strategies); cols = 4; rows = int(np.ceil(n / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(3.4 * cols, 2.6 * rows), sharex=True, sharey=True, squeeze=False)
    for ax, st in zip(axs.flat, strategies):
        G = [g for g in games if g["strategy"] == st]
        samp = np.array([[r["llm_action"] for r in g["rounds"]] for g in G if g["mode"] == "sample"])
        greedy = [g for g in G if g["mode"] == "greedy"][0]
        T = np.arange(len(greedy["rounds"]))
        if len(samp):
            ax.fill_between(T, samp.min(0), samp.max(0), color="#2a6fdb", alpha=0.15, lw=0)
        ax.plot(T, [r["llm_action"] for r in greedy["rounds"]], color="#2a6fdb", lw=2, label="LLM firm")
        ax.plot(T, [r["rival_action"] for r in greedy["rounds"]], color="#e07b39", lw=1.5, ls="--", label="rival")
        ax.axhline(NASH, color="#555", ls=":", lw=0.8); ax.axhline(MONO, color="#555", ls=":", lw=0.8)
        ax.set_title(f"{st.replace('_', ' ')}  (Δ={np.mean([g['collusion_index_joint'] for g in G]):.2f})", fontsize=8.5)
        ax.set_ylim(-0.5, 9.5)
    for ax in axs.flat[n:]:
        ax.axis("off")
    axs[0, 0].legend(frameon=False, fontsize=7)
    for ax in axs[-1]:
        ax.set_xlabel("round")
    for ax in axs[:, 0]:
        ax.set_ylabel("price index")
    fig.suptitle(f"Repeated pricing games, {tag} (greedy line, band = 4 sampled games; dotted = Nash 2 / monopoly 7)",
                 fontweight="bold", x=0.01, ha="left", fontsize=10)
    fig.tight_layout(); fig.savefig(out / f"fig13_games_{tag}.png", dpi=200); plt.close(fig)


def d_steer(d1, out, tag):
    conds = sorted({g["condition"] for g in d1["games"]}, key=lambda c: 0 if c == "none" else float(c[5:]))
    strategies = d1["strategies"]; rep = {}
    fig, ax = plt.subplots(figsize=(8.5, 3.8)); w = 0.8 / len(conds)
    colors = {"none": "#555", "steer-1": "#2a6fdb", "steer+1": "#e07b39", "steer+2": "#c44e52"}
    for i, c in enumerate(conds):
        means, los, his = [], [], []
        for st in strategies:
            x = [g["mean_llm_action"] for g in d1["games"] if g["condition"] == c and g["strategy"] == st]
            means.append(np.mean(x)); lo, hi = ci(x); los.append(lo); his.append(hi)
        rep[c] = dict(zip(strategies, means))
        xs = np.arange(len(strategies)) + (i - (len(conds) - 1) / 2) * w
        ax.bar(xs, means, w, color=colors.get(c, "#999"), label=c.replace("steer", "vector ×"))
        ax.errorbar(xs, means, yerr=[np.array(means) - los, np.array(his) - means], fmt="none", color="black", lw=0.8)
    ax.axhline(NASH, color="#555", ls=":", lw=0.8); ax.axhline(MONO, color="#555", ls=":", lw=0.8)
    ax.set_xticks(range(len(strategies)), [s.replace("_", "\n") for s in strategies], fontsize=8)
    ax.set_ylabel("Mean price of steered firm (index)"); ax.legend(frameon=False, fontsize=8, ncol=len(conds))
    ax.set_title(f"Steering one firm with the rival-edit vector changes its game prices ({tag})")
    fig.tight_layout(); fig.savefig(out / f"fig14_steered_games_{tag}.png", dpi=200); plt.close(fig)
    return rep


def scaling(runs_dir, out):
    order = ["0.5b", "1.5b", "3b", "7b", "14b", "32b"]
    rows = []
    for m in order:
        r = {"model": m}
        f = Path(runs_dir) / f"a1_{m}.json"
        if f.exists():
            d = json.load(open(f))
            if "summary" in d:
                s = d["summary"]["delta_expected_index_vs_control"]
                by = {}
                for x in d["rows"]:
                    by.setdefault(x["control_id"], {})[(x["condition"], x["edit_direction"])] = x
                nonce = max(abs(g[("negative_control_audit_nonce", None)]["expected_index"] - g[("control_realistic", None)]["expected_index"]) for g in by.values())
                eff = [abs(g[("realistic_rival_final", dd)]["expected_index"] - g[("control_realistic", None)]["expected_index"]) for g in by.values() for dd in ("undercut", "raise")]
                r.update(mean_abs_edit=float(np.mean(eff)), max_nonce=float(nonce),
                         frac_beyond_nonce=float(np.mean(np.array(eff) > nonce)),
                         mean_price=float(np.mean([x["expected_index"] for x in d["rows"] if x["condition"] == "control_realistic"])),
                         valid=d["summary"]["greedy_strict_valid"],
                         d_raise=s["realistic_rival_final:raise"]["mean"], d_cut=s["realistic_rival_final:undercut"]["mean"])
        f = Path(runs_dir) / f"b2_{m}.json"
        if f.exists():
            import sys; sys.path.insert(0, str(Path(__file__).parent))
            from phase_b2_confirm import pooled_within
            d = json.load(open(f))
            if "rows" in d:
                rr = [x for x in d["rows"] if x["template"] == "v1" and x["horizon"] == "final"]
                r["trend_break_rho"] = pooled_within(rr)[0] if np.std([x["expected_index"] for x in rr]) > 0 else None
        f = Path(runs_dir) / f"d1_{m}.json"
        if f.exists():
            d = json.load(open(f))
            if "games" in d:
                for st in ("llm_selfplay", "tit_for_tat", "fixed_nash", "fixed_monopoly"):
                    r[f"delta_{st}"] = float(np.mean([g["collusion_index_joint"] for g in d["games"] if g["strategy"] == st and g["condition"] == "none"]))
                    r[f"price_{st}"] = float(np.mean([g["mean_llm_action"] for g in d["games"] if g["strategy"] == st and g["condition"] == "none"]))
        rows.append(r)
    rows = [r for r in rows if len(r) > 1]
    (out / "scaling_summary.json").write_text(json.dumps(rows, indent=1))
    if not rows:
        return rows
    x = np.arange(len(rows)); lab = [r["model"].upper() for r in rows]
    g = lambda k: [r.get(k) if r.get(k) is not None else np.nan for r in rows]
    fig, axs = plt.subplots(1, 4, figsize=(16, 3.7))
    axs[0].bar(x - 0.2, g("mean_abs_edit"), 0.4, color="#7b4fbf", label="rival-price edit")
    axs[0].bar(x + 0.2, g("max_nonce"), 0.4, color="#9aa0a6", label="irrelevant-number control (max)")
    axs[0].set_title("a. Sensitivity to the rival's price", fontsize=10); axs[0].set_ylabel("|change in expected price|")
    axs[0].legend(frameon=False, fontsize=7.5)
    axs[1].bar(x - 0.2, g("d_raise"), 0.4, color="#e07b39", label="rival raised price")
    axs[1].bar(x + 0.2, g("d_cut"), 0.4, color="#2a6fdb", label="rival cut price")
    axs[1].axhline(0, color="#999", lw=0.8)
    axs[1].set_title("b. Direction of response\n(best response: raise \u2192 up, cut \u2192 down)", fontsize=10)
    axs[1].set_ylabel("mean change in own price"); axs[1].legend(frameon=False, fontsize=7.5)
    axs[2].plot(x, g("mean_price"), marker="o", color="#2a6fdb", label="one-shot prompt")
    axs[2].plot(x, g("price_llm_selfplay"), marker="s", color="#e07b39", label="self-play game")
    axs[2].plot(x, g("price_tit_for_tat"), marker="^", color="#3a9d5d", label="vs tit-for-tat")
    axs[2].axhline(NASH, color="#555", ls=":", lw=0.8); axs[2].axhline(MONO, color="#555", ls=":", lw=0.8)
    axs[2].text(len(rows) - 0.5, NASH + 0.1, "Nash", fontsize=7); axs[2].text(len(rows) - 0.5, MONO + 0.1, "monopoly", fontsize=7)
    axs[2].set_title("c. Price level", fontsize=10); axs[2].set_ylabel("price index"); axs[2].legend(frameon=False, fontsize=7.5)
    axs[3].bar(x - 0.2, g("delta_llm_selfplay"), 0.4, color="#e07b39", label="self-play")
    axs[3].bar(x + 0.2, g("delta_tit_for_tat"), 0.4, color="#3a9d5d", label="vs tit-for-tat")
    axs[3].axhline(0, color="#555", ls=":", lw=0.8); axs[3].axhline(1, color="#555", ls=":", lw=0.8)
    axs[3].set_title("d. Collusion index \u0394 in 15-round games\n(0 = Nash profits, 1 = monopoly profits)", fontsize=10)
    axs[3].legend(frameon=False, fontsize=7.5)
    for ax in axs:
        ax.set_xticks(x, lab)
    fig.suptitle("Qwen2.5 0.5B to 32B on the same tests", fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(out / "fig15_scaling.png", dpi=200); plt.close(fig)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c3d"); ap.add_argument("--d1", action="append", default=[]); ap.add_argument("--scaling-dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); rep = {}
    if a.c3d:
        d = json.load(open(a.c3d))
        rep["c3"] = c3_figs(d["c3"], out)
        rep["steered_games_7b"] = d_steer(d["d1"], out, "7B")
    for f in a.d1:
        d = json.load(open(f)); tag = Path(f).stem.replace("d1_", "").upper()
        d_traj(d, out, tag)
    if a.scaling_dir:
        rep["scaling"] = scaling(a.scaling_dir, out)
    (out / "cd_summary.json").write_text(json.dumps(rep, indent=1, default=float))
    print(json.dumps(rep, indent=1, default=float)[:5000])


if __name__ == "__main__":
    main()


def steer_vs_random(edit_d1, rand_d1, out, tag="7B"):
    strategies = edit_d1["strategies"]; alphas = ["steer-1", "steer+1", "steer+2"]
    def delta(d1, c, st, key="mean_llm_action"):
        base = np.mean([g[key] for g in d1["games"] if g["condition"] == "none" and g["strategy"] == st])
        return np.mean([g[key] for g in d1["games"] if g["condition"] == c and g["strategy"] == st]) - base
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.8), sharey=False)
    rep = {}
    for ax, key, lab in ((axs[0], "mean_llm_action", "change in steered firm's mean price"),
                         (axs[1], "collusion_index_joint", "change in collusion index Δ (joint)")):
        w = 0.13; rep[key] = {}
        for i, c in enumerate(alphas):
            e = [delta(edit_d1, c, s, key) for s in strategies]; r = [delta(rand_d1, c, s, key) for s in strategies]
            rep[key][c] = {"edit": dict(zip(strategies, map(float, e))), "random": dict(zip(strategies, map(float, r)))}
            xs = np.arange(len(strategies)) + (i - 1) * 2 * w
            col = {"steer-1": "#2a6fdb", "steer+1": "#e07b39", "steer+2": "#c44e52"}[c]
            ax.bar(xs - w / 2, e, w, color=col, label=f"edit vector ×{c[5:]}")
            ax.bar(xs + w / 2, r, w, color=col, alpha=0.3, hatch="//", edgecolor=col, label=f"random vector ×{c[5:]}")
        ax.axhline(0, color="#555", lw=0.8)
        ax.set_xticks(range(len(strategies)), [s.replace("_", "\n") for s in strategies], fontsize=8)
        ax.set_ylabel(lab)
    axs[0].legend(frameon=False, fontsize=7, ncol=3, loc="lower left")
    axs[0].set_title("a. Price of the steered firm"); axs[1].set_title("b. Market outcome")
    fig.suptitle(f"Edit vector vs norm-matched random vector, repeated games ({tag}; solid = edit vector, hatched = random)",
                 fontweight="bold", x=0.01, ha="left", fontsize=10)
    fig.tight_layout(); fig.savefig(out / f"fig14b_steer_vs_random_{tag}.png", dpi=200); plt.close(fig)
    (out / f"steer_vs_random_{tag}.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__" and False:
    pass
