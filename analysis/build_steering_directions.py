"""Steering directions used for the Qwen2.5-7B C2 runs (all built on B1, template v1 only).

layer 3 answer/rival: from analysis/phase_b_probes.py (predeclared rule) -> directions.npz
layer 13 / 21 answer, layer 8 rival: mean differences below. Layers 21 (answer) and 8 (rival)
were chosen after the C1 patching map (Fig 9), which used the same A.1 controls that C2 evaluates on:
treat those runs as exploratory.
  deviation = mean(|final - extrapolated| >= 4) - mean(<= 1)
  rival     = mean(final rival >= 7) - mean(<= 2)
  own       = mean(own == 7) - mean(own == 1)
  action    = mean(model E in top third) - mean(bottom third)        [layer 21 controls run]
  deviation_perp_action = deviation with its projection on action removed
  random*   = standard normal (seeded)
"""
import json, sys
import numpy as np

P = {"flat_3": (3, 3, 3), "flat_5": (5, 5, 5), "rise_0": (0, 2, 4), "fall_9": (9, 7, 5), "rise_4": (4, 6, 8), "fall_6": (6, 4, 2)}


def build(b1_json, b1_npz, site, layer, out, seed=2, with_action=False):
    rows = json.load(open(b1_json))["rows"]; arr = np.load(b1_npz)
    pred = np.array([np.clip(P[r["family"]][-1] + (P[r["family"]][-1] - P[r["family"]][-2]), 0, 9) for r in rows])
    fin = np.array([r["final_rival_index"] for r in rows]); dev = np.abs(fin - pred)
    own = np.array([r["own_price_index"] for r in rows]); E = np.array([r["expected_index"] for r in rows])
    v1 = np.array([r["template"] == "v1" for r in rows])
    A = arr[f"acts_{site}"][:, layer, :].astype(np.float32)
    d = {f"deviation_{site}": A[v1 & (dev >= 4)].mean(0) - A[v1 & (dev <= 1)].mean(0)}
    if with_action:
        hi, lo = np.quantile(E[v1], [2 / 3, 1 / 3])
        act = A[v1 & (E >= hi)].mean(0) - A[v1 & (E <= lo)].mean(0)
        u = act / np.linalg.norm(act)
        d[f"action_{site}"] = act
        d[f"deviation_perp_action_{site}"] = d[f"deviation_{site}"] - (d[f"deviation_{site}"] @ u) * u
    else:
        d[f"rival_{site}"] = A[v1 & (fin >= 7)].mean(0) - A[v1 & (fin <= 2)].mean(0)
        d[f"own_{site}"] = A[v1 & (own == 7)].mean(0) - A[v1 & (own == 1)].mean(0)
    g = np.random.default_rng(seed)
    for s in range(2 if with_action else 3):
        d[f"random{s}_{site}"] = g.standard_normal(A.shape[1]).astype(np.float32)
    np.savez(out, **d)


if __name__ == "__main__":
    b1j, b1n = sys.argv[1], sys.argv[2]
    build(b1j, b1n, "answer", 13, "dirs_layer13_answer.npz", seed=1)
    build(b1j, b1n, "answer", 21, "dirs_layer21_answer.npz")
    build(b1j, b1n, "rival", 8, "dirs_layer8_rival.npz")
    build(b1j, b1n, "answer", 21, "dirs_layer21_answer_controls.npz", seed=3, with_action=True)
