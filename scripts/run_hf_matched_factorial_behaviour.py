"""Matched 3x4 behavioural factorial experiment; no activation capture."""
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
class FactorialScenario:
    scenario_id: str
    scenario_seed: int
    own_price_group: str
    rival_price_pattern: str
    own_action_indices: tuple[int, int, int, int]
    rival_action_indices: tuple[int, int, int, int]


def generate_factorial_scenarios(seed: int = 0) -> list[FactorialScenario]:
    """Build the complete 3 own-history x 4 rival-history factorial design."""
    own_groups = (
        ("consistently_low", (2, 2, 2, 2)),
        ("consistently_mid", (5, 5, 5, 5)),
        ("consistently_high", (8, 8, 8, 8)),
    )
    rival_patterns = (
        ("consistently_low", (1, 1, 1, 1)),
        ("consistently_high", (8, 8, 8, 8)),
        ("rising", (1, 3, 5, 7)),
        ("falling", (8, 6, 4, 2)),
    )
    scenarios = []
    for own_index, (own_name, own_actions) in enumerate(own_groups):
        for rival_index, (rival_name, rival_actions) in enumerate(rival_patterns):
            cell = own_index * len(rival_patterns) + rival_index
            scenarios.append(
                FactorialScenario(
                    scenario_id=f"factorial-own-{own_name}-rival-{rival_name}",
                    scenario_seed=seed + cell,
                    own_price_group=own_name,
                    rival_price_pattern=rival_name,
                    own_action_indices=own_actions,
                    rival_action_indices=rival_actions,
                )
            )
    return scenarios


def materialize_factorial_history(
    env: LogitBertrandEnv, scenario: FactorialScenario
) -> list[dict[str, Any]]:
    """Replay all four joint actions using the environment transition method."""
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


def _action_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["analysis_eligible"]]
    actions = [row["selected_price_index"] for row in valid]
    counts = {str(action): actions.count(action) for action in sorted(set(actions))}
    return {
        "n_rows": len(rows),
        "n_valid": len(valid),
        "n_invalid": len(rows) - len(valid),
        "parse_valid_fraction": len(valid) / len(rows) if rows else None,
        "action_counts_valid": counts,
        "action_diversity_valid": len(counts),
    }


def summarise_rows(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Keep own-history, rival-history, and protocol comparisons separate."""
    own_groups = sorted({row["own_price_group"] for row in rows})
    rival_patterns = sorted({row["rival_price_pattern"] for row in rows})
    within_own_group = {}
    for own_group in own_groups:
        within_own_group[own_group] = {}
        for protocol in (RAW_PROTOCOL, CHAT_PROTOCOL):
            cell_rows = [
                row for row in rows
                if row["own_price_group"] == own_group and row["protocol"] == protocol
            ]
            by_rival = {}
            for rival_pattern in rival_patterns:
                matched = [row for row in cell_rows if row["rival_price_pattern"] == rival_pattern]
                by_rival[rival_pattern] = _action_summary(matched)
            within_own_group[own_group][protocol] = {
                **_action_summary(cell_rows),
                "by_rival_price_pattern": by_rival,
            }

    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["scenario_id"], {})[row["protocol"]] = row
    valid_pairs = [
        pair for pair in grouped.values()
        if RAW_PROTOCOL in pair and CHAT_PROTOCOL in pair
        and pair[RAW_PROTOCOL]["analysis_eligible"] and pair[CHAT_PROTOCOL]["analysis_eligible"]
    ]
    protocol_differences = sum(
        pair[RAW_PROTOCOL]["selected_price_index"] != pair[CHAT_PROTOCOL]["selected_price_index"]
        for pair in valid_pairs
    )
    return {
        "own_price_history_effect_descriptive": {
            own_group: {
                protocol: _action_summary([
                    row for row in rows
                    if row["own_price_group"] == own_group and row["protocol"] == protocol
                ])
                for protocol in (RAW_PROTOCOL, CHAT_PROTOCOL)
            }
            for own_group in own_groups
        },
        "rival_price_history_effect_within_own_group": within_own_group,
        "prompt_protocol_effect_matched": {
            "valid_matched_cells": len(valid_pairs),
            "different_selected_actions": protocol_differences,
            "different_action_fraction": protocol_differences / len(valid_pairs) if valid_pairs else None,
        },
        "interpretation_scope": (
            "These are descriptive behavioural comparisons. They do not identify "
            "a coordination mechanism or establish causal effects beyond the prompt "
            "and realised-history interventions specified here."
        ),
    }


def run_factorial_experiment(
    extractor: HFActivationExtractor,
    *,
    seed: int = 0,
    protocol: str = "both",
) -> dict[str, Any]:
    """Evaluate all 12 matched histories under each requested protocol."""
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(1, env, persona=None, seed=seed)
    scenarios = generate_factorial_scenarios(seed)
    rows = []
    for scenario in scenarios:
        market_history = materialize_factorial_history(env, scenario)
        raw_prompt = agent._build_prompt(
            _agent_history(market_history), len(market_history), len(market_history) + 1
        )
        for protocol_label, prompt in protocol_prompts(raw_prompt, extractor.tokenizer, protocol).items():
            decision = _generate_decision(extractor, agent, prompt)
            rows.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "scenario_seed": scenario.scenario_seed,
                    "own_price_group": scenario.own_price_group,
                    "rival_price_pattern": scenario.rival_price_pattern,
                    "history_length": len(market_history),
                    "own_action_indices": list(scenario.own_action_indices),
                    "rival_action_indices": list(scenario.rival_action_indices),
                    "market_history": market_history,
                    "protocol": protocol_label,
                    "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest(),
                    "model_id": extractor.model_id,
                    "model_revision": extractor.revision,
                    "tokenizer_revision": extractor.tokenizer_revision,
                    **decision,
                }
            )
    return {
        "schema_version": "hf-matched-factorial-behaviour-v1",
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
        default="artifacts/interpretability/matched-factorial-behaviour.json",
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
        save_hf_trajectory(
            args.output, run_factorial_experiment(extractor, seed=args.seed, protocol=args.protocol)
        )
    finally:
        extractor.close()


if __name__ == "__main__":
    main()
