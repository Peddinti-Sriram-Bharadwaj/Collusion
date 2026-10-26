"""EXPLORATORY: judged reply category -> subsequent behaviour (implements reply_behaviour_PLAN.md, run once).

Not pre-registered, not confirmatory; no p-values. Reads main/analysis/challenges.csv, main/analysis/offers.csv,
main/judgements.csv (read-only); writes reply_behaviour_results.md and reply_behaviour_recipients.csv next to this
script. Run with Anaconda Python 3.12 (numpy 1.26.4, pandas 2.2.2, statsmodels 0.14.2):
    python -I reply_behaviour.py
"""
import hashlib
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

HERE = Path(__file__).resolve().parent
MAIN = HERE.parent
PLAN_SHA = "cadf940a2d1ca7a26bb39c2f7fb94a88b8fdc558fc751fb4d4c0bf66eefbf0ab"
PACT = ("C1", "C1b", "C2")
REF = ("C3", "C5")
CATS = ("committed", "suspicion-evasive", "rejection", "other")
B = 5000
SEED = 20261026
MIN_N, MIN_G = 5, 4


def truth(s):
    return s.astype(str) == "True"


# ----------------------------------------------------------------------------------------------- data
def load():
    ch = pd.read_csv(MAIN / "analysis" / "challenges.csv", dtype=str, keep_default_na=False)
    off = pd.read_csv(MAIN / "analysis" / "offers.csv", dtype=str, keep_default_na=False)
    jd = pd.read_csv(MAIN / "judgements.csv", dtype=str, keep_default_na=False)
    for d in (ch, off, jd):
        d["game_number"] = d["game_number"].astype(int)
    ch["round"] = ch["round"].astype(int)
    used = truth(ch["used"])
    cip = truth(ch["challenged_is_proposer"])
    elig = truth(ch["challenger_can_challenge_proposer"])
    ch["is_riley"] = used & cip & elig
    ch["is_other"] = used & ~cip & (ch["challenged"] != "Riley")
    ch["nc"] = ~truth(ch["was_challenged"])
    excluded_unflagged = int((used & cip & ~elig).sum())
    key = ["condition", "game_number", "challenger"]
    agg = pd.DataFrame({
        "nR": ch[ch.is_riley].groupby(key).size(),
        "ncR": ch[ch.is_riley].groupby(key)["nc"].sum(),
        "nO": ch[ch.is_other].groupby(key).size(),
        "ncO": ch[ch.is_other].groupby(key)["nc"].sum(),
    }).fillna(0).astype(int)
    agg.index = agg.index.set_names(["condition", "game_number", "agent"])
    agg = agg.reset_index()
    ever_elig = set(map(tuple, ch[truth(ch["post_offer"]) & elig][key].drop_duplicates().values))
    rec = jd[["condition", "game_number", "agent", "category"]].merge(
        off[["condition", "game_number", "agent", "model", "decision"]], on=["condition", "game_number", "agent"], how="left")
    rec = rec.merge(agg, on=["condition", "game_number", "agent"], how="left").fillna({"nR": 0, "ncR": 0, "nO": 0, "ncO": 0})
    c4 = agg[agg.condition == "C4"].rename(columns={"nR": "nR4", "ncR": "ncR4", "nO": "nO4", "ncO": "ncO4"}).drop(columns="condition")
    rec = rec.merge(c4, on=["game_number", "agent"], how="left").fillna({"nR4": 0, "ncR4": 0, "nO4": 0, "ncO4": 0})
    for c in ("nR", "ncR", "nO", "ncO", "nR4", "ncR4", "nO4", "ncO4"):
        rec[c] = rec[c].astype(int)
    rate = lambda k, n: np.where(rec[n] > 0, rec[k] / rec[n].where(rec[n] > 0, 1), np.nan)
    rec["R_T"], rec["R_C4"] = rate("ncR", "nR"), rate("ncR4", "nR4")
    rec["O_T"], rec["O_C4"] = rate("ncO", "nO"), rate("ncO4", "nO4")
    rec["dR"], rec["dO"] = rec.R_T - rec.R_C4, rec.O_T - rec.O_C4
    rec["sel_within"] = rec.R_T - rec.O_T
    rec["committed"] = (rec.category == "committed").astype(int)
    rec["accept"] = (rec.decision == "ACCEPT").astype(int)
    rec["ever_eligible"] = [(c, g, a) in ever_elig for c, g, a in zip(rec.condition, rec.game_number, rec.agent)]
    return ch, rec, excluded_unflagged


