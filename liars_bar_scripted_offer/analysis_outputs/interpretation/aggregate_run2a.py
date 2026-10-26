"""Descriptive aggregation of Run 2-A (Family B Phase A: C1c, C1ci, C1d) for the human interpretation memo.

Reads game records and followup/judgements_B.csv only (no model calls). Recomputes the pre-registered
contrasts independently of analyze_followup.py as a cross-check, then adds descriptive tables and a
fixed random sample for human reading. No test is run here; the confirmatory numbers are in
followup/analysis_judged/results.md.

Usage: python -I aggregate_run2a.py <game_records root>
Outputs (next to this script): agg_run2a.md, sample_run2a.md
Sample seed fixed before reading any sampled text: 20261026.
"""
import csv, glob, json, os, random, re, sys
from collections import Counter, defaultdict

ROOT = sys.argv[1]
OUT = os.path.dirname(os.path.abspath(__file__))
JUDGE = os.path.join(OUT, "..", "followup", "judgements_B.csv")
SEED = 20261026
CONDS = ["C1c", "C1ci", "C1d"]
MODELS = ["llama-3.1-8b", "llama-3.2-3b", "qwen2.5-7b"]

# Regexes fixed before counting.
KW_AUTH = re.compile(r"\b(not (really )?(one of the|a) players?|part of the (game'?s )?prompt|the prompt|system|instruction|host|moderator|game master|not a (real )?player)\b", re.I)
KW_RECORD = re.compile(r"\b(record|last three tables|previous (tables|games)|\d+ of \d+|every time|worked out|before|past|history)\b", re.I)
KW_DEAL = re.compile(r"\b(deal|pact|agreement|agreed|agree|promise[sd]?|truce|alliance|trust\w*)\b", re.I)


def load(pattern):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, pattern))):
        with open(f, encoding="utf-8") as fh:
            out.append((os.path.basename(f), json.load(fh)))
    return out


def used(d):
    return (not d["challenger_is_scripted"]) and (not d["is_fallback"]) and (not d["is_system"]) and d["post_offer"]


def rate(k, n):
    return "–" if n == 0 else f"{k / n:.3f} ({k}/{n})"


def mean_ci(xs):
    import math
    n = len(xs)
    if n == 0:
        return "–"
    m = sum(xs) / n
    if n < 2:
        return f"{m:+.3f} (n 1)"
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    # t critical approx (df>=4): use 2.0-2.78 table-free approximation via scipy-free lookup
    t = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 7: 2.45, 8: 2.36, 9: 2.31, 10: 2.26, 11: 2.23, 12: 2.20, 13: 2.18, 14: 2.16, 15: 2.14, 16: 2.13, 17: 2.12, 18: 2.11, 19: 2.10, 20: 2.09, 21: 2.08, 22: 2.07, 23: 2.07, 24: 2.06, 25: 2.06}.get(n, 2.05)
    h = t * sd / math.sqrt(n)
    return f"{m:+.3f} [{m - h:+.3f}, {m + h:+.3f}] (g {n})"


def x_riley(rec, agent=None):
    """X's used decisions on Riley's plays: (k_nc, n). `agent` overrides X (the control game is read for the NEW game's X, as analyze.Data.paired does)."""
    so = rec["scripted_offer"]
    x = agent or so.get("target")
    ds = [d for d in so["decisions"] if used(d) and d["is_proposer_play"] and d["challenger"] == x]
    return sum(1 for d in ds if not d["was_challenged"]), len(ds), ds


def x_others(rec, agent=None):
    so = rec["scripted_offer"]
    x = agent or so.get("target")
    ds = [d for d in so["decisions"] if used(d) and (not d["is_proposer_play"]) and d["challenger"] == x]
    return sum(1 for d in ds if not d["was_challenged"]), len(ds)


def riley_dead_at_offer(rec):
    so = rec["scripted_offer"]
    return so.get("target") is None or so.get("offer_round_actual") in (None, 0) and so.get("series") is None


main = {}
for name, rec in load("scripted_offer_main/C*_g*.json"):
    so = rec["scripted_offer"]
    main[(so["condition"], so["game_number"])] = rec
