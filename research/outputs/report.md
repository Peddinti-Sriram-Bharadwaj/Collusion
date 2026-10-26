# Strategic pricing research: consolidated report

_Auto-generated 2026-10-26T00:18:23+00:00 from the registry (hash `b8b7f235212f913f`). Do not edit by hand; run `python scripts/research.py analyze`._

## 1. Executive summary

Evidence below is from the strategic-deviation protocol only (legacy results are listed separately).

**Supported (overall 95% CI excludes zero in the predicted direction, or within the equivalence margin for null predictions):**

- delayed_deviation_response: -0.71 [-0.97, -0.49], 16 independent histories; replication across tested settings: single setting only.
- persistent_deviation_response: -0.27 [-0.47, -0.11], 16 independent histories; replication across tested settings: single setting only.
- raise_delayed_response: -0.52 [-0.71, -0.33], 16 independent histories; replication across tested settings: single setting only.
- high_price_default: 3.07 [2.83, 3.40], 16 independent histories; replication across tested settings: single setting only.
- supra_competitive_pricing: 0.87 [0.84, 0.89], 16 independent histories; replication across tested settings: single setting only.
- steering_price_level: -0.65 [-0.80, -0.53], 16 independent histories; replication across tested settings: robust.
- steering_specificity: -0.52 [-0.63, -0.43], 16 independent histories; replication across tested settings: robust.
- steering_random_level: -0.13 [-0.19, -0.08], 16 independent histories; replication across tested settings: mixed.
- steering_generic_level: -0.83 [-0.99, -0.71], 16 independent histories; replication across tested settings: single setting only.
- steering_sham: 0.00 [0.00, 0.00], 16 independent histories; replication across tested settings: single setting only.
- steering_x_recovery: 0.21 [0.01, 0.45], 16 independent histories; replication across tested settings: mixed.
- random_x_deviation: 0.03 [-0.05, 0.10], 16 independent histories; replication across tested settings: robust.

**Absent or opposite to prediction:**

- gradual_decline_response: 0.24 [0.04, 0.44] (opposite).
- raise_response: -0.06 [-0.17, 0.04] (absent).
- best_response_alignment: 1.63 [1.44, 1.87] (opposite).

**Unresolved (inconclusive, insufficient data, or not yet tested):**

- rival_price_responsiveness: inconclusive.
- absolute_price_response: inconclusive.
- unexpected_deviation_sensitivity: inconclusive.
- punishment_like_reduction: inconclusive.
- recovery_after_return: inconclusive.
- self_play_stability: untested.
- steering_x_deviation: inconclusive.
- steering_x_persistent: inconclusive.

## 1b. Pre-registered hypotheses H1-H5 (confirmatory batch only)

| hypothesis | name | predicted | mean | ci_low | ci_high | n_clusters | p_two_sided | p_holm | validity_rate | status | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | punishment-like response | negative | -0.075 | -0.251 | 0.086 | 16 | 0.405 | 0.810 | 1.000 | inconclusive | inconclusive |
| H2a | recovery after the rival returns | near_zero | -0.313 | -0.590 | -0.104 | 16 | 0.013 | 0.066 | 1.000 | inconclusive | inconclusive |
| H2b | persistent vs one-shot after the return | negative | 0.037 | -0.056 | 0.119 | 16 | 0.408 | 0.810 | 1.000 | absent | not supported: whole CI within +-0.25 steps of zero |
| H3 | expectation violation | negative | -0.216 | -0.515 | 0.083 | 16 | 0.162 | 0.487 | 1.000 | inconclusive | inconclusive |
| H4 | steering specificity | negative | -0.425 | -0.555 | -0.318 | 16 | 0.000 | 0.001 | 1.000 | supported | supported |
| H5 | steering x deviation | nonzero | 0.125 | -0.022 | 0.283 | 16 | 0.114 | 0.457 | 1.000 | inconclusive | inconclusive |

Estimators: research/protocols/strategic_deviation_v1.md (amendment A1) and src/research/hypotheses.py. n = independent pre-play histories. 'absent' requires the whole CI inside +-0.25 steps; a non-significant estimate with a wider CI is 'inconclusive', never 'absent'.

H4 components: learned level shift -0.51, random -0.08, generic price direction -0.83, learned minus generic 0.32.

### Exploratory contrasts (same confirmatory data; not pre-registered, not multiplicity-adjusted)

