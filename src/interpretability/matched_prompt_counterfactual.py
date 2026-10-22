"""Matched prompt-information counterfactuals for a saved market intervention.

The synthetic conditions here are deliberately *not* market trajectories: they
modify the information in one already-observed prompt to separate the textual
price and profit consequences of a prior market shock.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from src.env import LogitBertrandEnv
from src.llm_agent import LLMPricingAgent

from .activation_extractor import HFActivationExtractor
from .hf_episode import save_hf_trajectory
from .hf_pricing_adapter import representative_layers
from .representation_dataset import DecisionMetadata, aligned_record, persona_prompt_hash


_HISTORY_LINE = re.compile(
    r"^(Round \d+: you priced \$\d+\.\d{2} \(profit )"
    r"(?P<profit>\d+\.\d{3})"
    r"(?P<middle>\); rival price\(s\): )"
    r"(?P<rivals>\$\d+\.\d{2}(?:, \$\d+\.\d{2})*)$"
)


def _one_changed_history_line(control_prompt: str, undercut_prompt: str) -> tuple[int, re.Match[str], re.Match[str]]:
    """Validate that the observed prompts differ in exactly one history line."""
    control_lines = control_prompt.splitlines()
    undercut_lines = undercut_prompt.splitlines()
    if len(control_lines) != len(undercut_lines):
        raise ValueError("Control and undercut prompts differ in line count.")
    changed = [index for index, pair in enumerate(zip(control_lines, undercut_lines, strict=True)) if pair[0] != pair[1]]
    if len(changed) != 1:
        raise ValueError("Expected exactly one changed history line between control and undercut prompts.")
    index = changed[0]
    control_match = _HISTORY_LINE.fullmatch(control_lines[index])
    undercut_match = _HISTORY_LINE.fullmatch(undercut_lines[index])
    if control_match is None or undercut_match is None:
        raise ValueError("The changed prompt line is not a recognized stateless-history line.")
    if control_match.group(1) != undercut_match.group(1) or control_match.group("middle") != undercut_match.group("middle"):
        raise ValueError("The changed history lines differ outside own-profit and rival-price fields.")
    return index, control_match, undercut_match


def derive_matched_prompt_conditions(control_prompt: str, undercut_prompt: str) -> dict[str, dict[str, Any]]:
    """Create original, actual, and two single-field synthetic prompt conditions."""
    line_index, control_match, undercut_match = _one_changed_history_line(control_prompt, undercut_prompt)
    control_lines = control_prompt.splitlines()

    rival_only_line = (
        control_match.group(1) + control_match.group("profit") + control_match.group("middle")
        + undercut_match.group("rivals")
    )
    profit_only_line = (
        control_match.group(1) + undercut_match.group("profit") + control_match.group("middle")
        + control_match.group("rivals")
    )
    rival_only_lines = control_lines.copy()
    profit_only_lines = control_lines.copy()
    rival_only_lines[line_index] = rival_only_line
    profit_only_lines[line_index] = profit_only_line

    conditions = {
        "A_original_control": {
            "prompt": control_prompt,
            "information_status": "observed_market_history",
            "modified_fields": [],
        },
        "B_actual_market_undercut": {
            "prompt": undercut_prompt,
            "information_status": "observed_market_history",
            "modified_fields": ["own_profit", "rival_price"],
        },
        "C_synthetic_rival_price_only": {
            "prompt": "\n".join(rival_only_lines),
            "information_status": "synthetic_information_intervention",
            "modified_fields": ["rival_price"],
        },
        "D_synthetic_own_profit_only": {
            "prompt": "\n".join(profit_only_lines),
            "information_status": "synthetic_information_intervention",
            "modified_fields": ["own_profit"],
        },
        "negative_identical_control": {
            "prompt": control_prompt,
            "information_status": "negative_control_identical_prompt",
            "modified_fields": [],
        },
    }
    _validate_condition_edits(conditions, control_prompt, undercut_prompt)
    return conditions


def _validate_condition_edits(
    conditions: Mapping[str, Mapping[str, Any]], control_prompt: str, undercut_prompt: str,
) -> None:
    """Fail if a synthetic condition changes anything beyond its named field."""
    index, control_match, undercut_match = _one_changed_history_line(control_prompt, undercut_prompt)
    control_lines = control_prompt.splitlines()
    for name, fields in (("C_synthetic_rival_price_only", {"rival_price"}), ("D_synthetic_own_profit_only", {"own_profit"})):
        candidate_lines = str(conditions[name]["prompt"]).splitlines()
        if len(candidate_lines) != len(control_lines):
            raise ValueError(f"{name} changed prompt line count.")
        changed = [i for i, pair in enumerate(zip(control_lines, candidate_lines, strict=True)) if pair[0] != pair[1]]
        if changed != [index]:
            raise ValueError(f"{name} modified fields outside the designated history line.")
        match = _HISTORY_LINE.fullmatch(candidate_lines[index])
        if match is None or match.group(1) != control_match.group(1) or match.group("middle") != control_match.group("middle"):
            raise ValueError(f"{name} modified immutable history-line text.")
        if "rival_price" in fields:
            if match.group("profit") != control_match.group("profit") or match.group("rivals") != undercut_match.group("rivals"):
                raise ValueError(f"{name} did not isolate the rival-price change.")
        if "own_profit" in fields:
            if match.group("profit") != undercut_match.group("profit") or match.group("rivals") != control_match.group("rivals"):
                raise ValueError(f"{name} did not isolate the own-profit change.")
    if conditions["negative_identical_control"]["prompt"] != control_prompt:
        raise ValueError("Negative control must be byte-identical to the original control prompt.")


def load_agent1_round3_context(path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load Agent 1's human-round-3 prompts from a paired intervention artifact."""
    artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    design = artifact.get("design", {})
    expected_round = int(design.get("response_round", 2))
    try:
        control = next(
            record for record in artifact["trajectories"]["control"]["decisions"]
            if record["agent_id"] == 1 and record["round_id"] == expected_round
        )
        undercut = next(
            record for record in artifact["trajectories"]["undercut"]["decisions"]
            if record["agent_id"] == 1 and record["round_id"] == expected_round
        )
    except (KeyError, StopIteration) as exc:
        raise ValueError("Artifact does not contain Agent 1's specified response context.") from exc
    if not isinstance(control.get("prompt"), str) or not isinstance(undercut.get("prompt"), str):
        raise ValueError("Artifact lacks exact prompt text required for matched counterfactuals.")
    return control, undercut


