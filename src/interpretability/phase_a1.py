"""Phase A.1: revised rival-price pilot with action scoring and activation capture.

Changes relative to Phase A (``modal_phase_a``), motivated by the CPU economic
preflight (artifacts/interpretability/phase_a_preflight/README.md):

* every control history gets BOTH a rival undercut (index 0) and a raise (index 9),
  removing the direction/history-variant confound;
* each edit appears in two arms: ``synthetic_stale_profit`` (Phase A's edit: rival
  price changed, own profit text left stale) and ``realistic_rival_final`` (the
  rival's final action really is 0/9; profits recomputed through the environment);
* every control has its own audit-nonce negative control;
* the primary outcome is the model's distribution over the 10 single-token digits
  after the forced answer prefix ``{"price_index": ``; greedy generation with the
  strict parser is retained as the validity check;
* the same forward pass optionally captures residual-stream hidden states at the
  answer position and at the final displayed rival-price tokens (for Phase B/C).

The Phase A module and the Ollama path are not modified.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable, Sequence

import numpy as np
import torch

from src.env import LogitBertrandEnv
from src.interpretability.modal_phase_a import (
    CONTROL_AUDIT_NONCE, GENERATION_KWARGS, NEGATIVE_CONTROL_AUDIT_NONCE,
    _chat_prompt, _modified_display_history, _with_audit_nonce,
    generate_phase_a_pairs,
)
from src.interpretability.strict_pricing_parser import parse_strict_price_response
from src.llm_agent import LLMPricingAgent

SCHEMA_VERSION = "phase-a1-v1"
PROTOCOL = "qwen_chat_template_v1"
ANSWER_PREFIX = '{"price_index": '
EDITS = (("undercut", 0), ("raise", 9))
RIVAL_MARKER = "rival price(s): $"


@dataclass
class A1Row:
    row_id: str
    control_id: str
    condition: str
    edit_direction: str | None
    market_consistent: bool
    audit_nonce: int
    own_price_index: int
    rival_pattern: str
    history_variant: int
    action_indices: list
    displayed_final_rival_index: int
    history: list  # [(prices ndarray, profits ndarray), ...] as displayed


def replay(env: LogitBertrandEnv, actions: Sequence[tuple[int, int]], seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Legal environment replay of (rival, own) joint actions."""
    env.reset(np.random.default_rng(seed))
    out = []
    for joint in actions:
        _, profits, info = env.step(tuple(joint))
        out.append((np.asarray(info["prices"]).copy(), np.asarray(profits).copy()))
    return out


def build_phase_a1_rows(env: LogitBertrandEnv, seed: int = 20261023) -> list[A1Row]:
    """24 controls x (control, nonce, 2 edits x 2 arms) = 144 rows."""
    rows: list[A1Row] = []
    for pair in generate_phase_a_pairs(seed):
        base = dict(control_id=pair.pair_id, own_price_index=pair.own_price_index,
                    rival_pattern=pair.rival_pattern, history_variant=pair.history_variant)
        actions = [list(a) for a in pair.action_indices]
        ctrl = replay(env, pair.action_indices, pair.scenario_seed)
        final = pair.action_indices[-1][0]
        rows.append(A1Row(f"{pair.pair_id}-control", condition="control_realistic", edit_direction=None,
                          market_consistent=True, audit_nonce=CONTROL_AUDIT_NONCE, action_indices=actions,
                          displayed_final_rival_index=final, history=ctrl, **base))
        rows.append(A1Row(f"{pair.pair_id}-nonce", condition="negative_control_audit_nonce", edit_direction=None,
                          market_consistent=True, audit_nonce=NEGATIVE_CONTROL_AUDIT_NONCE, action_indices=actions,
                          displayed_final_rival_index=final, history=ctrl, **base))
        for direction, idx in EDITS:
            if idx == final:
                raise ValueError(f"{pair.pair_id}: edit to {idx} does not change the rival price")
            stale = _modified_display_history(ctrl, float(env.price_grid[idx]))
            rows.append(A1Row(f"{pair.pair_id}-{direction}-stale", condition="synthetic_stale_profit",
                              edit_direction=direction, market_consistent=False, audit_nonce=CONTROL_AUDIT_NONCE,
                              action_indices=actions, displayed_final_rival_index=idx, history=stale, **base))
            real_actions = [tuple(a) for a in pair.action_indices[:-1]] + [(idx, pair.own_price_index)]
            real = replay(env, real_actions, pair.scenario_seed)
            rows.append(A1Row(f"{pair.pair_id}-{direction}-real", condition="realistic_rival_final",
                              edit_direction=direction, market_consistent=True, audit_nonce=CONTROL_AUDIT_NONCE,
                              action_indices=[list(a) for a in real_actions], displayed_final_rival_index=idx,
                              history=real, **base))
    return rows


def raw_prompt(agent: LLMPricingAgent, row: A1Row) -> str:
    n = len(row.history)
    return _with_audit_nonce(agent._build_prompt(row.history, n, n + 1), row.audit_nonce)