| code | name | mean | ci_low | ci_high | n_clusters | status | share_positive |
|---|---|---|---|---|---|---|---|
| X1 | direction specificity of the delayed response | 0.287 | 0.134 | 0.447 | 16 | opposite | - |
| X2 | response to an unexpected rival price rise | -0.517 | -0.714 | -0.329 | 16 | supported | - |
| X3 | delayed response to a one-shot undercut | -0.712 | -0.967 | -0.493 | 16 | supported | - |
| X5 | initial price rise after a one-shot undercut (smoke observation) | -0.075 | -0.251 | 0.086 | 16 | descriptive | 0.562 |
| X4 | end-of-game price jump | 1.289 | 0.838 | 1.737 | 16 | supported | - |

Same estimators per batch (exploratory and smoke batches are descriptive only):

| batch_id | hypothesis | mean | ci_low | ci_high | n_clusters | status |
|---|---|---|---|---|---|---|
| sd_v1_primary_7b_001 | H1 | -0.075 | -0.251 | 0.086 | 16 | inconclusive |
| sd_v1_primary_7b_001 | H2a | -0.313 | -0.590 | -0.104 | 16 | inconclusive |
| sd_v1_primary_7b_001 | H2b | 0.037 | -0.056 | 0.119 | 16 | absent |
| sd_v1_primary_7b_001 | H3 | -0.216 | -0.515 | 0.083 | 16 | inconclusive |
| sd_v1_primary_7b_001 | H4 | -0.425 | -0.555 | -0.318 | 16 | supported |
| sd_v1_primary_7b_001 | H5 | 0.125 | -0.022 | 0.283 | 16 | inconclusive |
| sd_v1_smoke_7b_001 | H1 | 0.231 | 0.217 | 0.245 | 2 | insufficient |
| sd_v1_smoke_7b_001 | H2a | 0.407 | 0.191 | 0.622 | 2 | insufficient |
| sd_v1_smoke_7b_001 | H2b | 0.300 | 0.285 | 0.315 | 2 | insufficient |
| sd_v1_smoke_7b_001 | H3 | 0.142 | -0.937 | 1.220 | 2 | insufficient |
| sd_v1_smoke_7b_001 | H4 | -0.833 | -0.847 | -0.820 | 2 | insufficient |
| sd_v1_smoke_7b_001 | H5 | -0.039 | -0.234 | 0.156 | 2 | insufficient |

## 2. Experiment inventory

| batch | designation | status | units | decisions | gpu_seconds |
|---|---|---|---|---|---|
| sd_v1_primary_7b_001 | confirmatory | completed | 1656 | 23616 | 5269.63 |
| sd_v1_smoke_7b_001 | smoke | completed | 55 | 484 | 140.31 |

Total completed units: 1711; failed: 0; model decisions: 24100; summed unit runtime: 1.50 h. 

Legacy (pre-registry) records: 39 (see research/registry/legacy.jsonl).

## 2b. Validity, repeatability and compute

| batch_id | free_audits | free_valid_rate | greedy_agreement | prefixed_audits | prefixed_valid_rate |
|---|---|---|---|---|---|
| sd_v1_primary_7b_001 | 656 | 1.000 | 1.000 | 6048 | 1.000 |
| sd_v1_smoke_7b_001 | 68 | 1.000 | 0.765 | 172 | 1.000 |

Minimum digit probability mass over all decisions: 1.0000.

Repeatability: 9 identical reruns; max |dE| = 0.00e+00; actions identical in 9/9.

Compute and cost (Modal billing report per app where available; otherwise GPU-seconds x list price):

| batch_id | shards | gpu | container_seconds | est_cost_list_price_usd | modal_billed_usd_app_window | billing_window | recorded_at |
|---|---|---|---|---|---|---|---|
| sd_v1_smoke_7b_001 | 1 | A10 | 161.100 | 0.049 | 0.055 | [2026-10-25T21:00:00, 2026-10-25T22:00:00) hourly buckets, app collusion-research | 2026-10-25T23:07:50.777811Z |
| sd_v1_primary_7b_001 | 2 | A10 | 5471.600 | 1.672 | 1.810 | [2026-10-25T23:00:00, 2026-10-26T00:00:00) hourly buckets, app collusion-research | 2026-10-26T00:05:02.544949Z |

## 3. Parameter coverage

- **model**: 7b (1711)
- **template_id**: v1 (1709), v3_system (2)
- **temperature**: 0.0 (1707), 0.7 (4)
- **deviation_magnitude**: 5 (1711)
- **prefix_rounds**: 4 (1711)
- **recovery_delay**: 3 (1711)
- **econ_id**: base (1711)
- **steering**: generic_price:generic_price_answer_L20_b1 (112), learned:learned_answer_L20_c3d (528), none (207), random0 (296), random1 (224), random2 (224), sham (120)
- **alpha**: -1.0 (112), 0.0 (207), 1.0 (944), 2.0 (448)

Untested dimensions are listed in research/protocols/robustness_grid_v1.md (planned stages C-E).

