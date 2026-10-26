"""Mock-only checks for the uncommitted matched-history experiment."""
from __future__ import annotations

import numpy as np
import torch

from scripts import run_hf_matched_history_sensitivity as matched
from src.env import LogitBertrandEnv


class _Tokenizer:
    def __call__(self, prompt, return_tensors):
        assert return_tensors == "pt"
        return {"input_ids": torch.tensor([[11, 12, 13]]), "attention_mask": torch.tensor([[1, 1, 1]])}

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize is False and add_generation_prompt is True
        return "<chat>" + messages[0]["content"]

    def decode(self, token_ids, skip_special_tokens):
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


def test_matched_histories_share_own_actions_and_follow_market_rules():
    scenarios = matched.generate_matched_history_scenarios(seed=9)
    assert len(scenarios) == 4
    assert {scenario.own_action_indices for scenario in scenarios} == {(5, 5, 5, 5)}
    assert {scenario.rival_pattern for scenario in scenarios} == {
        "consistently_low", "consistently_high", "falling", "rising"
    }
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    for scenario in scenarios:
        history = matched.materialize_matched_history(env, scenario)
        assert len(history) == 4
        for row, rival, own in zip(history, scenario.rival_action_indices, scenario.own_action_indices):
            prices = env.price_grid[np.asarray([rival, own])]
            assert row["action_indices"] == [rival, own]
            assert np.allclose(row["prices"], prices)
            assert np.allclose(row["profits"], env._profits(prices))


def test_matched_experiment_records_separate_protocols_and_complete_rows(monkeypatch):
    monkeypatch.setattr(matched.HFActivationExtractor, "from_pretrained", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no download")))
    result = matched.run_matched_history_experiment(_Extractor(), seed=3, protocol="both")
    assert result["activation_extraction"] is False
    assert len(result["rows"]) == 8
    assert {row["protocol"] for row in result["rows"]} == {matched.RAW_PROTOCOL, matched.CHAT_PROTOCOL}
    assert all(row["history_length"] == 4 and len(row["market_history"]) == 4 for row in result["rows"])
    assert all(row["parse_valid"] and len(row["prompt_hash"]) == 64 for row in result["rows"])
    assert all(row["model_revision"] == "test" for row in result["rows"])
    assert result["summary"]["by_protocol"][matched.RAW_PROTOCOL]["action_diversity_valid"] == 1


def test_matched_experiment_is_deterministic_with_a_fixed_seed():
    first = matched.run_matched_history_experiment(_Extractor(), seed=3, protocol="raw")
    second = matched.run_matched_history_experiment(_Extractor(), seed=3, protocol="raw")
    assert first == second
    assert {row["protocol"] for row in first["rows"]} == {matched.RAW_PROTOCOL}
