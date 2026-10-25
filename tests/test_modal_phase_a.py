"""Mock-only tests for the pure Modal Phase A design; no Modal import/GPU."""
from __future__ import annotations

import torch

from src.env import LogitBertrandEnv
from src.interpretability import modal_phase_a as phase_a


class Tokenizer:
    init_kwargs = {"_commit_hash": "pin"}
    def __init__(self, response='{"price_index": 4}'):
        self.response = response
    def __call__(self, prompt, return_tensors):
        return {"input_ids": torch.tensor([[3, 4, 5]]), "attention_mask": torch.tensor([[1, 1, 1]])}
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize is False and add_generation_prompt is True
        return "<chat>" + messages[0]["content"]
    def decode(self, ids, skip_special_tokens):
        return self.response


class Model:
    device = None
    hf_device_map = {"": "cuda:0"}
    class config:
        _commit_hash = "pin"
    def generate(self, input_ids, attention_mask, **kwargs):
        assert kwargs == phase_a.GENERATION_KWARGS
        return torch.cat([input_ids, torch.tensor([[99]])], dim=1)


class Extractor:
    model_id = phase_a.PHASE_A_MODEL_ID
    revision = phase_a.PHASE_A_MODEL_REVISION
    tokenizer_revision = phase_a.PHASE_A_MODEL_REVISION
    def __init__(self, response='{"price_index": 4}'):
        self.model, self.tokenizer = Model(), Tokenizer(response)
    def _prepare_inputs(self, prompt):
        return self.tokenizer(prompt, return_tensors="pt")
    def memory_snapshot(self):
        return {"cuda_available": True, "max_allocated_bytes": 42}


def test_design_has_exactly_24_pairs_and_48_controlled_evaluations():
    pairs = phase_a.generate_phase_a_pairs(10)
    assert phase_a.validate_phase_a_design(pairs) == {
        "n_pairs": 24, "displayed_rival_price_decreases": 12, "displayed_rival_price_increases": 12,
    }
    assert len(pairs) == 24
    assert len({pair.pair_id for pair in pairs}) == 24
    assert len({pair.action_indices for pair in pairs}) == 24
    assert all(len(pair.action_indices) == 4 for pair in pairs)
    assert {pair.displayed_rival_final_index for pair in pairs} == {0, 9}
    assert {pair.own_price_index for pair in pairs} == {2, 5, 8}


def test_control_is_legal_and_synthetic_changes_only_final_rival_display():
    env, pair = LogitBertrandEnv(n_agents=2, n_prices=10), phase_a.generate_phase_a_pairs()[0]
    control = phase_a.materialize_control_history(env, pair)
    synthetic = phase_a._modified_display_history(control, float(env.price_grid[pair.displayed_rival_final_index]))
    for actions, (prices, profits) in zip(pair.action_indices, control):
        assert prices.tolist() == env.price_grid[list(actions)].tolist()
        assert profits.tolist() == env._profits(prices).tolist()
    assert control[:-1][0][0].tolist() == synthetic[:-1][0][0].tolist()
    assert control[-1][0][1] == synthetic[-1][0][1]
    assert control[-1][1].tolist() == synthetic[-1][1].tolist()
    assert control[-1][0][0] != synthetic[-1][0][0]


def test_smoke_is_one_complete_pair_plus_negative_control_and_records_metadata():
    result = phase_a.run_phase_a(Extractor(), seed=3, smoke_only=True)
    assert result["execution"]["status"] == "completed"
    assert len(result["rows"]) == 3
    assert {row["condition"] for row in result["rows"]} == {
        "control_realistic", "synthetic_rival_price_only", "negative_control_audit_nonce",
    }
    assert all(row["analysis_eligible"] and row["protocol"] == phase_a.PHASE_A_PROTOCOL for row in result["rows"])
    assert all(len(row["prompt_hash"]) == 64 and row["prompt_token_count"] == 3 for row in result["rows"])
    assert result["model"]["shared_model_instances"] == 1
    assert result["execution"]["peak_cuda_memory"]["max_allocated_bytes"] == 42