## 4. Behavioural consistency

| behaviour | predicted | mean | ci_low | ci_high | n_clusters | status | replication_status | validity_rate |
|---|---|---|---|---|---|---|---|---|
| rival_price_responsiveness | negative | 0.24 | -0.06 | 0.52 | 16.00 | inconclusive | single setting only | 1.00 |
| absolute_price_response | negative | 0.15 | -0.20 | 0.50 | 16.00 | inconclusive | single setting only | 1.00 |
| unexpected_deviation_sensitivity | negative | -0.22 | -0.52 | 0.08 | 16.00 | inconclusive | single setting only | 1.00 |
| punishment_like_reduction | negative | -0.07 | -0.25 | 0.09 | 16.00 | inconclusive | single setting only | 1.00 |
| delayed_deviation_response | negative | -0.71 | -0.97 | -0.49 | 16.00 | supported | single setting only | 1.00 |
| persistent_deviation_response | negative | -0.27 | -0.47 | -0.11 | 16.00 | supported | single setting only | 1.00 |
| gradual_decline_response | negative | 0.24 | 0.04 | 0.44 | 16.00 | opposite | single setting only | 1.00 |
| recovery_after_return | near_zero | -0.39 | -0.62 | -0.24 | 16.00 | inconclusive | single setting only | 1.00 |
| raise_response | nonzero | -0.06 | -0.17 | 0.04 | 16.00 | absent | single setting only | 1.00 |
| raise_delayed_response | nonzero | -0.52 | -0.71 | -0.33 | 16.00 | supported | single setting only | 1.00 |
| high_price_default | positive | 3.07 | 2.83 | 3.40 | 16.00 | supported | single setting only | 1.00 |
| supra_competitive_pricing | positive | 0.87 | 0.84 | 0.89 | 16.00 | supported | single setting only | 1.00 |
| best_response_alignment | near_zero | 1.63 | 1.44 | 1.87 | 16.00 | opposite | single setting only | 1.00 |
| self_play_stability | - | - | - | - | - | untested | untested | - |
| steering_price_level | negative | -0.65 | -0.80 | -0.53 | 16.00 | supported | robust | 1.00 |
| steering_specificity | negative | -0.52 | -0.63 | -0.43 | 16.00 | supported | robust | 1.00 |
| steering_random_level | near_zero | -0.13 | -0.19 | -0.08 | 16.00 | supported | mixed | 1.00 |
| steering_generic_level | negative | -0.83 | -0.99 | -0.71 | 16.00 | supported | single setting only | 1.00 |
| steering_sham | near_zero | 0.00 | 0.00 | 0.00 | 16.00 | supported | single setting only | 1.00 |
| steering_x_deviation | nonzero | 0.12 | -0.05 | 0.30 | 16.00 | inconclusive | inconclusive | 1.00 |
| steering_x_persistent | nonzero | 0.17 | -0.01 | 0.36 | 16.00 | inconclusive | mixed | 1.00 |
| steering_x_recovery | nonzero | 0.21 | 0.01 | 0.45 | 16.00 | supported | mixed | 1.00 |
| random_x_deviation | near_zero | 0.03 | -0.05 | 0.10 | 16.00 | supported | robust | 1.00 |

Full grid with every factor view: research/outputs/tables/behaviour_cells.csv.

### Consistency by parameter dimension

