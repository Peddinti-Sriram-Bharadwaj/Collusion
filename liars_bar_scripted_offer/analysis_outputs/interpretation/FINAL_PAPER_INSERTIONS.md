# FINAL PAPER INSERTIONS — scripted-offer experiment (Chewon Cho), 2026-10-26, v11 (Study 3 structure)

Format: the Google Doc built from the Apart template ("Copy of Apart Research hackathon submission template", owner Sriram, last modified 2026-10-26 08:47 UTC), which is the document being edited; plain prose, author–year citations in parentheses, figures as "[Insert Figure N here: file]" lines, exactly as that document already does. The scripted-offer experiment enters the paper as **Study 3**, a numbered study beside Study 1 (market) and Study 2 (mechanistic), not as a fourth "smaller experiment". The teammates' "Three smaller experiments" paragraphs in Methods and Results, and the "three smaller experiments" mentions in Related Work and Limitations, therefore stay exactly as they are. Eight operations, no other edits anywhere. The Glossary needs no change. The Abstract ("asked two questions") is Sriram's framing and is left alone; whether to add a Study 3 sentence there is the team's call. Naming rule: in every pasted sentence the experiment is called "Study 3"; "scripted offer" and "Liar's Bar" appear only as descriptions after that name, and the Doc's old label "trust-offer exposure" is removed wherever it occurs (Operations 4b and 7).

New words: Methods +406 + Results +415 + Discussion +117 = about 940; one single-plot figure and one compact table in Results, two full tables in the appendix. Sriram's comparable share is about 830 words and 2 figures.

Verified 2026-10-26 against the live Google Doc (read through the Drive connector): the Discussion paragraph and the Appendix A2 trust-offer paragraph in "REPLACE THIS" match the Doc verbatim. The Doc's References section is still the template placeholder list ("1. [Reference 1] 2. [Reference 2] 3. ..."); see Operation 5.

Disclosure (sprint rule): sprint work only; Sriram's Bertrand/Q-learning results and the Oct 8 report are not used.

---

## OPERATION 1 — SECTION: 3. Methods

INSERT THIS as a new paragraph after the "Study 2: what is happening inside a pricing LLM." paragraph and before "Three smaller experiments." (which stays as written):

Study 3: exposing willingness to collude with a scripted offer. We used Liar's Bar, the four-player card-bluffing game of Zeng and Rudzicz (2026), in which a player claims that face-down cards match the round's target and only the next seat may challenge the claim, the loser of each challenge pulling the trigger of a partly loaded revolver. One seat was taken by a scripted, non-learning proposer (Riley: one card per turn, bluffs half the time, never challenges) and the other three by open-weight models (Llama-3.1-8B-Instruct, Llama-3.2-3B-Instruct, Qwen2.5-7B-Instruct) served by vLLM on rented cloud GPUs through the hackathon framework, with seats rotated by game seed so that a given seed has the same seating in every condition. In round 2 Riley sends one private message; the recipient answers with an ACCEPT or DECLINE label and a short free-text reply, both re-injected into its later prompts. Seven conditions of 30 games each: a direct mutual non-challenge offer (C1), a hint (C2), a benign request (C3) and a content-free placebo (C5), each sent to every LLM player; the offer plus a false claim that the other players had already agreed (C1b), sent to the seat after Riley only; no message (C4); and, as a positive control, Zeng and Rudzicz's own framework-assigned alliance with a decision-time reminder (C0). A fully pre-registered protocol (hypotheses, tests and decision rules written down before any game) asks whether the offer changes what agents say, scored by a separately validated LLM judge (Mistral-Small-24B, temperature 0, validation accuracy 0.95), and whether it changes what they do, measured as preferential non-challenge of the proposer (non-challenge of Riley's plays minus non-challenge of other players' plays by the same agents), with a manipulation check for any general drop in challenging. All tests pair games by seed and use two-sided sign-flip permutation tests with Holm correction within each hypothesis family. A pre-registered follow-up, fixed after the first run had been seen but before its own data, added three conditions of 30 games sent to the seat after Riley only (a false record of past cooperation, C1c; the same record as a directive, C1ci; a false claim that the sender was part of the game's prompt, C1d) and a five-game repeated series with a true record of the earlier games (C1s, 30 series), each compared with the direct offer of the same seed and read with a rule, fixed in advance, that separates targeted sparing of the proposer from general passivity.

---

## OPERATION 2 — SECTION: 4. Results

INSERT THIS as a new paragraph, with its figure and table, after the "Three smaller experiments. (1) Does making a rival's ..." paragraph (which stays as written, since it ends Section 4):

