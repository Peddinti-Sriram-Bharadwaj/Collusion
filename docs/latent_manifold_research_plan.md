# Latent Representation and Manifold Research Plan

## Scope and invariants

This branch adds an opt-in Hugging Face representation-analysis path. It does
not modify the Ollama pricing implementation, existing prompts, personas, or
market behaviour. No model weights, activations, results, or credentials are
committed. The initial smoke test is neutral only: `personas=[None, None]`.

## Persona design

The experiment registry imports the repository's exact `PERSONA_TEXT` entries
rather than duplicating them. The planned balanced design includes the neutral
default, seven homogeneous conditions (`capitalist`, `socialist`,
`for_profit`, `nonprofit`, `rnd_oriented`, `consumer_empathetic`, `hoarder`),
and the existing mixed conditions capitalist/socialist and
hoarder/consumer-empathetic. It is a plan only; it does not schedule runs.

Every decision row records `persona_id` and a SHA-256 `persona_prompt_hash` of
the exact injected text, as well as a full-prompt hash, prompt length, model /
tokenizer revisions, backend, quantization, generation settings, market
configuration, episode/agent/round identifiers, proposed and executed action,
and realised profit.

Persona labels are never collusion labels. Persona-associated directions will
be estimated separately from candidate coordination-associated directions.
Before any steering study, a candidate coordination signal must retain its
predictive value after controls and generalize to held-out personas.

## Collection and alignment

For selected layers 4, 14, and 27, capture the final non-padding prompt token
before generation. Generated-token activations, if later collected, use a
separate dataset because they can reflect JSON formatting and sampling.
Alignment validation rejects unknown personas, persona-hash drift, mismatched
token counts, non-final token positions, missing requested layers, and
inconsistent vector dimensions.

## First prediction experiment

The prediction target is a pre-specified behavioural outcome, such as next
price bin, response to a rival-price change, or a future episode-tail
high-Delta indicator. It is not a persona label and high Delta is described as
collusion-like rather than proof of coordination.

Compare three identically regularized, group-split models:

1. **Behaviour history only:** own/rival prices, own profit, round number,
   price grid, market configuration, prompt length, and known prompt flags.
2. **Hidden activations only:** standardized layer vectors selected without
   behavioural features.
3. **Combined:** the union of both feature sets.

Split by complete episode/market seed, never individual rounds. Report
held-out performance and confidence intervals at the episode level. Repeat
with leave-one-persona-out evaluation and within-persona competitive versus
collusion-prone comparisons where sufficient natural behavioural variation
exists. Prompt wording/length, market histories, realised prices, and profits
are controls, not evidence of a coordination representation.

## Separating persona from coordination

First measure how well persona is predictable from hidden states; this is a
confound audit, not a success metric. Estimate persona directions using
matched histories within each market scenario. Estimate a coordination
candidate only from behavioural contrasts within the same persona, with
matched or adjusted histories and outcomes. A direction is ineligible for
steering if it: (a) fails held-out-persona generalization; (b) loses its
incremental predictive value over behavioural history; or (c) is substantially
aligned with a persona-prediction direction without a within-persona effect.

## Hardware options before model download

The available RTX 3060 Laptop GPU has 6 GB VRAM. The official BF16 Qwen2.5-7B
Instruct checkpoint is roughly 15 GB, so direct GPU loading is unsuitable.
Options requiring approval before download are:

1. CPU/offloaded exact 7B checkpoint: most faithful, but slow and requires
   substantial system RAM and a roughly 15 GB download.
2. 4-bit HF loading of the exact checkpoint: potentially near the 6 GB limit;
   needs a supported quantization stack and leaves little activation/cache
   headroom. Record quantization and do not compare it directly to another
   backend without validation.
3. Smaller Qwen pilot: practical for pipeline validation, but scientifically
   separate from the 7B Ollama result and unsuitable for direct representation
   comparison.

No option is selected and no weights are downloaded in this implementation.

## Neutral Hugging Face pilot

The proposed pilot is `Qwen/Qwen2.5-1.5B-Instruct` pinned to revision
`f73cfd58be7c44c3caabea717217251688cd47b1`. The adapter uses the existing
stateless prompt builder and its existing price-index parser, but is a separate
backend: it does not change the Ollama code path. It tokenizes once, captures
the final prompt token, and generates the price response from the same model
object, input-token hash, and generation parameters.

The pilot intentionally applies no Hugging Face chat template: it tokenizes
the exact raw stateless string produced by the repository prompt builder. Its
metadata records `prompt_format=raw_repository_stateless_v1`. This preserves
the existing prompt-builder semantics but is not token-for-token equivalent to
Ollama template behaviour; it is an explicit backend limitation, not a claim
of comparability.

`run_hf_neutral_episode` is neutral-only (`[None, None]`), reuses the existing
price grid, history format, profit calculation, and collusion index, and emits
the local `hf-neutral-trajectory-v1` schema. Its decision rows include price
and profit, activation vectors, model metadata, episode/agent/round IDs, and
an explicit failed-capture record when generation fails. Artifacts belong under
the ignored `artifacts/interpretability/` directory.

After resource approval, the guarded commands are:

```powershell
python -m scripts.run_hf_neutral_pilot --mode alignment --allow-model-load --output artifacts/interpretability/alignment.json
python -m scripts.run_hf_neutral_pilot --mode episode --allow-model-load --output artifacts/interpretability/neutral-five-round.json
```

The pilot remains an integration check, not a direct reproduction of the
Ollama 7B results: the model size, weights, tokenizer/template behaviour,
quantization, and generation backend differ. Raw prompt tokenization is kept
deliberately stable relative to the repository's stateless prompt builder; any
future chat-template transformation must be separately versioned and studied.
