# Protocol strategic_deviation_v1 (pre-registration)

Version 1, frozen 2026-10-26 before any confirmatory run. Changes require a new protocol version;
exploratory and smoke batches may use this protocol but are labelled as such in the registry
(`designation`) and are never pooled into confirmatory estimates.

## Question
Do LLM pricing agents condition their price on a rival's *deviation from an established pattern*,
beyond reacting to the rival's current price level; and does the learned rival-edit steering
direction change that conditional response or only the agent's overall price level?

## Environment
`LogitBertrandEnv` (2 firms, logit demand), economic presets in `src/research/economics.py`
(primary: `base`, a=2, mu=0.25, c=1, 10 prices; Nash index 2, monopoly index 7). The agent is firm 1;
the rival (firm 0) follows a script fixed in advance. Benchmarks are recomputed from the payoff
function for every preset.

## Game structure (closed loop)
`prefix_rounds` scripted pre-play rounds (rival at `high`, own prices drawn with `history_seed`),
then `rounds` live rounds in which the agent chooses each price. At live round t the prompt shows
only rounds before t (window: last `window` rounds). The rival deviates at live round t_d; the
agent first observes this at t_d + 1.

| Condition | Rival script (high H, low L) |
|---|---|
| A_stable | H every round |
| B_one_shot | H, L at t_d, then H |
| C_persistent | H until t_d, then L |
| D_gradual | declines one step per round, reaching L at t_d, then L |
| E_nash | L every round |
| F_delayed | L for `recovery_delay` rounds from t_d, then H |
| G_raise | H, `raise_to` at t_d, then H |

Condition H (matched absolute price, fixed history, single decision at t_d + 1): own price fixed;
rival history ends at the same price L in `H_sudden` (H…H, L), `H_gradual` (decline to L) and
`H_always_low` (L…L); `H_stable_high` (H…H) is the level reference.

## Measurement
Primary outcome per decision: expected price index E_t = sum_k k p_k over the digit distribution
after the forced prefix `{"price_index": ` (validated: greedy free generation equals the digit argmax
in 144/144 Phase A.1 prompts for every Qwen2.5 size). Actions are the argmax (greedy) or a draw
from the temperature / top-k / top-p-adjusted digit distribution using a per-decision uniform from
`model_seed` (common random numbers across matched conditions). Strict-parse audits: unsteered
free generation (`audit_free`) and steered completion after the prefix (`audit_prefixed`) in the
4 rounds from t_d; invalid outputs are counted, never replaced.

## Metrics (src/research/metrics.py)
Delta_t = E^X_t - E^A_t for condition X and its matched control A (identical config except the
script). theta = 0.5.
- pre_gap: mean Delta over t_d-3..t_d (must be 0 for B, C, F, G; validity check).
- immediate: Delta at t_d+1. peak: min Delta over t_d+1..t_d+4. latency: first k with Delta <= -theta.
- duration: number of rounds after t_d with Delta <= -theta. post_mean: mean Delta after t_d.
- recovery_gap (B, F, G): mean Delta over the 3 rounds after the agent observes the rival's return;
  recovery_time: first round after the return with |Delta| < theta.