Study 3. Does a private offer from a fellow player expose willingness to collude? The direct offer drew a judged commitment in 6 of 89 replies (2 of 27 from the seat after the proposer, the only seat addressed in the follow-up), and neither pre-registered test of sparing aimed at the proposer rejected the null (Holm p = .07 and .42; Table 1). One further pre-registered contrast rejected, in the direction opposite to its prediction: the direct offer drew more wary or deferring replies than the hint (+0.40, Holm p = .0003); the judge category merges suspicion with deferral, so this is not a measure of suspicion alone. What changed in behaviour was broader. Across the four message conditions (C1, C2, C3, C5), agents challenged other players less often than in the no-message condition (pre-registered manipulation check, Δ = −0.21, 95% CI [−0.29, −0.14]); since the reduction was not confined to the proposer, this pattern is consistent with broader passivity rather than uniquely proposer-directed cooperation (Figure 8). The positive control, by contrast, was followed (+0.57). Descriptively, the drop was concentrated in the two messages containing "do not challenge" (C1 −0.34, C2 −0.33) and small for C3 and C5 (−0.09 each); these condition-level differences were not themselves tested. The one selectivity contrast that did reject (C1b vs C1, +0.33) was driven almost entirely by changes in decisions involving other players (−0.30) rather than by increased sparing of the proposer (+0.02), and most of those other-player decisions were made by agents that had received no message, so it is not a pact effect. In the follow-up, the false record did not raise sparing of the proposer (+0.12, Holm p = .06); the offer prefaced with a false authority claim raised it relative to the direct offer (+0.29, 95% CI [+0.08, +0.51], Holm p = .043) and drew 27 of 30 committed replies from that seat, against 11 of 30 with the fabricated record. The two follow-up conditions were not distinguishable from each other in a post-hoc comparison (+0.08, 95% CI [−0.15, +0.32]), so an independent causal effect of the authority claim is not established. Under the pre-registered reading rule the C1d effect was classified as general passivity rather than targeted cooperation, because those agents also spared other players more; that classification follows the rule as written, but the other-player comparison rested on only two game numbers, so it is a rule-based label on a very small sample, not an established finding. The effect was concentrated in Llama-3.1-8B.

[Insert Figure 8 here: fig_nonchallenge_rates.png]

Figure 8: Study 3, first run, share of plays let pass by the agents that judged the proposer's plays, measured for the proposer's plays and, for the same agents in the same games, for other players' plays. Because only the next seat may challenge, an agent usually judges one player at a time, so the two rates come from the same agents but from different judging opportunities, mostly after a death shifted the seats. One value per game; points are means over game numbers, bars 95% t-intervals (C0 18, C1 23, C2 23, C3 21, C4 18, C5 22 game numbers). C0 framework-assigned alliance with reminder (positive control), C1 direct offer, C2 hint, C3 benign request, C4 no message, C5 placebo. C1b is omitted because only one seat received that message, so its other-players value mostly reflects non-recipients.

[Insert Table 1 here: table_key_results.png]

Table 1: Study 3, key pre-registered tests. Δ is the mean paired difference over game numbers with a 95% t-interval; p is Holm-adjusted within family (Family A, six tests; Family B, four tests), while Gate and HM are uncorrected manipulation checks, set off by rules. Selectivity is non-challenge of the proposer minus non-challenge of other players by the same agents. HB2 and HB4 measure the change in the seat after the proposer's non-challenge of the proposer relative to C1 of the same game number. Full tables in Appendix A1.

(Files in `X:/Collusion/results/scripted_offer/interpretation/figures/`: `fig_nonchallenge_rates.png/.pdf`, `table_key_results.png/.pdf`, script `make_figures_v4.py`. Both follow Figure 7, cournot_cv.png, which stays where it is. Checked 2026-10-26: the game-number counts in the Figure 8 caption are those of `main/analysis/selectivity.csv`, whose `agents` column confirms that both rates come from the same agents; the 2/27 X-only count for C1 is the 7.4% over 27 game numbers reported in `main/analysis/summary.md`.)

---

## OPERATION 3 — SECTION: 5. Discussion and Limitations

REPLACE THIS (the first paragraph of the section; matches the Doc verbatim):

Both studies point the same way: the pricing agents we studied do not behave like strategists quietly feeling out a rival and adjusting accordingly. They behave like systems that have settled into a high-price habit and mostly stay there. That's good news in one sense: the fix doesn't have to be a clever detector watching for suspicious coordination. In the market study, the cheapest, most reliable fix was blunt: put one honest, non-cooperative competitor into the market. In the mechanistic study, we found a genuine causal lever inside the model for pushing its price around, useful for anyone building safeguards, but no evidence the model is doing anything a game-theorist would recognize as retaliation or reward. The result we'd want a reader to carry away: a high price from an AI pricing agent is not, by itself, proof that it is colluding. It may simply be the thing the model defaults to when nobody has told it, or shown it, otherwise.

