#!/usr/bin/env bash
# Judge phase (PREREG v7, "Reply classification"): validation first, main-run judgement only if it passes,
# then the analysis with judgements. One GPU session for both (one cold start).
#
# NOT RUN BY THE ASSISTANT. Launching this costs money (about $1.5-4: one A100-80GB while the judge app is up,
# including the first weight download). Preconditions (manual):
#   1. The judge app is deployed with experiments/modal_infra/serve.py:
#        MODAL_SERVE_MODEL=mistralai/Mistral-Small-24B-Instruct-2501 MODAL_SERVE_REVISION=<commit sha> \
#        MODAL_SERVE_GPU=A100-80GB modal deploy serve.py
#      and the same revision is passed below as JUDGE_REVISION (recorded in PREREG Amendment 12 and
#      coding_rubric_v2.md section 4 before the first main-run judgement).
#   2. The local router runs with routes_modal.json (which has the judge route).
#   3. run_main.sh has finished (records in $RECORDS).
# Stops the judge app on exit, however the script ends.
set -u
# The Modal CLI and analyze.py print non-cp949 characters (e.g. U+2713, U+2013); force UTF-8 output on Windows.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
GAME=/x/Collusion/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar
RES=/x/Collusion/results/scripted_offer
OUT=$RES/main
RECORDS=$GAME/experiments/game_records/scripted_offer_main
PILOT2=$RES/pilot2/records
MODAL=<HOME>/.local/bin/modal
PY=$GAME/../.venv/Scripts/python.exe
JUDGE_MODEL=${JUDGE_MODEL:-mistralai/Mistral-Small-24B-Instruct-2501}
JUDGE_APP=${JUDGE_APP:-vllm-mistral-small-24b-instruct-2501}
JUDGE_REVISION=${JUDGE_REVISION:-}

if [ "${CONFIRM_PAID:-}" != "1" ]; then
  echo "refusing to start: set CONFIRM_PAID=1 to acknowledge that this launches paid Modal inference"; exit 2
fi
if [ -z "$JUDGE_REVISION" ]; then echo "refusing to start: JUDGE_REVISION (commit sha of the deployed judge) is required"; exit 2; fi
if [ -f "$OUT/judgements.csv" ]; then echo "refusing to start: $OUT/judgements.csv exists (main-run judgements are never redone)"; exit 2; fi
ROUTER=http://127.0.0.1:8100
. /x/Collusion/experiments/modal_infra/check_router.sh
router_alive "$ROUTER" "$JUDGE_MODEL" || { echo "refusing to start: router preflight failed"; exit 2; }

cleanup() {
  echo "[cleanup] $(date -u +%FT%TZ) stopping the judge app"
  "$MODAL" app stop "$JUDGE_APP" --yes 2>&1
  "$MODAL" app list 2>&1
  echo "[cleanup] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

cd "$GAME"
mkdir -p "$OUT/judge_validation"
# One request to the judge THROUGH the router (wakes its GPU; the trap stops it) before any judgement.
router_chat_ok "$ROUTER" "$JUDGE_MODEL" 1800 || { echo "[router] FAILED: judge did not answer 200 through the router"; exit 1; }
echo "[validate] $(date -u +%FT%TZ)"
"$PY" analysis/scripted_offer/judge_replies.py validate --pilot-records "$PILOT2" \
  --synthetic "$RES/judge_validation_synthetic.csv" --out-dir "$OUT/judge_validation" \
  --judge-model "$JUDGE_MODEL" --judge-revision "$JUDGE_REVISION" --results-dir "$OUT"
rc=$?
echo "[validate] exit=$rc (0 = both required criteria met)"
if [ "$rc" != "0" ]; then
  echo "validation FAILED: no main-run reply is judged. Revise the rubric/prompt (new version, logged in"
  echo "coding_rubric_v2.md section 8) and rerun validation; if the criteria cannot be met, HA1a-c are descriptive only."
  exit 1
fi
echo "[judge] $(date -u +%FT%TZ)"
"$PY" analysis/scripted_offer/judge_replies.py judge --records "$RECORDS" --out "$OUT/judgements.csv" \
  --judge-model "$JUDGE_MODEL" --judge-revision "$JUDGE_REVISION" --results-dir "$OUT"
echo "[judge] exit=$?"
"$PY" analysis/scripted_offer/analyze.py --records "$RECORDS" --out "$OUT/analysis" \
  --judgements "$OUT/judgements.csv" --judge-validated > "$OUT/analysis_stdout.txt" 2>&1
echo "[analysis] exit=$? -> $OUT/analysis/summary.md"
