# HA2c decomposition: post-result check (EXPLORATORY)

Disclosure: sprint work. Written 2026-10-26 after the confirmatory HA2c result was seen. **Not a redefinition of HA2c and not a confirmatory test**; the confirmatory result stays as computed by `analyze.py` (`main/analysis/summary.md`). p-values are two-sided sign-flip, uncorrected, descriptive. Script: `ha2c_decomposition.py`.

## Composition of C1b's selectivity (the HA2c game numbers)

- Decisions on Riley's plays by proposer-facing agents: 193, of which by non-recipients 118 (61%).
- Decisions on other LLM players' plays by proposer-facing agents: 110, of which by non-recipients 105 (95%).
- Game numbers in which X has no decision on another player's play (the other-players component is entirely non-recipient): 15 of 17.
- Game numbers in which X is not among the proposer-facing agents at all (no recipient behaviour in C1b's value): 3 (g11, g13, g27).
- In C1 every agent received the message, so C1's facing agents are all recipients.

## HA2c and its parts

| version | result |
|---|---|
| V0: HA2c as computed (confirmatory value, reproduced) | n = 17, mean +0.326, approx. 95% t-interval [+0.142, +0.510], sign-flip p 0.0017 |
| V4: Riley component only: non-challenge on Riley's plays, facing agents, C1b − C1 | n = 17, mean +0.024, approx. 95% t-interval [-0.154, +0.201], sign-flip p 0.7850 |
| V5: Other-players component only: non-challenge on other LLM players' plays, facing agents, C1b − C1 | n = 17, mean -0.303, approx. 95% t-interval [-0.471, -0.134], sign-flip p 0.0015 |
| V1: C1b recipient X only − C1 as computed | n = 2: not computable (values [-0.42, 0.5]) |
| V2: X only on both sides (selectivity) | n = 2: not computable (values [-1.346, 0.5]) |
| V3: X's non-challenge on Riley's plays only, C1b − C1 | n = 21, mean +0.168, approx. 95% t-interval [+0.018, +0.318], sign-flip p 0.0273 |

## Per game number (HA2c games)

| g | C1b facing agents | X | C1b nc Riley | C1b nc others | C1b n others | of which by X | C1 nc Riley | C1 nc others |
|---|---|---|---|---|---|---|---|---|
| 0 | Lily+Quinn | Lily | 0.83 | 0.14 | 7 | 0 | 0.85 | 0.96 |
| 2 | Lily+Quinn | Quinn | 0.88 | 0.56 | 16 | 0 | 0.79 | 0.40 |
| 5 | Lily+Quinn | Quinn | 0.67 | 0.50 | 4 | 0 | 0.25 | 0.33 |
| 6 | Lily+Quinn | Lily | 0.62 | 0.33 | 9 | 0 | 0.73 | 0.71 |
| 7 | Lily+Luke+Quinn | Luke | 0.83 | 0.40 | 5 | 0 | 0.80 | 0.50 |
| 10 | Luke | Luke | 0.29 | 1.00 | 2 | 2 | 0.65 | 0.94 |
| 11 | Lily+Luke | Quinn | 0.40 | 0.12 | 8 | 0 | 1.00 | 1.00 |
| 12 | Lily+Quinn | Lily | 0.73 | 0.60 | 10 | 0 | 0.79 | 0.93 |
| 13 | Quinn | Luke | 0.86 | 0.00 | 1 | 0 | 0.50 | 0.40 |
| 16 | Luke+Quinn | Luke | 0.85 | 0.75 | 4 | 0 | 0.80 | 1.00 |
| 19 | Lily+Luke | Luke | 0.68 | 0.45 | 11 | 0 | 0.79 | 0.50 |
| 21 | Lily | Lily | 0.50 | 0.00 | 3 | 3 | 0.00 | 0.00 |
| 24 | Lily+Luke | Lily | 0.38 | 0.50 | 2 | 0 | 0.81 | 1.00 |
| 25 | Lily+Luke | Luke | 0.43 | 0.33 | 6 | 0 | 0.00 | 0.50 |
| 27 | Quinn | Lily | 0.73 | 0.00 | 5 | 0 | 0.14 | 0.50 |
| 28 | Lily+Luke | Luke | 0.38 | 0.29 | 7 | 0 | 0.36 | 0.64 |
| 29 | Luke+Quinn | Quinn | 0.60 | 0.10 | 10 | 0 | 1.00 | 0.92 |

## Reading

- The HA2c difference sits in the other-players component (V5), not in the Riley component (V4).
- In C1b that component comes almost entirely from agents that never received the message; in C1 it comes from recipients, whose non-challenge toward other players rose after the message (HM, C1 −34 points).
- HA2c therefore mainly contrasts C1 recipients' general passivity with C1b non-recipients' ordinary behaviour, not the brokered offer's effect on X's preferential treatment of Riley. The PREREG statement that both sides are X's behaviour by construction does not hold in practice.
- X-only selectivity (V1, V2) is not computable (X almost never judges another player's play in C1b). X's own sparing of Riley (V3) is reported as the closest X-only quantity; it cannot separate Riley-specific sparing from X's general passivity and carries every C1 vs C1b difference (recipients, content, social proof, wording).
