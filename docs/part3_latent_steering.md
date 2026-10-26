> Detailed write-up moved out of the top-level README to keep it readable. Back to the [project overview](../README.md).

# Part 3 — Inside a pricing LLM: latent steering and strategic deviation (Gagana, sprint lane)

Sprint-only work by Gagana, developed on the `gagana/latent-manifold-steering` branch and merged into `master`. The always-current, auto-generated summary is
[`research/outputs/report.md`](../research/outputs/report.md); a short written summary is
[`docs/research_findings.md`](../docs/research_findings.md).

## Questions

1. When an LLM's price responds to a rival's price, is that response visible and causally locatable inside the
   model's activations, or only observable as external behaviour?
2. (Pre-registered.) Does the model respond *strategically* to a rival breaking an established pattern, for example
   by cutting its price after an undercut (punishment-like) and returning once the rival returns, and does steering
   the internal representation change that strategic response or only the overall price level?

## Setup

Two-firm repeated Bertrand game with logit demand and a ten-point price grid (Nash = index 2, monopoly = index 7).
The pricing agent is `Qwen2.5-7B-Instruct` at a pinned revision (0.5B-32B for the size comparison), run with Hugging
Face on Modal GPUs. The price is read from the digit distribution after a forced answer prefix
(`{"price_index": `); free and prefixed generations are audited with a strict JSON parser, and malformed outputs
are logged, never replaced. An earlier raw-prompt pipeline was found on re-audit to accept text copied from the
prompt's own example, and all of its output was discarded.

## Part 1: where the rival's price lives in the model

- Editing only the rival's displayed last price moved the model's price in 96% of matched prompt pairs, more than
  an irrelevant-number control, but not in the economically rational direction: a rival price cut and a rival price
  rise both lowered the model's price on average (Spearman rho ~ 0 with the one-round best response).
- The rival's price is linearly decodable from hidden states (held-out R^2 up to 0.86).
- Activation patching over 48 matched pairs localises the effect: rival-price tokens through about layer 10, the
  reply-start token at layer 18, the answer token by layer 20.
- A steering vector built at the answer token (layer 20) reproduces the real edit's effect on held-out histories
  (0.65 steps vs 0.73 for the real edit) and on 96 separately pre-registered histories. Its cosine similarity with
  the model's general high-vs-low price direction is 0.77-0.81, so much of it may be a general price-level route.

## Part 2: strategic-deviation study (pre-registered, 26 October run)

**Design.** The model plays 16-round games against seven scripted rivals: stable high price, one-off undercut,
persistent undercut, gradual decline, delayed return after an undercut, competitive (Nash) price throughout, and an
unexpected price rise. Fixed-history arms compare a sudden drop with a gradual decline ending at the same price.
Steering arms: none, zero-vector sham, the learned vector at strengths -1, +1, +2 and after the deviation only,
three norm-matched random vectors, and a generic price direction. Hypotheses, metrics and decision rules are in
[`research/protocols/strategic_deviation_v1.md`](../research/protocols/strategic_deviation_v1.md). A preflight audit
before launch found and fixed three design problems (duplicate histories, one history overlapping the vector's
training data, too few distinct fixed histories); see amendment A1 in the protocol and `research/preflight/`.

| Batch | Designation | Runs | Failed | Scored decisions | Strict-parse validity | Billed (Modal) |
|---|---|---|---|---|---|---|
| `sd_v1_smoke_7b_001` | smoke | 55 | 0 | 484 | 100% | $0.05 |
| `sd_v1_primary_7b_001` | confirmatory | 1,656 | 0 | 23,616 | 100% (656/656 greedy agreement) | $1.81 |
| `sd_v1_onefactor_7b_001` | exploratory | 656 | 0 | 10,496 | 100% (1,531/1,536 greedy agreement) | $1.08 |

All 8 identical reruns reproduced exactly; the sham changed no output.

**Pre-registered hypotheses** (main batch; 95% cluster-bootstrap CI over 16 independent histories; Holm-adjusted p):

| Hypothesis | Estimate (price steps) | 95% CI | Holm p | Verdict |
|---|---|---|---|---|
| H1 price cut right after a one-off undercut | -0.08 | [-0.25, +0.09] | 0.81 | inconclusive |
| H2a return to the previous price after the rival returns | -0.31 | [-0.59, -0.10] | 0.07 | inconclusive |
| H2b persistent vs one-off undercut, after the return | +0.04 | [-0.06, +0.12] | 0.81 | not supported (CI within +/-0.25) |
| H3 sudden vs gradual drop to the same price | -0.22 | [-0.52, +0.08] | 0.49 | inconclusive |
| H4 learned vector vs norm-matched random vectors | -0.43 | [-0.56, -0.32] | 0.002 | **supported** |
| H5 steering changes the response to an undercut | +0.13 | [-0.02, +0.28] | 0.46 | inconclusive |

**Main findings**

- **Supra-competitive default.** Against a stable rival the model prices 3.1 steps above Nash and 1.6 above the
  one-round best response (collusion index 0.87). This holds in every tested setting (index 0.73-0.95 across prompt
  templates, temperatures, sampling seeds, economic settings, deviation sizes and history lengths). It is a fixed
  high-price default, not evidence of coordination: the rival is scripted and cannot reciprocate.
