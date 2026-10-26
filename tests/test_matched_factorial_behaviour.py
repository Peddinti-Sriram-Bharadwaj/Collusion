"""Mock-only tests for the uncommitted 3x4 matched factorial experiment."""
from __future__ import annotations

import numpy as np
import torch

from scripts import run_hf_matched_factorial_behaviour as factorial
from src.env import LogitBertrandEnv


class _Tokenizer:
    def __call__(self, prompt, return_tensors):
        assert return_tensors == "pt"
        return {"input_ids": torch.tensor([[11, 12, 13]]), "attention_mask": torch.tensor([[1, 1, 1]])}

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize is False and add_generation_prompt is True
        return "<chat>" + messages[0]["content"]

    def decode(self, token_ids, skip_special_tokens):
        assert skip_special_tokens is True
        return '{"price_index": 4}'


class _Model:
    device = None

    def generate(self, input_ids, attention_mask, **kwargs):
        assert kwargs == {"do_sample": False, "max_new_tokens": 32, "temperature": None, "top_p": None, "top_k": None}
        return torch.cat([input_ids, torch.tensor([[99]])], dim=1)


class _Extractor:
    model_id = "mock/qwen"
    revision = "test"
    tokenizer_revision = "test"

    def __init__(self):
        self.model = _Model()
        self.tokenizer = _Tokenizer()
        self.capture_final_prompt_token = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no activation extraction"))

    def _prepare_inputs(self, prompt):
        return self.tokenizer(prompt, return_tensors="pt")


def test_factorial_design_is_complete_and_has_matched_four_round_histories():
    scenarios = factorial.generate_factorial_scenarios(seed=11)
    assert len(scenarios) == 12
    assert {(s.own_price_group, s.rival_price_pattern) for s in scenarios} == {
        (own, rival)
        for own in ("consistently_low", "consistently_mid", "consistently_high")
        for rival in ("consistently_low", "consistently_high", "rising", "falling")
    }
    for own_group in ("consistently_low", "consistently_mid", "consistently_high"):
        own_rows = [scenario for scenario in scenarios if scenario.own_price_group == own_group]
        assert len(own_rows) == 4
        assert len({scenario.own_action_indices for scenario in own_rows}) == 1
        assert all(len(scenario.own_action_indices) == len(scenario.rival_action_indices) == 4 for scenario in own_rows)


def test_factorial_market_histories_follow_environment_profit_rules():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    for scenario in factorial.generate_factorial_scenarios(seed=4):
        history = factorial.materialize_factorial_history(env, scenario)
        assert len(history) == 4
        for row, rival, own in zip(history, scenario.rival_action_indices, scenario.own_action_indices):
            prices = env.price_grid[np.asarray([rival, own])]
            assert row["action_indices"] == [rival, own]
            assert np.allclose(row["prices"], prices)
            assert np.allclose(row["profits"], env._profits(prices))


def test_factorial_output_has_protocol_pairs_and_complete_metadata(monkeypatch):
    monkeypatch.setattr(factorial.HFActivationExtractor, "from_pretrained", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no download")))
    result = factorial.run_factorial_experiment(_Extractor(), seed=2, protocol="both")
    assert result["activation_extraction"] is False
    assert len(result["rows"]) == 24
    assert all(row["history_length"] == 4 and len(row["market_history"]) == 4 for row in result["rows"])
    assert all(row["parse_valid"] and len(row["prompt_hash"]) == 64 for row in result["rows"])
    assert {row["protocol"] for row in result["rows"]} == {factorial.RAW_PROTOCOL, factorial.CHAT_PROTOCOL}
    paired = {}
    for row in result["rows"]:
        paired.setdefault(row["scenario_id"], set()).add(row["protocol"])
    assert len(paired) == 12 and all(protocols == {factorial.RAW_PROTOCOL, factorial.CHAT_PROTOCOL} for protocols in paired.values())
    summary = result["summary"]
    assert summary["prompt_protocol_effect_matched"]["valid_matched_cells"] == 12
    assert set(summary["rival_price_history_effect_within_own_group"]) == {
        "consistently_low", "consistently_mid", "consistently_high"
    }


def test_factorial_replay_is_deterministic():
    first = factorial.run_factorial_experiment(_Extractor(), seed=2, protocol="raw")
    second = factorial.run_factorial_experiment(_Extractor(), seed=2, protocol="raw")
    assert first == second
