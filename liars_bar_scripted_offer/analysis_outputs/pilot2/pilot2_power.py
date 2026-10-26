"""Sample-size pilot (pilot2): opportunity counts and simulated power for the gate, H1-H4.

    ../.venv/Scripts/python.exe <this file> --records <records dir> --out <dir> [--sims 1000]

Part 1 (counts) uses analyze.py's own Data / compute, so every count is exactly what the
pre-registered analysis would use.

Part 2 (power) is a simulation, not a test of the pilot data. Each simulated main run of N game
numbers resamples N pilot game numbers with replacement and keeps their OBSERVED opportunity
structure: which comparisons exist and how many used decisions each side has (this is where the
pilot's opportunity rates enter). Outcomes are then drawn under assumed effect sizes:
  * proposer-play non-challenge: baseline = pooled C4 rate in the pilot; game-to-game variation
    on the logit scale (SD tau); treated rate = baseline + effect (probability scale, clipped);
  * acceptance (H1): per-agent rates from the pilot (C1-C3 pooled, shrunk toward the overall mean),
    C1 = that, C3 = +effect, C2 = -effect; readable replies per game as observed.
Tests mirror analyze.py: one value per game number, one-sided within-game-number label
permutation (sign-flip for gate/H1/H2; choice of control among C1-C4 for H3/H4), Monte Carlo.
Power is reported at alpha .05 (unadjusted) and .01 (= .05/5, the first Holm step; a lower
bound on Holm power for a single true effect).
"""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

