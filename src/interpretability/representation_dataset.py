"""Decision-level activation metadata and alignment validation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

import numpy as np

from src.llm_agent import PERSONA_TEXT
from .activation_extractor import HiddenStateCapture


def persona_prompt_hash(persona_id: str | None) -> str:
    """Hash the exact repository-defined persona insertion, including neutral."""
    if persona_id not in PERSONA_TEXT:
        raise ValueError(f"Unknown repository persona: {persona_id!r}")
    return sha256(PERSONA_TEXT[persona_id].encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DecisionMetadata:
    episode_id: str
    market_seed: int
    generation_seed: int | None
    agent_id: int
    round_id: int
    persona_id: str | None
    persona_prompt_hash: str
    full_prompt_hash: str
    prompt_token_count: int
    n_agents: int
    n_prices: int
    n_rounds: int
    agent_mode: str
    model_id: str
    model_revision: str | None
    tokenizer_revision: str | None
    backend: str
    quantization: str | None
    generation_parameters: Mapping[str, Any]
    warning: bool
    peer_info: str | None
    fixed_agent_ids: tuple[int, ...]
    veto: bool
    veto_margin_fraction: float
    proposed_action_index: int | None = None
    executed_action_index: int | None = None
    price: float | None = None
    profit: float | None = None


def aligned_record(metadata: DecisionMetadata, capture: HiddenStateCapture) -> dict[str, Any]:
    """Construct a serializable decision record after strict alignment checks."""
    validate_activation_alignment(metadata, capture)
    record = asdict(metadata)
    record["token_position"] = capture.token_position
    record["layer_vectors"] = {str(layer): vector for layer, vector in capture.layer_vectors.items()}
    return record


def validate_activation_alignment(
    metadata: DecisionMetadata,
    capture: HiddenStateCapture,
    expected_layers: Sequence[int] | None = None,
) -> None:
    """Fail fast on metadata/token/vector mismatches before writing a dataset."""
    if metadata.persona_id not in PERSONA_TEXT:
        raise ValueError(f"Unknown repository persona: {metadata.persona_id!r}")
    if metadata.persona_prompt_hash != persona_prompt_hash(metadata.persona_id):
        raise ValueError("persona_prompt_hash does not match the exact repository persona text")
    if metadata.prompt_token_count != capture.prompt_token_count:
        raise ValueError("Metadata and capture disagree on prompt token count")
    if capture.token_position != capture.prompt_token_count - 1:
        raise ValueError("Capture is not aligned to the final prompt token")
    if not capture.layer_vectors:
        raise ValueError("No layer vectors captured")
    if expected_layers is not None and set(capture.layer_vectors) != set(expected_layers):
        raise ValueError("Captured layers do not match the requested layers")
    dimensions = {np.asarray(vector).ndim for vector in capture.layer_vectors.values()}
    if dimensions != {1}:
        raise ValueError("Every layer capture must be a one-dimensional token vector")
    widths = {np.asarray(vector).shape[0] for vector in capture.layer_vectors.values()}
    if len(widths) != 1 or next(iter(widths)) < 1:
        raise ValueError("Layer vectors must have a shared, non-zero hidden dimension")
