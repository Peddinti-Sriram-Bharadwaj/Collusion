"""Opt-in representation-analysis components for LLM pricing agents.

These modules do not change the Ollama pricing path.  Hugging Face model
loading is explicit and is never triggered by importing this package.
"""

from .activation_extractor import HFActivationExtractor, HiddenStateCapture
from .representation_dataset import (
    DecisionMetadata,
    aligned_record,
    persona_prompt_hash,
    validate_activation_alignment,
)
from .neutral_pipeline import capture_neutral_decision_context
from .hf_pricing_adapter import HFPricingAgent, PricingDecision
from .hf_episode import run_hf_neutral_episode, save_hf_trajectory

__all__ = [
    "DecisionMetadata",
    "HFActivationExtractor",
    "HiddenStateCapture",
    "aligned_record",
    "persona_prompt_hash",
    "validate_activation_alignment",
    "capture_neutral_decision_context",
    "HFPricingAgent",
    "PricingDecision",
    "run_hf_neutral_episode",
    "save_hf_trajectory",
]
