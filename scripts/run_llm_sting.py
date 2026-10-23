import json
from src.llm_agent import run_llm_sting_episode

N_SEEDS = 8
N_ROUNDS = 20
OFFER_ROUND = 5

out_path = "results/track_sting_open.jsonl"
with open(out_path, "a") as f:
    for seed in range(N_SEEDS):
        r = run_llm_sting_episode(n_prices=10, n_rounds=N_ROUNDS, offer_round=OFFER_ROUND, seed=seed * 100)
        row = {
            "seed": seed,
            "delta": r["delta"],
            "mean_gap_to_target": r["mean_gap_to_target"],
            "response_classifications": r["response_classifications"],
            "raw_message_log": r["raw_message_log"],
            "n_parse_failures": r["n_parse_failures"],
            "p_nash": r["p_nash"],
            "p_monop": r["p_monop"],
        }
        f.write(json.dumps(row) + "\n")
        f.flush()
        post_offer = r["response_classifications"][OFFER_ROUND:]
        accepted = post_offer.count("accepted")
        suspicious = post_offer.count("suspicious")
        print(
            f"[sting] seed={seed} delta={r['delta']:.4f} gap={r['mean_gap_to_target']:.4f} "
            f"accepted={accepted}/{len(post_offer)} suspicious={suspicious}/{len(post_offer)} "
            f"parse_failures={r['n_parse_failures']}",
            flush=True,
        )
print("DONE")
