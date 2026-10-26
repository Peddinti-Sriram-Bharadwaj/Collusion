#!/usr/bin/env bash
# Family B follow-up run (PREREG Amendment 14; followup/HYPOTHESES_v1.md).
#
# What it does, in order, and only after every preflight check passes:
#   0. Preflight (no cost): CONFIRM_PAID=1; PREREG.md carries Amendment 14 and the Family B code commit;
#      the game repo HEAD is that commit with a clean tree; the local router answers for the three agent models;
#      the Modal key file exists.
#   1. Deploy the three agent apps at the pinned revisions of the main run; identity check against
#      results/modal_identity.json (same weights, same vLLM as pilot 2 / main run); container monitor.
#   2. Warm-up (direct to the backends, outside every record), then
#      Phase B: C1s, --series 5 x 30 game numbers, K = 10          -> records scripted_offer_followup_b_series
#      Phase A: C1c, C1ci, C1d x 30 game numbers, K = 10          -> records scripted_offer_followup_b
#      Both phases run at the same time (B launched first, then A); each logs to its own file
#      (followup/phase_b.log, followup/phase_a.log) and both are cut off at DEADLINE_UTC.
#   3. Family B analysis (analyze_followup.py) against the main run's records (read only), once, after both phases.
#   Always stops every Modal app of this experiment on exit, however the script ends.
#
# Cost estimate (main-run rates): 90 + 150 = 240 games, about $20 (above the $15 budget cap; approved by the
# experimenter before the run, PREREG Amendment 14). Pre-run change: HB1 N = 12, k = 3 -> N = 30, k = 5.
# Not included: judging Family B replies (judge_replies.py's MESSAGE_CONDS does not list the Family B conditions;
# extending it is a separate change and a separate approval). The analysis runs without judgements (labels only).
set -u
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
ROOT=/x/Collusion
RES=$ROOT/results/scripted_offer
OUT=$RES/followup
GAME=$ROOT/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar
INFRA=$ROOT/experiments/modal_infra
MODAL=<HOME>/.local/bin/modal
MODAL_PY=<HOME>/AppData/Roaming/uv/tools/modal/Scripts/python.exe
PY=$GAME/../.venv/Scripts/python.exe
ROUTER=http://127.0.0.1:8100
ROUTES=$INFRA/routes_agents.json
MAIN_RECORDS=$GAME/experiments/game_records/scripted_offer_main
REC_A=$GAME/experiments/game_records/scripted_offer_followup_b
REC_B=$GAME/experiments/game_records/scripted_offer_followup_b_series
APPS="vllm-llama-3-1-8b-instruct vllm-llama-3-2-3b-instruct vllm-qwen2-5-7b-instruct vllm-ministral-8b-instruct-2410 vllm-mistral-small-24b-instruct-2501"
AGENT_MODELS="meta-llama/Llama-3.1-8B-Instruct meta-llama/Llama-3.2-3B-Instruct Qwen/Qwen2.5-7B-Instruct"
# Pinned revisions (results/modal_identity.json; identical to pilot 2, smoke test and main run).
DEPLOY="meta-llama/Llama-3.1-8B-Instruct=0e9e39f249a16976918f6564b8830bc894c89659
meta-llama/Llama-3.2-3B-Instruct=0cb88a4f764b7a12671c53f0838cd831a0843b95
Qwen/Qwen2.5-7B-Instruct=a09a35458c702b33eeacc393d103063234e8bc28"
FAMILY_B_COMMIT=190b249a969ed70f48c05837cc5d9e53c9250f23
N_SINGLE=${N_SINGLE:-30}      # game numbers for C1c, C1ci, C1d (pre-registered: 30)
N_SERIES=${N_SERIES:-30}      # game numbers for C1s (pre-registered: 30, Amendment 14 pre-run change)
SERIES_K=${SERIES_K:-5}       # games per series (pre-registered: 5, Amendment 14 pre-run change)
WORKERS=${WORKERS:-10}
DEADLINE_UTC=${DEADLINE_UTC:-2026-10-26T07:00:00Z}   # = 16:00 KST; deviation from the pre-registered 09:00 KST (Amendment 14)
. "$INFRA/check_router.sh"

