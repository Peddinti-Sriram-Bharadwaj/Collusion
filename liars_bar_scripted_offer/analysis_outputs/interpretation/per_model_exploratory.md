# Per-model split of the main-run contrasts (EXPLORATORY, not pre-registered)

Disclosure: sprint work; computed 2026-10-26 after every main-run result had been seen, at the experimenter's request, with `per_model_exploratory.py` (reuses `analyze.Data`, `paired_test`). Not part of Family A; no Holm correction; three models x many contrasts, so an isolated p < .05 is expected by chance and is not read as a finding. Unit: game number g; the agent of a given seat has the same model in every condition of the same g, so pairing within a model is well defined. n per model is about a third of the pre-registered n, so the intervals are wide.

| contrast | model | n (g) | mean | 95% CI | two-sided p (unadj.) |
|---|---|---|---|---|---|
| Gate C0-C4 proposer nc | llama-3.1-8b | 9 | +0.633 | [+0.342, +0.924] | 0.008 |
| Gate C0-C4 proposer nc | llama-3.2-3b | 5 | +0.975 | [+0.906, +1.044] | 0.062 |
| Gate C0-C4 proposer nc | qwen2.5-7b | 8 | +0.242 | [+0.082, +0.402] | 0.031 |
| | | | | | |
| HA1a committed C1-C2 | llama-3.1-8b | 29 | -0.069 | [-0.167, +0.029] | 0.501 |
| HA1a committed C1-C2 | llama-3.2-3b | 27 | -0.222 | [-0.476, +0.031] | 0.144 |
| HA1a committed C1-C2 | qwen2.5-7b | 30 | +0.033 | [-0.121, +0.188] | 1.000 |
| | | | | | |
| HA1b susp-evasive C1-C2 | llama-3.1-8b | 29 | -0.034 | [-0.273, +0.204] | 1.000 |
| HA1b susp-evasive C1-C2 | llama-3.2-3b | 27 | +0.630 | [+0.435, +0.824] | 0.000 |
| HA1b susp-evasive C1-C2 | qwen2.5-7b | 30 | +0.567 | [+0.378, +0.755] | 0.000 |
| | | | | | |
| HA1c X committed C1b-C1 | llama-3.1-8b | 8 | +0.750 | [+0.363, +1.137] | 0.031 |
| HA1c X committed C1b-C1 | llama-3.2-3b | 7 | +0.000 | [-0.534, +0.534] | 1.000 |
| HA1c X committed C1b-C1 | qwen2.5-7b | 10 | -0.100 | [-0.326, +0.126] | 1.000 |
| | | | | | |
| X nc on Riley C1-C4 | llama-3.1-8b | 8 | -0.269 | [-0.527, -0.012] | 0.125 |
| X nc on Riley C1-C4 | llama-3.2-3b | 6 | +0.468 | [+0.154, +0.781] | 0.062 |
| X nc on Riley C1-C4 | qwen2.5-7b | 7 | +0.217 | [+0.039, +0.394] | 0.062 |
| | | | | | |
| HM C1-C4 others challenge | llama-3.1-8b | 19 | +0.090 | [-0.066, +0.246] | 0.255 |
| HM C1-C4 others challenge | llama-3.2-3b | 21 | -0.326 | [-0.483, -0.169] | 0.000 |
| HM C1-C4 others challenge | qwen2.5-7b | 17 | -0.719 | [-0.844, -0.593] | 0.000 |
| | | | | | |
| HM C2-C4 others challenge | llama-3.1-8b | 18 | +0.036 | [-0.077, +0.148] | 0.515 |
| HM C2-C4 others challenge | llama-3.2-3b | 19 | -0.234 | [-0.467, -0.002] | 0.047 |
| HM C2-C4 others challenge | qwen2.5-7b | 18 | -0.676 | [-0.805, -0.548] | 0.000 |
| | | | | | |
| HM C3-C4 others challenge | llama-3.1-8b | 19 | +0.165 | [+0.052, +0.278] | 0.006 |
| HM C3-C4 others challenge | llama-3.2-3b | 19 | -0.151 | [-0.300, -0.002] | 0.044 |
| HM C3-C4 others challenge | qwen2.5-7b | 18 | -0.214 | [-0.417, -0.012] | 0.041 |
| | | | | | |
| HM C5-C4 others challenge | llama-3.1-8b | 19 | +0.113 | [+0.019, +0.206] | 0.022 |
| HM C5-C4 others challenge | llama-3.2-3b | 19 | -0.164 | [-0.356, +0.027] | 0.087 |
| HM C5-C4 others challenge | qwen2.5-7b | 18 | -0.181 | [-0.361, -0.001] | 0.045 |
| | | | | | |
| HM pooled msg-C4 others challenge | llama-3.1-8b | 19 | +0.108 | [+0.011, +0.206] | 0.028 |
| HM pooled msg-C4 others challenge | llama-3.2-3b | 21 | -0.229 | [-0.375, -0.082] | 0.005 |
| HM pooled msg-C4 others challenge | qwen2.5-7b | 18 | -0.441 | [-0.566, -0.315] | 0.000 |
| | | | | | |
| HA2a selectivity mean(C1,C2)-C5 | llama-3.1-8b | 10 | +0.074 | [-0.303, +0.450] | 0.664 |
| HA2a selectivity mean(C1,C2)-C5 | llama-3.2-3b | 5 | -0.302 | [-0.735, +0.131] | 0.188 |
| HA2a selectivity mean(C1,C2)-C5 | qwen2.5-7b | 5 | -0.364 | [-0.658, -0.070] | 0.062 |
| | | | | | |
| HA2c selectivity C1b-C1 | llama-3.1-8b | 5 | +0.383 | [+0.267, +0.500] | 0.062 |
| HA2c selectivity C1b-C1 | llama-3.2-3b | 2 | -0.652 | [-9.467, +8.163] | 1.000 |
| HA2c selectivity C1b-C1 | qwen2.5-7b | 5 | +0.456 | [+0.190, +0.722] | 0.062 |
| | | | | | |
| HA2b selectivity C1-C2 | llama-3.1-8b | 5 | -0.551 | [-0.882, -0.219] | 0.062 |
| HA2b selectivity C1-C2 | llama-3.2-3b | 8 | +0.051 | [-0.261, +0.364] | 0.688 |
| HA2b selectivity C1-C2 | qwen2.5-7b | 3 | -0.014 | [-0.273, +0.244] | 1.000 |
| | | | | | |
| X nc on others C1-C4 | llama-3.1-8b | 1 | – | – | – |
| X nc on others C1-C4 | llama-3.2-3b | 2 | -0.050 | [-7.038, +6.938] | 1.000 |
| X nc on others C1-C4 | qwen2.5-7b | 0 | – | – | – |
| | | | | | |

Pre-registered (all models pooled) reference values: Gate +0.569; HA1a −0.089; HA1b +0.400; HA1c +0.200; HA2a −0.197; HA2b −0.063; HA2c +0.326; HM −0.213 (`../main/analysis/summary.md`).

HB1 by model (from the pre-registered Family B analysis, descriptive there too): llama-3.1-8b +0.225 [+0.029, +0.422] (g 8); llama-3.2-3b +0.047 [−0.256, +0.351] (g 7); qwen2.5-7b −0.052 [−0.139, +0.036] (g 9).
