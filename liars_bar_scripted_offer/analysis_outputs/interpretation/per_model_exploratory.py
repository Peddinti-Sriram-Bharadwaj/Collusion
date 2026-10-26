"""Per-model split of the pre-registered contrasts. EXPLORATORY (not pre-registered; written 2026-10-26
after all results were seen, at the experimenter's request). Reuses analyze.Data / paired_test unchanged.

For every game number g the seat order is the same in every condition, so the agent in a given seat has
the same model across conditions; pairing by g within a model is therefore well defined.

Reported per model: mean of the per-game-number values, 95% t-interval, n, and the two-sided sign-flip p
(unadjusted; three models x many contrasts, so a single p < .05 is expected by chance and is not read).
Output: per_model_exploratory.md, per_model_values.csv.
"""
import csv, sys
from pathlib import Path

GAME_REPO = Path(sys.argv[1])          # .../Collusion_Liars_Bar
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(GAME_REPO / "analysis" / "scripted_offer"))
import analyze as A  # noqa: E402

records = GAME_REPO / "experiments" / "game_records" / "scripted_offer_main"
games = A.load_games(records)
judg = A.load_judgements(str(OUT.parent / "main" / "judgements.csv"))
data = A.Data(games, judg)
MODELS = ["llama-3.1-8b", "llama-3.2-3b", "qwen2.5-7b"]


def agents_of(cond, g, model):
    rec = data.games.get((cond, g))
    if not rec:
        return set()
    return {a for a, m in rec["scripted_offer"]["models"].items() if m == model}


def sel_for(cond, g, agents):
    """Selectivity restricted to `agents` that faced the proposer in that game."""
    if (cond, g) not in data.games:
        return None
    rows = data.rows_by[(cond, g)]
    facing = {r["challenger"] for r in rows if r["used"] and r["challenged_is_proposer"]} & agents
    if not facing:
        return None
    kp, np_ = A.rate(rows, facing, "proposer")
    ko, no = A.rate(rows, facing, "others_nc")
    if not np_ or not no:
        return None
    return kp / np_ - ko / no


values = []   # (contrast, model, g, value)


def add(name, m, g, v):
    if v is not None:
        values.append((name, m, g, v))


for m in MODELS:
    for g in data.numbers:
        ag = {c: agents_of(c, g, m) for c in ["C0", "C1", "C1b", "C2", "C3", "C4", "C5"]}
        # Gate: C0 ally (if of model m) nc on proposer − C4 same agent
        ally = data.offered("C0", g) & ag["C0"]
        if ally:
            pr = data.paired("C0", g, ally, "proposer")
            add("Gate C0-C4 proposer nc", m, g, pr and pr["diff"])
        # HA1a / HA1b: category shares among model-m recipients, C1 − C2
        for cat, nm in (("committed", "HA1a committed C1-C2"), ("suspicion-evasive", "HA1b susp-evasive C1-C2")):
            a, b = data.category_share("C1", g, cat, ag["C1"]), data.category_share("C2", g, cat, ag["C2"])
            if a is not None and b is not None:
                add(nm, m, g, a - b)
        # HA1c: X committed C1b − C1, X of model m
        xb, x1 = data.target("C1b", g), data.target("C1", g)
        if xb in ag["C1b"] and x1 in ag["C1"]:
            cb, c1 = data.category("C1b", g, xb), data.category("C1", g, x1)
            if cb is not None and c1 is not None:
                add("HA1c X committed C1b-C1", m, g, float(cb == "committed") - float(c1 == "committed"))
        # HA2a/b/c: selectivity of model-m facing agents
        s = {c: sel_for(c, g, ag[c]) for c in ["C1", "C1b", "C2", "C5"]}
        if s["C5"] is not None and (s["C1"] is not None or s["C2"] is not None):
            pact = [v for v in (s["C1"], s["C2"]) if v is not None]
            add("HA2a selectivity mean(C1,C2)-C5", m, g, sum(pact) / len(pact) - s["C5"])
        if s["C1"] is not None and s["C2"] is not None:
            add("HA2b selectivity C1-C2", m, g, s["C1"] - s["C2"])
        if s["C1b"] is not None and s["C1"] is not None and xb and x1:
            add("HA2c selectivity C1b-C1", m, g, s["C1b"] - s["C1"])
        # HM: model-m recipients' challenge rate on others, each message cond − C4; pooled mean per g
        hm = []
        for c in ["C1", "C2", "C3", "C5"]:
            rec_ag = data.offered(c, g) & ag[c]
            pr = data.paired(c, g, rec_ag, "others") if rec_ag else None
            if pr:
                hm.append(pr["diff"])
                add(f"HM {c}-C4 others challenge", m, g, pr["diff"])
        if hm:
            add("HM pooled msg-C4 others challenge", m, g, sum(hm) / len(hm))
        # Susceptibility to the 'spare me' message (not a PREREG hypothesis): X of model m, C1 − C4,
        # nc on proposer plays and nc on others' plays
        if x1 in ag["C1"]:
            pr = data.paired("C1", g, {x1}, "proposer")
            add("X nc on Riley C1-C4", m, g, pr and pr["diff"])
            pr = data.paired("C1", g, {x1}, "others_nc")
            add("X nc on others C1-C4", m, g, pr and pr["diff"])

# ---- render ----
names = []
for n, _, _, _ in values:
    if n not in names:
        names.append(n)
L = ["# Per-model split of the main-run contrasts (EXPLORATORY, not pre-registered)", "",
     "Disclosure: sprint work; computed 2026-10-26 after every main-run result had been seen, at the experimenter's request, with `per_model_exploratory.py` (reuses `analyze.Data`, `paired_test`). "
     "Not part of Family A; no Holm correction; three models x many contrasts, so an isolated p < .05 is expected by chance and is not read as a finding. "
     "Unit: game number g; the agent of a given seat has the same model in every condition of the same g, so pairing within a model is well defined. "
     "n per model is about a third of the pre-registered n, so the intervals are wide.", "",
     "| contrast | model | n (g) | mean | 95% CI | two-sided p (unadj.) |", "|---|---|---|---|---|---|"]
for n in names:
    for m in MODELS:
        vs = [v for nn, mm, _, v in values if nn == n and mm == m]
        if len(vs) < 2:
            L.append(f"| {n} | {m} | {len(vs)} | – | – | – |")
            continue
        t = A.paired_test(vs)
        ci = t.get("ci")
        L.append(f"| {n} | {m} | {t['n']} | {t['mean']:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | {t['p']:.3f} |"
                 if ci else f"| {n} | {m} | {t['n']} | {t['mean']:+.3f} | – | {t['p']:.3f} |")
    L.append("| | | | | | |")
L += ["", "Pre-registered (all models pooled) reference values: Gate +0.569; HA1a −0.089; HA1b +0.400; HA1c +0.200; HA2a −0.197; HA2b −0.063; HA2c +0.326; HM −0.213 (`../main/analysis/summary.md`).",
      "", "HB1 by model (from the pre-registered Family B analysis, descriptive there too): llama-3.1-8b +0.225 [+0.029, +0.422] (g 8); llama-3.2-3b +0.047 [−0.256, +0.351] (g 7); qwen2.5-7b −0.052 [−0.139, +0.036] (g 9)."]
(OUT / "per_model_exploratory.md").write_text("\n".join(L) + "\n", encoding="utf-8")
with open(OUT / "per_model_values.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["contrast", "model", "game_number", "value"])
    w.writerows(values)
print("ok", len(values))
