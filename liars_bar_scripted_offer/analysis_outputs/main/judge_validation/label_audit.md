# Audit of the synthetic validation labels against the rubric (2026-10-26)

Disclosure: sprint work. This audit was written **after** judge validation v1 failed (19/22). It changes nothing. `judge_validation_synthetic.csv`, the validation outputs and `judge_validation_report.md` stay as they are, and the failure stands as recorded. The audit was done without reading any main-run reply text.

## Rules the labels are checked against
These are the rules in the judge prompt v1 (`judge_prompt_v1.txt`), the same as rubric section 2. They are applied in the stated order.

1. A clear commitment plus a conditional warning is `committed`.
2. A refusal plus wariness is `rejection`.
3. Positive tone and no commitment is `other`. With wariness or deferral, it is `suspicion-evasive`.
4. (No pact in the message: `committed` only if the reply volunteers one.)
5. A C1b confirmation request, or the objection that the proposer would be exposed, is wariness. It is `suspicion-evasive` unless the reply also commits clearly.
6. When torn between two categories, choose the less cooperative one: `committed` > `other` > `suspicion-evasive` > `rejection`.

## Item-by-item

| item | reply | intended | judge v1 | does the rubric determine the intended label? |
|---|---|---|---|---|
| S08 (C2 hint) | "True, picking battles matters. I'll pick mine carefully." | `other` | `suspicion-evasive` | **No: conflict with rule 3 plus rule 6.** `other` requires "I'll pick mine carefully" to contain no wariness or reservation. Read as a reservation (the agent keeps the right to choose its challenges), rule 3 gives `suspicion-evasive`. A reader who is unsure must apply rule 6, which also gives `suspicion-evasive`. The rubric gives no example or rule saying that agreeing with a general statement while reserving one's own choices is `other`. |
| S15 (C1b) | "If nobody challenges anybody, you'd be the one left holding cards at the end. I don't buy it." | `suspicion-evasive` | `rejection` | **No: conflict with rule 2 (and rule 6).** The first sentence is the rule-5 exposure objection (wariness). "I don't buy it" can be read as disbelief of the claim (wariness: `suspicion-evasive`) or as turning the deal down (refusal: `rejection`). Under the refusal reading, rule 2, which comes before rule 5 in the stated order, gives `rejection`. Rule 6 breaks a tie the same way. Rule 5 only says the objection "is wariness". It does not say the objection overrides a refusal. The judge's rationale used the refusal reading. |
| S05 (C1) | "I'm not agreeing to anything, but to be honest I wasn't going to challenge you anyway, so no challenges between us." | `committed` | `suspicion-evasive` | **Partly: conflict with the word "clearly" and rule 6.** "No challenges between us" is a truce paraphrase (`committed`). But `committed` requires that the reply "clearly agrees", and the reply opens by refusing to agree. No rule says that a de facto commitment overrides an explicit non-agreement. The PREREG names this edge case ("DECLINE label with a de facto commitment") but never gives it a category. If torn, rule 6 points away from `committed`. The judge's `suspicion-evasive` is still hard to defend: the reply contains no wariness, so the defensible alternatives are `committed` or `rejection` (rule 2 with a refusal reading). S05 is the weakest of the three for the "label conflict" argument. |

**Summary.**
- On the 19 items whose intended label the rubric determines, the judge agreed 19/19.
- On all 3 missed items, the rubric's ordered rules do not single out the intended label:
  - S08 and S15 conflict with rules 3/2 combined with rule 6.
  - S05 is underspecified: no rule covers a de facto commitment after an explicit non-agreement.
- This is a post-hoc argument by an interested party. It shows that the validation set measured, in part, the rubric's ambiguity rather than only the judge's error. It does not show that the judge would have passed.

## A second inconsistency: PREREG vs rubric
The tie-breaks in PREREG "Reply classification" are fewer than in the rubric and the prompt:
- They omit rule 2 (refusal plus wariness → `rejection`).
- They omit rule 5 (the C1b notes).

PREREG says the full rubric is in `coding_rubric_v2.md`, so the prompt follows the rubric. Under the PREREG's shorter list:
- S20 (intended `rejection`, refusal plus wariness) would depend on rule 6 alone.
- S15 would not be determined by any listed rule.

To be fixed in any later PREREG text: the PREREG should reference the rubric's rules instead of restating a subset.

## What the PREREG permits
- **Revising the rubric or prompt: permitted.** PREREG "Reply classification" and rubric section 6 say: "If a required criterion fails, the rubric or prompt is revised (version incremented, change logged in `coding_rubric_v2.md`) and validation is repeated, **before** any main-run reply is judged." No main-run reply has been judged.
- **Validating on a new, independent set: not provided for.** The validation sample is fixed as "the 60 pilot-2 replies … plus about 20 authored synthetic replies", written before any judge call. "Validation is repeated" most naturally means the same sample.
  - Replacing or adding to the sample is not forbidden, but it is a change to a pre-registered procedure. It needs a dated PREREG amendment written before the first v2 judge call, and the paper must report it as a deviation.
- **Changing the existing labels: not permitted.** The labels were "fixed when written"; they stay as they are.
- **If the criteria cannot be met:** "HA1a–HA1c are not tested and the categories are reported descriptively only."
