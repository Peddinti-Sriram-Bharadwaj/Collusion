#!/usr/bin/env bash
# Sample-size pilot (pilot2): current code, unchanged conditions/prompts/mechanics.
# 6 game numbers (g = 0..5) x C0-C4, sequential, separate records dir (not pooled with the main run).
# Always stops every Modal app of this experiment on exit (success, error, timeout or kill).
set -u
GAME=/c/AISafetyResearch/Collusion/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar
OUT=/c/AISafetyResearch/Collusion/results/scripted_offer/pilot2
RECORDS=$GAME/experiments/game_records/scripted_offer_pilot2
MODAL=<HOME>/.local/bin/modal
APPS="vllm-llama-3-1-8b-instruct vllm-llama-3-2-3b-instruct vllm-qwen2-5-7b-instruct vllm-ministral-8b-instruct-2410"

cleanup() {
  echo "[cleanup] $(date -u +%FT%TZ) stopping Modal apps"
  for a in $APPS; do "$MODAL" app stop "$a" --yes 2>&1; done
  "$MODAL" app list 2>&1
  "$MODAL" container list 2>&1
  echo "[cleanup] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

cd "$GAME"
echo "[start] $(date -u +%FT%TZ) branch=$(git rev-parse --abbrev-ref HEAD) head=$(git rev-parse HEAD)"
git diff HEAD > "$OUT/code_snapshot.patch"
git status --short > "$OUT/code_status.txt"
timeout 28800 ../.venv/Scripts/python.exe src/game/run_scripted_offer.py --games 6 \
  --records-dir "$RECORDS" --results-dir "$OUT"
echo "[runner] exit=$? $(date -u +%FT%TZ)"