# ------------------------------------------------------------------------------------------ bootstrap
class Boot:
    """Cluster bootstrap over game numbers; one weight matrix per call, shared by all specs of a contrast."""

    def __init__(self, rng):
        self.rng = rng
        self.dropped = 0

    def means(self, specs):
        """specs: list of (values, games). Returns (B x len(specs)) array of resampled means (NaN = empty)."""
        universe = np.unique(np.concatenate([g for _, g in specs]))
        idx = {g: i for i, g in enumerate(universe)}
        W = np.zeros((B, len(universe)))
        draws = self.rng.integers(0, len(universe), size=(B, len(universe)))
        for b in range(B):
            W[b] = np.bincount(draws[b], minlength=len(universe))
        out = np.empty((B, len(specs)))
        for j, (v, g) in enumerate(specs):
            S, N = np.zeros(len(universe)), np.zeros(len(universe))
            np.add.at(S, [idx[x] for x in g], v)
            np.add.at(N, [idx[x] for x in g], 1)
            num, den = W @ S, W @ N
            with np.errstate(invalid="ignore", divide="ignore"):
                out[:, j] = np.where(den > 0, num / den, np.nan)
        return out

    def ci(self, samples):
        ok = ~np.isnan(samples)
        self.dropped += int((~ok).sum())
        if ok.sum() < 100:
            return (np.nan, np.nan)
        return tuple(np.percentile(samples[ok], [2.5, 97.5]))


def enough(df):
    return len(df) >= MIN_N and df.game_number.nunique() >= MIN_G


def fmt(x):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:+.3f}"


def fmt_ci(ci):
    return "too few" if ci is None else ("n/a" if np.isnan(ci[0]) else f"[{ci[0]:+.3f}, {ci[1]:+.3f}]")


