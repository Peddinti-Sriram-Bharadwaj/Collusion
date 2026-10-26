"""Figures for the scripted-offer section of the sprint report.

Format follows Collusion/submission/figs (plain matplotlib, 150 dpi, 95% CI, bold title); the content
is unrelated to those figures. Every number is copied from DRAFT_inference_sentences_EN.md /
main/analysis/summary.md / followup/analysis_judged/tests_B.json. The only computation is the
95% t-interval over game numbers for the optional Figure C, from main/analysis/selectivity.csv
(the same per-game values that summary.md averages).

Outputs (each as .png and .jpg):
  fig_scripted_offer_run1  - Run 1 pre-registered contrasts (Gate, HM, Family A)
  fig_scripted_offer_run2  - Run 2 pre-registered contrasts (Family B)
  fig_scripted_offer_passivity - optional, Run 1 non-challenge on proposer vs others
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
BLUE, GREY, ORANGE = "#4c72b0", "#9a9a9a", "#dd8452"


def save(fig, stem):
    png = os.path.join(HERE, stem + ".png")
    fig.savefig(png, dpi=150, bbox_inches="tight")
    Image.open(png).convert("RGB").save(os.path.join(HERE, stem + ".jpg"), quality=95)
    plt.close(fig)


# (short label, mean, lo, hi, verdict text, H0 rejected?)
RUN1 = [
    ("Gate  framework alliance, C0 - C4",           +0.569, +0.397, +0.740, "passed, p<.0001", True),
    ("HM  challenge others after any message, - C4", -0.213, -0.288, -0.138, "supported, p<.0001", True),
    ("HA1a  committed replies, offer - hint",         -0.089, -0.175, -0.003, "not rejected, p=.23", False),
    ("HA1b  wary replies, offer - hint",              +0.400, +0.281, +0.519, "rejected (opposite sign), p=.0003", True),
    ("HA1c  X committed, social proof - offer",       +0.200, -0.038, +0.438, "not rejected, p=.36", False),
    ("HA2a  selectivity, pact messages - placebo",    -0.197, -0.359, -0.034, "not rejected, p=.07", False),
    ("HA2b  selectivity, offer - hint",               -0.063, -0.224, +0.099, "not rejected, p=.42", False),
    ("HA2c  selectivity, social proof - offer",       +0.326, +0.141, +0.512, "rejected (other-player component), p=.009", True),
]
RUN2 = [
    ("HB1  true 5-game record, C1s game 3 - C1",     +0.069, -0.037, +0.176, "not supported, p=.38", False),
    ("HB2  false record, C1c - C1",                   +0.122, +0.017, +0.228, "not supported, p=.06", False),
    ("HB3  false record as directive, C1ci - C1",     -0.012, -0.172, +0.148, "not supported, p=.89", False),
    ("HB4  false system authority, C1d - C1",         +0.291, +0.075, +0.507, "rejected (general passivity), p=.043", True),
]

# cross-check Family B against the official test file
tb = json.load(open(os.path.join(ROOT, "followup", "analysis_judged", "tests_B.json")))
for name, t in zip(["HB1", "HB2", "HB3", "HB4"], RUN2):
    assert abs(tb[name]["dR"]["mean"] - t[1]) < 0.001, name
    assert abs(tb[name]["dR"]["ci"][0] - t[2]) < 0.001 and abs(tb[name]["dR"]["ci"][1] - t[3]) < 0.001, name


def forest(tests, title, xlabel, groups, xlim, stem, height):
    """groups: list of (row index where the group starts, group label)."""
    fig, ax = plt.subplots(figsize=(9.0, height))
    y = np.arange(len(tests))[::-1]
    for yi, t in zip(y, tests):
        c = BLUE if t[5] else GREY
        ax.plot([t[2], t[3]], [yi, yi], color=c, lw=2.4, solid_capstyle="round")
        ax.plot(t[1], yi, "o", color=c, ms=7)
        ax.text(1.02, yi, t[4], fontsize=8, va="center", ha="left",
                transform=ax.get_yaxis_transform(), color="black" if t[5] else "#555555")
    ax.axvline(0, color="grey", lw=0.9)
    for i, lab in groups:
        if i > 0:
            ax.axhline(y[i] + 0.5, color="#dddddd", lw=0.8)
        ax.text(xlim[0], y[i] + 0.42, lab, fontsize=8, color="#555555", va="bottom")
    ax.set_yticks(y); ax.set_yticklabels([t[0] for t in tests], fontsize=8.5)
    ax.set_xlim(*xlim); ax.set_ylim(-0.7, len(tests) - 0.1)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_title(title, fontsize=11, fontweight="bold", loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, stem)


forest(RUN1,
       "Run 1 (7 conditions x 30 games): pre-registered contrasts",
       "paired difference over game numbers (mean, 95% CI; p = Holm-adjusted within Family A, checks uncorrected)",
       [(0, "manipulation checks"), (2, "Family A (Holm, 6)")],
       (-0.45, 0.8), "fig_scripted_offer_run1", 4.2)

forest(RUN2,
       "Run 2 (Family B, 30 games per condition): change in X's sparing of the proposer vs Run 1 C1",
       "paired difference over game numbers (mean, 95% CI; p = Holm-adjusted, family of 4)",
       [(0, "Family B")],
       (-0.25, 0.6), "fig_scripted_offer_run2", 2.6)

# ---------- optional Figure C: passivity, not pact (Run 1, proposer-facing agents) ----------
sel = list(csv.DictReader(open(os.path.join(ROOT, "main", "analysis", "selectivity.csv"))))
conds = ["C4", "C5", "C3", "C2", "C1"]
names = {"C4": "C4\nno message", "C5": "C5\nplacebo", "C3": "C3\nbenign", "C2": "C2\nhint", "C1": "C1\ndirect offer"}


def stat(vals):
    a = np.array(vals, float); n = len(a)
    return a.mean(), st.t.ppf(0.975, n - 1) * a.std(ddof=1) / math.sqrt(n), n


ncp = collections.defaultdict(list); nco = collections.defaultdict(list)
for r in sel:
    ncp[r["condition"]].append(float(r["nc_proposer"])); nco[r["condition"]].append(float(r["nc_others"]))
summary_means = {"C4": (0.478, 0.349), "C5": (0.560, 0.340), "C3": (0.429, 0.380), "C2": (0.547, 0.583), "C1": (0.617, 0.641)}
P = [stat(ncp[c]) for c in conds]; O = [stat(nco[c]) for c in conds]
for c, p, o in zip(conds, P, O):
    assert abs(p[0] - summary_means[c][0]) < 0.002 and abs(o[0] - summary_means[c][1]) < 0.002, (c, p, o)
    print(c, "g=%d" % p[2], "proposer %.3f +- %.3f" % (p[0], p[1]), "others %.3f +- %.3f" % (o[0], o[1]))

fig, ax = plt.subplots(figsize=(6, 3.2))
x = np.arange(len(conds)); w = 0.38
ax.bar(x - w / 2, [p[0] for p in P], w, yerr=[p[1] for p in P], capsize=3, color=BLUE, label="on the proposer's plays")
ax.bar(x + w / 2, [o[0] for o in O], w, yerr=[o[1] for o in O], capsize=3, color=ORANGE, label="on other players' plays")
ax.set_xticks(x); ax.set_xticklabels([names[c] for c in conds], fontsize=8)
ax.set_ylabel("Non-challenge rate"); ax.set_ylim(0, 1.0)
ax.set_title("Run 1: non-challenge of the proposer vs of other players", fontsize=10, fontweight="bold")
ax.legend(fontsize=7, frameon=False, loc="upper left")
ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig_scripted_offer_passivity")
print("done")
