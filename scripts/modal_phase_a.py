"""Modal entrypoint for the bounded Qwen2.5-7B Phase A behavioural pilot.

This file is safe to import without Modal credentials.  Running ``modal run``
is the only operation that provisions a GPU or downloads model weights.
"""
from __future__ import annotations

import json
from time import perf_counter

import modal
from src.interpretability.modal_phase_a import (
    MODAL_GPU, MODAL_HF_CACHE_PATH, MODAL_MAX_CONTAINERS, MODAL_SCALEDOWN_SECONDS,
    MODAL_TIMEOUT_SECONDS, phase_a_loader_kwargs,
)

MODEL_CACHE_PATH = MODAL_HF_CACHE_PATH
MODEL_CACHE_VOLUME = modal.Volume.from_name("collusion-hf-model-cache", create_if_missing=True)
app = modal.App("collusion-phase-a-behavioural")
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.7.1", "transformers==4.48.3", "accelerate==1.15.0", "numpy==2.1.3")
    .env({"HF_HOME": MODEL_CACHE_PATH, "HF_HUB_CACHE": MODEL_CACHE_PATH})
    .add_local_python_source("src")
)


@app.function(
    image=image, gpu=MODAL_GPU, timeout=MODAL_TIMEOUT_SECONDS,
    scaledown_window=MODAL_SCALEDOWN_SECONDS, max_containers=MODAL_MAX_CONTAINERS,
    volumes={MODEL_CACHE_PATH: MODEL_CACHE_VOLUME},
)
def run_remote(*, smoke_only: bool = False, seed: int = 20261023) -> dict:
    """Load exactly one pinned model into one container, then infer sequentially."""
    import torch
    from src.interpretability.activation_extractor import HFActivationExtractor
    from src.interpretability.modal_phase_a import phase_a_remote_failure_artifact, run_phase_a

    extractor = None
    started_at = perf_counter()
    try:
        extractor = HFActivationExtractor.from_pretrained(**phase_a_loader_kwargs(MODEL_CACHE_PATH))
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        result = run_phase_a(extractor, seed=seed, smoke_only=smoke_only)
        return result
    except Exception as exc:
        # Return a serialisable failure record so the local entrypoint still
        # writes a JSON artifact rather than leaving diagnostic state remote.
        return phase_a_remote_failure_artifact(exc, perf_counter() - started_at)
    finally:
        # Persist a first-run cache even if inference later fails.
        MODEL_CACHE_VOLUME.commit()
        if extractor is not None:
            extractor.close()


@app.local_entrypoint()
def main(smoke_only: bool = False, seed: int = 20261023, output: str = "artifacts/interpretability/modal-phase-a.json") -> None:
    """Submit exactly one bounded job and save its returned JSON locally."""
    from src.interpretability.modal_phase_a import save_phase_a_artifact
    result = run_remote.remote(smoke_only=smoke_only, seed=seed)
    path = save_phase_a_artifact(output, result)
    print(json.dumps({"execution": result["execution"], "summary": result["summary"], "output": str(path)}, indent=2))
