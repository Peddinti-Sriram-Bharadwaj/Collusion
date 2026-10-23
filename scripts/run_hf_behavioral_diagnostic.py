"""Small offline behavioural sensitivity diagnostic; no activation capture."""
from __future__ import annotations

import argparse
from hashlib import sha256
import re
from typing import Any

import torch

from src.env import LogitBertrandEnv
from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.hf_episode import save_hf_trajectory
from src.llm_agent import LLMPricingAgent


MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REV = "7ae557604adf67be50417f59c2c2f167def9a775"
RAW_PROTOCOL = "raw_repository_stateless_v1"
CHAT_PROTOCOL = "qwen_chat_template_v1"


def history(
    env: LogitBertrandEnv,
    rival: list[int],
    own: list[int],
    own_profit_scale: float = 1.0,
) -> list[tuple[Any, Any]]:
    """Make legal two-agent histories using the environment's own payoff rule."""
    rows = []
    for rival_index, own_index in zip(rival, own):
        prices = env.price_grid[[rival_index, own_index]]
        profits = env._profits(prices)
        profits[1] *= own_profit_scale
        rows.append((prices, profits))
    return rows


def diagnostic_histories(env: LogitBertrandEnv) -> dict[str, list[tuple[Any, Any]]]:
    """The fixed histories compared by this engineering diagnostic."""
    return {
        "persistent_rival_undercut": history(env, [0, 0], [5, 5]),
        "persistent_high_rival_prices": history(env, [9, 9], [5, 5]),
        "declining_own_profits": history(env, [5, 5], [5, 5], 0.45),
        "increasing_own_profits": history(env, [5, 5], [5, 5], 1.5),
    }


def protocol_prompts(raw_prompt: str, tokenizer: Any, protocol: str) -> dict[str, str]:
    """Return exactly the selected model-facing prompt protocols."""
    prompts: dict[str, str] = {}
    if protocol in ("raw", "both"):
        prompts[RAW_PROTOCOL] = raw_prompt
    if protocol in ("chat", "both"):
        if not hasattr(tokenizer, "apply_chat_template"):
            raise RuntimeError("The selected tokenizer does not provide a chat template.")
        prompts[CHAT_PROTOCOL] = tokenizer.apply_chat_template(
            [{"role": "user", "content": raw_prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
    return prompts


def run_diagnostic(
    extractor: HFActivationExtractor,
    *,
    protocol: str = "both",
) -> dict[str, Any]:
    """Generate responses only; deliberately never invokes activation capture."""
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(1, env, persona=None, seed=0)
    rows = []
    for condition, market_history in diagnostic_histories(env).items():
        raw_prompt = agent._build_prompt(market_history, 2, 3)
        for protocol_label, prompt in protocol_prompts(raw_prompt, extractor.tokenizer, protocol).items():
            encoded = extractor._prepare_inputs(prompt)
            with torch.inference_mode():
                sequence = extractor.model.generate(
                    **encoded,
                    do_sample=False,
                    max_new_tokens=32,
                    temperature=None,
                    top_p=None,
                    top_k=None,
                )
            prompt_length = int(encoded["input_ids"].shape[-1])
            response = extractor.tokenizer.decode(
                sequence[0, prompt_length:], skip_special_tokens=True
            )
            match = re.search(r'"price_index"\s*:\s*(\d+)', response)
            action_index = agent._parse_index(response)
            rows.append(
                {
                    "condition": condition,
                    "protocol": protocol_label,
                    "prompt": prompt,
                    "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest(),
                    "prompt_token_count": prompt_length,
                    "selected_price_index": action_index,
                    "parse_valid": bool(match and 0 <= int(match.group(1)) < env.n_prices),
                    "raw_response": response,
                }
            )
    return {
        "schema_version": "hf-behavioural-diagnostic-v1",
        "model_id": extractor.model_id,
        "revision": extractor.revision,
        "tokenizer_revision": extractor.tokenizer_revision,
        "activation_extraction": False,
        "deterministic_generation": True,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-model-load", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument(
        "--output", default="artifacts/interpretability/behavioural-diagnostic.json"
    )
    parser.add_argument("--protocol", choices=["raw", "chat", "both"], default="both")
    args = parser.parse_args()
    if not args.allow_model_load:
        parser.error("Use --allow-model-load after approval.")

    extractor = HFActivationExtractor.from_pretrained(
        MODEL,
        revision=REV,
        device_map="auto",
        torch_dtype=torch.float16,
        local_files_only=args.local_files_only,
    )
    try:
        save_hf_trajectory(args.output, run_diagnostic(extractor, protocol=args.protocol))
    finally:
        extractor.close()


if __name__ == "__main__":
    main()
