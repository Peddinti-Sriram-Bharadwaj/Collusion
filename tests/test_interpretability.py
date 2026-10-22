from hashlib import sha256
from types import SimpleNamespace

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.experiment_config import NeutralSmokeConfig, balanced_persona_design
from src.interpretability.representation_dataset import (
    DecisionMetadata,
    aligned_record,
    persona_prompt_hash,
    validate_activation_alignment,
)
from src.interpretability.neutral_pipeline import capture_neutral_decision_context
from src.env import LogitBertrandEnv


class _FakeTokenizer:
    def __call__(self, prompt, return_tensors):
        assert return_tensors == "pt"
        return {"input_ids": torch.tensor([[11, 12, 13, 14]]), "attention_mask": torch.tensor([[1, 1, 1, 1]])}


class _FakeModel:
    device = None

    def __call__(self, input_ids, attention_mask, output_hidden_states, use_cache):
        assert output_hidden_states is True
        assert use_cache is False
        # Embedding output + 28 transformer-layer outputs, hidden width 6.
        states = tuple(torch.full((1, 4, 6), float(index)) for index in range(29))
        return SimpleNamespace(hidden_states=states)


def _metadata(token_count=4, persona=None):
    return DecisionMetadata(
        episode_id="neutral-smoke-000", market_seed=7, generation_seed=7,
        agent_id=0, round_id=0, persona_id=persona,
        persona_prompt_hash=persona_prompt_hash(persona),
        full_prompt_hash=sha256(b"example").hexdigest(), prompt_token_count=token_count,
        n_agents=2, n_prices=10, n_rounds=3, agent_mode="stateless",
        model_id="mock/qwen", model_revision="test", tokenizer_revision="test",
        backend="huggingface", quantization=None, generation_parameters={"temperature": 0.0},
        warning=False, peer_info=None, fixed_agent_ids=(), veto=False, veto_margin_fraction=0.3,
    )


def test_capture_uses_final_prompt_token_and_requested_layers():
    capture = HFActivationExtractor(_FakeModel(), _FakeTokenizer(), "mock/qwen", "test").capture_final_prompt_token("prompt", [4, 14, 27])
    assert capture.prompt_token_count == 4
    assert capture.token_position == 3
    assert set(capture.layer_vectors) == {4, 14, 27}
    assert np.all(capture.layer_vectors[4] == 5.0)  # hidden-state index is layer + 1
    assert capture.layer_vectors[27].shape == (6,)


def test_alignment_accepts_exact_neutral_persona_metadata():
    capture = HFActivationExtractor(_FakeModel(), _FakeTokenizer(), "mock/qwen").capture_final_prompt_token("prompt", [4, 14, 27])
    record = aligned_record(_metadata(), capture)
    assert record["persona_id"] is None
    assert record["token_position"] == 3


def test_alignment_rejects_persona_hash_or_token_count_mismatch():
    capture = HFActivationExtractor(_FakeModel(), _FakeTokenizer(), "mock/qwen").capture_final_prompt_token("prompt", [4, 14, 27])
    with pytest.raises(ValueError, match="token count"):
        validate_activation_alignment(_metadata(token_count=3), capture)
    bad = _metadata()
    object.__setattr__(bad, "persona_prompt_hash", "not-the-real-hash")
    with pytest.raises(ValueError, match="persona_prompt_hash"):
        validate_activation_alignment(bad, capture)


def test_existing_persona_design_is_complete_and_smoke_is_neutral_only():
    design = balanced_persona_design()
    assert NeutralSmokeConfig().personas == (None, None)
    assert set(design) == {
        "neutral_default", "homog_capitalist", "homog_socialist", "homog_for_profit",
        "homog_nonprofit", "homog_rnd_oriented", "homog_consumer_empathetic", "homog_hoarder",
        "mixed_capitalist_vs_socialist", "mixed_hoarder_vs_consumer_empathetic",
    }


def test_neutral_pipeline_reuses_existing_prompt_builder_and_marks_neutral():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    extractor = HFActivationExtractor(_FakeModel(), _FakeTokenizer(), "mock/qwen", "test")
    record = capture_neutral_decision_context(
        extractor=extractor, env=env, history=[], episode_id="smoke-0",
        market_seed=12, agent_id=0, round_id=0, n_rounds=3,
    )
    assert record["persona_id"] is None
    assert record["persona_prompt_hash"] == persona_prompt_hash(None)
    assert record["prompt_token_count"] == 4
    assert record["proposed_action_index"] is None