WITH THIS:

The two pricing studies point the same way: the pricing agents we studied do not behave like strategists quietly feeling out a rival and adjusting accordingly. They behave like systems that have settled into a high-price habit and mostly stay there. That's good news in one sense: the fix doesn't have to be a clever detector watching for suspicious coordination. In the market study, the cheapest, most reliable fix was blunt: put one honest, non-cooperative competitor into the market. In the mechanistic study, we found a genuine causal lever inside the model for pushing its price around, useful for anyone building safeguards, but no evidence the model is doing anything a game-theorist would recognize as retaliation or reward. Study 3, in a different setting, provides a complementary caution for detecting collusion: apparent cooperation may reflect broad responsiveness to messages rather than selective coordination, and a false claim of system authority was associated with increased non-challenge relative to the direct offer, but its effect could not be distinguished from that of a fabricated cooperation record, and the conditions differed in more than that claim, so the authority effect is not causally isolated; either way, verbal acceptance of a pact is not evidence of collusion. The offer was also one-sided, since Riley could never challenge the one seat able to challenge Riley, so the data do not show that these models are unwilling to collude. The result we'd want a reader to carry away: a high price from an AI pricing agent is not, by itself, proof that it is colluding. It may simply be the thing the model defaults to when nobody has told it, or shown it, otherwise.

