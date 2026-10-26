"""Guarded collector for the small balanced counterfactual dataset."""
from __future__ import annotations

import argparse
from time import perf_counter
from typing import Any

import torch

from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.balanced_counterfactual_dataset import (
    collect_balanced_counterfactual_dataset,
    generate_balanced_scenarios,
)
from src.interpretability.hf_episode import save_hf_trajectory


DEFAULT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


def run_and_persist_balanced_collection(
    extractor: HFActivationExtractor,
    *,
    output: str,
    scenarios: int,
    seed: int,
    selected_layers: list[int] | None,
) -> dict[str, Any]:
    """Collect once and save status and CUDA memory before error propagation."""
    started_at = perf_counter()
    status = "completed"
    error: BaseException | None = None
    result: dict[str, Any] | None = None
    try:
        generated_scenarios = generate_balanced_scenarios(scenarios, seed)
        result = collect_balanced_counterfactual_dataset(
            extractor,
            generated_scenarios,
            selected_layers=selected_layers,
        )
    except KeyboardInterrupt as exc:
        status = "interrupted"
        error = exc
    except BaseException as exc:
        status = "failed"
        error = exc

    if result is None:
        result = {
            "schema_version": "hf-balanced-counterfactual-dataset-v1",
            "model_id": extractor.model_id,
            "model_revision": extractor.revision,
            "tokenizer_revision": extractor.tokenizer_revision,
        }
    result["execution"] = {
        "status": status,
        "wall_clock_seconds": perf_counter() - started_at,
        "memory_before_release": extractor.memory_snapshot(),
        "error_type": None if error is None else type(error).__name__,
        "error_message": None if error is None else str(error),
    }
    save_hf_trajectory(output, result)
    if error is not None:
        raise error
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-model-load", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--scenarios", type=int, default=12)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--layers", type=int, nargs="+")
    parser.add_argument(
        "--output",
        default="artifacts/interpretability/balanced-counterfactual-dataset.json",
    )
    args = parser.parse_args()
    if not args.allow_model_load:
        parser.error("Refusing to load model weights without --allow-model-load.")

    extractor = HFActivationExtractor.from_pretrained(
        DEFAULT_MODEL_ID,
        revision=DEFAULT_MODEL_REVISION,
        device_map="auto",
        torch_dtype=torch.float16,
        local_files_only=args.local_files_only,
    )
    try:
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        run_and_persist_balanced_collection(
            extractor,
            output=args.output,
            scenarios=args.scenarios,
            seed=args.seed,
            selected_layers=args.layers,
        )
    finally:
        extractor.close()


if __name__ == "__main__":
    main()
