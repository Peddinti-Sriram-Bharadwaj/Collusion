"""Run Phase B1 / C1 / C2 tasks locally on a pinned HF model.

  python scripts/run_phase_bc.py --task b1 --model Qwen/Qwen2.5-0.5B-Instruct --revision <sha> --output out.json
  python scripts/run_phase_bc.py --task c1 ... --controls phase-a-000,phase-a-010 --layers 0,4,8
  python scripts/run_phase_bc.py --task c2 ... --directions dirs.npz --layer 10
"""
from __future__ import annotations

import argparse, json, platform, sys
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.interpretability.activation_extractor import HFActivationExtractor  # noqa: E402
from src.interpretability import phase_bc_tasks as T  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=["b1", "c1", "c2"])
    ap.add_argument("--model", required=True); ap.add_argument("--revision", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--limit", type=int); ap.add_argument("--controls"); ap.add_argument("--layers")
    ap.add_argument("--arms", default="real,stale"); ap.add_argument("--directions"); ap.add_argument("--layer", type=int)
    ap.add_argument("--site", default="rival"); ap.add_argument("--templates", default="v1,v2")
    args = ap.parse_args()
    t0 = perf_counter()
    ext = HFActivationExtractor.from_pretrained(args.model, revision=args.revision, device_map=None, torch_dtype=torch.float32)
    log = lambda m: print(m, flush=True)
    ctl = args.controls.split(",") if args.controls else None
    if args.task == "b1":
        res, arrays = T.task_b1(ext.model, ext.tokenizer, templates=tuple(args.templates.split(",")), limit=args.limit, log=log)
    elif args.task == "c1":
        layers = [int(x) for x in args.layers.split(",")] if args.layers else None
        res, arrays = T.task_c1_patch(ext.model, ext.tokenizer, controls=ctl, arms=tuple(args.arms.split(",")), layers=layers, log=log)
    else:
        d = np.load(args.directions)
        res, arrays = T.task_c2_steer(ext.model, ext.tokenizer, directions={k: d[k] for k in d.files},
                                      layer=args.layer, site=args.site, controls=ctl, log=log)
    res["model"] = {"model_id": args.model, "revision": args.revision, "dtype": "float32"}
    res["execution"] = {"backend": "local", "platform": platform.platform(), "torch": torch.__version__,
                        "wall_clock_seconds": perf_counter() - t0}
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    if arrays:
        np.savez_compressed(out.with_suffix(".npz"), **arrays)
    print("done", out, res["execution"])


if __name__ == "__main__":
    main()
