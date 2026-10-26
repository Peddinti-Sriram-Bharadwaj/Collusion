#!/usr/bin/env bash
# Judge phase v2 (PREREG Amendment 13; coding_rubric_v3.md section 6): ONE validation attempt with prompt v2 on the
# frozen independent set; main-run judgement only if it passes; then the analysis with judgements.
# If v2 fails there is no further revision: HA1a-c are not tested (option A) and no main-run reply is judged.
#
# NOT RUN until the user has reviewed Amendment 13 and the materials. Preconditions (checked below, before any cost):
#   1. judge_v2/freeze_manifest.json exists with status "ok", and every frozen file still matches its sha256.
#   2. PREREG.md contains the manifest's sha256 (recorded in Amendment 13 after the freeze).
#   3. No main-run judgements and no v2 validation output exist yet.
#   4. The judge app is deployed (launch_judge.sh with RUN_SCRIPT=run_judge_v2.sh does this) and the router routes it.
# Stops the judge app on exit, however the script ends.
set -u
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
GAME=/x/Collusion/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar
RES=/x/Collusion/results/scripted_offer
OUT=$RES/main
V2=$RES/judge_v2
VOUT=$OUT/judge_validation_v2
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
[ "$JUDGE_REVISION" = "9527884be6e5616bdd54de542f9ae13384489724" ] || { echo "refusing to start: JUDGE_REVISION differs from the recorded revision"; exit 2; }
[ -f "$OUT/judgements.csv" ] && { echo "refusing to start: $OUT/judgements.csv exists (main-run judgements are never redone)"; exit 2; }
[ -e "$VOUT" ] && { echo "refusing to start: $VOUT exists (v2 validation has one attempt only)"; exit 2; }
# Freeze checks: status ok, every hash matches, manifest hash recorded in PREREG.
"$PY" -I - "$V2/freeze_manifest.json" "$RES/PREREG.md" <<'EOF' || { echo "refusing to start: freeze check failed"; exit 2; }
import hashlib, json, sys
from pathlib import Path
mpath, prereg = Path(sys.argv[1]), Path(sys.argv[2])
if not mpath.exists():
    sys.exit("no freeze_manifest.json: run judge_v2/freeze_judge_v2.py first")
m = json.loads(mpath.read_text(encoding="utf-8"))
if m["status"] != "ok":
    sys.exit(f"freeze status is {m['status']!r}; the judge is not run")
bad = [n for n, h in m["sha256"].items() if hashlib.sha256(Path(m["paths"][n]).read_bytes()).hexdigest() != h]
if bad:
    sys.exit(f"frozen files changed since the freeze: {bad}")
mh = hashlib.sha256(mpath.read_bytes()).hexdigest()
if mh not in prereg.read_text(encoding="utf-8"):
    sys.exit(f"PREREG.md does not contain the manifest sha256 {mh}")
print(f"[freeze] ok: {len(m['sha256'])} files match; manifest {mh[:16]} recorded in PREREG; {m['n_items']} items")
EOF
ROUTER=http://127.0.0.1:8100
. /x/Collusion/experiments/modal_infra/check_router.sh
router_alive "$ROUTER" "$JUDGE_MODEL" || { echo "refusing to start: router preflight failed"; exit 2; }
# CHECK_ONLY=1: preconditions only, no judge call (launch_judge.sh runs this before deploying).
if [ "${CHECK_ONLY:-}" = "1" ]; then echo "[check-only] all preconditions hold"; exit 0; fi

cleanup() {
  echo "[cleanup] $(date -u +%FT%TZ) stopping the judge app"
  "$MODAL" app stop "$JUDGE_APP" --yes 2>&1
  "$MODAL" app list 2>&1
  echo "[cleanup] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

cd "$GAME"
COMMON="--judge-model $JUDGE_MODEL --judge-revision $JUDGE_REVISION --prompt-version v2 --results-dir $OUT"
router_chat_ok "$ROUTER" "$JUDGE_MODEL" 1800 || { echo "[router] FAILED: judge did not answer 200 through the router"; exit 1; }
echo "[validate v2] $(date -u +%FT%TZ)"
"$PY" analysis/scripted_offer/judge_replies.py validate --pilot-records "$PILOT2" \
  --synthetic "$V2/validation_set_v2.csv" --compare-synthetic "$RES/judge_validation_synthetic.csv" \
  --out-dir "$VOUT" $COMMON
rc=$?
echo "[validate v2] exit=$rc (0 = both required criteria met)"
if [ "$rc" != "0" ]; then
  echo "validation v2 FAILED: no further revision (Amendment 13). HA1a-c are not tested; no main-run reply is judged."
  exit 1
fi
echo "[judge] $(date -u +%FT%TZ)"
"$PY" analysis/scripted_offer/judge_replies.py judge --records "$RECORDS" --out "$OUT/judgements.csv" $COMMON
echo "[judge] exit=$?"
"$PY" analysis/scripted_offer/analyze.py --records "$RECORDS" --out "$OUT/analysis" \
  --judgements "$OUT/judgements.csv" --judge-validated > "$OUT/analysis_stdout.txt" 2>&1
echo "[analysis] exit=$? -> $OUT/analysis/summary.md"
