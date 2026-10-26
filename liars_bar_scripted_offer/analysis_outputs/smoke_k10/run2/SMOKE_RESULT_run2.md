# K = 10 smoke test, run 2, 2026-10-25: PASSED

Disclosure: this is sprint work. These 14 games are a smoke test only. They are never pooled with the pilots or the main run.

## Setup
- **Games.** 2 game numbers (g = 0, 1) × 7 conditions = 14 games, 10 workers (`run_scripted_offer.py --games 2 --workers 10`).
- **Script and log.** `../run_smoke.sh`, log in `../run2_smoke.log`.
- **Records.** `collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar/experiments/game_records/scripted_offer_smoke_k10_run2`.
- **Code.** Branch `scripted-offer`, commit `12060a2fde664a0513d5b35493d4ac857ad9dd50`. The diff and status are in `code_snapshot.patch` and `code_status.txt`.
- **Prompts.** The verbatim templates are in `prompts_verbatim/`.
- **Router.** PID 15348, started 11:46:13 UTC. Log: `results/router_logs/router_20261025T114613Z.jsonl`.

## Timeline (UTC)
- **11:51:49** Start. All three apps deployed (L40S, `@modal.concurrent(max_inputs=32)`, `max_containers=1`).
- **Identity check.** All three models match pilot 2 (`modal_identity_smoke.json`).
- **11:54:10** Warm-up done. All three backends answered 200 through the router, in 44–57 s.
- **11:54:10–12:03:46** The 14 games ran, 9 min 36 s of wall time. **All 14 ended `ok` on their first attempt.**
- **12:03:46** The trap stopped every app.
- **12:04:23** Independent check:
  - `modal app list --json`: all 7 apps `stopped`, 0 tasks.
  - `modal container list --json`: `[]`.

## Results

| Measure | Smoke K = 10 | Pilot 2 (serial) |
|---|---|---|
| LLM calls | 1,642, all HTTP 200 (0 errors) | 3,840 |
| Mean call latency | 2.34 s (median 2.16, p95 3.97, max 6.69) | 2.40 s (9,225 s / 3,840) |
| Mean game time | 290 s | 309 s |
| Wall time, 14 games | 576 s | about 4,300 s at 309 s per game |

- **Latency by model.**
  - Llama-3.2-3B: 1.78 s (700 calls).
  - Qwen2.5-7B: 2.70 s (652 calls).
  - Llama-3.1-8B: 2.88 s (290 calls).
- **Batching slowdown s ≈ 1.0.** It is the mean call latency here divided by pilot 2's: 2.34 / 2.40 = 0.97. Batching did not measurably slow down individual calls.
- **Concurrency.** Reconstructed from the router log as start = ts − latency.
  - Up to 10 requests were in flight at once, 6.65 on average.
  - The 14 games took 4,064 s of total game time in 576 s of wall time, a 7.1× speedup.
- **GPU containers.** This is the PREREG check, and it **passed: exactly 3 throughout the games**. Source: `container_monitor.log`, one snapshot every ~35 s.
  - From the first in-game snapshot (11:54:57) to the last (12:03:23), there were exactly 3 containers, one per model. These are the same 3 container IDs that started at warm-up.
  - The 6 containers seen at 11:53:13–11:54:21 were the 3 CPU identity-check containers (started 20:52 KST) next to the 3 GPU containers that were starting. The identity containers were gone before the first in-game snapshot.
- **Cost (estimate, not billed yet).**
  - 3 L40S × about 12 min of deployment (20:51–21:04 KST) × $1.95/h × 1.04 ≈ **$1.2**.
  - Billing can lag, so check `modal billing report` later.

## Implication for the main run (not a change to PREREG)
- With s ≈ 1.0 and K = 10, 210 games take about 21 waves × ~300 s ≈ 1.8 h. Most game numbers end faster, so the real time may be shorter.
- That works out to about 1.8 h × 3 × $1.95 × 1.04 ≈ $11, plus warm-up. This is within the PREREG estimate of 2.4 h and $15–18.
- PREREG Amendment 12 says the smoke result "is recorded here". That entry has not been added. It needs the user's approval.
