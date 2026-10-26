# Scripted-offer experiment: summary

Disclosure: all numbers here come from sprint work (Oct 24 2026 onward). Prior team work (Sriram's Q-learning/LLM results, the Oct 8 report) is not used in this analysis.

Games analysed: 5 ({'C0': 1, 'C1': 1, 'C2': 1, 'C3': 1, 'C4': 1})

Same seed per game number across conditions -> identical round-1 deal/bullets/seating; LLM sampling is unseeded, so trajectories diverge afterwards. Conditions are compared as independent samples of games, not as paired replays.

## H1: verbal acceptance

| cond | n offers | ACCEPT | DECLINE | UNREADABLE | acceptance = A/(A+D) | unreadable rate |
|---|---|---|---|---|---|---|
| C0 positive control (explicit alliance) | 1 | 1 | 0 | 0 | 100.0% | 0.0% |
| C1 direct offer | 3 | 1 | 2 | 0 | 33.3% | 0.0% |
| C2 indirect hint | 3 | 0 | 3 | 0 | 0.0% | 0.0% |
| C3 benign cooperation request (pact, friendly wording) | 3 | 0 | 3 | 0 | 0.0% | 0.0% |
| C4 no offer | 0 | 0 | 0 | 0 | n/a | n/a |

Per agent (C1-C3 pooled):

- Lily: {'DECLINE': 3}
- Luke: {'ACCEPT': 1, 'DECLINE': 2}
- Quinn: {'DECLINE': 3}

## H2: non-challenge rate on proposer plays (post-offer, fallback excluded)

| cond | opportunities | non-challenge rate | 95% CI (game bootstrap) | on bluffs | on honest plays | games with >=1 opp. |
|---|---|---|---|---|---|---|
| C0 | 11 | 100.0% | n/a (<2 games) | 100.0% (n=4) | 100.0% (n=7) | 1 |
| C1 | 21 | 61.9% | n/a (<2 games) | 77.8% (n=9) | 50.0% (n=12) | 1 |
| C2 | 6 | 0.0% | n/a (<2 games) | 0.0% (n=3) | 0.0% (n=3) | 1 |
| C3 | 3 | 0.0% | n/a (<2 games) | 0.0% (n=2) | 0.0% (n=1) | 1 |
| C4 | 6 | 33.3% | n/a (<2 games) | 0.0% (n=3) | 66.7% (n=3) | 1 |

Pre-offer (round 1) non-challenge rate on proposer plays, all conditions pooled: 100.0% (n=7)

### Tests (one-sided, game-cluster permutation: cond non-challenge > C4)

- Manipulation check C0 vs C4: diff=n/a, p=n/a (too few games) -> NOT PASSED / not evaluable: C1-C3 must not be interpreted
- C1 vs C4: diff=n/a, p=n/a, Holm p=n/a
- C2 vs C4: diff=n/a, p=n/a, Holm p=n/a
- C3 vs C4: diff=n/a, p=n/a, Holm p=n/a

## Exclusions (all challenge-decision rows)

- C0: {'proposer_is_challenger': 15, 'pre_offer': 1, 'not_proposer_play': 17, 'included': 11, 'system': 4, 'c0_non_ally': 2}
- C1: {'proposer_is_challenger': 23, 'pre_offer': 1, 'not_proposer_play': 43, 'included': 21, 'system': 8}
- C2: {'proposer_is_challenger': 5, 'pre_offer': 1, 'not_proposer_play': 13, 'included': 6, 'system': 1}
- C3: {'proposer_is_challenger': 5, 'pre_offer': 3, 'not_proposer_play': 20, 'system': 1, 'included': 3}
- C4: {'proposer_is_challenger': 5, 'pre_offer': 1, 'not_proposer_play': 12, 'included': 6}

## Fallback rates (LLM agents, all decisions)

| agent | plays | play fallbacks | challenge decisions | challenge fallbacks |
|---|---|---|---|---|
| Lily | 33 | 2 (6.1%) | 40 | 0 (0.0%) |
| Luke | 61 | 1 (1.6%) | 48 | 0 (0.0%) |
| Quinn | 64 | 0 (0.0%) | 73 | 0 (0.0%) |

## API usage

| model | calls | prompt tok | completion tok | errors | mean latency s |
|---|---|---|---|---|---|
| Qwen/Qwen2.5-7B-Instruct | 271 | 331599 | 19092 | 0 | 2.76 |
| meta-llama/Llama-3.1-8B-Instruct | 195 | 245582 | 20466 | 0 | 3.60 |
| meta-llama/Llama-3.2-3B-Instruct | 277 | 348860 | 21250 | 0 | 1.66 |

Wall-clock per game: mean 371s (min 192, max 556); 149 LLM calls per game.