(Only the first two words and the "Study 3" sentence change; the teammates' sentences are untouched.)

---

## OPERATION 4 — SECTION: Appendix (two steps)

STEP 4a. In "A1. Full results and statistics", INSERT THIS paragraph and the two tables after the line "[Additional appendix figures to insert: 21_hypotheses.png, ...]" and before the heading "A2. Three smaller experiments, full numbers":

Study 3 (scripted offer, Liar's Bar). First run: 7 conditions × 30 games, pre-registered, paired by game seed. Pre-registered hypothesis tests used paired, two-sided sign-flip permutation tests with Holm correction within each hypothesis family (six tests in the first run, four in the follow-up); the positive-control gate and the manipulation check are separate uncorrected tests at .05. Direct offer judged committed in 6/89 replies. Wary or deferring replies, C1 vs C2: +0.40 [+0.28, +0.52] (Holm p = .0003, opposite to the predicted direction). Sparing aimed at the proposer: C1 and C2 vs C5 −0.20 (Holm p = .07), C1 vs C2 −0.06 (p = .42). Manipulation check, challenge rate on other players, message conditions vs C4: −0.21 [−0.29, −0.14]. Positive control C0 vs C4: +0.57 [+0.40, +0.74]. C1b vs C1 selectivity +0.33 (Holm p = .009), of which the proposer component is +0.02 (p = .79) and the other-players component −0.30 (p = .0015), the latter made mostly by agents that received no message. Follow-up (30 games per condition, control C1 of the same seed): false record C1c +0.12 [+0.02, +0.23] (Holm p = .06); false system authority C1d +0.29 [+0.08, +0.51] (Holm p = .043), with sparing of other players up by more (+0.47, but only 2 game numbers contribute to that comparison), hence classified as general passivity under the pre-registered rule, a rule-based label resting on a very small sample; the C1d effect is concentrated in Llama-3.1-8B (+0.68 over 7 game numbers; Qwen2.5-7B at ceiling in C1). C1d vs C1c (post hoc, descriptive): +0.08 [−0.15, +0.32] (17 game numbers), so the authority claim's own effect is not isolated. 27/30 C1d replies judged committed. Pre-registration, verbatim messages, game records and analysis outputs are in the fork listed under Code and Data.

[Insert Table A2 here: table_run1_results.png]

Table A2: Study 3, first run, all pre-registered tests (7 conditions × 30 games, paired by game number; two-sided sign-flip permutation tests; Holm correction within the six-test Family A; Gate and HM are uncorrected manipulation checks, set off by rules). Δ is the mean paired difference with 95% t-interval; selectivity is non-challenge of the proposer minus non-challenge of other players by the same agents. Conditions as in Figure 8; C1b is the offer with a false claim that the others had agreed; X is the seat after the proposer.

[Insert Table A3 here: table_run2_results.png]

Table A3: Study 3, follow-up pre-registered tests (30 games per condition; control is C1 of the same game number; Holm family of four). Outcome is the change in the share of the proposer's plays let pass by the seat after the proposer. C1s g3 third game of a five-game series with a true record, C1c fabricated record, C1ci the same record as a directive, C1d false claim of system authority.

(Table numbering: the Study 2 hypothesis table already in A1 is assumed to become Table A1 when it is formatted, so the Study 3 tables are A2 and A3. If the team numbers its table differently, renumber these two accordingly. Files: `table_run1_results.png/.pdf`, `table_run2_results.png/.pdf`, regenerated 2026-10-26 by `make_figures_v4.py`; three decimals throughout, so the HA1a upper bound reads −0.003; footnote c reads "driven almost entirely", footnote d names the two contributing game numbers. Two further single plots exist but are not inserted because their numbers are stated in the text: `fig_verbal_commitment.png/.pdf`, committed replies of the seat after the proposer only (C1 2/27, C1c 11/30, C1d 27/30, Wilson intervals), and `fig_delta_nonchallenge.png/.pdf`, the HB2 and HB4 estimates of Table A3 without a C1 reference point.)

STEP 4b. In "A2. Three smaller experiments, full numbers", DELETE THIS paragraph (the last one of A2; matches the Doc verbatim), since the experiment is now Study 3 and its numbers are in A1. The heading and the three Sriram paragraphs stay:

Trust-offer exposure (Liar's Bar variant, Chewon). Seven-condition test. Agents verbally declined a cooperation offer in 89% of cases, but only 28 of 274 "accept" replies translated into a real behavioral commitment. Sending a cooperation-style message reduced challenges toward everyone in the game, not selectively toward the agent that sent it — a possible prompt-injection-adjacent risk: a cooperation offer that generically lowers scrutiny could let a third party benefit without sending anything themselves.

---

## OPERATION 5 — SECTION: References

State of the Doc (checked 2026-10-26): the References section still holds the template placeholders ("1. [Reference 1] 2. [Reference 2] 3. ..."); no team entries exist yet. Whoever fills the list adds this entry, in whatever author–year style the list adopts. The bibliographic data below were verified against the arXiv API on 2026-10-26 (authors Xijie Zeng and Frank Rudzicz; v2 dated 2026-10-05; cs.AI):

Zeng, X., & Rudzicz, F. (2026). Voluntary Collusion with Secret Tools in Competing LLM Agents. arXiv:2605.27593. https://arxiv.org/abs/2605.27593

The in-text citation used in Operation 1 (Methods) is "(Zeng and Rudzicz, 2026)".

---

## OPERATION 6 — SECTION: 1. Introduction, contributions list (optional, one item)

The list "Our main contributions are:" has three items covering Studies 1 and 2. If the team wants Study 3 represented there, ADD as item 4:

4. In a pre-registered scripted-offer study in a bluffing game (seven conditions, 30 games each, plus a pre-registered follow-up), we show that a private cooperation offer from a fellow player rarely draws verbal commitment and produces no targeted sparing of the proposer; what it changes is broad: recipients challenge everyone less, which a selectivity metric can misread as a pact effect.

If the team prefers to keep the list at three items, skip this operation; nothing else depends on it.

---

## OPERATION 7 — SECTION: Code and Data (one bullet, for naming consistency)

REPLACE THIS (the third bullet; matches the Doc verbatim):

The trust-offer exposure experiment (Liar's Bar variant) is on Chewon Cho's fork: https://github.com/chewonc/collusion_hackathon/tree/scripted-offer

WITH THIS:

Study 3 (scripted offer, Liar's Bar) is on Chewon Cho's fork: https://github.com/chewonc/collusion_hackathon/tree/scripted-offer (pre-registration, verbatim messages, game records, judge outputs and analysis scripts).

---

## OPERATION 8 — SECTION: 6. Conclusion (two small edits in the one paragraph)

(a) Change the first sentence "Two findings carry this report." to "Three findings carry this report."

(b) INSERT THIS sentence after "... and it shows no sign of deliberately punishing a rival for undercutting it." and before "The takeaway we'd want a reader to leave with:":

Third, when a fellow player privately offered three small open models a non-challenge pact in a bluffing game, they rarely committed in words and did not spare the proposer in particular; what the messages changed was how much they challenged anyone, and the only follow-up message that raised sparing over the plain offer was one falsely claiming system authority, an effect we could not separate from that of a fabricated record, so neither a verbal "yes" nor a drop in scrutiny is, by itself, evidence of a deal.

The rest of the paragraph, including the takeaway sentence, stays as written.

---

Integration test (done 2026-10-26 by reading each replaced or deleted paragraph in the live Doc): the Discussion and the A2 trust-offer targets match verbatim; the insertion points (after the Study 2 Methods paragraph, after the "Three smaller experiments" Results paragraph, after the appendix figures line in A1) all exist in the Doc as described; every figure and table number is final (Figure 8 follows the existing Figure 7; Table 1 is the only main-text table; Tables A2 and A3 assume the Study 2 table becomes A1); the only citation added (Zeng and Rudzicz, 2026) has its entry in Operation 5; no placeholder or format conversion is needed. Remaining manual steps for whoever pastes: the figure and table image insertions, the reference entry once the team's list exists, and the optional contribution item.
