# Strategic pricing research: consolidated report

_Auto-generated 2026-10-25T21:54:51+00:00 from the registry (hash `1c4c4374e3ddec82`). Do not edit by hand; run `python scripts/research.py analyze`._

## 1. Executive summary

Evidence below is from the strategic-deviation protocol only (legacy results are listed separately).

**Supported (overall 95% CI excludes zero in the predicted direction, or within the equivalence margin for null predictions):**

- none

**Absent or opposite to prediction:**

- none

**Unresolved (inconclusive, insufficient data, or not yet tested):**

- rival_price_responsiveness: not tested.
- unexpected_deviation_sensitivity: insufficient.
- absolute_price_response: insufficient.
- punishment_like_reduction: insufficient.
- persistent_deviation_response: insufficient.
- recovery_after_return: insufficient.
- raise_response: not tested.
- supra_competitive_default: insufficient.
- above_best_response: insufficient.
- steering_price_level: insufficient.
- steering_random_level: insufficient.
- steering_generic_level: not tested.
- steering_sham: insufficient.
- steering_x_deviation: insufficient.
- steering_x_persistent: insufficient.
- steering_x_recovery: insufficient.
- random_x_deviation: insufficient.

## 2. Experiment inventory

| batch | designation | status | units | decisions | gpu_seconds |
|---|---|---|---|---|---|
| sd_v1_smoke_7b_001 | smoke | completed | 55 | 484 | 140.31 |

Total completed units: 55; failed: 0; model decisions: 484; summed unit runtime: 0.04 h. 

Legacy (pre-registry) records: 39 (see research/registry/legacy.jsonl).

## 3. Parameter coverage

- **model**: 7b (55)
- **template_id**: v1 (53), v3_system (2)
- **temperature**: 0.0 (51), 0.7 (4)
- **deviation_magnitude**: 5 (55)
- **prefix_rounds**: 4 (55)
- **recovery_delay**: 3 (55)
- **econ_id**: base (55)
- **steering**: learned:learned_answer_L20_c3d (16), none (23), random0 (8), sham (8)
- **alpha**: 0.0 (23), 1.0 (32)

Untested dimensions are listed in research/protocols/robustness_grid_v1.md (planned stages C-E).

## 4. Behavioural consistency

| behaviour | predicted | mean | ci_low | ci_high | n_clusters | status | replication_status | validity_rate |
|---|---|---|---|---|---|---|---|---|
| rival_price_responsiveness | - | - | - | - | - | not tested | insufficient evidence | - |
| unexpected_deviation_sensitivity | negative | 0.14 | -0.94 | 1.22 | 2.00 | insufficient | insufficient evidence | 1.00 |
| absolute_price_response | negative | -0.19 | -0.65 | 0.26 | 2.00 | insufficient | insufficient evidence | 1.00 |
| punishment_like_reduction | negative | 0.30 | 0.25 | 0.31 | 2.00 | insufficient | insufficient evidence | 1.00 |
| persistent_deviation_response | negative | 0.25 | 0.08 | 0.42 | 2.00 | insufficient | insufficient evidence | 1.00 |
| recovery_after_return | near_zero | 0.39 | 0.03 | 0.54 | 2.00 | insufficient | insufficient evidence | 1.00 |
| raise_response | - | - | - | - | - | not tested | insufficient evidence | - |
| supra_competitive_default | positive | 0.90 | 0.90 | 0.91 | 2.00 | insufficient | insufficient evidence | 1.00 |
| above_best_response | positive | 1.96 | 1.91 | 2.08 | 2.00 | insufficient | insufficient evidence | 1.00 |
| steering_price_level | negative | -0.80 | -0.81 | -0.78 | 2.00 | insufficient | insufficient evidence | 1.00 |
| steering_random_level | near_zero | 0.04 | 0.03 | 0.04 | 2.00 | insufficient | insufficient evidence | 1.00 |
| steering_generic_level | - | - | - | - | - | not tested | insufficient evidence | - |
| steering_sham | near_zero | 0.00 | 0.00 | 0.00 | 2.00 | insufficient | insufficient evidence | 1.00 |
| steering_x_deviation | nonzero | -0.04 | -0.23 | 0.16 | 2.00 | insufficient | insufficient evidence | 1.00 |
| steering_x_persistent | nonzero | -0.18 | -0.29 | -0.06 | 2.00 | insufficient | insufficient evidence | 1.00 |
| steering_x_recovery | nonzero | -0.16 | -0.23 | -0.08 | 2.00 | insufficient | insufficient evidence | 1.00 |
| random_x_deviation | near_zero | 0.03 | -0.09 | 0.15 | 2.00 | insufficient | insufficient evidence | 1.00 |

