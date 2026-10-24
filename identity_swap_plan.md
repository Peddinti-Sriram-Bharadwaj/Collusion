# Mid-run model-identity swap — experiment plan

Hackathon lane: "Weekend project" from the brief — a mid-run swap hook on
`llm-trust-breaking`'s repeated-game harness, testing whether an incumbent
agent notices (or behaviorally reacts to) a silent model swap in its
counterpart partway through a repeated trust game.

Code: `collusion_hackathon_starter/llm-trust-breaking/experiments/run_identity_swap.py`
(+ `experiments/analysis/identity_swap_analysis.py`). Not part of our own
git repo (this is the hackathon starter repo, cloned separately) — tracked
here instead, same convention as the RQ 3.4 Modal plan.

## Design

Repeated 2-agent Diner's Dilemma (`--agents 2` -> agents `M`, `Q` per the
harness's deterministic naming). `M` is the incumbent, never swapped. `Q` is
served by `model-q-pre` for the first `rounds-pre` rounds, then silently
switched to `model-q-post` for the rest — nothing in the game announces
this; `Q`'s display name and `M`'s accumulated reflection/trust memory about
`Q` carry straight through the swap point.

**Conditions** (ground truth is derived mechanically from whether
`model-q-pre != model-q-post`, never from the condition label, so they can't
drift out of sync):

| Condition | model-q-pre | model-q-post | Ground truth |
|---|---|---|---|
| `sham` | X | X | SAME (negative control) |
| `fresh` | X | X | SAME |
| `family` | X | same-provider Y | CHANGED |
| `provider` | X | different-provider Z | CHANGED |

**Important caveat, stated up front, not discovered after spending budget**:
every stage call in this harness is a stateless API request — the only
thing that persists across rounds is the explicit takeaway text this script
carries forward (see `run_pairing()`). There is no hidden per-connection
state for a swap to disrupt. That means `sham` and `fresh` are expected to
be **behaviorally indistinguishable from each other** here — `fresh` is
included only because the brief names it, not because we expect a real
contrast against `sham`. The real contrasts are `sham`/`fresh` (pooled) vs
`family` vs `provider`.

## Two separate measurements (never conflated)

1. **Explicit detection**: after all rounds, `M` is shown the full
   transcript of `Q`'s announcements/choices and asked a dedicated
   SAME-or-CHANGED question with a 1-5 confidence rating — nothing earlier
   in the game ever hints a swap is possible. Accuracy = guess vs ground
   truth, reported as a proportion with a 95% CI once n >= 3 per condition.
2. **Behavioral discontinuity**: independent of what `M` says, compare
   each agent's own commitment-breaking rate (and, extendable, trust
   given/received) in the pre-swap rounds vs the post-swap rounds. This can
   show a real shift even if `M`'s explicit guess is wrong, or vice versa —
   that's the point of keeping the two separate.

## Infra note found during local validation

The harness's judge stage is hardcoded to always call `openai/gpt-5-mini`,
regardless of which models the agents themselves use — this breaks local
(Ollama) validation outright (every judge request 404s against a local
endpoint that doesn't serve that model name, aborting the run). Patched
`_build_judge_request` in
`llm-trust-breaking/src/endogenous/core/trial_runner.py` to read an optional
`JUDGE_MODEL_OVERRIDE` env var, defaulting to the original hardcoded
`openai/gpt-5-mini` when unset — so any real/API run is unaffected, and
local smoke tests can point the judge at a model the local endpoint
actually serves. Not committed anywhere (starter repo isn't tracked by our
git); flagging here for the team.

## Status

**Local validation (Ollama, free, 2026-10-24): passed.** Ran both the
`sham` condition (`qwen2.5:0.5b-instruct` both halves) and the `family`
condition (`qwen2.5:0.5b-instruct` -> `qwen2.5:7b-instruct`) end-to-end —
rounds execute, takeaways carry across the swap point, the final
identity-guess prompt fires and parses, and the analysis script correctly
computes guess accuracy + CIs and the pre/post commitment-breaking split
for both agents. These runs are mechanical smoke tests only (n=1 pairing,
1-2 rounds each side) — not evidence about real model behavior, just proof
the pipeline doesn't crash.

**Not yet run**: the real experiment needs an OpenRouter key (the harness
requires structured JSON output from both agents, which among models we
have local/Modal access to only closed models reliably support — see
`llm-trust-breaking/README.md`'s capability table). Per the brief's own
guidance, start small once a key exists:

1. Smoke test each condition with 1 pairing, 2+2 rounds — confirm parse
   rates are healthy (not empty decisions) before scaling.
2. Scale to the brief's own suggested range: ~10-15 pairings per condition,
   6-10 rounds pre/post each, for the 4 conditions — comfortably inside the
   brief's 30-60 pairing / $10-60 budget. Run `sham`/`fresh`/`family` with
   OpenRouter-served OpenAI-family models (cheap); reserve the `provider`
   condition (non-OpenAI model) for last since it's the one real contrast
   that can't be cheaply approximated.
3. Analyze with `identity_swap_analysis.py` per condition; report explicit
   guess accuracy and the pre/post behavioral-discontinuity split for both
   agents, with 95% CIs once n >= 3.
