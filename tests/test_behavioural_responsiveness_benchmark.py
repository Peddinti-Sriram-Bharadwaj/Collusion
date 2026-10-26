"""Mock-only checks for the uncommitted responsiveness benchmark."""
from __future__ import annotations

import numpy as np
import pytest
import torch

from scripts import run_hf_behavioural_responsiveness_benchmark as benchmark
from src.env import LogitBertrandEnv


class _Tokenizer:
    def __init__(self, response='{"price_index": 3}'):
        self.response = response

    def __call__(self, prompt, return_tensors):
        assert return_tensors == "pt"
        return {"input_ids": torch.tensor([[11, 12, 13]]), "attention_mask": torch.tensor([[1, 1, 1]])}

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize is False and add_generation_prompt is True
        return "<chat>" + messages[0]["content"]

    def decode(self, token_ids, skip_special_tokens):
        assert skip_special_tokens is True
        return self.response


class _Model:
    device = None
    hf_device_map = {"": "cuda:0"}

    def generate(self, input_ids, attention_mask, **kwargs):
        assert kwargs == {"do_sample": False, "max_new_tokens": 32, "temperature": None, "top_p": None, "top_k": None}
        return torch.cat([input_ids, torch.tensor([[99]])], dim=1)


class _Extractor:
    model_id = "mock/qwen"
    revision = "test"
    tokenizer_revision = "test"

    def __init__(self, response='{"price_index": 3}'):
        self.model = _Model()
        self.tokenizer = _Tokenizer(response)
        self.capture_final_prompt_token = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no activation extraction"))

    def _prepare_inputs(self, prompt):
        return self.tokenizer(prompt, return_tensors="pt")

    def memory_snapshot(self):
        return {"cuda_available": True, "max_allocated_bytes": 123, "max_reserved_bytes": 456}

    def close(self):
        self.closed = True


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
    assert first["rows"] == second["rows"]
    assert first["summary"] == second["summary"]
    assert first["model"] == second["model"]
    assert first["activation_extraction"] is False
    assert len(first["rows"]) == 20
    assert {row["protocol"] for row in first["rows"]} == {benchmark.RAW_PROTOCOL, benchmark.CHAT_PROTOCOL}
    assert all(row["parse_valid"] and len(row["prompt_hash"]) == 64 for row in first["rows"])
    assert all(row["model_revision"] == "test" for row in first["rows"])
    summary = first["summary"]
    assert summary["matched_protocol_pairs"] == 10
    assert summary["matched_protocol_different_action_fraction"] == 0.0
    assert summary["by_protocol"][benchmark.RAW_PROTOCOL]["action_diversity_valid"] == 1
    assert first["model"]["placement"]["shared_model_instances"] == 1
    assert first["execution"]["wall_clock_seconds"] >= 0
    assert first["execution"]["peak_cuda_memory"]["max_reserved_bytes"] == 456


def test_summary_counts_only_valid_matched_protocol_pairs():
    rows = [
        {"scenario_id": "a", "protocol": benchmark.RAW_PROTOCOL, "analysis_eligible": True, "selected_price_index": 1},
        {"scenario_id": "a", "protocol": benchmark.CHAT_PROTOCOL, "analysis_eligible": True, "selected_price_index": 2},
        {"scenario_id": "b", "protocol": benchmark.RAW_PROTOCOL, "analysis_eligible": True, "selected_price_index": 1},
        {"scenario_id": "b", "protocol": benchmark.CHAT_PROTOCOL, "analysis_eligible": False, "selected_price_index": None},
    ]
    summary = benchmark.summarise_rows(rows)
    assert summary["matched_protocol_pairs"] == 1
    assert summary["matched_protocol_different_actions"] == 1
    assert summary["matched_protocol_different_action_fraction"] == 1.0


def test_observed_instruction_echo_is_ineligible_without_a_fallback_action():
    echo = '''The output should be formatted like so:

{
  "price_index": 3
}
This problem involves understanding and applying concepts related to supply and demand curves,'''
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = benchmark.LLMPricingAgent(1, env, persona=None, seed=0)
    decision = benchmark._generate_decision(_Extractor(echo), agent, "mock prompt")
    assert decision["selected_price_index"] is None
    assert decision["analysis_eligible"] is False
    assert decision["parse_status"] == "extra_text_or_embedded_json"


def test_smoke_only_uses_exactly_one_fixed_scenario_per_protocol():
    result = benchmark.run_benchmark(_Extractor(), seed=7, protocol="both", smoke_only=True)
    assert result["smoke_only"] is True
    assert len(result["scenarios"]) == 1
    assert len(result["rows"]) == 2
    assert {row["scenario_id"] for row in result["rows"]} == {"responsiveness-000"}


def test_requested_model_revision_is_passed_once_and_unavailable_cache_fails(monkeypatch):
    calls = []

    def loader(model_id, **kwargs):
        calls.append((model_id, kwargs))
        return _Extractor()

    monkeypatch.setattr(benchmark.HFActivationExtractor, "from_pretrained", staticmethod(loader))
    extractor = benchmark.load_configured_extractor(
        model_id="Qwen/Qwen2.5-1.5B-Instruct", model_revision="pinned", local_files_only=True
    )
    assert isinstance(extractor, _Extractor)
    assert calls == [("Qwen/Qwen2.5-1.5B-Instruct", {
        "revision": "pinned", "device_map": "auto", "torch_dtype": torch.float16, "local_files_only": True,
    })]

    monkeypatch.setattr(
        benchmark.HFActivationExtractor,
        "from_pretrained",
        staticmethod(lambda *args, **kwargs: (_ for _ in ()).throw(OSError("not cached"))),
    )
    with pytest.raises(RuntimeError, match="No model or revision was substituted"):
        benchmark.load_configured_extractor(model_id="missing/model", model_revision="missing", local_files_only=True)


def test_cli_creates_one_shared_model_instance_for_a_smoke_run(monkeypatch):
    loader_calls, saved = [], []

    def loader(model_id, **kwargs):
        loader_calls.append((model_id, kwargs))
        return _Extractor()

    monkeypatch.setattr(benchmark.HFActivationExtractor, "from_pretrained", staticmethod(loader))
    monkeypatch.setattr(benchmark, "save_hf_trajectory", lambda path, result: saved.append((path, result)))
    monkeypatch.setattr(benchmark.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr("sys.argv", [
        "run_hf_behavioural_responsiveness_benchmark.py",
        "--allow-model-load", "--local-files-only", "--model-id", "mock/1.5b",
        "--model-revision", "pinned", "--protocol", "chat", "--smoke-only", "--output", "ignored.json",
    ])
    benchmark.main()
    assert len(loader_calls) == 1
    assert loader_calls[0][0] == "mock/1.5b"
    assert loader_calls[0][1]["revision"] == "pinned"
    assert loader_calls[0][1]["local_files_only"] is True
    assert saved[0][1]["model"]["placement"]["shared_model_instances"] == 1
    assert saved[0][1]["execution"]["model_load_wall_clock_seconds"] >= 0
    assert len(saved[0][1]["rows"]) == 1
