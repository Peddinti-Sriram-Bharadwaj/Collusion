"""Modal entrypoint: Phase A.1 (and later B/C tasks) on pinned Qwen2.5-7B-Instruct.

Only ``modal run`` provisions a GPU. One A10 container, sequential work; weights
are downloaded once by a CPU-only function into ``collusion-hf-model-cache`` and read offline.

  modal run scripts/modal_phase_a1.py::download_weights

  modal run scripts/modal_phase_a1.py --limit 6 --output artifacts/interpretability/phase_a1/qwen7b_smoke.json
  modal run scripts/modal_phase_a1.py --output artifacts/interpretability/phase_a1/qwen7b_full.json
  modal run scripts/modal_phase_a1.py --task b1 --output artifacts/interpretability/phase_b/qwen7b_b1.json
  modal run scripts/modal_phase_a1.py --task c1 --output ... --kwargs-json '{"arms": ["real"]}'
  modal run scripts/modal_phase_a1.py --task c2 --directions dirs.npz --kwargs-json '{"layer": 14, "site": "rival"}' 
"""
from __future__ import annotations

import io, json
from pathlib import Path
from time import perf_counter

import modal

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
CACHE = "/root/.cache/huggingface"
HUB = CACHE + "/hub"
# Dedicated weights cache. Filled once by the CPU-only `download_weights` function,
# then read offline by GPU functions (no GPU time spent downloading).
VOLUME = modal.Volume.from_name("collusion-hf-model-cache", create_if_missing=True)
RESULTS_PATH = "/results"
RESULTS = modal.Volume.from_name("collusion-latent-results", create_if_missing=True)
app = modal.App("collusion-phase-a1")
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.7.1", "transformers==4.48.3", "accelerate==1.15.0", "numpy==2.1.3", "requests")
    .env({"HF_HOME": CACHE, "HF_HUB_CACHE": HUB, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    .add_local_python_source("src")
)


@app.function(image=image, cpu=2, memory=4096, timeout=1800, volumes={CACHE: VOLUME})
def download_weights() -> dict:
    """CPU-only: fetch the pinned revision into the shared cache volume."""
    import os
    os.environ["HF_HUB_OFFLINE"] = "0"
    from huggingface_hub import snapshot_download
    t0 = perf_counter()
    path = snapshot_download(MODEL_ID, revision=REVISION, cache_dir=HUB,
                             allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])
    VOLUME.commit()
    files = sorted(os.listdir(path))
    return {"path": path, "files": files, "seconds": perf_counter() - t0}


@app.function(image=image, gpu="A10", timeout=3600, scaledown_window=30, max_containers=1, volumes={CACHE: VOLUME, RESULTS_PATH: RESULTS})
def run_remote(task: str = "a1", limit: int | None = None, generate: bool = True, capture: bool = True,
               kwargs: dict | None = None, run_name: str = "") -> dict:
    import numpy as np
    import torch
    from src.interpretability.activation_extractor import HFActivationExtractor
    t0 = perf_counter()
    info: dict = {"backend": "modal", "gpu": "A10"}
    try:
        ext = HFActivationExtractor.from_pretrained(MODEL_ID, revision=REVISION, device_map="auto",
                                                    torch_dtype=torch.float16, cache_dir=HUB, local_files_only=True)
        info["load_seconds"] = perf_counter() - t0
        torch.cuda.reset_peak_memory_stats()
        if task == "a1":
            from src.interpretability.phase_a1 import run_phase_a1
            result, arrays = run_phase_a1(ext.model, ext.tokenizer, generate=generate, capture=capture, limit=limit,
                                          log=lambda m: print(m, flush=True))
        elif task in ("b1", "c1", "c2", "b2", "c1pos"):
            from src.interpretability import phase_bc_tasks as T
            fn = {"b1": T.task_b1, "c1": T.task_c1_patch, "c2": T.task_c2_steer,
                  "b2": T.task_b2_confirm, "c1pos": T.task_c1_positions}[task]
            kw = dict(kwargs or {})
            if task == "b1" and limit:
                kw["limit"] = limit
            if task == "c2":
                kw["directions"] = {k: np.asarray(v, dtype=np.float32) for k, v in kw["directions"].items()}
            result, arrays = fn(ext.model, ext.tokenizer, log=lambda m: print(m, flush=True), **kw)
        else:
            raise ValueError(f"unknown task {task}")
        buf = io.BytesIO()
        if arrays:
            extra = {"row_ids": np.array([r["row_id"] for r in result["rows"]])} if "rows" in result else {}
            np.savez_compressed(buf, **extra, **arrays)
        result["model"] = {"model_id": MODEL_ID, "revision": REVISION, "dtype": "float16",
                           "reported_revision": getattr(ext.model.config, "_commit_hash", None),
                           "n_layers": ext.model.config.num_hidden_layers, "d_model": ext.model.config.hidden_size}
        info.update(status="completed", wall_clock_seconds=perf_counter() - t0,
                    peak_cuda_allocated_bytes=int(torch.cuda.max_memory_allocated()),
                    device=torch.cuda.get_device_name(0))
        result["execution"] = info
        payload = {"result": result, "npz": buf.getvalue()}
    except Exception as exc:
        import traceback
        info.update(status="failed", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc()[-3000:],
                    wall_clock_seconds=perf_counter() - t0)
        payload = {"result": {"execution": info, "rows": []}, "npz": b""}
    if run_name:  # persist remotely so a detached run can be fetched with `modal volume get`
        import os
        os.makedirs(RESULTS_PATH, exist_ok=True)
        with open(f"{RESULTS_PATH}/{run_name}.json", "w") as f:
            json.dump(payload["result"], f, indent=1)
        if payload["npz"]:
            with open(f"{RESULTS_PATH}/{run_name}.npz", "wb") as f:
                f.write(payload["npz"])
        RESULTS.commit()
    return payload


@app.local_entrypoint()
def main(task: str = "a1", output: str = "artifacts/interpretability/phase_a1/qwen7b.json",
         limit: int = 0, no_generate: bool = False, no_capture: bool = False, kwargs_json: str = "",
         directions: str = "", run_name: str = "", spawn: bool = False) -> None:
    import numpy as np
    kw = json.loads(kwargs_json) if kwargs_json else {}
    if directions:
        d = np.load(directions)
        names = kw.pop("direction_names", None) or list(d.files)
        kw["directions"] = {k: d[k].astype(float).tolist() for k in names}
    if spawn:  # fire-and-forget: survives client disconnect when run with `modal run --detach`
        if not run_name:
            raise SystemExit("--spawn requires --run-name (results are written to the results volume)")
        call = run_remote.spawn(task=task, limit=limit or None, generate=not no_generate, capture=not no_capture,
                                kwargs=kw, run_name=run_name)
        print(json.dumps({"spawned": call.object_id, "run_name": run_name}))
        return
    out = run_remote.remote(task=task, limit=limit or None, generate=not no_generate, capture=not no_capture, kwargs=kw,
                            run_name=run_name)
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out["result"], indent=1), encoding="utf-8")
    if out["npz"]:
        path.with_suffix(".npz" if task != "a1" else ".activations.npz").write_bytes(out["npz"])
    print(json.dumps({"execution": out["result"].get("execution"), "summary": out["result"].get("summary")}, indent=1))
