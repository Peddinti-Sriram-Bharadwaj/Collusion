#!/usr/bin/env bash
# Main-run launcher (PREREG v7, Amendment 12): deploy the three agent apps, identity check, container
# monitor, then run_main.sh (N = 30, K = 10, its own preflight checks and stop-all trap).
# Same deploy / identity / monitor steps as smoke_k10/run_smoke.sh (run 2, PASSED).
# Launched 2026-10-25 on the user's instruction to start the main run ("본실험 시작").
# Always stops every Modal app of this experiment on exit, however the script ends.
set -u
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
ROOT=/x/Collusion
RES=$ROOT/results/scripted_offer
OUT=$RES/main
INFRA=$ROOT/experiments/modal_infra
MODAL=<HOME>/.local/bin/modal
MODAL_PY=<HOME>/AppData/Roaming/uv/tools/modal/Scripts/python.exe
ROUTER=http://127.0.0.1:8100
APPS="vllm-llama-3-1-8b-instruct vllm-llama-3-2-3b-instruct vllm-qwen2-5-7b-instruct vllm-ministral-8b-instruct-2410 vllm-mistral-small-24b-instruct-2501"
# Pinned revisions (results/modal_identity.json, identical to pilot 2 and the smoke test).
DEPLOY="meta-llama/Llama-3.1-8B-Instruct=0e9e39f249a16976918f6564b8830bc894c89659
meta-llama/Llama-3.2-3B-Instruct=0cb88a4f764b7a12671c53f0838cd831a0843b95
Qwen/Qwen2.5-7B-Instruct=a09a35458c702b33eeacc393d103063234e8bc28"
AGENT_MODELS="meta-llama/Llama-3.1-8B-Instruct meta-llama/Llama-3.2-3B-Instruct Qwen/Qwen2.5-7B-Instruct"
. "$INFRA/check_router.sh"

# 0. Checks before anything is deployed (no cost).
router_alive "$ROUTER" $AGENT_MODELS || { echo "refusing to start: router preflight failed"; exit 2; }
if [ -z "${MODAL_SERVE_API_KEY:-}" ]; then
  MODAL_SERVE_API_KEY=$(tr -d '\r\n' < "$HOME/.modal_serve_key") || { echo "refusing to start: no key file"; exit 2; }
fi
[ -n "$MODAL_SERVE_API_KEY" ] || { echo "refusing to start: MODAL_SERVE_API_KEY empty"; exit 2; }
export MODAL_SERVE_API_KEY

MON_PID=""
cleanup() {
  echo "[launch cleanup] $(date -u +%FT%TZ)"
  [ -n "$MON_PID" ] && kill "$MON_PID" 2>/dev/null
  for a in $APPS; do "$MODAL" app stop "$a" --yes 2>&1; done
  "$MODAL" container list 2>&1
  echo "[launch cleanup] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

mkdir -p "$OUT"
sha256sum "$RES/PREREG.md" > "$OUT/prereg_sha256.txt"
echo "[launch] $(date -u +%FT%TZ) prereg $(cut -c1-16 "$OUT/prereg_sha256.txt")"

# 1. Deploy the three agent apps (serve.py: @modal.concurrent(max_inputs=32), max_containers=1).
cd "$INFRA"
while IFS== read -r model rev; do
  echo "[deploy] $model @ $rev"
  MODAL_SERVE_MODEL=$model MODAL_SERVE_REVISION=$rev MODAL_SERVE_GPU=L40S "$MODAL" deploy serve.py 2>&1 | tail -5
  [ "${PIPESTATUS[0]}" = "0" ] || { echo "[deploy] FAILED for $model"; exit 1; }
done <<< "$DEPLOY"

# 2. Identity check (CPU-only functions, no GPU) against pilot 2.
"$MODAL_PY" - "$OUT/modal_identity_main.json" <<'EOF' || { echo "[identity] FAILED"; exit 1; }
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
  done ) >> "$OUT/container_monitor.log" 2>&1 &
MON_PID=$!

# 4. The main run (router check, warm-up, 210 games, analysis without judgements; stops all apps on exit).
CONFIRM_PAID=1 N=30 WORKERS=10 bash "$RES/run_main.sh"
echo "[launch] run_main.sh exit=$? $(date -u +%FT%TZ)"