Full grid with every factor view: research/outputs/tables/behaviour_cells.csv.

## 5. Strategic-deviation results

- **rival_price_responsiveness** (E(rival at Nash) - E(rival stable high), live rounds after t_d): - [-, -], n=0 histories -> not tested.
- **unexpected_deviation_sensitivity** (same final rival price, sudden vs gradual history): 0.14 [-0.94, 1.22], n=2 histories -> insufficient.
- **absolute_price_response** (decision under always-low vs always-high rival): -0.19 [-0.65, 0.26], n=2 histories -> insufficient.
- **punishment_like_reduction** (one-shot undercut vs stable, first round after observing it): 0.30 [0.25, 0.31], n=2 histories -> insufficient.
- **persistent_deviation_response** (persistent undercut vs stable, all post rounds): 0.25 [0.08, 0.42], n=2 histories -> insufficient.
- **recovery_after_return** (price gap 1-3 rounds after the rival returns to the high price): 0.39 [0.03, 0.54], n=2 histories -> insufficient.
- **raise_response** (unexpected rival price increase vs stable): - [-, -], n=0 histories -> not tested.

## 6. Activation-steering results

- **steering_price_level** (steered minus unsteered expected price (same rival script)): -0.80 [-0.81, -0.78], n=2 histories -> insufficient.
- **steering_random_level** (norm-matched random direction, same strengths): 0.04 [0.03, 0.04], n=2 histories -> insufficient.
- **steering_generic_level** (generic price direction (positive control)): - [-, -], n=0 histories -> not tested.
- **steering_sham** (zero-vector hook): 0.00 [0.00, 0.00], n=2 histories -> insufficient.
- **steering_x_deviation** (change in one-shot deviation response caused by steering (DiD)): -0.04 [-0.23, 0.16], n=2 histories -> insufficient.
- **steering_x_persistent** (change in persistent-deviation response caused by steering (DiD)): -0.18 [-0.29, -0.06], n=2 histories -> insufficient.
- **steering_x_recovery** (change in post-return gap caused by steering (DiD)): -0.16 [-0.23, -0.08], n=2 histories -> insufficient.
- **random_x_deviation** (random-direction control for the DiD): 0.03 [-0.09, 0.15], n=2 histories -> insufficient.

Interpretation rule (pre-registered): a steering direction that shifts price level but leaves the DiD deviation-response terms at zero is classified as a generic price-level effect, not control over a strategic mechanism.

## 7. Robustness analysis

**block**: above_best_response: primary=insufficient, repeatability=insufficient, sweep:decoding=insufficient, sweep:template_id=insufficient; punishment_like_reduction: primary=insufficient, sweep:decoding=insufficient, sweep:template_id=insufficient; recovery_after_return: primary=insufficient, sweep:decoding=insufficient, sweep:template_id=insufficient; supra_competitive_default: primary=insufficient, sweep:decoding=insufficient, sweep:template_id=insufficient

**history_seed**: above_best_response: 0=insufficient, 1=insufficient; absolute_price_response: 0=insufficient, 1=insufficient; persistent_deviation_response: 0=insufficient, 1=insufficient; punishment_like_reduction: 0=insufficient, 1=insufficient; random_x_deviation: 0=insufficient, 1=insufficient; recovery_after_return: 0=insufficient, 1=insufficient; steering_price_level: 0=insufficient, 1=insufficient; steering_random_level: 0=insufficient, 1=insufficient; steering_sham: 0=insufficient, 1=insufficient; steering_x_deviation: 0=insufficient, 1=insufficient; steering_x_persistent: 0=insufficient, 1=insufficient; steering_x_recovery: 0=insufficient, 1=insufficient; supra_competitive_default: 0=insufficient, 1=insufficient; unexpected_deviation_sensitivity: 0=insufficient, 1=insufficient

**temperature**: above_best_response: 0.0=insufficient, 0.7=insufficient; punishment_like_reduction: 0.0=insufficient, 0.7=insufficient; recovery_after_return: 0.0=insufficient, 0.7=insufficient; supra_competitive_default: 0.0=insufficient, 0.7=insufficient

**template_id**: above_best_response: v1=insufficient, v3_system=insufficient; punishment_like_reduction: v1=insufficient, v3_system=insufficient; recovery_after_return: v1=insufficient, v3_system=insufficient; supra_competitive_default: v1=insufficient, v3_system=insufficient

## 8. Figures

### 01_trajectories

![01_trajectories](figures/01_trajectories.png)

