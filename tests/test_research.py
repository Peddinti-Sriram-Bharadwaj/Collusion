"""Tests for the research workflow (configs, rivals, metrics, stats, registry, steering, prompts, end-to-end)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM

from src.research import analysis as A, configs as C, decision as Dc, metrics as M, prompts as P, stats as S
from src.research import steering as St
from src.research.economics import ECON_PRESETS, benchmarks, collusion_index, profits
from src.research.registry import Registry
from src.research.rivals import DeviationDesign, SCRIPTED, returns_at, scripted_sequence
from src.research.runner import execute, register_results


# ---------------------------------------------------------------- economics / rivals
def test_benchmarks_from_payoff():
    b = benchmarks(ECON_PRESETS["base"])
    assert b["nash_index"] == 2 and b["monopoly_index"] == 7
    assert b["best_response_by_rival_index"] == [1, 1, 2, 2, 3, 3, 4, 4, 4, 4]
    r, o = profits(ECON_PRESETS["base"], 7, 7)
    assert abs(collusion_index(ECON_PRESETS["base"], o) - 1.0) < 0.01


def test_scripted_conditions_matched_before_deviation():
    d = DeviationDesign()
    seqs = {c: scripted_sequence(c, d) for c in SCRIPTED}
    for c in ("B_one_shot", "C_persistent", "F_delayed", "G_raise"):
        assert seqs[c][: d.deviation_round] == seqs["A_stable"][: d.deviation_round]
        assert seqs[c][d.deviation_round] != d.high
    assert seqs["D_gradual"][d.deviation_round] == d.low == seqs["C_persistent"][d.deviation_round]
    assert returns_at("B_one_shot", d) == d.deviation_round + 1 and returns_at("C_persistent", d) is None
    with pytest.raises(ValueError):
        DeviationDesign(low=7, high=7).validate(10)


# ---------------------------------------------------------------- configs
def test_expand_is_idempotent_and_validated(tmp_path):
    spec = {"batch_id": "b", "protocol": "p", "designation": "smoke", "model": "7b",
            "blocks": [{"name": "x", "grid": {"condition": ["A_stable", "B_one_shot"], "seeds.history_seed": [0, 1]}},
                       {"name": "y", "grid": {"condition": ["A_stable"]}}]}
    u = C.expand(spec)
    assert len(u) == 4  # block y duplicates an existing unit -> de-duplicated
    assert len({x["unit_id"] for x in u}) == 4 and C.expand(spec)[0]["unit_id"] == u[0]["unit_id"]
    bad = json.loads(json.dumps(spec)); bad["blocks"][0]["grid"]["condition"] = ["Z"]
    with pytest.raises(ValueError):
        C.expand(bad)
    est = C.estimate(u)
    assert est["forward_passes"] == 4 * 16


# ---------------------------------------------------------------- metrics / stats
def _rounds(E, own=0.2, riv=0.2):
    return [{"expected_index": e, "action": int(round(e)), "own_profit": own, "rival_profit": riv} for e in E]


def test_pair_metrics():
    A_ = _rounds([7] * 12)
    X = _rounds([7] * 6 + [4, 5, 7, 7, 7, 7])  # td=5 -> response at t=6
    m = M.pair_metrics(X, A_, td=5, returns_at=6)
    assert m["pre_gap"] == 0 and m["immediate"] == -3 and m["peak"] == -3 and m["latency"] == 1 and m["duration"] == 2
    assert m["recovery_gap"] == pytest.approx((-2 + 0 + 0) / 3) and m["recovery_time"] == 2


def test_stats_labels():
    s = S.summarize([-1.0, -1.2, -0.8, -1.1, -0.9], clusters=[0, 1, 2, 3, 4], seed=1)
    assert s["ci_high"] < 0 and S.cell_status(s, "negative") == "supported"
    z = S.summarize([0.01, -0.02, 0.0, 0.02, -0.01], clusters=range(5))
    assert S.cell_status(z, "negative") == "absent" and S.cell_status(z, "near_zero") == "supported"
    assert S.cell_status(S.summarize([1.0, 2.0], [0, 1]), "positive") == "insufficient"
    assert S.replication_status(["supported"] * 4 + ["inconclusive"]) == "robust"
    assert S.replication_status(["absent", "absent", "supported"]) == "not replicated"
    assert S.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    # clustered: repeated rounds of one cluster do not count as independent
    s2 = S.summarize([1.0] * 10, clusters=[0] * 10)
    assert s2["n_clusters"] == 1 and S.cell_status(s2, "positive") == "insufficient"


def test_did():
    assert M.did(-2.0, 0.0, -1.0, 0.0) == -1.0 and M.did(None, 0, 0, 0) is None


# ---------------------------------------------------------------- registry
def test_registry_append_dedupe_verify(tmp_path):
    reg = Registry(tmp_path / "research")
    path, sha = reg.write_raw("b1", "r1", {"x": 1})
    assert reg.register_run({"run_id": "r1", "batch_id": "b1", "status": "completed", "raw_path": path, "raw_sha256": sha})
    assert not reg.register_run({"run_id": "r1", "batch_id": "b1", "status": "completed"})
    assert reg.register_run({"run_id": "r2", "batch_id": "b1", "status": "failed", "error": "x"})
    assert reg.verify()["problems"] == [] and reg.completed_ids() == {"r1"}
    assert reg.read_raw(path) == {"x": 1}
    with open(reg.reg / "runs.jsonl", "a") as f:
        f.write("{not json\n")
    with pytest.raises(ValueError):
        reg.records()


# ---------------------------------------------------------------- decoding / steering / prompts
def test_choose_greedy_and_sampling():
    lp = np.log(np.array([0.1, 0.6, 0.3] + [1e-9] * 7))
    assert Dc.choose(lp, {"mode": "greedy"}, 0.99)[0] == 1
    a, p = Dc.choose(lp, {"mode": "sample", "temperature": 1.0, "top_p": 0.55, "top_k": 0}, 0.99)
    assert a == 1 and p[2] == 0  # nucleus keeps only the top token
    a, p = Dc.choose(lp, {"mode": "sample", "temperature": 1.0, "top_p": 1.0, "top_k": 2}, 0.05)
    assert a == 1 and p[0] == 0


def test_vector_alignment_checks(tmp_path):
    St.save_vector("v", np.ones(8), {"layer": 20, "site": "answer", "model_key": "7b"}, root=tmp_path)
    base = {"kind": "learned", "vector_id": "v", "alpha": 1.0, "layer": 20, "site": "answer"}
    v, prov = St.resolve(base, {"d_model": 8, "model_key": "7b"}, tmp_path)
    assert prov["layer"] == 20 and np.allclose(v, 1)
    for bad, meta in (({**base, "layer": 18}, {"d_model": 8}), (base, {"d_model": 16}), (base, {"d_model": 8, "model_key": "14b"})):
        with pytest.raises(ValueError):
            St.resolve(bad, meta, tmp_path)
    r, _ = St.resolve({**base, "kind": "random", "random_seed": 3}, {"d_model": 8}, tmp_path)
    assert np.isclose(np.linalg.norm(r), np.linalg.norm(np.ones(8)))
    s, _ = St.resolve({**base, "kind": "sham"}, {"d_model": 8}, tmp_path)
    assert not s.any()


class ChatTok:
    def encode(self, text, add_special_tokens=False):
        return [min(ord(c), 255) for c in text]
    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        return {"input_ids": self.encode(text)}
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        return "".join(f"<{m['role']}>{m['content']}" for m in messages) + "<assistant>"
    def decode(self, ids, skip_special_tokens=True):
        return "".join(chr(i) for i in ids)
    def convert_tokens_to_ids(self, t):
        return 60


def test_v1_template_matches_legacy_game_prompt():
    from src.interpretability.modal_phase_a import _chat_prompt, _with_audit_nonce, CONTROL_AUDIT_NONCE
    from src.llm_agent import LLMPricingAgent
    from src.research.economics import env_for
    env = env_for(ECON_PRESETS["base"]); g = env.price_grid
    hist = [(np.array([g[7], g[4]]), np.array([0.2, 0.3]))] * 3
    tok = ChatTok()
    legacy = _chat_prompt(_with_audit_nonce(LLMPricingAgent(1, env)._build_prompt(hist, 3, 15), CONTROL_AUDIT_NONCE), tok)
    assert P.render(tok, env, hist, 1, 3, 15, "v1") == legacy
    for t in P.TEMPLATES:
        txt = P.render(tok, env, hist, 1, 3, 15, t)
        assert '{"price_index": <integer>}' in txt and "1.94" in txt  # rival price present in every template
    assert "of 15" not in P.render(tok, env, hist, 1, 3, 15, "v1_implicit_horizon")


# ---------------------------------------------------------------- end to end on a tiny model
@pytest.fixture(scope="module")
def tiny():
    torch.manual_seed(0)
    cfg = Qwen2Config(vocab_size=256, hidden_size=16, intermediate_size=32, num_hidden_layers=3, num_attention_heads=2,
                      num_key_value_heads=1, max_position_embeddings=8192)
    return Qwen2ForCausalLM(cfg).eval()


def test_end_to_end_registry_analysis_plots_report(tiny, tmp_path, monkeypatch):
    vroot = tmp_path / "vectors"
    St.save_vector("vec", np.ones(16) * 5, {"layer": 2, "site": "answer", "model_key": "tiny"}, root=vroot)
    spec = {"batch_id": "t1", "protocol": A.PROTOCOL, "designation": "smoke", "model": "7b",
            "base": {"design": {"rounds": 6, "deviation_round": 2, "high": 7, "low": 2, "recovery_delay": 2},
                     "audit_generation": "deviation_window", "prefix_rounds": 2},
            "blocks": [{"name": "primary", "grid": {"condition": ["A_stable", "B_one_shot", "C_persistent"],
                                                     "seeds.history_seed": [0, 1, 2, 3],
                                                     "steering_preset": [{"steering": {"kind": "none"}},
                                                                         {"steering": {"kind": "learned", "vector_id": "vec", "alpha": 1.0, "layer": 2}},
                                                                         {"steering": {"kind": "sham", "vector_id": "vec", "alpha": 1.0, "layer": 2}}]}},
                       {"name": "fixed_history", "overrides": {"experiment": "fixed_history"},
                        "grid": {"condition": ["H_sudden", "H_gradual", "H_always_low", "H_stable_high"], "seeds.history_seed": [0, 1]}}]}
    units = C.expand(spec)
    reg = Registry(tmp_path / "research")
    items = []
    meta = {"model_key": "tiny", "d_model": 16, "backend": "test"}
    stats = execute(tiny, ChatTok(), units, batch={**spec, "git": {"commit": "x"}}, model_meta=meta,
                    sink=lambda r, p: items.append((r, p)), vector_root=vroot)
    assert stats["failed"] == 0, [r for r, _ in items if r["status"] == "failed"][:1]
    assert register_results(reg, items)["added"] == len(units)
    assert register_results(reg, items)["duplicates_skipped"] == len(units)  # idempotent
    # resume: executing again with the completed set skips everything
    assert execute(tiny, ChatTok(), units, batch={**spec, "git": {}}, model_meta=meta, sink=lambda r, p: None,
                   skip=reg.completed_ids(), vector_root=vroot)["skipped"] == len(units)
    assert reg.verify()["problems"] == []
    # sham hook leaves outputs unchanged
    recs = {r["config"]["steering"]["kind"] + r["config"]["condition"] + str(r["config"]["seeds"]["history_seed"]): r
            for r in reg.records() if r["config"]["experiment"] == "deviation_game"}
    a = reg.read_raw(recs["noneB_one_shot0"]["raw_path"])["rounds"]; b = reg.read_raw(recs["shamB_one_shot0"]["raw_path"])["rounds"]
    assert [x["digit_logprobs"] for x in a] == [x["digit_logprobs"] for x in b]
    # no future leakage: prompt length at round t only grows with history (rival action at t unseen)
    assert all(a[i]["prompt_tokens"] < a[i + 1]["prompt_tokens"] for i in range(len(a) - 1))
    out = tmp_path / "out"
    tables = A.build_tables(reg, out)
    assert len(tables["pairs"]) == 2 * 4 * 3 and len(tables["did"]) == 2 * 4 * 2 and not tables["fixed_history"].empty
    assert (tables["pairs"]["pre_gap"].abs() < 1e-9).all()  # identical scripts before t_d -> identical prices
    grid = A.behaviour_grid(tables)
    assert set(["behaviour", "status", "replication_status"]) <= set(grid.columns)
    from src.research import plots, report
    man = plots.make_all(tables, grid, reg.records(), out, "h", formats=("png",))
    made = [m for m in man if not m.get("skipped")]
    assert len(made) >= 8 and all((out / "figures" / m["files"][0]).exists() for m in made)
    rp = report.write_report(out, reg.records(), [], tables, grid, man, "h")
    txt = rp.read_text()
    assert "## 9. Limitations" in txt and "punishment_like_reduction" in txt, txt[txt.find("## 4."):txt.find("## 4.") + 1500]


def test_hypothesis_estimators_synthetic():
    import pandas as pd
    from src.research.hypotheses import estimates
    rows, pt, lvl, did, fh = [], [], [], [], []
    for h in range(6):
        cl = f"base|p4|4-8|s{h}"
        com = dict(history_cluster=cl, designation="confirmatory", replicate=0, block="primary", deviation_round=7,
                   prefixed_audits=4, prefixed_valid=4)
        rows.append(dict(run_id=f"b{h}", condition="B_one_shot", steer_kind="none", immediate=-1.0 - 0.1 * h, recovery_gap=0.05, **com))
        rows.append(dict(run_id=f"rep{h}", condition="B_one_shot", steer_kind="none", immediate=99.0, recovery_gap=99.0,
                         **{**com, "replicate": 1}))
        for t in range(16):
            pt.append(dict(run_id=f"b{h}", t=t, delta=0.0, condition="B_one_shot", steer_kind="none", **com))
            pt.append(dict(run_id=f"c{h}", t=t, delta=-1.0 if t > 7 else 0.0, condition="C_persistent", steer_kind="none", **com))
        lvl.append(dict(run_id=f"l{h}", steer_kind="learned", alpha=1.0, steer_timing="all", level_shift=-0.8, **com))
        for r in range(3):
            lvl.append(dict(run_id=f"r{h}{r}", steer_kind="random", alpha=1.0, steer_timing="all", level_shift=0.02 * r, **com))
        did.append(dict(run_id=f"d{h}", steer_kind="learned", alpha=1.0, steer_timing="all", condition="B_one_shot", did_immediate=0.01 * h, **com))
        fh.append(dict(run_id=f"f{h}", steer_kind="none", **{"H_sudden-H_gradual": -0.5}, **com))
    T = {"pairs": pd.DataFrame(rows), "pair_traj": pd.DataFrame(pt), "steer_level": pd.DataFrame(lvl), "did": pd.DataFrame(did),
         "fixed_history": pd.DataFrame(fh)}
    h = estimates(T, "confirmatory").set_index("hypothesis")
    assert h.loc["H1", "n_clusters"] == 6 and h.loc["H1", "mean"] < -1 and h.loc["H1", "status"] == "supported"  # replicate excluded
    assert h.loc["H2a", "status"] == "supported"            # inside the equivalence margin
    assert abs(h.loc["H2b", "mean"] + 1.0) < 1e-9          # C minus B after B's return
    assert abs(h.loc["H4", "mean"] - (-0.82)) < 1e-9        # learned minus mean of randoms
    assert h.loc["H3", "status"] == "supported"
    assert h["p_holm"].notna().all()
