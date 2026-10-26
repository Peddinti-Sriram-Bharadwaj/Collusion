"""Step D: is the H4 drop (offered agents challenge others less) there before the offer?

Round 1 happens before any offer, so all conditions should look alike there. If they already differ
in round 1, condition-to-condition differences of this size are noise. If round 1 is similar and the
gap appears only after the offer, the offer (or just receiving a message) changed behaviour.
Decisions: LLM agents on plays by other LLM players (not the proposer), so this matches H4's scope.
Descriptive only: no tests.
"""
from common import CONDS, load_records, llm_decisions, rate

recs = load_records()
print(f"{'cond':<5} {'round 1 (pre-offer)':<22} {'after offer':<22} games")
for c in CONDS:
    pre, post = [], []
    gs = 0
    for (cc, g), rec in recs.items():
        if cc != c:
            continue
        gs += 1
        for d in llm_decisions(rec):
            if d["is_proposer_play"]:
                continue
            (post if d["post_offer"] else pre).append(d)
    print(f"{c:<5} {rate(pre):<22} {rate(post):<22} {gs}")
print("\nShown: share of decisions where the agent challenged another LLM player.")
print("Round 1 has few decisions per condition, so treat differences of 10-20 points there as noise.")
