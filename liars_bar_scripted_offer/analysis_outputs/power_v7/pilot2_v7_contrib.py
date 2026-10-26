"""Read-only: per-game v7 quantities from pilot 2 records (selectivity, X reply, contributing game numbers)."""
import json, sys, glob, os
from collections import defaultdict

rec_dir = sys.argv[1]
games = {}
for p in sorted(glob.glob(os.path.join(rec_dir, "C?_g??.json"))):
    r = json.load(open(p, encoding="utf-8"))
    so = r["scripted_offer"]
    games[(so["condition"], so["game_number"])] = (r, so)

def used(d):
    return (not d["is_system"]) and (not d["challenger_is_scripted"]) and d["post_offer"] and (not d["is_fallback"])

def selectivity(so):
    ds = [d for d in so["decisions"] if used(d)]
    facing = {d["challenger"] for d in ds if d["is_proposer_play"]}
    if not facing:
        return None
    p = [d for d in ds if d["is_proposer_play"] and d["challenger"] in facing]
    o = [d for d in ds if (not d["is_proposer_play"]) and d["challenger"] in facing]
    if not p or not o:
        return None
    ncp = sum(not d["was_challenged"] for d in p) / len(p)
    nco = sum(not d["was_challenged"] for d in o) / len(o)
    return {"sel": ncp - nco, "ncp": ncp, "np": len(p), "nco": nco, "no": len(o), "agents": sorted(facing)}

def others_challenge_rate(so, agents):
    ds = [d for d in so["decisions"] if used(d) and d["challenger"] in agents and not d["is_proposer_play"]]
    return (sum(bool(d["was_challenged"]) for d in ds) / len(ds), len(ds)) if ds else (None, 0)

conds = ["C0", "C1", "C2", "C3", "C4"]
gs = sorted({g for _, g in games})
print("game | " + " | ".join(conds) + "   (selectivity: ncp-nco [np,no])")
sel = defaultdict(dict)
for g in gs:
    cells = []
    for c in conds:
        if (c, g) not in games:
            cells.append("missing"); continue
        s = selectivity(games[(c, g)][1])
        sel[c][g] = s
        cells.append("none" if s is None else f"{s['sel']:+.2f} ({s['ncp']:.2f}-{s['nco']:.2f}) [{s['np']},{s['no']}] {','.join(a[0] for a in s['agents'])}")
    print(f"g{g} | " + " | ".join(cells))

print("\ncontributing game numbers (selectivity defined):")
for c in conds:
    print(c, sum(1 for g in gs if sel[c].get(g)), "/", len(gs))
def pair(a, b):
    return [sel[a][g]["sel"] - sel[b][g]["sel"] for g in gs if sel[a].get(g) and sel[b].get(g)]
for a, b in (("C1", "C2"), ("C1", "C4"), ("C2", "C4"), ("C3", "C4"), ("C0", "C4"), ("C1", "C3")):
    v = pair(a, b)
    print(f"sel {a}-{b}: n={len(v)} vals={[round(x,2) for x in v]} mean={sum(v)/len(v) if v else None}")

# X (seat after proposer) reply availability and whether X faced proposer plays
print("\nX reply + X faces proposer plays, per offered condition:")
for c in ["C1", "C2", "C3"]:
    n_reply = n_face = 0
    for g in gs:
        r, so = games[(c, g)]
        x = so.get("target")
        off = [o for o in so["offers"] if o["agent"] == x]
        if off and off[0]["decision"] in ("ACCEPT", "DECLINE"):
            n_reply += 1
        s = sel[c].get(g)
        if s and x in s["agents"]:
            n_face += 1
    print(c, "X readable reply:", n_reply, "/", len(gs), " X in proposer-facing set:", n_face, "/", len(gs))

# X's own first play challenged by an LLM post-offer (C1b breach analogue), in all conditions
print("\nBreach analogue: post-offer challenges of X's plays by LLM, per game (first round, challenger), and X dead-before-offer:")
for c in conds:
    for g in gs:
        r, so = games[(c, g)]
        x = so.get("target")
        ev = [(d["round"], d["challenger"], d.get("challenger_can_challenge_proposer")) for d in so["decisions"]
              if used(d) and d["current_player"] == x and d["was_challenged"]]
        sysv = [d["round"] for d in so["decisions"] if d["is_system"] and d["current_player"] == x and d["post_offer"]]
        print(f"{c} g{g}: X={x} first_llm_breach={ev[0] if ev else None} n_breaches={len(ev)} system_on_X_rounds={sysv} rounds={len(r['rounds'])} winner={r.get('winner')}")

# other-LLM challenge rates for HM (recipients vs C4 same agents)
print("\nHM analogue: recipients' challenge rate on other-LLM plays minus same agents in C4:")
for c in ["C1", "C2", "C3"]:
    vals = []
    for g in gs:
        so = games[(c, g)][1]; so4 = games[("C4", g)][1]
        rec = {o["agent"] for o in so["offers"]}
        r1, n1 = others_challenge_rate(so, rec); r0, n0 = others_challenge_rate(so4, rec)
        if n1 and n0:
            vals.append(r1 - r0)
    print(c, "n=", len(vals), [round(v, 2) for v in vals], "mean", round(sum(vals)/len(vals), 3) if vals else None)
