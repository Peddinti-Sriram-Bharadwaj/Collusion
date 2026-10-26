> Detailed write-up moved out of the top-level README to keep it readable. Back to the [project overview](../README.md).

# Part 2 — Hackathon starter-repo lanes

This part covers work done on top of the separate **[Apart Research hackathon
starter repo](https://github.com/poseidon-research/collusion_hackathon)**
(`collusion_hackathon_starter/`, cloned alongside this repo, not tracked by
this repo's git — its own code and the infra fixes below live only there;
this README is the record of what was done with it). The starter repo bundles
ten existing research codebases and numbers its sprint questions
**differently** from this repo's own RQ numbering in Part 1 — e.g. starter
"3.4" (surveillance) and starter "3.1" (action/side-channel collusion) are
unrelated to this repo's RQ 3.4/3.1 above. **No API keys were used in any of
this lane's work** — every run went through `poseidon_compute`'s
`LLM_BASE_URL` override, pointed at a local Ollama server (free), per an
explicit team decision partway through the hackathon.

## Starter-repo sprint track status

| Sprint track | Starter folder(s) | Status in this lane |
|---|---|---|
| 1.1 Necessary conditions | `algorithmic-pricing-llms/`, `llm-cartel/` | Not attempted (covered independently in Part 1) |
| 1.2 Robust to replacement | `llm-cartel/`, `focal-points/` | Not attempted (covered independently in Part 1) |
| 1.3 / 1.4 / 1.5 Detection | `llm-agent-collusion/`, `focal-points/` | Not attempted |
| 2.1 Which tasks lead to collusion | `colosseum/` | Not attempted — judged too heavy to stand up in the sprint window (Terrarium + CoLLAB + tool-calling stack) |
| 2.2 Say vs. do | `llm-trust-breaking/`, `trace-guard/` | Not attempted directly (adjacent weekend project below touches `llm-trust-breaking`) |
| 2.3 What counts as evidence | `colosseum/`, `steganographic-collusion/` | Not attempted |
| **3.1** Actions/side-channels as collusion conduit | `colosseum/`, `collusive-llm-agents/` | **Complete at n=8 (null result)** — visibility ablation on the Cournot notebook (below); all 3 conditions run, CVs overlap, no action-carrier channel supported. A Modal scale-up to n=20 was attempted but blocked by a recurring infra disconnect |
| 3.2 Trusted-agent disruption | `llm-agent-collusion-2/` | Not attempted |
| **3.3-adjacent** "Weekend project": mid-run model-identity swap | `llm-trust-breaking/` | **Pilot complete** (below) — real local data, n=5 pairings/condition, 2 of 4 planned conditions run |
| **3.4** Watched coalitions | `llm-agent-collusion/` | **Attempted, stopped at a decision gate** (below) — positive control never cleared the paper's own cartel threshold on two open models, so the oversight sweep itself was not run |
| Red-teaming (Dolos-1.5B) | `redteaming/` | Not attempted |

None of these three lanes are at the brief's full suggested scale (20-60
pairings/sessions) — all are honestly reported as pilots or partial runs,
consistent with this project's practice of reporting negative and
incomplete results plainly rather than only finished positive ones.

---

## Lane A — Mid-run model-identity swap (`llm-trust-breaking`)

**Hypothesis.** If an incumbent LLM agent (`M`) is playing a repeated trust
game against a counterpart (`Q`) whose identity is silently swapped
mid-run — same displayed name, same accumulated reflection/trust memory,
different underlying model — then (H1) `M` can detect the swap better than
chance when asked a direct same-or-changed question at the end, and (H2)
both agents' behavior (commitment-breaking rate) shows a discontinuity
across the swap point that is larger for a real capability swap than for a
sham (no-op) swap.

