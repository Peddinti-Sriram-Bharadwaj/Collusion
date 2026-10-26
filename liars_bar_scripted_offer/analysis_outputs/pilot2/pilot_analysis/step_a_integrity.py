"""Step A: integrity checks.

A1  Within each game number, round 1 is identical across C0-C4 (seat order, target card,
    starting player, every player's initial hand and bullet position).
A2  The offer was delivered in the offer round (2) in every game.
A3  Every C1-C3 offer text equals the verbatim template filled with the names, and that text
    is inside the prompt the agent actually received.
"""
import os

from common import CONDS, PROMPTS, load_records

recs = load_records()
games = sorted({g for _, g in recs})
problems = 0


def round1(rec):
    r = rec["rounds"][0]
    states = {s["player_name"]: (s["initial_hand"], s["bullet_position"]) for s in r["player_initial_states"]}
    return {"seat_order": rec["scripted_offer"]["seat_order"], "target_card": r["target_card"],
            "starting_player": r["starting_player"], "initial_states": states}


print("A1  round 1 identical across conditions")
for g in games:
    ref = round1(recs[("C4", g)])
    bad = [c for c in CONDS if round1(recs[(c, g)]) != ref]
    print(f"  g{g}: {'OK' if not bad else 'MISMATCH in ' + ', '.join(bad)}")
    problems += len(bad)

print("\nA2  offer delivered in round 2")
for (c, g), rec in sorted(recs.items()):
    so = rec["scripted_offer"]
    if c == "C4":
        ok = not so["offers"]          # C4 sends nothing
    else:
        ok = so["offer_round_actual"] == 2 and len(so["offers"]) > 0 and all(o["round"] == 2 for o in so["offers"])
    if not ok:
        print(f"  {c} g{g}: PROBLEM (offer_round_actual={so['offer_round_actual']}, offers={len(so['offers'])})")
        problems += 1
print("  done (only problems are listed)")

print("\nA3  offer text = verbatim template, and present in the prompt")
templates = {}
for c, name in [("C1", "offer_direct"), ("C2", "offer_hint"), ("C3", "offer_benign")]:
    with open(os.path.join(PROMPTS, f"prompts__scripted_offer__{name}.txt"), encoding="utf-8") as f:
        templates[c] = f.read().strip()
checked = 0
for (c, g), rec in sorted(recs.items()):
    if c not in templates:
        continue
    so = rec["scripted_offer"]
    for o in so["offers"]:
        expected = templates[c].format(proposer_name=so["proposer"], agent_name=o["agent"])
        checked += 1
        if o["offer_text"].strip() != expected:
            print(f"  {c} g{g} {o['agent']}: TEXT DIFFERS FROM TEMPLATE")
            problems += 1
        elif o["offer_text"].strip() not in o["prompt"]:
            print(f"  {c} g{g} {o['agent']}: TEXT NOT FOUND IN PROMPT")
            problems += 1
print(f"  {checked} offers checked")

print(f"\nTOTAL PROBLEMS: {problems}")
