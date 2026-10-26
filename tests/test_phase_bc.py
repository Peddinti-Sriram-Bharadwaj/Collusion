"""Hook-level tests for Phase B/C primitives on a tiny random Qwen2 (no downloads)."""
from __future__ import annotations

import numpy as np
import pytest
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM

from src.env import LogitBertrandEnv
from src.interpretability import phase_bc as BC


class CharTok:
    def encode(self, text, add_special_tokens=False):
        return [min(ord(c), 255) for c in text]
    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        out = {"input_ids": self.encode(text)}
        if return_offsets_mapping:
            out["offset_mapping"] = [(i, i + 1) for i in range(len(text))]
        return out
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        return "<u>" + messages[0]["content"] + "<a>"


@pytest.fixture(scope="module")
def model():
    torch.manual_seed(0)
    cfg = Qwen2Config(vocab_size=256, hidden_size=32, intermediate_size=64, num_hidden_layers=3,
                      num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=4096)
    return Qwen2ForCausalLM(cfg).eval()


DIGITS = [ord(str(d)) for d in range(10)]


def test_b1_design_disjoint_from_phase_a():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    rows = BC.build_b1_rows(env)
    assert len(rows) == 2 * 6 * 3 * 10
    assert not set(BC.B1_OWN_INDICES) & {2, 5, 8}
    for r in rows[:30]:
        assert r.history[-1][0][0] == pytest.approx(env.price_grid[r.final_rival_index])


def test_rival_positions_both_templates(model):
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    from src.llm_agent import LLMPricingAgent
    agent = LLMPricingAgent(1, env, persona=None)
    tok = CharTok()
    r = BC.build_b1_rows(env)[7]
    for t in ("v1", "v2"):
        p = BC.build_prompt(env, agent, r.history, t, tok)
        pos = BC.final_rival_positions(tok, p, t)
        assert "".join(p[i] for i in pos) == f"{env.price_grid[r.final_rival_index]:.2f}"


def test_zero_add_and_identity_patch_are_noops(model):
    ids = list(range(40, 80))
    base = BC.run_scored(model, ids, DIGITS)
    same = BC.run_scored(model, ids, DIGITS, {1: BC.add_fn([5, 6], torch.zeros(32))})
    assert np.allclose(base["digit_probs"], same["digit_probs"], atol=1e-6)
    vals = BC.capture_layer_outputs(model, ids, [5, 6])[1]
    patched = BC.run_scored(model, ids, DIGITS, {1: BC.patch_fn([5, 6], vals)})
    assert np.allclose(base["digit_probs"], patched["digit_probs"], atol=1e-6)


def test_full_patch_reproduces_donor(model):
    rec = list(range(40, 80)); don = rec.copy(); don[10] = 120
    donor = BC.run_scored(model, don, DIGITS)
    pos = list(range(10, 40))  # every position at/after the difference
    vals = BC.capture_layer_outputs(model, don, pos)[0]
    patched = BC.run_scored(model, rec, DIGITS, {0: BC.patch_fn(pos, vals)})
    assert np.allclose(donor["digit_probs"], patched["digit_probs"], atol=1e-5)


def test_capture_shapes_and_steering_changes_output(model):
    ids = list(range(40, 80))
    res = BC.run_with_capture(model, ids, DIGITS, {"a": [39], "b": [3, 4]})
    assert res["acts"]["a"].shape == (3, 32)
    steered = BC.run_scored(model, ids, DIGITS, {2: BC.add_fn([39], torch.ones(32) * 50)})
    assert not np.allclose(steered["digit_probs"], res["digit_probs"])


def test_pre_final_round_site_is_causally_blind():
    from src.interpretability.phase_bc_tasks import pre_final_round_position
    from src.llm_agent import LLMPricingAgent
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(1, env, persona=None)
    tok = CharTok()
    rows = [r for r in BC.build_b1_rows(env) if r.family == "flat_3" and r.own_price_index == 1]
    for t in ("v1", "v2"):
        a, b = [BC.build_prompt(env, agent, r.history, t, tok) for r in rows if r.template == t][:2]
        pa, pb = pre_final_round_position(tok, a, t), pre_final_round_position(tok, b, t)
        assert pa == pb and a[:pa + 1] == b[:pb + 1]  # identical prefix up to the null site
        first_diff = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
        assert first_diff > pa


class CharTokDecode(CharTok):
    def decode(self, ids, skip_special_tokens=True):
        return "".join(chr(i) for i in ids)


def test_b2_and_position_patching_and_after_rival_steering(model):
    from src.interpretability import phase_bc_tasks as T
    assert T.extrapolate((1, 2, 3)) == 4 and T.extrapolate((7, 5, 3)) == 1 and T.extrapolate((3, 5, 7)) == 9
    tok = CharTokDecode()
    res, _ = T.task_b2_confirm(model, tok, templates=("v1",))
    assert len(res["rows"]) == 2 * 6 * 2 * 10
    finals = [r for r in res["rows"] if r["horizon"] == "nonfinal"]
    assert all(r["deviation"] == abs(r["final_rival_index"] - r["extrapolated_index"]) for r in finals)
    pos, _ = T.task_c1_positions(model, tok, controls=["phase-a-000"], layers=(1,))
    r = pos["results"][0]
    assert len(r["E_patched"][0]) == len(r["positions"]) and r["positions"][0] == r["rival_positions"][0]
    # patching the last position at the final layer reproduces nothing special, but values are finite
    assert np.isfinite(r["E_patched"]).all()
    st, _ = T.task_c2_steer(model, tok, directions={"z": np.zeros(32) + 1.0}, layer=1, site="after_rival",
                            alphas=(0, 1), controls=["phase-a-000"])
    rec = st["results"][0]
    assert rec["n_positions"] > 5 and len(rec["digit_mass"]["z"]) == 2
