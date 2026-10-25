"""Task runners for Phase B1 (activation dataset), C1 (patching), C2 (steering).

Each returns (json-able result, dict of numpy arrays). Model-agnostic; used both
locally (CPU, small model) and on Modal (7B).
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable, Sequence

import numpy as np
import torch

from src.env import LogitBertrandEnv
from src.interpretability.modal_phase_a import _chat_prompt
from src.interpretability.phase_a1 import (
    answer_prefix_ids, best_response_profile, build_phase_a1_rows, digit_token_ids, raw_prompt,
)
from src.interpretability.phase_bc import (
    add_fn, build_b1_rows, build_prompt, capture_layer_outputs, decoder_layers, final_rival_positions,
    patch_fn, run_scored, run_with_capture,
)
from src.llm_agent import LLMPricingAgent


def _setup(tokenizer, seed=20261023):
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(1, env, persona=None, seed=seed)
    digits = digit_token_ids(tokenizer, env.n_prices)
    prefix = answer_prefix_ids(tokenizer, digits)
    return env, agent, digits, prefix


def _ids(tokenizer, prompt, prefix):
    return list(tokenizer(prompt, add_special_tokens=False)["input_ids"]) + list(prefix)


FINAL_ROUND_MARKERS = {"v1": "\nRound ", "v2": "\n- period "}


def pre_final_round_position(tokenizer, prompt: str, template: str) -> int:
    """Token holding the newline that starts the final round's line.

    Causal masking means nothing about the final round (rival price or profit)
    can be present here: a true null site for final-round information.
    """
    char = prompt.rfind(FINAL_ROUND_MARKERS[template])
    enc = tokenizer(prompt, add_special_tokens=False, return_offsets_mapping=True)
    cands = [i for i, (a, b) in enumerate(enc["offset_mapping"]) if a <= char < b]
    if not cands:
        raise ValueError("final-round marker not tokenized")
    return cands[0]


def own_profit_positions(tokenizer, prompt: str) -> list[int]:
    """Final-round own-profit number in the v1 template ('(profit 0.197)')."""
    start = prompt.rfind("(profit ") + len("(profit ")
    end = start
    while end < len(prompt) and (prompt[end].isdigit() or prompt[end] == "."):
        end += 1
    enc = tokenizer(prompt, add_special_tokens=False, return_offsets_mapping=True)
    return [i for i, (a, b) in enumerate(enc["offset_mapping"]) if b > start and a < end]


# ---------------------------------------------------------------------------
def task_b1(model, tokenizer, *, templates=("v1", "v2"), limit=None, log=None):
    env, agent, digits, prefix = _setup(tokenizer)
    rows = build_b1_rows(env, templates)
    if limit:
        rows = rows[:limit]
    out, acts = [], {"answer": [], "rival": [], "pre_rival": [], "pre_final_round": []}
    for k, r in enumerate(rows):
        prompt = build_prompt(env, agent, r.history, r.template, tokenizer)
        ids = _ids(tokenizer, prompt, prefix)
        rpos = final_rival_positions(tokenizer, prompt, r.template)
        sites = {"answer": [len(ids) - 1], "rival": rpos, "pre_rival": [rpos[0] - 1],
                 "pre_final_round": [pre_final_round_position(tokenizer, prompt, r.template)]}
        res = run_with_capture(model, ids, digits, sites)
        for s in acts:
            acts[s].append(res["acts"][s])
        br = best_response_profile(env, r.final_rival_index)
        out.append({"row_id": r.row_id, "family": r.family, "template": r.template,
                    "own_price_index": r.own_price_index, "final_rival_index": r.final_rival_index,
                    "action_indices": r.action_indices, "prompt_hash": sha256(prompt.encode()).hexdigest(),
                    "rival_positions": rpos, "n_tokens": len(ids),
                    "best_response_index": br["best_response_index"], "eps1_optimal_set": br["eps1_optimal_set"],
                    **{k2: res[k2] for k2 in ("digit_probs", "expected_index", "argmax_index", "digit_mass")}})
        if log and (k % 20 == 0 or k == len(rows) - 1):
            log(f"b1 {k + 1}/{len(rows)} {r.row_id} E={res['expected_index']:.2f}")
    arrays = {f"acts_{s}": np.stack(v) for s, v in acts.items()}
    return {"task": "b1", "n_layers": len(decoder_layers(model)), "rows": out,
            "sites": {"answer": "last token (predicts digit)", "rival": "mean over final rival-price tokens",
                      "pre_rival": "token immediately before the final rival price; NOTE: sees the final-round own profit, which is a function of the rival price in realistic histories",
                      "pre_final_round": "newline token starting the final round line; causally blind to the final round (null site)"},
            "layout": "acts_<site>: [row, layer, d_model] float16, residual output of decoder layer"}, arrays


# ---------------------------------------------------------------------------
def a1_prompt_ids(env, agent, tokenizer, prefix):
    rows = build_phase_a1_rows(env)
    by = {}
    for r in rows:
        prompt = _chat_prompt(raw_prompt(agent, r), tokenizer)
        by[r.row_id] = (r, prompt, _ids(tokenizer, prompt, prefix))
    return by


def task_c1_patch(model, tokenizer, *, controls: Sequence[str] | None = None, arms=("real", "stale"),
                  layers: Sequence[int] | None = None, log=None):
    """Patch donor (edited) residuals into the control run, per layer and site."""
    env, agent, digits, prefix = _setup(tokenizer)
    by = a1_prompt_ids(env, agent, tokenizer, prefix)
    n_layers = len(decoder_layers(model))
    layers = list(range(n_layers)) if layers is None else list(layers)
    control_ids = sorted({r.control_id for r, _, _ in by.values()}) if controls is None else list(controls)
    results = []
    for ci, cid in enumerate(control_ids):
        _, cprompt, cids = by[f"{cid}-control"]
        base = run_scored(model, cids, digits)
        rpos = final_rival_positions(tokenizer, cprompt, "v1")
        ppos = own_profit_positions(tokenizer, cprompt)
        for arm in arms:
            for direction in ("undercut", "raise"):
                drow, dprompt, dids = by[f"{cid}-{direction}-{arm}"]
                if len(dids) != len(cids):
                    results.append({"control_id": cid, "arm": arm, "direction": direction, "skipped": "length mismatch"})
                    continue
                donor = run_scored(model, dids, digits)
                sites = {"rival": rpos, "answer": [len(cids) - 1], "own_profit": ppos}
                diff = [i for i, (a, b) in enumerate(zip(cids, dids)) if a != b]
                allpos = sorted(set(rpos + ppos + [len(cids) - 1]))
                donor_acts = capture_layer_outputs(model, dids, allpos)
                index = {p: j for j, p in enumerate(allpos)}
                effects = {s: [] for s in sites}
                for l in layers:
                    for s, pos in sites.items():
                        vals = donor_acts[l][[index[p] for p in pos]]
                        res = run_scored(model, cids, digits, {l: patch_fn(pos, vals)})
                        effects[s].append(res["expected_index"])
                results.append({"control_id": cid, "arm": arm, "direction": direction,
                                "differing_token_positions": diff, "sites": sites,
                                "E_control": base["expected_index"], "E_donor": donor["expected_index"],
                                "probs_control": base["digit_probs"], "probs_donor": donor["digit_probs"],
                                "layers": layers, "E_patched": effects})
        if log:
            log(f"c1 {ci + 1}/{len(control_ids)} {cid}")
    return {"task": "c1_patch", "n_layers": n_layers, "results": results}, {}


# ---------------------------------------------------------------------------
def task_c2_steer(model, tokenizer, *, directions: dict[str, np.ndarray], layer: int, site: str = "rival",
                  alphas=(-8, -4, -2, -1, 0, 1, 2, 4, 8), controls: Sequence[str] | None = None, log=None):
    """Add alpha * unit(direction) * scale at ``site`` positions of layer ``layer`` on A.1 controls.

    ``directions``: name -> [d_model] vectors (built on B1 only). ``scale`` is the
    typical residual norm at that site/layer, so alpha is in units of residual norm/10.
    """
    env, agent, digits, prefix = _setup(tokenizer)
    by = a1_prompt_ids(env, agent, tokenizer, prefix)
    control_ids = sorted({r.control_id for r, _, _ in by.values()}) if controls is None else list(controls)
    out = []
    for ci, cid in enumerate(control_ids):
        row, prompt, ids = by[f"{cid}-control"]
        rpos = final_rival_positions(tokenizer, prompt, "v1")
        if site == "rival":
            pos = rpos
        elif site == "after_rival":  # every position from the final rival price to the answer token
            pos = list(range(rpos[0], len(ids)))
        else:
            pos = [len(ids) - 1]
        acts = capture_layer_outputs(model, ids, pos)[layer]
        scale = float(acts.float().norm(dim=-1).mean()) / 10.0
        rec = {"control_id": cid, "final_rival_index": row.displayed_final_rival_index,
               "own_price_index": row.own_price_index, "scale": scale, "n_positions": len(pos), "E": {}, "digit_mass": {}}
        for name, vec in directions.items():
            u = torch.tensor(vec, dtype=torch.float32)
            u = u / u.norm()
            rec["E"][name] = []
            rec["digit_mass"][name] = []
            for a in alphas:
                res = run_scored(model, ids, digits, {layer: add_fn(pos, a * scale * u)} if a != 0 else {layer: add_fn(pos, 0 * u)})
                rec["E"][name].append(res["expected_index"])
                rec["digit_mass"][name].append(res["digit_mass"])
        out.append(rec)
        if log:
            log(f"c2 {ci + 1}/{len(control_ids)} {cid}")
    return {"task": "c2_steer", "layer": layer, "site": site, "alphas": list(alphas), "results": out}, {}


# ---------------------------------------------------------------------------
# Confirmatory deviation test (pre-registered in docs/prereg_deviation_b2.md)
# ---------------------------------------------------------------------------
B2_RIVAL_PREFIXES = {
    "flat_4": (4, 4, 4), "flat_7": (7, 7, 7), "rise_1": (1, 2, 3),
    "fall_8": (8, 7, 6), "rise_3": (3, 5, 7), "fall_7": (7, 5, 3),
}
B2_OWN_INDICES = (3, 6)
B2_HORIZONS = {"final": None, "nonfinal": 10}  # n_rounds; None -> "round 5 of 5"


def extrapolate(prefix) -> int:
    return int(np.clip(prefix[-1] + (prefix[-1] - prefix[-2]), 0, 9))


def task_b2_confirm(model, tokenizer, *, templates=("v1", "v2"), seed=20261026, log=None):
    """Behaviour only (digit scoring) on fresh histories; no activations."""
    from src.interpretability.phase_a1 import replay
    env, agent, digits, prefix_ids = _setup(tokenizer)
    rows = []
    cells = [(t, h, fam, own) for t in templates for h in B2_HORIZONS for fam in B2_RIVAL_PREFIXES for own in B2_OWN_INDICES]
    for k, (t, h, fam, own) in enumerate(cells):
        pre = B2_RIVAL_PREFIXES[fam]
        for final in range(env.n_prices):
            actions = [(r, own) for r in pre] + [(final, own)]
            hist = replay(env, actions, seed)
            prompt = build_prompt(env, agent, hist, t, tokenizer, n_rounds=B2_HORIZONS[h])
            res = run_scored(model, _ids(tokenizer, prompt, prefix_ids), digits)
            br = best_response_profile(env, final)
            rows.append({"template": t, "horizon": h, "family": fam, "own_price_index": own, "final_rival_index": final,
                         "extrapolated_index": extrapolate(pre), "last_prefix_index": pre[-1],
                         "deviation": abs(final - extrapolate(pre)), "change_from_last": abs(final - pre[-1]),
                         "prompt_hash": sha256(prompt.encode()).hexdigest(),
                         "best_response_index": br["best_response_index"], **res})
        if log:
            log(f"b2 cell {k + 1}/{len(cells)} {t} {h} {fam} own{own}")
    return {"task": "b2_confirm", "rows": rows,
            "design": {"prefixes": B2_RIVAL_PREFIXES, "own": B2_OWN_INDICES, "horizons": B2_HORIZONS, "templates": list(templates)}}, {}


# ---------------------------------------------------------------------------
# Position x layer patching (where is the information in transit?)
# ---------------------------------------------------------------------------
def task_c1_positions(model, tokenizer, *, controls: Sequence[str] | None = None, arm: str = "stale",
                      layers: Sequence[int] = (14, 16, 17, 18, 19, 20), log=None):
    """Patch one position at a time (every position from the final rival price to the end)."""
    env, agent, digits, prefix = _setup(tokenizer)
    by = a1_prompt_ids(env, agent, tokenizer, prefix)
    control_ids = sorted({r.control_id for r, _, _ in by.values()}) if controls is None else list(controls)
    results = []
    for ci, cid in enumerate(control_ids):
        _, cprompt, cids = by[f"{cid}-control"]
        base = run_scored(model, cids, digits)
        rpos = final_rival_positions(tokenizer, cprompt, "v1")
        positions = list(range(rpos[0], len(cids)))
        for direction in ("undercut", "raise"):
            _, _, dids = by[f"{cid}-{direction}-{arm}"]
            if len(dids) != len(cids):
                results.append({"control_id": cid, "direction": direction, "skipped": "length mismatch"}); continue
            donor = run_scored(model, dids, digits)
            acts = capture_layer_outputs(model, dids, positions)
            grid = []
            for l in layers:
                rowv = []
                for j, p in enumerate(positions):
                    res = run_scored(model, cids, digits, {l: patch_fn([p], acts[l][j:j + 1])})
                    rowv.append(res["expected_index"])
                grid.append(rowv)
            results.append({"control_id": cid, "direction": direction, "arm": arm, "positions": positions,
                            "tokens": [tokenizer.decode([cids[p]]) for p in positions],
                            "rival_positions": rpos, "layers": list(layers),
                            "E_control": base["expected_index"], "E_donor": donor["expected_index"], "E_patched": grid})
        if log:
            log(f"c1pos {ci + 1}/{len(control_ids)} {cid}")
    return {"task": "c1_positions", "results": results}, {}
