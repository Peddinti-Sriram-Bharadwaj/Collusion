"""Figure 8 (v2) for the scripted-offer part of the sprint report, 2026-10-26.

Panel (a), Run 1: for agents that judged the proposer's plays, the share of the proposer's plays and of
other players' plays let pass. Unit = game number (one value per game, mean over game numbers, 95% t-CI),
read from main/analysis/selectivity.csv, the per-game file that main/analysis/summary.md averages; the
means are asserted against the hand-off numbers. Conditions in their documented order; C1b is left out
because in C1b only one seat received the message, so its other-players value needs text to interpret.

Panel (b), seat after the proposer (X), two strips with different analysis units kept apart:
  top    - share of replies judged committed (reply level; Wilson 95% interval; counts from the hand-off:
           C1 6/89, C1c 11/30, C1d 27/30);
  bottom - pre-registered paired change in the share of the proposer's plays X let pass, relative to C1 of
           the same game number (game level; mean with 95% t-CI; HB2 and HB4 read from
           followup/analysis_judged/tests_B.json). C1 is the reference at zero.

Palette: muted, colorblind-safe, distinct in grayscale by marker shape and fill.
Outputs: fig_scripted_offer_v2.png (150 dpi) and fig_scripted_offer_v2.pdf.
"""
import csv, json, math, os, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import scipy.stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
C_PROP, C_OTH, C_VERB = "#2b5d8c", "#b07d3b", "#5c6b73"   # proposer's plays / other players' plays / verbal


def tci(vals):
    a = np.array(vals, float); n = len(a)
    return a.mean(), st.t.ppf(0.975, n - 1) * a.std(ddof=1) / math.sqrt(n), n


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


# ---------------- data, panel (a) ----------------
sel = list(csv.DictReader(open(os.path.join(ROOT, "main", "analysis", "selectivity.csv"))))
conds = ["C0", "C1", "C2", "C3", "C4", "C5"]
labels = {"C0": "C0\nframework\nalliance", "C1": "C1\ndirect\noffer", "C2": "C2\nhint",
          "C3": "C3\nbenign\nrequest", "C4": "C4\nno\nmessage", "C5": "C5\nplacebo"}
ncp = collections.defaultdict(list); nco = collections.defaultdict(list)
for r in sel:
    ncp[r["condition"]].append(float(r["nc_proposer"])); nco[r["condition"]].append(float(r["nc_others"]))
P = {c: tci(ncp[c]) for c in conds}; O = {c: tci(nco[c]) for c in conds}
check = {"C4": (0.478, 0.349), "C5": (0.560, 0.340), "C3": (0.429, 0.380), "C2": (0.547, 0.583), "C1": (0.617, 0.641)}
for c in check:
    assert abs(P[c][0] - check[c][0]) < 0.002 and abs(O[c][0] - check[c][1]) < 0.002, c
for c in conds:
    print("(a)", c, "g=%d" % P[c][2], "proposer %.3f +- %.3f" % P[c][:2], "others %.3f +- %.3f" % O[c][:2])

# ---------------- data, panel (b) ----------------
REPLY = [("C1", 6, 89), ("C1c", 11, 30), ("C1d", 27, 30)]
blabels = {"C1": "C1\ndirect\noffer", "C1c": "C1c\nfabricated\nrecord", "C1d": "C1d\nfalse system\nauthority"}
tb = json.load(open(os.path.join(ROOT, "followup", "analysis_judged", "tests_B.json")))
DELTA = {"C1c": tb["HB2"]["dR"], "C1d": tb["HB4"]["dR"]}
assert abs(DELTA["C1c"]["mean"] - 0.122) < 0.001 and abs(DELTA["C1d"]["mean"] - 0.291) < 0.001
for c in DELTA:
    print("(b)", c, "dR_X %.3f [%.3f, %.3f]" % (DELTA[c]["mean"], DELTA[c]["ci"][0], DELTA[c]["ci"][1]))