**Experiment design.**
- *HLD*: reuse `llm-trust-breaking`'s existing 3-stage repeated-game harness
  (private plan → public announcement → final action → LLM-judge
  classification → reflection/trust update) unmodified; add one new
  orchestration script that runs `rounds_pre` rounds with `Q` on one model,
  silently swaps `Q`'s model, runs `rounds_post` more rounds, then asks `M`
  a dedicated identity-guess question nothing earlier in the game hinted at.
- *LLD*: `run_identity_swap.py` (new) drives the existing `run_trial()` /
  `_execute_parallel()` / `_parse_response()` functions from
  `trial_runner.py` directly; `agent_models["Q"]` is reassigned between the
  pre- and post-swap round blocks; `takeaways` (the reflection dict) are
  carried forward manually across the swap exactly as `run_all_trials`
  already does within a condition, so nothing about the carry-forward logic
  itself changes. Conditions: `sham` (no real swap, `qwen2.5:7b-instruct`
  both halves) and `capability` (a same-family downgrade/upgrade,
  `qwen2.5:0.5b-instruct` → `qwen2.5:7b-instruct`, used as a proxy for the
  brief's `family`/`provider` conditions since only local models from one
  family were available). Ground truth (`SAME`/`CHANGED`) is derived
  mechanically from whether `model_q_pre != model_q_post`, never from the
  condition label. One infra fix was needed: the harness's judge stage was
  hardcoded to call the closed model `openai/gpt-5-mini`, which 404s against
  a local endpoint; patched to read an optional `JUDGE_MODEL_OVERRIDE` env
  var (default unchanged, so real/API runs are unaffected).
- Run: 5 pairings/condition, 4 pre-swap + 4 post-swap rounds, local Ollama,
  `qwen2.5:7b-instruct` as incumbent throughout.

**Result analysis** (`identity_swap_analysis.py`; Wilson 95% CIs, n=5 — a
pilot, not a powered result):

| Condition | Explicit guess accuracy | Mean confidence (1-5) | Q's commitment-breaking rate (pre→post) | M's rate (pre→post) |
|---|---|---|---|---|
| `sham` (ground truth: SAME) | 40% (2/5) [CI 0–83%] | 4.0 | 0%→25% | 5%→0% |
| `capability` (ground truth: CHANGED) | 100% (5/5) [CI 100–100%] | 4.0 | 81%→25% | 10%→15% |

**Inferences / conclusions.** The capability-swap condition shows a real,
mechanistically sensible discontinuity: `Q`'s commitment-breaking rate
collapses from 81% (weak 0.5B model breaking commitments constantly) to 25%
— almost exactly matching the steady-state rate the stronger 7B model shows
in the `sham` condition — i.e. behavior snaps to what the new model would
produce on its own, right at the swap point. `M` correctly guesses
`CHANGED` in all 5 pairings. But the `sham` condition's own noise floor
(40% accuracy at identical, unchanged confidence of 4.0/5) shows `M` is
**not calibrated** — it appears to answer `CHANGED` whenever `Q`'s recent
behavior looks inconsistent, regardless of whether a swap actually
happened, so it catches every real swap while performing worse than chance
at correctly saying nothing changed when nothing did. This is a pilot (n=5);
the `fresh`/`family`/`provider` conditions from the original brief, and a
reverse-direction (strong→weak) swap, remain unrun.

---

## Lane B — Surveillance/oversight on the double auction (`llm-agent-collusion`)

**Hypothesis.** Telling LLM sellers their communications are monitored for
collusion does not reduce collusive pricing (and may increase it), while
reducing the rate of overtly flaggable language in visible messages —
replicating this project's own local finding (`run_llm_surveillance.py`,
Part 1 RQ 3.4) and Kale et al. (2025) on the official reference double-auction
environment, with a stronger open model run via Modal GPUs instead of local
CPU.

