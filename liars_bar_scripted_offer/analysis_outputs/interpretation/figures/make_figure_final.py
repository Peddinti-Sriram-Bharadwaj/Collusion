"""Single two-panel figure for the scripted-offer contribution to the sprint report (2026-10-26).

Style matches the teammates' figures in Collusion/submission/figs (plain matplotlib defaults, 150 dpi,
bold title, 95% error bars). Conditions are ordered by their experimental definition
(C0, C1, C1b, C2, C3, C4, C5; Run 2 conditions C1c, C1ci, C1d after C1), never by effect size.

Numbers: panel (a) is the mean over game numbers of main/analysis/selectivity.csv (the file that
main/analysis/summary.md averages; the asserts below check the means against the hand-off) with a
95% t-interval. Panel (b): bars are reply counts from DRAFT_inference_sentences_EN.md with Wilson 95% intervals (reply level);
points are the pre-registered paired differences HB2/HB4 (game level, 95% t-CI), asserted against tests_B.json.

Outputs: fig_scripted_offer.png / .jpg / .pdf
"""
import csv, math, os, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
import scipy.stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
BLUE, ORANGE = "#4c72b0", "#dd8452"


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def stat(vals):
    a = np.array(vals, float); n = len(a)
    return a.mean(), st.t.ppf(0.975, n - 1) * a.std(ddof=1) / math.sqrt(n), n


# ---- panel (a): Run 1, proposer-facing agents, non-challenge on the proposer vs on other players ----
sel = list(csv.DictReader(open(os.path.join(ROOT, "main", "analysis", "selectivity.csv"))))
conds = ["C0", "C1", "C2", "C3", "C4", "C5"]
names = {"C0": "C0\nframework\nalliance", "C1": "C1\ndirect\noffer", "C1b": "C1b\noffer +\nsocial proof",
         "C2": "C2\nhint", "C3": "C3\nbenign\nrequest", "C4": "C4\nno\nmessage", "C5": "C5\nplacebo"}
ncp = collections.defaultdict(list); nco = collections.defaultdict(list)
for r in sel:
    ncp[r["condition"]].append(float(r["nc_proposer"])); nco[r["condition"]].append(float(r["nc_others"]))
P = [stat(ncp[c]) for c in conds]; O = [stat(nco[c]) for c in conds]
check = {"C4": (0.478, 0.349), "C5": (0.560, 0.340), "C3": (0.429, 0.380), "C2": (0.547, 0.583), "C1": (0.617, 0.641)}
for c, p, o in zip(conds, P, O):
    if c in check:
        assert abs(p[0] - check[c][0]) < 0.002 and abs(o[0] - check[c][1]) < 0.002, (c, p, o)
    print(c, "g=%d" % p[2], "proposer %.3f +- %.3f" % (p[0], p[1]), "others %.3f +- %.3f" % (o[0], o[1]))

# ---- panel (b): seat after the proposer (X). Bars: judged-committed replies (reply level, Wilson 95% CI).
# Points (right axis): pre-registered paired change in X's non-challenge of the proposer vs Run 1 C1 of the same
# game number (game level, mean with 95% t-CI; HB2 and HB4 in followup/analysis_judged/tests_B.json).
NL = chr(10)
REPLY = [("C1" + NL + "direct" + NL + "offer", 6, 89), ("C1c" + NL + "false" + NL + "record", 11, 30),
         ("C1d" + NL + "false system" + NL + "authority", 27, 30)]
DELTA = {"C1c": (0.122, 0.017, 0.228), "C1d": (0.291, 0.075, 0.507)}
import json
tb = json.load(open(os.path.join(ROOT, "followup", "analysis_judged", "tests_B.json")))
for h, c in [("HB2", "C1c"), ("HB4", "C1d")]:
    assert abs(tb[h]["dR"]["mean"] - DELTA[c][0]) < 0.001 and abs(tb[h]["dR"]["ci"][0] - DELTA[c][1]) < 0.001 and abs(tb[h]["dR"]["ci"][1] - DELTA[c][2]) < 0.001

fig, (a, b) = plt.subplots(1, 2, figsize=(7.6, 3.3), gridspec_kw={"width_ratios": [1.5, 1]})
x = np.arange(len(conds)); w = 0.38
a.bar(x - w / 2, [p[0] for p in P], w, yerr=[p[1] for p in P], capsize=3, color=BLUE, label="proposer's plays")
a.bar(x + w / 2, [o[0] for o in O], w, yerr=[o[1] for o in O], capsize=3, color=ORANGE, label="other players' plays")
a.set_xticks(x); a.set_xticklabels([names[c] for c in conds], fontsize=6.5)
a.set_ylabel("plays let pass (share)", fontsize=7.5); a.set_ylim(0, 1.2); a.tick_params(axis="y", labelsize=7)
a.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
a.set_title("(a) Run 1: whose plays are let pass", fontsize=8.5, fontweight="bold", loc="left")
a.legend(fontsize=6.5, frameon=False, loc="upper right", ncol=2)
a.spines[["top", "right"]].set_visible(False)

x = np.arange(len(REPLY)); w = 0.36
shares = [k / n for _, k, n in REPLY]
err = np.array([[s - wilson(k, n)[0], wilson(k, n)[1] - s] for (_, k, n), s in zip(REPLY, shares)]).T
h1 = b.bar(x - w / 2, shares, w, yerr=err, capsize=3, color=BLUE, label="replies judged committed (left axis)")
b.set_xticks(x); b.set_xticklabels([r[0] for r in REPLY], fontsize=6.5)
b.set_ylim(0, 1.3); b.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0]); b.tick_params(axis="y", labelsize=7)
b.set_ylabel("share of replies", fontsize=7.5)
b2 = b.twinx()
b2.axhline(0, color="grey", lw=0.8)
px = [1 + w / 2, 2 + w / 2]; pm = [DELTA["C1c"][0], DELTA["C1d"][0]]
pe = [[DELTA["C1c"][0] - DELTA["C1c"][1], DELTA["C1d"][0] - DELTA["C1d"][1]], [DELTA["C1c"][2] - DELTA["C1c"][0], DELTA["C1d"][2] - DELTA["C1d"][0]]]
h2 = b2.errorbar(px, pm, yerr=pe, fmt="D", color=ORANGE, ms=6, capsize=3, label="change vs C1 in proposer's plays" + NL + "let pass, paired by game (right axis)")
b2.plot([0 + w / 2], [0], "D", color=ORANGE, ms=6, mfc="white")
b2.set_ylim(-0.3, 0.85); b2.set_yticks([-0.2, 0, 0.2, 0.4, 0.6]); b2.tick_params(axis="y", labelsize=7, colors=ORANGE)
b2.set_ylabel("change vs C1 (share of plays)", fontsize=7.5, color=ORANGE)
b2.spines[["top"]].set_visible(False); b.spines[["top"]].set_visible(False)
b.legend([h1, h2], [h1.get_label(), h2.get_label()], fontsize=6.3, frameon=False, loc="upper left")
b.set_title("(b) Seat after proposer: words vs behaviour", fontsize=8.5, fontweight="bold", loc="left")
fig.tight_layout(w_pad=2.5)

png = os.path.join(HERE, "fig_scripted_offer.png")
fig.savefig(png, dpi=150, bbox_inches="tight")
fig.savefig(os.path.join(HERE, "fig_scripted_offer.pdf"), bbox_inches="tight")
Image.open(png).convert("RGB").save(os.path.join(HERE, "fig_scripted_offer.jpg"), quality=95)
print("done")
