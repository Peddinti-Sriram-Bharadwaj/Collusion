"""Import pre-registry experiments as *legacy* evidence (read-only; originals untouched).

Each legacy record points at the original artifact (path + sha256) and carries a compact
summary. Fields the artifact does not contain are recorded as "unknown". Legacy records
live in research/registry/legacy.jsonl and are never pooled with new protocol runs.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.research.ids import UNKNOWN, sha256_file

ART = Path(__file__).resolve().parents[2] / "artifacts" / "interpretability"


def _model(d: dict) -> tuple[str, str]:
    m = d.get("model") or {}
    return m.get("model_id", UNKNOWN), m.get("revision") or m.get("requested_model_revision") or UNKNOWN


def _a1(d):
    s = d.get("summary", {})
    return {"greedy_strict_valid": s.get("greedy_strict_valid"), "greedy_matches_digit_argmax": s.get("greedy_matches_digit_argmax"),
            "delta_expected_index_vs_control": s.get("delta_expected_index_vs_control")}


def _b2(d):
    rows = d.get("rows", [])
    v = [r for r in rows if r.get("template") == "v1" and r.get("horizon") == "final"]
    return {"n_rows": len(rows), "mean_E_v1_final": float(np.mean([r["expected_index"] for r in v])) if v else None}


def _d1(d):
    out = {}
    for g in d.get("games", []):
        if g.get("condition") != "none":
            continue
        out.setdefault(g["strategy"], []).append(g["collusion_index_joint"])
    return {"collusion_index_joint_mean_by_strategy": {k: float(np.mean(v)) for k, v in out.items()}}


SOURCES = [
    # glob, experiment type, summariser, protocol note
    ("runs/a1_*.json", "rival_price_edits_phase_a1", _a1, "Phase A.1: 24 histories x (control, nonce, cut/raise x stale/realistic); digit scoring + greedy strict parse"),
    ("runs/b2_*.json", "preregistered_fresh_history_b2", _b2, "B2 trend-break test (docs/prereg_deviation_b2.md)"),
    ("runs/d1_*.json", "repeated_games_d1", _d1, "15-round games vs 8 scripted/reactive rivals, greedy + 4 sampled"),
    ("runs/c3d_7b.json", "steering_transfer_and_steered_games", None, "C3 transfer vector + steered games (7B)"),
    ("runs/d1steer_7b_random.json", "steered_games_random_control", _d1, "games steered with a norm-matched random vector"),
    ("phase_c/c1_7b.json", "activation_patching_layers", None, "patching rival/profit/answer sites by layer"),
    ("phase_c/c1pos_7b.json", "activation_patching_positions", None, "single-position patching, layers 16/18/20"),
    ("phase_c/c2_7b_*.json", "steering_dose_response_mean_difference", None, "mean-difference steering on A.1 controls"),
    ("phase_b/qwen7b_b1.json", "probing_dataset_b1", None, "B1 activations (360 prompts) for probes"),
    ("phase_b2/b2_confirm_7b.json", "preregistered_fresh_history_b2", _b2, "B2 (7B, original location)"),
    ("phase_a_preflight/phase_a_economic_preflight.json", "economic_preflight", None, "CPU best-response analysis of Phase A"),
    ("cpu_0_5b/*.json", "cpu_dev_runs_0_5b", None, "Qwen2.5-0.5B CPU development runs"),
]


def collect(art: Path = ART) -> list[dict]:
    recs = []
    for pattern, etype, fn, note in SOURCES:
        for p in sorted(art.glob(pattern)):
            try:
                d = json.loads(p.read_text())
            except Exception as exc:
                recs.append({"legacy_id": f"legacy:{p.relative_to(art)}", "source_path": str(p.relative_to(art.parents[1])),
                             "experiment_type": etype, "status": "unreadable", "error": str(exc)})
                continue
            mid, rev = _model(d)
            ex = d.get("execution", {}) if isinstance(d, dict) else {}
            recs.append({
                "legacy_id": f"legacy:{p.relative_to(art)}", "source_path": str(p.relative_to(art.parents[1])),
                "source_sha256": sha256_file(str(p)), "experiment_type": etype, "protocol_note": note,
                "model_id": mid, "revision": rev, "backend": ex.get("backend", UNKNOWN), "hardware": ex.get("device") or ex.get("gpu") or UNKNOWN,
                "status": ex.get("status", UNKNOWN), "seeds": d.get("seed", UNKNOWN) if isinstance(d, dict) else UNKNOWN,
                "git": (ex.get("git") or UNKNOWN), "raw_responses_available": bool(any("raw_response" in r for r in d.get("rows", [])[:3])) if isinstance(d, dict) and isinstance(d.get("rows"), list) else UNKNOWN,
                "summary": fn(d) if fn else None,
                "comparability": "legacy protocol; not pooled with strategic_deviation_v1 runs",
            })
    return recs