# ------------------------------------------------------------------------------------------ analyses
def main():
    plan = HERE / "reply_behaviour_PLAN.md"
    if hashlib.sha256(plan.read_bytes()).hexdigest() != PLAN_SHA:
        sys.exit("plan file changed since it was hashed; not running")
    ch, rec, excl = load()
    rng = np.random.default_rng(SEED)
    bt = Boot(rng)
    L = ["# Exploratory results: judged reply category → subsequent behaviour", "",
         "**EXPLORATORY, not pre-registered, not confirmatory.** Plan: `reply_behaviour_PLAN.md` "
         f"(sha256 `{PLAN_SHA[:16]}…`, hashed before this script was written), run once. Bootstrap: {B} cluster "
         f"resamples over game numbers, seed {SEED}, 95% percentile intervals; no p-values. Disclosure: sprint work.", ""]
    pact = rec[rec.condition.isin(PACT)]
    rf = pact[pact.nR > 0]
    rfb = rf[rf.dR.notna()]

    # missing / undefined
    nor = pact[pact.nR == 0]
    L += ["## Sample and missing outcomes", "",
          f"- Judged recipient-games: {len(rec)} (pact {len(pact)}, C3 {sum(rec.condition == 'C3')}, C5 {sum(rec.condition == 'C5')}); "
          "1 unreadable C3 reply was not judged.",
          f"- Used Riley decisions without the eligibility flag, excluded: {excl}.",
          f"- Pact recipients with no Riley decision: {len(nor)} (never eligible after the offer: {int((~nor.ever_eligible).sum())}; "
          f"eligible but no used Riley decision: {int(nor.ever_eligible.sum())}).",
          f"- Pact Riley-facing recipients: {len(rf)}; of these with a C4 baseline on Riley plays: {len(rfb)} "
          f"(no baseline: {len(rf) - len(rfb)}).", ""]

    # E1
    L += ["## E1. Riley behaviour by reply category (pact conditions; Riley-facing recipients)", "",
          "R_T = non-challenge rate on Riley's plays; ΔR = R_T − the same agent's rate in C4 (same game number, same seat order).", "",
          "| category | recipients | game numbers | Riley decisions | mean R_T | 95% CI | with baseline | mean ΔR | 95% CI | share ΔR > 0 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    def e1_row(name, d):
        db = d[d.dR.notna()]
        ciR = bt.ci(bt.means([(d.R_T.values, d.game_number.values)])[:, 0]) if enough(d) else None
        ciD = bt.ci(bt.means([(db.dR.values, db.game_number.values)])[:, 0]) if enough(db) else None
        share = f"{(db.dR > 0).mean():.2f}" if len(db) else "n/a"
        return (f"| {name} | {len(d)} | {d.game_number.nunique()} | {int(d.nR.sum())} | {fmt(d.R_T.mean())} | {fmt_ci(ciR)} | "
                f"{len(db)} | {fmt(db.dR.mean())} | {fmt_ci(ciD)} | {share} |")
    for c in CATS:
        L.append(e1_row(c, rf[rf.category == c]))
    L.append(e1_row("non-committed (pooled)", rf[rf.category != "committed"]))
    for cond in REF:
        d = rec[(rec.condition == cond) & (rec.nR > 0)]
        for c in CATS:
            if (d.category == c).any():
                L.append(e1_row(f"reference {cond} {c}", d[d.category == c]))
    L += ["", "By category × model (descriptive; n = recipients, mean R_T / mean ΔR (n with baseline)):", "",
          "| category | llama-3.1-8b | llama-3.2-3b | qwen2.5-7b |", "|---|---|---|---|"]
    for c in CATS:
        cells = []
        for m in ("llama-3.1-8b", "llama-3.2-3b", "qwen2.5-7b"):
            d = rf[(rf.category == c) & (rf.model == m)]
            db = d[d.dR.notna()]
            cells.append(f"n={len(d)}: {fmt(d.R_T.mean()) if len(d) else 'n/a'} / {fmt(db.dR.mean()) if len(db) else 'n/a'} ({len(db)})")
        L.append(f"| {c} | " + " | ".join(cells) + " |")
    L += ["", "By category × condition (descriptive; same cell format):", "", "| category | C1 | C1b | C2 |", "|---|---|---|---|"]
    for c in CATS:
        cells = []
        for cond in PACT:
            d = rf[(rf.category == c) & (rf.condition == cond)]
            db = d[d.dR.notna()]
            cells.append(f"n={len(d)}: {fmt(d.R_T.mean()) if len(d) else 'n/a'} / {fmt(db.dR.mean()) if len(db) else 'n/a'} ({len(db)})")
        L.append(f"| {c} | " + " | ".join(cells) + " |")

    # E2
    def contrast(a, b, col):
        if not (enough(a) and enough(b)):
            return None, a[col].mean() - b[col].mean() if len(a) and len(b) else np.nan
        s = bt.means([(a[col].values, a.game_number.values), (b[col].values, b.game_number.values)])
        return bt.ci(s[:, 0] - s[:, 1]), a[col].mean() - b[col].mean()
    L += ["", "## E2. Committed vs non-committed; Riley-specific vs general", "",
          "(a) ΔR, committed − non-committed:", "", "| scope | committed n (games) | non-committed n (games) | difference | 95% CI |", "|---|---|---|---|---|"]
    for scope, d in (("pact pooled", rfb), ("C2 only", rfb[rfb.condition == "C2"]), ("C1b only", rfb[rfb.condition == "C1b"])):
        a, b = d[d.committed == 1], d[d.committed == 0]
        ci, diff = contrast(a, b, "dR")
        L.append(f"| {scope} | {len(a)} ({a.game_number.nunique()}) | {len(b)} ({b.game_number.nunique()}) | {fmt(diff)} | {fmt_ci(ci)} |")
    ob = pact[(pact.nO > 0) & pact.dO.notna()]
    L += ["", "(b) General passivity: ΔO = non-challenge rate on other LLM players' plays − the same agent's rate in C4 "
          "(pact recipients with other-player decisions and a C4 baseline):", "",
          "| category | recipients | game numbers | other-player decisions | mean ΔO | 95% CI |", "|---|---|---|---|---|---|"]
    groups = {c: ob[ob.category == c] for c in CATS}
    groups["non-committed (pooled)"] = ob[ob.category != "committed"]
    for name, d in groups.items():
        ci = bt.ci(bt.means([(d.dO.values, d.game_number.values)])[:, 0]) if enough(d) else None
        L.append(f"| {name} | {len(d)} | {d.game_number.nunique()} | {int(d.nO.sum())} | {fmt(d.dO.mean())} | {fmt_ci(ci)} |")
    L += ["", "(c) Riley-specific index = mean ΔR (Riley-facing, E1) − mean ΔO (other-judging, E2b); between-agent:", "",
          "| category | ΔR n | ΔO n | index | 95% CI |", "|---|---|---|---|---|"]
    def index_specs(cat_mask_r, cat_mask_o):
        r, o = rfb[cat_mask_r(rfb)], ob[cat_mask_o(ob)]
        return r, o
    masks = {c: (lambda d, c=c: d.category == c) for c in CATS}
    masks["non-committed (pooled)"] = lambda d: d.category != "committed"
    for name, m in masks.items():
        r, o = rfb[m(rfb)], ob[m(ob)]
        idx = r.dR.mean() - o.dO.mean() if len(r) and len(o) else np.nan
        if enough(r) and enough(o):
            s = bt.means([(r.dR.values, r.game_number.values), (o.dO.values, o.game_number.values)])
            ci = bt.ci(s[:, 0] - s[:, 1])
        else:
            ci = None
        L.append(f"| {name} | {len(r)} | {len(o)} | {fmt(idx)} | {fmt_ci(ci)} |")
    rc, oc = rfb[rfb.committed == 1], ob[ob.committed == 1]
    rn, on = rfb[rfb.committed == 0], ob[ob.committed == 0]
    if all(enough(x) for x in (rc, oc, rn, on)):
        s = bt.means([(rc.dR.values, rc.game_number.values), (oc.dO.values, oc.game_number.values),
                      (rn.dR.values, rn.game_number.values), (on.dO.values, on.game_number.values)])
        ci = bt.ci((s[:, 0] - s[:, 1]) - (s[:, 2] - s[:, 3]))
    else:
        ci = None
    dd = (rc.dR.mean() - oc.dO.mean()) - (rn.dR.mean() - on.dO.mean())
    L += ["", f"Index committed − index non-committed: {fmt(dd)} {fmt_ci(ci)}.", "",
          "(d) Within-agent selectivity R_T − O_T (descriptive only; mixes target and game phase):", "",
          "| category | recipients with both | mean |", "|---|---|---|"]
    for c in CATS:
        d = pact[(pact.category == c) & pact.sel_within.notna()]
        L.append(f"| {c} | {len(d)} | {fmt(d.sel_within.mean()) if len(d) else 'n/a'} |")

    # E3
    L += ["", "## E3. Preferential treatment despite wariness or refusal", "",
          "Rows repeated from E1/E2 for `suspicion-evasive` and `rejection`, next to `other` (pact) and the C3/C5 reference:", "",
          "| group | Riley-facing n | mean R_T | mean ΔR (n) | share ΔR > 0 | ΔO (n) | index |", "|---|---|---|---|---|---|---|"]
    def e3_row(name, r_all, o_all):
        rb = r_all[r_all.dR.notna()]
        return (f"| {name} | {len(r_all)} | {fmt(r_all.R_T.mean()) if len(r_all) else 'n/a'} | {fmt(rb.dR.mean()) if len(rb) else 'n/a'} ({len(rb)}) | "
                f"{f'{(rb.dR > 0).mean():.2f}' if len(rb) else 'n/a'} | {fmt(o_all.dO.mean()) if len(o_all) else 'n/a'} ({len(o_all)}) | "
                f"{fmt(rb.dR.mean() - o_all.dO.mean()) if len(rb) and len(o_all) else 'n/a'} |")
    for c in ("suspicion-evasive", "rejection", "other"):
        L.append(e3_row(f"pact {c}", rf[rf.category == c], ob[ob.category == c]))
    for cond in REF:
        d = rec[rec.condition == cond]
        L.append(e3_row(f"reference {cond} (all categories)", d[d.nR > 0], d[(d.nO > 0) & d.dO.notna()]))

    # E4
    L += ["", "## E4. ACCEPT/DECLINE label vs judged commitment (pact Riley-facing recipients with a C4 baseline; outcome ΔR)", "",
          "| cell | n | game numbers | mean ΔR | 95% CI |", "|---|---|---|---|---|"]
    cells = {"ACCEPT & committed": rfb[(rfb.accept == 1) & (rfb.committed == 1)],
             "ACCEPT & not committed": rfb[(rfb.accept == 1) & (rfb.committed == 0)],
             "DECLINE": rfb[rfb.accept == 0],
             "DECLINE & committed": rfb[(rfb.accept == 0) & (rfb.committed == 1)]}
    for name, d in cells.items():
        ci = bt.ci(bt.means([(d.dR.values, d.game_number.values)])[:, 0]) if enough(d) else None
        L.append(f"| {name} | {len(d)} | {d.game_number.nunique()} | {fmt(d.dR.mean()) if len(d) else 'n/a'} | {fmt_ci(ci) if len(d) else 'n/a'} |")
    c1b = rfb[rfb.condition == "C1b"]
    L += ["", "Within C1b (descriptive): " + "; ".join(
        f"{lab}: n={len(d)}, mean ΔR {fmt(d.dR.mean()) if len(d) else 'n/a'}"
        for lab, d in (("ACCEPT", c1b[c1b.accept == 1]), ("DECLINE", c1b[c1b.accept == 0]),
                       ("committed", c1b[c1b.committed == 1]), ("not committed", c1b[c1b.committed == 0]))), ""]
    forms = {"M0": "dR ~ C(condition) + C(model)", "M_label": "dR ~ C(condition) + C(model) + accept",
             "M_commit": "dR ~ C(condition) + C(model) + committed", "M_both": "dR ~ C(condition) + C(model) + accept + committed"}
    L += ["| model | coefficient(s), cluster-robust SE by game number | LOGO-CV MSE |", "|---|---|---|"]
    data = rfb[["dR", "condition", "model", "accept", "committed", "game_number"]].reset_index(drop=True)
    folds = sorted(data.game_number.unique())
    fold_mse = {}
    for name, f in forms.items():
        fit = smf.ols(f, data=data).fit(cov_type="cluster", cov_kwds={"groups": data.game_number})
        coefs = "; ".join(f"{k} {fit.params[k]:+.3f} (SE {fit.bse[k]:.3f})" for k in ("accept", "committed") if k in fit.params) or "–"
        se = []
        for g in folds:
            tr, te = data[data.game_number != g], data[data.game_number == g]
            m = smf.ols(f, data=tr).fit()
            se.append(((te.dR - m.predict(te)) ** 2).values)
        fold_mse[name] = np.array([s.mean() for s in se])
        L.append(f"| {name} | {coefs} | {np.concatenate(se).mean():.4f} |")
    diff = fold_mse["M_label"] - fold_mse["M_commit"]
    se_diff = diff.std(ddof=1) / np.sqrt(len(diff))
    verdict = ("indistinguishable" if abs(diff.mean()) < se_diff else
               ("M_commit lower" if diff.mean() > 0 else "M_label lower"))
    L += ["", f"Mean per-fold MSE difference M_label − M_commit = {diff.mean():+.4f}, SE across {len(diff)} folds {se_diff:.4f} "
          f"→ **{verdict}** (\"spread across folds\" operationalised as the standard error of the mean per-fold difference).", ""]

    # E5
    L += ["## E5. Decision-level sensitivity (GEE logistic, exchangeable, clusters = game number)", ""]
    keyset = set(map(tuple, rf[["condition", "game_number", "agent"]].values))
    dec = ch[ch.is_riley & ch.condition.isin(PACT)].copy()
    dec = dec[[k in keyset for k in zip(dec.condition, dec.game_number, dec.challenger)]]
    dec = dec.merge(rf[["condition", "game_number", "agent", "committed", "accept", "model"]],
                    left_on=["condition", "game_number", "challenger"], right_on=["condition", "game_number", "agent"])
    dec["y"] = dec.nc.astype(int)
    dec["bluff"] = truth(dec.proposer_bluffed).astype(int)
    dec["afb"] = (truth(dec.after_first_breach) & (dec.condition == "C1b")).astype(int)
    for term in ("committed", "accept"):
        f = f"y ~ {term} + C(model) + C(condition) + bluff + round + afb"
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                res = smf.gee(f, groups="game_number", data=dec, family=sm.families.Binomial(),
                              cov_struct=sm.cov_struct.Exchangeable()).fit()
            conv = [str(x.message) for x in w if "converge" in str(x.message).lower()]
            lo, hi = res.conf_int().loc[term]
            L.append(f"- {term}: OR {np.exp(res.params[term]):.2f} [{np.exp(lo):.2f}, {np.exp(hi):.2f}] "
                     f"({len(dec)} Riley decisions, {dec.game_number.nunique()} clusters)"
                     + (f"; convergence warning: {conv[0]}" if conv else ""))
        except Exception as e:  # reported, nothing substituted (plan E5)
            L.append(f"- {term}: model failed ({type(e).__name__}: {e}); nothing substituted")

    L += ["", "## Bookkeeping", "", f"- Bootstrap resamples dropped (an empty group in a resample): {bt.dropped}.",
          "- Deviations from the plan: none, except that the plan's \"spread across folds\" (E4) is made concrete as stated there.", "",
          "## Interpretation limits", "",
          "Category is not randomised (associations, not effects); model is confounded with category; judged categories carry "
          "judge error (38/40 on synthetic items, unknown on real replies); the E2c index compares different seats; opportunities "
          "depend on survival paths; the committed group is small.", ""]
    (HERE / "reply_behaviour_results.md").write_text("\n".join(L), encoding="utf-8")
    rec.to_csv(HERE / "reply_behaviour_recipients.csv", index=False)
    print("\n".join(L))


if __name__ == "__main__":
    main()