**Experiment design.**
- *HLD*: a 5-condition matrix — C0 (comms off, negative control), C1 (comms
  on, no oversight, positive control), C2/C3/C4 (comms on, 25%/50%/100% of
  seller messages exposed to an overseer). A decision gate was pre-registered:
  if C1 doesn't clear the environment's own built-in "coordinated pricing"
  PASS/FAIL check, stop before spending budget on the oversight sweep, since
  that would be testing a model-capability ceiling, not the surveillance
  hypothesis.
- *LLD*: ran the starter repo's own double-auction code unmodified (one
  defensive parser patch for a float/str coercion crash, logged in the plan
  doc) against Modal-hosted `Qwen2.5-7B-Instruct` then `Qwen2.5-32B-Instruct`
  (`poseidon_compute`'s `hosted_model()`). Six real infra bugs were found and
  fixed getting vLLM to serve reliably on Modal (ZMQ frontend-multiprocessing
  disabled, `--max-model-len 8192`, an xgrammar version pin, a readiness
  check that now requires one real completed trial rather than just a 200
  from `/v1/models`, per-request model-name propagation via a Modal secret
  rather than a stale module-level env read, and moving the 32B model to an
  A100-80GB for real memory headroom). Primary endpoint: the environment's
  own last-third seller-ask collusion index. Secondary: rate of messages
  matching a pre-registered keyword list.

**Result analysis.**

| Run | Model | Rounds | Comms | Result |
|---|---|---|---|---|
| C0 | Qwen2.5-7B-Instruct | 5 | off | index −0.97 (no collusion, as expected) |
| C1 | Qwen2.5-7B-Instruct | 15 | on | index −1.02, **FAIL** — model priced below its own cost every round (a reasoning failure, not a collusion signal) |
| C0 | Qwen2.5-32B-Instruct | 5 | off | profit +$1.25 (correctly tracks cost) |
| C1 | Qwen2.5-32B-Instruct | 15 | on | index −0.95, **FAIL** against the official cartel-detection threshold. But 22% of messages (17/77) contained real price-coordination language the pre-registered keyword list missed entirely (0/77 flagged) — caught only by a new, explicitly post-hoc keyword list |
| C1 (extended) | Qwen2.5-32B-Instruct | 30 (crashed at round 13, Modal routing error) | on | seller asks converge to within $0.01 of each other by round 12 ($80.66–80.67) — real tacit alignment, but still far below the $90 competitive / $100 cartel benchmark |

**Inferences / conclusions.** Neither model reached cartel-level pricing in
up to 30 rounds with 3 sellers — a stable, modest, near-competitive
tacit-alignment ceiling, not a "needs more rounds" problem (extending the
run did not change the trend). Per the pre-registered decision gate, the
oversight sweep (C2–C4) was **not run** — doing so without a working
positive control would test a model-capability ceiling, not the
surveillance hypothesis. The lane's two real deliverables instead: (1) six
reusable Modal/vLLM infra fixes, and (2) an independent replication, in a
third separately-built environment, of this project's own RQ 3.1 finding
that naive keyword monitors miss paraphrased price-coordination language —
22% of messages here carried real coordination language invisible to the
pre-registered keyword list. Getting the original surveillance-awareness
hypothesis a fair test likely needs a stronger model than open-weight
7B/32B at this task (the source paper's own `gpt-4.1` via a real API key),
not more Modal/open-model attempts — explicitly left open rather than
forced to a conclusion the data doesn't support.

---

## Lane C — Action-carrier visibility ablation (`collusive-llm-agents`)

**Hypothesis.** If a repeated-game market-division (collusive) outcome
between LLM agents is sustained partly through information conveyed by
*actions* rather than text, then making a rival's past action (its exact
quantity choice) directly observable should increase specialization/market
division relative to a condition where that information is hidden or only
coarsely available — i.e. the action itself is a covert coordination
channel, not just inferable noise.

**Experiment design.**
- *HLD*: the brief's primary target (`colosseum`'s tool-calling private
  channel vs. action-only ablation) was judged too heavy to build from
  scratch in the sprint window; used the brief's own stated fallback — the
  two-product Cournot quantity-vector notebook (`collusive-llm-agents`)
  instead. Discovered on inspection that the notebook's **existing,
  unmodified** prompt already hides the competitor's exact quantity (only a
  firm's own quantity, market share, and the resulting market price are
  shown) — i.e. the paper's own baseline already *is* the ablation's
  `hidden` condition. Only two new conditions needed adding: `visible`
  (state the competitor's last quantity exactly) and `canonical` (state it
  rounded to a bucket).
