"""Pre-registered analysis for B2 (docs/prereg_deviation_b2.md)."""
from __future__ import annotations

import argparse, json
from math import comb
from pathlib import Path

import numpy as np


def rankdata(x):
    x = np.asarray(x, float); order = np.argsort(x, kind="mergesort"); r = np.empty(len(x))
    r[order] = np.arange(len(x)); out = r.copy()
    for v in np.unique(x):  # average ties
        m = x == v; out[m] = r[m].mean()
    return out


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    if ra.std() == 0 or rb.std() == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def sign_test_less(rhos):
    rhos = [r for r in rhos if np.isfinite(r) and r != 0]
    n, k = len(rhos), sum(r < 0 for r in rhos)
    p = sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n
    return {"n_cells": n, "n_negative": k, "p_one_sided": p}


def pooled_within(rows, x="deviation", y="expected_index"):
    """Spearman on within-cell centred ranks (cells = family x own)."""
    cells = {}
    for r in rows:
        cells.setdefault((r["family"], r["own_price_index"]), []).append(r)
    xs, ys = [], []
    for c in cells.values():
        xr, yr = rankdata([r[x] for r in c]), rankdata([r[y] for r in c])
        xs += list(xr - xr.mean()); ys += list(yr - yr.mean())
    return float(np.corrcoef(xs, ys)[0, 1]), cells


def perm_p(rows, x="deviation", n=10000, seed=0):
    obs, cells = pooled_within(rows, x)
    g = np.random.default_rng(seed)
    prepped = [(rankdata([r[x] for r in c]), rankdata([r["expected_index"] for r in c])) for c in cells.values()]
    prepped = [(a - a.mean(), b - b.mean()) for a, b in prepped]
    cnt = 0
    for _ in range(n):
        xs = np.concatenate([a for a, _ in prepped]); ys = np.concatenate([g.permutation(b) for _, b in prepped])
        cnt += np.corrcoef(xs, ys)[0, 1] <= obs
    return obs, (cnt + 1) / (n + 1)


def test(rows, x="deviation"):
    obs, cells = pooled_within(rows, x)
    cell_rhos = {f"{k[0]}|own{k[1]}": spearman([r[x] for r in c], [r["expected_index"] for r in c]) for k, c in cells.items()}
    _, p = perm_p(rows, x)
    st = sign_test_less(list(cell_rhos.values()))
    return {"pooled_within_cell_rho": obs, "permutation_p_one_sided": p, "sign_test": st, "cell_rhos": cell_rhos,
            "supported": bool(p < 0.05 and st["p_one_sided"] < 0.05)}


def holm(ps):
    order = np.argsort(ps); adj = np.empty(len(ps)); m = len(ps); run = 0
    for i, j in enumerate(order):
        run = max(run, (m - i) * ps[j]); adj[j] = min(1.0, run)
    return adj.tolist()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--b2", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = json.load(open(a.b2))["rows"]
    sel = lambda t, h: [r for r in rows if r["template"] == t and r["horizon"] == h]
    rep = {"H1_v1_final": test(sel("v1", "final")),
           "S1_v2_final": test(sel("v2", "final")),
           "S2_v1_nonfinal": test(sel("v1", "nonfinal"))}
    trend = [r for r in sel("v1", "final") if not r["family"].startswith("flat")]
    rep["S3_trend_prefixes_v1_final"] = {"deviation": test(trend, "deviation"), "change_from_last": test(trend, "change_from_last")}
    ps = [rep["S1_v2_final"]["permutation_p_one_sided"], rep["S2_v1_nonfinal"]["permutation_p_one_sided"],
          rep["S3_trend_prefixes_v1_final"]["deviation"]["permutation_p_one_sided"]]
    rep["secondary_holm_adjusted_p"] = dict(zip(["S1", "S2", "S3_deviation"], holm(ps)))
    rep["exploratory"] = {
        f"{t}_{h}_mean_E": float(np.mean([r["expected_index"] for r in sel(t, h)])) for t in ("v1", "v2") for h in ("final", "nonfinal")}
    rep["exploratory"]["v2_nonfinal"] = test(sel("v2", "nonfinal"))
    rep["exploratory"]["min_digit_mass"] = float(min(r["digit_mass"] for r in rows))
    (out / "b2_confirm_report.json").write_text(json.dumps(rep, indent=1))
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                             "axes.titleweight": "bold", "axes.titlelocation": "left"})
        fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
        for ax, (t, h, ttl) in zip(axs, [("v1", "final", "template v1, final round (H1)"), ("v1", "nonfinal", "template v1, round 5 of 10 (S2)")]):
            R = sel(t, h)
            for fam, c in zip(sorted({r["family"] for r in R}), ["#2a6fdb", "#e07b39", "#3a9d5d", "#7b4fbf", "#c44e52", "#9aa0a6"]):
                for own, ls in ((3, "-"), (6, "--")):
                    pts = sorted((r["deviation"], r["expected_index"]) for r in R if r["family"] == fam and r["own_price_index"] == own)
                    dv = sorted({p[0] for p in pts}); m = [np.mean([p[1] for p in pts if p[0] == v]) for v in dv]
                    ax.plot(dv, m, color=c, ls=ls, lw=1.3, marker="o", ms=2.5, label=f"{fam}" if own == 3 else None)
            res = rep["H1_v1_final" if h == "final" else "S2_v1_nonfinal"]
            ax.set_title(f"{ttl}\nwithin-cell ρ = {res['pooled_within_cell_rho']:.2f}, perm p = {res['permutation_p_one_sided']:.4f}", fontsize=9)
            ax.set_xlabel("|rival's last price − extrapolated trend| (grid steps)")
        axs[0].set_ylabel("Expected own price index"); axs[0].legend(fontsize=7, frameon=False, ncol=2)
        fig.suptitle("Pre-registered test on fresh histories: does rival deviation lower the price?",
                     fontweight="bold", x=0.01, ha="left")
        fig.tight_layout(); fig.savefig(out / "fig10_b2_confirm.png", dpi=200); plt.close(fig)
    except ImportError:
        pass
    print(json.dumps({k: (v if k.startswith("secondary") or k == "exploratory" else
                          {kk: vv for kk, vv in v.items() if kk != "cell_rhos"} if "pooled_within_cell_rho" in v else v)
                      for k, v in rep.items()}, indent=1, default=str)[:3500])


if __name__ == "__main__":
    main()
