# Exploratory results: judged reply category → subsequent behaviour

**EXPLORATORY, not pre-registered, not confirmatory.** Plan: `reply_behaviour_PLAN.md` (sha256 `cadf940a2d1ca7a2…`, hashed before this script was written), run once. Bootstrap: 5000 cluster resamples over game numbers, seed 20261026, 95% percentile intervals; no p-values. Disclosure: sprint work.

## Sample and missing outcomes

- Judged recipient-games: 382 (pact 206, C3 87, C5 89); 1 unreadable C3 reply was not judged.
- Used Riley decisions without the eligibility flag, excluded: 3.
- Pact recipients with no Riley decision: 87 (never eligible after the offer: 71; eligible but no used Riley decision: 16).
- Pact Riley-facing recipients: 119; of these with a C4 baseline on Riley plays: 86 (no baseline: 33).

## E1. Riley behaviour by reply category (pact conditions; Riley-facing recipients)

R_T = non-challenge rate on Riley's plays; ΔR = R_T − the same agent's rate in C4 (same game number, same seat order).

| category | recipients | game numbers | Riley decisions | mean R_T | 95% CI | with baseline | mean ΔR | 95% CI | share ΔR > 0 |
|---|---|---|---|---|---|---|---|---|---|
| committed | 18 | 14 | 119 | +0.593 | [+0.488, +0.699] | 13 | +0.250 | [-0.018, +0.485] | 0.69 |
| suspicion-evasive | 45 | 26 | 351 | +0.593 | [+0.488, +0.702] | 30 | +0.045 | [-0.113, +0.202] | 0.37 |
| rejection | 9 | 9 | 68 | +0.583 | [+0.306, +0.833] | 8 | -0.099 | [-0.385, +0.177] | 0.38 |
| other | 47 | 25 | 396 | +0.753 | [+0.658, +0.852] | 35 | +0.251 | [+0.140, +0.366] | 0.74 |
| non-committed (pooled) | 101 | 29 | 815 | +0.667 | [+0.593, +0.741] | 73 | +0.128 | [+0.025, +0.229] | 0.55 |
| reference C3 other | 41 | 26 | 282 | +0.564 | [+0.450, +0.673] | 32 | +0.087 | [-0.070, +0.247] | 0.50 |
| reference C5 suspicion-evasive | 4 | 4 | 14 | +0.375 | too few | 4 | -0.142 | too few | 0.50 |
| reference C5 other | 39 | 25 | 286 | +0.602 | [+0.500, +0.696] | 30 | +0.069 | [-0.034, +0.174] | 0.53 |

By category × model (descriptive; n = recipients, mean R_T / mean ΔR (n with baseline)):

| category | llama-3.1-8b | llama-3.2-3b | qwen2.5-7b |
|---|---|---|---|
| committed | n=9: +0.521 / +0.111 (8) | n=7: +0.569 / +0.496 (4) | n=2: +1.000 / +0.375 (1) |
| suspicion-evasive | n=19: +0.295 / -0.210 (14) | n=12: +0.591 / +0.467 (7) | n=14: +1.000 / +0.113 (9) |
| rejection | n=4: +0.188 / -0.438 (4) | n=1: +0.500 / +0.375 (1) | n=4: +1.000 / +0.194 (3) |
| other | n=8: +0.391 / +0.085 (7) | n=17: +0.604 / +0.374 (11) | n=22: +1.000 / +0.240 (17) |

By category × condition (descriptive; same cell format):

| category | C1 | C1b | C2 |
|---|---|---|---|
| committed | n=2: +0.750 / +0.500 (1) | n=8: +0.510 / +0.326 (7) | n=8: +0.637 / +0.094 (5) |
| suspicion-evasive | n=31: +0.635 / +0.066 (19) | n=6: +0.730 / +0.076 (5) | n=8: +0.329 / -0.048 (6) |
| rejection | n=5: +0.450 / -0.175 (5) | n=4: +0.750 / +0.028 (3) | n=0: n/a / n/a (0) |
| other | n=12: +0.773 / +0.185 (8) | n=6: +0.861 / +0.412 (5) | n=29: +0.723 / +0.238 (22) |

## E2. Committed vs non-committed; Riley-specific vs general

(a) ΔR, committed − non-committed:

| scope | committed n (games) | non-committed n (games) | difference | 95% CI |
|---|---|---|---|---|
| pact pooled | 13 (12) | 73 (25) | +0.122 | [-0.116, +0.319] |
| C2 only | 5 (5) | 28 (23) | -0.083 | [-0.608, +0.364] |
| C1b only | 7 (7) | 13 (13) | +0.131 | [-0.284, +0.532] |

(b) General passivity: ΔO = non-challenge rate on other LLM players' plays − the same agent's rate in C4 (pact recipients with other-player decisions and a C4 baseline):

| category | recipients | game numbers | other-player decisions | mean ΔO | 95% CI |
|---|---|---|---|---|---|
| committed | 13 | 12 | 156 | +0.204 | [+0.026, +0.389] |
| suspicion-evasive | 41 | 23 | 359 | +0.244 | [+0.142, +0.360] |
| rejection | 13 | 12 | 122 | +0.047 | [-0.215, +0.322] |
| other | 46 | 26 | 487 | +0.427 | [+0.298, +0.554] |
| non-committed (pooled) | 100 | 30 | 968 | +0.303 | [+0.210, +0.397] |

