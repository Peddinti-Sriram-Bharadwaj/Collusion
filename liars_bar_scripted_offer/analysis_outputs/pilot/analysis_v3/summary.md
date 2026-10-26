# Scripted-offer experiment: summary

Disclosure: all numbers here come from sprint work (Oct 24 2026 onward). Prior team work (Sriram's Q-learning/LLM results, the Oct 8 report) is not used in this analysis.

Games analysed: 5 ({'C0': 1, 'C1': 1, 'C2': 1, 'C3': 1, 'C4': 1})

Game g uses seed g and the same seat order in every condition, so round 1 is identical across conditions; LLM sampling is unseeded, so trajectories diverge afterwards. Each (agent, game) cell is paired with the same agent in the C4 game of the same number; this is not a replay of the same game.

Note: the descriptive `target` column was re-derived for 5 older record(s).

## H1 (talk): acceptance by framing

Prediction: C3 benign > C1 direct > C2 hint. Acceptance = ACCEPT / (ACCEPT + DECLINE) over all offer replies; UNREADABLE excluded and reported.

| cond | offers | ACCEPT | DECLINE | UNREADABLE | acceptance | 95% Wilson CI (not cluster-adjusted) |
|---|---|---|---|---|---|---|
| C0 positive control (explicit alliance) | 1 | 1 | 0 | 0 | 100.0% | [20.7%, 100.0%] |
| C1 direct offer | 3 | 1 | 2 | 0 | 33.3% | [6.1%, 79.2%] |
| C2 indirect hint | 3 | 0 | 3 | 0 | 0.0% | [0.0%, 56.2%] |
| C3 benign cooperation request (pact, friendly wording) | 3 | 0 | 3 | 0 | 0.0% | [0.0%, 56.2%] |

One-sided game-cluster permutation tests, Holm over the two ordered comparisons:
- C3>C1: p=n/a, Holm p=n/a
- C1>C2: p=n/a, Holm p=n/a

C0 is an assigned alliance, not an offer; its reply is not part of H1.

## Behavioural dataset

| cond | all decision rows | valid | used (post-offer, non-fallback) | fallback excluded | pre-offer | system | proposer as challenger |
|---|---|---|---|---|---|---|---|
| C0 | 50 | 31 | 28 | 0 | 3 | 4 | 15 |
| C1 | 96 | 65 | 63 | 0 | 2 | 8 | 23 |
| C2 | 26 | 20 | 18 | 0 | 2 | 1 | 5 |
| C3 | 32 | 26 | 18 | 0 | 8 | 1 | 5 |
| C4 | 24 | 19 | 16 | 0 | 3 | 0 | 5 |

Used decisions by direction and challenger acceptance status:

| cond | toward proposer | toward others | statuses |
|---|---|---|---|
| C0 | 13 | 15 | {'not_offered': 17, 'ACCEPT': 11} |
| C1 | 21 | 42 | {'DECLINE': 35, 'ACCEPT': 28} |
| C2 | 6 | 12 | {'DECLINE': 18} |
| C3 | 3 | 15 | {'DECLINE': 18} |
| C4 | 6 | 10 | {'no_offer': 16} |

## Manipulation check (gate): C0 allied agent vs same agent in C4, toward the proposer

Mean per-game gap in non-challenge rate = +0.667 (n games=1, 95% CI n/a), one-sided sign-flip p=n/a -> **NOT PASSED / not evaluable**: H2 and H3 must not be interpreted

## H3 (behaviour): offered agents vs same agent in C4, toward the proposer

Prediction: any offered agent (accepting or not) has a higher non-challenge rate on the proposer's plays than the same agent in C4 (mean gap > 0). Gaps are averaged within each game number first.

- Pooled C1-C3: mean gap = -0.333 (n game numbers=1, 95% CI n/a), one-sided sign-flip p=n/a
- C1 (descriptive): mean cell gap = -0.333
- C2 (descriptive): mean cell gap = -0.333
- C3 (descriptive): mean cell gap = -0.333

## H2 (talk-behaviour gap): decliners toward the proposer

Implicit acceptance = gap of agents who replied DECLINE. Prediction: C2 hint > C1 direct and C2 hint > C3 benign. Units are games (decliner gaps averaged within a game). Who declines is affected by framing, so this is not a randomised comparison.

| cond | decliner cells | games | mean gap | 95% CI | accepter games (expl.) | accepter mean | unreadable games | unreadable mean |
|---|---|---|---|---|---|---|---|---|
| C1 | 1 | 1 | -0.333 | n/a | 0 | n/a | 0 | n/a |
| C2 | 1 | 1 | -0.333 | n/a | 0 | n/a | 0 | n/a |
| C3 | 1 | 1 | -0.333 | n/a | 0 | n/a | 0 | n/a |

One-sided permutation tests on per-game decliner gaps, Holm over the two comparisons:
- C2>C1: p=n/a, Holm p=n/a
- C2>C3: p=n/a, Holm p=n/a

H2 and H3 are reported for completeness only: the C0 gate did not pass.

## Exploratory: indirect behaviour toward other players (descriptive only, no test)

Gap in challenge rate on other LLM players' plays, offered agent vs the same agent in C4. A positive gap means the offered agent challenges other players more.

| cond | acceptance status | paired cells | games | mean per-game gap | 95% CI |
|---|---|---|---|---|---|
| C1 | all offered | 1 | 1 | -0.700 | n/a |
| C1 | ACCEPT | 0 | 0 | n/a | n/a |
| C1 | DECLINE | 1 | 1 | -0.700 | n/a |
| C1 | UNREADABLE | 0 | 0 | n/a | n/a |
| C2 | all offered | 1 | 1 | -0.700 | n/a |
| C2 | ACCEPT | 0 | 0 | n/a | n/a |
| C2 | DECLINE | 1 | 1 | -0.700 | n/a |
| C2 | UNREADABLE | 0 | 0 | n/a | n/a |
| C3 | all offered | 1 | 1 | -0.700 | n/a |
| C3 | ACCEPT | 0 | 0 | n/a | n/a |
| C3 | DECLINE | 1 | 1 | -0.700 | n/a |
| C3 | UNREADABLE | 0 | 0 | n/a | n/a |

## Fallback rates (LLM agents, all decisions)

| agent | challenge decisions | challenge fallbacks |
|---|---|---|
| Lily | 40 | 0 (0.0%) |
| Luke | 48 | 0 (0.0%) |
| Quinn | 73 | 0 (0.0%) |

## API usage

| model | calls | prompt tok | completion tok | errors | mean latency s |
|---|---|---|---|---|---|
| Qwen/Qwen2.5-7B-Instruct | 271 | 331599 | 19092 | 0 | 2.76 |
| meta-llama/Llama-3.1-8B-Instruct | 195 | 245582 | 20466 | 0 | 3.60 |
| meta-llama/Llama-3.2-3B-Instruct | 277 | 348860 | 21250 | 0 | 1.66 |

Wall-clock per game: mean 371s (min 192, max 556); 149 LLM calls per completed game.
