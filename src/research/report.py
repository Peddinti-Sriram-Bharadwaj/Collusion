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
        inc = ov[ov.status.isin(["inconclusive", "insufficient", "not tested"])]
        L += ["Evidence below is from the strategic-deviation protocol only (legacy results are listed separately).", ""]
        L += ["**Supported (overall 95% CI excludes zero in the predicted direction, or within the equivalence margin for null predictions):**", ""]
        L += [f"- {r.behaviour}: {_fmt(r['mean'])} [{_fmt(r.ci_low)}, {_fmt(r.ci_high)}], {_n(r.n_clusters)} independent histories; replication across tested settings: {r.replication_status}." for _, r in sup.iterrows()] or ["- none"]
        L += ["", "**Absent or opposite to prediction:**", ""]
        L += [f"- {r.behaviour}: {_fmt(r['mean'])} [{_fmt(r.ci_low)}, {_fmt(r.ci_high)}] ({r.status})." for _, r in neg.iterrows()] or ["- none"]
        L += ["", "**Unresolved (inconclusive, insufficient data, or not yet tested):**", ""]
        L += [f"- {r.behaviour}: {r.status}." for _, r in inc.iterrows()] or ["- none"]
        L += [""]
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
        rv = grid[grid.view != "overall"]
        for view, g in rv.groupby("view"):
            L += [f"**{view}**: " + "; ".join(f"{b}: " + ", ".join(f"{lv}={st}" for lv, st in zip(gg.level, gg.status))
                                             for b, gg in g.groupby("behaviour")), ""]
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
    gaps = ov[ov.status.isin(["insufficient", "inconclusive", "not tested"])].behaviour.tolist() if not ov.empty else []
    L += [f"- Resolve: {', '.join(gaps)}." if gaps else "- Run stage C one-factor sweeps and stage E held-out confirmation.",
          "- See research/protocols/robustness_grid_v1.md for the staged plan and cost estimates.", ""]
    L += ["## Legacy evidence (pre-registry, separate protocols)", ""]
    for r in legacy:
        L += [f"- `{r['legacy_id']}` ({r['experiment_type']}; model {r.get('model_id', 'unknown')}; revision "
              f"{str(r.get('revision', 'unknown'))[:10]}): {r.get('protocol_note', '')}"]
    p = out_dir / "report.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p
