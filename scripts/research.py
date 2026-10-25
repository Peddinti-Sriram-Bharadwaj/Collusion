"""Research workflow CLI (see docs/experiment_tracking.md).

  python scripts/research.py plan    --spec research/configs/<batch>.json
  python scripts/research.py launch  --spec research/configs/<batch>.json      # Modal, detached
  python scripts/research.py sync    --batch <batch_id>                        # Modal volume -> registry
  python scripts/research.py run-local --spec ... [--model-dir path]           # CPU/local GPU, writes registry
  python scripts/research.py analyze                                           # tables, grid, figures, report
  python scripts/research.py legacy-import
  python scripts/research.py verify
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.research.configs import estimate, expand, load_spec  # noqa: E402
from src.research.ids import git_state, sha256_file, short_hash  # noqa: E402
from src.research.registry import Registry  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "research" / "outputs"
# Throughput measured on Modal A10 / Qwen2.5-7B fp16 (Phase A.1/C runs, 2026-10-25); re-measured by every batch.
SEC_PER_PASS = {"0.5b": 0.03, "1.5b": 0.04, "3b": 0.06, "7b": 0.09, "14b": 0.12, "32b": 0.25}
SEC_PER_GEN = {"0.5b": 0.4, "1.5b": 0.5, "3b": 0.7, "7b": 1.2, "14b": 1.6, "32b": 3.0}
USD_PER_HOUR = {"A10": 1.10, "A100-80GB": 2.50}  # check https://modal.com/pricing before large runs


def cmd_plan(a):
    spec = load_spec(a.spec); units = expand(spec); est = estimate(units)
    m = spec["model"]; gpu = "A100-80GB" if m in ("14b", "32b") else "A10"
    secs = est["forward_passes"] * SEC_PER_PASS[m] + est["generations"] * SEC_PER_GEN[m] + 120
    blocks = {}
    for u in units:
        blocks[u["block"]] = blocks.get(u["block"], 0) + 1
    print(json.dumps({"batch_id": spec["batch_id"], "designation": spec["designation"], "model": m, "gpu": gpu, **est,
                      "blocks": blocks, "est_gpu_hours": round(secs / 3600, 3),
                      "est_cost_usd": round(secs / 3600 * USD_PER_HOUR[gpu], 2)}, indent=1))


def cmd_launch(a):
    spec = load_spec(a.spec)
    reg = Registry()
    out = subprocess.run(["modal", "run", "--detach", "scripts/modal_research.py", "--spec", a.spec],
                         capture_output=True, text=True, timeout=170)
    line = next((l for l in out.stdout.splitlines() if l.startswith("{") and "spawned" in l), None)
    reg.register_batch_event({"event": "launch", "batch_id": spec["batch_id"], "spec_path": a.spec,
                              "spec_sha256": sha256_file(a.spec), "git": git_state(), "modal": json.loads(line) if line else
                              {"error": out.stderr[-2000:]}})
    print(line or out.stderr[-2000:])


def cmd_sync(a):
    from src.research.runner import register_results
    reg = Registry()
    tmp = Path(tempfile.mkdtemp())
    r = subprocess.run(["modal", "volume", "get", "--force", "collusion-latent-results", f"research/{a.batch}", str(tmp)],
                       capture_output=True, text=True, timeout=170)
    files = sorted(tmp.rglob("*.json"))
    items = []
    done_info = None
    for f in files:
        if f.name == "_batch_done.json":
            done_info = json.loads(f.read_text()); continue
        d = json.loads(f.read_text()); items.append((d["record"], d["payload"]))
    res = register_results(reg, items)
    reg.register_batch_event({"event": "sync", "batch_id": a.batch, "files": len(files), **res, "batch_done": done_info})
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({**res, "files": len(files), "batch_done": done_info, "modal_stderr": r.stderr[-500:] if r.returncode else ""}))


def cmd_run_local(a):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from src.research.runner import MODELS, execute, register_results
    spec = load_spec(a.spec); units = expand(spec); reg = Registry()
    mid, rev = MODELS[spec["model"]]
    tok = AutoTokenizer.from_pretrained(a.model_dir or mid, revision=None if a.model_dir else rev)
    model = AutoModelForCausalLM.from_pretrained(a.model_dir or mid, revision=None if a.model_dir else rev, torch_dtype=torch.float32).eval()
    meta = {"model_key": spec["model"], "model_id": mid, "revision": rev, "d_model": model.config.hidden_size,
            "n_layers": model.config.num_hidden_layers, "backend": "local-cpu-hf-transformers"}
    items = []
    batch = {"batch_id": spec["batch_id"], "protocol": spec["protocol"], "designation": spec["designation"], "git": git_state()}
    stats = execute(model, tok, units, batch=batch, model_meta=meta, sink=lambda r, p: items.append((r, p)),
                    skip=reg.completed_ids(), log=print)
    print(stats, register_results(reg, items))


def cmd_analyze(a):
    from src.research import analysis as A, legacy, plots, report
    reg = Registry()
    reg.register_legacy(legacy.collect())
    recs = reg.records(); leg = reg.records("legacy")
    rhash = short_hash([(r["run_id"], r["status"], r.get("raw_sha256")) for r in recs], 16)
    tables = A.build_tables(reg, OUT)
    grid = A.behaviour_grid(tables) if not tables["units"].empty else __import__("pandas").DataFrame(
        columns=["behaviour", "view", "level", "status", "mean", "ci_low", "ci_high", "n_clusters", "replication_status", "description", "evidence_runs"])
    paths = A.write_tables(tables, grid, OUT)
    (OUT / "tables" / "behaviour_grid.json").write_text(grid.to_json(orient="records", indent=1))
    manifest = plots.make_all(tables, grid, [r for r in recs if r.get("protocol_version") == A.PROTOCOL], OUT, rhash,
                              formats=tuple(a.formats.split(",")))
    rp = report.write_report(OUT, [r for r in recs if r.get("protocol_version") == A.PROTOCOL], leg, tables, grid, manifest, rhash)
    print(json.dumps({"registry_hash": rhash, "tables": list(paths), "figures": sum(1 for m in manifest if not m.get("skipped")),
                      "skipped": [m["figure"] for m in manifest if m.get("skipped")], "report": str(rp)}, indent=1))


def cmd_legacy(a):
    from src.research import legacy
    print(Registry().register_legacy(legacy.collect()), "new legacy records")


def cmd_verify(a):
    print(json.dumps(Registry().verify(), indent=1))


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("plan", cmd_plan), ("launch", cmd_launch), ("run-local", cmd_run_local)):
        p = sub.add_parser(name); p.add_argument("--spec", required=True); p.set_defaults(fn=fn)
        if name == "run-local":
            p.add_argument("--model-dir")
    p = sub.add_parser("sync"); p.add_argument("--batch", required=True); p.set_defaults(fn=cmd_sync)
    p = sub.add_parser("analyze"); p.add_argument("--formats", default="png,svg,pdf"); p.set_defaults(fn=cmd_analyze)
    sub.add_parser("legacy-import").set_defaults(fn=cmd_legacy)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
