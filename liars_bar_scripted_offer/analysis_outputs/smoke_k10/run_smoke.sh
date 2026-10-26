#!/usr/bin/env bash
# K = 10 smoke test (PREREG v7, Amendment 12): 2 game numbers (g = 0, 1) x 7 conditions = 14 games, 10 workers.
# Purpose: measure the batching slowdown s, confirm exactly 3 GPU containers serve the 10 workers, check
# latencies and error rates. Separate records dir: never pooled with the main run or the pilots.
# Always stops every Modal app of this experiment on exit (success, error, timeout or kill).
set -u
# The Modal CLI prints non-cp949 characters (e.g. U+2713); force UTF-8 output on Windows.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
ROOT=/x/Collusion
GAME=$ROOT/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar
INFRA=$ROOT/experiments/modal_infra
# run2: fresh output and records dirs (the aborted 2026-10-25 attempts stay in smoke_k10/ and
# scripted_offer_smoke_k10/ untouched).
OUT=$ROOT/results/scripted_offer/smoke_k10/run2
RECORDS=$GAME/experiments/game_records/scripted_offer_smoke_k10_run2
MODAL=<HOME>/.local/bin/modal
MODAL_PY=<HOME>/AppData/Roaming/uv/tools/modal/Scripts/python.exe
PY=$GAME/../.venv/Scripts/python.exe
ROUTER=http://127.0.0.1:8100
APPS="vllm-llama-3-1-8b-instruct vllm-llama-3-2-3b-instruct vllm-qwen2-5-7b-instruct vllm-ministral-8b-instruct-2410 vllm-mistral-small-24b-instruct-2501"
# Pinned revisions (results/modal_identity.json, identical to pilot 2).
DEPLOY="meta-llama/Llama-3.1-8B-Instruct=0e9e39f249a16976918f6564b8830bc894c89659
meta-llama/Llama-3.2-3B-Instruct=0cb88a4f764b7a12671c53f0838cd831a0843b95
Qwen/Qwen2.5-7B-Instruct=a09a35458c702b33eeacc393d103063234e8bc28"
AGENT_MODELS="meta-llama/Llama-3.1-8B-Instruct meta-llama/Llama-3.2-3B-Instruct Qwen/Qwen2.5-7B-Instruct"
. "$INFRA/check_router.sh"

# 0. Router preflight before anything is deployed (no backend contacted, no cost).
router_alive "$ROUTER" $AGENT_MODELS || { echo "refusing to start: router preflight failed"; exit 2; }

MON_PID=""
cleanup() {
  echo "[cleanup] $(date -u +%FT%TZ) stopping Modal apps"
  [ -n "$MON_PID" ] && kill "$MON_PID" 2>/dev/null
  for a in $APPS; do "$MODAL" app stop "$a" --yes 2>&1; done
  "$MODAL" app list 2>&1
  "$MODAL" container list 2>&1
  echo "[cleanup] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

if [ -e "$RECORDS" ]; then echo "refusing to start: $RECORDS exists (use a new run directory)"; exit 2; fi
mkdir -p "$OUT"
rm -f "$OUT/warmup_status.txt"   # this run's warm-up results only
cd "$GAME"
echo "[start] $(date -u +%FT%TZ) branch=$(git rev-parse --abbrev-ref HEAD) head=$(git rev-parse HEAD)"
git rev-parse HEAD > "$OUT/code_commit.txt"
git diff HEAD > "$OUT/code_snapshot.patch"
git status --short > "$OUT/code_status.txt"

# 1. Deploy the three agent apps (serve.py: @modal.concurrent(max_inputs=32), max_containers=1).
cd "$INFRA"
while IFS== read -r model rev; do
  echo "[deploy] $model @ $rev"
  MODAL_SERVE_MODEL=$model MODAL_SERVE_REVISION=$rev MODAL_SERVE_GPU=L40S "$MODAL" deploy serve.py 2>&1 | tail -5
  [ "${PIPESTATUS[0]}" = "0" ] || { echo "[deploy] FAILED for $model"; exit 1; }
done <<< "$DEPLOY"

# 2. Identity check (CPU-only functions, no GPU).
"$MODAL_PY" - "$OUT/modal_identity_smoke.json" <<'EOF' || { echo "[identity] FAILED"; exit 1; }
import json, sys, modal
apps = {"meta-llama/Llama-3.1-8B-Instruct": ("vllm-llama-3-1-8b-instruct", "0e9e39f249a16976918f6564b8830bc894c89659"),
        "meta-llama/Llama-3.2-3B-Instruct": ("vllm-llama-3-2-3b-instruct", "0cb88a4f764b7a12671c53f0838cd831a0843b95"),
        "Qwen/Qwen2.5-7B-Instruct": ("vllm-qwen2-5-7b-instruct", "a09a35458c702b33eeacc393d103063234e8bc28")}
ref = json.load(open("X:/Collusion/results/modal_identity.json"))
calls = {m: modal.Function.from_name(a, "identity").spawn() for m, (a, _) in apps.items()}
out, ok = {}, True
for m, c in calls.items():
    r = out[m] = c.get(timeout=3600)
    same = (r["revision"] == apps[m][1] and r["files_sha256"] == ref[m]["files_sha256"]
            and r["vllm_version"] == ref[m]["vllm_version"])
    r["matches_pilot2_identity"] = same
    ok &= same
    print("[identity]", m, "ok" if same else "MISMATCH", flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=2)
sys.exit(0 if ok else 1)
EOF

# 3. Container monitor: every 30 s, outside every record.
( while true; do
    echo "=== $(date -u +%FT%TZ)"; "$MODAL" container list --json 2>&1
    sleep 30
  done ) > "$OUT/container_monitor.log" 2>&1 &
MON_PID=$!

# 4. Warm-up through the local router (it holds the backend key): one 1-token request per model,
#    all at once, before game 1. Logged only in the router log, never in a game record.
cd "$GAME"
for m in $AGENT_MODELS; do
  router_chat_ok "$ROUTER" "$m" 1200 | tee -a "$OUT/warmup_status.txt" &
  WARM_PIDS="${WARM_PIDS:-} $!"
done
wait $WARM_PIDS   # not the container monitor
echo "[warmup] done $(date -u +%FT%TZ)"
# Every backend must answer 200 through the router before any game starts; otherwise stop (trap cleans up).
n_ok=$(grep -c "status=200 " "$OUT/warmup_status.txt" 2>/dev/null || true)
if [ "${n_ok:-0}" != "3" ]; then
  echo "[warmup] FAILED: ${n_ok:-0}/3 backends answered 200 through the router; not starting any game"
  exit 1
fi

# 5. The 14 games, 10 workers.
timeout 3600 "$PY" src/game/run_scripted_offer.py --games 2 --workers 10 \
  --records-dir "$RECORDS" --results-dir "$OUT"
echo "[runner] exit=$? $(date -u +%FT%TZ)"
