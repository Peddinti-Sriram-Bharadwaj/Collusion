"""Two figures for the scripted-offer part of the sprint report (v2, 2026-10-26).

Format follows the teammates' figures (plain matplotlib default style, 150 dpi, bold title,
95% intervals, verdict text beside each estimate as in 21_hypotheses.png). Content is ours.
Every number is copied from DRAFT_inference_sentences_EN.md; the only computations are
(a) the 95% t-interval over game numbers in Fig 1a, from main/analysis/selectivity.csv, which is
the file summary.md averages, and (b) Wilson 95% intervals for the reply shares in Fig 2b.

Outputs (.png and .jpg): fig_scripted_offer_1.{png,jpg}  (Run 1)
                          fig_scripted_offer_2.{png,jpg}  (Run 2)
"""
import csv, json, math, os, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
import scipy.stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GREEN, AMBER, RED, GREY, BLUE, ORANGE = "#2e9e5b", "#e3b23c", "#c84b4b", "#8c8c8c", "#4c72b0", "#dd8452"


def save(fig, stem):
    png = os.path.join(HERE, stem + ".png")
    fig.savefig(png, dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(HERE, stem + ".pdf"), bbox_inches="tight")
    Image.open(png).convert("RGB").save(os.path.join(HERE, stem + ".jpg"), quality=95)
    plt.close(fig)


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


# ---------------- Figure 1: Run 1 ----------------
# (label, mean, lo, hi, verdict text, colour)
RUN1 = [
    ("Gate: framework alliance\n(C0 - C4, manipulation check)",      +0.569, +0.397, +0.740, "passed (p<.0001)", GREEN),
    ("HM: challenging other players\nafter any message (- C4, check)", -0.213, -0.288, -0.138, "supported (p<.0001)", GREEN),
    ("HA1a: committed replies,\ndirect offer - hint",                  -0.089, -0.175, -0.003, "not rejected (Holm p=.23)", AMBER),
    ("HA1b: wary/deferring replies,\ndirect offer - hint",             +0.400, +0.281, +0.519, "rejected, opposite sign (Holm p=.0003)", RED),
    ("HA1c: X committed,\nsocial proof - direct offer",                +0.200, -0.038, +0.438, "not rejected (Holm p=.36)", AMBER),
    ("HA2a: sparing aimed at proposer,\npact messages - placebo",      -0.197, -0.359, -0.034, "not rejected (Holm p=.07)", AMBER),
    ("HA2b: sparing aimed at proposer,\ndirect offer - hint",          -0.063, -0.224, +0.099, "not rejected (Holm p=.42)", AMBER),
    ("HA2c: sparing aimed at proposer,\nsocial proof - direct offer",  +0.326, +0.141, +0.512, "rejected, but all of it is\nother-player decisions (Holm p=.009)", RED),
]

sel = list(csv.DictReader(open(os.path.join(ROOT, "main", "analysis", "selectivity.csv"))))
conds = ["C4", "C5", "C3", "C2", "C1"]
names = {"C4": "no message", "C5": "placebo", "C3": "benign\nrequest", "C2": "hint", "C1": "direct\noffer"}
ncp = collections.defaultdict(list); nco = collections.defaultdict(list)
for r in sel:
    ncp[r["condition"]].append(float(r["nc_proposer"])); nco[r["condition"]].append(float(r["nc_others"]))


def stat(vals):
    a = np.array(vals, float); n = len(a)
    return a.mean(), st.t.ppf(0.975, n - 1) * a.std(ddof=1) / math.sqrt(n), n


P = [stat(ncp[c]) for c in conds]; O = [stat(nco[c]) for c in conds]
summary_means = {"C4": (0.478, 0.349), "C5": (0.560, 0.340), "C3": (0.429, 0.380), "C2": (0.547, 0.583), "C1": (0.617, 0.641)}
for c, p, o in zip(conds, P, O):
    assert abs(p[0] - summary_means[c][0]) < 0.002 and abs(o[0] - summary_means[c][1]) < 0.002, (c, p, o)

fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1, 1.6]})
x = np.arange(len(conds)); w = 0.38
a.bar(x - w / 2, [p[0] for p in P], w, yerr=[p[1] for p in P], capsize=3, color=BLUE, label="on the proposer's plays")
a.bar(x + w / 2, [o[0] for o in O], w, yerr=[o[1] for o in O], capsize=3, color=ORANGE, label="on other players' plays")
a.set_xticks(x); a.set_xticklabels([names[c] for c in conds], fontsize=9)
a.set_ylabel("non-challenge rate (share of plays let pass)"); a.set_ylim(0, 1.0)
a.set_title("(a) Who gets spared after a message", fontsize=11, fontweight="bold", loc="left")
a.legend(fontsize=8, frameon=False, loc="upper left")
a.spines[["top", "right"]].set_visible(False)

