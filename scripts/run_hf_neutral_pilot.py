"""Guarded local runner for the opt-in neutral Hugging Face pilot.

No model is loaded unless ``--allow-model-load`` is supplied deliberately.
Outputs are written under ignored artifacts/interpretability/ by default.
"""
from __future__ import annotations

import argparse
import json
from time import perf_counter

from src.env import LogitBertrandEnv
from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.hf_episode import run_hf_neutral_episode, save_hf_trajectory
from src.interpretability.hf_pricing_adapter import HFPricingAgent


DEFAULT_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
DEFAULT_MODEL_REVISION = "f73cfd58be7c44c3caabea717217251688cd47b1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("alignment", "episode"), default="alignment")
    parser.add_argument("--allow-model-load", action="store_true")
    parser.add_argument("--output", default="artifacts/interpretability/hf_neutral_pilot.json")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--layers", type=int, nargs="+", default=None)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument(
        "--local-files-only", action="store_true",
        help="Require an existing local Hugging Face snapshot; never contact the Hub.",
    )
    args = parser.parse_args()
    if not args.allow_model_load:
        parser.error("Refusing to load model weights. Re-run only after approval with --allow-model-load.")

    import torch

    extractor = HFActivationExtractor.from_pretrained(
        args.model_id, revision=args.revision, device_map="auto", torch_dtype=torch.float16,
        local_files_only=args.local_files_only,
    )
    summary = {
        "output": args.output,
        "model_id": args.model_id,
        "revision": args.revision,
        "local_files_only": args.local_files_only,
    }
    try:
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        started_at = perf_counter()
        if args.mode == "alignment":
            env = LogitBertrandEnv(n_agents=2, n_prices=10)
            agent = HFPricingAgent(
                agent_id=0, env=env, extractor=extractor, persona=None,
                seed=args.seed, selected_layers=args.layers,
            )
            decision = agent.act(
                [], 0, 5, episode_id=f"hf-alignment-{args.seed}", market_seed=args.seed,
            )
            trajectory = {
                "schema_version": "hf-alignment-v2",
                "engineering_smoke_test": True,
                "record": decision.activation_record,
                "generated_response": decision.raw_text,
                "parse_failed": decision.parse_failed,
                "action_index": decision.action_index,
                "error": decision.error,
            }
            if decision.activation_record is None:
                raise RuntimeError(f"Alignment generation failed: {decision.error}")
        else:
            trajectory = run_hf_neutral_episode(
                extractor, n_rounds=5, seed=args.seed, selected_layers=args.layers,
            )
        save_hf_trajectory(args.output, trajectory)
        summary["runtime_seconds"] = perf_counter() - started_at
        summary["memory_before_release"] = extractor.memory_snapshot()
    finally:
        extractor.close()
        summary["memory_after_release"] = extractor.memory_snapshot()
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
