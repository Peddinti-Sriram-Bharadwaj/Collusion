"""Paired, market-level competitor-price interventions for the HF pilot.

This module changes an *executed market action*, not a hidden activation. It
therefore supports causal claims about the specified price-history shock and a
subsequent decision, but not about an internal coordination mechanism.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

import numpy as np

from src.env import LogitBertrandEnv

from .activation_extractor import HFActivationExtractor
from .hf_episode import save_hf_trajectory
from .hf_pricing_adapter import HFPricingAgent


VALID_VARIANTS = ("control", "no_op", "undercut")


def _activation_distance(control: dict[str, Any], intervention: dict[str, Any]) -> dict[str, dict[str, float | None]]:
    """Summarize a response representation difference without interpreting it."""
    result: dict[str, dict[str, float | None]] = {}
    for layer, left in control.get("layer_vectors", {}).items():
        right = intervention.get("layer_vectors", {}).get(layer)
        if right is None:
            raise ValueError(f"Intervention response is missing layer {layer}.")
        left_array = np.asarray(left, dtype=float)
        right_array = np.asarray(right, dtype=float)
        if left_array.shape != right_array.shape:
            raise ValueError(f"Mismatched vectors at layer {layer}.")
        denominator = float(np.linalg.norm(left_array) * np.linalg.norm(right_array))
        cosine = None if denominator == 0.0 else float(np.dot(left_array, right_array) / denominator)
        result[str(layer)] = {
            "l2_distance": float(np.linalg.norm(left_array - right_array)),
            "cosine_similarity": cosine,
        }
    return result


def _decision_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Return next-response fields used by the paired comparison."""
    return {
        "agent_id": record["agent_id"],
        "round_id": record["round_id"],
        "proposed_action_index": record.get("proposed_action_index"),
        "executed_action_index": record.get("executed_action_index"),
        "price": record.get("price"),
        "profit": record.get("profit"),
        "parse_failed": record.get("parse_failed"),
        "eligible_for_analysis": record.get("eligible_for_analysis"),
        "full_prompt_hash": record.get("full_prompt_hash"),
        "input_token_ids_hash": record.get("input_token_ids_hash"),
    }


def _trajectories_match(control: dict[str, Any], no_op: dict[str, Any]) -> bool:
    """Check that recording a no-op did not change any market/model outcome."""
    if not (
        np.array_equal(control["price_history"], no_op["price_history"])
        and np.array_equal(control["profit_history"], no_op["profit_history"])
        and len(control["decisions"]) == len(no_op["decisions"])
    ):
        return False
    fields = (
        "proposed_action_index", "executed_action_index", "price", "profit",
        "raw_response", "full_prompt_hash", "input_token_ids_hash", "parse_failed",
        "eligible_for_analysis",
    )
    for left, right in zip(control["decisions"], no_op["decisions"], strict=True):
        if any(left.get(field) != right.get(field) for field in fields):
            return False
        if set(left.get("layer_vectors", {})) != set(right.get("layer_vectors", {})):
            return False
        if any(
            not np.array_equal(np.asarray(left["layer_vectors"][layer]), np.asarray(right["layer_vectors"][layer]))
            for layer in left.get("layer_vectors", {})
        ):
            return False
    return True