# ---------------- figure ----------------
fig = plt.figure(figsize=(7.6, 3.4))
gs = fig.add_gridspec(2, 2, width_ratios=[1.45, 1], height_ratios=[1, 1], hspace=0.12, wspace=0.42)
a = fig.add_subplot(gs[:, 0]); b1 = fig.add_subplot(gs[0, 1]); b2 = fig.add_subplot(gs[1, 1], sharex=b1)
for ax in (a, b1, b2):
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(labelsize=7)

# (a) dot-and-whisker, both rates per condition, joined by a thin grey line (the gap is the proposer-specific margin)
x = np.arange(len(conds)); dx = 0.17
for i, c in enumerate(conds):
    a.plot([i - dx, i + dx], [P[c][0], O[c][0]], color="#bbbbbb", lw=1, zorder=1)
a.errorbar(x - dx, [P[c][0] for c in conds], yerr=[P[c][1] for c in conds], fmt="o", color=C_PROP, ms=5.5,
           capsize=2.5, lw=1.2, label="proposer's plays", zorder=3)
a.errorbar(x + dx, [O[c][0] for c in conds], yerr=[O[c][1] for c in conds], fmt="s", color=C_OTH, mfc="white",
           mew=1.4, ms=5.5, capsize=2.5, lw=1.2, label="other players' plays", zorder=3)
a.set_xticks(x); a.set_xticklabels([labels[c] for c in conds], fontsize=6.8)
a.set_ylim(0, 1.0); a.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
a.set_ylabel("share of plays let pass (per game, mean, 95% CI)", fontsize=7.5)
a.set_title("(a) Run 1: which plays are let pass", fontsize=8.5, fontweight="bold", loc="left")
a.legend(fontsize=6.8, frameon=False, loc="upper right", ncol=2, handletextpad=0.4, columnspacing=1.0)
a.axvline(0.5, color="#dddddd", lw=0.8)   # positive control (C0) set off from the peer-message conditions

# (b) top strip: verbal commitment, reply level
xb = np.arange(len(REPLY))
shares = [k / n for _, k, n in REPLY]
err = np.array([[s - wilson(k, n)[0], wilson(k, n)[1] - s] for (_, k, n), s in zip(REPLY, shares)]).T
b1.errorbar(xb, shares, yerr=err, fmt="^", color=C_VERB, ms=6, capsize=2.5, lw=1.2)
for xi, (c, k, n) in zip(xb, REPLY):
    b1.text(xi + 0.12, k / n, "%d/%d" % (k, n), fontsize=6.3, va="center", ha="left", color=C_VERB)
b1.set_ylim(-0.05, 1.12); b1.set_yticks([0, 0.5, 1.0])
b1.set_ylabel("replies judged\ncommitted (share)", fontsize=7)
b1.set_title("(b) Seat after the proposer: words vs behaviour", fontsize=8.5, fontweight="bold", loc="left")
plt.setp(b1.get_xticklabels(), visible=False); b1.tick_params(axis="x", length=0)

# (b) bottom strip: behaviour, pre-registered paired change vs C1, game level
b2.axhline(0, color="#999999", lw=0.8)
b2.plot([0], [0], "o", color=C_PROP, mfc="white", mew=1.4, ms=5.5)   # C1 = reference
for xi, c in zip(xb[1:], ["C1c", "C1d"]):
    m, (lo, hi) = DELTA[c]["mean"], DELTA[c]["ci"]
    b2.errorbar([xi], [m], yerr=[[m - lo], [hi - m]], fmt="o", color=C_PROP, ms=5.5, capsize=2.5, lw=1.2)
b2.set_ylim(-0.25, 0.65); b2.set_yticks([-0.2, 0, 0.2, 0.4, 0.6])
b2.set_ylabel("proposer's plays\nlet pass, change\nvs C1 (per game)", fontsize=7)
b2.set_xticks(xb); b2.set_xticklabels([blabels[c] for c, _, _ in REPLY], fontsize=6.8)

fig.savefig(os.path.join(HERE, "fig_scripted_offer_v2.png"), dpi=150, bbox_inches="tight")
fig.savefig(os.path.join(HERE, "fig_scripted_offer_v2.pdf"), bbox_inches="tight")
print("done")
