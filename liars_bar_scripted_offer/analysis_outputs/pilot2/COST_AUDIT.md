# Pilot 2: Modal cost audit and optimisation options

Date 2026-10-24. Nothing was launched or changed for this audit. All Modal calls were read-only (`modal billing report`, `modal billing rates`).

## Sources
- **Billing.** `modal billing report --start 2026-10-24T00:00Z --end 09:00Z --resolution h --show-resources --json`, saved as `modal_billing_by_resource_2026-10-24.json`.
  - The pilot-2 window is 03:00–07:00 UTC. The 01:00 rows belong to the earlier 5-game infrastructure pilot and are excluded.
- **Call timing.** `records/usage.jsonl`, one row per LLM call, with latency and tokens.
- **Game timing.** `records/run_log.jsonl`.
- **GPU rates.** L40S $1.95/h, A100-80GB $2.50/h, H100 $3.95/h, L4 $0.80/h, A10G $1.10/h.

## 1. Where the $15.61 went

Setup: 3 × L40S, one per model (Llama-3.1-8B, Llama-3.2-3B, Qwen2.5-7B). Ministral was not used and was never billed in the window.

| item | L40S-seconds | cost | share |
|---|---|---|---|
| Inference: a request in flight on that model's GPU | 9,225 | $5.00 | 32% |
| Idle: container up, waiting while another model answered | ≈18,300 | $9.91 | 63% |
| Cold starts (first request to ready: Qwen ≈65 s, Llama-3.1 ≈40 s, Llama-3.2 ≈38 s) | ≈143 | $0.08 | 0.5% |
| Unexplained second Qwen container | ≈48 | $0.03 | 0.2% |
| CPU (container) | – | $0.11 | 0.7% |
| Memory (container) | – | $0.48 | 3.1% |
| **Total** | **27,716 (7.70 GPU-h)** | **$15.61** | |

- **The unexplained Qwen container.** Qwen billed 3,648 L40S-seconds inside the single hour 04:00–05:00, so a second container overlapped for about 48 s.

Per model:

| model | billed L40S-s | busy (Σ call latency) | utilisation | calls | median latency | mean tokens per call (prompt / completion) |
|---|---|---|---|---|---|---|
| Llama-3.1-8B | 9,212 | 4,160 | 45% | 1,143 | 3.60 s | 1,231 / 108 |
| Llama-3.2-3B | 9,168 | 2,013 | 22% | 1,319 | 1.42 s | 1,245 / 80 |
| Qwen2.5-7B | 9,336 | 3,052 | 33% | 1,387 | 2.07 s | 1,244 / 70 |

**Findings**
- **Billing starts at the first request and ended exactly at `modal app stop`.** Containers started at about 03:52:24, 03:53:32 and 03:54:22 UTC, matching each model's first call. Billing ended at about 06:27 UTC. Nothing was billed after the run: the stop trap meant the 30-minute scale-down window never applied.
- **The run was strictly serial.** There were 0 overlapping calls, and 99.4% of game wall time was spent waiting for a model reply (Σ latency 9,225 s vs. Σ game time 9,281 s). So at most 1 of the 3 GPUs was working at any moment.
- **Even a "busy" GPU served a batch of 1.** vLLM on an L40S can batch dozens of 1.2k-token requests with little extra latency, so real compute utilisation was far below the 33% time-utilisation.
- **Cost scales only with wall time.** Each game costs about 3 GPUs × 309 s × $1.95/h ≈ $0.52. Cold starts and egress are negligible.

## 2. Options that keep the experimental conditions unchanged
"Unchanged" means the same models, pinned revisions, vLLM version, dtype, launch flags, sampling parameters, prompts and game mechanics.

### A. Run games in parallel. **Large saving, recommended.**
- **Idea.** Run K games at once from the same job list (same game numbers, same counterbalanced condition order), so the three servers batch requests from different games.
  - Wall time, and therefore cost, falls by about K / s, where s is the per-call slowdown from batching.
  - With K = 10, each model sees on average about 3–4 concurrent requests, at most 10. On an L40S, decode for 3–8B models is bandwidth-bound, so s is expected to be about 1.1–1.3. **This is an assumption that must be measured.**
- **Required change 1 (infrastructure, `serve.py`).** Add `@modal.concurrent(max_inputs=32)` and `max_containers=1` to `serve`.
  - Without them, a Modal container accepts one request at a time: Modal's own docstring says so, and the repo's `modal_serve.py` notes it at line 53. Parallel games against the current deployment would therefore start extra L40S containers, each with a cold start, which multiplies cost instead of cutting it.
  - `max_containers=1` also caps the risk seen in the unexplained second Qwen container.
  - Model, revision, flags and image stay identical. Redeploy, then rerun the identity check.
- **Required change 2 (runner).** It needs a way to run K games concurrently.
  - **Must be processes, not threads.** The runner redirects stdout process-wide and keeps a global `_usage_ctx`.
  - **Minimal version:**
    - a `--game-numbers` (or `--worker i/K`) option;
    - K processes;
    - per-worker records directories, merged before `analyze.py`.
  - No game code changes. Each game reseeds from its own seed, and `test_run_order.py` already shows records do not depend on execution order.