def _run_variant(
    extractor: HFActivationExtractor,
    *,
    variant: str,
    n_rounds: int,
    seed: int,
    episode_id: str,
    intervention_round: int,
    override_index: int,
    selected_layers: Sequence[int] | None,
    generation_parameters: dict[str, Any] | None,
) -> dict[str, Any]:
    """Run one matched trajectory, updating history from executed actions."""
    if variant not in VALID_VARIANTS:
        raise ValueError(f"Unknown variant {variant!r}; choose one of {VALID_VARIANTS}.")
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    if not 0 <= override_index < env.n_prices:
        raise ValueError(f"override_index must be in 0..{env.n_prices - 1}.")

    agents = [
        HFPricingAgent(
            agent_id=i,
            env=env,
            extractor=extractor,
            persona=None,
            seed=seed + i,
            selected_layers=selected_layers,
            generation_parameters=generation_parameters,
        )
        for i in range(2)
    ]
    history: list[tuple[np.ndarray, np.ndarray]] = []
    price_history = np.zeros((n_rounds, 2))
    profit_history = np.zeros((n_rounds, 2))
    decisions: list[dict[str, Any]] = []
    interventions: list[dict[str, Any]] = []
    n_parse_failures = 0

    for round_num in range(n_rounds):
        # Both agents receive precisely the same prior executed history; neither
        # sees its rival's current proposed action.
        round_decisions = [
            agent.act(
                history,
                round_num,
                n_rounds,
                episode_id=episode_id,
                market_seed=seed,
                generation_seed=seed + agent.agent_id,
            )
            for agent in agents
        ]
        proposed_actions = [decision.action_index for decision in round_decisions]
        executed_actions = list(proposed_actions)
        intervention = {
            "variant": variant,
            "round_id": round_num,
            "target_agent_id": 0,
            "requested_override_index": override_index if round_num == intervention_round else None,
            "proposed_action_index": proposed_actions[0] if round_num == intervention_round else None,
            "executed_action_index": proposed_actions[0] if round_num == intervention_round else None,
            "applied": False,
            "kind": "none",
        }
        if round_num == intervention_round:
            if variant == "no_op":
                intervention.update({"kind": "no_op", "applied": True})
            elif variant == "undercut":
                if round_decisions[0].parse_failed:
                    raise ValueError("Undercut requires a valid Agent 0 proposed action, not a fallback action.")
                if override_index >= proposed_actions[0]:
                    raise ValueError(
                        "Undercut requires override_index strictly below Agent 0's proposed action; "
                        f"got override={override_index}, proposed={proposed_actions[0]}."
                    )
                executed_actions[0] = override_index
                intervention.update({
                    "kind": "executed_price_override",
                    "applied": True,
                    "executed_action_index": override_index,
                })
            else:
                intervention["kind"] = "control"
        interventions.append(intervention)

        executed_tuple = tuple(executed_actions)
        prices = env.price_grid[np.asarray(executed_tuple)]
        profits = env._profits(prices)
        for agent_id, decision in enumerate(round_decisions):
            n_parse_failures += int(decision.parse_failed)
            record = decision.activation_record or {
                "episode_id": episode_id,
                "agent_id": agent_id,
                "round_id": round_num,
                "persona_id": None,
                "activation_status": "failed",
                "error": decision.error,
            }
            record["activation_status"] = "captured" if decision.activation_record else "failed"
            record.setdefault("parse_failed", True)
            record.setdefault("eligible_for_analysis", False)
            record.setdefault("decision_status", "generation_error")
            record["proposed_action_index"] = (
                proposed_actions[agent_id]
                if decision.activation_record and not decision.parse_failed
                else None
            )
            record["executed_action_index"] = executed_actions[agent_id]
            record["price"] = float(prices[agent_id])
            record["profit"] = float(profits[agent_id])
            record["market_intervention"] = deepcopy(intervention)
            decisions.append(record)

        # This is intentionally the executed counterfactual market outcome.
        history.append((prices.copy(), profits.copy()))
        price_history[round_num] = prices
        profit_history[round_num] = profits

    tail_window = max(1, n_rounds // 3)
    return {
        "schema_version": "hf-competitor-intervention-trajectory-v1",
        "variant": variant,
        "episode_id": episode_id,
        "market_seed": seed,
        "persona_configuration": [None, None],
        "model_id": extractor.model_id,
        "model_revision": extractor.revision,
        "tokenizer_revision": extractor.tokenizer_revision,
        "intervention_round": intervention_round,
        "override_index": override_index,
        "price_history": price_history,
        "profit_history": profit_history,
        "decisions": decisions,
        "interventions": interventions,
        "n_parse_failures": n_parse_failures,
        "delta": env.collusion_index(profit_history[-tail_window:].mean(axis=0)),
        "p_nash": env.p_nash,
        "p_monop": env.p_monop,
    }


def run_paired_competitor_price_intervention(
    extractor: HFActivationExtractor,
    *,
    n_rounds: int = 5,
    seed: int = 0,
    intervention_round: int = 1,
    override_index: int = 0,
    selected_layers: Sequence[int] | None = None,
    generation_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run matched control, no-op, and undercut trajectories.

    Agent 1's response in ``intervention_round + 1`` is the pre-specified
    behavioural endpoint. The representation summary is descriptive: a market
    shock can causally change a later prompt and decision, but this experiment
    alone does not establish a causal hidden-state mechanism.
    """
    if n_rounds < 2 or not 0 <= intervention_round < n_rounds - 1:
        raise ValueError("intervention_round must leave at least one subsequent response round.")
    common = {
        "n_rounds": n_rounds,
        "seed": seed,
        "intervention_round": intervention_round,
        "override_index": override_index,
        "selected_layers": selected_layers,
        "generation_parameters": generation_parameters,
    }
    trajectories = {
        variant: _run_variant(extractor, variant=variant, episode_id=f"hf-{variant}-{seed}", **common)
        for variant in VALID_VARIANTS
    }
    response_round = intervention_round + 1
    response_records = {
        variant: next(
            record for record in trajectory["decisions"]
            if record["agent_id"] == 1 and record["round_id"] == response_round
        )
        for variant, trajectory in trajectories.items()
    }
    control = response_records["control"]
    noop = response_records["no_op"]
    undercut = response_records["undercut"]
    no_op_equivalent = _trajectories_match(trajectories["control"], trajectories["no_op"])
    return {
        "schema_version": "hf-paired-competitor-intervention-v1",
        "engineering_pilot": True,
        "causal_scope": (
            "This manipulates an executed market price and measures a later response. "
            "Activation differences are descriptive and do not identify a causal internal mechanism."
        ),
        "design": {
            "personas": [None, None],
            "n_agents": 2,
            "n_rounds": n_rounds,
            "seed": seed,
            "intervention_round": intervention_round,
            "response_round": response_round,
            "target_agent_id": 0,
            "response_agent_id": 1,
            "override_index": override_index,
            "variants": list(VALID_VARIANTS),
        },
        "trajectories": trajectories,
        "response_comparison": {
            "control": _decision_summary(control),
            "no_op": _decision_summary(noop),
            "undercut": _decision_summary(undercut),
            "no_op_matches_control": no_op_equivalent,
            "undercut_minus_control_activation": _activation_distance(control, undercut),
        },
    }


def save_paired_competitor_intervention(path: str, result: dict[str, Any]) -> None:
    """Save an ignored local artifact using the shared NumPy-safe serializer."""
    save_hf_trajectory(path, result)
