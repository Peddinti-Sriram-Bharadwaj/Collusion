"""Phase B analysis: layer-wise linear probes, controls, geometry and steering directions.

Input: B1 json + npz (from scripts/run_phase_bc.py --task b1 or the Modal runner).
Outputs (next to --out): probes.json, directions.npz, fig4/5/6 PNGs.

Probe protocol (predeclared):
* ridge regression (alpha chosen by inner CV) on standardized activations;
* outer split = leave-one-rival-family-out (6 families), template v1 only for Fig 4;
* metric = out-of-fold R^2 for the final rival index;
* controls: (i) shuffled targets (same splits), (ii) the pre_rival site, which by
  causal masking cannot contain the final rival price, (iii) layer 0 = token identity;
* cross-template: fit on v1, test on v2 (and reverse), all families;
* steering layer = argmax over layers 1..L-2 of answer-site R^2 (B1 only).
"""
from __future__ import annotations

import argparse, json
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ALPHAS = np.logspace(-1, 5, 13)


def probe_cv(X, y, groups, rng=None, shuffle=False):
    y = y.astype(float).copy()
    if shuffle:
        y = rng.permutation(y)
    pred = np.zeros_like(y)
    for g in np.unique(groups):
        tr, te = groups != g, groups == g
        m = make_pipeline(StandardScaler(), RidgeCV(alphas=ALPHAS)).fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return float(r2_score(y, pred))