Mean expected price per live round; vertical line = deviation round. Source: `src/research/plots.py:fig_trajectories`, tables trajectories, 8 runs (hash `59efd937b8de3f44`).

### 02_deviation_response

![02_deviation_response](figures/02_deviation_response.png)

Per-round matched difference with 95% cluster-bootstrap CI. Source: `src/research/plots.py:fig_deviation_response`, tables pair_traj, 9 runs (hash `d4b709ce2b29dfdb`).

### 03_punishment_recovery

![03_punishment_recovery](figures/03_punishment_recovery.png)

One-shot, delayed-return and persistent deviations. Source: `src/research/plots.py:fig_punish_recover`, tables pair_traj, 9 runs (hash `d4b709ce2b29dfdb`).

### 04_steering_trajectories

![04_steering_trajectories](figures/04_steering_trajectories.png)

Learned direction vs random control and baseline. Source: `src/research/plots.py:fig_steer_traj`, tables trajectories, 23 runs (hash `e5eaaa5219aab6e2`).

### 05_steering_vs_random

![05_steering_vs_random](figures/05_steering_vs_random.png)

Mean per-round shift with 95% CI. Source: `src/research/plots.py:fig_steer_vs_random`, tables steer_level, 24 runs (hash `4fc3a2b6394449c3`).

### 06_level_vs_interaction

![06_level_vs_interaction](figures/06_level_vs_interaction.png)

Points on the x-axis only = generic price shift; off-axis = changes deviation responsiveness. Source: `src/research/plots.py:fig_level_vs_interaction`, tables steer_level, did, 24 runs (hash `4fc3a2b6394449c3`).

### 07_seed_distributions

![07_seed_distributions](figures/07_seed_distributions.png)

Unit-level spread; bar = mean. Source: `src/research/plots.py:fig_seed_dist`, tables pairs, 9 runs (hash `d4b709ce2b29dfdb`).

### 15_coverage

![15_coverage](figures/15_coverage.png)

Counts of completed run units. Source: `src/research/plots.py:fig_coverage`, tables units, 55 runs (hash `aa4910c5d7f7042b`).

### 17_best_response

![17_best_response](figures/17_best_response.png)

Mean expected price conditional on the rival's previous price. Source: `src/research/plots.py:fig_br`, tables trajectories, 15 runs (hash `a5987a6d6d7592b7`).

### 18_collusion_index

![18_collusion_index](figures/18_collusion_index.png)

Per-game joint collusion index. Source: `src/research/plots.py:fig_collusion`, tables units, 39 runs (hash `502a9d2a6beec3d4`).

### 12_dose_response

![12_dose_response](figures/12_dose_response.png)

Means with 95% CI across histories. Source: `src/research/plots.py:fig_dose`, tables steer_level, did, 24 runs (hash `4fc3a2b6394449c3`).

### 08_template_robustness

![08_template_robustness](figures/08_template_robustness.png)

Effect estimate (95% CI) by template_id. Source: `src/research/plots.py:fig_factor`, tables behaviour_cells, 15 runs (hash `a5987a6d6d7592b7`).

### 09_temperature

![09_temperature](figures/09_temperature.png)

Effect estimate (95% CI) by temperature. Source: `src/research/plots.py:fig_factor`, tables behaviour_cells, 15 runs (hash `a5987a6d6d7592b7`).

- 10_history_length: not generated (no variation in prefix_rounds)
- 11_deviation_magnitude: not generated (no variation in deviation_magnitude)
### 13_forest

![13_forest](figures/13_forest.png)

Colour = pre-declared cell status. Source: `src/research/plots.py:fig_forest`, tables behaviour_cells, 41 runs (hash `157b21b0795d9619`).

### 14_consistency_heatmap

![14_consistency_heatmap](figures/14_consistency_heatmap.png)

Status per behaviour and tested parameter level. Source: `src/research/plots.py:fig_consistency_heatmap`, tables behaviour_cells, 41 runs (hash `157b21b0795d9619`).

### 19_negative_results

![19_negative_results](figures/19_negative_results.png)

Behaviours whose evidence is absent, inconclusive or mixed. Source: `src/research/plots.py:fig_negative`, tables behaviour_cells, 0 runs (hash `4f53cda18c2baa0c`).

- 16_cross_model: not generated (no variation in model)
### 20_run_dashboard

![20_run_dashboard](figures/20_run_dashboard.png)

Completion and validity per batch. Source: `src/research/plots.py:fig_dashboard`, tables registry, 55 runs (hash `aa4910c5d7f7042b`).

## 9. Limitations and interpretation