fb = {}
for name, rec in load("scripted_offer_followup_b/C1*_g*.json"):
    so = rec["scripted_offer"]
    fb[(so["condition"], so["game_number"])] = rec

judg = defaultdict(dict)
with open(JUDGE, encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        judg[r["condition"]][(int(r["game_number"]), r["agent"])] = r["category"]

L = ["# Run 2-A (C1c, C1ci, C1d) — descriptive aggregation and cross-check", "",
     "Disclosure: sprint work; produced by `aggregate_run2a.py` from the game records and `followup/judgements_B.csv`, no model calls. No test is run here; the confirmatory numbers are HB2–HB4 in `followup/analysis_judged/results.md`.", "",
     "Used decision = LLM challenger, not fallback, not system, post-offer. X = `target` = `x_recipient` (the only recipient in these conditions). nc = non-challenge. Paired contrasts read the control game for the **new game's X agent** (as `analyze.Data.paired` does), so a g where that agent has no Riley decision in the control game drops out even if the control game's own X does.", ""]

# ---- 1. Run history
L += ["## 1. Run history (from run_log.jsonl)", ""]
rl = [json.loads(l) for l in open(os.path.join(ROOT, "scripted_offer_followup_b", "run_log.jsonl"), encoding="utf-8")]
c = Counter((r["condition"], r["status"]) for r in rl)
L.append("| condition | ok | interrupted attempts (replayed from scratch) |")
L.append("|---|---|---|")
for cond in CONDS:
    L.append(f"| {cond} | {c[(cond, 'ok')]} | {c[(cond, 'error')]} |")
L.append("")
L.append("Interrupted attempts: " + ", ".join(r["attempt_id"] for r in rl if r["status"] != "ok") + ". Each was replayed as a new attempt (`_a2`); no partial record was kept. API errors/retries in ok games: " + str(sum(r["api_errors"] + r["api_retries"] for r in rl if r["status"] == "ok")) + ".")
L.append("")

# ---- 2. Pooled rates and paired contrasts (cross-check)
L += ["## 2. X's non-challenge on Riley, pooled over decisions and paired by g (cross-check of analyze_followup.py)", "",
      "| condition | games | games with X decisions on Riley | X nc on Riley (pooled) | X nc on others (pooled) | ΔR_X vs C1(g), mean [95% t-CI] (g) | ΔO_X (g) |",
      "|---|---|---|---|---|---|---|"]
dR_by = {}
for cond in CONDS:
    kk = nn = ko = no = 0
    dR, dO = [], []
    gx = 0
    for g in range(30):
        rec = fb.get((cond, g))
        if rec is None:
            continue
        k, n, _ = x_riley(rec)
        kk += k; nn += n
        o1, o2 = x_others(rec)
        ko += o1; no += o2
        if n:
            gx += 1
        c1 = main.get(("C1", g))
        xa = rec["scripted_offer"].get("target")
        k0, n0, _ = x_riley(c1, xa)
        if n and n0 and xa and c1["scripted_offer"].get("target"):
            dR.append((g, rec["scripted_offer"]["models"][xa], k / n - k0 / n0))
        q1, q2 = x_others(c1, xa)
        if o2 and q2:
            dO.append(o1 / o2 - q1 / q2)
    dR_by[cond] = dR
    L.append(f"| {cond} | {sum(1 for g in range(30) if (cond, g) in fb)} | {gx} | {rate(kk, nn)} | {rate(ko, no)} | {mean_ci([v for _, _, v in dR])} | {mean_ci(dO)} |")
L.append("")
L.append("Reference (same pooling), main run: C1 X nc on Riley = " + rate(*[sum(x) for x in zip(*[x_riley(main[('C1', g)])[:2] for g in range(30)])]) + "; C0 X nc on Riley = " + rate(*[sum(x) for x in zip(*[x_riley(main[('C0', g)])[:2] for g in range(30)])]) + "; C1b X nc on Riley = " + rate(*[sum(x) for x in zip(*[x_riley(main[('C1b', g)])[:2] for g in range(30)])]) + ".")
L.append("")
L.append("The paired means must equal the HB2/HB3/HB4 rows of `analysis_judged/results.md` (+0.122 g 22; −0.012 g 22; +0.291 g 19). The t-CI here is the same formula as the report's.")
L.append("")

# ---- 3. by model
L += ["## 3. ΔR_X by X's model, and the sign pattern (how many g rose / flat / fell)", "",
      "| condition | model | g | mean [95% CI] | rose / flat / fell | X nc on Riley pooled (cond) | pooled (C1 same g) |",
      "|---|---|---|---|---|---|---|"]
for cond in CONDS:
    for m in MODELS:
        vals = [v for _, mm, v in dR_by[cond] if mm == m]
        gs = [g for g, mm, _ in dR_by[cond] if mm == m]
        up = sum(1 for v in vals if v > 1e-9); fl = sum(1 for v in vals if abs(v) <= 1e-9); dn = len(vals) - up - fl
        k1 = sum(x_riley(fb[(cond, g)])[0] for g in gs); n1 = sum(x_riley(fb[(cond, g)])[1] for g in gs)
        k0 = sum(x_riley(main[("C1", g)], fb[(cond, g)]["scripted_offer"]["target"])[0] for g in gs); n0 = sum(x_riley(main[("C1", g)], fb[(cond, g)]["scripted_offer"]["target"])[1] for g in gs)
        L.append(f"| {cond} | {m} | {len(vals)} | {mean_ci(vals)} | {up} / {fl} / {dn} | {rate(k1, n1)} | {rate(k0, n0)} |")
L.append("")

# ---- 4. replies
L += ["## 4. X's reply to the message: own label and judged category, by model", "",
      "| condition | model | n | ACCEPT | judged: committed / rejection / suspicion-evasive / other |",
      "|---|---|---|---|---|"]
reply_rows = defaultdict(list)
for cond in CONDS:
    for g in range(30):
        rec = fb.get((cond, g))
        if rec is None:
            continue
        for o in rec["scripted_offer"]["offers"]:
            reply_rows[cond].append((g, o["agent"], o["model"], o["decision"], o["reply"], judg[cond].get((g, o["agent"]), "not judged")))
    for m in MODELS + ["all"]:
        rr = [r for r in reply_rows[cond] if m == "all" or r[2] == m]
        if not rr:
            continue
        cc = Counter(r[5] for r in rr)
        L.append(f"| {cond} | {m} | {len(rr)} | {sum(1 for r in rr if r[3] == 'ACCEPT')} | {cc['committed']} / {cc['rejection']} / {cc['suspicion-evasive']} / {cc['other']} |")
L.append("")
L.append("Reference, main run C1 (all recipients): ACCEPT 10/89, committed 6/89; C1b (X only): see `main/analysis/summary.md`. Run 2-B game 1 (C1 message): committed 8/89.")
L.append("")

# ---- 5. keyword flags in replies and reasons
L += ["## 5. Keyword flags (fixed regex, counted not judged; a hit = the words occur)", "",
      "Regex A (authority / non-player): `" + KW_AUTH.pattern + "`", "",
      "Regex R (record / history): `" + KW_RECORD.pattern + "`", "",
      "Regex D (deal / trust): `" + KW_DEAL.pattern + "`", "",
      "| condition | X replies: A / R / D hits (n) | X reasons on Riley plays (post-offer): A / R / D hits (n) |",
      "|---|---|---|"]
for cond in CONDS:
    rr = reply_rows[cond]
    a = sum(1 for r in rr if KW_AUTH.search(r[4] or "")); rc = sum(1 for r in rr if KW_RECORD.search(r[4] or "")); dd = sum(1 for r in rr if KW_DEAL.search(r[4] or ""))
    reasons = []
    for g in range(30):
        rec = fb.get((cond, g))
        if rec:
            reasons += [d["challenge_reason"] or "" for d in x_riley(rec)[2]]
    a2 = sum(1 for t in reasons if KW_AUTH.search(t)); r2 = sum(1 for t in reasons if KW_RECORD.search(t)); d2 = sum(1 for t in reasons if KW_DEAL.search(t))
    L.append(f"| {cond} | {a} / {rc} / {dd} ({len(rr)}) | {a2} / {r2} / {d2} ({len(reasons)}) |")
L.append("")

# ---- 6. C1d vs C0 and HB3-HB2 cross-check
L += ["## 6. Cross-condition descriptives (cross-check)", ""]
v = []
for g in range(30):
    a, b = fb.get(("C1d", g)), main.get(("C0", g))
    if a and b:
        k, n, _ = x_riley(a); k0, n0, _ = x_riley(b, a["scripted_offer"].get("target"))
        if n and n0 and a["scripted_offer"].get("target") and b["scripted_offer"].get("target"):
            v.append(k / n - k0 / n0)
L.append("C1d − C0, X nc on Riley: " + mean_ci(v) + " (report: −0.163 [−0.343, +0.017], g 22).")
v = []
for g in range(30):
    a, b = fb.get(("C1ci", g)), fb.get(("C1c", g))
    if a and b:
        k, n, _ = x_riley(a); k0, n0, _ = x_riley(b, a["scripted_offer"].get("target"))
        if n and n0 and b["scripted_offer"].get("target"):
            v.append(k / n - k0 / n0)
L.append("")
L.append("C1ci − C1c, X nc on Riley: " + mean_ci(v) + " (report: −0.168 [−0.322, −0.014], g 20).")
L.append("")
# who contributes dO_X in C1d
L.append("ΔO_X contributors (game numbers where X judged a non-Riley player in both the new game and C1(g)):")
for cond in CONDS:
    gs = []
    for g in range(30):
        a, b = fb.get((cond, g)), main.get(("C1", g))
        if a and b and x_others(a)[1] and x_others(b, a["scripted_offer"].get("target"))[1]:
            gs.append(f"g{g} {a['scripted_offer']['models'][a['scripted_offer']['target']]}")
    L.append(f"- {cond}: {', '.join(gs) or 'none'}")
L.append("")

# ---- 7. Riley bluff tracking
L += ["## 7. Does X's non-challenge of Riley track Riley's actual bluffing? (pooled)", "",
      "| condition | nc when Riley bluffed | nc when Riley honest |", "|---|---|---|"]
for cond in CONDS:
    kb = nb = kh = nh = 0
    for g in range(30):
        rec = fb.get((cond, g))
        if not rec:
            continue
        for d in x_riley(rec)[2]:
            if d["play_was_bluff"]:
                nb += 1; kb += (not d["was_challenged"])
            else:
                nh += 1; kh += (not d["was_challenged"])
    L.append(f"| {cond} | {rate(kb, nb)} | {rate(kh, nh)} |")
L.append("")

with open(os.path.join(OUT, "agg_run2a.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")

# ---- sample for human reading
rng = random.Random(SEED)
S = ["# Run 2-A: fixed random sample for human reading", "",
     f"Drawn with seed {SEED} before reading. Read all of them; do not replace any. Per condition: 8 X replies (all 30 for C1d are listed in full because the condition is the one that rejected) and 8 post-offer X decisions on Riley's plays.", ""]
for cond in CONDS:
    S.append(f"## {cond} — X replies")
    S.append("")
    rr = reply_rows[cond]
    pick = rr if cond == "C1d" else rng.sample(rr, 8)
    for g, agent, m, dec, reply, cat in sorted(pick):
        S.append(f"- g{g:02d} {agent} ({m}) · label {dec} · judge **{cat}**: \"{(reply or '').strip()}\"")
    S.append("")
    S.append(f"## {cond} — X decisions on Riley's plays (post-offer)")
    S.append("")
    pool = []
    for g in range(30):
        rec = fb.get((cond, g))
        if rec:
            for d in x_riley(rec)[2]:
                pool.append((g, rec["scripted_offer"]["target"], rec["scripted_offer"]["models"][rec["scripted_offer"]["target"]], d))
    for g, agent, m, d in sorted(rng.sample(pool, 8), key=lambda t: (t[0], t[3]["round"])):
        S.append(f"- g{g:02d} r{d['round']} {agent} ({m}) · Riley bluffed: {d['play_was_bluff']} · X challenged: {d['was_challenged']} · reason: \"{(d['challenge_reason'] or '').strip()}\"")
    S.append("")
with open(os.path.join(OUT, "sample_run2a.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(S) + "\n")
print("wrote agg_run2a.md, sample_run2a.md")
