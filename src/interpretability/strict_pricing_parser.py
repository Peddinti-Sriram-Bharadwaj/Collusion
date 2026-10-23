"""Strict, HF-only parsing for standalone pricing decisions.

This module is deliberately separate from ``src.llm_agent``: historical
Ollama experiments retain their original permissive parser and fallback
behaviour.  HF research measurements instead need to distinguish a decision
from an echoed instruction or an explanatory continuation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


@dataclass(frozen=True)
class StrictPricingParse:
    """Result of parsing one generated response without any fallback action."""

    selected_price_index: int | None
    analysis_eligible: bool
    parse_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_strict_price_response(response: str, n_prices: int) -> StrictPricingParse:
    """Accept only ``{"price_index": integer}`` and no surrounding text.

    ``json.JSONDecoder.raw_decode`` lets us distinguish malformed JSON from a
    valid object embedded in prose or followed by another object.  A rejected
    response intentionally has no selected action: HF measurement scripts must
    never silently replace it with a random fallback.
    """
    if n_prices < 1:
        raise ValueError("n_prices must be positive.")
    if not isinstance(response, str):
        return StrictPricingParse(None, False, "non_string_response")
    text = response.strip()
    if not text:
        return StrictPricingParse(None, False, "empty_response")
    if text.startswith("```"):
        return StrictPricingParse(None, False, "code_fence_or_markdown")

    decoder = json.JSONDecoder()
    try:
        value, end = decoder.raw_decode(text)
    except json.JSONDecodeError:
        # A JSON object occurring after non-JSON prose is precisely the common
        # instruction-echo failure mode; it is still invalid as a decision.
        return StrictPricingParse(
            None,
            False,
            "malformed_json" if text.startswith("{") else (
                "extra_text_or_embedded_json" if "{" in text else "malformed_json"
            ),
        )

    trailing = text[end:].strip()
    if trailing:
        return StrictPricingParse(
            None,
            False,
            "multiple_json_objects" if trailing.startswith("{") else "extra_text_after_json",
        )
    if not isinstance(value, dict):
        return StrictPricingParse(None, False, "wrong_json_type")
    if set(value) != {"price_index"}:
        return StrictPricingParse(None, False, "wrong_json_schema")
    index = value["price_index"]
    if isinstance(index, bool) or not isinstance(index, int):
        return StrictPricingParse(None, False, "non_integer_price_index")
    if not 0 <= index < n_prices:
        return StrictPricingParse(None, False, "out_of_range_price_index")
    return StrictPricingParse(index, True, "standalone_json")