def best_response_profile(env: LogitBertrandEnv, rival_index: int) -> dict[str, Any]:
    rival = float(env.price_grid[rival_index])
    profits = np.array([env._profits(np.array([rival, p]))[1] for p in env.price_grid])
    best = int(np.argmax(profits))
    return {"best_response_index": best,
            "eps1_optimal_set": [int(i) for i in np.where(profits >= 0.99 * profits[best])[0]],
            "own_profit_by_index": profits.tolist()}


# ---------------------------------------------------------------------------
# Tokenizer helpers
# ---------------------------------------------------------------------------
def digit_token_ids(tokenizer: Any, n_prices: int = 10) -> list[int]:
    ids = []
    for d in range(n_prices):
        enc = tokenizer.encode(str(d), add_special_tokens=False)
        if len(enc) != 1:
            raise ValueError(f"Digit {d} is not a single token ({enc}); digit scoring is invalid for this tokenizer.")
        ids.append(enc[0])
    return ids


def answer_prefix_ids(tokenizer: Any, digit_ids: Sequence[int]) -> list[int]:
    """Token ids of ANSWER_PREFIX exactly as they appear before a digit answer."""
    full = tokenizer.encode(ANSWER_PREFIX + "0", add_special_tokens=False)
    if full[-1] != digit_ids[0]:
        raise ValueError("Answer prefix does not tokenize with the digit as a separate final token.")
    return list(full[:-1])


def rival_price_token_positions(tokenizer: Any, prompt: str) -> list[int]:
    """Token positions covering the final displayed rival price (e.g. '1.42')."""
    start = prompt.rfind(RIVAL_MARKER)
    if start < 0:
        raise ValueError("Prompt has no rival-price field.")
    start += len(RIVAL_MARKER)
    end = start
    while end < len(prompt) and (prompt[end].isdigit() or prompt[end] == "."):
        end += 1
    enc = tokenizer(prompt, add_special_tokens=False, return_offsets_mapping=True)
    positions = [i for i, (a, b) in enumerate(enc["offset_mapping"]) if b > start and a < end]
    if not positions:
        raise ValueError("Rival price characters map to no tokens.")
    return positions


# ---------------------------------------------------------------------------
# Model calls
# ---------------------------------------------------------------------------
def _device(model: Any):
    dev = getattr(model, "device", None)
    return dev if dev is not None else "cpu"


def score_digits(model: Any, input_ids: Sequence[int], digit_ids: Sequence[int],
                 capture_positions: dict[str, Sequence[int]] | None = None,
                 hooks: Iterable[Any] = ()) -> dict[str, Any]:
    """One forward pass over prompt+answer prefix; distribution over digit tokens.

    ``capture_positions`` maps names to token positions; for each name the hidden
    states (all layers incl. embeddings) are averaged over those positions.
    """
    ids = torch.tensor([list(input_ids)], device=_device(model))
    want_hidden = bool(capture_positions)
    with torch.inference_mode():
        out = model(input_ids=ids, output_hidden_states=want_hidden, use_cache=False)
    logp = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
    dlogp = logp[torch.tensor(list(digit_ids), device=logp.device)]
    mass = float(dlogp.exp().sum())
    probs = torch.softmax(dlogp, dim=-1).cpu().numpy().astype(float)
    result = {
        "digit_probs": probs.tolist(),
        "digit_logprobs": dlogp.cpu().numpy().astype(float).tolist(),
        "digit_mass": mass,
        "expected_index": float((probs * np.arange(len(probs))).sum()),
        "argmax_index": int(np.argmax(probs)),
    }
    if want_hidden:
        hs = torch.stack([h[0] for h in out.hidden_states])  # [L+1, T, d]
        result["hidden"] = {name: hs[:, list(pos), :].float().mean(dim=1).cpu().numpy().astype(np.float16)
                            for name, pos in capture_positions.items()}
    return result


def greedy_decision(model: Any, tokenizer: Any, prompt_ids: Sequence[int], n_prices: int) -> dict[str, Any]:
    ids = torch.tensor([list(prompt_ids)], device=_device(model))
    with torch.inference_mode():
        seq = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), **GENERATION_KWARGS)
    response = tokenizer.decode(seq[0, ids.shape[-1]:], skip_special_tokens=True)
    parsed = parse_strict_price_response(response, n_prices)
    return {**parsed.to_dict(), "raw_response": response}


