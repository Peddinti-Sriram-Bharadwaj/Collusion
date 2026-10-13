import json
from src.llm_agent import run_llm_episode

HOMOGENEOUS = [
    "capitalist",
    "socialist",
    "for_profit",
    "nonprofit",
    "rnd_oriented",
    "consumer_empathetic",
    "hoarder",
]

CONDITIONS = {f"homog_{p}": dict(personas=[p, p]) for p in HOMOGENEOUS}
CONDITIONS["mixed_capitalist_vs_socialist"] = dict(personas=["capitalist", "socialist"])
CONDITIONS["mixed_hoarder_vs_consumer_empathetic"] = dict(personas=["hoarder", "consumer_empathetic"])

N_SEEDS = 5

for name, kwargs in CONDITIONS.items():
    out_path = f"results/track_personas_{name}.jsonl"
    with open(out_path, "a") as f:
        for seed in range(N_SEEDS):
            r = run_llm_episode(n_agents=2, n_prices=10, n_rounds=30, seed=seed * 100, **kwargs)
            row = {
                "seed": seed,
                "delta": r["delta"],
                "avg_profit": r["avg_profit"],
                "n_parse_failures": r["n_parse_failures"],
                "p_nash": r["p_nash"],
                "p_monop": r["p_monop"],
            }
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(f"[{name}] seed={seed} delta={r['delta']:.4f} parse_failures={r['n_parse_failures']}", flush=True)
print("DONE")
