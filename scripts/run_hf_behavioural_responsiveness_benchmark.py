"""Offline-only behavioural responsiveness benchmark; no activation capture."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import re
from typing import Any, Sequence

import numpy as np
import torch

from src.env import LogitBertrandEnv
from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.hf_episode import save_hf_trajectory
from src.llm_agent import LLMPricingAgent


DEFAULT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
RAW_PROTOCOL = "raw_repository_stateless_v1"
CHAT_PROTOCOL = "qwen_chat_template_v1"


@dataclass(frozen=True)
class BenchmarkScenario:
    scenario_id: str
    scenario_seed: int
    market_condition: str
    action_indices: tuple[tuple[int, int], ...]


def generate_market_scenarios(seed: int = 0) -> list[BenchmarkScenario]:
    """Return fixed-pattern, seed-labelled legal action histories.

    Agent 0 is the rival and Agent 1 is the prompted firm.  Patterns span
    one, two, four, and eight realised market rounds.  Seeds identify the
    environment reset used when the histories are materialised; prices and
    profits always come from ``LogitBertrandEnv.step``.
    """
    patterns = [
        ("one_round_rival_low", ((0, 5),)),
        ("one_round_rival_high", ((9, 5),)),
        ("two_round_persistent_undercut", ((1, 6), (1, 6))),
        ("two_round_persistent_high", ((8, 3), (8, 3))),
        ("four_round_rival_falling", ((8, 4), (6, 4), (4, 4), (2, 4))),
        ("four_round_rival_rising", ((1, 4), (3, 4), (6, 4), (8, 4))),
        ("four_round_rival_alternating", ((1, 5), (8, 5), (1, 5), (8, 5))),
        ("four_round_matched_mid_prices", ((5, 5), (5, 5), (5, 5), (5, 5))),
        ("eight_round_repeated_undercuts", ((2, 7), (1, 7), (2, 7), (1, 7), (2, 7), (1, 7), (2, 7), (1, 7))),
        ("eight_round_repeated_high_rival", ((8, 3), (9, 3), (8, 3), (9, 3), (8, 3), (9, 3), (8, 3), (9, 3))),
    ]
    return [
        BenchmarkScenario(
            scenario_id=f"responsiveness-{index:03d}",
            scenario_seed=seed + index,
            market_condition=condition,
            action_indices=actions,
        )
        for index, (condition, actions) in enumerate(patterns)
    ]


def materialize_history(
    env: LogitBertrandEnv, scenario: BenchmarkScenario
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Replay legal joint actions through the environment's transition API."""
    env.reset(np.random.default_rng(scenario.scenario_seed))
    history = []
    for actions in scenario.action_indices:
        _, profits, info = env.step(actions)
        history.append((np.asarray(info["prices"]).copy(), np.asarray(profits).copy()))
    return history


def protocol_prompts(raw_prompt: str, tokenizer: Any, protocol: str) -> dict[str, str]:
    prompts: dict[str, str] = {}
    if protocol in ("raw", "both"):
        prompts[RAW_PROTOCOL] = raw_prompt
    if protocol in ("chat", "both"):
        if not hasattr(tokenizer, "apply_chat_template"):
            raise RuntimeError("The selected tokenizer does not provide a chat template.")
        prompts[CHAT_PROTOCOL] = tokenizer.apply_chat_template(
            [{"role": "user", "content": raw_prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
    return prompts


def _generate_decision(extractor: HFActivationExtractor, agent: LLMPricingAgent, prompt: str) -> dict[str, Any]:
    """Use deterministic generation only; never invoke hidden-state capture."""
    encoded = extractor._prepare_inputs(prompt)
    with torch.inference_mode():
        sequence = extractor.model.generate(
            **encoded,
            do_sample=False,
            max_new_tokens=32,
            temperature=None,
            top_p=None,
            top_k=None,
        )
    prompt_length = int(encoded["input_ids"].shape[-1])
    response = extractor.tokenizer.decode(
        sequence[0, prompt_length:], skip_special_tokens=True
    )
    match = re.search(r'"price_index"\s*:\s*(\d+)', response)
    return {
        "selected_price_index": agent._parse_index(response),
        "parse_valid": bool(match and 0 <= int(match.group(1)) < agent.env.n_prices),
        "raw_response": response,
        "prompt_token_count": prompt_length,
    }


def summarise_rows(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Summarise protocol-specific diversity and paired protocol disagreement."""
    by_protocol: dict[str, dict[str, Any]] = {}
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

    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["scenario_id"], {})[row["protocol"]] = row
    pairs = [
        values for values in grouped.values()
        if RAW_PROTOCOL in values and CHAT_PROTOCOL in values
        and values[RAW_PROTOCOL]["parse_valid"] and values[CHAT_PROTOCOL]["parse_valid"]
    ]
    different = sum(
        pair[RAW_PROTOCOL]["selected_price_index"] != pair[CHAT_PROTOCOL]["selected_price_index"]
        for pair in pairs
    )
    return {
        "by_protocol": by_protocol,
        "matched_protocol_pairs": len(pairs),
        "matched_protocol_different_actions": different,
        "matched_protocol_different_action_fraction": different / len(pairs) if pairs else None,
    }


def run_benchmark(
    extractor: HFActivationExtractor,
    *,
    seed: int = 0,
    protocol: str = "both",
) -> dict[str, Any]:
    """Evaluate each generated market history once for each selected protocol."""
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(1, env, persona=None, seed=seed)
    scenarios = generate_market_scenarios(seed)
    rows = []
    for scenario in scenarios:
        market_history = materialize_history(env, scenario)
        raw_prompt = agent._build_prompt(
            market_history, len(market_history), len(market_history) + 1
        )
        for protocol_label, prompt in protocol_prompts(raw_prompt, extractor.tokenizer, protocol).items():
            row = _generate_decision(extractor, agent, prompt)
            rows.append({
                "scenario_id": scenario.scenario_id,
                "scenario_seed": scenario.scenario_seed,
                "market_condition": scenario.market_condition,
                "history_length": len(market_history),
                "realised_action_indices": [list(actions) for actions in scenario.action_indices],
                "protocol": protocol_label,
                "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest(),
                "model_id": extractor.model_id,
                "model_revision": extractor.revision,
                "tokenizer_revision": extractor.tokenizer_revision,
                **row,
            })
    return {
        "schema_version": "hf-behavioural-responsiveness-benchmark-v1",
        "seed": seed,
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
        default="artifacts/interpretability/behavioural-responsiveness-benchmark.json",
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
            args.output, run_benchmark(extractor, seed=args.seed, protocol=args.protocol)
        )
    finally:
        extractor.close()


if __name__ == "__main__":
    main()