def test_matched_prompts_differ_only_in_the_declared_rival_or_audit_field():
    rows = phase_a.run_phase_a(Extractor(), smoke_only=True)["rows"]
    by_condition = {row["condition"]: row for row in rows}
    control = by_condition["control_realistic"]
    synthetic = by_condition["synthetic_rival_price_only"]
    negative = by_condition["negative_control_audit_nonce"]
    assert control["audit_nonce"] == synthetic["audit_nonce"] == phase_a.CONTROL_AUDIT_NONCE
    assert control["history"][:-1] == synthetic["history"][:-1]
    assert control["history"][-1]["profits"] == synthetic["history"][-1]["profits"]
    assert control["history"][-1]["prices"][1] == synthetic["history"][-1]["prices"][1]
    line_changes = [
        (left, right) for left, right in zip(control["raw_prompt"].splitlines(), synthetic["raw_prompt"].splitlines())
        if left != right
    ]
    assert len(line_changes) == 1
    control_line, synthetic_line = line_changes[0]
    prefix = "rival price(s): "
    assert control_line.split(prefix)[0] == synthetic_line.split(prefix)[0]
    assert control_line.startswith("Round 3:") and synthetic_line.startswith("Round 3:")
    assert control_line.split(prefix)[1] != synthetic_line.split(prefix)[1]
    # The nonce is the complete negative-control change in both raw and templated prompts.
    assert control["raw_prompt"].replace(str(phase_a.CONTROL_AUDIT_NONCE), str(phase_a.NEGATIVE_CONTROL_AUDIT_NONCE)) == negative["raw_prompt"]
    assert control["model_prompt"].replace(str(phase_a.CONTROL_AUDIT_NONCE), str(phase_a.NEGATIVE_CONTROL_AUDIT_NONCE)) == negative["model_prompt"]
    assert negative["intervention_label"] == "negative_control_audit_nonce_only"


def test_full_mock_run_preserves_24_pairs_48_core_rows_plus_one_negative_control():
    result = phase_a.run_phase_a(Extractor())
    assert result["design_checks"]["displayed_rival_price_decreases"] == 12
    assert result["design_checks"]["displayed_rival_price_increases"] == 12
    assert len(result["rows"]) == 49
    assert result["summary"]["n_pairs"] == 24
    assert result["summary"]["n_valid_pairs"] == 24


def test_pinned_loader_and_local_artifact_contract(tmp_path):
    kwargs = phase_a.phase_a_loader_kwargs()
    assert kwargs["model_id"] == phase_a.PHASE_A_MODEL_ID
    assert kwargs["revision"] == phase_a.PHASE_A_MODEL_REVISION
    assert kwargs["cache_dir"] == phase_a.MODAL_HF_CACHE_PATH
    assert kwargs["local_files_only"] is False
    result = {"schema_version": "test", "rows": []}
    destination = phase_a.save_phase_a_artifact(tmp_path / "result.json", result)
    assert destination.exists()
    assert destination.read_text(encoding="utf-8").startswith("{")


def test_remote_loading_failure_has_a_serialisable_local_artifact_contract():
    result = phase_a.phase_a_remote_failure_artifact(RuntimeError("mock load failure"), 1.25)
    assert result["execution"]["status"] == "failed"
    assert "mock load failure" in result["execution"]["error"]
    assert result["rows"] == []
    assert result["model"]["requested_model_revision"] == phase_a.PHASE_A_MODEL_REVISION


def test_invalid_response_has_no_action_and_summary_excludes_pair():
    result = phase_a.run_phase_a(Extractor("explained {\"price_index\": 4}"), smoke_only=True)
    assert all(row["selected_price_index"] is None and not row["analysis_eligible"] for row in result["rows"])
    assert result["summary"]["n_valid_pairs"] == 0


def test_failed_generation_is_recorded_without_requiring_modal_or_a_gpu():
    class FailingModel(Model):
        def generate(self, *args, **kwargs):
            raise RuntimeError("mock generation failure")
    extractor = Extractor()
    extractor.model = FailingModel()
    result = phase_a.run_phase_a(extractor, smoke_only=True)
    assert result["execution"]["status"] == "failed"
    assert "mock generation failure" in result["execution"]["error"]
    assert result["rows"] == []
