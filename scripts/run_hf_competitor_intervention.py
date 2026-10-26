"""Guarded runner for the paired competitor-price intervention pilot."""
from __future__ import annotations

import argparse
import json
from time import perf_counter
from typing import Any

from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.competitor_intervention import (
    run_paired_competitor_price_intervention,
    save_paired_competitor_intervention,
)


DEFAULT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


def run_and_persist_paired_experiment(
    extractor: HFActivationExtractor,
    *,
    output: str,
    run_kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Run once and save completion/failure metadata before propagating errors.

    The model remains owned by the caller, so this helper can be tested with
    mocks and the caller can release GPU memory after artifact persistence.
    """
    started_at = perf_counter()
    status = "completed"
    error: BaseException | None = None
    result: dict[str, Any] | None = None
    try:
        result = run_paired_competitor_price_intervention(extractor, **run_kwargs)
    except KeyboardInterrupt as exc:
        status = "interrupted"
        error = exc
    except BaseException as exc:
        status = "failed"
        error = exc

    memory_before_release = extractor.memory_snapshot()
    if result is None:
        result = {
            "schema_version": "hf-paired-competitor-intervention-v1",
            "engineering_pilot": True,
            "model_id": extractor.model_id,
            "model_revision": extractor.revision,
            "tokenizer_revision": extractor.tokenizer_revision,
        }
    result["execution"] = {
        "status": status,
        "wall_clock_seconds": perf_counter() - started_at,
        "memory_before_release": memory_before_release,
        "error_type": None if error is None else type(error).__name__,
        "error_message": None if error is None else str(error),
    }
    save_paired_competitor_intervention(output, result)
    if error is not None:
        raise error
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-model-load", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--intervention-round", type=int, default=1)
    parser.add_argument("--override-index", type=int, default=0)
    parser.add_argument("--layers", type=int, nargs="+", default=None)
    parser.add_argument("--output", default="artifacts/interpretability/hf_competitor_intervention.json")
    args = parser.parse_args()
    if not args.allow_model_load:
        parser.error("Refusing to load model weights. Re-run only after approval with --allow-model-load.")

    import torch

    extractor = HFActivationExtractor.from_pretrained(
        args.model_id,
        revision=args.revision,
        device_map="auto",
        torch_dtype=torch.float16,
        local_files_only=args.local_files_only,
    )
    summary = {"output": args.output, "model_id": args.model_id, "revision": args.revision}
    try:
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        result = run_and_persist_paired_experiment(
            extractor,
            output=args.output,
            run_kwargs={
                "n_rounds": args.rounds,
                "seed": args.seed,
                "intervention_round": args.intervention_round,
                "override_index": args.override_index,
                "selected_layers": args.layers,
            },
        )
        summary["execution"] = result["execution"]
    finally:
        extractor.close()
        summary["memory_after_release"] = extractor.memory_snapshot()
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
