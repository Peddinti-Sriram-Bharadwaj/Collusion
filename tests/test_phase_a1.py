"""Mock-only tests for Phase A.1 design, scoring and summaries (no downloads)."""
from __future__ import annotations

import numpy as np
import pytest
import torch

from src.env import LogitBertrandEnv
from src.interpretability import phase_a1 as A1


def test_design_is_crossed_and_complete():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    rows = A1.build_phase_a1_rows(env)
    assert len(rows) == 144 and len({r.row_id for r in rows}) == 144
    controls = {r.control_id for r in rows}
    assert len(controls) == 24
    for cid in controls:
        group = [r for r in rows if r.control_id == cid]
        conds = sorted((r.condition, r.edit_direction) for r in group)
        assert conds == sorted([("control_realistic", None), ("negative_control_audit_nonce", None),
                                ("synthetic_stale_profit", "undercut"), ("synthetic_stale_profit", "raise"),
                                ("realistic_rival_final", "undercut"), ("realistic_rival_final", "raise")])


def test_arms_differ_only_where_intended():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    rows = {r.row_id: r for r in A1.build_phase_a1_rows(env)}
    ctrl, stale, real = rows["phase-a-005-control"], rows["phase-a-005-undercut-stale"], rows["phase-a-005-undercut-real"]
    # earlier rounds identical in all arms
    for a, b in zip(ctrl.history[:-1], real.history[:-1]):
        assert np.allclose(a[0], b[0]) and np.allclose(a[1], b[1])
    # stale arm: rival price edited, profits untouched
    assert stale.history[-1][0][0] == pytest.approx(env.price_grid[0])
    assert np.allclose(stale.history[-1][1], ctrl.history[-1][1])
    # realistic arm: profits recomputed by the environment
    expected = env._profits(np.array([env.price_grid[0], env.price_grid[ctrl.own_price_index]]))
    assert np.allclose(real.history[-1][1], expected)
    assert not np.allclose(real.history[-1][1], ctrl.history[-1][1])


class Tok:
    """Character-level toy tokenizer: digits are single tokens."""
    def encode(self, text, add_special_tokens=False):
        return [ord(c) for c in text]
    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        out = {"input_ids": [ord(c) for c in text]}
        if return_offsets_mapping:
            out["offset_mapping"] = [(i, i + 1) for i in range(len(text))]
        return out


def test_token_helpers():
    tok = Tok()
    digits = A1.digit_token_ids(tok)
    assert digits == [ord(str(d)) for d in range(10)]
    assert A1.answer_prefix_ids(tok, digits) == [ord(c) for c in A1.ANSWER_PREFIX]
    prompt = "Round 0: ...; rival price(s): $1.33\nRound 1: ...; rival price(s): $1.42\nend"
    pos = A1.rival_price_token_positions(tok, prompt)
    assert "".join(prompt[i] for i in pos) == "1.42"


def test_multi_token_digit_rejected():
    class Bad(Tok):
        def encode(self, text, add_special_tokens=False):
            return [1, 2] if text == "7" else super().encode(text)
    with pytest.raises(ValueError):
        A1.digit_token_ids(Bad())


class ToyModel:
    device = "cpu"
    def __init__(self, vocab=200, d=4, layers=2):
        self.vocab, self.d, self.layers = vocab, d, layers
    def __call__(self, input_ids, output_hidden_states=False, use_cache=False):
        T = input_ids.shape[1]
        logits = torch.full((1, T, self.vocab), -1e4)
        logits[0, -1, ord("4")] = 2.0
        logits[0, -1, ord("5")] = 1.0
        class Out: pass
        o = Out(); o.logits = logits
        if output_hidden_states:
            o.hidden_states = tuple(torch.full((1, T, self.d), float(l)) for l in range(self.layers + 1))
        return o


def test_score_digits_distribution_and_capture():
    digits = [ord(str(d)) for d in range(10)]
    res = A1.score_digits(ToyModel(), [1, 2, 3], digits, {"answer": [2], "span": [0, 1]})
    p = np.array(res["digit_probs"])
    assert p.sum() == pytest.approx(1.0) and res["argmax_index"] == 4
    assert res["expected_index"] == pytest.approx(4 + np.exp(1) / (np.exp(1) + np.exp(2)), rel=1e-4)
    assert res["digit_mass"] == pytest.approx(1.0, abs=1e-3)
    assert res["hidden"]["answer"].shape == (3, 4) and res["hidden"]["answer"][2, 0] == 2.0


def test_summary_deltas():
    def row(cid, cond, direction, e):
        probs = np.zeros(10); probs[int(e)] = 1
        return {"control_id": cid, "condition": cond, "edit_direction": direction, "expected_index": e,
                "digit_probs": probs.tolist(), "digit_mass": 1.0, "argmax_index": int(e), "eps1_optimal_set": [4]}
    rows = [row("c", "control_realistic", None, 4), row("c", "realistic_rival_final", "raise", 6),
            row("c", "negative_control_audit_nonce", None, 4)]
    s = A1.summarise_phase_a1(rows)
    assert s["delta_expected_index_vs_control"]["realistic_rival_final:raise"]["mean"] == 2
    assert s["delta_expected_index_vs_control"]["negative_control_audit_nonce"]["mean"] == 0
    assert s["mean_total_variation_vs_control"]["realistic_rival_final:raise"] == 1.0
