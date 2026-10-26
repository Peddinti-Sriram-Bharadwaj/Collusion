"""Guarded offline runner for matched prompt-information counterfactuals."""
from __future__ import annotations

import argparse
import json
from time import perf_counter
from typing import Any

from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.matched_prompt_counterfactual import (
    load_agent1_round3_context,
    run_matched_prompt_counterfactuals,
    save_matched_prompt_counterfactuals,
)


DEFAULT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-model-load", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument("--source", default="artifacts/interpretability/paired-undercut-round2.json")
    parser.add_argument("--output", default="artifacts/interpretability/matched-prompt-counterfactuals.json")
    parser.add_argument("--layers", type=int, nargs="+", default=None)
    args = parser.parse_args()
    if not args.allow_model_load:
        parser.error("Refusing to load model weights. Re-run only after approval with --allow-model-load.")

    import torch

    control, undercut = load_agent1_round3_context(args.source)
    extractor = HFActivationExtractor.from_pretrained(
        args.model_id,
        revision=args.revision,
        device_map="auto",
        torch_dtype=torch.float16,
        local_files_only=args.local_files_only,
    )
    summary = {"output": args.output, "model_id": args.model_id, "revision": args.revision}
    result: dict[str, Any] | None = None
    status = "completed"
    error: BaseException | None = None
    try:
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        started_at = perf_counter()
        try:
            result = run_matched_prompt_counterfactuals(
                extractor, control_context=control, undercut_context=undercut, selected_layers=args.layers,
            )
        except KeyboardInterrupt as exc:
            status, error = "interrupted", exc
        except BaseException as exc:
            status, error = "failed", exc
        if result is None:
            result = {
                "schema_version": "hf-matched-prompt-counterfactual-v1",
                "engineering_pilot": True,
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
        save_matched_prompt_counterfactuals(args.output, result)
        summary["execution"] = result["execution"]
        if error is not None:
            raise error
    finally:
        extractor.close()
        summary["memory_after_release"] = extractor.memory_snapshot()
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
