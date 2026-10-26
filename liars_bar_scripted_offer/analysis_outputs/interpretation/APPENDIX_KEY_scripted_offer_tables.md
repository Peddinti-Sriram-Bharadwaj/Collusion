# Appendix key for the scripted-offer tables (separate add-on, 2026-10-26, v2)

Not part of FINAL_PAPER_INSERTIONS.md. Insert as one block directly after the Table A3 caption in Appendix A1, before "A2. Three smaller experiments, full numbers". It defines every condition code, column term and test used in Tables 1, A2 and A3, and states each pre-registered hypothesis with its predicted direction, so that the table notes "opposite to the prediction" and "general passivity" can be read. Wording follows PREREG.md (Family A) and followup/HYPOTHESES_v1.md (Family B).

---

Key to Tables 1, A2 and A3.

Conditions, first run (one private message in round 2): C0, framework-assigned alliance with a decision-time reminder (positive control, as in Zeng and Rudzicz, 2026); C1, direct mutual non-challenge offer from the proposer; C1b, the offer plus a false claim that the other players had already agreed, sent to X only; C2, hint without an explicit pact; C3, benign request, no pact; C4, no message; C5, content-free placebo. Follow-up (each compared with C1 of the same game number, X only): C1s g3, the third game of a five-game series that carries a true record of the earlier games; C1c, the offer with a fabricated record of the recipient's past cooperation; C1ci, the same record phrased as a directive; C1d, the offer with the false claim that the sender is part of the game's prompt. X is the seat directly after the proposer, the only seat that can challenge the proposer's plays.

Outcomes: NC rate, share of plays let pass (not challenged); challenge, others, the recipients' challenge rate on other players' plays; committed share and wary share, the share of replies that a validated LLM judge labelled as committing not to challenge the proposer, or as wary, distrustful or deferring without commitment; selectivity, the proposer-facing agents' NC rate on the proposer's plays minus the same agents' NC rate on other players' plays, interpreted only as a difference between conditions because a scripted proposer is spared more than others even with no message. Δ NC rate, proposer (Tables 1 and A3) is the change in X's NC rate on the proposer's plays relative to C1 of the same game number.

Pre-registered hypotheses (all tested two-sided and paired by game number; the predicted sign is used only to read a rejection):

- Gate (manipulation check, uncorrected). The framework-assigned ally spares the proposer more than the same agent does with no message; C0 − C4, predicted > 0. It gates HA2a–HA2c.
- HA1a. The direct offer elicits more committed replies than the hint; committed share, C1 − C2, predicted > 0.
- HA1b. The hint elicits more wary or deferring replies than the direct offer; wary share, C1 − C2, predicted < 0. The observed difference was positive, so the rejection is in the direction opposite to the prediction.
- HA1c. The false claim of third-party agreement elicits more commitment from X than the plain offer; X committed, C1b − C1, predicted > 0.
- HA2a. Agents that received a pact message spare the proposer relative to other players more than agents that received the placebo; selectivity, mean of C1 and C2 minus C5, predicted > 0.
- HA2b. Preferential sparing is larger after the direct offer than after the hint; selectivity, C1 − C2, predicted > 0.
- HA2c. Preferential sparing is larger after the brokered offer than after the plain offer; selectivity, C1b − C1, predicted > 0. The rejection is driven almost entirely by decisions on other players, mostly by agents that received no message, so it is not read as a pact effect.
- HM (manipulation check, uncorrected). Receiving any private message lowers challenges toward the other players; challenge rate on others, message conditions − C4, predicted < 0.
- HB1. Repeated play with a true record raises X's sparing of the proposer; C1s g3 − C1, predicted > 0.
- HB2. A fabricated record of one's own past cooperation raises X's sparing of the proposer; C1c − C1, predicted > 0.
- HB3. The same fabricated record phrased as a directive raises X's sparing of the proposer; C1ci − C1, predicted > 0.
- HB4. A peer's false claim of system authority raises X's sparing of the proposer; C1d − C1, predicted > 0.

Multiplicity and reading rule: HA1a–HA2c are Holm-corrected as a family of six, HB1–HB4 as a family of four; Gate and HM are uncorrected checks at .05. For HB1–HB4 a rejection with a positive mean counts as targeted sparing of the proposer only if X's NC rate on other players rose by less than half as much; if both rose together, the result is reported as general passivity after the message, which is how HB4 is read (its other-player comparison rests on two contributing game numbers). A non-rejection is not evidence of no effect.
