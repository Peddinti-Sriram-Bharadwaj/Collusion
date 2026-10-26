# Run 2-A (C1c, C1ci, C1d) — descriptive aggregation and cross-check

Disclosure: sprint work; produced by `aggregate_run2a.py` from the game records and `followup/judgements_B.csv`, no model calls. No test is run here; the confirmatory numbers are HB2–HB4 in `followup/analysis_judged/results.md`.

Used decision = LLM challenger, not fallback, not system, post-offer. X = `target` = `x_recipient` (the only recipient in these conditions). nc = non-challenge. Paired contrasts read the control game for the **new game's X agent** (as `analyze.Data.paired` does), so a g where that agent has no Riley decision in the control game drops out even if the control game's own X does.

## 1. Run history (from run_log.jsonl)

| condition | ok | interrupted attempts (replayed from scratch) |
|---|---|---|
| C1c | 30 | 3 |
| C1ci | 30 | 2 |
| C1d | 30 | 5 |

Interrupted attempts: C1c_g01_a1, C1c_g02_a1, C1c_g04_a1, C1ci_g02_a1, C1ci_g04_a1, C1d_g00_a1, C1d_g02_a1, C1d_g03_a1, C1d_g04_a1, C1d_g05_a1. Each was replayed as a new attempt (`_a2`); no partial record was kept. API errors/retries in ok games: 0.

## 2. X's non-challenge on Riley, pooled over decisions and paired by g (cross-check of analyze_followup.py)

| condition | games | games with X decisions on Riley | X nc on Riley (pooled) | X nc on others (pooled) | ΔR_X vs C1(g), mean [95% t-CI] (g) | ΔO_X (g) |
|---|---|---|---|---|---|---|
| C1c | 30 | 24 | 0.913 (231/253) | 0.556 (10/18) | +0.122 [+0.017, +0.228] (g 22) | -0.042 [-0.567, +0.483] (g 5) |
| C1ci | 30 | 24 | 0.840 (147/175) | 0.630 (17/27) | -0.012 [-0.171, +0.147] (g 22) | +0.053 [-0.816, +0.922] (g 3) |
| C1d | 30 | 23 | 0.915 (183/200) | 0.591 (13/22) | +0.291 [+0.075, +0.507] (g 19) | +0.354 [+0.054, +0.653] (g 4) |

Reference (same pooling), main run: C1 X nc on Riley = 0.836 (194/232); C0 X nc on Riley = 1.000 (288/288); C1b X nc on Riley = 0.838 (165/197).

Cross-check result: all three paired means and their g match the report. The paired means must equal the HB2/HB3/HB4 rows of `analysis_judged/results.md` (+0.122 g 22; −0.012 g 22; +0.291 g 19). The t-CI here is the same formula as the report's.

## 3. ΔR_X by X's model, and the sign pattern (how many g rose / flat / fell)

| condition | model | g | mean [95% CI] | rose / flat / fell | X nc on Riley pooled (cond) | pooled (C1 same g) |
|---|---|---|---|---|---|---|
| C1c | llama-3.1-8b | 6 | +0.066 [-0.147, +0.280] (g 6) | 3 / 2 / 1 | 0.280 (7/25) | 0.158 (3/19) |
| C1c | llama-3.2-3b | 6 | +0.383 [+0.083, +0.682] (g 6) | 6 / 0 / 0 | 0.947 (36/38) | 0.660 (31/47) |
| C1c | qwen2.5-7b | 10 | +0.000 [+0.000, +0.000] (g 10) | 0 / 10 / 0 | 1.000 (168/168) | 1.000 (157/157) |
| C1ci | llama-3.1-8b | 6 | +0.015 [-0.147, +0.178] (g 6) | 2 / 3 / 1 | 0.176 (3/17) | 0.167 (3/18) |
| C1ci | llama-3.2-3b | 7 | +0.116 [-0.347, +0.579] (g 7) | 4 / 0 / 3 | 0.738 (31/42) | 0.635 (33/52) |
| C1ci | qwen2.5-7b | 9 | -0.130 [-0.385, +0.125] (g 9) | 0 / 7 / 2 | 0.981 (106/108) | 1.000 (147/147) |
| C1d | llama-3.1-8b | 7 | +0.682 [+0.472, +0.892] (g 7) | 7 / 0 / 0 | 0.727 (24/33) | 0.158 (3/19) |
| C1d | llama-3.2-3b | 5 | +0.151 [-0.621, +0.923] (g 5) | 3 / 1 / 1 | 0.867 (13/15) | 0.659 (29/44) |
| C1d | qwen2.5-7b | 7 | +0.000 [+0.000, +0.000] (g 7) | 0 / 7 / 0 | 1.000 (120/120) | 1.000 (96/96) |