| behaviour | dimension | status | n_levels | n_supported | n_opposite | n_absent | n_inconclusive | n_insufficient | sign_agreement | level_mean_min | level_mean_max | level_mean_sd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rival_price_responsiveness | cross_history | mixed | 16.00 | - | - | - | - | - | 0.62 | -1.38 | 1.17 | 0.59 |
| absolute_price_response | cross_history | not replicated | 16.00 | - | - | - | - | - | 0.50 | -0.88 | 1.17 | 0.73 |
| absolute_price_response | cross_batch | inconclusive | 2.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | - | -0.19 | 0.15 | 0.24 |
| unexpected_deviation_sensitivity | cross_history | mixed | 16.00 | - | - | - | - | - | 0.62 | -1.23 | 1.06 | 0.64 |
| unexpected_deviation_sensitivity | cross_batch | inconclusive | 2.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | - | -0.22 | 0.14 | 0.25 |
| punishment_like_reduction | cross_history | not replicated | 16.00 | - | - | - | - | - | 0.56 | -0.86 | 0.36 | 0.36 |
| punishment_like_reduction | cross_batch | inconclusive | 2.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | - | -0.07 | 0.30 | 0.26 |
| delayed_deviation_response | cross_history | robust | 16.00 | - | - | - | - | - | 1.00 | -2.13 | -0.03 | 0.50 |
| delayed_deviation_response | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | -0.71 | -0.06 | 0.46 |
| persistent_deviation_response | cross_history | robust | 16.00 | - | - | - | - | - | 0.81 | -1.49 | 0.06 | 0.39 |
| persistent_deviation_response | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | -0.27 | 0.25 | 0.37 |
| gradual_decline_response | cross_history | mixed | 16.00 | - | - | - | - | - | 0.69 | -0.32 | 1.01 | 0.42 |
| recovery_after_return | cross_history | robust | 16.00 | - | - | - | - | - | 1.00 | -1.84 | -0.02 | 0.41 |
| recovery_after_return | cross_rival_policy | inconclusive | 2.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | - | -0.47 | -0.31 | 0.11 |
| recovery_after_return | cross_batch | inconclusive | 2.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | - | -0.39 | 0.39 | 0.55 |
| raise_response | cross_history | not replicated | 16.00 | - | - | - | - | - | 0.56 | -0.60 | 0.24 | 0.22 |
| raise_delayed_response | cross_history | robust | 16.00 | - | - | - | - | - | 0.94 | -1.34 | 0.26 | 0.41 |
| high_price_default | cross_history | robust | 16.00 | - | - | - | - | - | 1.00 | 2.50 | 5.00 | 0.61 |
| high_price_default | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | 3.07 | 3.65 | 0.41 |
| supra_competitive_pricing | cross_history | robust | 16.00 | - | - | - | - | - | 1.00 | 0.81 | 1.00 | 0.05 |
| supra_competitive_pricing | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | 0.87 | 0.90 | 0.03 |
| best_response_alignment | cross_history | robust | 16.00 | - | - | - | - | - | 1.00 | 1.20 | 2.73 | 0.44 |
| best_response_alignment | cross_rival_policy | not replicated | 7.00 | 0.00 | 7.00 | 0.00 | 0.00 | 0.00 | - | 0.75 | 2.93 | 0.80 |
| best_response_alignment | cross_batch | not replicated | 2.00 | 0.00 | 1.00 | 0.00 | 0.00 | 1.00 | - | 1.63 | 1.98 | 0.25 |
| steering_price_level | cross_history | robust | 16.00 | - | - | - | - | - | 1.00 | -1.43 | -0.40 | 0.28 |
| steering_price_level | cross_rival_policy | robust | 7.00 | 7.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | -0.76 | -0.59 | 0.07 |
| steering_price_level | cross_steering_strength | robust | 2.00 | 2.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | -0.79 | -0.51 | 0.20 |
| steering_price_level | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | -0.80 | -0.65 | 0.10 |
| steering_specificity | cross_history | robust | 16.00 | - | - | - | - | - | 1.00 | -1.07 | -0.36 | 0.21 |
| steering_specificity | cross_rival_policy | robust | 7.00 | 7.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | -0.57 | -0.45 | 0.04 |
| steering_specificity | cross_steering_strength | robust | 2.00 | 2.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | -0.62 | -0.42 | 0.14 |
| steering_specificity | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | -0.83 | -0.52 | 0.22 |
| steering_random_level | cross_history | robust | 16.00 | - | - | - | - | - | 1.00 | -0.50 | -0.02 | 0.12 |
| steering_random_level | cross_rival_policy | robust | 7.00 | 6.00 | 0.00 | 0.00 | 1.00 | 0.00 | - | -0.20 | -0.06 | 0.06 |
| steering_random_level | cross_steering_strength | mixed | 2.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | - | -0.18 | -0.08 | 0.07 |
| steering_random_level | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | -0.13 | 0.04 | 0.12 |
| steering_generic_level | cross_history | robust | 16.00 | - | - | - | - | - | 1.00 | -1.65 | -0.57 | 0.30 |
| steering_generic_level | cross_rival_policy | robust | 7.00 | 7.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | -0.96 | -0.68 | 0.09 |
| steering_sham | cross_history | not replicated | 16.00 | - | - | - | - | - | 0.00 | 0.00 | 0.00 | 0.00 |
| steering_sham | cross_rival_policy | robust | 7.00 | 7.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | 0.00 | 0.00 | 0.00 |
| steering_sham | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | 0.00 | 0.00 | 0.00 |
| steering_x_deviation | cross_history | not replicated | 16.00 | - | - | - | - | - | 0.56 | -0.43 | 0.92 | 0.38 |
| steering_x_deviation | cross_steering_strength | inconclusive | 3.00 | 0.00 | 0.00 | 0.00 | 3.00 | 0.00 | - | 0.12 | 0.12 | 0.00 |
| steering_x_deviation | cross_batch | inconclusive | 2.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | - | -0.04 | 0.12 | 0.11 |
| steering_x_persistent | cross_history | mixed | 16.00 | - | - | - | - | - | 0.69 | -0.56 | 1.17 | 0.39 |
| steering_x_persistent | cross_steering_strength | mixed | 3.00 | 2.00 | 0.00 | 0.00 | 1.00 | 0.00 | - | -0.13 | 0.37 | 0.26 |
| steering_x_persistent | cross_batch | inconclusive | 2.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | - | -0.18 | 0.17 | 0.24 |
| steering_x_recovery | cross_history | robust | 16.00 | - | - | - | - | - | 0.88 | -0.59 | 1.60 | 0.46 |
| steering_x_recovery | cross_rival_policy | mixed | 2.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | - | 0.17 | 0.26 | 0.06 |
| steering_x_recovery | cross_steering_strength | mixed | 3.00 | 2.00 | 0.00 | 0.00 | 1.00 | 0.00 | - | 0.09 | 0.33 | 0.12 |
| steering_x_recovery | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | -0.16 | 0.21 | 0.26 |
| random_x_deviation | cross_history | not replicated | 16.00 | - | - | - | - | - | 0.56 | -0.26 | 0.32 | 0.16 |
| random_x_deviation | cross_steering_strength | robust | 2.00 | 2.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | -0.03 | 0.08 | 0.08 |
| random_x_deviation | cross_batch | robust | 2.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | - | 0.03 | 0.03 | 0.00 |

