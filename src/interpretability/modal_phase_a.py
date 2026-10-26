"""Pure, testable design and execution helpers for the Modal Phase A pilot.

This is intentionally an HF-only research path.  It neither imports nor
changes the Ollama experiment implementation.  Phase A tests behavioural
responses to matched *displayed* rival-price histories; it does not collect
activations or make claims about collusion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

import numpy as np
import torch

from src.env import LogitBertrandEnv
from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.strict_pricing_parser import parse_strict_price_response
from src.llm_agent import LLMPricingAgent

PHASE_A_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
PHASE_A_MODEL_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
PHASE_A_PROTOCOL = "qwen_chat_template_v1"
GENERATION_KWARGS = {"do_sample": False, "max_new_tokens": 32, "temperature": None, "top_p": None, "top_k": None}
MODAL_GPU = "A10"
MODAL_TIMEOUT_SECONDS = 1200
MODAL_SCALEDOWN_SECONDS = 30
MODAL_MAX_CONTAINERS = 1
MODAL_HF_CACHE_PATH = "/root/.cache/huggingface"
CONTROL_AUDIT_NONCE = 314159
NEGATIVE_CONTROL_AUDIT_NONCE = 271828
NEGATIVE_CONTROL_PAIR_ID = "phase-a-000"


def phase_a_loader_kwargs(cache_dir: str = MODAL_HF_CACHE_PATH) -> dict[str, Any]:
    """The exact, pinned Hugging Face loading contract for the Modal job."""
    return {
        "model_id": PHASE_A_MODEL_ID,
        "revision": PHASE_A_MODEL_REVISION,
        "device_map": "auto",
        "torch_dtype": torch.float16,
        "local_files_only": False,
        "cache_dir": cache_dir,
    }


@dataclass(frozen=True)
class PhaseAPair:
    """A legal replay plus a rival-price-only synthetic display intervention."""

    pair_id: str
    scenario_seed: int
    own_price_index: int
    rival_pattern: str
    history_variant: int
    intervention_label: str
    action_indices: tuple[tuple[int, int], ...]
    displayed_rival_final_index: int


def generate_phase_a_pairs(seed: int = 20261023) -> list[PhaseAPair]:
    """Make 24 fixed, reproducible pairs: 3 own x 4 rival histories x 2 shifts.

    Each control trajectory contains four legal joint actions.  Its paired
    synthetic row replaces only the *final displayed rival price* with grid
    index 0 (undercut) or 9 (raise), preserving the original own-price and
    own-profit text.  Thus controls are market-consistent and interventions
    are intentionally labelled as information interventions, not realised
    market transitions.
    """
    rival_patterns = {
        "persistent_low": ((1, 1, 1, 1), (2, 2, 2, 2)),
        "persistent_high": ((7, 7, 7, 7), (8, 8, 8, 8)),
        "rising": ((1, 3, 5, 6), (2, 4, 6, 7)),
        "falling": ((7, 5, 3, 2), (8, 6, 4, 3)),
    }
    pairs: list[PhaseAPair] = []
    serial = 0
    for own_index in (2, 5, 8):
        for pattern_name, variants in rival_patterns.items():
            for variant, rival_indices in enumerate(variants):
                legal_actions = tuple((rival, own_index) for rival in rival_indices)
                label, final_index = (("rival_final_undercut", 0) if variant == 0 else ("rival_final_raise", 9))
                pairs.append(PhaseAPair(
                    pair_id=f"phase-a-{serial:03d}", scenario_seed=seed + serial,
                    own_price_index=own_index, rival_pattern=pattern_name, history_variant=variant,
                    intervention_label=label, action_indices=legal_actions,
                    displayed_rival_final_index=final_index,
                ))
                serial += 1
    return pairs


def validate_phase_a_design(pairs: Iterable[PhaseAPair]) -> dict[str, int]:
    """Reject accidental duplication or an intervention with no price change."""
    pairs = list(pairs)
    if len(pairs) != 24 or len({pair.pair_id for pair in pairs}) != 24:
        raise ValueError("Phase A must contain exactly 24 uniquely identified pairs.")
    if len({pair.action_indices for pair in pairs}) != 24:
        raise ValueError("Phase A controls must be distinct; duplicated controls are not independent pairs.")
    decreases = increases = 0
    for pair in pairs:
        if len(pair.action_indices) != 4:
            raise ValueError(f"{pair.pair_id} does not have a four-round control history.")
        original = pair.action_indices[-1][0]
        if pair.displayed_rival_final_index < original:
            decreases += 1
        elif pair.displayed_rival_final_index > original:
            increases += 1
        else:
            raise ValueError(f"{pair.pair_id} intervention does not change its final rival price.")
    if decreases != 12 or increases != 12:
        raise ValueError("Phase A requires 12 displayed-rival decreases and 12 increases.")
    return {"n_pairs": len(pairs), "displayed_rival_price_decreases": decreases, "displayed_rival_price_increases": increases}


def materialize_control_history(env: LogitBertrandEnv, pair: PhaseAPair) -> list[tuple[np.ndarray, np.ndarray]]:
    """Replay the control sequence through the original environment API."""
    env.reset(np.random.default_rng(pair.scenario_seed))
    history: list[tuple[np.ndarray, np.ndarray]] = []
    for actions in pair.action_indices:
        _, profits, info = env.step(actions)
        history.append((np.asarray(info["prices"]).copy(), np.asarray(profits).copy()))
    return history


def _modified_display_history(history: list[tuple[np.ndarray, np.ndarray]], rival_price: float) -> list[tuple[np.ndarray, np.ndarray]]:
    """Copy a history and edit only final rival-price display data for agent 1."""
    displayed = [(prices.copy(), profits.copy()) for prices, profits in history]
    prices, profits = displayed[-1]
    prices[0] = rival_price
    # Deliberately do not recompute profits: this is the controlled synthetic
    # rival-price-only condition, not a legal realised environment transition.
    displayed[-1] = (prices, profits)
    return displayed


def best_response_index(env: LogitBertrandEnv, rival_price: float) -> tuple[int, float]:
    """Static grid best response for agent 1 against a supplied rival price.

    Assumes a one-shot next-round decision, the environment's fixed demand and
    costs, and no value from future rounds/history.  It is an economic
    comparator, not a normative label or a model of the prompted objective.
    """
    profits = [float(env._profits(np.asarray([rival_price, own_price]))[1]) for own_price in env.price_grid]
    index = int(np.argmax(profits))
    return index, profits[index]


def _with_audit_nonce(raw_prompt: str, nonce: int) -> str:
    """Attach constant-format, non-economic metadata for the negative control.

    The nonce is explicitly excluded from market semantics and appears in every
    Phase A prompt.  The negative control changes only its value.
    """
    return raw_prompt + (
        "\n\n[Research audit metadata only; not a price, profit, action index, "
        f"market parameter, or instruction. audit_nonce={nonce}]"
    )


def _chat_prompt(raw_prompt: str, tokenizer: Any) -> str:
    if not hasattr(tokenizer, "apply_chat_template"):
        raise RuntimeError("The selected tokenizer does not provide a chat template.")
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": raw_prompt}], tokenize=False, add_generation_prompt=True,
    )


def _generate(extractor: HFActivationExtractor, prompt: str, n_prices: int) -> dict[str, Any]:
    """One deterministic, no-gradient decision from the shared model instance."""
    encoded = extractor._prepare_inputs(prompt)
    with torch.inference_mode():
        sequence = extractor.model.generate(**encoded, **GENERATION_KWARGS)
    prompt_tokens = int(encoded["input_ids"].shape[-1])
    response = extractor.tokenizer.decode(sequence[0, prompt_tokens:], skip_special_tokens=True)
    parsed = parse_strict_price_response(response, n_prices)
    return {
        **parsed.to_dict(), "parse_valid": parsed.analysis_eligible,
        "raw_response": response, "prompt_token_count": prompt_tokens,
    }


def _memory(extractor: HFActivationExtractor) -> dict[str, Any]:
    callback = getattr(extractor, "memory_snapshot", None)
    return callback() if callable(callback) else {"cuda_available": False}


def _model_metadata(extractor: HFActivationExtractor) -> dict[str, Any]:
    model = extractor.model
    config = getattr(model, "config", None)
    tokenizer = extractor.tokenizer
    return {
        "model_id": extractor.model_id,
        "requested_model_revision": extractor.revision,
        "reported_model_revision": getattr(config, "_commit_hash", None) or extractor.revision,
        "requested_tokenizer_revision": extractor.tokenizer_revision,
        "reported_tokenizer_revision": getattr(tokenizer, "init_kwargs", {}).get("_commit_hash") or extractor.tokenizer_revision,
        "model_device": str(getattr(model, "device", None)),
        "hf_device_map": None if getattr(model, "hf_device_map", None) is None else {str(k): str(v) for k, v in model.hf_device_map.items()},
        "shared_model_instances": 1,
    }


def _row(
    extractor: HFActivationExtractor, agent: LLMPricingAgent, pair: PhaseAPair,
    history: list[tuple[np.ndarray, np.ndarray]], condition: str, market_consistent: bool,
    audit_nonce: int = CONTROL_AUDIT_NONCE,
) -> dict[str, Any]:
    started_at = perf_counter()
    raw_prompt = _with_audit_nonce(agent._build_prompt(history, len(history), len(history) + 1), audit_nonce)
    prompt = _chat_prompt(raw_prompt, extractor.tokenizer)
    rival_price = float(history[-1][0][0])
    baseline_index, baseline_profit = best_response_index(agent.env, rival_price)
    decision = _generate(extractor, prompt, agent.env.n_prices)
    selected = decision["selected_price_index"]
    return {
        "pair_id": pair.pair_id, "scenario_seed": pair.scenario_seed,
        "condition": condition, "market_consistent": market_consistent,
        "intervention_label": (pair.intervention_label if not market_consistent else
            ("negative_control_audit_nonce_only" if condition == "negative_control_audit_nonce" else "none")),
        "audit_nonce": audit_nonce,
        "rival_pattern": pair.rival_pattern, "history_variant": pair.history_variant, "own_price_index": pair.own_price_index,
        "control_action_indices": [list(actions) for actions in pair.action_indices],
        "displayed_final_rival_price": rival_price,
        "history": [{"prices": prices.tolist(), "profits": profits.tolist()} for prices, profits in history],
        "raw_prompt": raw_prompt, "model_prompt": prompt,
        "raw_prompt_hash": sha256(raw_prompt.encode()).hexdigest(), "prompt_hash": sha256(prompt.encode()).hexdigest(),
        "protocol": PHASE_A_PROTOCOL,
        "one_shot_best_response_index": baseline_index,
        "one_shot_best_response_profit": baseline_profit,
        "selected_minus_best_response_index": None if selected is None else selected - baseline_index,
        "selected_minus_best_response_price": None if selected is None else float(agent.env.price_grid[selected] - agent.env.price_grid[baseline_index]),
        "selected_price": None if selected is None else float(agent.env.price_grid[selected]),
        "decision_wall_clock_seconds": perf_counter() - started_at,
        **decision,
    }


def summarise_phase_a(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["pair_id"], {})[row["condition"]] = row
    comparable = [group for group in groups.values() if {"control_realistic", "synthetic_rival_price_only"} <= set(group)]
    valid_pairs = [group for group in comparable if all(row["analysis_eligible"] for row in group.values())]
    deltas = [group["synthetic_rival_price_only"]["selected_price_index"] - group["control_realistic"]["selected_price_index"] for group in valid_pairs]
    return {
        "n_rows": len(rows), "n_pairs": len(comparable),
        "n_valid_rows": sum(bool(row["analysis_eligible"]) for row in rows),
        "n_invalid_rows": sum(not bool(row["analysis_eligible"]) for row in rows),
        "n_valid_pairs": len(valid_pairs),
        "paired_action_differences": sum(delta != 0 for delta in deltas),
        "paired_signed_index_changes": deltas,
        "mean_signed_index_change": float(np.mean(deltas)) if deltas else None,
    }


def run_phase_a(extractor: HFActivationExtractor, *, seed: int = 20261023, smoke_only: bool = False) -> dict[str, Any]:
    """Run 48 core decisions plus one predeclared negative-control decision.

    Smoke mode executes one complete pair and that pair's negative control.
    """
    start = perf_counter()
    pairs = generate_phase_a_pairs(seed)
    design_checks = validate_phase_a_design(pairs)
    if smoke_only:
        pairs = pairs[:1]
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(1, env, persona=None, seed=seed)
    rows: list[dict[str, Any]] = []
    try:
        for pair in pairs:
            control = materialize_control_history(env, pair)
            synthetic = _modified_display_history(control, float(env.price_grid[pair.displayed_rival_final_index]))
            rows.append(_row(extractor, agent, pair, control, "control_realistic", True))
            rows.append(_row(extractor, agent, pair, synthetic, "synthetic_rival_price_only", False))
            if pair.pair_id == NEGATIVE_CONTROL_PAIR_ID:
                rows.append(_row(
                    extractor, agent, pair, control, "negative_control_audit_nonce", True,
                    audit_nonce=NEGATIVE_CONTROL_AUDIT_NONCE,
                ))
        status = "completed"
        error = None
    except Exception as exc:
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"
    return {
        "schema_version": "modal-phase-a-behavioural-v1", "seed": seed, "smoke_only": smoke_only,
        "model": _model_metadata(extractor), "protocol": PHASE_A_PROTOCOL,
        "deterministic_generation": True, "activation_extraction": False,
        "pairs": [asdict(pair) for pair in pairs], "design_checks": design_checks,
        "rows": rows, "summary": summarise_phase_a(rows),
        "best_response_assumptions": "Static one-shot grid maximization for agent 1 against the displayed final rival price; fixed LogitBertrandEnv demand/costs; no dynamic value or history effect.",
        "execution": {"status": status, "error": error, "wall_clock_seconds": perf_counter() - start, "peak_cuda_memory": _memory(extractor)},
    }


def save_phase_a_artifact(path: str | Path, result: dict[str, Any]) -> Path:
    """Persist a returned remote result locally, never in the Modal container only."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return destination


def phase_a_remote_failure_artifact(error: Exception, wall_clock_seconds: float) -> dict[str, Any]:
    """A serialisable failure result so Modal's local entrypoint can save it."""
    return {
        "schema_version": "modal-phase-a-behavioural-v1",
        "model": {
            "model_id": PHASE_A_MODEL_ID,
            "requested_model_revision": PHASE_A_MODEL_REVISION,
            "requested_tokenizer_revision": PHASE_A_MODEL_REVISION,
        },
        "rows": [],
        "summary": summarise_phase_a([]),
        "execution": {
            "status": "failed",
            "error": f"{type(error).__name__}: {error}",
            "wall_clock_seconds": wall_clock_seconds,
            "peak_cuda_memory": {"cuda_available": None},
        },
    }
