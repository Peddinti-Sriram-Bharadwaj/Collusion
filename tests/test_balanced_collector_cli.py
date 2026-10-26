"""Mock-only persistence tests for the guarded balanced collector CLI."""
from __future__ import annotations

import pytest

from scripts import collect_hf_balanced_counterfactual_dataset as collector_cli


class _StubExtractor:
    model_id = "mock/qwen"
    revision = "test"
    tokenizer_revision = "test"

    def memory_snapshot(self):
        return {
            "cuda_available": True,
            "allocated_bytes": 10,
            "reserved_bytes": 20,
            "max_allocated_bytes": 30,
            "max_reserved_bytes": 40,
        }


def test_balanced_collector_persists_runtime_cuda_memory_and_failures(monkeypatch):
    captured = []
    monkeypatch.setattr(
        collector_cli,
        "save_hf_trajectory",
        lambda path, result: captured.append((path, result)),
    )
    monkeypatch.setattr(collector_cli, "generate_balanced_scenarios", lambda count, seed: ["scenario"])
    monkeypatch.setattr(
        collector_cli,
        "collect_balanced_counterfactual_dataset",
        lambda extractor, scenarios, selected_layers: {"schema_version": "test", "rows": []},
    )

    result = collector_cli.run_and_persist_balanced_collection(
        _StubExtractor(), output="ok.json", scenarios=12, seed=4, selected_layers=[4, 12, 23]
    )
    assert result["execution"]["status"] == "completed"
    assert result["execution"]["wall_clock_seconds"] >= 0
    assert result["execution"]["memory_before_release"]["max_reserved_bytes"] == 40
    assert captured[-1][1]["execution"]["error_type"] is None

    monkeypatch.setattr(
        collector_cli,
        "collect_balanced_counterfactual_dataset",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("mock failure")),
    )
    with pytest.raises(RuntimeError, match="mock failure"):
        collector_cli.run_and_persist_balanced_collection(
            _StubExtractor(), output="failed.json", scenarios=12, seed=4, selected_layers=None
        )
    assert captured[-1][1]["execution"]["status"] == "failed"
    assert captured[-1][1]["execution"]["error_type"] == "RuntimeError"

    monkeypatch.setattr(
        collector_cli,
        "collect_balanced_counterfactual_dataset",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(KeyboardInterrupt):
        collector_cli.run_and_persist_balanced_collection(
            _StubExtractor(), output="interrupted.json", scenarios=12, seed=4, selected_layers=None
        )
    assert captured[-1][1]["execution"]["status"] == "interrupted"
    assert captured[-1][1]["execution"]["error_type"] == "KeyboardInterrupt"
