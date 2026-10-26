"""Multi-model Modal runner (Qwen2.5 family) for Phase A.1 / B2 / C3 / D tasks.

  modal run scripts/modal_runner.py::download --model 14b
  modal run --detach scripts/modal_runner.py --model 14b --task a1 --run-name a1_14b --spawn
  modal run --detach scripts/modal_runner.py --model 7b --task c3d --run-name c3d_7b --spawn

Results land in the `collusion-latent-results` volume as <run-name>.json/.npz.
Revisions are pinned; small models use an A10, 14B/32B an A100-80GB.
"""
from __future__ import annotations

import io, json
from time import perf_counter

import modal

MODELS = {
    "0.5b": ("Qwen/Qwen2.5-0.5B-Instruct", "7ae557604adf67be50417f59c2c2f167def9a775"),
    "1.5b": ("Qwen/Qwen2.5-1.5B-Instruct", "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"),
    "3b": ("Qwen/Qwen2.5-3B-Instruct", "aa8e72537993ba99e69dfaafa59ed015b17504d1"),
    "7b": ("Qwen/Qwen2.5-7B-Instruct", "a09a35458c702b33eeacc393d103063234e8bc28"),
    "14b": ("Qwen/Qwen2.5-14B-Instruct", "cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8"),
    "32b": ("Qwen/Qwen2.5-32B-Instruct", "5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd"),
}
BIG = {"14b", "32b"}
CACHE = "/root/.cache/huggingface"
HUB = CACHE + "/hub"
VOLUME = modal.Volume.from_name("collusion-hf-model-cache", create_if_missing=True)
RESULTS_PATH = "/results"
RESULTS = modal.Volume.from_name("collusion-latent-results", create_if_missing=True)
app = modal.App("collusion-runner")
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.7.1", "transformers==4.48.3", "accelerate==1.15.0", "numpy==2.1.3", "requests")
    .env({"HF_HOME": CACHE, "HF_HUB_CACHE": HUB, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    .add_local_python_source("src")
)


@app.function(image=image, cpu=4, memory=8192, timeout=3600, volumes={CACHE: VOLUME})
def download_weights(model: str) -> dict:
    import os
    os.environ["HF_HUB_OFFLINE"] = "0"
    from huggingface_hub import snapshot_download
    mid, rev = MODELS[model]
    t0 = perf_counter()
    path = snapshot_download(mid, revision=rev, cache_dir=HUB, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])
    VOLUME.commit()
    return {"model": mid, "revision": rev, "files": sorted(os.listdir(path)), "seconds": perf_counter() - t0}