def transfer(Xa, ya, Xb, yb):
    """Fit on one template, test on the other; returns (R^2, Pearson r).

    R^2 penalises any offset/scale shift between templates; r measures whether
    the same direction still orders the held-out template correctly."""
    m = make_pipeline(StandardScaler(), RidgeCV(alphas=ALPHAS)).fit(Xa, ya)
    p = m.predict(Xb)
    return float(r2_score(yb, p)), float(np.corrcoef(yb, p)[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--b1", required=True); ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    res = json.load(open(args.b1)); arr = np.load(Path(args.b1).with_suffix(".npz"))
    rows = res["rows"]; L = arr["acts_answer"].shape[1]
    fam = np.array([r["family"] for r in rows]); tpl = np.array([r["template"] for r in rows])
    rival = np.array([r["final_rival_index"] for r in rows], float)
    own = np.array([r["own_price_index"] for r in rows], float)
    E = np.array([r["expected_index"] for r in rows], float)
    rng = np.random.default_rng(0)
    v1, v2 = tpl == "v1", tpl == "v2"
    report = {"n_rows": len(rows), "n_layers": L, "probe": {}, "behaviour": {}}

    # behaviour on B1: does the model's expected price track the rival price?
    for t, m in (("v1", v1), ("v2", v2)):
        if m.any():
            report["behaviour"][t] = {"corr_E_rival": float(np.corrcoef(E[m], rival[m])[0, 1]),
                                      "corr_E_own": float(np.corrcoef(E[m], own[m])[0, 1]),
                                      "slope_E_on_rival": float(np.polyfit(rival[m], E[m], 1)[0]),
                                      "mean_E": float(E[m].mean())}
    sites = [s for s in ("answer", "rival", "pre_rival", "pre_final_round") if f"acts_{s}" in arr.files]
    for site in sites:
        X = arr[f"acts_{site}"].astype(np.float32)
        rec = {"rival_r2": [], "rival_r2_shuffled": [], "own_r2": [], "E_r2": [], "transfer_v1_to_v2": [], "transfer_v2_to_v1": [],
               "transfer_v1_to_v2_r": [], "transfer_v2_to_v1_r": []}
        for l in range(L):
            Xl = X[:, l, :]
            rec["rival_r2"].append(probe_cv(Xl[v1], rival[v1], fam[v1]))
            rec["rival_r2_shuffled"].append(probe_cv(Xl[v1], rival[v1], fam[v1], rng, shuffle=True))
            rec["own_r2"].append(probe_cv(Xl[v1], own[v1], fam[v1]))
            rec["E_r2"].append(probe_cv(Xl[v1], E[v1], fam[v1]) if E[v1].std() > 1e-6 else None)
            if v2.any():
                for a, b, key in ((v1, v2, "v1_to_v2"), (v2, v1, "v2_to_v1")):
                    r2, r = transfer(Xl[a], rival[a], Xl[b], rival[b])
                    rec[f"transfer_{key}"].append(r2); rec[f"transfer_{key}_r"].append(r)
        report["probe"][site] = rec
        print(site, "rival R2 by layer:", np.round(rec["rival_r2"], 2).tolist(), flush=True)

    ans = np.array(report["probe"]["answer"]["rival_r2"])
    steer_layer = int(1 + np.argmax(ans[1:L - 1]))
    report["steering_layer_rule"] = "argmax_{1<=l<=L-2} answer-site leave-family-out R^2 (template v1)"
    report["steering_layer"] = steer_layer

    # geometry at the steering layer, answer site, template v1
    Xs = arr["acts_answer"][v1][:, steer_layer, :].astype(np.float32)
    Xc = Xs - Xs.mean(0)
    pca = PCA(n_components=10).fit(Xc)
    ev = pca.explained_variance_
    pr = float(ev.sum() ** 2 / (ev ** 2).sum())
    pcs = pca.transform(Xc)
    # remove own-price and family means to isolate rival-price variation
    resid = Xc.copy()
    for key in (own[v1], fam[v1]):
        for k in np.unique(key):
            resid[key == k] -= resid[key == k].mean(0)
    pca_r = PCA(n_components=5).fit(resid)
    pcs_r = pca_r.transform(resid)
    report["geometry"] = {
        "layer": steer_layer, "explained_variance_ratio_top10": pca.explained_variance_ratio_.tolist(),
        "participation_ratio_top10": pr,
        "corr_pc_rival": [float(np.corrcoef(pcs[:, i], rival[v1])[0, 1]) for i in range(5)],
        "residualized_explained_variance_ratio_top5": pca_r.explained_variance_ratio_.tolist(),
        "residualized_corr_pc_rival": [float(np.corrcoef(pcs_r[:, i], rival[v1])[0, 1]) for i in range(5)],
    }
    # class means by rival index (for trajectory plot)
    means = np.stack([resid[rival[v1] == k].mean(0) for k in range(10)])
    traj = pca_r.transform(means)[:, :2]

    # steering directions (B1 only, template v1)
    dirs = {}
    for site in ("answer", "rival"):
        A = arr[f"acts_{site}"][v1][:, steer_layer, :].astype(np.float32)
        hi, lo = rival[v1] >= 7, rival[v1] <= 2
        dirs[f"rival_{site}"] = A[hi].mean(0) - A[lo].mean(0)
        dirs[f"own_{site}"] = A[own[v1] == 7].mean(0) - A[own[v1] == 1].mean(0)
        g = np.random.default_rng(1)
        for s in range(3):
            dirs[f"random{s}_{site}"] = g.standard_normal(A.shape[1]).astype(np.float32)
    np.savez(out / "directions.npz", **dirs)
    report["direction_cosines"] = {
        site: {"rival_vs_own": float(np.dot(dirs[f"rival_{site}"], dirs[f"own_{site}"]) /
                                     (np.linalg.norm(dirs[f"rival_{site}"]) * np.linalg.norm(dirs[f"own_{site}"])))}
        for site in ("answer", "rival")}
    (out / "probes.json").write_text(json.dumps(report, indent=1))

    # figures
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.titlelocation": "left"})
    C = {"answer": "#2a6fdb", "rival": "#e07b39", "pre_rival": "#3a9d5d", "pre_final_round": "#9aa0a6"}
    LBL = {"answer": "answer token", "rival": "rival-price tokens", "pre_rival": "token before rival price (sees profit)",
           "pre_final_round": "start of final round (null site)"}
    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    for site, rec in report["probe"].items():
        ax.plot(range(L), np.clip(rec["rival_r2"], -0.5, None), color=C[site], lw=2, label=LBL[site])
    ax.plot(range(L), report["probe"]["answer"]["rival_r2_shuffled"], color="#555", ls=":", lw=1.5, label="answer token, shuffled labels")
    ax.axvline(steer_layer, color="#c44e52", lw=1, ls="--"); ax.text(steer_layer + 0.2, -0.45, "steering layer", color="#c44e52", fontsize=8)
    ax.set_ylim(-0.52, 1.05); ax.set_xlabel("Layer"); ax.set_ylabel("Held-out R\u00b2 (rival's last price)\n(clipped at -0.5)")
    ax.set_title("Where the rival's price is linearly decodable"); ax.legend(frameon=False, fontsize=7.5, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout(); fig.savefig(out / "fig4_probe_by_layer.png", dpi=200); plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.8))
    sc = axs[0].scatter(pcs_r[:, 0], pcs_r[:, 1], c=rival[v1], cmap="viridis", s=18)
    axs[0].plot(traj[:, 0], traj[:, 1], color="black", lw=1.2, marker="o", ms=3)
    axs[0].set_xlabel("PC1"); axs[0].set_ylabel("PC2"); axs[0].set_title(f"Answer token, layer {steer_layer}")
    fig.colorbar(sc, ax=axs[0], label="rival's last price (index)")
    axs[1].bar(range(1, 6), pca_r.explained_variance_ratio_, color="#2a6fdb")
    axs[1].set_xlabel("PC (after removing own-price and family means)"); axs[1].set_ylabel("Variance explained")
    axs[1].set_title("Spectrum")
    fig.tight_layout(); fig.savefig(out / "fig5_geometry.png", dpi=200); plt.close(fig)

    if v2.any():
        fig, ax = plt.subplots(figsize=(7, 3.6))
        for site in ("answer", "rival"):
            ax.plot(range(L), report["probe"][site]["rival_r2"], color=C[site], lw=2, label=f"{site}: v1 held-out family")
            r = np.array(report["probe"][site]["transfer_v1_to_v2_r"]); ax.plot(range(L), np.sign(r) * r ** 2, color=C[site], lw=1.5, ls="--", label=f"{site}: train v1 \u2192 test v2 (signed r\u00b2)")
        ax.set_ylim(-0.2, 1.05); ax.set_xlabel("Layer"); ax.set_ylabel("Held-out fit (rival's last price)")
        ax.set_title("Generalization across histories and prompt templates"); ax.legend(frameon=False, fontsize=8)
        fig.tight_layout(); fig.savefig(out / "fig6_generalization.png", dpi=200); plt.close(fig)
    print(json.dumps({k: report[k] for k in ("behaviour", "steering_layer", "geometry", "direction_cosines")}, indent=1))


if __name__ == "__main__":
    main()
