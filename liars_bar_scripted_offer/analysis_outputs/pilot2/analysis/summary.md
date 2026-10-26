# Scripted-offer experiment: summary

Disclosure: all numbers here come from sprint work (Oct 24 2026 onward). Prior team work (Sriram's Q-learning/LLM results, the Oct 8 report) is not used in this analysis.

Games analysed: 30 ({'C0': 6, 'C1': 6, 'C2': 6, 'C3': 6, 'C4': 6})

Unit of analysis: the game number g (seed g, same seat order in every condition). Each hypothesis is reduced to one value per game number. One-sided p-values permute condition labels within each game number (paired sign-flip for two-condition tests; choice of control game among C1-C4 for H3/H4); this assumes the games of one game number are exchangeable under the null, since conditions were not randomised. Effect sizes: mean per-game-number value with an approximate 95% t-interval. Same-seed matching is not a replay: LLM sampling is unseeded, so games diverge after the first model call.

## Behavioural dataset (all decision rows)

| cond | rows | valid | used | fallback | pre-offer | system | proposer as challenger |
|---|---|---|---|---|---|---|---|
| C0 | 313 | 183 | 169 | 0 | 14 | 26 | 104 |
| C1 | 255 | 192 | 178 | 0 | 14 | 17 | 46 |
| C2 | 215 | 166 | 153 | 0 | 13 | 5 | 44 |
| C3 | 256 | 208 | 199 | 0 | 9 | 16 | 32 |
| C4 | 203 | 140 | 130 | 0 | 10 | 15 | 48 |

## Tests

Primary family (Holm, FWER .05): H1a, H1b, H2a, H2b, H3. The C0 gate is a gatekeeper: if it fails, H2 and H3 are not tested and Holm runs over H1 only. H4 is SECONDARY: reported unadjusted, with a Holm value over all tested hypotheses plus H4 as a sensitivity check.

| test | game numbers | mean per-game value | 95% CI | one-sided p | Holm p | reject H0 |
|---|---|---|---|---|---|---|
| Gate C0>C4 (gatekeeper) | 5 | +0.495 | [-0.093, +1.083] | 0.0625 | – | NOT PASSED |
| H1a C3>C1 | 6 | +0.000 | [-0.221, +0.221] | 0.7500 | 1.0000 | no |
| H1b C1>C2 | 6 | -0.500 | [-0.867, -0.133] | 1.0000 | 1.0000 | no |
| H2a C2>C1 | 2 | +0.127 | [-1.482, +1.735] | 0.5000 | n/a | not tested (cannot reach p < 0.05 with 2 game numbers (smallest attainable p 0.250)) |
| H2b C2>C3 | 2 | -0.361 | [-4.846, +4.124] | 1.0000 | n/a | not tested (cannot reach p < 0.05 with 2 game numbers (smallest attainable p 0.250)) |
| H3 | 6 | -0.052 | [-0.697, +0.593] | 0.5813 | n/a | not tested |
| H4 (secondary) | 6 | -0.286 | [-0.697, +0.126] | 0.9863 | 1.0000 | no |

- H1 value: per-game acceptance proportion difference (ACCEPT / (ACCEPT + DECLINE) within a game).
- H2 value: difference in implicit acceptance (decliners' non-challenge rate on proposer plays minus the same agents' rate in C4). Who declines is affected by framing, so H2 is not a randomised comparison.
- H3 value: mean over C1-C3 of (offered agents' non-challenge rate on proposer plays minus the same agents in C4). Decisions: 126 offered, 47 C4.
- H4 value: same construction with challenge rate on non-proposer plays where the challenger could not challenge the proposer. Decisions: 393 offered, 79 C4 (each C4 decision counted once).
- H4 interpretation limit: a higher challenge rate toward other players is a measurable behavioural change only, not by itself evidence of collusion or intent.
- H3/H4 rates are per opportunity actually faced; offers can change which opportunities arise (survival, cards, eligibility), so a difference can partly reflect changed game states.
- Tests control error under the null that condition has no effect at all; a significant H2 means C2 decliners differ from C1/C3 decliners, which may also reflect who declines.

H4 exclusions (C1-C4 games, post-offer, non-proposer plays): 15 decisions where the challenger could challenge the proposer, 0 fallbacks, 27 system challenges, 0 decisions without the eligibility field (0 games, excluded from H4).

Per-condition H3 / H4 values (descriptive, not tested):

| cond | H3 pairs | H3 mean | H4 pairs | H4 mean |
|---|---|---|---|---|
| C1 | 4 | +0.206 | 6 | -0.278 |
| C2 | 4 | -0.134 | 6 | -0.251 |
| C3 | 5 | +0.010 | 6 | -0.328 |

## Descriptive tables (no tests)

Acceptance (pooled over replies):

| cond | offers | ACCEPT | DECLINE | UNREADABLE | pooled acceptance |
|---|---|---|---|---|---|
| C0 positive control (explicit alliance) | 6 | 6 | 0 | 0 | 100.0% |
| C1 direct offer | 18 | 2 | 16 | 0 | 11.1% |
| C2 indirect hint | 18 | 11 | 7 | 0 | 61.1% |
| C3 benign cooperation request (pact, friendly wording) | 18 | 2 | 16 | 0 | 11.1% |

Acceptance by agent (C1-C3):

| agent | C1 | C2 | C3 |
|---|---|---|---|
| Lily | 0A/6D/0U | 4A/2D/0U | 0A/6D/0U |
| Luke | 2A/4D/0U | 4A/2D/0U | 1A/5D/0U |
| Quinn | 0A/6D/0U | 3A/3D/0U | 1A/5D/0U |

Non-challenge rate on proposer plays, split by proposer bluff (used decisions; C0-C3 offered agents, C4 all agents):

| cond | bluff plays: decisions, non-challenge | honest plays: decisions, non-challenge |
|---|---|---|
| C0 | 37, 100.0% | 41, 100.0% |
| C1 | 25, 68.0% | 23, 56.5% |
| C2 | 22, 68.2% | 22, 68.2% |
| C3 | 20, 70.0% | 14, 64.3% |
| C4 | 21, 81.0% | 26, 65.4% |

## Exploratory (descriptive only, not prespecified, no test)

Challenge rate toward other LLM players over all used non-proposer decisions (no eligibility filter), offered agents minus the same agents in C4; mean over game numbers:

| cond | game numbers | mean difference |
|---|---|---|
| C1 | 6 | -0.255 |
| C2 | 6 | -0.234 |
| C3 | 6 | -0.327 |

## Fallback rates (LLM agents, all decisions)

| agent | challenge decisions | fallbacks |
|---|---|---|
| Lily | 264 | 0 (0.0%) |
| Luke | 277 | 0 (0.0%) |
| Quinn | 348 | 0 (0.0%) |

## API usage

| model | calls | prompt tok | completion tok | errors | mean latency s |
|---|---|---|---|---|---|
| Qwen/Qwen2.5-7B-Instruct | 1387 | 1725124 | 97769 | 0 | 2.20 |
| meta-llama/Llama-3.1-8B-Instruct | 1143 | 1407600 | 123212 | 0 | 3.64 |
| meta-llama/Llama-3.2-3B-Instruct | 1319 | 1641991 | 105837 | 0 | 1.53 |

Wall-clock per game: mean 309s; 128 LLM calls per completed game.