def _run(model: str, task: str, kwargs: dict, run_name: str, gpu: str) -> dict:
    import numpy as np
    import torch
    from src.interpretability.activation_extractor import HFActivationExtractor
    mid, rev = MODELS[model]
    t0 = perf_counter()
    info = {"backend": "modal", "gpu": gpu, "model_key": model}
    arrays = {}
    try:
        ext = HFActivationExtractor.from_pretrained(mid, revision=rev, device_map="auto", torch_dtype=torch.bfloat16 if model in BIG else torch.float16,
                                                    cache_dir=HUB, local_files_only=True)
        info["load_seconds"] = perf_counter() - t0
        torch.cuda.reset_peak_memory_stats()
        log = lambda m: print(m, flush=True)
        kw = dict(kwargs or {})
        if task == "a1":
            from src.interpretability.phase_a1 import run_phase_a1
            result, arrays = run_phase_a1(ext.model, ext.tokenizer, generate=True, capture=False, log=log)
        elif task == "b2":
            from src.interpretability.phase_bc_tasks import task_b2_confirm
            result, arrays = task_b2_confirm(ext.model, ext.tokenizer, log=log)
        elif task == "d1":
            from src.interpretability.phase_d import task_d1_games
            result, arrays = task_d1_games(ext.model, ext.tokenizer, log=log, **kw)
        elif task == "c3":
            from src.interpretability.phase_d import task_c3_transfer
            sites = tuple((s_, int(l_)) for s_, l_ in kw.get("sites", [["answer", 20]]))
            result, arrays = task_c3_transfer(ext.model, ext.tokenizer, sites=sites, log=log)
        elif task == "d1steer":  # games steered with a vector saved by an earlier c3 run
            from src.interpretability.phase_d import task_d1_games
            import numpy as np
            vecs = np.load(f"{RESULTS_PATH}/{kw['vector_run']}.npz")
            site, layer = kw["steer_key"].rsplit("_L", 1)
            result, arrays = task_d1_games(ext.model, ext.tokenizer, log=log,
                                           strategies=tuple(kw.get("strategies", ("fixed_monopoly", "tit_for_tat", "one_shot_deviation",
                                                                                  "rise_then_drop", "llm_selfplay"))),
                                           steering={"vector": vecs[f"vector_{kw['steer_key']}"], "layer": int(layer), "site": site,
                                                     "alphas": kw.get("alphas", [-1.0, 1.0, 2.0])})
        elif task == "c3d":  # transfer vector, then games steered with it
            from src.interpretability.phase_d import task_c3_transfer, task_d1_games
            c3, vecs = task_c3_transfer(ext.model, ext.tokenizer, log=log)
            steer_key = kw.get("steer_key", "answer_L20")
            site, layer = steer_key.rsplit("_L", 1)
            d1, _ = task_d1_games(ext.model, ext.tokenizer, log=log,
                                  strategies=tuple(kw.get("strategies", ("fixed_monopoly", "tit_for_tat", "one_shot_deviation",
                                                                         "rise_then_drop", "llm_selfplay"))),
                                  steering={"vector": vecs[f"vector_{steer_key}"], "layer": int(layer), "site": site,
                                            "alphas": kw.get("alphas", [-1.0, 1.0, 2.0])})
            result, arrays = {"task": "c3d", "c3": c3, "d1": d1}, vecs
        else:
            raise ValueError(task)
        cfg = ext.model.config
        result["model"] = {"model_id": mid, "revision": rev, "reported_revision": getattr(cfg, "_commit_hash", None),
                           "n_layers": cfg.num_hidden_layers, "d_model": cfg.hidden_size,
                           "dtype": "bfloat16" if model in BIG else "float16"}
        info.update(status="completed", wall_clock_seconds=perf_counter() - t0,
                    peak_cuda_allocated_bytes=int(torch.cuda.max_memory_allocated()), device=torch.cuda.get_device_name(0))
        result["execution"] = info
    except Exception as exc:
        import traceback
        info.update(status="failed", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc()[-3000:],
                    wall_clock_seconds=perf_counter() - t0)
        result = {"execution": info}
    import os
    os.makedirs(RESULTS_PATH, exist_ok=True)
    with open(f"{RESULTS_PATH}/{run_name}.json", "w") as f:
        json.dump(result, f, indent=1, default=float)
    if arrays:
        buf = io.BytesIO(); np.savez_compressed(buf, **arrays)
        with open(f"{RESULTS_PATH}/{run_name}.npz", "wb") as f:
            f.write(buf.getvalue())
    RESULTS.commit()
    return {"status": info["status"], "run_name": run_name}


@app.function(image=image, gpu="A10", timeout=3600, scaledown_window=30, volumes={CACHE: VOLUME, RESULTS_PATH: RESULTS})
def run_small(model: str, task: str, kwargs: dict, run_name: str) -> dict:
    return _run(model, task, kwargs, run_name, "A10")


@app.function(image=image, gpu="A100-80GB", timeout=3600, scaledown_window=30, memory=65536,
              volumes={CACHE: VOLUME, RESULTS_PATH: RESULTS})
def run_big(model: str, task: str, kwargs: dict, run_name: str) -> dict:
    return _run(model, task, kwargs, run_name, "A100-80GB")


@app.local_entrypoint()
def main(model: str = "7b", task: str = "a1", run_name: str = "", kwargs_json: str = "", spawn: bool = True,
         download: bool = False) -> None:
    if download:
        call = download_weights.spawn(model)
        print(json.dumps({"spawned_download": call.object_id, "model": model}))
        return
    if not run_name:
        raise SystemExit("--run-name is required")
    fn = run_big if model in BIG else run_small
    kw = json.loads(kwargs_json) if kwargs_json else {}
    if spawn:
        call = fn.spawn(model, task, kw, run_name)
        print(json.dumps({"spawned": call.object_id, "run_name": run_name, "model": model, "task": task}))
    else:
        print(json.dumps(fn.remote(model, task, kw, run_name)))