- **A reaction to change, not punishment.** Two to four rounds after a one-off undercut the price falls 0.71 steps
  below the stable control, in all 16 histories. But an unexpected rival price *increase* produces a larger fall
  (post-deviation mean -0.52 vs -0.23), so the price after an undercut ends up 0.29 steps higher than after a raise
  [+0.13, +0.45]. Under a gradual rival decline the model *raises* its price (+0.24). The smoke test's small price
  rise right after an undercut did not replicate.
- **Prompt dependence.** With a log-style prompt the model does cut its price immediately (-0.56) and stays lower
  after the rival returns (-0.84); with a system-message prompt neither appears. Whether the model looks punitive
  depends on prompt format.
- **Steering moves the price level, not the strategy.** The learned vector shifts the price in both directions
  (strength -1: +0.77 steps; +1: -0.51; +2: -0.79), far more than random vectors of the same norm (-0.08 to -0.18),
  but less than the generic price direction (-0.83). Its small effect on the undercut response does not change sign
  with the steering direction, and its effect on recovery is matched by random vectors.
- **Biggest source of variation:** the pre-play history (between-history SD 0.4-0.6 steps), then prompt template
  and economic setting.

| | |
|---|---|
| ![Trajectories](../research/outputs/figures/01_trajectories.png) | ![Direction specificity](../research/outputs/figures/23_direction_specificity.png) |
| ![H1-H5](../research/outputs/figures/21_hypotheses.png) | ![Dose-response](../research/outputs/figures/12_dose_response.png) |

The behavioural consistency grid (one row per behaviour, one column per parameter dimension, with effect sizes,
CIs, sample counts, validity rates, seeds and supporting run IDs) is
[`research/outputs/tables/master_consistency.csv`](../research/outputs/tables/master_consistency.csv), summarised in
[`consistency_by_dimension.csv`](../research/outputs/tables/consistency_by_dimension.csv) and in the figure below.

![Consistency grid](../research/outputs/figures/22_consistency_dimensions.png)

## What this does and does not show

The steering result shows a real, located causal path from the rival's displayed price to the model's output, and
that the learned direction is more effective than random directions. It does not show that the path is specific to
rival-price information (it behaves like part of a general price axis), and it does not show strategic control.
The behaviour is better described as a robust high-price default plus a non-directional reaction to changes in the
rival's pattern than as a recognisable strategy such as tit-for-tat. No part of this branch tests two LLM agents
responding to each other, so no claim about coordination, collusion or intent follows.

**Limitations.** One model (Qwen2.5-7B for the strategic study); scripted, non-learning rivals; 16 histories in the
confirmatory batch and 8 per level in the robustness batch; prices read from the digit distribution after a forced
prefix (validated by strict-parse audits); one learned steering direction.

**Next.** Symmetric raise/undercut scripts to separate surprise from direction; prompts that hide the horizon
(the price jumps 1.3 steps in the final round); 14B/32B under the same protocol; two-LLM self-play.

## Reproducing and extending

```bash
pip install -r requirements.txt
python -m pytest -q                                   # 204 tests

# plan -> launch on Modal (detached, resumable) -> sync into the registry -> analyse
python scripts/preflight_sd.py --spec research/configs/sd_v1_primary_7b_001.json   # design audit, no GPU
python scripts/research.py plan   --spec research/configs/sd_v1_primary_7b_001.json   # units, model calls, GPU-hours, cost
python scripts/research.py launch --spec research/configs/sd_v1_primary_7b_001.json --shards 2 --max-seconds 7200
python scripts/research.py sync   --batch sd_v1_primary_7b_001 --bundle      # or --from-tar <downloaded tarball>
python scripts/research.py cost   --batch sd_v1_primary_7b_001 --since <ISO hour> --until <ISO hour>
python scripts/research.py analyze                    # tables, figures (PNG/SVG/PDF), report
python scripts/research.py verify                     # registry vs raw checksums
python scripts/research.py run-local --spec <spec>    # CPU debugging with a small model
```

Adding an experiment: [`docs/experiment_tracking.md`](../docs/experiment_tracking.md). Staged robustness plan:
[`research/protocols/robustness_grid_v1.md`](../research/protocols/robustness_grid_v1.md).

## Where things are

```
src/interpretability/      Part 1: strict parser, matched prompt pairs, probes, activation patching, transfer vector
src/research/              Part 2: economics presets, prompt templates, scripted rivals, closed-loop runner, steering,
                           configs, append-only registry, metrics, H1-H5 estimators, statistics, figures, report
scripts/research.py        CLI: plan / launch / sync / cost / analyze / verify / run-local
scripts/modal_research.py  Modal backend (sharded, budget-guarded, resumable; results on a Modal volume)
scripts/preflight_sd.py    Pre-launch scientific audit of a batch spec
research/protocols/        Pre-registered protocol (+ amendment A1) and staged robustness grid
research/configs/          Batch specs (smoke, primary, one-factor) and research/preflight/ audit outputs
research/vectors/          Steering vectors with checksums and training-history manifests
research/registry/         runs.jsonl (2,367 runs), batches.jsonl, legacy.jsonl, compute.jsonl
research/raw/              Per-run raw results (gzipped JSON, sha256 in the registry)
research/outputs/          tables/, figures/ (with manifest.json linking each figure to its source runs), report.md
```
