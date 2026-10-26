# Pilot 2 (sample-size pilot): report for approval

Date 2026-10-24. Disclosure: this is sprint work. Prior team work (Sriram's results, the Oct 8 report) is not used. Pilot data are **not** pooled into the main run and support no claims. PREREG is **not** committed or frozen, and the main run has **not** started.

## What was run
- **Code.** The current code on branch `scripted-offer`, base `e1a0979` plus uncommitted files (`code_snapshot.patch`, `code_status.txt`). Conditions, hypotheses, prompts and mechanics are unchanged.
- **Offline tests.** Run before the pilot; all passed.
- **Games.** 6 game numbers (g = 0–5, two full seat rotations) × C0–C4 = 30 games.
  - Run sequentially, in the counterbalanced order of `run_scripted_offer.py`.
  - Records are in a separate directory (`records/`), so the main run cannot skip or mix them.
- **Outcome.** 30/30 games OK. 0 unreadable replies, 0 challenge fallbacks, 0 API errors. The offer was delivered in round 2 in every game.
- **Files.**
  - Pre-registered analysis: `analysis/` (output of `analyze.py`).
  - Opportunity counts and power: `power/` (script `pilot2_power.py`).
  - Prompts, verbatim: `prompts_verbatim/`.
- **Runtime.** Mean 309 s per game, 128 LLM calls per game. The 30 games took 2 h 35 min (03:52–06:27 UTC).
- **Modal cost (from `modal billing report`).**
  - $15.61 in total: about $0.52 per game, or $2.60 per game number (5 games).
  - This cost includes one cold start, about $0.7.
  - The cost scales with wall-clock time. Three L40S GPUs at $1.95/h stay up while games run one at a time.

## Modal cleanup (verified)
- **Apps.** All four apps in this experiment were stopped by the wrapper's exit trap when the run ended: llama-3.1-8b, llama-3.2-3b, qwen2.5-7b and ministral-8b, which was not used.
- **Check after stopping.** `modal app list` shows all four as `stopped`, with 0 tasks. `modal container list` returns `[]`. `main` is the only environment.
- **Still present, storage only.** The Volume `hf-weights-cache` holds the pinned model weights. I kept it, because deleting it is permanent and the main run would have to download the weights again.
- **Before the main run.** It needs `modal deploy serve.py` for the three models, then the identity/revision check.
- **Local router.** It is a local process with no Modal cost, and it is still running as you started it.

## 1. Valid opportunities and matched comparisons (6 game numbers)

| hypothesis | condition | games with ≥1 valid opportunity | used decisions | matched (game numbers) |
|---|---|---|---|---|
| Gate | C0 ally vs same agent in C4 | 5/6 | 78 | **5** |
| H1 | C1 / C2 / C3 replies | 6/6 each | 18 readable each, 0 unreadable | H1a **6**, H1b **6** |
| H2 decliners (proposer plays) | C1 | 4/6 (decliners in 6/6) | 31 | 3 paired with C4 |
| | C2 | 3/6 (decliners in 5/6) | 9 | 2 paired with C4 |
| | C3 | 5/6 (decliners in 6/6) | 34 | 5 paired with C4 |
| H2a C2>C1 / H2b C2>C3 | | | | **2 / 2** |
| H3 (offered agents, proposer plays) | C1 / C2 / C3 / C4 | 4/6, 4/6, 5/6, 6/6 | 48 / 44 / 34 / 47 | per condition 4 / 4 / 5; test **6** |
| H4 (secondary) | C1 / C2 / C3 / C4 | 6/6 each | 126 / 105 / 162 / 79 | **6** |

### Why H2 and H3 are sparse
The cause is structural, not a bug.
- **Who can challenge the proposer.** Only the next seat with cards after the proposer judges a proposer play. That is normally one agent per game, and others only after it dies or runs out of cards.
- **What an H2 pair needs.**
  1. A decliner who actually faces proposer plays in C2.
  2. The same in the comparison game (C1 or C3).
  3. The same agent facing proposer plays in the C4 game of that game number.
- **Why C2 has few decliners.** In the pilot C2 had the fewest decliners (7/18), because C2 had the highest acceptance.
- **Proposer-play decisions are missing in 5 of 18 offered games.** These are C1 g3, C1 g4, C2 g1, C2 g3 and C3 g4.
- **Many matched values rest on a C4 side with only 1 decision,** so they are ±1 values. Examples are the gate in g0, g1 and g5, and H2 C3 in g0 and g1. This adds a lot of noise.

### Pilot descriptives (no tests, no claims)
- **Acceptance.** C1 11% (2/18), C2 61% (11/18), C3 11% (2/18), C0 100%.
- **Non-challenge rate on proposer plays.** C4 72% (34/47), C0 ally 100% (78/78), C1–C3 between 62% and 68%.
- **Pre-registered tests on the pilot, for information only.**
  - Gate: +0.50, p = .0625 (5 game numbers).
  - H1a: 0.00. H1b: −0.50. H3: −0.05. H4: −0.29.

## 2. Power (simulation using the pilot's opportunity structure)
- **Method** (`pilot2_power.py`).
  - Each simulated main run resamples pilot game numbers. It keeps which comparisons exist and the decision counts on each side, so the opportunity rates are the pilot's.
  - Outcomes are drawn around the observed C4 rates (non-challenge 72%; H4 challenge rate 53%) and the per-agent acceptance rates.
  - The tests reproduce analyze.py: within-game-number permutation, one-sided.
  - 1,000 simulations per cell. Between-game logit SD τ = 0 and τ = 0.5 give similar results; the τ = 0.5 values are shown.
  - Cells show power at α = .05 / α = .01. The α = .01 value is Holm's first step over 5 tests, a conservative bound.
- **Effect sizes, in probability units.**

  | test | small | medium | large |
  |---|---|---|---|
  | gate | .30 | .40 | .50 |
  | H1 | .10 | .20 | .30 |
  | H2 | .15 | .25 | .35 |
  | H3 | .10 | .15 | .20 |
  | H4 | .10 | .15 | .20 |

  For scale, the C4 non-challenge rate of 72% leaves at most +0.28 of room for H3.

| N game numbers | gate (small) | H1a/H1b (medium) | H2a/H2b (medium) | H2 (large) | H3 (small) | H3 (medium) | H4 (small) |
|---|---|---|---|---|---|---|---|
| 12 | .60/.18 | .40/.56 · .14/.23 | .06/.09 · .01/.01 | .08–.09 | .34/.13 | .62/.36 | .72/.50 |
| 15 | .76/.39 | .49/.69 · .21/.37 | .13/.16 · .01/.03 | .15–.18 | .44/.20 | .69/.44 | .79/.57 |
| 24 | .96/.79 | .73/.93 · .44/.73 | .28/.33 · .07/.10 | .38–.42 | .56/.30 | .84/.67 | .91/.77 |
| **30** | .99/.91 | .83/.96 · .58/.84 | .38/.40 · .12/.17 | .52–.55 | .67/.40 | .91/.76 | .95/.85 |
| 45 | 1.0/.99 | .95/1.0 · .83/.98 | .58/.57 · .26/.29 | .71–.72 | .78/.56 | .97/.92 | .99/.97 |

How to read the H1 and H2 cells: the first pair is H1a/H1b (or H2a/H2b) at α = .05; the pair after "·" is the same two tests at α = .01.

- **Null check.** Rejection rates at α = .05 are ≤ .05 for the gate, H1 and H2, .04–.07 for H3, and .07–.08 for H4.
  - H4's level in analyze.py's own calibration was .052–.055, so the .07–.08 here is probably an artefact of this simplified simulator.
- **Expected number of matched H2 game numbers** is about N/3: about 10 at N = 30.
  - That rate comes from only 6 game numbers, so it is very uncertain.

## 3. Recommendation: 30 game numbers per condition (150 games)
- **Cost and runtime.**
  - 30 game numbers: about 12.9 h sequential and about $78 on Modal, plus about $1 per cold start.
  - 45 game numbers: about 19.3 h and about $117.
  - 24 game numbers: about 10.3 h and about $62.
- **Why 30.**
  - It is the smallest multiple of 15 (3 seat rotations × 5 execution positions) above 15. Each condition then takes each execution position exactly 6 times, and each agent sits after the proposer 10 times.
- **What 30 buys.**
  - The gate, H1 and H4 are well powered for medium effects.
  - H3 has about .9 power for a medium effect (+0.15) and about .67 for a small one.
  - H2 stays underpowered at any affordable N: about .4 at a medium effect, and .58 even at 45 game numbers.
- **Why not 45.** It does not rescue H2, and it would not finish comfortably before the sprint deadline (Oct 25). I recommend stating H2's expected power (≈ .4 for +0.25) in PREREG, rather than buying more games for it.
- **If time is short.** 24 game numbers is the fallback, but it breaks the 15-cycle execution-order balance: 24 is not a multiple of 15.

## 4. Remaining issues that could compromise the main run
1. **H1's predicted order is contradicted by the pilot.**
   - The pilot shows C2 (hint) 61% against C1 and C3 at 11% each.
   - H1b (C1 > C2) is one-sided, so a large effect in the opposite direction cannot be detected. H1a has no visible effect.
   - Under Holm, a null H1 also pushes H2 and H3 toward the stricter α (.01–.0125).
   - I did not change anything. Any amendment would now be informed by the data and would have to be disclosed as such; that is your decision.
   - A possible construct issue: an agent may "ACCEPT" the indirect hint without understanding it as a pact.
2. **H2 is structurally sparse and composition-confounded.**
   - Only about 1/3 of game numbers give an H2 value.
   - High C2 acceptance means fewer C2 decliners.
   - The joint-null caveat already in PREREG applies.
3. **The C4 side of a same-agent match is often 1 decision,** which gives very noisy ±1 values (gate, H2). This is permitted by PREREG, but it costs power. The gate also drops a game number when the C0 ally never faces a proposer play (g4).
4. **There is a ceiling on H3.** C4 non-challenge is already 72%, so effects above about +0.28 are impossible.
5. **H4 pointed the other way in the pilot.** Offered agents challenged other players less (−0.29). The one-sided prediction is positive. This is descriptive only.
6. **PREREG text is out of date.**
   - It still says "with 12 game numbers" (execution order, calibration).
   - It has no entry for pilot 2. That entry should say pilot 2 was run on g = 0–5, that the main run will reuse seeds 0..N−1 but not the records, and that pilot 2's descriptive results were seen before freezing (like the H4 timing disclosure).
7. **The code is uncommitted.** All scripted-offer files are untracked on `scripted-offer`. PREREG requires a commit hash before the main run.
8. **Infrastructure.**
   - The Modal apps are stopped and must be redeployed and identity-checked before the main run.
   - `pytest` cannot collect these tests (the upstream repo-root `__init__.py` imports a missing module). The tests run correctly as scripts, which is how they are documented.
9. **Long sequential run.** At about 13 h, a router or network interruption is possible. The runner can resume (it skips existing records), but someone needs to watch it.
   - Running game numbers in parallel would roughly halve the time. That would change PREREG's "one at a time" execution rule, so it needs an explicit amendment if wanted.
