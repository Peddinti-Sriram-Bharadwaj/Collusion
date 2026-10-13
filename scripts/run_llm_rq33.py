import json
from src.llm_agent import run_llm_episode

SAME = ["qwen2.5:7b-instruct", "qwen2.5:7b-instruct"]
DIFF = ["qwen2.5:7b-instruct", "qwen2.5:0.5b-instruct"]

CONDITIONS = {
    "same_actual_told_same": dict(models=SAME, peer_info="same"),
    "diff_actual_told_diff": dict(models=DIFF, peer_info="different"),
    "diff_actual_no_info": dict(models=DIFF, peer_info=None),
}

for name, kwargs in CONDITIONS.items():
    out_path = f"results/track_rq33_{name}.jsonl"
    with open(out_path, "a") as f:
        for seed in range(10):
            r = run_llm_episode(n_agents=2, n_prices=10, n_rounds=30, seed=seed * 100, **kwargs)
            row = {
                "seed": seed,
                "delta": r["delta"],
                "n_parse_failures": r["n_parse_failures"],
                "p_nash": r["p_nash"],
                "p_monop": r["p_monop"],
            }
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(f"[{name}] seed={seed} delta={r['delta']:.4f} parse_failures={r['n_parse_failures']}", flush=True)
print("DONE")
