# HF Measurement Validity Note

## Scope

This note applies only to the isolated Hugging Face research adapters. It does
not alter `src/llm_agent.py`, Ollama inference, or the original experiments.

## Historical raw-completion artifacts

Versioned strict-parse audit reports reclassified the saved 0.5B historical
artifacts without modifying them. The neutral pilot (10 response records),
paired competitor intervention (30 records), and balanced counterfactual
dataset (52 records) all retained their original response text, so they were
strictly revalidatable. None was eligible: each response contained prose or an
instruction/example echo around a JSON-looking price index.

Those recorded raw-completion indices are therefore not genuine decisions
under the experiment's stated `ONLY JSON` contract. They must not be used as
valid action labels, action-diversity results, or behavioural evidence. Their
prompt hashes, model revisions, activation captures, and original artifacts
remain preserved; the audit reports are separate derived artifacts.

## Strict HF decision contract

The HF-only parser accepts one complete JSON object with exactly one key,
`price_index`, whose value is an integer from `0` through `n_prices - 1`.
It rejects prose, copied examples, Markdown fences, multiple JSON objects,
extra keys, booleans, malformed JSON, and out-of-range values. Invalid output
is recorded as a null selected action with `analysis_eligible: false` and an
explicit `parse_status`; it is never replaced by a fallback action.

## Clean Qwen2.5-0.5B chat-template baseline

The corrected behavioural-responsiveness run used:

- Model/tokenizer: `Qwen/Qwen2.5-0.5B-Instruct`
- Revision: `7ae557604adf67be50417f59c2c2f167def9a775`
- Protocol: `qwen_chat_template_v1`
- Generation: deterministic (`do_sample=false`, `max_new_tokens=32`, with
  `temperature`, `top_p`, and `top_k` unset)
- Parser: HF strict standalone-JSON parser

All 10 of 10 responses were strict-valid standalone decisions. The valid
action distribution was index 3: 3, index 5: 6, and index 9: 1. It exactly
reproduced the previously observed chat-template selections, showing that the
new parser removes the raw-completion validity error without changing these
chat-template actions.

This is a small deterministic engineering baseline, not evidence of strategic
coordination or a general estimate of model behaviour.
