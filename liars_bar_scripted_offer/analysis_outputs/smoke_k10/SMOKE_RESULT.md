# K = 10 smoke test, 2026-10-25: ABORTED, no game completed

Disclosure: this is sprint work. It produced no game record and no measurement of s. Nothing here is pooled with the pilots or the main run.

## What happened
- **Attempt 1 (11:24 UTC).** The Modal CLI crashed while printing a ✓ under the Windows cp949 console encoding, right after deploying Llama-3.1-8B. The script's trap stopped every app. No GPU was used. Log: `run_smoke_attempt1_cp949_fail.log`. Fix: `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` in `run_smoke.sh`.
- **Attempt 2 (11:24:53 UTC).**
  - **Deploy.** All three agent apps deployed (`serve.py`: `@modal.concurrent(max_inputs=32)`, `max_containers=1`, L40S).
  - **Identity check.** All three models match pilot 2: same revision, same file sha256 values, vLLM 0.6.6. Details in `modal_identity_smoke.json`.
  - **Warm-up through the local router.** All three requests failed with curl status 000 after 44–52 s.
  - **Games.** 10 workers started. All 60 LLM calls failed with `APIConnectionError` (0 succeeded).
  - **Diagnosis.** The Qwen backend answered directly with 401, the expected reply to a request sent without the key, so it was up. A chat request to the router at 127.0.0.1:8100 was dropped with no HTTP response. **The local router, running since 2026-10-24 04:35, accepts connections but does not forward chat requests.**
  - **Stop.** I killed the runner at 11:28:39 UTC, and the trap stopped all apps.
- **Final state.** `modal app list` shows every app `stopped` with 0 tasks. `modal container list` is `[]`. The Volume `hf-weights-cache` is kept.
- **Cost.** About $0.20, from `modal billing report` for 11:00–13:00 UTC: Qwen $0.080, Llama-3.2 $0.080, Llama-3.1 $0.044. Billing can lag, so recheck later.
- **Container count.** The 30-second monitor saw one GPU container per model, plus Llama-3.1's CPU identity container. There was no second GPU container, but no load was ever applied, so this is **not** the PREREG check.

## Before a rerun
1. Restart the router with `MODAL_SERVE_API_KEY` in its environment, from `X:\Collusion\experiments\modal_infra`:
   `python router.py --routes routes_modal.json --port 8100`
   (The old process's `--log` path pointed at the pre-move C: location.)
2. Check one chat request through the router before deploying anything.
3. The records directory `scripted_offer_smoke_k10/_workers` holds 10 failed attempts. Use a fresh records directory for the rerun.
