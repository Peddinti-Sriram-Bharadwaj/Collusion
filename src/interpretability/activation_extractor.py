"""Hugging Face hidden-state capture, isolated from the Ollama agent path."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import gc
from typing import Any, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class HiddenStateCapture:
    """Residual-stream vectors for one prompt before any output is generated."""

    prompt_token_count: int
    token_position: int
    input_token_ids_hash: str
    layer_vectors: Mapping[int, np.ndarray]


class HFActivationExtractor:
    """Capture selected final-prompt-token hidden states from a causal LM.

    The class accepts already-constructed model/tokenizer objects to make it
    testable without downloads.  ``from_pretrained`` is intentionally an
    explicit operation so importing or configuring an experiment cannot load
    model weights.
    """

    def __init__(self, model: Any, tokenizer: Any, model_id: str, revision: str | None = None, tokenizer_revision: str | None = None):
        if revision is not None and tokenizer_revision is not None and revision != tokenizer_revision:
            raise ValueError("Model and tokenizer revisions must match for an activation run.")
        self.model = model
        self.tokenizer = tokenizer
        self.model_id = model_id
        self.revision = revision
        self.tokenizer_revision = tokenizer_revision or revision

    @classmethod
    def from_pretrained(
        cls,
        model_id: str,
        *,
        revision: str | None = None,
        device_map: str | Mapping[str, Any] | None = "auto",
        torch_dtype: Any | None = None,
        load_in_4bit: bool = False,
        local_files_only: bool = False,
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

        model_kwargs: dict[str, Any] = {
            "revision": revision,
            "device_map": device_map,
            "local_files_only": local_files_only,
        }
        if torch_dtype is not None:
            model_kwargs["torch_dtype"] = torch_dtype
        if load_in_4bit:
            model_kwargs["load_in_4bit"] = True
        tokenizer = AutoTokenizer.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only,
        )
        model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
        model.eval()
        return cls(model=model, tokenizer=tokenizer, model_id=model_id, revision=revision, tokenizer_revision=revision)

    def memory_snapshot(self) -> dict[str, int | bool]:
        """Report CUDA allocator state without allocating or loading anything."""
        try:
            import torch
        except ImportError:  # pragma: no cover
            return {"cuda_available": False}
        if not torch.cuda.is_available():
            return {"cuda_available": False}
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        return {
            "cuda_available": True,
            "allocated_bytes": int(torch.cuda.memory_allocated()),
            "reserved_bytes": int(torch.cuda.memory_reserved()),
            "max_allocated_bytes": int(torch.cuda.max_memory_allocated()),
            "free_bytes": int(free_bytes),
            "total_bytes": int(total_bytes),
        }

    def close(self) -> None:
        """Release this adapter's model reference and return cached CUDA memory."""
        model = getattr(self, "model", None)
        if model is not None and hasattr(model, "to"):
            model.to("cpu")
        self.model = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:  # pragma: no cover
            pass

    def _prepare_inputs(self, prompt: str):
        """Tokenize once so capture and generation share identical input IDs."""
        if self.model is None:
            raise RuntimeError("Activation extractor is closed.")
        encoded = self.tokenizer(prompt, return_tensors="pt")
        device = getattr(self.model, "device", None)
        if device is not None and hasattr(encoded, "to"):
            return encoded.to(device)
        if device is not None:
            return {key: value.to(device) if hasattr(value, "to") else value for key, value in encoded.items()}
        return encoded

    def _capture_from_inputs(self, encoded: Mapping[str, Any], layers: Sequence[int]) -> HiddenStateCapture:
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

        attention_mask = encoded.get("attention_mask")
        if attention_mask is None:
            prompt_token_count = int(encoded["input_ids"].shape[-1])
        else:
            non_padding_positions = attention_mask[0].nonzero(as_tuple=False).flatten()
            prompt_token_count = int(non_padding_positions.numel())
        if prompt_token_count < 1:
            raise ValueError("Prompt tokenization produced no tokens.")
        token_position = prompt_token_count - 1 if attention_mask is None else int(non_padding_positions[-1].item())

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
        token_ids = encoded["input_ids"].detach().cpu().numpy().tobytes()
        del output, hidden_states
        return HiddenStateCapture(prompt_token_count, token_position, sha256(token_ids).hexdigest(), vectors)

    def capture_final_prompt_token(self, prompt: str, layers: Sequence[int]) -> HiddenStateCapture:
        """Run one prompt forward and retain selected layers at its last token."""
        return self._capture_from_inputs(self._prepare_inputs(prompt), layers)

    def generate_with_capture(
        self,
        prompt: str,
        layers: Sequence[int],
        generation_parameters: Mapping[str, Any],
    ) -> tuple[HiddenStateCapture, str]:
        """Capture prompt states then generate from the same tokenized context.

        The prefill pass is intentionally separate from generation so only the
        final prompt token is stored.  Both operations use the same model
        object, encoded input IDs, and supplied generation settings.
        """
        try:
            import torch
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("PyTorch is required for activation capture.") from exc
        encoded = self._prepare_inputs(prompt)
        capture = self._capture_from_inputs(encoded, layers)
        prompt_width = int(encoded["input_ids"].shape[-1])
        with torch.inference_mode():
            sequence = self.model.generate(**encoded, **dict(generation_parameters))
        generated_ids = sequence[0, prompt_width:]
        text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        del sequence, generated_ids, encoded
        return capture, text
