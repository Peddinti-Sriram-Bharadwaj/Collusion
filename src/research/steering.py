"""Steering-vector registry with provenance, plus intervention hooks.

Vectors live in research/vectors/<vector_id>.npz with a sibling <vector_id>.json manifest
(model, revision, layer, site, template, construction, training histories, norm, sha256).
Random and sham interventions are generated on the fly and are norm-matched to a
reference vector so strengths are comparable across direction types.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.research.ids import sha256_file

VECTOR_DIR = Path(__file__).resolve().parents[2] / "research" / "vectors"


def list_vectors() -> list[str]:
    return sorted(p.stem for p in VECTOR_DIR.glob("*.npz"))


def load_vector(vector_id: str, root: Path | None = None) -> tuple[np.ndarray, dict]:
    root = root or VECTOR_DIR
    meta = json.loads((root / f"{vector_id}.json").read_text())
    arr = np.load(root / f"{vector_id}.npz")["vector"].astype(np.float32)
    if meta.get("sha256") and sha256_file(str(root / f"{vector_id}.npz")) != meta["sha256"]:
        raise ValueError(f"checksum mismatch for vector {vector_id}")
    return arr, meta


def save_vector(vector_id: str, vector: np.ndarray, meta: dict, root: Path | None = None) -> dict:
    root = root or VECTOR_DIR
    root.mkdir(parents=True, exist_ok=True)
    np.savez(root / f"{vector_id}.npz", vector=np.asarray(vector, dtype=np.float32))
    meta = {**meta, "vector_id": vector_id, "dim": int(np.asarray(vector).shape[-1]),
            "norm": float(np.linalg.norm(vector)), "sha256": sha256_file(str(root / f"{vector_id}.npz"))}
    (root / f"{vector_id}.json").write_text(json.dumps(meta, indent=1))
    return meta


def resolve(steering: dict, model_meta: dict, root: Path | None = None) -> tuple[np.ndarray | None, dict]:
    """Return (vector to add, provenance) for a steering config; None for no intervention."""
    kind = steering["kind"]
    if kind == "none":
        return None, {"kind": "none"}
    ref_id = steering.get("vector_id") or steering.get("reference_vector_id")
    ref, ref_meta = load_vector(ref_id, root) if ref_id else (None, {})
    if ref_meta:
        for key in ("layer", "site"):
            if ref_meta.get(key) is not None and ref_meta[key] != steering[key]:
                raise ValueError(f"steering {key}={steering[key]} does not match vector {ref_id} ({ref_meta[key]})")
        if model_meta.get("d_model") and ref_meta["dim"] != model_meta["d_model"]:
            raise ValueError(f"vector dim {ref_meta['dim']} != model d_model {model_meta['d_model']}")
        if ref_meta.get("model_key") and model_meta.get("model_key") and ref_meta["model_key"] != model_meta["model_key"]:
            raise ValueError(f"vector {ref_id} was built for {ref_meta['model_key']}, not {model_meta['model_key']}")
    if kind == "sham":
        dim = model_meta.get("d_model") or (ref.shape[0] if ref is not None else None)
        return np.zeros(dim, dtype=np.float32), {"kind": "sham", "note": "hook active, zero vector"}
    if kind in ("learned", "generic_price"):
        return ref, {"kind": kind, **ref_meta}
    if kind == "random":
        if ref is None:
            raise ValueError("random steering needs reference_vector_id/vector_id for norm matching")
        g = np.random.default_rng(int(steering.get("random_seed", 0)))
        v = g.standard_normal(ref.shape[0]).astype(np.float32)
        v = v / np.linalg.norm(v) * np.linalg.norm(ref)
        return v, {"kind": "random", "random_seed": int(steering.get("random_seed", 0)), "norm_matched_to": ref_id,
                   "norm": float(np.linalg.norm(v))}
    raise ValueError(kind)


def add_at(position: int, vector: torch.Tensor):
    """Forward hook body: add ``vector`` at absolute ``position`` (skips cached decode steps)."""
    def fn(h):
        if h.shape[1] <= position:
            return None
        h = h.clone()
        h[0, position, :] += vector.to(h.dtype).to(h.device)
        return h
    return fn
