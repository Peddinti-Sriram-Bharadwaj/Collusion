"""Opt-in Hugging Face pricing adapter; Ollama agents remain untouched."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any, Sequence

import numpy as np

from src.env import LogitBertrandEnv
from src.llm_agent import LLMPricingAgent

from .activation_extractor import HFActivationExtractor
from .representation_dataset import DecisionMetadata, aligned_record, persona_prompt_hash


@dataclass(frozen=True)
class PricingDecision:
    action_index: int
    parse_failed: bool
    raw_text: str | None
    activation_record: dict[str, Any] | None
    error: str | None = None


def representative_layers(extractor: HFActivationExtractor) -> tuple[int, ...]:
    """Select early/middle/late layers from the loaded model configuration."""
    n_layers = getattr(getattr(extractor.model, "config", None), "num_hidden_layers", None)
    if not isinstance(n_layers, int) or n_layers < 1:
        raise ValueError("Model config must expose a positive num_hidden_layers; pass layers explicitly otherwise.")
    return tuple(sorted({max(0, n_layers // 6), n_layers // 2, n_layers - 1}))


class HFPricingAgent:
    """Stateless pricing agent sharing the repository's prompt and parser."""

    def __init__(
        self,
        agent_id: int,
        env: LogitBertrandEnv,
        extractor: HFActivationExtractor,
        *,
        persona: None = None,
        seed: int = 0,
        selected_layers: Sequence[int] | None = None,
        generation_parameters: dict[str, Any] | None = None,
        quantization: str | None = None,
    ):
        if persona is not None:
            raise ValueError("The pilot adapter is intentionally neutral-only: persona must be None.")
        self.agent_id = agent_id
        self.env = env
        self.extractor = extractor
        self.selected_layers = tuple(selected_layers or representative_layers(extractor))
        self.generation_parameters = generation_parameters or {"do_sample": False, "max_new_tokens": 32}
        self.quantization = quantization
        self.rng = np.random.default_rng(seed)
        # Reuse source-of-truth prompt construction and response parsing.
        self._prompt_agent = LLMPricingAgent(agent_id, env, persona=None, seed=seed)

    def act(
        self,
        history: list[tuple],
        round_num: int,
        n_rounds: int,
        *,
        episode_id: str,
        market_seed: int,
        generation_seed: int | None = None,
    ) -> PricingDecision:
        prompt = self._prompt_agent._build_prompt(history, round_num, n_rounds)
        try:
            capture, text = self.extractor.generate_with_capture(prompt, self.selected_layers, self.generation_parameters)
            idx = self._prompt_agent._parse_index(text)
            match = re.search(r'"price_index"\s*:\s*(\d+)', text)
            parse_failed = match is None or not (0 <= int(match.group(1)) < self.env.n_prices)
            metadata = DecisionMetadata(
                episode_id=episode_id, market_seed=market_seed, generation_seed=generation_seed,
                agent_id=self.agent_id, round_id=round_num, persona_id=None,
                persona_prompt_hash=persona_prompt_hash(None),
                full_prompt_hash=sha256(prompt.encode("utf-8")).hexdigest(),
                input_token_ids_hash=capture.input_token_ids_hash,
                prompt_token_count=capture.prompt_token_count, n_agents=self.env.n_agents,
                n_prices=self.env.n_prices, n_rounds=n_rounds, agent_mode="stateless",
                prompt_format="raw_repository_stateless_v1",
                model_id=self.extractor.model_id, model_revision=self.extractor.revision,
                tokenizer_revision=self.extractor.tokenizer_revision, backend="huggingface",
                quantization=self.quantization, generation_parameters=self.generation_parameters,
                warning=False, peer_info=None, fixed_agent_ids=(), veto=False,
                veto_margin_fraction=0.3,
                proposed_action_index=None if parse_failed else idx, executed_action_index=idx,
            )
            record = aligned_record(metadata, capture)
            record["raw_response"] = text
            record["parse_failed"] = parse_failed
            record["eligible_for_analysis"] = not parse_failed
            record["decision_status"] = "valid" if not parse_failed else "invalid_parse"
            return PricingDecision(idx, parse_failed, text, record)
        except Exception as exc:
            return PricingDecision(int(self.rng.integers(0, self.env.n_prices)), True, None, None, str(exc))