- **High prices** and **supra-competitive outcomes** (collusion index > 0) describe outcomes, not mechanisms; a model with a fixed high-price default produces them against any rival.
- **Strategic conditioning** requires a response that depends on the rival's behaviour beyond its current price level (e.g. sudden vs gradual histories ending at the same price, condition H).
- **Punishment-like behaviour** is a matched price reduction after a rival undercut; it is not evidence of intent, and a myopic best-responder also lowers its price after an undercut.
- **Coordination** would require mutual conditioning sustaining prices above competitive levels; scripted rivals cannot establish it. **Intentional collusion** is not testable with these experiments.
- Actions are read from the digit distribution after a forced answer prefix; strict-parse audits of free and prefixed generations are reported per batch and never substituted for missing actions.
- Greedy decoding is deterministic: replication units are distinct histories (history_seed), not model seeds.

## 10. Next experiments

- Resolve: rival_price_responsiveness, unexpected_deviation_sensitivity, absolute_price_response, punishment_like_reduction, persistent_deviation_response, recovery_after_return, raise_response, supra_competitive_default, above_best_response, steering_price_level, steering_random_level, steering_generic_level, steering_sham, steering_x_deviation, steering_x_persistent, steering_x_recovery, random_x_deviation.
- See research/protocols/robustness_grid_v1.md for the staged plan and cost estimates.

## Legacy evidence (pre-registry, separate protocols)

