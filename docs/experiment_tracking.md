# Experiment tracking

All strategic-pricing experiments run through one pipeline:
config spec -> unit expansion -> Modal (or local) execution -> append-only registry -> tables -> figures -> report.

## Adding an experiment
1. Write a spec in `research/configs/<batch_id>.json` with `batch_id`, `protocol`
   (a file in `research/protocols/`), `designation` (`smoke` | `exploratory` | `confirmatory`), `model`, optional
   `base` overrides, and `blocks`. Each block has a `name`, optional `overrides`, and a `grid` whose keys are unit
   fields (dotted paths such as `seeds.history_seed`, or `steering_preset` for whole steering dicts). Block names of
   the form `sweep:<factor>` feed the robustness views.
2. `python scripts/research.py plan --spec <spec>`: validates every unit and prints units, forward passes,
   generations, GPU-hours and cost (estimates are about 2x conservative on 7B; the smoke batch used 161 s versus
   331 s estimated).
3. `python scripts/research.py launch --spec <spec>`: detached Modal run (`modal run --detach` + `spawn`), so closing
   the laptop does not cancel it. Each unit is written to the volume `collusion-latent-results` at
   `research/<batch_id>/<run_id>.json`; a relaunch skips units already on the volume.
4. `python scripts/research.py sync --batch <batch_id>`: downloads, writes raw gz payloads to
   `research/raw/<batch_id>/`, appends records to `research/registry/runs.jsonl` (completed run_ids are skipped).
5. `python scripts/research.py analyze`: rebuilds `research/outputs/{tables,figures,report.md}` from the whole
   registry. Figures carry a `manifest.json` listing the run_ids and raw-file hashes behind each figure.
6. `python scripts/research.py verify`: checks every registry record against its raw payload checksum.

`run-local --spec <spec> --model 0.5b` runs on CPU for debugging.

## What a run record contains
`run_id` (hash of the full unit config, so identical configs are idempotent), batch id, protocol, designation,
block, the full unit config (condition, design, economics preset, template id and hash, window, decoding, steering
kind/vector id/vector sha/alpha/layer/site/timing, all seeds, replicate), model id and pinned revision, backend,
GPU, dtype, git commit / branch / dirty flag, host, start and end time, status (`completed` | `failed` with
traceback), validity counts (strict-parse audits, agreement, min digit mass), summary metrics, raw path and sha256.

## Rules
- The registry is append-only. Nothing is overwritten; corrections are new batches.
- Failed or malformed decisions are recorded as such. Nothing is replaced with a default action.
- Smoke and exploratory batches are never pooled into confirmatory estimates; the report shows the designation of
  every number.
- Legacy runs (Phase A-D outputs under `artifacts/interpretability/runs/`) are indexed in
  `research/registry/legacy.jsonl` with whatever metadata could be recovered; missing fields are `unknown`.
- Secrets never enter configs, logs or records. Modal credentials come from the local Modal profile.
