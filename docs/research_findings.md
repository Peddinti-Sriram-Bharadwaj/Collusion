# Research findings (strategic_deviation_v1)

The auto-generated, always-current version is `research/outputs/report.md` (`python scripts/research.py analyze`).
This page summarises the state after the Stage B (confirmatory) and Stage C (exploratory) batches on 2026-10-26.
All numbers: Qwen2.5-7B-Instruct (revision a09a354), expected price index (0-9 grid; Nash 2, monopoly 7), 95%
cluster-bootstrap CIs over independent pre-play histories.

## Batches
| batch | designation | runs | failed | scored decisions | strict-parse validity | cost |
|---|---|---|---|---|---|---|
| sd_v1_smoke_7b_001 | smoke | 55 | 0 | 484 | 100% | $0.05 billed |
| sd_v1_primary_7b_001 | confirmatory | 1,656 | 0 | 23,616 | 100% (6,704 audits; 656/656 greedy agreement) | $1.81 billed |
| sd_v1_onefactor_7b_001 | exploratory | 656 | 0 | 10,496 | 100% (4,736 audits; 1,531/1,536 greedy agreement) | $1.08 billed |

## Pre-registered hypotheses (Stage B, 16 histories, Holm across H1-H5)
| | estimate | 95% CI | Holm p | verdict |
|---|---|---|---|---|
| H1 punishment-like immediate response | -0.08 | [-0.25, 0.09] | 0.81 | inconclusive |
| H2a recovery after return (gap) | -0.31 | [-0.59, -0.10] | 0.07 | inconclusive (not within +-0.25) |
| H2b persistent minus one-shot after return | +0.04 | [-0.06, 0.12] | 0.81 | not supported (CI within +-0.25) |
| H3 sudden minus gradual, same final price | -0.22 | [-0.52, 0.08] | 0.49 | inconclusive |
| H4 learned minus random level shift (alpha +1) | -0.43 | [-0.56, -0.32] | 0.002 | supported |
| H5 steering x one-shot deviation (DiD) | +0.13 | [-0.02, 0.28] | 0.46 | inconclusive |

## Main observations (evidence ladder: behaviour -> statistics -> causal reading -> collusion implications)
1. **Supra-competitive default** (robust in every tested setting): 3.1 steps above Nash, 1.6 above the one-round
   best response, collusion index 0.87 (0.73-0.95 across settings). Causal reading: a fixed high-price default.
   Implication: high prices alone are not evidence of coordination; a scripted rival cannot reciprocate.
2. **Non-directional change response** (exploratory): a delayed fall after a one-off undercut (peak -0.71, robust across
   templates, temperatures, economics, histories) is matched or exceeded after a rival price *increase* (post-deviation
   mean -0.52 vs -0.23; undercut minus raise +0.29 [0.13, 0.45]). This argues against a punishment interpretation.
3. **Against best response**: the price rises under a gradual rival decline (+0.24) and does not fall against a
   Nash-price rival; the gap to the best response is largest when the rival prices low.
4. **Prompt dependence**: with the log-style template the model shows a clear immediate cut (-0.56) and a large
   post-return gap (-0.84); with the system-message template neither appears.
5. **Steering**: the learned answer-L20 vector moves the price level bidirectionally (alpha -1: +0.77; +1: -0.51;
   +2: -0.79), specific relative to random directions (H4) but weaker than the generic price direction (-0.83 at the
   same norm). Interaction with the deviation response is small, does not flip with steering direction and, for
   recovery, is matched by random directions: no evidence that the vector controls a strategic mechanism.
6. **Not replicated**: the smoke test's initial price rise after an undercut (16 histories: mean -0.08, 9/16 positive).
7. **End-of-game rise** of 1.3 steps in the final round under every script (horizon stated in the prompt).

## Limitations
One model; scripted rivals; 16 (Stage B) or 8 (Stage C) histories; actions read from the digit distribution after a
forced prefix (validated by strict-parse audits); one learned direction. No claim about coordination, collusion or
intent follows from these experiments.
