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
from .competitor_intervention import (
    run_paired_competitor_price_intervention,
    save_paired_competitor_intervention,
)
from .matched_prompt_counterfactual import (
    derive_matched_prompt_conditions,
    load_agent1_round3_context,
    run_matched_prompt_counterfactuals,
    save_matched_prompt_counterfactuals,
)

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
    "run_paired_competitor_price_intervention",
    "save_paired_competitor_intervention",
    "derive_matched_prompt_conditions",
    "load_agent1_round3_context",
    "run_matched_prompt_counterfactuals",
    "save_matched_prompt_counterfactuals",
]