(c) Riley-specific index = mean ΔR (Riley-facing, E1) − mean ΔO (other-judging, E2b); between-agent:

| category | ΔR n | ΔO n | index | 95% CI |
|---|---|---|---|---|
| committed | 13 | 13 | +0.046 | [-0.268, +0.337] |
| suspicion-evasive | 30 | 41 | -0.199 | [-0.402, -0.001] |
| rejection | 8 | 13 | -0.146 | [-0.527, +0.263] |
| other | 35 | 46 | -0.176 | [-0.348, +0.005] |
| non-committed (pooled) | 73 | 100 | -0.175 | [-0.318, -0.039] |

Index committed − index non-committed: +0.221 [-0.070, +0.458].

(d) Within-agent selectivity R_T − O_T (descriptive only; mixes target and game phase):

| category | recipients with both | mean |
|---|---|---|
| committed | 10 | +0.080 |
| suspicion-evasive | 25 | +0.016 |
| rejection | 4 | +0.037 |
| other | 25 | -0.027 |

## E3. Preferential treatment despite wariness or refusal

Rows repeated from E1/E2 for `suspicion-evasive` and `rejection`, next to `other` (pact) and the C3/C5 reference:

| group | Riley-facing n | mean R_T | mean ΔR (n) | share ΔR > 0 | ΔO (n) | index |
|---|---|---|---|---|---|---|
| pact suspicion-evasive | 45 | +0.593 | +0.045 (30) | 0.37 | +0.244 (41) | -0.199 |
| pact rejection | 9 | +0.583 | -0.099 (8) | 0.38 | +0.047 (13) | -0.146 |
| pact other | 47 | +0.753 | +0.251 (35) | 0.74 | +0.427 (46) | -0.176 |
| reference C3 (all categories) | 41 | +0.564 | +0.087 (32) | 0.50 | +0.067 (55) | +0.020 |
| reference C5 (all categories) | 43 | +0.581 | +0.044 (34) | 0.53 | +0.076 (56) | -0.032 |

## E4. ACCEPT/DECLINE label vs judged commitment (pact Riley-facing recipients with a C4 baseline; outcome ΔR)

| cell | n | game numbers | mean ΔR | 95% CI |
|---|---|---|---|---|
| ACCEPT & committed | 13 | 12 | +0.250 | [-0.013, +0.480] |
| ACCEPT & not committed | 32 | 23 | +0.181 | [+0.048, +0.316] |
| DECLINE | 41 | 22 | +0.087 | [-0.051, +0.206] |
| DECLINE & committed | 0 | 0 | n/a | n/a |

Within C1b (descriptive): ACCEPT: n=9, mean ΔR +0.369; DECLINE: n=11, mean ΔR +0.135; committed: n=7, mean ΔR +0.326; not committed: n=13, mean ΔR +0.194

| model | coefficient(s), cluster-robust SE by game number | LOGO-CV MSE |
|---|---|---|
| M0 | – | 0.1298 |
| M_label | accept +0.147 (SE 0.152) | 0.1332 |
| M_commit | committed +0.155 (SE 0.072) | 0.1283 |
| M_both | accept +0.072 (SE 0.175); committed +0.123 (SE 0.090) | 0.1331 |

Mean per-fold MSE difference M_label − M_commit = +0.0039, SE across 25 folds 0.0033 → **M_commit lower** ("spread across folds" operationalised as the standard error of the mean per-fold difference).

## E5. Decision-level sensitivity (GEE logistic, exchangeable, clusters = game number)

- committed: OR 0.00 [0.00, 0.00] (934 Riley decisions, 29 clusters)
- accept: OR 0.00 [0.00, 0.00] (934 Riley decisions, 29 clusters)

## Bookkeeping

- Bootstrap resamples dropped (an empty group in a resample): 19.
- Deviations from the plan: none, except that the plan's "spread across folds" (E4) is made concrete as stated there.

## Interpretation limits

Category is not randomised (associations, not effects); model is confounded with category; judged categories carry judge error (38/40 on synthetic items, unknown on real replies); the E2c index compares different seats; opportunities depend on survival paths; the committed group is small.

## Post-run notes (added 2026-10-26 after the single run; no number above was changed)
- **E5 failed: perfect separation.** In the pact conditions, Qwen2.5-7B recipients facing Riley never challenged Riley: 511 of 511 Riley decisions were non-challenges. The same agents in C4 let 195 of 246 pass (0.79). The logistic GEE therefore has no finite estimate, and the printed odds ratios (0.00 [0.00, 0.00]) are an artefact, not a result. Per the plan, E5 is reported as failed and nothing is substituted.
- **Console error.** The script's final print to the console failed on a cp949 encoding error (U+2212). This happened after this file and `reply_behaviour_recipients.csv` were written. The analysis was not rerun (`reply_behaviour_run.txt`).
- **Correction to the feasibility report given in chat before the run.** The pact Riley-facing counts were stated there as suspicion-evasive 49 and other 43. The correct pact-only counts are 45 and 47, as above. The 49 included C5. The plan did not depend on these numbers.