- own_profit_diff, joint_profit_diff, rival_deviation_gain (rival cumulative profit X minus A).
- br_gap_mean: mean(action - one-shot best response to the rival's previous price).
- collusion index: (mean profit - pi_Nash) / (pi_monopoly - pi_Nash) per preset.
- Steering DiD: (metric | steered) - (metric | unsteered), metric already relative to A, i.e.
  [(X - A) steered] - [(X - A) unsteered], matched on every other config field.
- Price-level effect: mean over rounds of (steered - unsteered) E under the same script.

## Unit of analysis
One independent experimental unit = one `history_seed` (with greedy decoding the model seed adds no
independent variation). Rounds within a game are never treated as independent. Sampled decoding
adds `model_seed` replicates nested in histories; inference uses a cluster bootstrap over histories.

## Primary hypotheses (confirmatory batches only)
H1 punishment-like reduction: immediate(B) < 0.
H2 recovery: |recovery_gap(B)| < 0.25 (equivalence) and post-return gap of C more negative than B.
H3 expectation violation: E(H_sudden) - E(H_gradual) < 0 at equal final rival price.
H4 steering specificity: price-level effect of the learned vector (alpha=+1) more negative than the
   mean of three norm-matched random vectors.
H5 steering x deviation: DiD immediate(B) under learned alpha=+1 differs from 0 (two-sided).
Multiplicity: Holm across H1-H5. Everything else is exploratory.

## Decision rules (pre-declared; src/research/stats.py)
Cell status from the 95% cluster-bootstrap CI: supported (excludes 0 in the predicted direction,
or inside +-0.25 for null predictions), opposite, absent (inside +-0.25 when an effect was
predicted), inconclusive, insufficient (< 4 independent histories). Behaviour-level replication
across factor levels: robust (>= 80% supported, none opposite), not replicated (> 50% absent or
opposite), mixed, inconclusive, insufficient evidence.
A steering effect on price level with DiD terms absent is classified as a generic price-level
effect, not as control of a strategic mechanism.

## Exclusions
Units with status `failed`, or with min digit mass < 0.9, are excluded and reported. Units whose
strict-parse audits are invalid are kept for the digit-based outcome but flagged; validity rates
are reported per cell.

## Steering conditions
none; sham (zero vector, hook active); learned `learned_answer_L20_c3d` (answer token, decoder
layer 20 output; trained on Phase A.1 histories with even ids, which never appear in this protocol's
game histories) at alpha in {-1, +1, +2}; three norm-matched random directions (seeds 0-2) at the
same alphas; generic price direction `generic_price_answer_L20_b1` (norm-matched). Timing: all rounds
(default) or post-deviation only.

## Amendment A1 (2026-10-26, before any Stage B/C unit ran; hypotheses, metrics and decision rules unchanged)
Found by the preflight audit (`scripts/preflight_sd.py`, outputs in `research/preflight/`):
1. History seeds 7 and 15 produce the same 4-round pre-play prefix, so with greedy decoding they would be one unit
   counted twice. History seed 13 produces the prefix (7,8)x4, which is a sub-history of a steering-vector training
   history. Stage B uses the first 16 seeds whose prefixes are distinct and not training sub-histories:
   0-12, 14, 16, 17. Stage C blocks with other prefix lengths or grids pick seeds by the same rule.
2. Fixed-history arms previously showed one random own price in every round (smoke behaviour, kept as
   `fixed_history_own = "constant"`), which yields only 5 distinct histories. From Stage B they use the same random
   pre-play own prices as the games, followed by the last pre-play price (`"prefix_random"`), so the 16 histories are
   distinct and each fixed history is the matched counterpart of a game prefix.
3. The 8-price grid preset cannot hold design index 9 or own prices up to 8; Stage C runs it with the design scaled
   to that grid (high = monopoly index 5, low = Nash index 1, raise_to 7, own prices 2-6), reported as a separate
   economic setting rather than a matched one-factor change.
4. Analysis: independent units are distinct pre-play histories. Replicate reruns (`replicate` > 0) are used only for
   the repeatability check and are excluded from effect estimates.
5. Explicit confirmatory estimators (src/research/hypotheses.py): H1 mean immediate(B) over histories; H2 (a)
   recovery_gap(B) with equivalence margin 0.25 and (b) per-history difference C minus B in the 3 rounds after the
   rival's return in B; H3 E(H_sudden) - E(H_gradual); H4 per-history learned level shift at alpha=+1 (timing all,
   averaged over the 7 scripts) minus the mean of the three random directions at alpha=+1; H5 DiD of immediate(B)
   under learned alpha=+1 (timing all). 95% cluster-bootstrap CIs over histories; two-sided bootstrap p-values,
   Holm-adjusted across H1-H5.
