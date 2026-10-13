import json
from src.llm_agent import run_llm_episode

CONDITIONS = {
    "warning_only": dict(warning=True),
    "hard_veto": dict(veto=True, veto_margin_fraction=0.3),
}

for name, kwargs in CONDITIONS.items():
    out_path = f"results/track_rq32_{name}.jsonl"
    with open(out_path, "a") as f:
        for seed in range(10):
            r = run_llm_episode(n_agents=2, n_prices=10, n_rounds=30, seed=seed * 100, **kwargs)
            row = {
                "seed": seed,
                "delta": r["delta"],
                "n_parse_failures": r["n_parse_failures"],
                "n_vetoes": r.get("n_vetoes", 0),
                "p_nash": r["p_nash"],
                "p_monop": r["p_monop"],
            }
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(f"[{name}] seed={seed} delta={r['delta']:.4f} vetoes={r.get('n_vetoes', 0)} parse_failures={r['n_parse_failures']}", flush=True)
print("DONE")
