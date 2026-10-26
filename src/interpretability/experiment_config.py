"""Explicit, non-executing configurations for latent-manifold experiments."""
from __future__ import annotations

from dataclasses import dataclass

from src.llm_agent import PERSONA_TEXT


REPOSITORY_PERSONAS = tuple(PERSONA_TEXT.keys())
HOMOGENEOUS_PERSONAS = tuple(persona for persona in REPOSITORY_PERSONAS if persona is not None)
MIXED_PERSONA_CONDITIONS = {
    "mixed_capitalist_vs_socialist": ("capitalist", "socialist"),
    "mixed_hoarder_vs_consumer_empathetic": ("hoarder", "consumer_empathetic"),
}


@dataclass(frozen=True)
class NeutralSmokeConfig:
    """The only approved collection configuration before a model-load approval."""

    personas: tuple[None, None] = (None, None)
    n_agents: int = 2
    n_prices: int = 10
    n_rounds: int = 3
    agent_mode: str = "stateless"
    selected_layers: tuple[int, int, int] = (4, 14, 27)


def balanced_persona_design() -> dict[str, tuple[str | None, str | None]]:
    """Return existing neutral, homogeneous, and mixed conditions without running them."""
    design: dict[str, tuple[str | None, str | None]] = {"neutral_default": (None, None)}
    design.update({f"homog_{persona}": (persona, persona) for persona in HOMOGENEOUS_PERSONAS})
    design.update(MIXED_PERSONA_CONDITIONS)
    return design
