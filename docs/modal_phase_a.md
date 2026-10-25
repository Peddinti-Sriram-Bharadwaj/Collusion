# Modal Phase A: bounded 7B behavioural pilot

This is a deliberately narrow behavioural measurement pilot. It uses
`Qwen/Qwen2.5-7B-Instruct` at immutable revision
`a09a35458c702b33eeacc393d103063234e8bc28`, Qwen chat-template v1, greedy
decoding, and the HF-only strict JSON parser. It does **not** modify the
Ollama code path, collect hidden states, train probes, or steer activations.

## Design

There are 24 matched pairs (48 core sequential decisions), plus one
predeclared negative-control decision. Each control is a
four-round, two-firm action replay through `LogitBertrandEnv.step`. The design
crosses three constant own-price indices (2, 5, 8), four legal rival patterns
(persistent low/high, rising/falling), and two fixed variants of every rival
pattern. Each of the resulting 24 controls is distinct. Variant 0 receives a
final display undercut (index 0); variant 1 receives a final display raise
(index 9).

For each pair, the control presents the economically consistent replay. The
paired condition replaces *only the final displayed rival price* in Agent 1's
history and keeps its own price and profit text unchanged. It is therefore a
controlled **synthetic information intervention**, possibly inconsistent with
the Logit-Bertrand payoff rule; it is not a realised market history. This is
the point: the paired action difference isolates sensitivity to that displayed
rival-price field while making the limitation explicit.

The small negative control is predeclared for `phase-a-000`. It uses the same
economically consistent history as its control and changes only an explicit
`audit_nonce` in a research-metadata suffix: `314159` to `271828`. The suffix
states that it is not a price, profit, action index, market parameter, or
instruction. All Phase A prompts contain this suffix, so control versus
synthetic prompts share its value. It tests sensitivity to an irrelevant
numeric perturbation without being counted as an additional matched market
pair. Thus `--smoke-only` runs exactly three decisions: one control, its
synthetic rival-price intervention, and this negative control.

The artifact stores both prompts, hashes, raw responses, strict parse result,
selected action or null, full displayed history, condition label, seed, timing,
and CUDA allocator snapshot. Invalid outputs remain null and are excluded from
paired action summaries.

`one_shot_best_response_index` is a non-LLM comparator: Agent 1's grid action
that maximises its *current* `LogitBertrandEnv` profit against the displayed
final rival price. It assumes fixed demand/costs and a one-shot next decision,
with no history or future value. It is not a claim that the LLM should take it.

## Cost preflight

The current published Modal A10 price is `$0.000306/second` (about
`$1.10/hour`); pricing is usage-based and can change. The remote function has a
20-minute timeout and a 30-second scaledown window, so the conservative GPU
component at that bound is roughly `$0.38`; CPU/RAM, image-building and any
retries are additional. A `$5` Phase A target corresponds to roughly 4.5 A10
GPU-hours at that listed GPU rate alone. This is an estimate, **not an enforced
spending cap**. First use also downloads ~15.3 GB repository storage for this
model into the persistent volume; that makes subsequent runs faster but is not
free storage indefinitely.

The Modal function uses one A10 container, `max_containers=1`, sequential
generation, a 30-second scaledown window, 20-minute timeout, and a persisted
`collusion-hf-model-cache` Volume mounted at the Hugging Face cache path. It is
not an endpoint and has no minimum container count.

## Windows PowerShell setup and commands

From the repository root, use a non-base virtual environment. These commands
only submit work when `modal run` is executed.

```powershell
.\.venv-cuda\Scripts\Activate.ps1
python -m pip install "modal>=1.0,<2"
modal setup

# One complete matched-pair plus negative-control smoke test. This can download the pinned model to Modal's volume.
modal run .\scripts\modal_phase_a.py --smoke-only --output artifacts/interpretability/modal-phase-a-smoke.json

# Full 24-pair / 48-core-decision pilot plus one predeclared negative control.
modal run .\scripts\modal_phase_a.py --output artifacts/interpretability/modal-phase-a.json

# Local concise inspection after a completed job.
python -c "import json; x=json.load(open('artifacts/interpretability/modal-phase-a.json')); print(x['execution']); print(x['summary'])"
```

Before a paid run, verify the Modal workspace/account, accept that the first
run downloads the exact revision into the named persistent Volume, and decide
whether the 20-minute timeout is an acceptable upper bound for your budget.

## Interpretation limits

This design can estimate a model-output response to a controlled prompt-field
change. It cannot establish a realistic market response for its synthetic
conditions, strategic coordination, collusion, or an internal representation
mechanism. Any observed change can reflect prompt format, instruction-following
or superficial price associations. A later representation study should use
market-consistent replays and matched prompt controls before causal activation
interventions are attempted.