def _metrics(reference: Mapping[str, np.ndarray], candidate: Mapping[str, np.ndarray]) -> dict[str, dict[str, float | None]]:
    result: dict[str, dict[str, float | None]] = {}
    for layer, reference_vector in reference.items():
        candidate_vector = candidate.get(layer)
        if candidate_vector is None:
            raise ValueError(f"Missing candidate layer {layer}.")
        left = np.asarray(reference_vector, dtype=float)
        right = np.asarray(candidate_vector, dtype=float)
        if left.shape != right.shape:
            raise ValueError(f"Mismatched shape at layer {layer}.")
        reference_norm = float(np.linalg.norm(left))
        candidate_norm = float(np.linalg.norm(right))
        l2 = float(np.linalg.norm(right - left))
        result[str(layer)] = {
            "l2_distance": l2,
            "normalized_l2_distance": None if reference_norm == 0.0 else l2 / reference_norm,
            "cosine_similarity": None if reference_norm == 0.0 or candidate_norm == 0.0 else float(np.dot(left, right) / (reference_norm * candidate_norm)),
            "reference_norm": reference_norm,
            "condition_norm": candidate_norm,
        }
    return result


def run_matched_prompt_counterfactuals(
    extractor: HFActivationExtractor,
    *,
    control_context: Mapping[str, Any],
    undercut_context: Mapping[str, Any],
    selected_layers: Sequence[int] | None = None,
    generation_parameters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate five matched prompts; synthetic prompts never update a market."""
    control_prompt = str(control_context["prompt"])
    undercut_prompt = str(undercut_context["prompt"])
    conditions = derive_matched_prompt_conditions(control_prompt, undercut_prompt)
    env = LogitBertrandEnv(n_agents=2, n_prices=int(control_context["n_prices"]))
    parser = LLMPricingAgent(agent_id=1, env=env, persona=None, seed=int(control_context["market_seed"]) + 1)
    layers = tuple(selected_layers or representative_layers(extractor))
    generation = dict(generation_parameters or {
        "do_sample": False, "max_new_tokens": 32, "temperature": None, "top_p": None, "top_k": None,
    })
    records: dict[str, dict[str, Any]] = {}
    for name, condition in conditions.items():
        prompt = str(condition["prompt"])
        capture, text = extractor.generate_with_capture(prompt, layers, generation)
        match = re.search(r'"price_index"\s*:\s*(\d+)', text)
        parse_failed = match is None or not (0 <= int(match.group(1)) < env.n_prices)
        action = parser._parse_index(text)
        metadata = DecisionMetadata(
            episode_id=f"matched-prompt-{control_context['episode_id']}",
            market_seed=int(control_context["market_seed"]),
            generation_seed=control_context.get("generation_seed"),
            agent_id=1,
            round_id=int(control_context["round_id"]),
            persona_id=None,
            persona_prompt_hash=persona_prompt_hash(None),
            full_prompt_hash=sha256(prompt.encode("utf-8")).hexdigest(),
            input_token_ids_hash=capture.input_token_ids_hash,
            prompt_token_count=capture.prompt_token_count,
            n_agents=2,
            n_prices=env.n_prices,
            n_rounds=int(control_context["n_rounds"]),
            agent_mode="stateless",
            prompt_format="raw_repository_stateless_v1",
            model_id=extractor.model_id,
            model_revision=extractor.revision,
            tokenizer_revision=extractor.tokenizer_revision,
            backend="huggingface",
            quantization=None,
            generation_parameters=generation,
            warning=False,
            peer_info=None,
            fixed_agent_ids=(),
            veto=False,
            veto_margin_fraction=0.3,
            proposed_action_index=None if parse_failed else action,
            executed_action_index=None,
        )
        record = aligned_record(metadata, capture)
        record.update({
            "condition": name,
            "information_status": condition["information_status"],
            "modified_fields": condition["modified_fields"],
            "prompt": prompt,
            "raw_response": text,
            "parse_failed": parse_failed,
            "eligible_for_analysis": not parse_failed,
            "selected_action_index": action,
            "decision_status": "valid" if not parse_failed else "invalid_parse",
            "source_control_prompt_hash": control_context["full_prompt_hash"],
            "source_undercut_prompt_hash": undercut_context["full_prompt_hash"],
        })
        records[name] = record
    reference_vectors = {int(layer): np.asarray(vector) for layer, vector in records["A_original_control"]["layer_vectors"].items()}
    comparisons = {
        name: _metrics(reference_vectors, {int(layer): np.asarray(vector) for layer, vector in record["layer_vectors"].items()})
        for name, record in records.items()
    }
    return {
        "schema_version": "hf-matched-prompt-counterfactual-v1",
        "engineering_pilot": True,
        "interpretation_scope": (
            "Synthetic conditions alter prompt information only; representation differences are descriptive "
            "and are not collusion labels or evidence of a causal internal mechanism."
        ),
        "source": {
            "control_prompt_hash": control_context["full_prompt_hash"],
            "undercut_prompt_hash": undercut_context["full_prompt_hash"],
            "response_agent_id": 1,
            "response_round_id": control_context["round_id"],
        },
        "conditions": records,
        "comparisons_to_A_original_control": comparisons,
    }


def save_matched_prompt_counterfactuals(path: str | Path, result: dict[str, Any]) -> None:
    """Save a local JSON artifact with NumPy vectors handled by shared serializer."""
    save_hf_trajectory(path, result)
