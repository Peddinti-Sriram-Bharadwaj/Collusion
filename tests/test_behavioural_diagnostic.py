"""Mock-only tests for the local behavioural diagnostic (intentionally unstaged)."""
from __future__ import annotations

from types import SimpleNamespace

import torch

from scripts import run_hf_behavioral_diagnostic as diagnostic


class _Tokenizer:
    def __init__(self, response='{"price_index": 3}'):
        self.response = response

    def __call__(self, prompt, return_tensors):
        assert return_tensors == "pt"
        return {"input_ids": torch.tensor([[11, 12, 13]]), "attention_mask": torch.tensor([[1, 1, 1]])}

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize is False and add_generation_prompt is True
        return "<chat>" + messages[0]["content"]

    def decode(self, tokens, skip_special_tokens):
        assert skip_special_tokens is True
        return self.response


class _Model:
    device = None

    def generate(self, input_ids, attention_mask, **kwargs):
        assert kwargs == {"do_sample": False, "max_new_tokens": 32, "temperature": None, "top_p": None, "top_k": None}
        return torch.cat([input_ids, torch.tensor([[99]])], dim=1)


class _Extractor:
    model_id = "mock/qwen"
    revision = "test"
    tokenizer_revision = "test"

    def __init__(self, response='{"price_index": 3}'):
        self.model = _Model()
        self.tokenizer = _Tokenizer(response)
        self.capture_final_prompt_token = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("activation capture must not run"))

    def _prepare_inputs(self, prompt):
        return self.tokenizer(prompt, return_tensors="pt")


def test_raw_and_chat_protocols_record_distinct_hashes_without_activation_capture(monkeypatch):
    monkeypatch.setattr(diagnostic.HFActivationExtractor, "from_pretrained", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no download")))
    result = diagnostic.run_diagnostic(_Extractor(), protocol="both")
    assert result["activation_extraction"] is False
    assert result["deterministic_generation"] is True
    assert len(result["rows"]) == 8
    raw = [row for row in result["rows"] if row["protocol"] == diagnostic.RAW_PROTOCOL]
    chat = [row for row in result["rows"] if row["protocol"] == diagnostic.CHAT_PROTOCOL]
    assert len(raw) == len(chat) == 4
    assert all(len(row["prompt_hash"]) == 64 and row["parse_valid"] for row in result["rows"])
    assert all(chat_row["prompt"].startswith("<chat>") for chat_row in chat)
    assert {row["prompt_hash"] for row in raw}.isdisjoint({row["prompt_hash"] for row in chat})


def test_protocol_selection_invalid_responses_and_determinism():
    valid = diagnostic.run_diagnostic(_Extractor(), protocol="raw")
    repeat = diagnostic.run_diagnostic(_Extractor(), protocol="raw")
    assert valid["rows"] == repeat["rows"]
    assert {row["protocol"] for row in valid["rows"]} == {diagnostic.RAW_PROTOCOL}

    invalid = diagnostic.run_diagnostic(_Extractor("not JSON"), protocol="chat")
    assert {row["protocol"] for row in invalid["rows"]} == {diagnostic.CHAT_PROTOCOL}
    assert all(not row["parse_valid"] for row in invalid["rows"])
