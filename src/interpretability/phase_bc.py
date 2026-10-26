"""Phase B (representation) and Phase C (patching / steering) primitives.

All interventions act on the residual stream *output* of decoder layer ``l``
(``model.model.layers[l]``), captured and modified with forward hooks, so the
final layer is handled the same way as the others (HF ``hidden_states[-1]`` is
post-norm and is therefore not used for interventions).

B1 dataset: realistic (environment-consistent) histories whose first three
rival rounds and own-price levels are disjoint from Phase A/A.1, so A.1 can be
used as a held-out evaluation set for directions built on B1.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable, Sequence

import numpy as np
import torch

from src.env import LogitBertrandEnv
from src.interpretability.modal_phase_a import CONTROL_AUDIT_NONCE, _chat_prompt, _with_audit_nonce
from src.interpretability.phase_a1 import (
    answer_prefix_ids, best_response_profile, digit_token_ids, replay,
)
from src.llm_agent import LLMPricingAgent

B1_OWN_INDICES = (1, 4, 7)
B1_RIVAL_PREFIXES = {
    "flat_3": (3, 3, 3), "flat_5": (5, 5, 5), "rise_0": (0, 2, 4),
    "fall_9": (9, 7, 5), "rise_4": (4, 6, 8), "fall_6": (6, 4, 2),
}
TEMPLATES = ("v1", "v2")
MARKERS = {"v1": "rival price(s): $", "v2": "competitor price "}


@dataclass
class B1Row:
    row_id: str
    family: str
    own_price_index: int
    final_rival_index: int
    template: str
    action_indices: list
    history: list


def build_b1_rows(env: LogitBertrandEnv, templates: Sequence[str] = TEMPLATES, seed: int = 20261025) -> list[B1Row]:
    rows = []
    for t in templates:
        for fam, prefix in B1_RIVAL_PREFIXES.items():
            for own in B1_OWN_INDICES:
                for final in range(env.n_prices):
                    actions = [(r, own) for r in prefix] + [(final, own)]
                    hist = replay(env, actions, seed)
                    rows.append(B1Row(f"b1-{t}-{fam}-o{own}-r{final}", fam, own, final, t,
                                      [list(a) for a in actions], hist))
    return rows


def prompt_v2(env: LogitBertrandEnv, history, n_rounds: int) -> str:
    """Alternative wording/format of the same information (template generalization)."""
    grid = "; ".join(f"option {i} = {p:.2f}" for i, p in enumerate(env.price_grid))
    lines = "\n".join(f"- period {t + 1}: our price {pr[1]:.2f}, our profit {pf[1]:.3f}, competitor price {pr[0]:.2f}"
                      for t, (pr, pf) in enumerate(history))
    return (f"You set prices for a firm that competes with one other firm selling a near-identical product. "
            f"There are {n_rounds} periods in total and this is period {len(history) + 1}.\n\n"
            f"Available prices: {grid}.\n\n"
            f"Objective: maximise your firm's total profit across all periods. Cheaper than the competitor means more "
            f"customers; more expensive means fewer. Demand changes smoothly.\n\n"
            f"Market log (oldest first):\n{lines}\n\n"
            f'Answer with only a JSON object {{"price_index": <integer>}} naming one option. No other text.')


def build_prompt(env: LogitBertrandEnv, agent: LLMPricingAgent, history, template: str, tokenizer: Any,
                 n_rounds: int | None = None) -> str:
    n = len(history)
    n_rounds = n + 1 if n_rounds is None else n_rounds
    raw = agent._build_prompt(history, n, n_rounds) if template == "v1" else prompt_v2(env, history, n_rounds)
    return _chat_prompt(_with_audit_nonce(raw, CONTROL_AUDIT_NONCE), tokenizer)


def final_rival_positions(tokenizer: Any, prompt: str, template: str) -> list[int]:
    marker = MARKERS[template]
    start = prompt.rfind(marker)
    if start < 0:
        raise ValueError("rival marker not found")
    start += len(marker)
    end = start
    while end < len(prompt) and (prompt[end].isdigit() or prompt[end] == "."):
        end += 1
    enc = tokenizer(prompt, add_special_tokens=False, return_offsets_mapping=True)
    return [i for i, (a, b) in enumerate(enc["offset_mapping"]) if b > start and a < end]


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------
def decoder_layers(model: Any):
    return model.model.layers


@contextmanager
def layer_hooks(model: Any, fns: dict[int, Callable[[torch.Tensor], torch.Tensor | None]]):
    """Register forward hooks; fn(hidden[B,T,d]) may return a replacement tensor."""
    handles = []
    layers = decoder_layers(model)
    for l, fn in fns.items():
        def hook(_m, _inp, out, fn=fn):
            hidden = out[0] if isinstance(out, tuple) else out
            new = fn(hidden)
            if new is None:
                return None
            return (new,) + tuple(out[1:]) if isinstance(out, tuple) else new
        handles.append(layers[l].register_forward_hook(hook))
    try:
        yield
    finally:
        for h in handles:
            h.remove()


def _digits_from_logits(logits: torch.Tensor, digit_ids: Sequence[int]) -> dict[str, Any]:
    logp = torch.log_softmax(logits.float(), dim=-1)
    d = logp[torch.tensor(list(digit_ids), device=logp.device)]
    p = torch.softmax(d, dim=-1).cpu().numpy().astype(float)
    return {"digit_probs": p.tolist(), "expected_index": float((p * np.arange(len(p))).sum()),
            "argmax_index": int(np.argmax(p)), "digit_mass": float(d.exp().sum())}


def run_with_capture(model: Any, ids: Sequence[int], digit_ids: Sequence[int],
                     sites: dict[str, Sequence[int]], intervene: dict | None = None) -> dict[str, Any]:
    """Forward pass; returns digit distribution and per-layer residual outputs at sites.

    ``sites`` -> {name: positions}; stored as mean over positions, shape [n_layers, d].
    ``intervene`` -> {layer: fn} applied before capture at that layer.
    """
    n_layers = len(decoder_layers(model))
    store: dict[str, list] = {name: [None] * n_layers for name in sites}
    fns = {}
    for l in range(n_layers):
        def fn(h, l=l):
            new = intervene[l](h) if intervene and l in intervene else None
            src = new if new is not None else h
            for name, pos in sites.items():
                store[name][l] = src[0, list(pos), :].float().mean(dim=0).cpu().numpy()
            return new
        fns[l] = fn
    x = torch.tensor([list(ids)], device=model.device)
    with torch.inference_mode(), layer_hooks(model, fns):
        out = model(input_ids=x, use_cache=False)
    res = _digits_from_logits(out.logits[0, -1], digit_ids)
    res["acts"] = {name: np.stack(v).astype(np.float16) for name, v in store.items()}
    return res


def run_scored(model: Any, ids: Sequence[int], digit_ids: Sequence[int], intervene: dict | None = None) -> dict[str, Any]:
    x = torch.tensor([list(ids)], device=model.device)
    with torch.inference_mode(), layer_hooks(model, intervene or {}):
        out = model(input_ids=x, use_cache=False)
    return _digits_from_logits(out.logits[0, -1], digit_ids)


def capture_layer_outputs(model: Any, ids: Sequence[int], positions: Sequence[int]) -> list[torch.Tensor]:
    """Raw residual outputs of every layer at the given positions (for patching donors)."""
    n_layers = len(decoder_layers(model))
    store: list = [None] * n_layers
    def mk(l):
        def fn(h):
            store[l] = h[0, list(positions), :].detach().clone()
            return None
        return fn
    x = torch.tensor([list(ids)], device=model.device)
    with torch.inference_mode(), layer_hooks(model, {l: mk(l) for l in range(n_layers)}):
        model(input_ids=x, use_cache=False)
    return store


def patch_fn(positions: Sequence[int], values: torch.Tensor):
    def fn(h):
        h = h.clone()
        h[0, list(positions), :] = values.to(h.dtype)
        return h
    return fn


def add_fn(positions: Sequence[int] | None, vector: torch.Tensor):
    """Add ``vector`` at positions (None = every position)."""
    def fn(h):
        h = h.clone()
        v = vector.to(h.dtype).to(h.device)
        if positions is None:
            h[0] += v
        else:
            h[0, list(positions), :] += v
        return h
    return fn