y = np.arange(len(RUN1))[::-1]
for yi, t in zip(y, RUN1):
    b.plot([t[2], t[3]], [yi, yi], color=t[5], lw=2.4, solid_capstyle="round")
    b.plot(t[1], yi, "o", color=t[5], ms=7)
    b.text(1.02, yi, t[4], fontsize=8, va="center", ha="left", transform=b.get_yaxis_transform())
b.axvline(0, color="grey", lw=0.9)
b.axhline(y[2] + 0.5, color="#dddddd", lw=0.8)
b.set_yticks(y); b.set_yticklabels([t[0] for t in RUN1], fontsize=8)
b.set_xlim(-0.45, 0.8); b.set_ylim(-0.7, len(RUN1) - 0.3)
b.set_xlabel("paired difference over game numbers (mean, 95% CI)", fontsize=9)
b.set_title("(b) Pre-registered tests, Run 1 (7 conditions x 30 games)", fontsize=11, fontweight="bold", loc="left")
b.spines[["top", "right"]].set_visible(False)
fig.tight_layout(w_pad=2.0)
save(fig, "fig_scripted_offer_1")

# ---------------- Figure 2: Run 2 ----------------
RUN2 = [
    ("HB1: true record of 5 games\n(C1s game 3 - C1)",            +0.069, -0.037, +0.176, "not supported (Holm p=.38)", AMBER),
    ("HB2: false record of past cooperation\n(C1c - C1)",          +0.122, +0.017, +0.228, "not supported (Holm p=.06)", AMBER),
    ("HB3: same false record as a directive\n(C1ci - C1)",         -0.012, -0.172, +0.148, "not supported (Holm p=.89)", AMBER),
    ("HB4: peer falsely claims to be\npart of the prompt (C1d - C1)", +0.291, +0.075, +0.507, "rejected (Holm p=.043); reading rule:\ngeneral passivity, not aimed at the proposer", RED),
]
tb = json.load(open(os.path.join(ROOT, "followup", "analysis_judged", "tests_B.json")))
for name, t in zip(["HB1", "HB2", "HB3", "HB4"], RUN2):
    assert abs(tb[name]["dR"]["mean"] - t[1]) < 0.001, name
    assert abs(tb[name]["dR"]["ci"][0] - t[2]) < 0.001 and abs(tb[name]["dR"]["ci"][1] - t[3]) < 0.001, name

# judged "committed" replies (counts from the hand-off) and X's pooled non-challenge of the proposer
REPLY = [("C1\ndirect offer\n(Run 1)", 6, 89, 0.836), ("C1c\nfalse record", 11, 30, 0.913),
         ("C1ci\nrecord as\ndirective", 7, 30, 0.840), ("C1d\nfalse system\nauthority", 27, 30, 0.915)]

fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.0), gridspec_kw={"width_ratios": [1.6, 1]})
y = np.arange(len(RUN2))[::-1]
for yi, t in zip(y, RUN2):
    a.plot([t[2], t[3]], [yi, yi], color=t[5], lw=2.4, solid_capstyle="round")
    a.plot(t[1], yi, "o", color=t[5], ms=7)
    a.text(1.02, yi, t[4], fontsize=8, va="center", ha="left", transform=a.get_yaxis_transform())
a.axvline(0, color="grey", lw=0.9)
a.set_yticks(y); a.set_yticklabels([t[0] for t in RUN2], fontsize=8)
a.set_xlim(-0.25, 0.6); a.set_ylim(-0.6, len(RUN2) - 0.4)
a.set_xlabel("change in X's non-challenge of the proposer vs Run 1 C1, same game number (mean, 95% CI)", fontsize=8.5)
a.set_title("(a) Pre-registered tests, Run 2 (Family B, 30 games per condition)", fontsize=11, fontweight="bold", loc="left")
a.spines[["top", "right"]].set_visible(False)

x = np.arange(len(REPLY)); w = 0.38
shares = [k / n for _, k, n, _ in REPLY]
err = np.array([[s - wilson(k, n)[0], wilson(k, n)[1] - s] for (_, k, n, _), s in zip(REPLY, shares)]).T
b.bar(x - w / 2, shares, w, yerr=err, capsize=3, color=BLUE, label="replies judged 'committed'")
b.bar(x + w / 2, [p for *_, p in REPLY], w, color=ORANGE, label="X let the proposer's plays pass\n(pooled over decisions)")
b.set_xticks(x); b.set_xticklabels([r[0] for r in REPLY], fontsize=8)
b.set_ylim(0, 1.3); b.set_yticks([0,0.2,0.4,0.6,0.8,1.0]); b.set_ylabel("share")
b.set_title("(b) Words vs behaviour, seat after the proposer", fontsize=11, fontweight="bold", loc="left")
b.legend(fontsize=7.5, frameon=False, loc="upper left", ncol=1)
b.spines[["top", "right"]].set_visible(False)
fig.tight_layout(w_pad=2.0)
save(fig, "fig_scripted_offer_2")
print("done")