def run_phase_a1(model: Any, tokenizer: Any, *, seed: int = 20261023, generate: bool = True,
                 capture: bool = True, limit: int | None = None, log=None) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Score every Phase A.1 row; returns (json-able result, activation arrays)."""
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(1, env, persona=None, seed=seed)
    digits = digit_token_ids(tokenizer, env.n_prices)
    prefix = answer_prefix_ids(tokenizer, digits)
    rows = build_phase_a1_rows(env, seed)
    if limit is not None:
        rows = rows[:limit]
    out_rows, acts = [], {"answer": [], "rival_price": [], "rival_last_digit": []}
    for k, row in enumerate(rows):
        raw = raw_prompt(agent, row)
        prompt = _chat_prompt(raw, tokenizer)
        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        rival_pos = rival_price_token_positions(tokenizer, prompt)
        full = list(prompt_ids) + prefix
        positions = {"answer": [len(full) - 1], "rival_price": rival_pos, "rival_last_digit": [rival_pos[-1]]} if capture else None
        scored = score_digits(model, full, digits, positions)
        hidden = scored.pop("hidden", None)
        if hidden is not None:
            for name in acts:
                acts[name].append(hidden[name])
        decision = greedy_decision(model, tokenizer, prompt_ids, env.n_prices) if generate else {}
        br = best_response_profile(env, row.displayed_final_rival_index)
        out_rows.append({
            "row_id": row.row_id, "control_id": row.control_id, "condition": row.condition,
            "edit_direction": row.edit_direction, "market_consistent": row.market_consistent,
            "audit_nonce": row.audit_nonce, "own_price_index": row.own_price_index,
            "rival_pattern": row.rival_pattern, "history_variant": row.history_variant,
            "action_indices": row.action_indices, "displayed_final_rival_index": row.displayed_final_rival_index,
            "history": [{"prices": p.tolist(), "profits": q.tolist()} for p, q in row.history],
            "raw_prompt": raw, "raw_prompt_hash": sha256(raw.encode()).hexdigest(),
            "prompt_hash": sha256(prompt.encode()).hexdigest(), "prompt_token_count": len(prompt_ids),
            "rival_price_token_positions": rival_pos,
            **scored, **decision, **br,
        })
        if log:
            log(f"{k + 1}/{len(rows)} {row.row_id} E={scored['expected_index']:.2f} argmax={scored['argmax_index']} "
                f"greedy={decision.get('selected_price_index')}")
    arrays = {name: np.stack(v) for name, v in acts.items() if v}
    result = {
        "schema_version": SCHEMA_VERSION, "seed": seed, "protocol": PROTOCOL,
        "answer_prefix": ANSWER_PREFIX, "digit_token_ids": digits, "answer_prefix_ids": prefix,
        "generation_kwargs": GENERATION_KWARGS if generate else None,
        "activation_sites": {"answer": "last token of prompt+answer prefix (predicts the digit)",
                             "rival_price": "mean over final displayed rival-price tokens",
                             "rival_last_digit": "last token of final displayed rival price"} if capture else None,
        "hidden_state_layout": "[row, layer(0=embeddings), d_model] float16" if capture else None,
        "rows": out_rows, "summary": summarise_phase_a1(out_rows),
    }
    return result, arrays


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def summarise_phase_a1(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by = {}
    for r in rows:
        by.setdefault(r["control_id"], {})[(r["condition"], r.get("edit_direction"))] = r
    def deltas(cond, direction):
        d = [g[(cond, direction)]["expected_index"] - g[("control_realistic", None)]["expected_index"]
             for g in by.values() if (cond, direction) in g and ("control_realistic", None) in g]
        return {"n": len(d), "mean": float(np.mean(d)) if d else None,
                "min": float(np.min(d)) if d else None, "max": float(np.max(d)) if d else None}
    def tv(cond, direction):
        d = [0.5 * float(np.abs(np.subtract(g[(cond, direction)]["digit_probs"], g[("control_realistic", None)]["digit_probs"])).sum())
             for g in by.values() if (cond, direction) in g and ("control_realistic", None) in g]
        return float(np.mean(d)) if d else None
    valid = [r for r in rows if "analysis_eligible" in r]
    summary = {
        "n_rows": len(rows),
        "mean_digit_mass": float(np.mean([r["digit_mass"] for r in rows])) if rows else None,
        "greedy_strict_valid": f"{sum(bool(r['analysis_eligible']) for r in valid)}/{len(valid)}" if valid else None,
        "greedy_matches_digit_argmax": (f"{sum(r['selected_price_index'] == r['argmax_index'] for r in valid if r['analysis_eligible'])}/"
                                        f"{sum(bool(r['analysis_eligible']) for r in valid)}") if valid else None,
        "eps1_best_response_agreement_argmax": f"{sum(r['argmax_index'] in r['eps1_optimal_set'] for r in rows)}/{len(rows)}",
        "delta_expected_index_vs_control": {},
        "mean_total_variation_vs_control": {},
    }
    for cond, direction in [("negative_control_audit_nonce", None), ("realistic_rival_final", "undercut"),
                            ("realistic_rival_final", "raise"), ("synthetic_stale_profit", "undercut"),
                            ("synthetic_stale_profit", "raise")]:
        key = cond if direction is None else f"{cond}:{direction}"
        summary["delta_expected_index_vs_control"][key] = deltas(cond, direction)
        summary["mean_total_variation_vs_control"][key] = tv(cond, direction)
    return summary
