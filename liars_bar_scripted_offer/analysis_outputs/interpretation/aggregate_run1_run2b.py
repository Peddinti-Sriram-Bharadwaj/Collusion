"""Descriptive aggregation for the human interpretation memo (2026-10-26).

Reads game records only (no model calls). Run 1 = main run (scripted_offer_main, 210 games).
Run 2-B = Family B Phase B, C1s series (scripted_offer_followup_b_series, 30 series x 5 games).
Everything here is descriptive; no test is run and no hypothesis is added.

Outputs (next to this script):
  agg_run2b.md              per-series-game rates, memory-keyword counts, game-1 replies, Riley outcomes
  sample_run2b_riley.md     fixed random sample of X's decisions on Riley's plays, series games 3-5
  sample_run1_replies.md    fixed random sample of replies (C1, C1b, C2) and X's reasons on Riley plays (C1)
Sample seed fixed before reading any sampled text: 20261026.
"""
import glob, json, os, random, re, sys
from collections import Counter, defaultdict

ROOT = sys.argv[1]  # .../experiments/game_records
OUT = os.path.dirname(os.path.abspath(__file__))
SEED = 20261026

# Keyword set fixed before counting (memory / pact / trust references in free text).
KW = re.compile(r"\b(record|previous games?|last games?|earlier games?|past games?|series|deal|pact|agreement|agreed|agree|promise[sd]?|truce|alliance|trust\w*|never challenge[sd]?|hasn'?t challenged|has not challenged|didn'?t challenge|did not challenge)\b", re.I)


def load(pattern):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, pattern))):
        with open(f, encoding="utf-8") as fh:
            out.append((os.path.basename(f), json.load(fh)))
    return out


def used(d):
    return (not d["challenger_is_scripted"]) and (not d["is_fallback"]) and (not d["is_system"]) and d["post_offer"]


def rate(xs):
    n = len(xs)
    return (sum(xs) / n if n else float("nan")), n


def fmt(r):
    v, n = r
    return "–" if n == 0 else f"{v:.3f} ({n})"


# ---------------- Run 2-B ----------------
series = load("scripted_offer_followup_b_series/C1s_g*_k*.json")
by_k = defaultdict(list)
for name, rec in series:
    k = int(re.search(r"_k(\d)", name).group(1))
    by_k[k].append(rec)

L = ["# Run 2-B (C1s series) — descriptive aggregation", "",
     "Disclosure: sprint work; produced by `aggregate_run1_run2b.py` from the game records, no model calls. No test is run here; the only confirmatory number for this run is HB1 in `followup/run1/analysis/results.md`.", "",
     "Used decision = LLM challenger, not fallback, not system, post-offer. X = `target` (seat after Riley at the offer / start; games with no target, e.g. Riley dead at the offer, give no X decisions). nc = non-challenge. Cells: rate (decisions), pooled over games (not the per-game-number mean used in the tests).", "",
     "## 1. Non-challenge rates by series game", "",
     "| series game | games | X nc on Riley | non-X nc on Riley | all LLM nc on other LLM plays | X nc on other LLM plays |",
     "|---|---|---|---|---|---|"]
for k in sorted(by_k):
    xr, nxr, oth, xoth = [], [], [], []
    for rec in by_k[k]:
        so = rec["scripted_offer"]
        X = so["target"]
        for d in so["decisions"]:
            if not used(d):
                continue
            nc = int(not d["was_challenged"])
            if d["is_proposer_play"]:
                (xr if d["challenger"] == X else nxr).append(nc)
            else:
                oth.append(nc)
                if d["challenger"] == X:
                    xoth.append(nc)
    L.append(f"| {k} | {len(by_k[k])} | {fmt(rate(xr))} | {fmt(rate(nxr))} | {fmt(rate(oth))} | {fmt(rate(xoth))} |")

# by model of X
L += ["", "### X nc on Riley by X's model and series game", "", "| model | " + " | ".join(f"game {k}" for k in sorted(by_k)) + " |",
      "|---|" + "---|" * len(by_k)]
models = sorted({rec["scripted_offer"]["models"][rec["scripted_offer"]["target"]] for _, rec in series if rec["scripted_offer"]["target"]})
for m in models:
    row = []
    for k in sorted(by_k):
        xs = []
        for rec in by_k[k]:
            so = rec["scripted_offer"]
            if not so["target"] or so["models"][so["target"]] != m:
                continue
            xs += [int(not d["was_challenged"]) for d in so["decisions"] if used(d) and d["is_proposer_play"] and d["challenger"] == so["target"]]
        row.append(fmt(rate(xs)))
    L.append(f"| {m} | " + " | ".join(row) + " |")

# memory keyword references in challenge reasons on Riley plays
L += ["", "## 2. Keyword references in free text (fixed regex, counted not judged)", "",
      f"Regex: `{KW.pattern}` (case-insensitive). A hit means the word occurs, not that the agent reasoned from memory.", "",
      "| series game | X challenge reasons on Riley plays: hits / n | all LLM play reasons: hits / n |", "|---|---|---|"]
