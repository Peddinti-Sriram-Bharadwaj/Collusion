"""One pricing decision: digit scoring (primary), decoding, and strict-parse audits.

Primary measurement: the model's distribution over the 10 single-token price digits after
the forced answer prefix ``{"price_index": `` (validated against free generation in
Phase A.1: greedy answer == digit argmax in 144/144 prompts for every Qwen size tested).
Actions are drawn from that digit distribution (greedy = argmax; sampled = temperature /
top-k / top-p applied to the digit logits) using a supplied uniform number, so matched
conditions can share random numbers.

Audits (never used to fill in actions):
  * free: unsteered greedy generation from the bare prompt, strict-parsed;
  * prefixed: greedy completion after the forced prefix *with* the intervention active,
    strict-parsed as prefix+completion (checks steering does not break the output format).
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import torch

from src.interpretability.modal_phase_a import GENERATION_KWARGS
from src.interpretability.phase_a1 import ANSWER_PREFIX
from src.interpretability.phase_bc import layer_hooks
from src.interpretability.strict_pricing_parser import parse_strict_price_response
from src.research.steering import add_at


def _device(model):
    return getattr(model, "device", "cpu")


def digit_scores(model, ids: Sequence[int], digit_ids: Sequence[int], hooks: dict | None = None) -> dict:
    x = torch.tensor([list(ids)], device=_device(model))
    with torch.inference_mode(), layer_hooks(model, hooks or {}):
        out = model(input_ids=x, use_cache=False)
    logp = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
    d = logp[torch.tensor(list(digit_ids), device=logp.device)]
    return {"digit_logprobs": d.cpu().numpy().astype(float).tolist(), "digit_mass": float(d.exp().sum())}


def choose(digit_logprobs: Sequence[float], decoding: dict, u: float) -> tuple[int, list[float]]:
    lp = np.asarray(digit_logprobs, float)
    if decoding["mode"] == "greedy":
        p = np.exp(lp - lp.max()); p /= p.sum()
        return int(np.argmax(p)), p.tolist()
    z = lp / float(decoding["temperature"])
    k = int(decoding.get("top_k") or 0)
    if 0 < k < len(z):
        z[np.argsort(z)[:-k]] = -np.inf
    p = np.exp(z - np.max(z)); p /= p.sum()
    top_p = float(decoding.get("top_p", 1.0))
    if top_p < 1.0:
        order = np.argsort(-p); keep = np.cumsum(p[order]) - p[order] < top_p
        mask = np.zeros_like(p, bool); mask[order[keep]] = True
        p = np.where(mask, p, 0.0); p /= p.sum()
    cdf = np.cumsum(p)
    return int(min(np.searchsorted(cdf, u, side="right"), len(p) - 1)), p.tolist()


def audit_free(model, tokenizer, prompt_ids: Sequence[int], n_prices: int) -> dict:
    x = torch.tensor([list(prompt_ids)], device=_device(model))
    with torch.inference_mode():
        seq = model.generate(input_ids=x, attention_mask=torch.ones_like(x), **GENERATION_KWARGS)
    text = tokenizer.decode(seq[0, x.shape[-1]:], skip_special_tokens=True)
    p = parse_strict_price_response(text, n_prices)
    return {"raw_response": text, "parse_status": p.parse_status, "valid": p.analysis_eligible,
            "action": p.selected_price_index}


def audit_prefixed(model, tokenizer, ids_with_prefix: Sequence[int], n_prices: int, hooks: dict | None) -> dict:
    x = torch.tensor([list(ids_with_prefix)], device=_device(model))
    kw = dict(GENERATION_KWARGS); kw["max_new_tokens"] = 8
    with torch.inference_mode(), layer_hooks(model, hooks or {}):
        seq = model.generate(input_ids=x, attention_mask=torch.ones_like(x), **kw)
    text = ANSWER_PREFIX + tokenizer.decode(seq[0, x.shape[-1]:], skip_special_tokens=True)
    p = parse_strict_price_response(text, n_prices)
    return {"raw_response": text, "parse_status": p.parse_status, "valid": p.analysis_eligible,
            "action": p.selected_price_index}


def steering_hooks(vector: np.ndarray | None, alpha: float, layer: int, position: int) -> dict | None:
    if vector is None:
        return None
    return {layer: add_at(position, alpha * torch.tensor(vector, dtype=torch.float32))}
