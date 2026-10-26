# Family B results (PREREG Amendment 14; HYPOTHESES_v1.md)

Disclosure: sprint work. Family B (Amendment 14) was pre-registered after the main-run results had been seen; it is a separate Holm family (size 4) and is never pooled with the 210 games. Prior team work (Sriram's Bertrand results, the Oct 8 report) is not used.

Main-run records: `X:/Collusion/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar/experiments/game_records/scripted_offer_main`. Family B records: `X:/Collusion/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar/experiments/game_records/scripted_offer_followup_b`, `X:/Collusion/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar/experiments/game_records/scripted_offer_followup_b_series`.
Judgements: absent (labels only). Series length: 5.

Unit: the game number g. dR_X = X's non-challenge rate on Riley's plays in the new condition minus the same agent's rate in the main run's C1(g); dO_X = the same contrast on other LLM players' plays. Two-sided paired sign-flip; Holm over the four tests with family size 4 (an unrun condition counts as untested). Reading rule (fixed before any game): a rejection with mean > 0 is read as targeted only if mean dO_X < 0.5 x mean dR_X.

## Tests

| test | condition | g | dR_X mean | 95% CI | p | Holm p | dO_X mean (g) | reading |
|---|---|---|---|---|---|---|---|---|
| HB1 | C1s_k3 vs C1 | 24 | +0.069 | [-0.037, +0.176] | 0.1894 | 0.7576 | – (0) | not supported (no rejection; a null is not evidence of no effect) |
| HB2 | C1c vs C1 | 0 | – | – | – | – | – (0) | not run (counted as an untested member of Family B) |
| | | | | | | | | note: condition not run |
| HB3 | C1ci vs C1 | 0 | – | – | – | – | – (0) | not run (counted as an untested member of Family B) |
| | | | | | | | | note: condition not run |
| HB4 | C1d vs C1 | 0 | – | – | – | – | – (0) | not run (counted as an untested member of Family B) |
| | | | | | | | | note: condition not run |

Decision counts per contributing game number are in `paired_values_B.csv` (k1/n1 = X's non-challenges / decisions in the new condition, k0/n0 = the same in C1(g)).

## Descriptive (no tests)

### dR_X by X's model

| test | model | g | mean | 95% CI |
|---|---|---|---|---|
| HB1 | llama-3.1-8b | 8 | +0.225 | [+0.029, +0.422] |
| HB1 | llama-3.2-3b | 7 | +0.047 | [-0.256, +0.351] |
| HB1 | qwen2.5-7b | 9 | -0.052 | [-0.139, +0.036] |

### Series (HB1): each series game vs single-game C1(g), and X's nc on Riley per series game

| series game | g | dR_X vs C1 | 95% CI | | g | mean nc_Riley(X) | 95% CI |
|---|---|---|---|---|---|---|---|
| game 1 | 23 | +0.085 | [-0.009, +0.178] | | 26 | +0.606 | [+0.441, +0.772] |
| game 2 | 25 | +0.106 | [-0.023, +0.234] | | 30 | +0.630 | [+0.502, +0.758] |
| game 3 | 24 | +0.069 | [-0.037, +0.176] | | 29 | +0.626 | [+0.490, +0.762] |
| game 4 | 24 | +0.021 | [-0.154, +0.196] | | 29 | +0.580 | [+0.444, +0.716] |
| game 5 | 23 | +0.139 | [-0.021, +0.299] | | 28 | +0.599 | [+0.460, +0.738] |

Game 1 vs C1 is a same-seed replication with independent sampling (expected about 0); the slope over games is descriptive only. Memory and extra play experience are not separable (no C4/C5 series).

### HB3 - HB2 (same X, per game number): g 0, mean –, 95% CI –

### C1d vs C0 (claimed authority without reminder vs assigned alliance with reminder), X's nc on Riley: g 0, mean –, 95% CI –

### X's replies (labels are not pact acceptance; HB3 asks no question)

| condition | labels | judged categories |
|---|---|---|
| C1c | {} | not judged |
| C1ci | {} | not judged |
| C1d | {} | not judged |
| C1s_k1 | {'DECLINE': 72, 'ACCEPT': 17} | not judged |

### Self-check: C1b recipient's nc on Riley, C1b - C1 (V3 of the HA2c decomposition)
g 21, mean +0.168, 95% CI [+0.019, +0.317], p 0.0275 (main run reference: n 21, +0.168, p .027). A mismatch means the pairing code differs from the decomposition.

## Limitations (fixed in the pre-registration)
- C1c/C1ci/C1d differ from C1 in recipients (X only vs all), length and content; a rejection is 'differs from the plain proposal for X', not an effect of one ingredient.
- The fabricated record (HB2/HB3) and the authority claim (HB4) are false claims by Riley; dual-use caveat applies.
- Fixed turn order: only X judges Riley; opportunities depend on survival paths; Qwen's high baseline leaves little headroom.
- Family B was written after the main-run results were seen; it is confirmatory only in the sense of being fixed before its own data existed.
