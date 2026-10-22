"""Hugging Face hidden-state capture, isolated from the Ollama agent path."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class HiddenStateCapture:
    """Residual-stream vectors for one prompt before any output is generated."""

    prompt_token_count: int
    token_position: int
    layer_vectors: Mapping[int, np.ndarray]


class HFActivationExtractor:
    """Capture selected final-prompt-token hidden states from a causal LM.

    The class accepts already-constructed model/tokenizer objects to make it
    testable without downloads.  ``from_pretrained`` is intentionally an
    explicit operation so importing or configuring an experiment cannot load
    model weights.
    """

    def __init__(self, model: Any, tokenizer: Any, model_id: str, revision: str | None = None):
        self.model = model
        self.tokenizer = tokenizer
        self.model_id = model_id
        self.revision = revision

    @classmethod
    def from_pretrained(
        cls,
        model_id: str,
        *,
        revision: str | None = None,
        device_map: str | Mapping[str, Any] | None = "auto",
        torch_dtype: Any | None = None,
        load_in_4bit: bool = False,
    ) -> "HFActivationExtractor":
        """Load a model only when a caller explicitly requests it.

        ``load_in_4bit`` requires a compatible quantization installation and
        does not make representations comparable to another quantization by
        itself; callers must record the complete backend configuration.
        """
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("Install transformers to load a Hugging Face activation backend.") from exc

        model_kwargs: dict[str, Any] = {"revision": revision, "device_map": device_map}
        if torch_dtype is not None:
            model_kwargs["torch_dtype"] = torch_dtype
        if load_in_4bit:
            model_kwargs["load_in_4bit"] = True
        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
        model.eval()
        return cls(model=model, tokenizer=tokenizer, model_id=model_id, revision=revision)

    def capture_final_prompt_token(self, prompt: str, layers: Sequence[int]) -> HiddenStateCapture:
        """Run one prompt forward and retain selected layers at its last token.

        This deliberately captures *pre-generation* context.  Generated-token
        activations encode JSON formatting and token sampling and must be
        collected under a distinct schema if later required.
        """
        if not layers:
            raise ValueError("At least one layer must be selected.")
        try:
            import torch
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("PyTorch is required for activation capture.") from exc

        encoded = self.tokenizer(prompt, return_tensors="pt")
        device = getattr(self.model, "device", None)
        if device is not None and hasattr(encoded, "to"):
            encoded = encoded.to(device)
        elif device is not None:
            encoded = {key: value.to(device) if hasattr(value, "to") else value for key, value in encoded.items()}

        attention_mask = encoded.get("attention_mask")
        if attention_mask is None:
            prompt_token_count = int(encoded["input_ids"].shape[-1])
        else:
            prompt_token_count = int(attention_mask[0].sum().item())
        if prompt_token_count < 1:
            raise ValueError("Prompt tokenization produced no tokens.")
        token_position = prompt_token_count - 1

        with torch.inference_mode():
            output = self.model(**encoded, output_hidden_states=True, use_cache=False)
        hidden_states = output.hidden_states
        # Transformers exposes index 0 for embeddings, then layer 0 at index 1.
        max_layer = len(hidden_states) - 2
        vectors: dict[int, np.ndarray] = {}
        for layer in layers:
            if layer < 0 or layer > max_layer:
                raise ValueError(f"Layer {layer} is unavailable; valid transformer layers are 0..{max_layer}.")
            vector = hidden_states[layer + 1][0, token_position].detach().float().cpu().numpy().copy()
            vectors[int(layer)] = vector
        return HiddenStateCapture(prompt_token_count, token_position, vectors)