# This script targets the v5/v6 analysis (gate, H1-H4). analyze.py became v7 on 2026-10-25, so the v6
# code it was run with is kept next to it as analyze_v6_snapshot.py and imported from there.
import importlib.util
_spec = importlib.util.spec_from_file_location("analyze", Path(__file__).with_name("analyze_v6_snapshot.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)


# ----------------------------------------------------------------------
# Part 1: counts
# ----------------------------------------------------------------------
def structure(games):
    """Per game number: what each hypothesis gets (n of used decisions per side, or None)."""
    data = A.Data(games)
    per_g = {}
    for g in data.numbers:
        s = {"g": g}
        # gate
        pr = data.paired("C0", g, data.offered("C0", g), "proposer") if ("C0", g) in data.games else None
        s["gate"] = (pr["n1"], pr["n0"]) if pr else None
        # H1: readable replies per condition, per agent
        s["replies"] = {}
        for c in A.OFFER_CONDS:
            rec = data.games.get((c, g))
            s["replies"][c] = [(o["agent"], o["decision"]) for o in rec["scripted_offer"]["offers"]] if rec else []
        # H2: decliners
        s["h2"] = {}
        for c in A.OFFER_CONDS:
            pr = data.paired(c, g, data.offered(c, g, ("DECLINE",)), "proposer")
            s["h2"][c] = (pr["n1"], pr["n0"]) if pr else None
        # H3 / H4: n of used decisions for alive-at-offer agents in each of C1-C4, and whether paired with C4
        for name, kind in (("h3", "proposer"), ("h4", "h4")):
            if any((c, g) not in data.games for c in A.GROUP):
                s[name] = None
                continue
            ns = {}
            for c in A.GROUP:
                agents = A.alive_at_offer(data.games[(c, g)]) or set()
                ctrl_agents = A.alive_at_offer(data.games[("C4", g)]) or set()
                same = agents & ctrl_agents
                if kind == "h4" and not data.h4_logged(c, g):
                    ns[c] = 0
                else:
                    ns[c] = A.rate(data.rows_by[(c, g)], same, kind)[1]
            paired = {c: data.paired(c, g, A.alive_at_offer(data.games[(c, g)]) or set(), kind) is not None
                      for c in A.OFFER_CONDS}
            s[name] = {"n": ns, "paired": paired}
        per_g[g] = s
    return data, per_g


def counts_table(data, per_g, res):
    lines = []
    G = len(data.numbers)
    lines.append(f"Game numbers: {G} ({data.numbers}); games: {res['games_by_cond']}\n")
    lines.append("| hypothesis | condition | games with >=1 valid opportunity | used decisions (treated side) | "
                 "matched comparisons (game numbers) |")
    lines.append("|---|---|---|---|---|")
    rows = data.rows
    used = [r for r in rows if r["used"]]

    def opp(c, pred):
        rs = [r for r in used if r["condition"] == c and pred(r)]
        return len({r["game_number"] for r in rs}), len(rs)

    # gate
    gg, gn = opp("C0", lambda r: r["challenged_is_proposer"] and r["acceptance_status"] == "ACCEPT")
    lines.append(f"| Gate C0>C4 | C0 ally | {gg}/{G} | {gn} | {res['tests_gate_n']} |")
    # H1
    for c in A.OFFER_CONDS:
        n_read = sum(1 for g in data.numbers for a, d in per_g[g]["replies"][c] if d in ("ACCEPT", "DECLINE"))
        n_unr = sum(1 for g in data.numbers for a, d in per_g[g]["replies"][c] if d == "UNREADABLE")
        g_read = sum(1 for g in data.numbers if any(d in ("ACCEPT", "DECLINE") for a, d in per_g[g]["replies"][c]))
        lines.append(f"| H1 replies | {c} | {g_read}/{G} | {n_read} readable, {n_unr} unreadable | – |")
    lines.append(f"| H1a C3>C1 | – | – | – | {res['tests']['H1a C3>C1']['n']} |")
    lines.append(f"| H1b C1>C2 | – | – | – | {res['tests']['H1b C1>C2']['n']} |")
    # H2
    for c in A.OFFER_CONDS:
        dec_g = sum(1 for g in data.numbers if data.offered(c, g, ("DECLINE",)))
        gg, gn = opp(c, lambda r: r["challenged_is_proposer"] and r["acceptance_status"] == "DECLINE")
        paired = sum(1 for g in data.numbers if per_g[g]["h2"][c])
        lines.append(f"| H2 decliners | {c} | {gg}/{G} (games with any decliner: {dec_g}) | {gn} | "
                     f"{paired} paired with C4 |")
    lines.append(f"| H2a C2>C1 | – | – | – | {res['tests']['H2a C2>C1']['n']} |")
    lines.append(f"| H2b C2>C3 | – | – | – | {res['tests']['H2b C2>C3']['n']} |")
    # H3
    for c in A.GROUP:
        gg, gn = opp(c, lambda r: r["challenged_is_proposer"])
        paired = sum(1 for g in data.numbers if per_g[g]["h3"] and c != "C4" and per_g[g]["h3"]["paired"][c])
        lines.append(f"| H3 | {c} | {gg}/{G} | {gn} | {paired if c != 'C4' else '–'} paired with C4 |")
    lines.append(f"| H3 test | – | – | – | {res['tests']['H3']['n']} |")
    for c in A.GROUP:
        gg, gn = opp(c, lambda r: (not r["challenged_is_proposer"]) and r["challenger_can_challenge_proposer"] is False)
        paired = sum(1 for g in data.numbers if per_g[g]["h4"] and c != "C4" and per_g[g]["h4"]["paired"][c])
        lines.append(f"| H4 (secondary) | {c} | {gg}/{G} | {gn} | {paired if c != 'C4' else '–'} paired with C4 |")
    lines.append(f"| H4 test | – | – | – | {res['tests']['H4']['n']} |")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Part 2: power simulation
# ----------------------------------------------------------------------
def logit(p):
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def expit(x):
    return 1 / (1 + np.exp(-x))


def signflip_p(vals, rng, B):
    vals = np.asarray(vals, float)
    n = len(vals)
    if n < 2:
        return None
    obs = vals.mean()
    if 2 ** n <= B:
        signs = np.array(np.meshgrid(*[[1, -1]] * n)).reshape(n, -1).T
        return float(np.mean((signs * vals).mean(1) >= obs - 1e-12))
    signs = rng.choice([1, -1], size=(B, n))
    return float((np.sum((signs * vals).mean(1) >= obs - 1e-12) + 1) / (B + 1))


def h3_p(table, rng, B):
    """table: array (n_g, 4) of values (np.nan = no value); column 3 = observed (C4 control)."""
    t = np.asarray(table, float)
    t = t[~np.isnan(t[:, 3])]
    n = len(t)
    if n < 2:
        return None
    obs = t[:, 3].mean()
    idx = rng.integers(0, 4, size=(B, n))
    vals = t[np.arange(n)[None, :], idx]
    stat = np.nanmean(vals, axis=1)
    ok = ~np.isnan(stat)
    return float((np.sum(stat[ok] >= obs - 1e-12) + 1) / (ok.sum() + 1))


def simulate(per_g, base_nc, agent_acc, N, effects, tau, rng, B):
    """One simulated main run of N game numbers. Returns p-values per test."""
    gs = [per_g[k] for k in rng.choice(sorted(per_g), size=N)]
    out = {}
    clip = lambda p: float(np.clip(p, 0.001, 0.999))

    def draw_rate(n, p_game):
        return rng.binomial(n, p_game) / n

    # per game number baseline non-challenge on logit scale
    bases = [expit(logit(base_nc) + rng.normal(0, tau)) for _ in gs]

    # gate
    vals = []
    for s, b in zip(gs, bases):
        if s["gate"]:
            n1, n0 = s["gate"]
            vals.append(draw_rate(n1, clip(b + effects["gate"])) - draw_rate(n0, b))
    out["gate"] = signflip_p(vals, rng, B)

    # H1 (agents' acceptance; C1 = agent rate, C3 = +d, C2 = -d)
    d = effects["H1"]
    shift = {"C1": 0.0, "C2": -d, "C3": d}
    acc = {c: [] for c in A.OFFER_CONDS}
    for s in gs:
        for c in A.OFFER_CONDS:
            ds = [rng.random() < clip(agent_acc.get(a, agent_acc["_all"]) + shift[c])
                  for a, dec in s["replies"][c] if dec in ("ACCEPT", "DECLINE")]
            acc[c].append(sum(ds) / len(ds) if ds else None)
    for name, hi, lo in (("H1a", "C3", "C1"), ("H1b", "C1", "C2")):
        v = [h - l for h, l in zip(acc[hi], acc[lo]) if h is not None and l is not None]
        out[name] = signflip_p(v, rng, B)

    # H2 (C2 decliners' implicit acceptance = +d, C1/C3 decliners = 0)
    d = effects["H2"]
    for name, other in (("H2a", "C1"), ("H2b", "C3")):
        v = []
        for s, b in zip(gs, bases):
            if s["h2"]["C2"] and s["h2"][other]:
                (a1, a0), (o1, o0) = s["h2"]["C2"], s["h2"][other]
                ia2 = draw_rate(a1, clip(b + d)) - draw_rate(a0, b)
                iao = draw_rate(o1, b) - draw_rate(o0, b)
                v.append(ia2 - iao)
        out[name] = signflip_p(v, rng, B)

    # H3 / H4: all offered conditions shifted by d; values under every choice of control
    for name, key, base_fn in (("H3", "h3", lambda b: b), ("H4", "h4", None)):
        d = effects[name]
        table = []
        for s, b in zip(gs, bases):
            st = s[key]
            if not st:
                continue
            if key == "h4":
                b = expit(logit(effects["h4_base"]) + rng.normal(0, tau))
            r = {}
            for c in A.GROUP:
                n = st["n"][c]
                p = b if c == "C4" else clip(b + d)
                r[c] = draw_rate(n, p) if n else None
            row = []
            for ctrl in A.GROUP:
                vs = [r[c] - r[ctrl] for c in A.GROUP if c != ctrl and r[c] is not None and r[ctrl] is not None]
                row.append(sum(vs) / len(vs) if vs else np.nan)
            table.append(row)
        out[name] = h3_p(table, rng, B) if table else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sims", type=int, default=1000)
    ap.add_argument("--perms", type=int, default=2000)
    ap.add_argument("--Ns", default="6,12,15,18,24,30,36,45")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    games = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(args.records).glob("C?_g??.json"))]
    res = A.compute(games)
    data, per_g = structure(games)
    res["tests_gate_n"] = res["gate"]["n"]
    text = ["# Pilot2 opportunity counts (from analyze.py's Data/compute)\n", counts_table(data, per_g, res), ""]

    # Observed rates that parameterise the simulation
    used = [r for r in data.rows if r["used"]]
    c4p = [r for r in used if r["condition"] == "C4" and r["challenged_is_proposer"]]
    base_nc = (sum(not r["was_challenged"] for r in c4p) / len(c4p)) if c4p else 0.5
    c4o = [r for r in used if r["condition"] == "C4" and not r["challenged_is_proposer"]
           and r["challenger_can_challenge_proposer"] is False]
    h4_base = (sum(bool(r["was_challenged"]) for r in c4o) / len(c4o)) if c4o else 0.3
    tally = defaultdict(Counter)
    for g in data.numbers:
        for c in A.OFFER_CONDS:
            for a, d in per_g[g]["replies"][c]:
                tally[a][d] += 1
    tot_a = sum(t["ACCEPT"] for t in tally.values())
    tot_r = sum(t["ACCEPT"] + t["DECLINE"] for t in tally.values())
    overall = (tot_a + 1) / (tot_r + 2)
    agent_acc = {a: (t["ACCEPT"] + 2 * overall) / (t["ACCEPT"] + t["DECLINE"] + 2) for a, t in tally.items()}
    agent_acc["_all"] = overall
    params = {"C4 non-challenge on proposer plays": base_nc, "n C4 proposer decisions": len(c4p),
              "C4 challenge rate, H4 set": h4_base, "n C4 H4 decisions": len(c4o),
              "acceptance per agent (shrunk)": agent_acc}
    text += ["## Simulation parameters (observed in pilot2)\n", "```", json.dumps(params, indent=1), "```", ""]

    rng = np.random.default_rng(20261024)
    Ns = [int(x) for x in args.Ns.split(",")]
    scenarios = [("null", {"gate": 0.0, "H1": 0.0, "H2": 0.0, "H3": 0.0, "H4": 0.0}),
                 ("small", {"gate": 0.30, "H1": 0.10, "H2": 0.15, "H3": 0.10, "H4": 0.10}),
                 ("medium", {"gate": 0.40, "H1": 0.20, "H2": 0.25, "H3": 0.15, "H4": 0.15}),
                 ("large", {"gate": 0.50, "H1": 0.30, "H2": 0.35, "H3": 0.20, "H4": 0.20})]
    tests = ["gate", "H1a", "H1b", "H2a", "H2b", "H3", "H4"]
    results = []
    for tau in (0.0, 0.5):
        for sname, eff in scenarios:
            eff = dict(eff, h4_base=h4_base)
            for N in Ns:
                ps = defaultdict(list)
                for _ in range(args.sims):
                    o = simulate(per_g, base_nc, agent_acc, N, eff, tau, rng, args.perms)
                    for t in tests:
                        ps[t].append(o[t])
                row = {"tau": tau, "scenario": sname, "N": N}
                for t in tests:
                    p = ps[t]
                    row[t + "_p05"] = np.mean([x is not None and x < .05 for x in p])
                    row[t + "_p01"] = np.mean([x is not None and x < .01 for x in p])
                    row[t + "_evaluable"] = np.mean([x is not None for x in p])
                results.append(row)
                print(sname, tau, N, {t: round(row[t + "_p05"], 2) for t in tests}, flush=True)
    (out / "power_results.json").write_text(json.dumps({"params": params, "scenarios": scenarios,
                                                       "results": results}, indent=1), encoding="utf-8")
    for tau in (0.0, 0.5):
        for sname, eff in scenarios:
            text.append(f"## Power, scenario {sname} {eff}, between-game SD (logit) tau={tau}\n")
            text.append("Cells: P(p<.05) / P(p<.01). " + ", ".join(tests))
            text.append("")
            text.append("| N game numbers | " + " | ".join(tests) + " |")
            text.append("|---|" + "---|" * len(tests))
            for row in results:
                if row["tau"] == tau and row["scenario"] == sname:
                    text.append(f"| {row['N']} | " + " | ".join(
                        f"{row[t + '_p05']:.2f} / {row[t + '_p01']:.2f}" for t in tests) + " |")
            text.append("")
    (out / "power_summary.md").write_text("\n".join(text), encoding="utf-8")


if __name__ == "__main__":
    main()
