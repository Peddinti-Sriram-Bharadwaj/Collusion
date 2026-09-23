import json
from src.llm_agent import run_llm_episode

out_path = "results/track_llm_spotcheck_seeds5to14.jsonl"
with open(out_path, "a") as f:
    for seed in range(5, 15):
        r = run_llm_episode(n_agents=2, n_prices=10, n_rounds=30, seed=seed * 100)
        row = {
            "seed": seed,
            "delta": r["delta"],
            "n_parse_failures": r["n_parse_failures"],
            "p_nash": r["p_nash"],
            "p_monop": r["p_monop"],
        }
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(f"seed={seed} delta={r['delta']:.4f} parse_failures={r['n_parse_failures']}", flush=True)
print("DONE")