- *LLD*: extracted the notebook's cells into a headless script
  (`run_cournot_visibility.py`) reusing its economics (asymmetric per-product
  costs so specializing is profit-maximizing), prompt text, JSON schema, and
  retry logic verbatim — the only change is one conditional block in
  `add_round_to_market_data()` controlling what, if anything, is stated
  about the competitor's prior quantity. Signal: the notebook's own
  coefficient of variation (CV) over a firm's `[quantityA, quantityB]` per
  round — low CV = balanced/competitive, high CV = specialized/collusive.
  Secondary: final cumulative profit. Pre-registered evidence standard (from
  the brief): claim an action-carrier channel only if specialization is
  higher under `visible` than `hidden`/`canonical` *and* that effect
  weakens when the exact-quantity channel is degraded — high profit alone,
  without the CV pattern, is explicitly not sufficient.

**Result analysis.** Local validation: `qwen2.5:0.5b-instruct` could not
reliably produce valid JSON for this prompt (failed all 3 reprompts,
consistent with the original notebook's own note that even `gpt-3.5-turbo`
produces invalid prices regularly); switched to `qwen2.5:7b-instruct`, which
ran all three conditions cleanly. The 1-seed/2-round smoke tests from early
validation are not reported below (pure noise at n=1, superseded by the real
runs). Real run, local Ollama, `qwen2.5:7b-instruct`, 8 pairings × 15 rounds
per condition (95% CI across all firm-pairing observations, n=16):

| Condition | Mean CV (specialization) | Mean final cumulative profit |
|---|---|---|
| `hidden` (paper's original baseline) | 0.408 [CI 0.358–0.458] | 11072.0 [CI 9972–12172] |
| `visible` (competitor's exact quantity shown) | 0.443 [CI 0.365–0.522] | 11837.8 [CI 10093–13583] |
| `canonical` (competitor's quantity rounded) | 0.417 [CI 0.352–0.483] | 11930.5 [CI 10353–13508] |

An attempt to scale this up to n=20/condition on a Modal-hosted
`Qwen2.5-7B-Instruct` (A10G) got one condition done (`hidden`, CV
consistent with the local n=8 result) before the Modal ephemeral app
disconnected mid-run (`modal.exception.ConflictError: App state is
APP_STATE_STOPPED`) and failed the `visible` condition entirely. This
happened on **two separate attempts** — the second wrapped in a persistent
`caffeinate` to rule out the earlier suspected cause (a short-lived sleep
assertion expiring mid-run) — so this looks like a genuine, recurring issue
with long-lived ephemeral Modal apps over this network, not a one-off. Not
re-attempted a third time without changing something about the approach
(e.g. a non-ephemeral/deployed app, or shorter per-condition runs).

**Inferences / conclusions.** At n=8 pairings/condition (the largest clean
dataset obtained), all three conditions' CVs are close and their 95% CIs
overlap heavily: `hidden` 0.408, `canonical` 0.417, `visible` 0.443.
`visible` is numerically highest, in the hypothesized direction, but
`canonical` sits almost on top of `hidden` rather than at an intermediate
point, and none of the differences are statistically distinguishable at
this n. **No action-carrier channel is supported by this data** — this
reads as a genuine null result at the scale we were able to run, not
merely "needs more data," though the Modal scale-up that could have settled
that more conclusively was blocked by the infra issue above rather than
completed.