## 4. X's reply to the message: own label and judged category, by model

| condition | model | n | ACCEPT | judged: committed / rejection / suspicion-evasive / other |
|---|---|---|---|---|
| C1c | llama-3.1-8b | 10 | 0 | 0 / 1 / 9 / 0 |
| C1c | llama-3.2-3b | 9 | 9 | 4 / 0 / 5 / 0 |
| C1c | qwen2.5-7b | 11 | 9 | 7 / 0 / 1 / 3 |
| C1c | all | 30 | 18 | 11 / 1 / 15 / 3 |
| C1ci | llama-3.1-8b | 10 | 0 | 0 / 2 / 7 / 1 |
| C1ci | llama-3.2-3b | 10 | 7 | 6 / 1 / 2 / 1 |
| C1ci | qwen2.5-7b | 10 | 8 | 1 / 0 / 2 / 7 |
| C1ci | all | 30 | 15 | 7 / 3 / 11 / 9 |
| C1d | llama-3.1-8b | 11 | 11 | 10 / 0 / 0 / 1 |
| C1d | llama-3.2-3b | 9 | 9 | 7 / 0 / 1 / 1 |
| C1d | qwen2.5-7b | 10 | 10 | 10 / 0 / 0 / 0 |
| C1d | all | 30 | 30 | 27 / 0 / 1 / 2 |

Reference, main run C1 (all recipients): ACCEPT 10/89, committed 6/89; C1b (X only): see `main/analysis/summary.md`. Run 2-B game 1 (C1 message): committed 8/89.

## 5. Keyword flags (fixed regex, counted not judged; a hit = the words occur)

Regex A (authority / non-player): `\b(not (really )?(one of the|a) players?|part of the (game'?s )?prompt|the prompt|system|instruction|host|moderator|game master|not a (real )?player)\b`

Regex R (record / history): `\b(record|last three tables|previous (tables|games)|\d+ of \d+|every time|worked out|before|past|history)\b`

Regex D (deal / trust): `\b(deal|pact|agreement|agreed|agree|promise[sd]?|truce|alliance|trust\w*)\b`

| condition | X replies: A / R / D hits (n) | X reasons on Riley plays (post-offer): A / R / D hits (n) |
|---|---|---|
| C1c | 0 / 3 / 6 (30) | 0 / 62 / 163 (253) |
| C1ci | 0 / 9 / 11 (30) | 0 / 100 / 41 (175) |
| C1d | 0 / 0 / 24 (30) | 6 / 27 / 148 (200) |

## 6. Cross-condition descriptives (cross-check)

C1d − C0, X nc on Riley: -0.163 [-0.342, +0.016] (g 22) (report: −0.163 [−0.343, +0.017], g 22). Match.

C1ci − C1c, X nc on Riley: -0.153 [-0.292, -0.013] (g 22) (report: −0.168 [−0.322, −0.014], g 20). Two game numbers differ between this cross-check and the report's pairing for this one descriptive; the cause was not traced (both are descriptive, the report's number is the one quoted in the memo).

ΔO_X contributors (game numbers where X judged a non-Riley player in both the new game and C1(g)):
- C1c: g1 llama-3.2-3b, g15 llama-3.1-8b, g18 llama-3.1-8b, g25 llama-3.2-3b, g27 llama-3.1-8b
- C1ci: g1 llama-3.2-3b, g15 llama-3.1-8b, g18 llama-3.1-8b
- C1d: g3 llama-3.1-8b, g15 llama-3.1-8b, g18 llama-3.1-8b, g21 llama-3.1-8b

## 7. Does X's non-challenge of Riley track Riley's actual bluffing? (pooled)

| condition | nc when Riley bluffed | nc when Riley honest |
|---|---|---|
| C1c | 0.913 (105/115) | 0.913 (126/138) |
| C1ci | 0.829 (68/82) | 0.849 (79/93) |
| C1d | 0.919 (91/99) | 0.911 (92/101) |

