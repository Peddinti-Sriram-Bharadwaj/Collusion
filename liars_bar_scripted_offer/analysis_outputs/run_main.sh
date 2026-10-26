#!/usr/bin/env bash
# Main run (PREREG v7, Amendment 12): N = 30 game numbers x 7 conditions = 210 games, K = 10 parallel workers.
#
# NOT RUN BY THE ASSISTANT. Launching this costs money (about $15-18 for the games at pilot-2 rates).
# Preconditions (all manual, each needs its own approval):
#   1. The three agent apps are deployed with experiments/modal_infra/serve.py (identity check recorded).
#   2. The local router is running:  experiments/modal_infra/start_router.ps1  (checked below, before any cost)
#   3. The K=10 smoke test (~$1) confirmed `modal container list` shows exactly 3 GPU containers.
#   4. PREREG.md "Main run" states N = 30 (checked below), and the code is committed (hash recorded there).
# Always stops every Modal app of this experiment on exit (success, error, timeout or kill), judge app included.
set -u
# The Modal CLI and analyze.py print non-cp949 characters (e.g. U+2713, U+2013); force UTF-8 output on Windows.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
GAME=/x/Collusion/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar
OUT=/x/Collusion/results/scripted_offer/main
RECORDS=$GAME/experiments/game_records/scripted_offer_main
# Warm-up wakes only the three agent backends (routes_modal.json also lists Ministral and the judge,
# which are not deployed for the games, so warming them would wait out --max-wait and abort the run).
ROUTES=/x/Collusion/experiments/modal_infra/routes_agents.json
MODAL=<HOME>/.local/bin/modal
PY=$GAME/../.venv/Scripts/python.exe
APPS="vllm-llama-3-1-8b-instruct vllm-llama-3-2-3b-instruct vllm-qwen2-5-7b-instruct vllm-ministral-8b-instruct-2410 vllm-mistral-small-24b-instruct-2501"
N=${N:-30}
WORKERS=${WORKERS:-10}
if [ "$WORKERS" -lt 2 ] 2>/dev/null || ! [ "$WORKERS" -eq "$WORKERS" ] 2>/dev/null; then
  echo "refusing to start: WORKERS=$WORKERS; the main run is parallel only (WORKERS >= 2)"; exit 2
fi

if [ "${CONFIRM_PAID:-}" != "1" ]; then
  echo "refusing to start: set CONFIRM_PAID=1 to acknowledge that this launches paid Modal inference"; exit 2
fi
if ! grep -q 'Main run (Amendment 12' /x/Collusion/results/scripted_offer/PREREG.md || \
   ! grep -q '\*\*N = 30\*\*' /x/Collusion/results/scripted_offer/PREREG.md; then
  echo "refusing to start: PREREG.md does not state N = 30 in its Main run section"; exit 2
fi
if [ "$N" != "30" ]; then echo "refusing to start: N=$N differs from the pre-registered N = 30"; exit 2; fi
# The warm-up talks to the backends directly (not via the router), so it needs the backend key here.
if [ -z "${MODAL_SERVE_API_KEY:-}" ]; then echo "refusing to start: MODAL_SERVE_API_KEY is not set (needed by the warm-up)"; exit 2; fi
ROUTER=http://127.0.0.1:8100
AGENT_MODELS="meta-llama/Llama-3.1-8B-Instruct meta-llama/Llama-3.2-3B-Instruct Qwen/Qwen2.5-7B-Instruct"
. /x/Collusion/experiments/modal_infra/check_router.sh
router_alive "$ROUTER" $AGENT_MODELS || { echo "refusing to start: router preflight failed"; exit 2; }

cleanup() {
  echo "[cleanup] $(date -u +%FT%TZ) stopping Modal apps"
  for a in $APPS; do "$MODAL" app stop "$a" --yes 2>&1; done
  "$MODAL" app list 2>&1
  "$MODAL" container list 2>&1
  echo "[cleanup] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

mkdir -p "$OUT"
cd "$GAME"
echo "[start] $(date -u +%FT%TZ) branch=$(git rev-parse --abbrev-ref HEAD) head=$(git rev-parse HEAD) N=$N K=$WORKERS"
git rev-parse HEAD > "$OUT/code_commit.txt"
git diff HEAD > "$OUT/code_snapshot.patch"
git status --short > "$OUT/code_status.txt"
# Phase 0: one request per agent model THROUGH the router (the games' path, the router's key), all at once.
# Stops the run (trap stops the apps) unless all three answer 200.
ok=0; pids=""
for m in $AGENT_MODELS; do router_chat_ok "$ROUTER" "$m" 1200 > "$OUT/router_check_${m##*/}.txt" & pids="$pids $!"; done
for p in $pids; do wait "$p" && ok=$((ok + 1)); done
cat "$OUT"/router_check_*.txt
if [ "$ok" != "3" ]; then echo "[router] FAILED: $ok/3 agent models answered 200 through the router; no game started"; exit 1; fi
# Phase 1: warm every backend at once, then the games (resumable: rerun the same command after an interruption).
timeout 21600 "$PY" src/game/run_scripted_offer.py --games "$N" --workers "$WORKERS" \
  --records-dir "$RECORDS" --results-dir "$OUT" --warmup-routes "$ROUTES"
echo "[runner] exit=$? $(date -u +%FT%TZ)"
# Phase 2: pre-registered analysis without judgements (HA1 not tested until run_judge.sh has run).
"$PY" analysis/scripted_offer/analyze.py --records "$RECORDS" --out "$OUT/analysis" > "$OUT/analysis_stdout.txt" 2>&1
echo "[analysis] exit=$? -> $OUT/analysis/summary.md"
echo "Next: judge phase (run_judge.sh), separate approval. Agent apps are stopped by the trap now."
