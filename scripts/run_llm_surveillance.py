import json
from src.llm_agent import run_llm_messaging_episode

CONDITIONS = {
    "surveillance_aware_open_messages": dict(monitor=False, surveillance=True),
}

N_SEEDS = 5
N_ROUNDS = 25

for name, kwargs in CONDITIONS.items():
    out_path = f"results/track_surveillance_{name}.jsonl"
    with open(out_path, "a") as f:
        for seed in range(N_SEEDS):
            r = run_llm_messaging_episode(n_agents=2, n_prices=10, n_rounds=N_ROUNDS, seed=seed * 100, **kwargs)
            row = {
                "seed": seed,
                "delta": r["delta"],
                "n_parse_failures": r["n_parse_failures"],
                "n_collusive_attempts": r["n_collusive_attempts"],
                "raw_message_log": r["raw_message_log"],
                "delivered_message_log": r["delivered_message_log"],
                "p_nash": r["p_nash"],
                "p_monop": r["p_monop"],
            }
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(
                f"[{name}] seed={seed} delta={r['delta']:.4f} "
                f"collusive_attempts={r['n_collusive_attempts']} parse_failures={r['n_parse_failures']}",
                flush=True,
            )
print("DONE")
