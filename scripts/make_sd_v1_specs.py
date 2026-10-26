"""Generate the Stage B (primary) and Stage C (one-factor) specs for strategic_deviation_v1.

History seeds are the first N seeds whose pre-play own-price prefix is (a) distinct from every other selected
prefix and (b) not a contiguous sub-history of any steering-vector training history (protocol amendment A1).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from src.interpretability.phase_a1 import build_phase_a1_rows  # noqa: E402
from src.research.economics import ECON_PRESETS, env_for  # noqa: E402

VEC = "learned_answer_L20_c3d"
_train_ids = set(json.loads((ROOT / f"research/vectors/{VEC}.json").read_text())["training_histories"])
TRAIN = {tuple(map(tuple, r.action_indices)) for r in build_phase_a1_rows(env_for(ECON_PRESETS["base"])) if r.control_id in _train_ids}


def prefix(seed, n, lo, hi):
    g = np.random.default_rng(seed); return tuple(int(g.integers(lo, hi + 1)) for _ in range(n))


def pick_seeds(k, n_rounds=4, lo=4, hi=8, high=7):
    out, seen, s = [], set(), 0
    while len(out) < k:
        p = prefix(s, n_rounds, lo, hi); h = tuple((high, o) for o in p)
        leak = any(t[i:i + len(h)] == h for t in TRAIN for i in range(len(t) - len(h) + 1))
        if p not in seen and not leak:
            out.append(s); seen.add(p)
        s += 1
    return out


def st(kind, alpha=0.0, seed=0, timing="all", vid=VEC):
    s = {"kind": kind}
    if kind != "none":
        s.update(vector_id=vid, alpha=alpha, random_seed=seed, timing=timing)
    return {"steering": s}


H16 = pick_seeds(16)
STEER = ([st("none"), st("sham", 1.0)] + [st("learned", a) for a in (-1.0, 1.0, 2.0)]
         + [st("random", a, s) for a in (1.0, 2.0) for s in (0, 1, 2)]
         + [st("generic_price", 1.0, vid="generic_price_answer_L20_b1"), st("learned", 1.0, timing="post_deviation")])
BASE = {"design": {"rounds": 16, "deviation_round": 7, "high": 7, "low": 2, "recovery_delay": 3, "raise_to": 9},
        "audit_generation": "deviation_window"}
primary = {"batch_id": "sd_v1_primary_7b_001", "protocol": "strategic_deviation_v1", "designation": "confirmatory", "model": "7b",
           "description": "Stage B primary: H1-H5 on Qwen2.5-7B, 16 distinct histories, greedy, v1 template, base economics.",
           "history_seeds": H16, "base": BASE,
           "blocks": [
               {"name": "primary", "grid": {"condition": ["A_stable", "B_one_shot", "C_persistent", "D_gradual", "E_nash", "F_delayed", "G_raise"],
                                            "seeds.history_seed": H16, "steering_preset": STEER}},
               {"name": "fixed_history", "overrides": {"experiment": "fixed_history"},
                "grid": {"condition": ["H_sudden", "H_gradual", "H_always_low", "H_stable_high"], "seeds.history_seed": H16,
                         "steering_preset": [st("none"), st("learned", 1.0), st("random", 1.0, 0)]}},
               {"name": "repeatability", "grid": {"condition": ["A_stable", "B_one_shot"], "seeds.history_seed": H16[:4], "replicate": [1]}}]}

H8 = H16[:8]; C3 = ["A_stable", "B_one_shot", "C_persistent"]
blocks = []
for t in ["v1_implicit_horizon", "v2_log", "v3_system", "v4_history_first"]:
    blocks.append({"name": "sweep:template_id", "overrides": {"template_id": t}, "grid": {"condition": C3, "seeds.history_seed": H8}})
for T in (0.3, 0.7, 1.0):
    blocks.append({"name": "sweep:temperature", "overrides": {"decoding": {"mode": "sample", "temperature": T}},
                   "grid": {"condition": C3, "seeds.history_seed": H8[:4], "seeds.model_seed": [0, 1, 2, 3]}})
for low in (1, 3, 4):
    blocks.append({"name": "sweep:deviation_magnitude", "overrides": {"design": {"low": low}}, "grid": {"condition": C3, "seeds.history_seed": H8}})
for p in (2, 8):
    blocks.append({"name": "sweep:prefix_rounds", "overrides": {"prefix_rounds": p}, "grid": {"condition": C3, "seeds.history_seed": pick_seeds(8, p)}})
for d in (1, 2, 5):
    blocks.append({"name": "sweep:recovery_delay", "overrides": {"design": {"recovery_delay": d}}, "grid": {"condition": ["A_stable", "F_delayed"], "seeds.history_seed": H8}})
for e in ("low_mu", "high_mu", "high_cost"):
    blocks.append({"name": "sweep:econ_id", "overrides": {"econ_id": e}, "grid": {"condition": C3, "seeds.history_seed": H8}})
# grid8: 8 prices, Nash index 1, monopoly index 5 -> design scaled to the grid (high = monopoly, low = Nash)
g8 = pick_seeds(8, 4, 2, 6, high=5)
blocks.append({"name": "sweep:econ_id", "overrides": {"econ_id": "grid8", "prefix_own_range": [2, 6],
                                                      "design": {"high": 5, "low": 1, "raise_to": 7}},
               "grid": {"condition": C3, "seeds.history_seed": g8}})
blocks.append({"name": "sweep:window", "overrides": {"window": 5}, "grid": {"condition": C3, "seeds.history_seed": H8}})
blocks.append({"name": "sweep:alpha", "grid": {"condition": ["A_stable", "B_one_shot"], "seeds.history_seed": H8,
                                               "steering_preset": [st("learned", a) for a in (-2.0, -0.5, 0.5, 1.5)] + [st("random", a, 0) for a in (-2.0, -0.5, 0.5, 1.5)]}})
onefactor = {"batch_id": "sd_v1_onefactor_7b_001", "protocol": "strategic_deviation_v1", "designation": "exploratory", "model": "7b",
             "description": "Stage C one-factor robustness: each factor varied alone from the primary settings.",
             "base": BASE, "blocks": blocks}
for spec in (primary, onefactor):
    (ROOT / "research/configs" / f"{spec['batch_id']}.json").write_text(json.dumps(spec, indent=1))
print("H16", H16)