- **Required change 3 (PREREG).** Amend "Execution order: games run one at a time, with no parallel calls" to "K at a time, in the same job order", stating the reason (cost and runtime) and that it is set before any main-run data.
- **Validity notes.**
  - vLLM batching is not bit-identical to batch-1 inference, but LLM sampling is already unseeded. No new kind of randomness is added, and the output distribution is the same.
  - Pairing by game number is kept. With a queue in game-number order, the 5 games of one game number run at about the same time and under the same load, which is a tighter match than now.
  - The run would take about 1.5–2 h instead of about 13 h, so drift and interruption risk also shrink.
- **Validation before the main run (needs your OK, costs about $1).** A 10–15-minute smoke test with K = 10, to:
  1. measure s;
  2. confirm `modal container list` shows exactly 3 containers;
  3. check latencies and error rates;
  4. then stop the apps.

### B. Put all three models on one GPU. **Additional saving, not recommended.**
- **On an L40S (48 GB).** The weights alone take about 37.7 GB (16.1 + 15.2 + 6.4). The Llama models' native 128k context needs about 16 GB and 15 GB of KV cache, so this only works with a new `--max-model-len`. That is a launch-flag change, and the pilot never used it.
- **On an A100-80GB ($2.50/h).** It fits with careful per-process `--gpu-memory-utilization`. It would cut a K = 10 run from about $10.6 to about $4.5 (N = 30).
- **Drawbacks.**
  - It changes the GPU architecture (Ampere instead of Ada) relative to the pilot.
  - It needs a new three-server container with fragile memory profiling, and a longer cold start.
  - The absolute saving after option A is only about $6.
- **L4 per model.** It is not cheaper per unit of throughput: $/bandwidth is about $0.0027 for L4 vs. about $0.0023 for L40S. It is about 2.5 times slower, and Llama-3.1-8B would need `--max-model-len`.

### C. Smaller items
- **Warm-up before game 1** (one request per model). No saving: cold start is $0.08. It does stop the first game being slowed by about 1–2 minutes (C0 g0 took 549 s against a 309 s mean).
- **Prefix caching** (`--enable-prefix-caching`). The roughly 1.2k-token prompts share the rules prefix, but latency is dominated by decoding 70–110 tokens. The gain is probably under 10%, and it is a flag change. Not worth it.
- **Keep the stop-on-exit trap.** With `scaledown_window` at 30 minutes, a run that dies without the trap would leave idle GPUs costing about $2.9.
- **Hosted per-token APIs (Nebius / OpenRouter).** Rejected. Pinned revisions, dtype and vLLM version cannot be guaranteed, so that would change the serving conditions.

## 3. N = 24 vs N = 30

Method:
- **Current setup.** Bootstrap over the pilot's per-game-number durations.
- **Optimised setup.** Each simulated run resamples pilot game durations (cold-start game excluded), multiplies them by the slowdown s, and schedules them on K workers with a queue. It then adds 150 s for warm-up and teardown.
- **Cost.** Wall time × 3 L40S × $1.95/h × 1.04 (the CPU and memory share).

| setup | N = 24 (120 games): wall | N = 24: cost | N = 30 (150 games): wall | N = 30: cost |
|---|---|---|---|---|
| **Current** (serial, 3 × L40S) | 10.3 h (9.5–11.2) | **$63** ($58–68) | 12.9 h (12.0–13.9) | **$78** ($73–84) |
| Parallel K = 10, s = 1.1 | 1.2 h | $7.3 | 1.5 h | $9.0 |
| **Parallel K = 10, s = 1.3 (planning value)** | **1.4 h** | **$8.6** | **1.7 h** | **$10.6** |
| Parallel K = 10, s = 1.6 (pessimistic) | 1.7 h | $10.5 | 2.1 h | $13.0 |
| Parallel K = 15, s = 1.3 | 1.0 h | $6.0 | 1.2 h | $7.3 |
| Parallel K = 10, s = 1.3, one A100-80GB (option B) | 1.4 h | $3.7 | 1.7 h | $4.5 |

How to read the table:
- The ranges in brackets for the current setup are 90% bootstrap intervals.
- The 95th percentile of the optimised runs is within 5% of the median shown.
- The validation smoke test adds about $1 to any optimised setup.

**Reading.**
- Option A cuts the main run's cost by about 85–90% at either N. For example, N = 30 drops from about $78 / 13 h to about $11 / 1.7 h.
- At that price, the cost difference between N = 24 and N = 30 is about $2. Cost is no longer a reason to prefer N = 24, which also breaks the 15-cycle counterbalancing.
- Option B saves only another $4–6 and adds hardware and flag changes, so I do not recommend it.

## What would need your approval (not done)
1. Changing `serve.py` (`@modal.concurrent`, `max_containers=1`), redeploying, and rerunning the identity check.
2. Adding a parallel-worker option to the runner, plus a merge step.
3. Amending PREREG's execution-order section.
4. A K = 10 smoke test (about $1) to measure s, with all apps stopped afterwards.
