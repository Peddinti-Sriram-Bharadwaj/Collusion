#!/usr/bin/env bash
# Family B judge step (PREREG Amendment 14; HYPOTHESES_v1.md "Replies"): judge X's replies in C1c/C1ci/C1d and
# game 1 of the C1s series with the frozen judge v2 (rubric v3, prompt v2, same model revision and settings as
# the main run, validated on 2026-10-26: accuracy 0.95, stability pass), then re-run the Family B analysis
# with the judgements. Descriptive only: no hypothesis depends on these categories. Launched on the
# experimenter's instruction in chat ("돌려.", 2026-10-26 ~16:40 KST), after the Family B results had been seen.
# Game-repo commit d27fe38 (judge_replies.py --family-b). Writes followup/judgements_B.csv (never overwritten)
# and followup/analysis_judged/; followup/analysis/ (labels only) is left as it is.
# Stops the judge app on exit, however the script ends.
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
REC=$GAME/experiments/game_records
REC_A=$REC/scripted_offer_followup_b
REC_B=$REC/scripted_offer_followup_b_series
MAIN=$REC/scripted_offer_main
JUDGE_MODEL=mistralai/Mistral-Small-24B-Instruct-2501
JUDGE_APP=vllm-mistral-small-24b-instruct-2501
JUDGE_REVISION=9527884be6e5616bdd54de542f9ae13384489724
CODE_COMMIT=d27fe38
. "$INFRA/check_router.sh"

[ "${CONFIRM_PAID:-}" = "1" ] || { echo "refusing to start: set CONFIRM_PAID=1 to acknowledge paid Modal inference"; exit 2; }
[ -f "$OUT/judgements_B.csv" ] && { echo "refusing to start: $OUT/judgements_B.csv exists (judgements are never redone)"; exit 2; }
[ -f "$OUT/analysis/results.md" ] || { echo "refusing to start: Family B analysis (labels only) not present"; exit 2; }
grep -q "$JUDGE_REVISION" "$RES/PREREG.md" || { echo "refusing to start: judge revision not in PREREG.md"; exit 2; }
grep -q "validate v2\] exit=0" "$RES/judge_v2_run.log" || { echo "refusing to start: judge v2 validation did not pass"; exit 2; }
cd "$GAME"
[ -z "$(git status --short)" ] || { echo "refusing to start: game tree not clean"; git status --short; exit 2; }
HEAD=$(git rev-parse HEAD); case "$HEAD" in "$CODE_COMMIT"*) ;; *) echo "refusing to start: HEAD $HEAD is not $CODE_COMMIT"; exit 2;; esac
[ "$(ls "$REC_A"/C1c_g??.json "$REC_A"/C1ci_g??.json "$REC_A"/C1d_g??.json 2>/dev/null | wc -l)" = "90" ] || { echo "refusing to start: expected 90 Phase A records"; exit 2; }
[ "$(ls "$REC_B"/C1s_g??_k1.json 2>/dev/null | wc -l)" = "30" ] || { echo "refusing to start: expected 30 C1s game-1 records"; exit 2; }
router_alive "$ROUTER" "$JUDGE_MODEL" || { echo "refusing to start: router preflight failed"; exit 2; }
if [ "${CHECK_ONLY:-}" = "1" ]; then echo "[check-only] all preconditions hold (HEAD $HEAD)"; exit 0; fi

cleanup() {
  echo "[cleanup] $(date -u +%FT%TZ) stopping the judge app"
  "$MODAL" app stop "$JUDGE_APP" --yes 2>&1
  "$MODAL" container list 2>&1
  echo "[cleanup] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

echo "[launch] $(date -u +%FT%TZ) head=$HEAD judge $JUDGE_MODEL @ $JUDGE_REVISION"
sha256sum "$RES/PREREG.md" "$OUT/HYPOTHESES_v1.md" "$RES/coding_rubric_v3.md" "$GAME/analysis/scripted_offer/judge_prompt_v2.txt" > "$OUT/judge_B_sha256_at_run.txt"
echo "$HEAD" > "$OUT/judge_B_code_commit.txt"

# 1. Deploy the judge (same recipe as launch_judge.sh: A100-80GB, pinned revision).
cd "$INFRA"
MODAL_SERVE_MODEL=$JUDGE_MODEL MODAL_SERVE_REVISION=$JUDGE_REVISION MODAL_SERVE_GPU=A100-80GB \
  "$MODAL" deploy serve.py 2>&1 | tail -5
[ "${PIPESTATUS[0]}" = "0" ] || { echo "[deploy] FAILED"; exit 1; }

# 2. Identity record.
"$MODAL_PY" - "$OUT/modal_identity_judge_B.json" "$JUDGE_APP" "$JUDGE_REVISION" <<'PYEOF' || { echo "[identity] FAILED"; exit 1; }
import json, sys, modal
out, app, rev = sys.argv[1:4]
r = modal.Function.from_name(app, "identity").remote()
json.dump(r, open(out, "w"), indent=2)
ok = r["revision"] == rev and "config.json" in r["files_sha256"]
print("[identity]", r["model"], r["revision"], r["vllm_version"], r["config"]["architectures"], "ok" if ok else "MISMATCH", flush=True)
sys.exit(0 if ok else 1)
PYEOF

# 3. Judge (prompt v2, default settings = main run: temperature 0, top_p 1, seed 20261025, max_tokens 150).
cd "$GAME"
router_chat_ok "$ROUTER" "$JUDGE_MODEL" 1800 || { echo "[router] FAILED: judge did not answer 200 through the router"; exit 1; }
echo "[judge B] $(date -u +%FT%TZ)"
"$PY" analysis/scripted_offer/judge_replies.py judge --family-b "$REC_A" --family-b "$REC_B" --out "$OUT/judgements_B.csv" \
  --judge-model "$JUDGE_MODEL" --judge-revision "$JUDGE_REVISION" --prompt-version v2 --results-dir "$OUT"
rc=$?; echo "[judge B] exit=$rc"
[ "$rc" = "0" ] || exit 1

# 4. Analysis with judgements (separate directory; the labels-only analysis is kept).
"$PY" analysis/scripted_offer/analyze_followup.py --main "$MAIN" --followup "$REC_A" --followup "$REC_B" \
  --judgements "$OUT/judgements_B.csv" --out "$OUT/analysis_judged" > "$OUT/analysis_judged_stdout.txt" 2>&1
echo "[analysis] exit=$? -> $OUT/analysis_judged/results.md"
