"""Four-round matched-history sensitivity experiment; no activation capture."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Sequence

import numpy as np
import torch

from scripts.run_hf_behavioural_responsiveness_benchmark import (
    CHAT_PROTOCOL,
    DEFAULT_MODEL_ID,
    DEFAULT_MODEL_REVISION,
    RAW_PROTOCOL,
    _generate_decision,
    protocol_prompts,
)
from src.env import LogitBertrandEnv
from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.hf_episode import save_hf_trajectory
from src.llm_agent import LLMPricingAgent


@dataclass(frozen=True)
class MatchedHistoryScenario:
    scenario_id: str
    scenario_seed: int
    rival_pattern: str
    rival_action_indices: tuple[int, int, int, int]
    own_action_indices: tuple[int, int, int, int]


def generate_matched_history_scenarios(seed: int = 0) -> list[MatchedHistoryScenario]:
    """Four rival patterns with one shared four-round own-price sequence."""
    own_actions = (5, 5, 5, 5)
    patterns = (
        ("consistently_low", (1, 1, 1, 1)),
        ("consistently_high", (8, 8, 8, 8)),
        ("falling", (8, 6, 4, 2)),
        ("rising", (1, 3, 5, 7)),
    )
    return [
        MatchedHistoryScenario(
            scenario_id=f"matched-history-{index:03d}",
            scenario_seed=seed + index,
            rival_pattern=pattern,
            rival_action_indices=rival_actions,
            own_action_indices=own_actions,
        )
        for index, (pattern, rival_actions) in enumerate(patterns)
    ]


def materialize_matched_history(
    env: LogitBertrandEnv, scenario: MatchedHistoryScenario
) -> list[dict[str, Any]]:
    """Replay all market rounds so prices and profits follow environment rules."""
    env.reset(np.random.default_rng(scenario.scenario_seed))
    history = []
    for round_id, (rival, own) in enumerate(
        zip(scenario.rival_action_indices, scenario.own_action_indices)
    ):
        _, profits, info = env.step((rival, own))
        history.append(
            {
                "round_id": round_id,
                "action_indices": [rival, own],
                "prices": [float(price) for price in info["prices"]],
                "profits": [float(profit) for profit in profits],
            }
        )
    return history


def _agent_history(history: Sequence[dict[str, Any]]) -> list[tuple[np.ndarray, np.ndarray]]:
    return [
        (np.asarray(row["prices"], dtype=float), np.asarray(row["profits"], dtype=float))
        for row in history
    ]


def summarise_rows(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Report action variation separately for raw and chat prompt protocols."""
    by_protocol = {}
    for protocol in (RAW_PROTOCOL, CHAT_PROTOCOL):
        protocol_rows = [row for row in rows if row["protocol"] == protocol]
        valid = [row for row in protocol_rows if row["parse_valid"]]
        actions = [row["selected_price_index"] for row in valid]
        counts = {str(action): actions.count(action) for action in sorted(set(actions))}
        by_protocol[protocol] = {
            "n_rows": len(protocol_rows),
            "n_valid": len(valid),
            "parse_valid_fraction": len(valid) / len(protocol_rows) if protocol_rows else None,
            "action_counts_valid": counts,
            "action_diversity_valid": len(counts),
        }
    return {"by_protocol": by_protocol}


def run_matched_history_experiment(
    extractor: HFActivationExtractor,
    *,
    seed: int = 0,
    protocol: str = "both",
) -> dict[str, Any]:
    """Evaluate the four matched histories once per selected prompt protocol."""
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(1, env, persona=None, seed=seed)
    scenarios = generate_matched_history_scenarios(seed)
    rows = []
    for scenario in scenarios:
        complete_history = materialize_matched_history(env, scenario)
        agent_history = _agent_history(complete_history)
        raw_prompt = agent._build_prompt(
            agent_history, len(agent_history), len(agent_history) + 1
        )
        for protocol_label, prompt in protocol_prompts(raw_prompt, extractor.tokenizer, protocol).items():
            decision = _generate_decision(extractor, agent, prompt)
            rows.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "scenario_seed": scenario.scenario_seed,
                    "rival_pattern": scenario.rival_pattern,
                    "history_length": len(complete_history),
                    "own_action_indices": list(scenario.own_action_indices),
                    "rival_action_indices": list(scenario.rival_action_indices),
                    "market_history": complete_history,
                    "protocol": protocol_label,
                    "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest(),
                    "model_id": extractor.model_id,
                    "model_revision": extractor.revision,
                    "tokenizer_revision": extractor.tokenizer_revision,
                    **decision,
                }
            )
    return {
        "schema_version": "hf-matched-history-sensitivity-v1",
        "seed": seed,
        "market_parameters": {
            "n_agents": env.n_agents,
            "n_prices": env.n_prices,
            "a": env.a,
            "a0": env.a0,
            "mu": env.mu,
            "c": env.c,
            "price_grid": [float(price) for price in env.price_grid],
        },
        "deterministic_generation": True,
        "activation_extraction": False,
        "scenarios": [asdict(scenario) for scenario in scenarios],
        "rows": rows,
        "summary": summarise_rows(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-model-load", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--protocol", choices=["raw", "chat", "both"], default="both")
    parser.add_argument(
        "--output",
        default="artifacts/interpretability/matched-history-sensitivity.json",
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
        result = run_matched_history_experiment(
            extractor, seed=args.seed, protocol=args.protocol
        )
        save_hf_trajectory(args.output, result)
    finally:
        extractor.close()


if __name__ == "__main__":
    main()
