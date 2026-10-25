"""Consolidated research report (markdown), regenerated from registry, tables and figure manifest."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.research.ids import utc_now


def md_table(df: pd.DataFrame, nd: int = 2) -> str:
    """Markdown table without optional dependencies."""
    cols = list(df.columns)
    def cell(v):
        if isinstance(v, float):
            return "-" if pd.isna(v) else f"{v:.{nd}f}"
        return str(v).replace("|", "/")
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(cell(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(out)


def _n(x) -> int:
    return 0 if x is None or (isinstance(x, float) and pd.isna(x)) else int(x)


def _fmt(x, nd=2):
    return "-" if x is None or (isinstance(x, float) and pd.isna(x)) else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def write_report(out_dir: Path, records: list, legacy: list, tables: dict, grid: pd.DataFrame, manifest: list,
                 registry_hash: str, budget_note: str = "") -> Path:
    runs = pd.DataFrame([{"batch": r["batch_id"], "status": r["status"], "designation": r.get("designation"),
                          "model": (r.get("model") or {}).get("model_key"), "seconds": r.get("runtime_seconds") or 0,
                          "n_dec": (r.get("validity") or {}).get("n_decisions") or 0} for r in records])
    ov = grid[grid.view == "overall"] if not grid.empty else grid
    L = [f"# Strategic pricing research: consolidated report", "",
         f"_Auto-generated {utc_now()} from the registry (hash `{registry_hash}`). Do not edit by hand; run "
         f"`python scripts/research.py analyze`._", ""]
    # 1 executive summary
    L += ["## 1. Executive summary", ""]
    if ov.empty:
        L += ["No protocol runs registered yet.", ""]
    else:
        sup = ov[ov.status == "supported"]; neg = ov[ov.status.isin(["absent", "opposite"])]
        inc = ov[ov.status.isin(["inconclusive", "insufficient", "untested"])]
        L += ["Evidence below is from the strategic-deviation protocol only (legacy results are listed separately).", ""]
        L += ["**Supported (overall 95% CI excludes zero in the predicted direction, or within the equivalence margin for null predictions):**", ""]
        L += [f"- {r.behaviour}: {_fmt(r['mean'])} [{_fmt(r.ci_low)}, {_fmt(r.ci_high)}], {_n(r.n_clusters)} independent histories; replication across tested settings: {r.replication_status}." for _, r in sup.iterrows()] or ["- none"]
        L += ["", "**Absent or opposite to prediction:**", ""]
        L += [f"- {r.behaviour}: {_fmt(r['mean'])} [{_fmt(r.ci_low)}, {_fmt(r.ci_high)}] ({r.status})." for _, r in neg.iterrows()] or ["- none"]
        L += ["", "**Unresolved (inconclusive, insufficient data, or not yet tested):**", ""]
        L += [f"- {r.behaviour}: {r.status}." for _, r in inc.iterrows()] or ["- none"]
        L += [""]
    # 1b hypotheses
    hyp = tables.get("hypotheses")
    L += ["## 1b. Pre-registered hypotheses H1-H5 (confirmatory batch only)", ""]
    if hyp is not None and not hyp.empty and hyp["n_clusters"].fillna(0).sum() > 0:
        cols = ["hypothesis", "name", "predicted", "mean", "ci_low", "ci_high", "n_clusters", "p_two_sided", "p_holm",
                "validity_rate", "status", "verdict"]
        L += [md_table(hyp[[c for c in cols if c in hyp]], 3), "",
              "Estimators: research/protocols/strategic_deviation_v1.md (amendment A1) and src/research/hypotheses.py. "
              "n = independent pre-play histories. 'absent' requires the whole CI inside +-0.25 steps; a non-significant "
              "estimate with a wider CI is 'inconclusive', never 'absent'.", ""]
        if "learned_level" in hyp:
            h4 = hyp[hyp.hypothesis == "H4"].iloc[0]
            L += [f"H4 components: learned level shift {_fmt(h4.get('learned_level'))}, random {_fmt(h4.get('random_level'))}, "
                  f"generic price direction {_fmt(h4.get('generic_level'))}, learned minus generic {_fmt(h4.get('learned_minus_generic'))}.", ""]
    else:
        L += ["No confirmatory batch registered yet.", ""]
    hb = tables.get("hypotheses_by_batch")
    if hb is not None and not hb.empty:
        L += ["Same estimators per batch (exploratory and smoke batches are descriptive only):", "",
              md_table(hb[["batch_id", "hypothesis", "mean", "ci_low", "ci_high", "n_clusters", "status"]], 3), ""]
    # 2 inventory
    L += ["## 2. Experiment inventory", ""]
    if runs.empty:
        L += ["No runs.", ""]
    else:
        inv = runs.groupby(["batch", "designation", "status"]).agg(units=("status", "size"), decisions=("n_dec", "sum"),
                                                                   gpu_seconds=("seconds", "sum")).reset_index()
        L += [md_table(inv), "", f"Total completed units: {int((runs.status == 'completed').sum())}; failed: "
              f"{int((runs.status == 'failed').sum())}; model decisions: {int(runs.n_dec.sum())}; summed unit runtime: "
              f"{runs.seconds.sum() / 3600:.2f} h. {budget_note}", ""]
    L += [f"Legacy (pre-registry) records: {len(legacy)} (see research/registry/legacy.jsonl).", ""]
    # 2b validity / repeatability / compute
    L += ["## 2b. Validity, repeatability and compute", ""]
    u0 = tables.get("units")
    if u0 is not None and not u0.empty:
        v = u0.groupby("batch_id")[["free_audits", "free_valid", "free_agree", "prefixed_audits", "prefixed_valid", "prefixed_agree"]].sum(min_count=1)
        v["free_valid_rate"] = v.free_valid / v.free_audits; v["prefixed_valid_rate"] = v.prefixed_valid / v.prefixed_audits
        v["greedy_agreement"] = v.free_agree / v.free_audits
        L += [md_table(v.reset_index()[["batch_id", "free_audits", "free_valid_rate", "greedy_agreement", "prefixed_audits", "prefixed_valid_rate"]], 3), "",
              f"Minimum digit probability mass over all decisions: {u0.min_digit_mass.min():.4f}.", ""]
    rep = tables.get("repeatability")
    if rep is not None and not rep.empty:
        L += [f"Repeatability: {len(rep)} identical reruns; max |dE| = {rep.max_abs_dE.max():.2e}; actions identical in "
              f"{int(rep.actions_identical.sum())}/{len(rep)}.", ""]
    comp = out_dir.parent / "registry" / "compute.jsonl"
    if comp.exists():
        cr = pd.DataFrame([json.loads(l) for l in comp.read_text().splitlines() if l.strip()])
        L += ["Compute and cost (Modal billing report per app where available; otherwise GPU-seconds x list price):", "",
              md_table(cr, 3), ""]
    # 3 coverage
    L += ["## 3. Parameter coverage", ""]
    u = tables.get("units")
    if u is not None and not u.empty:
        for col in ("model", "template_id", "temperature", "deviation_magnitude", "prefix_rounds", "recovery_delay", "econ_id", "steering", "alpha"):
            if col in u:
                L += [f"- **{col}**: " + ", ".join(f"{k} ({v})" for k, v in u[col].value_counts().sort_index().items())]
        L += ["", "Untested dimensions are listed in research/protocols/robustness_grid_v1.md (planned stages C-E).", ""]
    # 4 consistency
    L += ["## 4. Behavioural consistency", ""]
    if not ov.empty:
        cols = ["behaviour", "predicted", "mean", "ci_low", "ci_high", "n_clusters", "status", "replication_status", "validity_rate"]
        L += [md_table(ov[[c for c in cols if c in ov]]), "",
              "Full grid with every factor view: research/outputs/tables/behaviour_cells.csv.", ""]
    dims = tables.get("consistency_by_dimension")
    if dims is not None and not dims.empty:
        d2 = dims[dims.status != "untested"]
        if not d2.empty:
            L += ["### Consistency by parameter dimension", "",
                  md_table(d2[[c for c in ["behaviour", "dimension", "status", "n_levels", "n_supported", "n_opposite", "n_absent",
                                           "n_inconclusive", "n_insufficient", "sign_agreement", "level_mean_min", "level_mean_max", "level_mean_sd"] if c in d2]], 2),
                  "", "Labels: robust (>=80% of levels supported, none opposite), mixed, not replicated (>50% absent/opposite), "
                  "inconclusive, insufficient evidence; cross_history uses sign agreement of per-history estimates (>=0.8 robust).", ""]
    # 5/6 deviation + steering
    for title, names in (("## 5. Strategic-deviation results", ["punishment_like_reduction", "persistent_deviation_response",
                                                                 "recovery_after_return", "raise_response", "unexpected_deviation_sensitivity",
                                                                 "absolute_price_response", "rival_price_responsiveness"]),
                         ("## 6. Activation-steering results", ["steering_price_level", "steering_generic_level", "steering_random_level",
                                                                "steering_sham", "steering_x_deviation", "steering_x_persistent",
                                                                "steering_x_recovery", "random_x_deviation"])):
        L += [title, ""]
        sub = ov[ov.behaviour.isin(names)] if not ov.empty else ov
        for _, r in sub.iterrows():
            L += [f"- **{r.behaviour}** ({r.description}): {_fmt(r['mean'])} [{_fmt(r.ci_low)}, {_fmt(r.ci_high)}], "
                  f"n={_n(r.n_clusters)} histories -> {r.status}."]
        if title.startswith("## 6"):
            L += ["", "Interpretation rule (pre-registered): a steering direction that shifts price level but leaves the DiD "
                  "deviation-response terms at zero is classified as a generic price-level effect, not control over a "
                  "strategic mechanism."]
        L += [""]
    # 7 robustness
    L += ["## 7. Robustness analysis", ""]
    if not grid.empty:
        rv = grid[~grid.view.isin(["overall", "history_cluster", "batch_id"])]
        for view, g in rv.groupby("view"):
            L += [f"**{view}**", "", md_table(g[["behaviour", "level", "mean", "ci_low", "ci_high", "n_clusters", "status"]]), ""]
    # 8 figures
    L += ["## 8. Figures", ""]
    for m in manifest:
        if m.get("skipped"):
            L += [f"- {m['figure']}: not generated ({m['skipped']})"]
        else:
            L += [f"### {m['figure']}", "", f"![{m['figure']}](figures/{m['files'][0]})", "",
                  f"{m['caption']} Source: `{m['code']}`, tables {', '.join(m['tables'])}, {m['n_source_runs']} runs "
                  f"(hash `{m['source_runs_hash']}`).", ""]
    # 9 limitations
    L += ["## 9. Limitations and interpretation", "",
          "Evidence ladder used throughout: observed behaviour -> statistical evidence (CI over independent histories) -> "
          "causal interpretation (only for matched manipulations and steering contrasts against sham/random/generic "
          "controls) -> collusion-related implications (none follow directly from scripted-rival experiments).", "",
          "- **High prices** and **supra-competitive outcomes** (collusion index > 0) describe outcomes, not mechanisms; a model "
          "with a fixed high-price default produces them against any rival.",
          "- **Strategic conditioning** requires a response that depends on the rival's behaviour beyond its current price level "
          "(e.g. sudden vs gradual histories ending at the same price, condition H).",
          "- **Punishment-like behaviour** is a matched price reduction after a rival undercut; it is not evidence of intent, and "
          "a myopic best-responder also lowers its price after an undercut.",
          "- **Coordination** would require mutual conditioning sustaining prices above competitive levels; scripted rivals "
          "cannot establish it. **Intentional collusion** is not testable with these experiments.",
          "- Actions are read from the digit distribution after a forced answer prefix; strict-parse audits of free and "
          "prefixed generations are reported per batch and never substituted for missing actions.",
          "- Greedy decoding is deterministic: replication units are distinct histories (history_seed), not model seeds.", ""]
    # 10 next
    L += ["## 10. Next experiments", ""]
    gaps = ov[ov.status.isin(["insufficient", "inconclusive", "untested"])].behaviour.tolist() if not ov.empty else []
    L += [f"- Resolve: {', '.join(gaps)}." if gaps else "- Run stage C one-factor sweeps and stage E held-out confirmation.",
          "- See research/protocols/robustness_grid_v1.md for the staged plan and cost estimates.", ""]
    L += ["## Legacy evidence (pre-registry, separate protocols)", ""]
    for r in legacy:
        L += [f"- `{r['legacy_id']}` ({r['experiment_type']}; model {r.get('model_id', 'unknown')}; revision "
              f"{str(r.get('revision', 'unknown'))[:10]}): {r.get('protocol_note', '')}"]
    p = out_dir / "report.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p
