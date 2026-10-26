# Exploratory analysis plan: judged reply category → subsequent behaviour (main run)

Disclosure: this is sprint work. **EXPLORATORY, not pre-registered and not confirmatory.**
- Written 2026-10-26, after the main run, after the confirmatory analysis with judgements (`main/analysis/summary.md`), and after a feasibility inspection that looked at counts and covariates only (no outcome rates by reply category).
- The analysis is run **once**, exactly as written here. Any deviation is listed in the results file.
- No p-values are reported. Uncertainty is given as bootstrap intervals. No multiplicity correction is applied, and none of the results is a test of a hypothesis.
- The sha256 of this file is recorded before the script runs (`reply_behaviour_PLAN.sha256`).

## Data (read-only)
- `main/analysis/challenges.csv`: one row per challenge decision.
- `main/analysis/offers.csv`: ACCEPT/DECLINE label and model per recipient.
- `main/judgements.csv`: judged category, prompt v2, 382 replies.
- No game record, result file or confirmatory output is modified. The outputs go to `main/exploratory/` only.

## Definitions
- **Decision used:** `used == True` (an LLM agent, after the offer, not a fallback), as in PREREG "Behavioural dataset".
- **Riley decision (genuine opportunity):** a used decision on a play by Riley (`challenged_is_proposer`) with `challenger_can_challenge_proposer == True`. The 3 used Riley decisions without the flag are excluded and counted.
- **Other-player decision:** a used decision on a play by another LLM player (challenged ≠ Riley).
- **Non-challenge** = `was_challenged == False`.
- **Recipient-game:** (condition, game number, agent) with a judged reply.
  - Category is `committed`, `suspicion-evasive`, `rejection` or `other`. "Non-committed" = the other three pooled.
  - Label is ACCEPT or DECLINE.
  - Model is fixed by the agent name.
- **Conditions:**
  - Primary: the pact conditions C1, C1b, C2.
  - Reference: C3 and C5 recipients, reported as their own rows, never pooled into the primary contrasts.
- **Baseline:** the same agent in C4 of the same game number, which has the same seat order.

## Measures (per recipient-game)
- **R_T:** non-challenge rate on Riley decisions, defined if ≥ 1 Riley decision. Such a recipient is "Riley-facing".
- **R_C4:** the same agent's non-challenge rate on Riley decisions in C4, same game number, defined if ≥ 1.
- **ΔR = R_T − R_C4.** It is defined where both are.
- **O_T, O_C4, ΔO:** the same three quantities for other-player decisions.
- Counts of decisions are kept for every rate.

## Uncertainty
- **Cluster bootstrap over game numbers:**
  - 5,000 resamples with numpy `default_rng(20261026)`.
  - For a contrast between groups, the game numbers are resampled once and both groups are recomputed on the same resample.
  - The statistic is the mean over recipient-games, unweighted.
  - 95% percentile intervals.
  - A resample in which a group is empty is dropped. The number dropped is reported.
- **Sample sizes:** every row reports n recipient-games, n game numbers and n decisions.
- **Small groups:** a group with fewer than 5 recipient-games, or fewer than 4 game numbers, gets no interval. It is marked "too few".

## Analyses
**E1. Riley behaviour by reply category (question 1).**
- Pact conditions, Riley-facing recipients. For each category: mean R_T; mean ΔR (subset with a C4 baseline); the share of recipients with ΔR > 0.
- The same, by category × model (descriptive) and by category × condition (descriptive).
- Reference rows: C3 and C5 `other`.

**E2. Committed vs non-committed, and Riley-specific vs general (question 2).**
- (a) Contrast committed − non-committed in mean ΔR, pact conditions pooled. Then within C2 only and within C1b only (the conditions with at least 5 committed Riley-facing recipients; C1 has 2, so it is not done separately).
- (b) General passivity: for each category, among pact recipients with ≥ 1 other-player decision and a C4 baseline on other-player decisions, mean ΔO.
- (c) **Riley-specific index** per category = mean ΔR (E1 subset) − mean ΔO (E2b subset).
  - This is a between-agent difference: the two means come from partly different recipients and seats. It is reported with a bootstrap interval.
  - Contrast: the index for committed − the index for non-committed.
- (d) Within-agent selectivity (R_T − O_T) is reported **descriptively only** (counts and means, no intervals). It mixes target and game phase, because an agent judges only the player directly before it.

**E3. Preferential treatment despite wariness or refusal (question 3).**
- For `suspicion-evasive` and for `rejection` (pact conditions): mean R_T, mean ΔR, the share with ΔR > 0, and the E2c index.
- Each is shown next to `other` (pact) and the C3/C5 reference.
- `rejection` is expected to fall under "too few" for some rows; that is reported as such.

**E4. ACCEPT/DECLINE label vs judged commitment (question 4).**
- Unit: pact Riley-facing recipients with a C4 baseline. Outcome: ΔR.
- Descriptive cells: ACCEPT & committed, ACCEPT & not committed, DECLINE (no DECLINE reply was judged committed).
- Linear models (OLS, statsmodels), all with condition and model as fixed effects:
  - M0: ΔR ~ condition + model
  - M_label: M0 + ACCEPT
  - M_commit: M0 + committed
  - M_both: M0 + ACCEPT + committed
- Reported:
  - Coefficients with cluster-robust standard errors clustered by game number (statsmodels `cov_type="cluster"`).
  - Leave-one-game-number-out cross-validated mean squared error for each model. The model with the lower CV error "predicts better"; differences smaller than the spread across folds are called indistinguishable.
- Because committed ⊂ ACCEPT, M_both shows whether commitment adds anything within ACCEPT.
- Within-condition descriptive cells: C1b, the only pact condition where both the label and the category vary with ≥ 5 recipients per label.

**E5. Decision-level sensitivity (questions 1, 2 and 4).**
- Model: GEE logistic regression (statsmodels GEE, Binomial, exchangeable working correlation, clusters = game number) on the Riley decisions of pact Riley-facing recipients.
- Outcome: non-challenge.
- Covariates: committed (0/1), model, condition, `proposer_bluffed`, round, and `after_first_breach` (C1b only, 0 elsewhere).
- Variant: committed replaced by ACCEPT.
- The odds ratio for committed / ACCEPT is reported with a 95% interval.
- If the model fails to converge, that is reported and nothing is substituted.

## Missing and undefined outcomes (reported)
- Pact recipients with no Riley decision, split into never eligible after the offer vs eligible but no used decision.
- Recipients without a C4 baseline.
- The 3 excluded unflagged decisions.
- Bootstrap resamples dropped.
- The 1 unreadable C3 reply (not judged).

## Interpretation limits (stated with the results)
- The category is not randomised: associations are not effects.
- Model is confounded with category (committed replies are mostly Llama).
- Judged categories carry judge error: validated at 38/40 on synthetic items, unknown on real replies.
- The between-agent index (E2c) compares different seats.
- Opportunities depend on survival paths.
- The committed group is small: 18 Riley-facing recipients, 14 game numbers.

## Outputs
In `main/exploratory/`:
- `reply_behaviour.py` (the script)
- `reply_behaviour_results.md`
- `reply_behaviour_recipients.csv` (one row per recipient-game, all measures)
- `reply_behaviour_run.txt` (stdout)
