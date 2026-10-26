#!/usr/bin/env bash
# Judge-phase launcher (PREREG v7, "Reply classification"): deploy the judge app, record its identity,
# then run_judge.sh (validation first; main-run judgement only if validation passes; analysis with judgements).
# Launched 2026-10-26 on the user's instruction ("Run the judge phase first (deploy judge, record revision,
# run_judge.sh)"). Revision recorded in PREREG.md and coding_rubric_v2.md section 4 before this ran.
# Stops the judge app on exit, however the script ends.
set -u
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
ROOT=/x/Collusion
RES=$ROOT/results/scripted_offer
OUT=$RES/main
INFRA=$ROOT/experiments/modal_infra
MODAL=<HOME>/.local/bin/modal
MODAL_PY=<HOME>/AppData/Roaming/uv/tools/modal/Scripts/python.exe
ROUTER=http://127.0.0.1:8100
JUDGE_MODEL=mistralai/Mistral-Small-24B-Instruct-2501
JUDGE_APP=vllm-mistral-small-24b-instruct-2501
JUDGE_REVISION=9527884be6e5616bdd54de542f9ae13384489724
. "$INFRA/check_router.sh"

router_alive "$ROUTER" "$JUDGE_MODEL" || { echo "refusing to start: router preflight failed"; exit 2; }
grep -q "$JUDGE_REVISION" "$RES/PREREG.md" || { echo "refusing to start: judge revision not in PREREG.md"; exit 2; }
grep -q "$JUDGE_REVISION" "$RES/coding_rubric_v2.md" || { echo "refusing to start: judge revision not in rubric"; exit 2; }
[ -f "$OUT/judgements.csv" ] && { echo "refusing to start: $OUT/judgements.csv exists"; exit 2; }
if [ "${RUN_SCRIPT:-run_judge.sh}" != "run_judge.sh" ]; then
  # v2 (Amendment 13): the freeze and PREREG checks must pass before anything is deployed.
  CHECK_ONLY=1 CONFIRM_PAID=1 JUDGE_REVISION=$JUDGE_REVISION bash "$RES/$RUN_SCRIPT" || { echo "refusing to start: $RUN_SCRIPT preconditions"; exit 2; }
fi

cleanup() {
  echo "[launch_judge cleanup] $(date -u +%FT%TZ)"
  "$MODAL" app stop "$JUDGE_APP" --yes 2>&1
  "$MODAL" container list 2>&1
  echo "[launch_judge cleanup] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# v2 runs write their own records, so the v1 files are kept (suffix _v2; added 2026-10-26).
SFX=""; [ "${RUN_SCRIPT:-run_judge.sh}" != "run_judge.sh" ] && SFX="_v2"
sha256sum "$RES/PREREG.md" "$RES/coding_rubric_v2.md" "$RES/coding_rubric_v3.md" > "$OUT/judge_prereg_sha256$SFX.txt"
echo "[launch_judge] $(date -u +%FT%TZ) $JUDGE_MODEL @ $JUDGE_REVISION"

# 1. Deploy (serve.py, A100-80GB, @modal.concurrent(max_inputs=32), max_containers=1).
cd "$INFRA"
MODAL_SERVE_MODEL=$JUDGE_MODEL MODAL_SERVE_REVISION=$JUDGE_REVISION MODAL_SERVE_GPU=A100-80GB \
  "$MODAL" deploy serve.py 2>&1 | tail -5
[ "${PIPESTATUS[0]}" = "0" ] || { echo "[deploy] FAILED"; exit 1; }

# 2. Identity record (CPU-only; downloads the pinned snapshot into the weights volume if absent).
"$MODAL_PY" - "$OUT/modal_identity_judge$SFX.json" "$JUDGE_APP" "$JUDGE_REVISION" <<'EOF' || { echo "[identity] FAILED"; exit 1; }
import json, sys, modal
out, app, rev = sys.argv[1:4]
r = modal.Function.from_name(app, "identity").remote()
json.dump(r, open(out, "w"), indent=2)
ok = r["revision"] == rev and "config.json" in r["files_sha256"]
print("[identity]", r["model"], r["revision"], r["vllm_version"], r["config"]["architectures"], "ok" if ok else "MISMATCH", flush=True)
sys.exit(0 if ok else 1)
EOF

# 3. Validation, then (only on a pass) main-run judgement and the analysis with judgements.
# RUN_SCRIPT=run_judge_v2.sh selects the Amendment 13 v2 phase (added 2026-10-26; default unchanged).
RUN_SCRIPT=${RUN_SCRIPT:-run_judge.sh}
CONFIRM_PAID=1 JUDGE_REVISION=$JUDGE_REVISION bash "$RES/$RUN_SCRIPT"
echo "[launch_judge] $RUN_SCRIPT exit=$? $(date -u +%FT%TZ)"