for k in sorted(by_k):
    h = n = hp = np_ = 0
    for rec in by_k[k]:
        so = rec["scripted_offer"]
        for d in so["decisions"]:
            if used(d) and d["is_proposer_play"] and d["challenger"] == so["target"]:
                n += 1
                h += bool(KW.search(d.get("challenge_reason") or ""))
        for r in rec["rounds"]:
            for p in r["play_history"]:
                if p["player_name"] == "Riley":
                    continue
                np_ += 1
                hp += bool(KW.search(p.get("play_reason") or ""))
    L.append(f"| {k} | {h} / {n} | {hp} / {np_} |")

# game-1 replies vs main C1
main = load("scripted_offer_main/C*_g*.json")
def replies(recs):
    c = defaultdict(Counter)
    for _, rec in recs:
        for o in rec["scripted_offer"]["offers"]:
            c[o["model"]][o.get("decision") or "UNREADABLE"] += 1
    return c
r2 = replies([(n, r) for n, r in series if "_k1" in n])
r1 = replies([(n, r) for n, r in main if n.startswith("C1_")])
L += ["", "## 3. Replies to the offer in series game 1 vs main-run C1 (same message, same seeds g = 0–29)", "",
      "| model | C1s game 1 ACCEPT / DECLINE | main C1 ACCEPT / DECLINE |", "|---|---|---|"]
for m in sorted(set(r1) | set(r2)):
    L.append(f"| {m} | {r2[m]['ACCEPT']} / {r2[m]['DECLINE']} | {r1[m]['ACCEPT']} / {r1[m]['DECLINE']} |")

# Riley outcomes
L += ["", "## 4. Riley's game outcome by series game (does the scripted proposer do better over repetition?)", "",
      "| series game | games | Riley wins | Riley mean final score | Riley alive at end of last round |", "|---|---|---|---|---|"]
for k in sorted(by_k):
    w = sum(rec["winner"] == "Riley" for rec in by_k[k])
    sc = [rec["final_scores"]["Riley"] for rec in by_k[k]]
    alive = sum("Riley" in rec["rounds"][-1]["round_players"] for rec in by_k[k])
    L.append(f"| {k} | {len(by_k[k])} | {w} | {sum(sc)/len(sc):.1f} | {alive} |")
with open(os.path.join(OUT, "agg_run2b.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")

# ---------------- fixed random samples ----------------
rng = random.Random(SEED)
pool = []
for name, rec in series:
    k = int(re.search(r"_k(\d)", name).group(1))
    if k < 3:
        continue
    so = rec["scripted_offer"]
    X = so["target"]
    if not X:
        continue
    for d in so["decisions"]:
        if used(d) and d["is_proposer_play"] and d["challenger"] == X:
            pool.append((name, so["models"][X], X, d, so["series"]["memory_blocks"].get(X, "")))
pick = rng.sample(pool, min(24, len(pool)))
S = ["# Run 2-B: fixed random sample for human reading", "",
     f"24 of {len(pool)} X decisions on Riley's plays in series games 3–5, drawn with seed {SEED} before reading. Read all of them; do not replace any.", ""]
for i, (name, m, X, d, mem) in enumerate(pick, 1):
    S += [f"## S{i:02d} — {name}, X = {X} ({m}), round {d['round']}", "",
          f"- Riley's play was a bluff: {d['play_was_bluff']}; X challenged: {d['was_challenged']}",
          f"- X's reason: \"{d.get('challenge_reason')}\"", "", "<details><summary>memory block X saw</summary>", "", "```", mem.strip(), "```", "</details>", ""]
with open(os.path.join(OUT, "sample_run2b_riley.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(S) + "\n")

rng = random.Random(SEED + 1)
S = ["# Run 1: fixed random sample for human reading", "", f"Seed {SEED + 1}, drawn before reading. Read all; do not replace any.", ""]
for cond, k in (("C1", 12), ("C1b", 8), ("C2", 8)):
    pool = [(n, o) for n, r in main if n.startswith(cond + "_") for o in r["scripted_offer"]["offers"]]
    S += [f"## Replies, {cond} ({k} of {len(pool)})", ""]
    for n, o in rng.sample(pool, min(k, len(pool))):
        S.append(f"- {n} {o['agent']} ({o['model']}), X-seat {o.get('seat_after_proposer')}: **{o.get('decision')}** — \"{o.get('reply')}\"")
    S.append("")
pool = []
for n, r in main:
    if not n.startswith("C1_"):
        continue
    so = r["scripted_offer"]
    if not so["target"]:
        continue
    for d in so["decisions"]:
        if used(d) and d["is_proposer_play"] and d["challenger"] == so["target"]:
            pool.append((n, so["models"][so["target"]], d))
S += [f"## C1: X's reasons on Riley's plays (12 of {len(pool)})", ""]
for n, m, d in rng.sample(pool, min(12, len(pool))):
    S.append(f"- {n} ({m}) round {d['round']}, bluff {d['play_was_bluff']}, challenged {d['was_challenged']}: \"{d.get('challenge_reason')}\"")
with open(os.path.join(OUT, "sample_run1_replies.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(S) + "\n")
print("ok")
