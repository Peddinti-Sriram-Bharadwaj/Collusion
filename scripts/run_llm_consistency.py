import json
from src.llm_agent import run_llm_messaging_episode

# RQ 2.2-style word/action consistency check: does an agent's own suggested
# price in its message match the price it (or its rival) actually sets next
# round? Reuses the open-messages condition from RQ 3.1, this time also
# persisting price_history so the say-do comparison can be computed.
N_SEEDS = 5
N_ROUNDS = 25

out_path = "results/track_consistency_open_messages.jsonl"
with open(out_path, "a") as f:
    for seed in range(N_SEEDS):
        r = run_llm_messaging_episode(n_agents=2, n_prices=10, n_rounds=N_ROUNDS, monitor=False, seed=seed * 100)
        row = {
            "seed": seed,
            "delta": r["delta"],
            "n_parse_failures": r["n_parse_failures"],
            "n_collusive_attempts": r["n_collusive_attempts"],
            "raw_message_log": r["raw_message_log"],
            "price_history": r["price_history"].tolist(),
            "p_nash": r["p_nash"],
            "p_monop": r["p_monop"],
        }
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(f"[consistency] seed={seed} delta={r['delta']:.4f} parse_failures={r['n_parse_failures']}", flush=True)
print("DONE")