# ---- 0. Preflight (no cost) -----------------------------------------------------------------
if [ "${CONFIRM_PAID:-}" != "1" ]; then
  echo "refusing to start: set CONFIRM_PAID=1 to acknowledge that this launches paid Modal inference"; exit 2
fi
if [ "$N_SINGLE" != "30" ] || [ "$N_SERIES" != "30" ] || [ "$SERIES_K" != "5" ]; then
  echo "refusing to start: N_SINGLE=$N_SINGLE N_SERIES=$N_SERIES SERIES_K=$SERIES_K differ from the pre-registered 30 / 30 / 5"; exit 2
fi
grep -q 'Amendment 14 (2026-10-26' "$RES/PREREG.md" || { echo "refusing to start: PREREG.md has no Amendment 14"; exit 2; }
grep -q "$FAMILY_B_COMMIT" "$RES/PREREG.md" || { echo "refusing to start: PREREG.md does not record the Family B code commit"; exit 2; }
HEAD=$(git -C "$GAME" rev-parse HEAD)
if [ "$HEAD" != "$FAMILY_B_COMMIT" ]; then
  # A later commit is allowed only if PREREG records it too (e.g. the analysis script commit).
  grep -q "$HEAD" "$RES/PREREG.md" || { echo "refusing to start: HEAD $HEAD is not recorded in PREREG.md"; exit 2; }
fi
if [ -n "$(git -C "$GAME" status --short -- src prompts analysis)" ]; then
  echo "refusing to start: uncommitted changes under src/, prompts/ or analysis/:"; git -C "$GAME" status --short -- src prompts analysis; exit 2
fi
for d in "$REC_A" "$REC_B"; do
  if [ -d "$d" ] && ls "$d"/C*_g*.json >/dev/null 2>&1; then
    echo "note: $d already holds records; the runner resumes and skips finished games (never pooled with anything else)"
  fi
done
[ -d "$MAIN_RECORDS" ] || { echo "refusing to start: main-run records not found at $MAIN_RECORDS"; exit 2; }
router_alive "$ROUTER" $AGENT_MODELS || { echo "refusing to start: router preflight failed (start experiments/modal_infra/start_router.ps1)"; exit 2; }
if [ -z "${MODAL_SERVE_API_KEY:-}" ]; then
  MODAL_SERVE_API_KEY=$(tr -d '\r\n' < "$HOME/.modal_serve_key") || { echo "refusing to start: no key file"; exit 2; }
fi
[ -n "$MODAL_SERVE_API_KEY" ] || { echo "refusing to start: MODAL_SERVE_API_KEY empty"; exit 2; }
export MODAL_SERVE_API_KEY

remaining() {   # seconds until DEADLINE_UTC (0 when passed)
  local now dl
  now=$(date -u +%s); dl=$(date -u -d "$DEADLINE_UTC" +%s 2>/dev/null || echo 0)
  if [ "$dl" -le "$now" ]; then echo 0; else echo $((dl - now)); fi
}
[ "$(remaining)" -gt 600 ] || { echo "refusing to start: fewer than 10 minutes before DEADLINE_UTC=$DEADLINE_UTC"; exit 2; }

