"""Phase C3 (transferable steering vector at the hand-off sites) and Phase D (repeated games).

C3: the activation difference that a rival-price edit causes at the hand-off sites found by
patching (reply-start token at layer 18; answer token at layer 20) is averaged over training
pairs and added to held-out prompts. If one vector reproduces the edit's effect on unseen
histories, the mechanism is shared across histories rather than pair-specific.

D: the LLM prices against scripted rivals (and itself) for several rounds in LogitBertrandEnv,
optionally with the C3 vector added at every decision, so a representation-level intervention
can be read out as a market outcome (prices, profits, collusion index).
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import torch

from src.env import LogitBertrandEnv
from src.interpretability.modal_phase_a import _chat_prompt, _with_audit_nonce, CONTROL_AUDIT_NONCE
from src.interpretability.phase_a1 import answer_prefix_ids, build_phase_a1_rows, digit_token_ids, raw_prompt, replay
from src.interpretability.phase_bc import add_fn, build_prompt, capture_layer_outputs, decoder_layers, run_scored
from src.llm_agent import LLMPricingAgent

REPLY_START = "<|im_start|>"


def site_position(tokenizer: Any, ids: Sequence[int], site: str) -> int:
    if site == "answer":
        return len(ids) - 1
    if site == "reply_start":
        tid = tokenizer.convert_tokens_to_ids(REPLY_START)
        pos = [i for i, t in enumerate(ids) if t == tid]
        if not pos:
            raise ValueError("reply-start token not found")
        return pos[-1]
    raise ValueError(site)


def _ids(tokenizer, prompt, prefix):
    return list(tokenizer(prompt, add_special_tokens=False)["input_ids"]) + list(prefix)


def _vec_at(model, ids, layer, pos):
    return capture_layer_outputs(model, ids, [pos])[layer][0].float().cpu()


# ---------------------------------------------------------------------------
# C3
# ---------------------------------------------------------------------------
def task_c3_transfer(model, tokenizer, *, sites=(("reply_start", 18), ("answer", 20)),
                     alphas=(-2, -1, -0.5, 0, 0.5, 1, 1.5, 2), n_random=3, log=None):
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(1, env, persona=None, seed=0)
    digits = digit_token_ids(tokenizer, env.n_prices)
    prefix = answer_prefix_ids(tokenizer, digits)
    by = {}
    for r in build_phase_a1_rows(env):
        by[r.row_id] = (r, _ids(tokenizer, _chat_prompt(raw_prompt(agent, r), tokenizer), prefix))
    controls = sorted({r.control_id for r, _ in by.values()})
    train = [c for i, c in enumerate(controls) if i % 2 == 0]
    test = [c for i, c in enumerate(controls) if i % 2 == 1]
    out = {"task": "c3_transfer", "train_controls": train, "test_controls": test, "alphas": list(alphas), "sites": {}}
    vectors = {}
    for site, layer in sites:
        diffs, nonce = [], []
        for c in train:
            cids = by[f"{c}-control"][1]
            base = _vec_at(model, cids, layer, site_position(tokenizer, cids, site))
            for d in ("undercut", "raise"):
                eids = by[f"{c}-{d}-real"][1]
                diffs.append(_vec_at(model, eids, layer, site_position(tokenizer, eids, site)) - base)
            nids = by[f"{c}-nonce"][1]
            nonce.append(_vec_at(model, nids, layer, site_position(tokenizer, nids, site)) - base)
        v = torch.stack(diffs).mean(0)
        norm = float(v.norm())
        g = torch.Generator().manual_seed(layer)
        dirs = {"edit_vector": v,
                "nonce_vector": torch.stack(nonce).mean(0) / torch.stack(nonce).mean(0).norm() * norm}
        for k in range(n_random):
            rv = torch.randn(v.shape, generator=g)
            dirs[f"random{k}"] = rv / rv.norm() * norm
        consistency = float(torch.nn.functional.cosine_similarity(torch.stack(diffs), v[None], dim=-1).mean())
        key = f"{site}_L{layer}"
        vectors[key] = v.numpy()
        rec = {"layer": layer, "site": site, "vector_norm": norm, "mean_cos_pair_diff_to_vector": consistency,
               "a1_test": [], "b2_test": []}

        def steer(ids, vec, a):
            pos = site_position(tokenizer, ids, site)
            return run_scored(model, ids, digits, {layer: add_fn([pos], a * vec)} if a else None)["expected_index"]

        # held-out A1: add to controls; compare with the real edits of the same histories; rescue edited prompts
        for c in test:
            cids = by[f"{c}-control"][1]
            E0 = run_scored(model, cids, digits)["expected_index"]
            edits = {d: run_scored(model, by[f"{c}-{d}-real"][1], digits)["expected_index"] for d in ("undercut", "raise")}
            curves = {n: [steer(cids, vec, a) - E0 for a in alphas] for n, vec in dirs.items()}
            rescue = {d: {n: steer(by[f"{c}-{d}-real"][1], vec, -1.0) - edits[d] for n, vec in dirs.items()}
                      for d in ("undercut", "raise")}
            rec["a1_test"].append({"control_id": c, "E_control": E0, "E_edits": edits, "curves": curves, "rescue": rescue})
        # fresh B2 histories (no overlap with A1): continuation (deviation 0) vs strong break (>=5)
        from src.interpretability.phase_bc_tasks import B2_RIVAL_PREFIXES, B2_OWN_INDICES, B2_HORIZONS, extrapolate
        for t in ("v1", "v2"):
            for h, nr in B2_HORIZONS.items():
                for fam, pre in B2_RIVAL_PREFIXES.items():
                    for own in B2_OWN_INDICES:
                        ex = extrapolate(pre)
                        far = 0 if ex >= 5 else 9
                        for kind, final in (("continue", ex), ("break", far)):
                            hist = replay(env, [(r, own) for r in pre] + [(final, own)], 20261026)
                            ids = _ids(tokenizer, build_prompt(env, agent, hist, t, tokenizer, n_rounds=nr), prefix)
                            E0 = run_scored(model, ids, digits)["expected_index"]
                            rec["b2_test"].append({"template": t, "horizon": h, "family": fam, "own": own, "kind": kind,
                                                   "final": final, "E": E0,
                                                   "curves": {n: [steer(ids, vec, a) - E0 for a in alphas] for n, vec in dirs.items()}})
        out["sites"][key] = rec
        if log:
            log(f"c3 site {key} done (norm {norm:.1f}, pair consistency {consistency:.2f})")
    return out, {f"vector_{k}": v for k, v in vectors.items()}


# ---------------------------------------------------------------------------
# D: repeated games
# ---------------------------------------------------------------------------
STRATEGIES = ("fixed_monopoly", "fixed_nash", "tit_for_tat", "undercut_by_one", "one_shot_deviation",
              "rise_then_drop", "random", "llm_selfplay")


def rival_action(strategy: str, t: int, joint: list, rng: np.random.Generator, n_prices: int = 10) -> int | None:
    last_llm = joint[-1][1] if joint else None
    if strategy == "fixed_monopoly":
        return 7
    if strategy == "fixed_nash":
        return 2
    if strategy == "tit_for_tat":
        return 7 if last_llm is None else last_llm
    if strategy == "undercut_by_one":
        return 7 if last_llm is None else max(0, last_llm - 1)
    if strategy == "one_shot_deviation":  # cooperative except a single undercut, then back
        return 2 if t == 6 else 7
    if strategy == "rise_then_drop":       # steady upward trend, then a sudden break
        return min(7, 1 + t) if t < 9 else 2
    if strategy == "random":
        return int(rng.integers(0, n_prices))
    if strategy == "llm_selfplay":
        return None
    raise ValueError(strategy)


def task_d1_games(model, tokenizer, *, strategies=STRATEGIES, rounds: int = 15, seeds=(0, 1, 2, 3),
                  steering: dict | None = None, log=None):
    """Greedy (argmax) game plus sampled games per strategy; optional steering of agent 1.

    steering = {"vector": [d], "layer": int, "site": "answer"|"reply_start", "alphas": [..]}.
    """
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agents = {i: LLMPricingAgent(i, env, persona=None, seed=0) for i in (0, 1)}
    digits = digit_token_ids(tokenizer, env.n_prices)
    prefix = answer_prefix_ids(tokenizer, digits)
    conds = [("none", 0.0)]
    vec = None
    if steering:
        vec = torch.tensor(np.asarray(steering["vector"], dtype=np.float32))
        conds += [(f"steer{a:+g}", float(a)) for a in steering["alphas"] if a != 0]

    def decide(agent_id, history, t, rng, mode, alpha):
        raw = agents[agent_id]._build_prompt(history, t, rounds)
        ids = _ids(tokenizer, _chat_prompt(_with_audit_nonce(raw, CONTROL_AUDIT_NONCE), tokenizer), prefix)
        hooks = None
        if alpha and agent_id == 1:
            pos = site_position(tokenizer, ids, steering["site"])
            hooks = {steering["layer"]: add_fn([pos], alpha * vec)}
        res = run_scored(model, ids, digits, hooks)
        p = np.asarray(res["digit_probs"])
        a = int(np.argmax(p)) if mode == "greedy" else int(rng.choice(len(p), p=p / p.sum()))
        return a, res

    games = []
    for cond, alpha in conds:
        for strategy in strategies:
            for mode, seed in [("greedy", 0)] + [("sample", s) for s in seeds]:
                rng = np.random.default_rng(1000 + seed)
                env.reset(np.random.default_rng(seed))
                history, joint, rows = [], [], []
                for t in range(rounds):
                    r_act = rival_action(strategy, t, joint, rng)
                    r_info = None
                    if r_act is None:
                        r_act, r_res = decide(0, history, t, rng, mode, 0.0)
                        r_info = {"E": r_res["expected_index"]}
                    a1, res1 = decide(1, history, t, rng, mode, alpha)
                    _, profits, info = env.step((r_act, a1))
                    history.append((np.asarray(info["prices"]).copy(), np.asarray(profits).copy()))
                    joint.append((r_act, a1))
                    rows.append({"t": t, "rival_action": r_act, "llm_action": a1, "llm_E": res1["expected_index"],
                                 "llm_probs": res1["digit_probs"], "prices": info["prices"].tolist(),
                                 "profits": profits.tolist(), "rival_llm": r_info})
                prof = np.array([r["profits"] for r in rows])
                games.append({"condition": cond, "alpha": alpha, "strategy": strategy, "mode": mode, "seed": seed,
                              "rounds": rows,
                              "mean_llm_action": float(np.mean([r["llm_action"] for r in rows])),
                              "mean_rival_action": float(np.mean([r["rival_action"] for r in rows])),
                              "collusion_index_llm": float(env.collusion_index(prof[:, 1])),
                              "collusion_index_joint": float(env.collusion_index(prof.mean(1)))})
            if log:
                log(f"d1 {cond} {strategy} done")
    return {"task": "d1_games", "rounds": rounds, "strategies": list(strategies), "seeds": list(seeds),
            "steering": None if not steering else {k: v for k, v in steering.items() if k != "vector"},
            "benchmarks": {"nash_index_nearest": int(np.argmin(abs(env.price_grid - env.p_nash))),
                           "monopoly_index_nearest": int(np.argmin(abs(env.price_grid - env.p_monop))),
                           "pi_nash": env.pi_nash, "pi_monop": env.pi_monop},
            "games": games}, {}
