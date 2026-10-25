"""Modal backend for research batches (resumable, results persisted per unit on a Volume).

Launch (returns immediately; survives client disconnect):
  modal run --detach scripts/modal_research.py --spec research/configs/<batch>.json
Then pull results into the registry:
  python scripts/research.py sync --batch <batch_id>
"""
from __future__ import annotations

import json, os
from time import perf_counter

import modal

CACHE = "/root/.cache/huggingface"; HUB = CACHE + "/hub"
OUT = "/results/research"
WEIGHTS = modal.Volume.from_name("collusion-hf-model-cache", create_if_missing=True)
RESULTS = modal.Volume.from_name("collusion-latent-results", create_if_missing=True)
app = modal.App("collusion-research")
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.7.1", "transformers==4.48.3", "accelerate==1.15.0", "numpy==2.1.3", "requests")
    .env({"HF_HOME": CACHE, "HF_HUB_CACHE": HUB, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    .add_local_python_source("src")
    .add_local_dir("research/vectors", "/root/research/vectors")
)
BIG = {"14b", "32b"}


def _run(spec: dict, git: dict, gpu: str) -> dict:
    import torch
    from pathlib import Path
    from src.interpretability.activation_extractor import HFActivationExtractor
    from src.research.configs import expand
    from src.research.runner import MODELS, execute
    model_key = spec["model"]
    mid, rev = MODELS[model_key]
    out_dir = Path(OUT) / spec["batch_id"]; out_dir.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in out_dir.glob("*.json")}  # resume: completed units already on the volume
    done = {d for d in done if json.loads((out_dir / f"{d}.json").read_text())["record"]["status"] == "completed"}
    t0 = perf_counter()
    ext = HFActivationExtractor.from_pretrained(mid, revision=rev, device_map="auto",
                                                torch_dtype=torch.bfloat16 if model_key in BIG else torch.float16,
                                                cache_dir=HUB, local_files_only=True)
    cfg = ext.model.config
    meta = {"model_key": model_key, "model_id": mid, "revision": rev, "reported_revision": getattr(cfg, "_commit_hash", None),
            "n_layers": cfg.num_hidden_layers, "d_model": cfg.hidden_size, "backend": f"modal-{gpu}-hf-transformers",
            "dtype": "bfloat16" if model_key in BIG else "float16", "load_seconds": perf_counter() - t0}
    units = expand(spec)
    counter = {"n": 0}

    def sink(rec, payload):
        tmp = out_dir / f".{rec['run_id']}.tmp"
        tmp.write_text(json.dumps({"record": rec, "payload": payload}, default=str))
        os.replace(tmp, out_dir / f"{rec['run_id']}.json")
        counter["n"] += 1
        if counter["n"] % 20 == 0:
            RESULTS.commit()

    batch = {"batch_id": spec["batch_id"], "protocol": spec["protocol"], "designation": spec["designation"],
             "experiment_id": spec.get("experiment_id", spec["protocol"]), "git": git}
    stats = execute(ext.model, ext.tokenizer, units, batch=batch, model_meta=meta, sink=sink, skip=done,
                    vector_root=Path("/root/research/vectors"), log=lambda m: print(m, flush=True))
    (out_dir / "_batch_done.json").write_text(json.dumps({"stats": stats, "model": meta, "seconds": perf_counter() - t0,
                                                          "gpu": gpu}))
    RESULTS.commit()
    return stats


@app.function(image=image, gpu="A10", timeout=3600 * 3, volumes={CACHE: WEIGHTS, "/results": RESULTS})
def run_small(spec: dict, git: dict) -> dict:
    return _run(spec, git, "A10")


@app.function(image=image, gpu="A100-80GB", memory=65536, timeout=3600 * 3, volumes={CACHE: WEIGHTS, "/results": RESULTS})
def run_big(spec: dict, git: dict) -> dict:
    return _run(spec, git, "A100-80GB")


@app.local_entrypoint()
def main(spec: str) -> None:
    import sys
    sys.path.insert(0, os.getcwd())
    from src.research.configs import load_spec, expand, estimate
    from src.research.ids import git_state
    s = load_spec(spec)
    est = estimate(expand(s))
    fn = run_big if s["model"] in BIG else run_small
    call = fn.spawn(s, git_state())
    print(json.dumps({"spawned": call.object_id, "batch_id": s["batch_id"], "estimate": est}))
