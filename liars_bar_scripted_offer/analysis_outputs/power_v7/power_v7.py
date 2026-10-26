"""Two-sided sign-flip power for v7 Family A, with pilot-2 contribution rates. Local CPU only."""
import numpy as np, itertools
rng = np.random.default_rng(7)

def p_signflip_two_sided(v):
    n = len(v)
    if n < 2: return None
    obs = abs(v.mean())
    if n <= 14:
        signs = np.array(list(itertools.product([1, -1], repeat=n)))
        return float(np.mean(np.abs((signs * v).mean(1)) >= obs - 1e-12))
    S = rng.choice([1, -1], size=(4000, n))
    return float((np.sum(np.abs((S * v).mean(1)) >= obs - 1e-12) + 1) / 4001)

def power(N, r, gen, alphas, sims=1500):
    hits = {a: 0 for a in alphas}; ns = []
    for _ in range(sims):
        n = rng.binomial(N, r); ns.append(n)
        v = gen(n)
        p = p_signflip_two_sided(v) if n >= 2 else None
        for a in alphas:
            hits[a] += (p is not None and p < a)
    return {a: hits[a] / sims for a in alphas}, np.mean(ns)

ALPH = (0.05, 0.0125, 0.0083)
Ns = (8, 12, 16, 24, 30)
print("alphas: .05 | .0125 (Holm first step, 4 tests) | .0083 (Holm first step, 6 tests)")

def sel_gen(delta, sigma=0.7):
    return lambda n: np.clip(rng.normal(delta, sigma, n), -2, 2)
def share_gen(delta, k=3):
    # per game: share of k recipients committed, C1 ~ Bin(k,p1)/k, C2 ~ Bin(k,p2)/k
    p2 = 0.15; p1 = min(0.95, p2 + delta)
    return lambda n: rng.binomial(k, p1, n) / k - rng.binomial(k, p2, n) / k
def binary_gen(delta):
    p1 = 0.15; pb = min(0.95, p1 + delta)
    return lambda n: rng.binomial(1, pb, n) - rng.binomial(1, p1, n)

cases = [
    ("HA2b sel C1-C2  r=.50  d=.15 s=.7", 0.50, sel_gen(0.15)),
    ("HA2b sel C1-C2  r=.50  d=.25 s=.7", 0.50, sel_gen(0.25)),
    ("HA2b sel C1-C2  r=.50  d=.35 s=.7", 0.50, sel_gen(0.35)),
    ("HA2a sel pact-C5 r=.60 d=.25 s=.6", 0.60, sel_gen(0.25, 0.6)),
    ("HA2c sel C1b-C1 r=.45  d=.25 s=.7", 0.45, sel_gen(0.25)),
    ("HA2c sel C1b-C1 r=.45  d=.40 s=.7", 0.45, sel_gen(0.40)),
    ("HA1a commit C1-C2 r=.95 d=.20", 0.95, share_gen(0.20)),
    ("HA1a commit C1-C2 r=.95 d=.35", 0.95, share_gen(0.35)),
    ("HA1c X commit C1b-C1 r=.55 d=.30", 0.55, binary_gen(0.30)),
    ("HA1c X commit C1b-C1 r=.55 d=.50", 0.55, binary_gen(0.50)),
    ("Gate C0-C4 proposer r=.75 d=.30 s=.4", 0.75, sel_gen(0.30, 0.4)),
    ("null sel r=.5 d=0 (type I)", 0.50, sel_gen(0.0)),
]
for name, r, gen in cases:
    row = []
    for N in Ns:
        pw, nbar = power(N, r, gen, ALPH)
        row.append(f"N={N}(n={nbar:.1f}): " + "/".join(f"{pw[a]:.2f}" for a in ALPH))
    print(name); print("   " + " | ".join(row))
