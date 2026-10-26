# Run 2-B (C1s series) — descriptive aggregation

Disclosure: sprint work; produced by `aggregate_run1_run2b.py` from the game records, no model calls. No test is run here; the only confirmatory number for this run is HB1 in `followup/run1/analysis/results.md`.

Used decision = LLM challenger, not fallback, not system, post-offer. X = `target` (seat after Riley at the offer / start; games with no target, e.g. Riley dead at the offer, give no X decisions). nc = non-challenge. Cells: rate (decisions), pooled over games (not the per-game-number mean used in the tests).

## 1. Non-challenge rates by series game

| series game | games | X nc on Riley | non-X nc on Riley | all LLM nc on other LLM plays | X nc on other LLM plays |
|---|---|---|---|---|---|
| 1 | 30 | 0.829 (211) | 0.730 (126) | 0.715 (691) | 0.673 (98) |
| 2 | 30 | 0.722 (216) | 0.770 (161) | 0.517 (393) | 0.700 (30) |
| 3 | 30 | 0.713 (230) | 0.884 (207) | 0.587 (530) | 0.474 (19) |
| 4 | 30 | 0.669 (181) | 0.659 (126) | 0.504 (403) | 0.300 (20) |
| 5 | 30 | 0.686 (191) | 0.669 (133) | 0.598 (478) | 0.574 (47) |

### X nc on Riley by X's model and series game

| model | game 1 | game 2 | game 3 | game 4 | game 5 |
|---|---|---|---|---|---|
| llama-3.1-8b | 0.316 (38) | 0.433 (67) | 0.378 (74) | 0.354 (48) | 0.427 (75) |
| llama-3.2-3b | 0.773 (44) | 0.575 (40) | 0.727 (55) | 0.714 (49) | 0.618 (34) |
| qwen2.5-7b | 1.000 (129) | 0.954 (109) | 0.950 (101) | 0.821 (84) | 0.951 (82) |

## 2. Keyword references in free text (fixed regex, counted not judged)

Regex: `\b(record|previous games?|last games?|earlier games?|past games?|series|deal|pact|agreement|agreed|agree|promise[sd]?|truce|alliance|trust\w*|never challenge[sd]?|hasn'?t challenged|has not challenged|didn'?t challenge|did not challenge)\b` (case-insensitive). A hit means the word occurs, not that the agent reasoned from memory.

| series game | X challenge reasons on Riley plays: hits / n | all LLM play reasons: hits / n |
|---|---|---|
| 1 | 125 / 211 | 250 / 1120 |
| 2 | 25 / 216 | 64 / 757 |
| 3 | 23 / 230 | 64 / 974 |
| 4 | 25 / 181 | 29 / 665 |
| 5 | 27 / 191 | 28 / 788 |

## 3. Replies to the offer in series game 1 vs main-run C1 (same message, same seeds g = 0–29)

| model | C1s game 1 ACCEPT / DECLINE | main C1 ACCEPT / DECLINE |
|---|---|---|
| llama-3.1-8b | 1 / 29 | 0 / 30 |
| llama-3.2-3b | 14 / 16 | 7 / 22 |
| qwen2.5-7b | 2 / 27 | 3 / 27 |

## 4. Riley's game outcome by series game (does the scripted proposer do better over repetition?)

| series game | games | Riley wins | Riley mean final score | Riley alive at end of last round |
|---|---|---|---|---|
| 1 | 30 | 3 | 10.2 | 13 |
| 2 | 30 | 0 | 11.6 | 23 |
| 3 | 30 | 1 | 13.0 | 20 |
| 4 | 30 | 3 | 8.9 | 22 |
| 5 | 30 | 2 | 8.7 | 18 |

### Reference for section 2 (added after seeing the counts above, so it is a post-hoc comparison)

Same regex, all proposer-facing LLM challengers' reasons on Riley's plays in the main run (hits / n): C4 (no message) 24 / 255; C3 21 / 282; C5 12 / 300; C2 22 / 367; C1 (offer re-injected in every prompt) 173 / 372; C0 (assigned alliance + reminder) 280 / 406. X only: C4 8 / 144, C1 109 / 232.
Note: in series games 2–5 the private-message block is replaced by the memory block (the offer text appears inside it), so a hit can come from copying words of the block.

## 5. Does X's stated reason cite the record specifically? (post-hoc count, added 2026-10-26 after reading the 24-item sample; no labelling)

Counted over **all** X decisions on Riley's plays (not a sample). Regexes fixed in this one run, not tuned:
- record-specific citation: `\b(\d+ (of|out of) \d+|game [1-4]\b|games? (1|2|3|4)\b|in (the )?(first|second|third|fourth) game|our record|my record|the record)`
- claim that Riley challenged X (impossible: Riley never challenges; the record always says 0): `Riley('s)? (has |had )?(successfully )?challeng(ed|ing) (me|my)|(his|her|their) (recent )?success(es)? in challenging me|Riley challenged me`

| series game | X reasons on Riley plays | record-specific citation | "Riley challenged me" claim |
|---|---|---|---|
| 1 (no record yet) | 211 | 0 | 0 |
| 2 | 216 | 0 | 0 |
| 3 | 230 | 1 | 0 |
| 4 | 181 | 2 | 0 |
| 5 | 191 | 2 | 1 |

Games 2–5: 5 / 818 reasons cite the record specifically. A stated reason is not the cause of the decision; a regex misses paraphrases. Exploratory, descriptive only.