- `legacy:runs/a1_0.5b.json` (rival_price_edits_phase_a1; model Qwen/Qwen2.5-0.5B-Instruct; revision 7ae557604a): Phase A.1: 24 histories x (control, nonce, cut/raise x stale/realistic); digit scoring + greedy strict parse
- `legacy:runs/a1_1.5b.json` (rival_price_edits_phase_a1; model Qwen/Qwen2.5-1.5B-Instruct; revision 989aa7980e): Phase A.1: 24 histories x (control, nonce, cut/raise x stale/realistic); digit scoring + greedy strict parse
- `legacy:runs/a1_14b.json` (rival_price_edits_phase_a1; model Qwen/Qwen2.5-14B-Instruct; revision cf98f3b3bb): Phase A.1: 24 histories x (control, nonce, cut/raise x stale/realistic); digit scoring + greedy strict parse
- `legacy:runs/a1_32b.json` (rival_price_edits_phase_a1; model Qwen/Qwen2.5-32B-Instruct; revision 5ede1c97bb): Phase A.1: 24 histories x (control, nonce, cut/raise x stale/realistic); digit scoring + greedy strict parse
- `legacy:runs/a1_3b.json` (rival_price_edits_phase_a1; model Qwen/Qwen2.5-3B-Instruct; revision aa8e725379): Phase A.1: 24 histories x (control, nonce, cut/raise x stale/realistic); digit scoring + greedy strict parse
- `legacy:runs/a1_7b.json` (rival_price_edits_phase_a1; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): Phase A.1: 24 histories x (control, nonce, cut/raise x stale/realistic); digit scoring + greedy strict parse
- `legacy:runs/b2_0.5b.json` (preregistered_fresh_history_b2; model Qwen/Qwen2.5-0.5B-Instruct; revision 7ae557604a): B2 trend-break test (docs/prereg_deviation_b2.md)
- `legacy:runs/b2_1.5b.json` (preregistered_fresh_history_b2; model Qwen/Qwen2.5-1.5B-Instruct; revision 989aa7980e): B2 trend-break test (docs/prereg_deviation_b2.md)
- `legacy:runs/b2_14b.json` (preregistered_fresh_history_b2; model Qwen/Qwen2.5-14B-Instruct; revision cf98f3b3bb): B2 trend-break test (docs/prereg_deviation_b2.md)
- `legacy:runs/b2_32b.json` (preregistered_fresh_history_b2; model Qwen/Qwen2.5-32B-Instruct; revision 5ede1c97bb): B2 trend-break test (docs/prereg_deviation_b2.md)
- `legacy:runs/b2_3b.json` (preregistered_fresh_history_b2; model Qwen/Qwen2.5-3B-Instruct; revision aa8e725379): B2 trend-break test (docs/prereg_deviation_b2.md)
- `legacy:runs/b2_7b.json` (preregistered_fresh_history_b2; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): B2 trend-break test (docs/prereg_deviation_b2.md)
- `legacy:runs/d1_0.5b.json` (repeated_games_d1; model Qwen/Qwen2.5-0.5B-Instruct; revision 7ae557604a): 15-round games vs 8 scripted/reactive rivals, greedy + 4 sampled
- `legacy:runs/d1_1.5b.json` (repeated_games_d1; model Qwen/Qwen2.5-1.5B-Instruct; revision 989aa7980e): 15-round games vs 8 scripted/reactive rivals, greedy + 4 sampled
- `legacy:runs/d1_14b.json` (repeated_games_d1; model Qwen/Qwen2.5-14B-Instruct; revision cf98f3b3bb): 15-round games vs 8 scripted/reactive rivals, greedy + 4 sampled
- `legacy:runs/d1_32b.json` (repeated_games_d1; model Qwen/Qwen2.5-32B-Instruct; revision 5ede1c97bb): 15-round games vs 8 scripted/reactive rivals, greedy + 4 sampled
- `legacy:runs/d1_3b.json` (repeated_games_d1; model Qwen/Qwen2.5-3B-Instruct; revision aa8e725379): 15-round games vs 8 scripted/reactive rivals, greedy + 4 sampled
- `legacy:runs/d1_7b.json` (repeated_games_d1; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): 15-round games vs 8 scripted/reactive rivals, greedy + 4 sampled
- `legacy:runs/c3d_7b.json` (steering_transfer_and_steered_games; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): C3 transfer vector + steered games (7B)
- `legacy:runs/d1steer_7b_random.json` (steered_games_random_control; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): games steered with a norm-matched random vector
- `legacy:phase_c/c1_7b.json` (activation_patching_layers; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): patching rival/profit/answer sites by layer
- `legacy:phase_c/c1pos_7b.json` (activation_patching_positions; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): single-position patching, layers 16/18/20
- `legacy:phase_c/c2_7b_L10_after_rival.json` (steering_dose_response_mean_difference; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): mean-difference steering on A.1 controls
- `legacy:phase_c/c2_7b_L13_answer.json` (steering_dose_response_mean_difference; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): mean-difference steering on A.1 controls
- `legacy:phase_c/c2_7b_L16_after_rival.json` (steering_dose_response_mean_difference; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): mean-difference steering on A.1 controls
- `legacy:phase_c/c2_7b_L21_answer.json` (steering_dose_response_mean_difference; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): mean-difference steering on A.1 controls
- `legacy:phase_c/c2_7b_L21_answer_controls.json` (steering_dose_response_mean_difference; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): mean-difference steering on A.1 controls
- `legacy:phase_c/c2_7b_L3_answer_rule.json` (steering_dose_response_mean_difference; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): mean-difference steering on A.1 controls
- `legacy:phase_c/c2_7b_L8_rival.json` (steering_dose_response_mean_difference; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): mean-difference steering on A.1 controls
- `legacy:phase_b/qwen7b_b1.json` (probing_dataset_b1; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): B1 activations (360 prompts) for probes
- `legacy:phase_b2/b2_confirm_7b.json` (preregistered_fresh_history_b2; model Qwen/Qwen2.5-7B-Instruct; revision a09a35458c): B2 (7B, original location)
- `legacy:phase_a_preflight/phase_a_economic_preflight.json` (economic_preflight; model unknown; revision unknown): CPU best-response analysis of Phase A
- `legacy:cpu_0_5b/phase_c_summary_0_5b.json` (cpu_dev_runs_0_5b; model unknown; revision unknown): Qwen2.5-0.5B CPU development runs
- `legacy:cpu_0_5b/phase_c_summary_0_5b_steer.json` (cpu_dev_runs_0_5b; model unknown; revision unknown): Qwen2.5-0.5B CPU development runs
- `legacy:cpu_0_5b/probes.json` (cpu_dev_runs_0_5b; model unknown; revision unknown): Qwen2.5-0.5B CPU development runs
- `legacy:cpu_0_5b/qwen0_5b_a1.json` (cpu_dev_runs_0_5b; model Qwen/Qwen2.5-0.5B-Instruct; revision 7ae557604a): Qwen2.5-0.5B CPU development runs
- `legacy:cpu_0_5b/qwen0_5b_b1.json` (cpu_dev_runs_0_5b; model Qwen/Qwen2.5-0.5B-Instruct; revision 7ae557604a): Qwen2.5-0.5B CPU development runs
- `legacy:cpu_0_5b/qwen0_5b_c1.json` (cpu_dev_runs_0_5b; model Qwen/Qwen2.5-0.5B-Instruct; revision 7ae557604a): Qwen2.5-0.5B CPU development runs
- `legacy:cpu_0_5b/qwen0_5b_c2.json` (cpu_dev_runs_0_5b; model Qwen/Qwen2.5-0.5B-Instruct; revision 7ae557604a): Qwen2.5-0.5B CPU development runs