Labels: robust (>=80% of levels supported, none opposite), mixed, not replicated (>50% absent/opposite), inconclusive, insufficient evidence; cross_history uses sign agreement of per-history estimates (>=0.8 robust).

## 5. Strategic-deviation results

- **rival_price_responsiveness** (E(rival at Nash price throughout) - E(stable high rival), live rounds after t_d): 0.24 [-0.06, 0.52], n=16 histories -> inconclusive.
- **absolute_price_response** (single decision: always-low vs always-high rival history): 0.15 [-0.20, 0.50], n=16 histories -> inconclusive.
- **unexpected_deviation_sensitivity** (same final rival price: sudden drop vs gradual decline (H3)): -0.22 [-0.52, 0.08], n=16 histories -> inconclusive.
- **punishment_like_reduction** (one-shot undercut vs stable, first round after observing it (H1)): -0.07 [-0.25, 0.09], n=16 histories -> inconclusive.
- **persistent_deviation_response** (persistent undercut vs stable, all post-deviation rounds): -0.27 [-0.47, -0.11], n=16 histories -> supported.
- **recovery_after_return** (gap 1-3 rounds after the rival's return is observed (H2a, forgiveness-like if ~0)): -0.39 [-0.62, -0.24], n=16 histories -> inconclusive.
- **raise_response** (unexpected rival price increase vs stable): -0.06 [-0.17, 0.04], n=16 histories -> absent.

## 6. Activation-steering results

- **steering_price_level** (learned vector: steered minus unsteered expected price (same rival script)): -0.65 [-0.80, -0.53], n=16 histories -> supported.
- **steering_random_level** (norm-matched random directions, same strengths): -0.13 [-0.19, -0.08], n=16 histories -> supported.
- **steering_generic_level** (generic price direction (positive control)): -0.83 [-0.99, -0.71], n=16 histories -> supported.
- **steering_sham** (zero-vector hook): 0.00 [0.00, 0.00], n=16 histories -> supported.
- **steering_x_deviation** (change in the one-shot deviation response caused by steering (H5, DiD)): 0.12 [-0.05, 0.30], n=16 histories -> inconclusive.
- **steering_x_persistent** (change in the persistent-deviation response caused by steering (DiD)): 0.17 [-0.01, 0.36], n=16 histories -> inconclusive.
- **steering_x_recovery** (change in the post-return gap caused by steering (DiD)): 0.21 [0.01, 0.45], n=16 histories -> supported.
- **random_x_deviation** (random-direction control for the DiD): 0.03 [-0.05, 0.10], n=16 histories -> supported.

Interpretation rule (pre-registered): a steering direction that shifts price level but leaves the DiD deviation-response terms at zero is classified as a generic price-level effect, not control over a strategic mechanism.

## 7. Robustness analysis

**alpha**

| behaviour | level | mean | ci_low | ci_high | n_clusters | status |
|---|---|---|---|---|---|---|
| steering_price_level | 1.0 | -0.51 | -0.65 | -0.39 | 16.00 | supported |
| steering_price_level | 2.0 | -0.79 | -0.95 | -0.67 | 16.00 | supported |
| steering_specificity | 1.0 | -0.42 | -0.56 | -0.32 | 16.00 | supported |
| steering_specificity | 2.0 | -0.62 | -0.71 | -0.53 | 16.00 | supported |
| steering_random_level | 1.0 | -0.08 | -0.12 | -0.05 | 16.00 | supported |
| steering_random_level | 2.0 | -0.18 | -0.27 | -0.11 | 16.00 | inconclusive |
| steering_x_deviation | -1.0 | 0.12 | -0.18 | 0.41 | 16.00 | inconclusive |
| steering_x_deviation | 1.0 | 0.12 | -0.02 | 0.28 | 16.00 | inconclusive |
| steering_x_deviation | 2.0 | 0.12 | -0.04 | 0.29 | 16.00 | inconclusive |
| steering_x_persistent | -1.0 | -0.13 | -0.41 | 0.13 | 16.00 | inconclusive |
| steering_x_persistent | 1.0 | 0.37 | 0.20 | 0.57 | 16.00 | supported |
| steering_x_persistent | 2.0 | 0.26 | 0.10 | 0.47 | 16.00 | supported |
| steering_x_recovery | -1.0 | 0.09 | -0.24 | 0.37 | 16.00 | inconclusive |
| steering_x_recovery | 1.0 | 0.22 | 0.04 | 0.48 | 16.00 | supported |
| steering_x_recovery | 2.0 | 0.33 | 0.18 | 0.56 | 16.00 | supported |
| random_x_deviation | 1.0 | -0.03 | -0.09 | 0.03 | 16.00 | supported |
| random_x_deviation | 2.0 | 0.08 | -0.02 | 0.19 | 16.00 | supported |

**condition**

| behaviour | level | mean | ci_low | ci_high | n_clusters | status |
|---|---|---|---|---|---|---|
| recovery_after_return | B_one_shot | -0.31 | -0.59 | -0.10 | 16.00 | inconclusive |
| recovery_after_return | F_delayed | -0.47 | -0.68 | -0.31 | 16.00 | opposite |
| best_response_alignment | A_stable | 1.07 | 0.83 | 1.40 | 16.00 | opposite |
| best_response_alignment | B_one_shot | 1.08 | 0.87 | 1.32 | 16.00 | opposite |
| best_response_alignment | C_persistent | 1.88 | 1.66 | 2.14 | 16.00 | opposite |
| best_response_alignment | D_gradual | 2.41 | 2.17 | 2.70 | 16.00 | opposite |
| best_response_alignment | E_nash | 2.93 | 2.83 | 3.04 | 16.00 | opposite |
| best_response_alignment | F_delayed | 1.29 | 1.10 | 1.51 | 16.00 | opposite |
| best_response_alignment | G_raise | 0.75 | 0.48 | 1.04 | 16.00 | opposite |
| steering_price_level | A_stable | -0.76 | -0.99 | -0.59 | 16.00 | supported |
| steering_price_level | B_one_shot | -0.72 | -0.86 | -0.61 | 16.00 | supported |
| steering_price_level | C_persistent | -0.61 | -0.77 | -0.47 | 16.00 | supported |
| steering_price_level | D_gradual | -0.59 | -0.79 | -0.43 | 16.00 | supported |
| steering_price_level | E_nash | -0.64 | -0.71 | -0.56 | 16.00 | supported |
| steering_price_level | F_delayed | -0.62 | -0.76 | -0.49 | 16.00 | supported |
| steering_price_level | G_raise | -0.61 | -0.80 | -0.45 | 16.00 | supported |
| steering_specificity | A_stable | -0.57 | -0.71 | -0.45 | 16.00 | supported |
| steering_specificity | B_one_shot | -0.53 | -0.65 | -0.44 | 16.00 | supported |
| steering_specificity | C_persistent | -0.49 | -0.60 | -0.39 | 16.00 | supported |
| steering_specificity | D_gradual | -0.50 | -0.63 | -0.39 | 16.00 | supported |
| steering_specificity | E_nash | -0.55 | -0.61 | -0.50 | 16.00 | supported |
| steering_specificity | F_delayed | -0.56 | -0.67 | -0.46 | 16.00 | supported |
| steering_specificity | G_raise | -0.45 | -0.59 | -0.34 | 16.00 | supported |
| steering_random_level | A_stable | -0.20 | -0.32 | -0.10 | 16.00 | inconclusive |
| steering_random_level | B_one_shot | -0.19 | -0.25 | -0.14 | 16.00 | supported |
| steering_random_level | C_persistent | -0.12 | -0.19 | -0.06 | 16.00 | supported |
| steering_random_level | D_gradual | -0.09 | -0.21 | 0.02 | 16.00 | supported |
| steering_random_level | E_nash | -0.08 | -0.14 | -0.02 | 16.00 | supported |
| steering_random_level | F_delayed | -0.06 | -0.13 | 0.00 | 16.00 | supported |
| steering_random_level | G_raise | -0.16 | -0.24 | -0.09 | 16.00 | supported |
| steering_generic_level | A_stable | -0.96 | -1.20 | -0.78 | 16.00 | supported |
| steering_generic_level | B_one_shot | -0.89 | -1.03 | -0.76 | 16.00 | supported |
| steering_generic_level | C_persistent | -0.83 | -1.00 | -0.69 | 16.00 | supported |
| steering_generic_level | D_gradual | -0.68 | -0.88 | -0.52 | 16.00 | supported |
| steering_generic_level | E_nash | -0.86 | -0.94 | -0.79 | 16.00 | supported |
| steering_generic_level | F_delayed | -0.84 | -0.99 | -0.71 | 16.00 | supported |
| steering_generic_level | G_raise | -0.75 | -0.95 | -0.59 | 16.00 | supported |
| steering_sham | A_stable | 0.00 | 0.00 | 0.00 | 16.00 | supported |
| steering_sham | B_one_shot | 0.00 | 0.00 | 0.00 | 16.00 | supported |
| steering_sham | C_persistent | 0.00 | 0.00 | 0.00 | 16.00 | supported |
| steering_sham | D_gradual | 0.00 | 0.00 | 0.00 | 16.00 | supported |
| steering_sham | E_nash | 0.00 | 0.00 | 0.00 | 16.00 | supported |
| steering_sham | F_delayed | 0.00 | 0.00 | 0.00 | 16.00 | supported |
| steering_sham | G_raise | 0.00 | 0.00 | 0.00 | 16.00 | supported |
| steering_x_recovery | B_one_shot | 0.17 | -0.09 | 0.47 | 16.00 | inconclusive |
| steering_x_recovery | F_delayed | 0.26 | 0.05 | 0.47 | 16.00 | supported |

**steering**

| behaviour | level | mean | ci_low | ci_high | n_clusters | status |
|---|---|---|---|---|---|---|
| steering_random_level | random0 | -0.06 | -0.11 | -0.00 | 16.00 | supported |
| steering_random_level | random1 | -0.26 | -0.31 | -0.21 | 16.00 | inconclusive |
| steering_random_level | random2 | -0.07 | -0.20 | 0.02 | 16.00 | supported |
| random_x_deviation | random0 | 0.04 | -0.04 | 0.13 | 16.00 | supported |
| random_x_deviation | random1 | -0.04 | -0.18 | 0.06 | 16.00 | supported |
| random_x_deviation | random2 | 0.09 | -0.02 | 0.21 | 16.00 | supported |

## 8. Figures

### 01_trajectories

![01_trajectories](figures/01_trajectories.png)

Mean expected price per live round; vertical line = deviation round. Source: `src/research/plots.py:fig_trajectories`, tables trajectories, 112 runs (hash `751214608e34c976`).

### 02_deviation_response

![02_deviation_response](figures/02_deviation_response.png)

Per-round matched difference with 95% cluster-bootstrap CI. Source: `src/research/plots.py:fig_deviation_response`, tables pair_traj, 96 runs (hash `7e0dbf2f6ead25e2`).

### 02b_fixed_history

![02b_fixed_history](figures/02b_fixed_history.png)

H3: sudden vs gradual at the same final rival price; absolute response: always-low vs always-high. Source: `src/research/plots.py:fig_fixed_history`, tables fixed_history, 48 runs (hash `2598add5c148a627`).

### 03_punishment_recovery

![03_punishment_recovery](figures/03_punishment_recovery.png)

One-shot, delayed-return and persistent deviations. Source: `src/research/plots.py:fig_punish_recover`, tables pair_traj, 48 runs (hash `481e3c08641d31af`).

### 04_steering_trajectories

![04_steering_trajectories](figures/04_steering_trajectories.png)

Learned direction vs random control and baseline. Source: `src/research/plots.py:fig_steer_traj`, tables trajectories, 416 runs (hash `1f93c04ccb3cbebc`).

### 05_steering_vs_random

![05_steering_vs_random](figures/05_steering_vs_random.png)

Mean per-round shift with 95% CI. Source: `src/research/plots.py:fig_steer_vs_random`, tables steer_level, 1344 runs (hash `588437a1766e7f04`).

### 06_level_vs_interaction

![06_level_vs_interaction](figures/06_level_vs_interaction.png)

Points on the x-axis only = generic price shift; off-axis = changes deviation responsiveness. Source: `src/research/plots.py:fig_level_vs_interaction`, tables steer_level, did, 1232 runs (hash `7fc01591ecdd8279`).

### 07_seed_distributions

![07_seed_distributions](figures/07_seed_distributions.png)

Unit-level spread; bar = mean. Source: `src/research/plots.py:fig_seed_dist`, tables pairs, 96 runs (hash `7e0dbf2f6ead25e2`).

### 15_coverage

![15_coverage](figures/15_coverage.png)

Counts of completed run units. Source: `src/research/plots.py:fig_coverage`, tables units, 1711 runs (hash `b5422c411b38d3b3`).

### 17_best_response

![17_best_response](figures/17_best_response.png)

Mean expected price conditional on the rival's previous price. Source: `src/research/plots.py:fig_br`, tables trajectories, 112 runs (hash `751214608e34c976`).

### 18_collusion_index

![18_collusion_index](figures/18_collusion_index.png)

Per-game joint collusion index. Source: `src/research/plots.py:fig_collusion`, tables units, 1456 runs (hash `5ed245b3f1828389`).

### 12_dose_response

![12_dose_response](figures/12_dose_response.png)

Means with 95% CI across histories. Source: `src/research/plots.py:fig_dose`, tables steer_level, did, 1008 runs (hash `2bc83ca67558666e`).

### 21_hypotheses

![21_hypotheses](figures/21_hypotheses.png)

Colour = pre-declared status. Source: `src/research/plots.py:fig_hypotheses`, tables hypotheses, 94 runs (hash `6b45037e0e432225`).

### 22_consistency_dimensions

![22_consistency_dimensions](figures/22_consistency_dimensions.png)

Replication label across the levels of one dimension. Source: `src/research/plots.py:fig_dimensions`, tables consistency_by_dimension, 0 runs (hash `4f53cda18c2baa0c`).

- 08_template_robustness: not generated (no variation in template_id)
- 09_temperature: not generated (no variation in temperature)
- 10_history_length: not generated (no variation in prefix_rounds)
- 11_deviation_magnitude: not generated (no variation in deviation_magnitude)
- 11b_economics: not generated (no variation in econ_id)
- 11c_recovery_delay: not generated (no variation in recovery_delay)
### 11d_steering_strength

![11d_steering_strength](figures/11d_steering_strength.png)

Effect estimate (95% CI) by alpha. Source: `src/research/plots.py:fig_factor`, tables behaviour_cells, 397 runs (hash `143ce6b84139d434`).

- 11e_sampling_seed: not generated (no variation in seed_model_seed)
### 13_forest

![13_forest](figures/13_forest.png)

Colour = pre-declared cell status. Source: `src/research/plots.py:fig_forest`, tables behaviour_cells, 512 runs (hash `39e67ca20a95753e`).

### 14_consistency_heatmap

![14_consistency_heatmap](figures/14_consistency_heatmap.png)

Status per behaviour and tested parameter level. Source: `src/research/plots.py:fig_consistency_heatmap`, tables behaviour_cells, 397 runs (hash `143ce6b84139d434`).

### 19_negative_results

![19_negative_results](figures/19_negative_results.png)

Behaviours whose evidence is absent, inconclusive or mixed. Source: `src/research/plots.py:fig_negative`, tables behaviour_cells, 0 runs (hash `4f53cda18c2baa0c`).

- 16_cross_model: not generated (no variation in model)
### 20_run_dashboard

![20_run_dashboard](figures/20_run_dashboard.png)

Completion and validity per batch. Source: `src/research/plots.py:fig_dashboard`, tables registry, 1711 runs (hash `b5422c411b38d3b3`).

## 9. Limitations and interpretation

Evidence ladder used throughout: observed behaviour -> statistical evidence (CI over independent histories) -> causal interpretation (only for matched manipulations and steering contrasts against sham/random/generic controls) -> collusion-related implications (none follow directly from scripted-rival experiments).

- **High prices** and **supra-competitive outcomes** (collusion index > 0) describe outcomes, not mechanisms; a model with a fixed high-price default produces them against any rival.
- **Strategic conditioning** requires a response that depends on the rival's behaviour beyond its current price level (e.g. sudden vs gradual histories ending at the same price, condition H).
- **Punishment-like behaviour** is a matched price reduction after a rival undercut; it is not evidence of intent, and a myopic best-responder also lowers its price after an undercut.
- **Coordination** would require mutual conditioning sustaining prices above competitive levels; scripted rivals cannot establish it. **Intentional collusion** is not testable with these experiments.
- Actions are read from the digit distribution after a forced answer prefix; strict-parse audits of free and prefixed generations are reported per batch and never substituted for missing actions.
- Greedy decoding is deterministic: replication units are distinct histories (history_seed), not model seeds.

## 10. Next experiments

- Resolve: rival_price_responsiveness, absolute_price_response, unexpected_deviation_sensitivity, punishment_like_reduction, recovery_after_return, self_play_stability, steering_x_deviation, steering_x_persistent.
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