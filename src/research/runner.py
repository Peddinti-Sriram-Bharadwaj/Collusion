"""Batch execution (backend-agnostic) and registration.

``execute`` runs units sequentially on an already-loaded model and hands each finished
result to a sink. Failures are recorded as status=failed records (never as default actions)
and do not stop the batch. ``register_results`` moves sink outputs into the registry,
skipping run_ids that are already completed (idempotent, resumable).
"""
from __future__ import annotations

import traceback
from time import perf_counter
from typing import Any, Callable, Iterable

from src.research import steering as S
from src.research.deviation import run_unit
from src.research.ids import UNKNOWN, git_state, host_info, utc_now
from src.research.prompts import TEMPLATES, template_hash
from src.research.registry import Registry

MODELS = {
    "0.5b": ("Qwen/Qwen2.5-0.5B-Instruct", "7ae557604adf67be50417f59c2c2f167def9a775"),
    "1.5b": ("Qwen/Qwen2.5-1.5B-Instruct", "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"),
    "3b": ("Qwen/Qwen2.5-3B-Instruct", "aa8e72537993ba99e69dfaafa59ed015b17504d1"),
    "7b": ("Qwen/Qwen2.5-7B-Instruct", "a09a35458c702b33eeacc393d103063234e8bc28"),
    "14b": ("Qwen/Qwen2.5-14B-Instruct", "cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8"),
    "32b": ("Qwen/Qwen2.5-32B-Instruct", "5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd"),
}


def run_id_for(batch_id: str, unit: dict) -> str:
    return f"{batch_id}--{unit['unit_id']}"


def execute(model, tok, units: Iterable[dict], *, batch: dict, model_meta: dict, sink: Callable[[dict, dict], None],
            skip: set[str] | None = None, vector_root=None, log: Callable[[str], None] | None = None) -> dict:
    skip = skip or set()
    n_done = n_fail = n_skip = 0
    hw = host_info()
    for i, unit in enumerate(units):
        rid = run_id_for(batch["batch_id"], unit)
        if rid in skip:
            n_skip += 1
            continue
        t0 = perf_counter()
        base = {"run_id": rid, "batch_id": batch["batch_id"], "experiment_id": batch.get("experiment_id", batch["protocol"]),
                "protocol_version": batch["protocol"], "designation": batch["designation"], "unit_id": unit["unit_id"],
                "block": unit.get("block"), "started_at": utc_now(), "config": unit, "git": batch.get("git") or git_state(),
                "model": {**model_meta, "backend": model_meta.get("backend", UNKNOWN), "hardware": hw},
                "prompt": {"template_id": unit["template_id"], "template_hash": template_hash(unit["template_id"])},
                "seeds": unit["seeds"], "history_id": f"h{unit['seeds']['history_seed']}-p{unit['prefix_rounds']}",
                "rival_policy_id": unit["condition"], "econ_id": unit["econ_id"]}
        try:
            vec, prov = S.resolve(unit["steering"], model_meta, vector_root)
            out = run_unit(model, tok, unit, vec)
            rec = {**base, "status": "completed", "steering": {**unit["steering"], "provenance": prov},
                   "summary": out["summary"], "validity": out["validity"], "runtime_seconds": perf_counter() - t0}
            payload = {"run_id": rid, "unit": unit, "rounds": out["rounds"], "benchmarks": out["benchmarks"],
                       "steering_provenance": prov}
            n_done += 1
        except Exception as exc:
            rec = {**base, "status": "failed", "error": f"{type(exc).__name__}: {exc}",
                   "traceback": traceback.format_exc()[-4000:], "runtime_seconds": perf_counter() - t0}
            payload = None
            n_fail += 1
        sink(rec, payload)
        if log:
            log(f"[{i + 1}] {rec['status']} {unit['experiment']}:{unit['condition']} steer={unit['steering']['kind']}"
                f"{unit['steering']['alpha']:+g} {rec.get('error', '')}")
    return {"completed": n_done, "failed": n_fail, "skipped": n_skip}


def register_results(reg: Registry, items: Iterable[tuple[dict, dict | None]]) -> dict:
    added = dup = 0
    done = reg.completed_ids()
    for rec, payload in items:
        if rec["status"] == "completed" and rec["run_id"] in done:
            dup += 1
            continue
        if payload is not None:
            rec["raw_path"], rec["raw_sha256"] = reg.write_raw(rec["batch_id"], rec["run_id"], payload)
        reg.register_run(rec)
        added += 1
        if rec["status"] == "completed":
            done.add(rec["run_id"])
    return {"added": added, "duplicates_skipped": dup}
