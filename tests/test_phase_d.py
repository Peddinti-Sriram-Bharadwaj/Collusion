"""Tiny-model tests for Phase C3/D plumbing (no downloads)."""
from __future__ import annotations

import numpy as np
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM

from src.interpretability import phase_d as D
from tests.test_phase_bc import CharTokDecode


def _model():
    torch.manual_seed(0)
    cfg = Qwen2Config(vocab_size=256, hidden_size=32, intermediate_size=64, num_hidden_layers=3,
                      num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=8192)
    return Qwen2ForCausalLM(cfg).eval()


def test_rival_strategies():
    rng = np.random.default_rng(0)
    assert D.rival_action("tit_for_tat", 0, [], rng) == 7
    assert D.rival_action("tit_for_tat", 3, [(7, 4)], rng) == 4
    assert D.rival_action("undercut_by_one", 3, [(7, 0)], rng) == 0
    assert [D.rival_action("one_shot_deviation", t, [], rng) for t in (5, 6, 7)] == [7, 2, 7]
    assert D.rival_action("rise_then_drop", 9, [], rng) == 2 and D.rival_action("llm_selfplay", 0, [], rng) is None


def test_games_run_and_steering_changes_decisions():
    m, tok = _model(), CharTokDecode()
    res, _ = D.task_d1_games(m, tok, strategies=("fixed_monopoly", "llm_selfplay"), rounds=3, seeds=(0,),
                             steering={"vector": np.ones(32) * 30, "layer": 2, "site": "answer", "alphas": [1]})
    g = res["games"]
    assert len(g) == 2 * 2 * 2 and all(len(x["rounds"]) == 3 for x in g)
    base = [x for x in g if x["condition"] == "none" and x["mode"] == "greedy" and x["strategy"] == "fixed_monopoly"][0]
    st = [x for x in g if x["condition"] != "none" and x["mode"] == "greedy" and x["strategy"] == "fixed_monopoly"][0]
    assert base["rounds"][0]["llm_probs"] != st["rounds"][0]["llm_probs"]
    sp = [x for x in g if x["strategy"] == "llm_selfplay"][0]
    assert sp["rounds"][0]["rival_llm"] is not None
