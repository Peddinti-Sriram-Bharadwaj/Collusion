"""Mock-only checks for the uncommitted responsiveness benchmark."""
from __future__ import annotations

import numpy as np
import torch

from scripts import run_hf_behavioural_responsiveness_benchmark as benchmark
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
        return '{"price_index": 3}'


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


def test_market_scenarios_are_reproducible_and_replay_through_environment():
    first = benchmark.generate_market_scenarios(seed=17)
    second = benchmark.generate_market_scenarios(seed=17)
    assert first == second
    assert {len(s.action_indices) for s in first} == {1, 2, 4, 8}
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    for scenario in first:
        history = benchmark.materialize_history(env, scenario)
        assert len(history) == len(scenario.action_indices)
        for actions, (prices, profits) in zip(scenario.action_indices, history):
            assert np.array_equal(prices, env.price_grid[np.asarray(actions)])
            assert np.allclose(profits, env._profits(prices))


def test_benchmark_records_protocol_configuration_hashes_and_is_deterministic(monkeypatch):
    monkeypatch.setattr(benchmark.HFActivationExtractor, "from_pretrained", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no model download")))
    first = benchmark.run_benchmark(_Extractor(), seed=2, protocol="both")
    second = benchmark.run_benchmark(_Extractor(), seed=2, protocol="both")
    assert first == second
    assert first["activation_extraction"] is False
    assert len(first["rows"]) == 20
    assert {row["protocol"] for row in first["rows"]} == {benchmark.RAW_PROTOCOL, benchmark.CHAT_PROTOCOL}
    assert all(row["parse_valid"] and len(row["prompt_hash"]) == 64 for row in first["rows"])
    assert all(row["model_revision"] == "test" for row in first["rows"])
    summary = first["summary"]
    assert summary["matched_protocol_pairs"] == 10
    assert summary["matched_protocol_different_action_fraction"] == 0.0
    assert summary["by_protocol"][benchmark.RAW_PROTOCOL]["action_diversity_valid"] == 1


def test_summary_counts_only_valid_matched_protocol_pairs():
    rows = [
        {"scenario_id": "a", "protocol": benchmark.RAW_PROTOCOL, "parse_valid": True, "selected_price_index": 1},
        {"scenario_id": "a", "protocol": benchmark.CHAT_PROTOCOL, "parse_valid": True, "selected_price_index": 2},
        {"scenario_id": "b", "protocol": benchmark.RAW_PROTOCOL, "parse_valid": True, "selected_price_index": 1},
        {"scenario_id": "b", "protocol": benchmark.CHAT_PROTOCOL, "parse_valid": False, "selected_price_index": 9},
    ]
    summary = benchmark.summarise_rows(rows)
    assert summary["matched_protocol_pairs"] == 1
    assert summary["matched_protocol_different_actions"] == 1
    assert summary["matched_protocol_different_action_fraction"] == 1.0
