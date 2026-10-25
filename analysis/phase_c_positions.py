"""Fig: position x layer patching map (fraction of edit effect recovered by patching one position)."""
from __future__ import annotations

import argparse, json
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--c1pos", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    d = json.load(open(a.c1pos)); res = [r for r in d["results"] if "skipped" not in r]
    n_pos = min(len(r["positions"]) for r in res)
    layers = res[0]["layers"]
    total = np.array([r["E_donor"] - r["E_control"] for r in res])
    eff = np.array([np.array(r["E_patched"])[:, :n_pos] - r["E_control"] for r in res])  # [pairs, layers, pos]
    frac = (eff * total[:, None, None]).sum(0) / (total ** 2).sum()
    tokens = res[0]["tokens"][:n_pos]
    top = {}
    for li, l in enumerate(layers):
        order = np.argsort(-frac[li])[:6]
        top[str(l)] = [{"offset": int(j), "token": tokens[j], "fraction": float(frac[li, j])} for j in order]
    rep = {"n_pairs": len(res), "layers": layers, "tokens": tokens, "fraction": frac.tolist(), "top_positions": top,
           "sum_over_positions": frac.sum(1).tolist()}
    (out / "c1pos_summary.json").write_text(json.dumps(rep, indent=1))
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 3.2))
    im = ax.imshow(frac, aspect="auto", cmap="Blues", vmin=0, vmax=max(0.05, float(frac.max())))
    ax.set_yticks(range(len(layers)), [f"layer {l}" for l in layers])
    lab = [t.replace("\n", "\\n") for t in tokens]
    ax.set_xticks(range(n_pos), lab, rotation=90, fontsize=6)
    ax.set_xlabel("Token position (from the rival's final price to the answer)")
    fig.colorbar(im, ax=ax, label="fraction of effect recovered", pad=0.01)
    ax.set_title("Which single position carries the rival-price edit, layer by layer", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(out / "fig10_position_patching_7b.png", dpi=200); plt.close(fig)
    print(json.dumps({"sum_over_positions": rep["sum_over_positions"], "top": top}, indent=1))


if __name__ == "__main__":
    main()
