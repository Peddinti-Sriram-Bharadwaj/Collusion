"""Run one unit of the strategic-deviation protocol (closed-loop game, fixed history, reactive game).

Information discipline: the prompt at live round t contains only rounds < t (pre-play prefix
plus earlier live rounds); the rival's round-t action is chosen before the agent acts but is
never shown to it until round t+1. Scripted rival sequences are fixed in advance and do not
depend on the agent.
"""
from __future__ import annotations

from time import perf_counter
from typing import Any

import numpy as np

from src.interpretability.phase_a1 import answer_prefix_ids, digit_token_ids
from src.research import decision as D
from src.research.economics import ECON_PRESETS, benchmarks, collusion_index, env_for
from src.research.prompts import render
from src.research.rivals import DeviationDesign, reactive_action, returns_at, scripted_sequence


def _ids(tok, prompt, prefix):
    return list(tok(prompt, add_special_tokens=False)["input_ids"]) + list(prefix)


class Decider:
    """Holds model-level state (digit ids, answer prefix, steering vector) for a unit."""

    def __init__(self, model, tok, unit: dict, vector: np.ndarray | None):
        self.model, self.tok, self.unit, self.vector = model, tok, unit, vector
        econ = ECON_PRESETS[unit["econ_id"]]
        self.econ, self.env = econ, env_for(econ)
        self.digits = digit_token_ids(tok, self.env.n_prices)
        self.prefix = answer_prefix_ids(tok, self.digits)
        self.rng = np.random.default_rng(unit["seeds"]["model_seed"])

    def decide(self, history, agent_id, round_num, n_rounds, steer: bool, audit: bool) -> dict:
        u = self.unit
        prompt = render(self.tok, self.env, history, agent_id, round_num, n_rounds, u["template_id"], u["window"])
        ids = _ids(self.tok, prompt, self.prefix)
        s = u["steering"]
        hooks = D.steering_hooks(self.vector, s["alpha"], s["layer"], len(ids) - 1) if (steer and s["site"] == "answer") else None
        if steer and s["site"] == "reply_start" and self.vector is not None:
            from src.interpretability.phase_d import site_position
            hooks = D.steering_hooks(self.vector, s["alpha"], s["layer"], site_position(self.tok, ids, "reply_start"))
        sc = D.digit_scores(self.model, ids, self.digits, hooks)
        uval = float(self.rng.random())  # drawn every decision so matched units stay coupled
        action, probs = D.choose(sc["digit_logprobs"], u["decoding"], uval)
        p = np.asarray(probs)
        rec = {"action": action, "expected_index": float((np.exp(np.asarray(sc["digit_logprobs"])) /
                                                          np.exp(np.asarray(sc["digit_logprobs"])).sum() * np.arange(len(p))).sum()),
               "digit_logprobs": sc["digit_logprobs"], "digit_mass": sc["digit_mass"], "u": uval,
               "prompt_tokens": len(ids) - len(self.prefix), "steered": hooks is not None}
        if audit:
            if hooks is None:
                rec["audit_free"] = D.audit_free(self.model, self.tok, ids[:-len(self.prefix)], self.env.n_prices)
            rec["audit_prefixed"] = D.audit_prefixed(self.model, self.tok, ids, self.env.n_prices, hooks)
        return rec


def _step(env, rival_idx, own_idx, agent_is_1=True):
    g = env.price_grid
    prices = np.array([g[rival_idx], g[own_idx]])
    return prices, env._profits(prices)


def _prefix(unit, env):
    d = DeviationDesign(**unit["design"])
    rng = np.random.default_rng(unit["seeds"]["history_seed"])
    lo, hi = unit["prefix_own_range"]
    rows, joint = [], []
    for _ in range(unit["prefix_rounds"]):
        own = int(rng.integers(lo, hi + 1))
        pr, pf = _step(env, d.high, own)
        rows.append((pr, pf)); joint.append((d.high, own))
    return rows, joint


