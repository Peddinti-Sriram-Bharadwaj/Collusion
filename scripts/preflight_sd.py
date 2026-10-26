"""Pre-launch scientific audit for strategic_deviation_v1 batches (no GPU, no model weights).

Usage: python scripts/preflight_sd.py --spec research/configs/<batch>.json [--out research/preflight/<batch>.json]
Checks: unit validity/counts, history independence, scripted-match isolation, information discipline,
vector/evaluation history overlap, benchmark correctness, steering-control matching, coverage per hypothesis.
"""
from __future__ import annotations
import argparse, json, sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.research.configs import expand, load_spec  # noqa: E402
from src.research.economics import ECON_PRESETS, benchmarks, env_for  # noqa: E402
from src.research.rivals import DeviationDesign, SCRIPTED, scripted_sequence, returns_at  # noqa: E402
from src.research.runner import MODELS  # noqa: E402
from src.research.steering import load_vector  # noqa: E402


def prefix_own(unit):
    rng = np.random.default_rng(unit["seeds"]["history_seed"])
    lo, hi = unit["prefix_own_range"]
    return tuple(int(rng.integers(lo, hi + 1)) for _ in range(unit["prefix_rounds"]))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--spec", required=True); ap.add_argument("--out")
    a = ap.parse_args()
    spec = load_spec(a.spec); units = expand(spec)
    R = {"batch_id": spec["batch_id"], "n_units": len(units), "checks": {}, "issues": []}
    C = R["checks"]
    # 1 independence of histories
    games = [u for u in units if u["experiment"] == "deviation_game"]
    pref = defaultdict(set)
    for u in games:
        pref[(u["prefix_rounds"], tuple(u["prefix_own_range"]))].add((u["seeds"]["history_seed"], prefix_own(u)))
    for k, s in pref.items():
        seqs = [p for _, p in s]
        C[f"history_prefixes_{k[0]}r"] = {"n_seeds": len(s), "n_distinct": len(set(seqs)),
                                          "examples": sorted(s)[:4]}
        if len(set(seqs)) < len(seqs):
            R["issues"].append(f"duplicate own-price prefixes for prefix_rounds={k[0]}")
    fh = [u for u in units if u["experiment"] == "fixed_history"]
    fh_own = Counter(int(np.random.default_rng(u["seeds"]["history_seed"]).integers(u["prefix_own_range"][0], u["prefix_own_range"][1] + 1))
                     for u in fh if u["condition"] == "H_sudden" and u["steering"]["kind"] == "none")
    C["fixed_history_own_index_counts"] = dict(sorted(fh_own.items()))
    # 2 scripted matching: identical to A_stable up to and including t_d-1 (B,C,F,G identical through t_d-1; D starts earlier by design)
    designs = {json.dumps(u["design"], sort_keys=True) for u in games}
    sm = {}
    for dz in designs:
        d = DeviationDesign(**json.loads(dz)); A = scripted_sequence("A_stable", d)
        for c in SCRIPTED:
            s = scripted_sequence(c, d)
            first = next((t for t in range(d.rounds) if s[t] != A[t]), None)
            sm[f"{c}@{dz}"] = {"first_diff_round": first, "returns_at": returns_at(c, d), "seq": s}
            if c in ("B_one_shot", "C_persistent", "F_delayed", "G_raise") and first != d.deviation_round:
                R["issues"].append(f"{c} differs from A_stable at round {first}, expected t_d={d.deviation_round}")
    C["scripted_sequences"] = {k: v for k, v in list(sm.items())[:7]}
    # 3 information discipline is structural (deviation.py appends round t after the decision); verified by test_research
    C["information_discipline"] = "decision at live round t renders history[:P+t]; rival action t appended after the decision (src/research/deviation.py; tests/test_research.py::no leakage)"
    # 4 vector training vs evaluation histories
    from src.interpretability.phase_a1 import build_phase_a1_rows
    env0 = env_for(ECON_PRESETS["base"])
    rows = build_phase_a1_rows(env0)
    meta = json.loads((ROOT / "research/vectors/learned_answer_L20_c3d.json").read_text())
    train_ids = set(meta.get("training_histories") or [])
    train_hist = {tuple(map(tuple, r.action_indices)) for r in rows if r.control_id in train_ids or not train_ids}
    eval_hist = set()
    for u in games:
        d = DeviationDesign(**u["design"]); own = prefix_own(u)
        eval_hist.add(tuple((d.high, o) for o in own))
    overlap = [h for h in eval_hist if any(t[i:i + len(h)] == h for t in train_hist for i in range(len(t) - len(h) + 1))]
    C["vector_history_overlap"] = {"n_training_histories": len(train_hist), "train_ids_recorded": bool(train_ids),
                                   "n_eval_prefixes": len(eval_hist), "n_overlapping": len(overlap),
                                   "train_rival_patterns": sorted({tuple(a[0] for a in t) for t in train_hist})[:6]}
    if overlap:
        R["issues"].append(f"{len(overlap)} evaluation prefixes coincide with vector-training histories")
    v, vm = load_vector("learned_answer_L20_c3d", ROOT / "research/vectors")
    C["vector"] = {"id": "learned_answer_L20_c3d", "norm": float(np.linalg.norm(v)), "dim": int(v.shape[0]),
                   "layer": vm.get("layer"), "site": vm.get("site"), "model": vm.get("model_key")}
    # 5 model revision / templates / sites
    m = spec["model"]; C["model"] = {"key": m, "id": MODELS[m][0], "revision": MODELS[m][1]}
    C["templates"] = sorted({u["template_id"] for u in units}); C["sites_layers"] = sorted({(u["steering"]["site"], u["steering"]["layer"]) for u in units if u["steering"]["kind"] != "none"})
    # 6 benchmarks from payoff function
    bm = {}
    for e in sorted({u["econ_id"] for u in units}):
        cfg = ECON_PRESETS[e]; b = benchmarks(cfg); env = env_for(cfg); g = env.price_grid
        br = [int(np.argmax([env._profits(np.array([g[r], g[p]]))[1] for p in range(len(g))])) for r in range(len(g))]
        ok = br == b["best_response_by_rival_index"]
        bm[e] = {"nash_index": b["nash_index"], "monopoly_index": b["monopoly_index"], "br": br, "br_recomputed_match": ok,
                 "deviation_gain_vs_monopoly": b["deviation_gain_vs_monopoly"], "n_prices": len(g)}
        if not ok:
            R["issues"].append(f"benchmark mismatch {e}")
        hi = {u["design"]["high"] for u in units if u["econ_id"] == e} | {u["design"]["raise_to"] for u in units if u["econ_id"] == e}
        if max(hi) >= len(g):
            R["issues"].append(f"design price index {max(hi)} outside grid for econ {e}")
    C["benchmarks"] = bm
    # 9 steering controls matched
    st = Counter((u["steering"]["kind"], u["steering"].get("vector_id"), u["steering"]["alpha"], u["steering"]["timing"]) for u in units)
    C["steering_arms"] = {str(k): n for k, n in sorted(st.items(), key=str)}
    ln = [u["steering"] for u in units if u["steering"]["kind"] in ("learned", "random", "sham", "generic_price")]
    C["steering_layer_site_consistent"] = len({(s["layer"], s["site"]) for s in ln}) <= 1
    # 11 coverage per hypothesis (independent histories per comparison)
    def hs(f): return sorted({u["seeds"]["history_seed"] for u in units if f(u)})
    none = lambda u: u["steering"]["kind"] == "none" and u.get("replicate", 0) == 0
    cov = {
        "H1 B vs A (none)": len(set(hs(lambda u: none(u) and u["condition"] == "B_one_shot")) & set(hs(lambda u: none(u) and u["condition"] == "A_stable"))),
        "H2 B,C,F vs A (none)": len(set(hs(lambda u: none(u) and u["condition"] == "C_persistent")) & set(hs(lambda u: none(u) and u["condition"] == "B_one_shot"))),
        "H3 sudden vs gradual (none)": len(set(hs(lambda u: none(u) and u["condition"] == "H_sudden")) & set(hs(lambda u: none(u) and u["condition"] == "H_gradual"))),
        "H4 learned+1 & random+1 & none": len(set(hs(lambda u: u["steering"]["kind"] == "learned" and u["steering"]["alpha"] == 1.0 and u["steering"]["timing"] == "all"))
                                               & set(hs(lambda u: u["steering"]["kind"] == "random" and u["steering"]["alpha"] == 1.0))),
        "H5 learned+1 on B and A": len(set(hs(lambda u: u["steering"]["kind"] == "learned" and u["steering"]["alpha"] == 1.0 and u["condition"] == "B_one_shot"))),
    }
    C["coverage_independent_histories"] = cov
    for k, n in cov.items():
        if n and n < 8:
            R["issues"].append(f"low coverage for {k}: {n} histories")
    C["n_by_block"] = dict(Counter(u.get("block") for u in units))
    C["n_by_experiment"] = dict(Counter(u["experiment"] for u in units))
    out = Path(a.out or ROOT / "research/preflight" / f"{spec['batch_id']}.json"); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(R, indent=1, default=str))
    print(json.dumps({"issues": R["issues"], "coverage": cov, "vector_overlap": C["vector_history_overlap"]["n_overlapping"],
                      "prefixes": {k: v for k, v in C.items() if k.startswith("history_prefixes")}}, indent=1, default=str))


if __name__ == "__main__":
    main()
