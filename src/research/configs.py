"""Configuration system: batch specifications expand into fully specified, hashable run units.

A batch spec (JSON in research/configs/) has a shared ``base`` and a list of ``blocks``;
each block overrides parts of ``base`` and declares a ``grid`` whose Cartesian product is
expanded. One-factor robustness sweeps are written as blocks with a single varied key.
Every unit gets ``unit_id = hash(canonical config)`` so re-submitting a batch is idempotent.
"""
from __future__ import annotations

import copy, itertools, json
from dataclasses import dataclass
from typing import Any

from src.research.economics import ECON_PRESETS
from src.research.ids import short_hash
from src.research.prompts import TEMPLATES
from src.research.rivals import REACTIVE, SCRIPTED, DeviationDesign

EXPERIMENTS = ("deviation_game", "fixed_history", "reactive_game")
FIXED_HISTORY_ARMS = ("H_sudden", "H_gradual", "H_always_low", "H_stable_high")
STEERING_KINDS = ("none", "sham", "learned", "random", "generic_price")
SITES = ("answer", "reply_start")

DEFAULT_UNIT: dict[str, Any] = {
    "experiment": "deviation_game",
    "model": "7b",
    "condition": "A_stable",
    "design": {"rounds": 16, "deviation_round": 7, "high": 7, "low": 2, "raise_to": 9, "recovery_delay": 3},
    "prefix_rounds": 4,             # scripted pre-play rounds shown as history (rival at `high`)
    "prefix_own_range": [4, 8],     # own price indices for pre-play, drawn with history_seed
    "econ_id": "base",
    "template_id": "v1",
    "window": 10,                   # rounds of history shown in the prompt
    "decoding": {"mode": "greedy", "temperature": 1.0, "top_p": 1.0, "top_k": 0},
    "steering": {"kind": "none", "vector_id": None, "alpha": 0.0, "layer": 20, "site": "answer",
                 "timing": "all", "random_seed": 0},
    "seeds": {"model_seed": 0, "history_seed": 0, "env_seed": 0, "rival_seed": 0},
    "audit_generation": "deviation_window",   # none | deviation_window | all
    "fixed_own_index": 5,           # fixed_history: own price shown in every history round
    "replicate": 0,
}


def deep_update(base: dict, upd: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in upd.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_update(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def set_path(d: dict, path: str, value: Any) -> dict:
    out = copy.deepcopy(d)
    cur = out
    keys = path.split(".")
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value
    return out


def validate_unit(u: dict, n_prices: int = 10) -> None:
    if u["experiment"] not in EXPERIMENTS:
        raise ValueError(f"unknown experiment {u['experiment']}")
    if u["experiment"] == "deviation_game" and u["condition"] not in SCRIPTED:
        raise ValueError(f"unknown scripted condition {u['condition']}")
    if u["experiment"] == "fixed_history" and u["condition"] not in FIXED_HISTORY_ARMS:
        raise ValueError(f"unknown fixed-history arm {u['condition']}")
    if u["experiment"] == "reactive_game" and u["condition"] not in REACTIVE:
        raise ValueError(f"unknown rival policy {u['condition']}")
    if u["econ_id"] not in ECON_PRESETS:
        raise ValueError(f"unknown econ {u['econ_id']}")
    if u["template_id"] not in TEMPLATES:
        raise ValueError(f"unknown template {u['template_id']}")
    s = u["steering"]
    if s["kind"] not in STEERING_KINDS or s["site"] not in SITES or s["timing"] not in ("all", "post_deviation"):
        raise ValueError(f"bad steering {s}")
    if s["kind"] in ("learned", "generic_price") and not s.get("vector_id"):
        raise ValueError("learned/generic steering needs vector_id")
    dec = u["decoding"]
    if dec["mode"] not in ("greedy", "sample") or dec["temperature"] <= 0 or not 0 < dec["top_p"] <= 1:
        raise ValueError(f"bad decoding {dec}")
    DeviationDesign(**u["design"]).validate(n_prices)
    lo, hi = u["prefix_own_range"]
    if not (0 <= lo <= hi < n_prices):
        raise ValueError("prefix_own_range out of grid")


def unit_id(u: dict) -> str:
    return short_hash({k: v for k, v in u.items() if k not in ("block",)}, 16)


def expand(spec: dict) -> list[dict]:
    """Expand a batch spec into validated, de-duplicated unit configs."""
    base = deep_update(DEFAULT_UNIT, spec.get("base", {}))
    base["model"] = spec.get("model", base["model"])
    units, seen = [], set()
    for block in spec["blocks"]:
        b = deep_update(base, block.get("overrides", {}))
        grid = block.get("grid", {})
        keys = list(grid)
        for combo in itertools.product(*[grid[k] for k in keys]) if keys else [()]:
            u = b
            for k, v in zip(keys, combo):
                u = deep_update(u, v) if k == "steering_preset" else set_path(u, k, v)
            u = copy.deepcopy(u)
            u["block"] = block["name"]
            validate_unit(u)
            uid = unit_id(u)
            if uid in seen:
                continue
            seen.add(uid)
            u["unit_id"] = uid
            units.append(u)
    return units


def load_spec(path: str) -> dict:
    with open(path) as f:
        spec = json.load(f)
    for k in ("batch_id", "protocol", "designation", "blocks"):
        if k not in spec:
            raise ValueError(f"batch spec missing {k}")
    if spec["designation"] not in ("smoke", "exploratory", "confirmatory"):
        raise ValueError("designation must be smoke | exploratory | confirmatory")
    return spec


def estimate(units: list[dict]) -> dict:
    """Forward-pass and generation counts (exact for scripted games; reactive self-play doubles)."""
    passes = gens = 0
    for u in units:
        per_audit = 2 if u["steering"]["kind"] == "none" else 1  # free + prefixed audits when unsteered
        if u["experiment"] == "fixed_history":
            passes += 1
            gens += per_audit if u["audit_generation"] != "none" else 0
            continue
        T = u["design"]["rounds"]
        mult = 2 if u["condition"] == "llm_selfplay" else 1
        passes += T * mult
        if u["audit_generation"] == "all":
            gens += T * per_audit
        elif u["audit_generation"] == "deviation_window":
            gens += min(4, T) * per_audit
    return {"units": len(units), "forward_passes": passes, "generations": gens}