MON_PID=""; PID_A=""; PID_B=""
cleanup() {
  echo "[cleanup] $(date -u +%FT%TZ)"
  [ -n "$MON_PID" ] && kill "$MON_PID" 2>/dev/null
  for p in $PID_A $PID_B; do kill "$p" 2>/dev/null; done
  for a in $APPS; do "$MODAL" app stop "$a" --yes 2>&1; done
  "$MODAL" container list 2>&1
  echo "[cleanup] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

mkdir -p "$OUT"
sha256sum "$RES/PREREG.md" > "$OUT/prereg_sha256_at_run.txt"
sha256sum "$OUT/HYPOTHESES_v1.md" > "$OUT/hypotheses_sha256_at_run.txt"
echo "$HEAD" > "$OUT/code_commit.txt"
git -C "$GAME" diff HEAD > "$OUT/code_snapshot.patch"
git -C "$GAME" status --short > "$OUT/code_status.txt"
echo "[launch] $(date -u +%FT%TZ) head=$HEAD prereg $(cut -c1-16 "$OUT/prereg_sha256_at_run.txt") deadline=$DEADLINE_UTC"

# ---- 1. Deploy, identity check, monitor -------------------------------------------------------
cd "$INFRA"
while IFS== read -r model rev; do
  echo "[deploy] $model @ $rev"
  MODAL_SERVE_MODEL=$model MODAL_SERVE_REVISION=$rev MODAL_SERVE_GPU=L40S "$MODAL" deploy serve.py 2>&1 | tail -5
  [ "${PIPESTATUS[0]}" = "0" ] || { echo "[deploy] FAILED for $model"; exit 1; }
done <<< "$DEPLOY"

"$MODAL_PY" - "$OUT/modal_identity_followup.json" <<'EOF' || { echo "[identity] FAILED"; exit 1; }
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
    r["matches_main_run_identity"] = same
    ok &= same
    print("[identity]", m, "ok" if same else "MISMATCH", flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=2)
sys.exit(0 if ok else 1)
EOF

( while true; do
    echo "=== $(date -u +%FT%TZ)"; "$MODAL" container list --json 2>&1
    sleep 30
  done ) >> "$OUT/container_monitor.log" 2>&1 &
MON_PID=$!

# ---- 2. Router check through the games' path, then the games ---------------------------------
cd "$GAME"
ok=0; pids=""
for m in $AGENT_MODELS; do router_chat_ok "$ROUTER" "$m" 1200 > "$OUT/router_check_${m##*/}.txt" & pids="$pids $!"; done
for p in $pids; do wait "$p" && ok=$((ok + 1)); done
cat "$OUT"/router_check_*.txt
if [ "$ok" != "3" ]; then echo "[router] FAILED: $ok/3 agent models answered 200 through the router; no game started"; exit 1; fi

# Phase B first (in the background), then Phase A; both share one timeout fixed at launch.
TMO=$(remaining)
echo "[phase B] $(date -u +%FT%TZ) C1s --series $SERIES_K x $N_SERIES, K=$WORKERS, timeout ${TMO}s -> $OUT/phase_b.log"
timeout "$TMO" "$PY" src/game/run_scripted_offer.py --conditions C1s --series "$SERIES_K" --games "$N_SERIES"   --workers "$WORKERS" --records-dir "$REC_B" --results-dir "$OUT" --warmup-routes "$ROUTES" > "$OUT/phase_b.log" 2>&1 &
PID_B=$!
echo "[phase A] $(date -u +%FT%TZ) C1c,C1ci,C1d x $N_SINGLE, K=$WORKERS, timeout ${TMO}s -> $OUT/phase_a.log"
timeout "$TMO" "$PY" src/game/run_scripted_offer.py --conditions C1c,C1ci,C1d --games "$N_SINGLE"   --workers "$WORKERS" --records-dir "$REC_A" --results-dir "$OUT" --warmup-routes "$ROUTES" > "$OUT/phase_a.log" 2>&1 &
PID_A=$!
wait "$PID_B"; RC_B=$?
echo "[phase B] exit=$RC_B $(date -u +%FT%TZ)"
wait "$PID_A"; RC_A=$?
echo "[phase A] exit=$RC_A $(date -u +%FT%TZ)"
[ "$RC_A" = "124" ] || [ "$RC_B" = "124" ] && echo "[deadline] DEADLINE_UTC reached; unfinished games are reported as pre-registered and not run"

# ---- 3. Analysis (read-only on the main run's records) -----------------------------------------
"$PY" analysis/scripted_offer/analyze_followup.py --main "$MAIN_RECORDS" --followup "$REC_A" --followup "$REC_B" \
  --out "$OUT/analysis" > "$OUT/analysis_stdout.txt" 2>&1
echo "[analysis] exit=$? -> $OUT/analysis/results.md"
echo "Judging Family B replies (descriptive) is a separate step and approval; see the header. Apps are stopped by the trap now."
