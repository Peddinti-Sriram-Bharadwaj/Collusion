"""Scripted-offer figures and tables, v3 (2026-10-26): one plot or one table per file.

Figures (game-level or reply-level units, never pooled decisions):
  fig_nonchallenge_rates   Run 1, agents that judged the proposer's plays: share of the proposer's plays and of
                           other players' plays let pass; one value per game, mean over game numbers, 95% t-CI.
                           Source: main/analysis/selectivity.csv (asserted against the hand-off means).
  fig_verbal_commitment    Seat after the proposer: share of replies judged committed, Wilson 95% interval.
                           Counts from DRAFT_inference_sentences_EN.md: C1 6/89, C1c 11/30, C1d 27/30.
Tables (pre-registered tests; values from main/analysis/summary.md and followup/analysis_judged/tests_B.json,
Run 2 asserted against the json):
  table_run1_results       Gate, HA1a-c, HA2a-c, HM.
  table_run2_results       HB1-HB4.
Each saved as .pdf and .png (150 dpi). Palette: slate blue, dark teal, muted grey.
"""
import csv, json, math, os, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import scipy.stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SLATE, TEAL, GREY = "#3b5b8c", "#1f6f6f", "#6e6e6e"
plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5,
                     "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": "white"})


def save(fig, stem):
    fig.savefig(os.path.join(HERE, stem + ".pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(HERE, stem + ".png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def tci(vals):
    a = np.array(vals, float); n = len(a)
    return a.mean(), st.t.ppf(0.975, n - 1) * a.std(ddof=1) / math.sqrt(n), n


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


# ---------------- Figure: non-challenge rates, Run 1 ----------------
sel = list(csv.DictReader(open(os.path.join(ROOT, "main", "analysis", "selectivity.csv"))))
conds = ["C0", "C1", "C2", "C3", "C4", "C5"]
ncp = collections.defaultdict(list); nco = collections.defaultdict(list)
for r in sel:
    ncp[r["condition"]].append(float(r["nc_proposer"])); nco[r["condition"]].append(float(r["nc_others"]))
P = {c: tci(ncp[c]) for c in conds}; O = {c: tci(nco[c]) for c in conds}
check = {"C4": (0.478, 0.349), "C5": (0.560, 0.340), "C3": (0.429, 0.380), "C2": (0.547, 0.583), "C1": (0.617, 0.641)}
for c in check:
    assert abs(P[c][0] - check[c][0]) < 0.002 and abs(O[c][0] - check[c][1]) < 0.002, c
for c in conds:
    print("rates", c, "g=%d" % P[c][2], "proposer %.3f +- %.3f" % P[c][:2], "others %.3f +- %.3f" % O[c][:2])

fig, ax = plt.subplots(figsize=(4.2, 2.4))
x = np.arange(len(conds)); dx = 0.16
ax.errorbar(x - dx, [P[c][0] for c in conds], yerr=[P[c][1] for c in conds], fmt="o", color=SLATE, ms=4,
            capsize=2, lw=1, label="Proposer")
ax.errorbar(x + dx, [O[c][0] for c in conds], yerr=[O[c][1] for c in conds], fmt="s", color=TEAL, mfc="white",
            mew=1.2, ms=4, capsize=2, lw=1, label="Others")
ax.set_xticks(x); ax.set_xticklabels(conds)
ax.set_ylim(0, 1.0); ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_title("Non-challenge rate", loc="left", fontsize=8, pad=4)
ax.legend(frameon=False, loc="upper right", ncol=2, handletextpad=0.4, columnspacing=1.0)
save(fig, "fig_nonchallenge_rates")

# ---------------- Figure: verbal commitment ----------------
REPLY = [("C1", 2, 27), ("C1c", 11, 30), ("C1d", 27, 30)]  # X-only replies; C1 2/27 = 7.4% (summary.md)
fig, ax = plt.subplots(figsize=(2.6, 2.3))
xb = np.arange(len(REPLY)); shares = [k / n for _, k, n in REPLY]
err = np.array([[s - wilson(k, n)[0], wilson(k, n)[1] - s] for (_, k, n), s in zip(REPLY, shares)]).T
ax.errorbar(xb, shares, yerr=err, fmt="o", color=SLATE, ms=4, capsize=2, lw=1)
for xi, (c, k, n) in zip(xb, REPLY):
    ax.text(xi + 0.1, k / n, "%d/%d" % (k, n), fontsize=7, va="center", ha="left", color=GREY)
ax.set_xticks(xb); ax.set_xticklabels([c for c, _, _ in REPLY]); ax.set_xlim(-0.5, 2.7)
ax.set_ylim(0, 1.0); ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_title("Committed replies (seat after proposer)", loc="left", fontsize=8, pad=4)
save(fig, "fig_verbal_commitment")

# ---------------- Tables ----------------
tb = json.load(open(os.path.join(ROOT, "followup", "analysis_judged", "tests_B.json")))
RUN1 = [  # test, contrast, delta, lo, hi, p-text, note
    ("Gate", "C0 − C4", 0.569, 0.397, 0.740, "< .0001", "a"),
    ("HA1a", "C1 − C2", -0.089, -0.175, -0.003, ".228", "", True),
    ("HA1b", "C1 − C2", 0.400, 0.281, 0.519, ".0003", "b"),
    ("HA1c", "C1b − C1", 0.200, -0.038, 0.438, ".362", ""),
    ("HA2a", "(C1, C2) − C5", -0.197, -0.359, -0.034, ".074", ""),
    ("HA2b", "C1 − C2", -0.063, -0.224, 0.099, ".422", ""),
    ("HA2c", "C1b − C1", 0.326, 0.141, 0.512, ".009", "c"),
    ("HM", "messages − C4", -0.213, -0.288, -0.138, "< .0001", "a", True),
]
RUN2 = []
for h, con in [("HB1", "C1s g3 − C1"), ("HB2", "C1c − C1"), ("HB3", "C1ci − C1"), ("HB4", "C1d − C1")]:
    d = tb[h]["dR"]; RUN2.append((h, con, d["mean"], d["ci"][0], d["ci"][1], None, "d" if h == "HB4" else ""))
HOLM2 = {"HB1": ".379", "HB2": ".059", "HB3": ".889", "HB4": ".043"}
assert abs(RUN2[3][2] - 0.291) < 0.001 and abs(RUN2[1][2] - 0.122) < 0.001


def fmt(v):
    return ("+" if v > 0 else "−" if v < 0 else "") + "%.3f" % abs(v)


def table(rows, stem, holm, outcome_col, notes, width):
    cols = ["Test", "Contrast", outcome_col, "Δ", "95% CI", "Holm p"]
    xs = [0.00, 0.10, 0.28, 0.52, 0.64, 0.89]
    n = len(rows); rh = 0.17
    fig, ax = plt.subplots(figsize=(width, rh * (n + 2) + 0.15 + 0.17 * len(notes)))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    top = 0.98; y = top
    for cx, c in zip(xs, cols):
        ax.text(cx, y, c, fontsize=8, fontweight="bold", va="top", ha="left")
    dy = 0.80 / (n + 1)
    ax.plot([0, 1], [top + 0.03, top + 0.03], color="black", lw=1.0)
    ax.plot([0, 1], [top - dy * 0.75, top - dy * 0.75], color="black", lw=0.6)
    for i, row in enumerate(rows):
        t, con, d, lo, hi, p, note = row[:7]
        y = top - dy * (i + 1.3)
        if len(row) > 7 and row[7]:
            ax.plot([0, 1], [y + dy * 0.22, y + dy * 0.22], color="#888888", lw=0.5)
        ptxt = holm.get(t, p) if holm else p
        vals = [t + (("$^{%s}$" % note) if note else ""), con, OUTCOME[t], fmt(d), "[%s, %s]" % (fmt(lo), fmt(hi)), ptxt]
        for cx, v in zip(xs, vals):
            ax.text(cx, y, v, fontsize=8, va="top", ha="left")
    yb = top - dy * (n + 1.15)
    ax.plot([0, 1], [yb, yb], color="black", lw=1.0)
    for j, nt in enumerate(notes):
        ax.text(0, yb - 0.035 - j * 0.09, nt, fontsize=6.8, va="top", ha="left", color="#333333")
    save(fig, stem)


OUTCOME = {"Gate": "NC rate, proposer", "HA1a": "committed share", "HA1b": "wary share", "HA1c": "committed share (X)",
           "HA2a": "selectivity", "HA2b": "selectivity", "HA2c": "selectivity", "HM": "challenge, others",
           "HB1": "Δ NC rate, proposer", "HB2": "Δ NC rate, proposer", "HB3": "Δ NC rate, proposer", "HB4": "Δ NC rate, proposer"}
table(RUN1, "table_run1_results", None, "Outcome",
      ["a: manipulation check, uncorrected.   b: rejected in the direction opposite to the prediction.",
       "c: driven almost entirely by decisions on other players (proposer component +0.024, p = .79; other-player component −0.303).",
       "Gate and HM are pre-registered manipulation checks, not members of the Holm family (rule separates them)."],
      6.6)
table(RUN2, "table_run2_results", HOLM2, "Outcome",
      ["d: null rejected, but classified as general passivity under the pre-registered rule; the other-player comparison",
       "(+0.474) rests on only two contributing game numbers.",
       "Δ NC rate: seat after the proposer, change vs C1 of the same game number; Holm family of 4."],
      6.6)

KEY = [RUN1[0], RUN1[7], ("HA2a",) + RUN1[4][1:] + (True,), RUN1[6], ("HB2",) + RUN2[1][1:6] + ("", True), RUN2[3]]
HOLMK = dict(HOLM2)
table(KEY, "table_key_results", HOLMK, "Outcome",
      ["a: manipulation check, uncorrected.   c: driven almost entirely by decisions on other players (proposer component +0.024, p = .79).",
       "d: classified as general passivity under the pre-registered rule (other-player comparison rests on two game numbers).",
       "Rules separate checks, Family A (Holm, 6) and Family B (Holm, 4). Full tables in the appendix."],
      6.6)

# ---------------- Figure (optional): change vs direct offer ----------------
fig, ax = plt.subplots(figsize=(2.6, 2.3))
ax.axhline(0, color="#999999", lw=0.7)
for xi, h in zip([1, 2], ["HB2", "HB4"]):
    d = tb[h]["dR"]; m, lo, hi = d["mean"], d["ci"][0], d["ci"][1]
    ax.errorbar([xi], [m], yerr=[[m - lo], [hi - m]], fmt="o", color=SLATE, ms=4, capsize=2, lw=1)
ax.set_xticks([1, 2]); ax.set_xticklabels(["C1c", "C1d"]); ax.set_xlim(0.4, 2.6)
ax.set_ylim(-0.25, 0.6); ax.set_yticks([-0.2, 0, 0.2, 0.4, 0.6])
ax.set_title("Change in proposer non-challenge", loc="left", fontsize=8, pad=4)
save(fig, "fig_delta_nonchallenge")
print("done")
