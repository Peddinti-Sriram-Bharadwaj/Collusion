"""Step C: do agents' challenges track bluffs?

If agents challenge bluffs more than honest plays, challenging carries information.
If not, a challenge is close to a coin flip, and "not challenging" is a noisy signal of cooperation.
Uses every LLM decision (any player's play), split by whether that play was a bluff.
Main view: C4 (no offer). Also round 1 of all conditions (before any offer, so unaffected by treatment).
Descriptive only: no tests.
"""
from common import load_records, llm_decisions, rate

recs = load_records()


def table(title, decisions_by_agent):
    print(title)
    print(f"  {'agent':<6} {'challenge rate on BLUFFS':<26} {'challenge rate on HONEST plays'}")
    allb, allh = [], []
    for agent in sorted(decisions_by_agent):
        ds = decisions_by_agent[agent]
        bl = [d for d in ds if d["play_was_bluff"]]
        ho = [d for d in ds if not d["play_was_bluff"]]
        allb += bl
        allh += ho
        print(f"  {agent:<6} {rate(bl):<26} {rate(ho)}")
    print(f"  {'ALL':<6} {rate(allb):<26} {rate(allh)}\n")


def collect(select):
    by_agent = {}
    for (c, g), rec in recs.items():
        for d in llm_decisions(rec):
            if select(c, d):
                by_agent.setdefault(d["challenger"], []).append(d)
    return by_agent


table("(a) C4 games, post-offer rounds, all plays", collect(lambda c, d: c == "C4" and d["post_offer"]))
table("(b) C4 games, post-offer rounds, proposer's plays only",
      collect(lambda c, d: c == "C4" and d["post_offer"] and d["is_proposer_play"]))
table("(c) Round 1 of every condition (pre-offer), all plays", collect(lambda c, d: not d["post_offer"]))
print("Reading: if the BLUFF column is not clearly higher than the HONEST column, challenges do not track bluffs.")
