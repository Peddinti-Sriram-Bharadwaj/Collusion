"""EXPLORATORY (not pre-registered; written 2026-10-26 after seeing summary.md).
Paired within-game-number contrasts of selectivity and its two components, from analysis/selectivity.csv.
Two-sided sign-flip p (exact for n <= 16, else 200k Monte Carlo, seed 0); mean ± 1.96 SE. No multiplicity correction."""
import csv, statistics as st, itertools, math, random, sys
rows = list(csv.DictReader(open(sys.argv[1])))
num = lambda v: None if v in ('', 'nan', 'None') else float(v)
d = {(r['condition'], int(r['game_number'])): {k: num(r[k]) for k in ('nc_proposer', 'nc_others', 'selectivity')}
     for r in rows if num(r['selectivity']) is not None}
def signflip(x):
    obs = abs(sum(x))
    if len(x) <= 16:
        return sum(abs(sum(a * b for a, b in zip(s, x))) >= obs - 1e-12 for s in itertools.product([1, -1], repeat=len(x))) / 2 ** len(x)
    random.seed(0)
    return sum(abs(sum(a * random.choice((1, -1)) for a in x)) >= obs - 1e-12 for _ in range(200000)) / 200000
for a, b in [('C1b', 'C5'), ('C1b', 'C4'), ('C5', 'C4'), ('C1', 'C4'), ('C2', 'C4')]:
    for comp in ('selectivity', 'nc_proposer', 'nc_others'):
        x = [d[(a, g)][comp] - d[(b, g)][comp] for g in range(30) if (a, g) in d and (b, g) in d]
        print(f"{a}-{b} {comp:12s} n={len(x):2d} mean={st.mean(x):+.3f} +/-{1.96 * st.stdev(x) / math.sqrt(len(x)):.3f} p2={signflip(x):.3f}")
