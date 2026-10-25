"""Phase C analysis: activation patching map (Fig 9) and steering dose-response/specificity (Fig 7, 8)."""
from __future__ import annotations

import argparse, json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlelocation": "left"})
SITE_C = {"rival": "#e07b39", "answer": "#2a6fdb", "own_profit": "#3a9d5d"}


def boot_ci(x, n=2000, seed=0):
    x = np.asarray(x, float)
    g = np.random.default_rng(seed)
    m = [g.choice(x, len(x)).mean() for _ in range(n)]
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def c1(path, out, tag):
    """Fraction of the edit's effect recovered by patching one site at one layer.

    Per arm, site and layer: sum_i (E_patched_i - E_ctrl_i)(E_donor_i - E_ctrl_i) / sum_i (E_donor_i - E_ctrl_i)^2,
    i.e. the least-squares slope of patched effect on full effect (1 = site carries the whole effect).
    This is direction-agnostic, which matters because both rival raises and cuts lower the 7B price.
    """
    d = json.load(open(path))
    res = [r for r in d["results"] if "skipped" not in r]
    summary = {"n_pairs": len(res), "skipped": len(d["results"]) - len(res), "metric": c1.__doc__.strip(), "by_arm": {}}
    arms = sorted({r["arm"] for r in res})
    label = {"real": "realistic edit (rival price + profit text differ)", "stale": "stale-profit edit (only rival price differs)"}
    fig, axs = plt.subplots(1, len(arms), figsize=(5.2 * len(arms), 3.8), squeeze=False, sharey=True)
    for ai, arm in enumerate(arms):
        rr = [r for r in res if r["arm"] == arm]
        layers = rr[0]["layers"]
        total = np.array([r["E_donor"] - r["E_control"] for r in rr])
        s = {"mean_abs_total_effect": float(np.abs(total).mean()), "sites": {}}
        ax = axs[0, ai]
        for site in rr[0]["E_patched"]:
            eff = np.array([np.array(r["E_patched"][site]) - r["E_control"] for r in rr])
            frac = (eff * total[:, None]).sum(0) / (total ** 2).sum()
            g = np.random.default_rng(0)
            boots = []
            for _ in range(1000):
                idx = g.integers(0, len(rr), len(rr))
                boots.append((eff[idx] * total[idx, None]).sum(0) / (total[idx] ** 2).sum())
            lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
            s["sites"][site] = {"fraction_recovered_by_layer": frac.tolist(), "ci_low": lo.tolist(), "ci_high": hi.tolist()}
            c = SITE_C.get(site, "#555")
            ax.plot(layers, frac, color=c, lw=2, marker="o", ms=3, label=f"patch {site.replace('_', ' ')} tokens" if site != "answer" else "patch answer token")
            ax.fill_between(layers, lo, hi, color=c, alpha=0.15, lw=0)
        ax.axhline(1, color="black", ls="--", lw=0.8); ax.axhline(0, color="#999", lw=0.8)
        ax.set_xlabel("Layer patched"); ax.set_title(f"{label.get(arm, arm)}\n{len(rr)} pairs, mean |effect| {np.abs(total).mean():.2f}", fontsize=9)
        if ai == 0:
            ax.set_ylabel("Fraction of edit effect recovered")
            ax.legend(frameon=False, fontsize=8, loc="center left")
        summary["by_arm"][arm] = s
    fig.suptitle("Activation patching: where the rival-price edit acts", fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(out / f"fig9_patching_{tag}.png", dpi=200); plt.close(fig)
    return summary


def c2(path, out, tag):
    d = json.load(open(path))
    alphas = np.array(d["alphas"], float)
    res = d["results"]
    names = list(res[0]["E"])
    zero = int(np.where(alphas == 0)[0][0])
    curves, slopes = {}, {}
    for n in names:
        eff = np.array([np.array(r["E"][n]) - r["E"][n][zero] for r in res])  # [controls, alphas]
        curves[n] = eff
        slopes[n] = np.array([np.polyfit(alphas, e, 1)[0] for e in eff])
    summary = {"layer": d["layer"], "site": d["site"], "n_controls": len(res), "directions": {}}
    for n in names:
        summary["directions"][n] = {"mean_effect_by_alpha": curves[n].mean(0).tolist(),
                                    "slope_mean": float(slopes[n].mean()), "slope_ci": boot_ci(slopes[n])}
    def group(n):
        for g in ("rival", "own", "deviation"):
            if n.startswith(g):
                return g
        return "random"
    colors = {"rival": "#e07b39", "own": "#3a9d5d", "deviation": "#7b4fbf", "random": "#9aa0a6"}
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    for n in names:
        m = curves[n].mean(0)
        lo_hi = np.array([boot_ci(curves[n][:, j]) for j in range(len(alphas))])
        ax.plot(alphas, m, color=colors[group(n)], lw=2 if group(n) != "random" else 1, label=n)
        if group(n) != "random":
            ax.fill_between(alphas, lo_hi[:, 0], lo_hi[:, 1], color=colors[group(n)], alpha=0.15, lw=0)
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_xlabel("Steering strength α (× mean residual norm / 10)"); ax.set_ylabel("Change in expected price index")
    ax.set_title(f"Steering dose-response (layer {d['layer']}, {d['site']} site)"); ax.legend(frameon=False, fontsize=7)
    fig.tight_layout(); fig.savefig(out / f"fig7_dose_response_{tag}.png", dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    for i, n in enumerate(names):
        s = summary["directions"][n]
        ax.bar(i, s["slope_mean"], color=colors[group(n)])
        ax.errorbar(i, s["slope_mean"], yerr=[[s["slope_mean"] - s["slope_ci"][0]], [s["slope_ci"][1] - s["slope_mean"]]], color="black", capsize=3)
    ax.set_xticks(range(len(names)), names, rotation=30, ha="right", fontsize=8)
    ax.axhline(0, color="#999", lw=0.8); ax.set_ylabel("Slope: Δ expected index per unit α")
    ax.set_title("Specificity: feature directions vs random controls")
    fig.tight_layout(); fig.savefig(out / f"fig8_specificity_{tag}.png", dpi=200); plt.close(fig)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c1"); ap.add_argument("--c2"); ap.add_argument("--out", required=True); ap.add_argument("--tag", default="")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rep = {}
    if a.c1:
        rep["c1"] = c1(a.c1, out, a.tag)
    if a.c2:
        rep["c2"] = c2(a.c2, out, a.tag)
    (out / f"phase_c_summary_{a.tag}.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1)[:4000])


if __name__ == "__main__":
    main()
