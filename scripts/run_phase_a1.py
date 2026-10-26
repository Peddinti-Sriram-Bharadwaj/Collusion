"""Run Phase A.1 locally (CPU or local GPU) on a pinned HF model.

Example (CPU dry run on the 0.5B model):
  python scripts/run_phase_a1.py --model Qwen/Qwen2.5-0.5B-Instruct \
      --revision 7ae557604adf67be50417f59c2c2f167def9a775 \
      --output artifacts/interpretability/phase_a1/qwen0_5b.json
"""
from __future__ import annotations

import argparse, json, platform, subprocess, sys
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.interpretability.activation_extractor import HFActivationExtractor  # noqa: E402
from src.interpretability.phase_a1 import run_phase_a1  # noqa: E402


def git_state() -> dict:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
        return {"commit": commit, "dirty_worktree": dirty}
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-generate", action="store_true")
    ap.add_argument("--no-capture", action="store_true")
    ap.add_argument("--dtype", default="float32", choices=["float32", "float16", "bfloat16"])
    args = ap.parse_args()
    torch.set_num_threads(max(1, torch.get_num_threads()))
    t0 = perf_counter()
    ext = HFActivationExtractor.from_pretrained(args.model, revision=args.revision, device_map=None,
                                                torch_dtype=getattr(torch, args.dtype))
    load_s = perf_counter() - t0
    result, arrays = run_phase_a1(ext.model, ext.tokenizer, generate=not args.no_generate,
                                  capture=not args.no_capture, limit=args.limit,
                                  log=lambda m: print(m, flush=True))
    result["model"] = {"model_id": args.model, "revision": args.revision, "dtype": args.dtype,
                       "n_layers": ext.model.config.num_hidden_layers, "d_model": ext.model.config.hidden_size}
    result["execution"] = {"backend": "local", "device": str(ext.model.device), "platform": platform.platform(),
                           "torch": torch.__version__, "load_seconds": load_s,
                           "wall_clock_seconds": perf_counter() - t0, "git": git_state()}
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    if arrays:
        np.savez_compressed(out.with_suffix(".activations.npz"), row_ids=np.array([r["row_id"] for r in result["rows"]]), **arrays)
    print(json.dumps({"summary": result["summary"], "execution": result["execution"]}, indent=1))


if __name__ == "__main__":
    main()