def run_unit(model, tok, unit: dict, vector: np.ndarray | None) -> dict:
    t0 = perf_counter()
    dec = Decider(model, tok, unit, vector)
    env, d = dec.env, DeviationDesign(**unit["design"])
    s = unit["steering"]
    exp = unit["experiment"]
    bench = benchmarks(dec.econ)
    rounds: list[dict] = []

    if exp == "fixed_history":
        rng = np.random.default_rng(unit["seeds"]["history_seed"])
        lo, hi = unit["prefix_own_range"]
        n = unit["prefix_rounds"] + d.deviation_round + 1
        if unit.get("fixed_history_own", "constant") == "prefix_random":
            pre = [int(rng.integers(lo, hi + 1)) for _ in range(unit["prefix_rounds"])]
            own_seq = (pre + [pre[-1]] * n)[:n]
        else:  # smoke-batch behaviour
            own_seq = [int(rng.integers(lo, hi + 1))] * n
        own = own_seq[-1]
        gradual = scripted_sequence("D_gradual", d)
        seqs = {"H_sudden": [d.high] * (n - 1) + [d.low],
                "H_gradual": ([d.high] * unit["prefix_rounds"] + gradual)[:n],
                "H_always_low": [d.low] * n, "H_stable_high": [d.high] * n}
        seq = seqs[unit["condition"]]
        history = [_step(env, r, o) for r, o in zip(seq, own_seq)]
        rec = dec.decide(history, 1, n, n + (d.rounds - d.deviation_round - 1), steer=s["kind"] != "none",
                         audit=unit["audit_generation"] != "none")
        rec.update({"t": 0, "rival_history": seq, "own_index": own, "own_history": own_seq,
                    "best_response_index": bench["best_response_by_rival_index"][seq[-1]]})
        rounds.append(rec)
        summary = {"decision_expected_index": rec["expected_index"], "decision_action": rec["action"],
                   "final_rival_index": seq[-1], "own_index": own}
    else:
        history, joint = _prefix(unit, env)
        P = unit["prefix_rounds"]
        n_total = P + d.rounds
        seq = scripted_sequence(unit["condition"], d) if exp == "deviation_game" else None
        rng_r = np.random.default_rng(unit["seeds"]["rival_seed"])
        live_joint: list[tuple[int, int]] = []
        for t in range(d.rounds):
            steer_now = s["kind"] != "none" and (s["timing"] == "all" or t > d.deviation_round)
            audit = (unit["audit_generation"] == "all" or
                     (unit["audit_generation"] == "deviation_window" and d.deviation_round <= t <= d.deviation_round + 3))
            rival_rec = None
            if exp == "deviation_game":
                r = seq[t]
            else:
                r = reactive_action(unit["condition"], t, live_joint, rng_r, env.n_prices, d.high, d.low)
                if r is None:  # self-play: agent 0 is the same model, never steered
                    rival_rec = dec.decide(history, 0, P + t, n_total, steer=False, audit=False)
                    r = rival_rec["action"]
            rec = dec.decide(history, 1, P + t, n_total, steer=steer_now, audit=audit)
            pr, pf = _step(env, r, rec["action"])
            history.append((pr, pf)); live_joint.append((r, rec["action"]))
            rec.update({"t": t, "rival_action": r, "own_profit": float(pf[1]), "rival_profit": float(pf[0]),
                        "best_response_to_last_rival": bench["best_response_by_rival_index"][live_joint[-2][0] if t > 0 else d.high],
                        "rival_llm": None if rival_rec is None else {k: rival_rec[k] for k in ("action", "expected_index")}})
            rounds.append(rec)
        own_p = np.array([r["own_profit"] for r in rounds]); riv_p = np.array([r["rival_profit"] for r in rounds])
        acts = np.array([r["action"] for r in rounds]); E = np.array([r["expected_index"] for r in rounds])
        summary = {"mean_action": float(acts.mean()), "mean_expected_index": float(E.mean()),
                   "own_cum_profit": float(own_p.sum()), "rival_cum_profit": float(riv_p.sum()),
                   "joint_cum_profit": float((own_p + riv_p).sum()),
                   "collusion_index_joint": collusion_index(dec.econ, float(((own_p + riv_p) / 2).mean())),
                   "collusion_index_own": collusion_index(dec.econ, float(own_p.mean())),
                   "br_gap_mean": float(np.mean([r["action"] - r["best_response_to_last_rival"] for r in rounds])),
                   "stability_last5_sd": float(acts[-5:].std()),
                   "returns_at": returns_at(unit["condition"], d) if exp == "deviation_game" else None}
    audits_free = [r["audit_free"] for r in rounds if "audit_free" in r]
    audits_pref = [r["audit_prefixed"] for r in rounds if "audit_prefixed" in r]
    validity = {
        "n_decisions": len(rounds),
        "free_audits": len(audits_free), "free_valid": sum(a["valid"] for a in audits_free),
        "free_agree": sum(a["valid"] and a["action"] == r["action"] for r in rounds if "audit_free" in r for a in [r["audit_free"]])
        if unit["decoding"]["mode"] == "greedy" else None,
        "prefixed_audits": len(audits_pref), "prefixed_valid": sum(a["valid"] for a in audits_pref),
        "prefixed_agree": sum(a["valid"] and a["action"] == r["action"] for r in rounds if "audit_prefixed" in r for a in [r["audit_prefixed"]])
        if unit["decoding"]["mode"] == "greedy" else None,
        "min_digit_mass": float(min(r["digit_mass"] for r in rounds)),
    }
    return {"rounds": rounds, "summary": summary, "validity": validity, "benchmarks": bench,
            "runtime_seconds": perf_counter() - t0}
