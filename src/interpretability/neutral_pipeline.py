"""Neutral, one-decision activation collection wired to existing prompt logic.

This deliberately does not generate a price or invoke Ollama.  A caller must
provide an explicitly loaded Hugging Face extractor, making model loading and
any expensive inference an opt-in action.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Sequence

from src.env import LogitBertrandEnv
from src.llm_agent import LLMPricingAgent

from .activation_extractor import HFActivationExtractor
from .representation_dataset import DecisionMetadata, aligned_record, persona_prompt_hash


def capture_neutral_decision_context(
    *,
    extractor: HFActivationExtractor,
    env: LogitBertrandEnv,
    history: list[tuple],
    episode_id: str,
    market_seed: int,
    agent_id: int,
    round_id: int,
    n_rounds: int,
    selected_layers: Sequence[int] | None = None,
    generation_seed: int | None = None,
    quantization: str | None = None,
) -> dict:
    """Build the repository's neutral prompt and align its hidden states.

    This is the approved smoke-test path: its persona is fixed to ``None``.
    It returns a record before any action is generated, so action/profit fields
    remain null until a later, explicitly approved execution adapter exists.
    """
    agent = LLMPricingAgent(agent_id=agent_id, env=env, persona=None, seed=market_seed + agent_id)
    prompt = agent._build_prompt(history, round_id, n_rounds)
    n_layers = getattr(getattr(extractor.model, "config", None), "num_hidden_layers", None)
    if selected_layers is None:
        if not isinstance(n_layers, int) or n_layers < 1:
            raise ValueError("Specify selected_layers when the model lacks num_hidden_layers.")
        selected_layers = tuple(sorted({max(0, n_layers // 6), n_layers // 2, n_layers - 1}))
    capture = extractor.capture_final_prompt_token(prompt, selected_layers)
    metadata = DecisionMetadata(
        episode_id=episode_id,
        market_seed=market_seed,
        generation_seed=generation_seed,
        agent_id=agent_id,
        round_id=round_id,
        persona_id=None,
        persona_prompt_hash=persona_prompt_hash(None),
        full_prompt_hash=sha256(prompt.encode("utf-8")).hexdigest(),
        input_token_ids_hash=capture.input_token_ids_hash,
        prompt_token_count=capture.prompt_token_count,
        n_agents=env.n_agents,
        n_prices=env.n_prices,
        n_rounds=n_rounds,
        agent_mode="stateless", prompt_format="raw_repository_stateless_v1",
        model_id=extractor.model_id,
        model_revision=extractor.revision,
        tokenizer_revision=extractor.tokenizer_revision,
        backend="huggingface",
        quantization=quantization,
        generation_parameters={},
        warning=False,
        peer_info=None,
        fixed_agent_ids=(),
        veto=False,
        veto_margin_fraction=0.3,
    )
    return aligned_record(metadata, capture)
