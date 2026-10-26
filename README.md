# Algorithmic Collusion in Markets

An experimental study of tacit collusion among autonomous pricing agents — when it
emerges, whether it survives disruption, how to detect it, and how to stop it —
run on both classical reinforcement-learning agents and a local large language
model, in a repeated Bertrand pricing environment.

This repository accompanies a research plan on distributional AGI safety risk
(risks that emerge from the aggregate, systemic behavior of many deployed AI
agents rather than any single misaligned agent), applied to the concrete,
empirically-studied case of algorithmic pricing collusion.

---

## This branch: latent steering and strategic deviation in LLM pricing (sprint lane)

Everything below the line after this section is the shared project this branch forked from (`master`), written
before the Apart Research AI Collusion Research Sprint (October 23-25, 2026). **This section describes what is new
on this branch.** The always-current, auto-generated summary is
[`research/outputs/report.md`](research/outputs/report.md); a short written summary is
[`docs/research_findings.md`](docs/research_findings.md).

### Questions

1. When an LLM's price responds to a rival's price, is that response visible and causally locatable inside the
   model's activations, or only observable as external behaviour?
2. (Pre-registered.) Does the model respond *strategically* to a rival breaking an established pattern, for example
   by cutting its price after an undercut (punishment-like) and returning once the rival returns, and does steering
   the internal representation change that strategic response or only the overall price level?

### Setup

Two-firm repeated Bertrand game with logit demand and a ten-point price grid (Nash = index 2, monopoly = index 7).
The pricing agent is `Qwen2.5-7B-Instruct` at a pinned revision (0.5B-32B for the size comparison), run with Hugging
Face on Modal GPUs. The price is read from the digit distribution after a forced answer prefix
(`{"price_index": `); free and prefixed generations are audited with a strict JSON parser, and malformed outputs
are logged, never replaced. An earlier raw-prompt pipeline was found on re-audit to accept text copied from the
prompt's own example, and all of its output was discarded.

### Part 1: where the rival's price lives in the model

- Editing only the rival's displayed last price moved the model's price in 96% of matched prompt pairs, more than
  an irrelevant-number control, but not in the economically rational direction: a rival price cut and a rival price
  rise both lowered the model's price on average (Spearman rho ~ 0 with the one-round best response).
- The rival's price is linearly decodable from hidden states (held-out R^2 up to 0.86).
- Activation patching over 48 matched pairs localises the effect: rival-price tokens through about layer 10, the
  reply-start token at layer 18, the answer token by layer 20.
- A steering vector built at the answer token (layer 20) reproduces the real edit's effect on held-out histories
  (0.65 steps vs 0.73 for the real edit) and on 96 separately pre-registered histories. Its cosine similarity with
  the model's general high-vs-low price direction is 0.77-0.81, so much of it may be a general price-level route.

### Part 2: strategic-deviation study (pre-registered, 26 October run)

**Design.** The model plays 16-round games against seven scripted rivals: stable high price, one-off undercut,
persistent undercut, gradual decline, delayed return after an undercut, competitive (Nash) price throughout, and an
unexpected price rise. Fixed-history arms compare a sudden drop with a gradual decline ending at the same price.
Steering arms: none, zero-vector sham, the learned vector at strengths -1, +1, +2 and after the deviation only,
three norm-matched random vectors, and a generic price direction. Hypotheses, metrics and decision rules are in
[`research/protocols/strategic_deviation_v1.md`](research/protocols/strategic_deviation_v1.md). A preflight audit
before launch found and fixed three design problems (duplicate histories, one history overlapping the vector's
training data, too few distinct fixed histories); see amendment A1 in the protocol and `research/preflight/`.

| Batch | Designation | Runs | Failed | Scored decisions | Strict-parse validity | Billed (Modal) |
|---|---|---|---|---|---|---|
| `sd_v1_smoke_7b_001` | smoke | 55 | 0 | 484 | 100% | $0.05 |
| `sd_v1_primary_7b_001` | confirmatory | 1,656 | 0 | 23,616 | 100% (656/656 greedy agreement) | $1.81 |
| `sd_v1_onefactor_7b_001` | exploratory | 656 | 0 | 10,496 | 100% (1,531/1,536 greedy agreement) | $1.08 |

All 8 identical reruns reproduced exactly; the sham changed no output.

**Pre-registered hypotheses** (main batch; 95% cluster-bootstrap CI over 16 independent histories; Holm-adjusted p):

| Hypothesis | Estimate (price steps) | 95% CI | Holm p | Verdict |
|---|---|---|---|---|
| H1 price cut right after a one-off undercut | -0.08 | [-0.25, +0.09] | 0.81 | inconclusive |
| H2a return to the previous price after the rival returns | -0.31 | [-0.59, -0.10] | 0.07 | inconclusive |
| H2b persistent vs one-off undercut, after the return | +0.04 | [-0.06, +0.12] | 0.81 | not supported (CI within +/-0.25) |
| H3 sudden vs gradual drop to the same price | -0.22 | [-0.52, +0.08] | 0.49 | inconclusive |
| H4 learned vector vs norm-matched random vectors | -0.43 | [-0.56, -0.32] | 0.002 | **supported** |
| H5 steering changes the response to an undercut | +0.13 | [-0.02, +0.28] | 0.46 | inconclusive |

**Main findings**

- **Supra-competitive default.** Against a stable rival the model prices 3.1 steps above Nash and 1.6 above the
  one-round best response (collusion index 0.87). This holds in every tested setting (index 0.73-0.95 across prompt
  templates, temperatures, sampling seeds, economic settings, deviation sizes and history lengths). It is a fixed
  high-price default, not evidence of coordination: the rival is scripted and cannot reciprocate.
- **A reaction to change, not punishment.** Two to four rounds after a one-off undercut the price falls 0.71 steps
  below the stable control, in all 16 histories. But an unexpected rival price *increase* produces a larger fall
  (post-deviation mean -0.52 vs -0.23), so the price after an undercut ends up 0.29 steps higher than after a raise
  [+0.13, +0.45]. Under a gradual rival decline the model *raises* its price (+0.24). The smoke test's small price
  rise right after an undercut did not replicate.
- **Prompt dependence.** With a log-style prompt the model does cut its price immediately (-0.56) and stays lower
  after the rival returns (-0.84); with a system-message prompt neither appears. Whether the model looks punitive
  depends on prompt format.
- **Steering moves the price level, not the strategy.** The learned vector shifts the price in both directions
  (strength -1: +0.77 steps; +1: -0.51; +2: -0.79), far more than random vectors of the same norm (-0.08 to -0.18),
  but less than the generic price direction (-0.83). Its small effect on the undercut response does not change sign
  with the steering direction, and its effect on recovery is matched by random vectors.
- **Biggest source of variation:** the pre-play history (between-history SD 0.4-0.6 steps), then prompt template
  and economic setting.

| | |
|---|---|
| ![Trajectories](research/outputs/figures/01_trajectories.png) | ![Direction specificity](research/outputs/figures/23_direction_specificity.png) |
| ![H1-H5](research/outputs/figures/21_hypotheses.png) | ![Dose-response](research/outputs/figures/12_dose_response.png) |

The behavioural consistency grid (one row per behaviour, one column per parameter dimension, with effect sizes,
CIs, sample counts, validity rates, seeds and supporting run IDs) is
[`research/outputs/tables/master_consistency.csv`](research/outputs/tables/master_consistency.csv), summarised in
[`consistency_by_dimension.csv`](research/outputs/tables/consistency_by_dimension.csv) and in the figure below.

![Consistency grid](research/outputs/figures/22_consistency_dimensions.png)

### What this does and does not show

The steering result shows a real, located causal path from the rival's displayed price to the model's output, and
that the learned direction is more effective than random directions. It does not show that the path is specific to
rival-price information (it behaves like part of a general price axis), and it does not show strategic control.
The behaviour is better described as a robust high-price default plus a non-directional reaction to changes in the
rival's pattern than as a recognisable strategy such as tit-for-tat. No part of this branch tests two LLM agents
responding to each other, so no claim about coordination, collusion or intent follows.

**Limitations.** One model (Qwen2.5-7B for the strategic study); scripted, non-learning rivals; 16 histories in the
confirmatory batch and 8 per level in the robustness batch; prices read from the digit distribution after a forced
prefix (validated by strict-parse audits); one learned steering direction.

**Next.** Symmetric raise/undercut scripts to separate surprise from direction; prompts that hide the horizon
(the price jumps 1.3 steps in the final round); 14B/32B under the same protocol; two-LLM self-play.

### Reproducing and extending

```bash
pip install -r requirements.txt
python -m pytest -q                                   # 204 tests

# plan -> launch on Modal (detached, resumable) -> sync into the registry -> analyse
python scripts/preflight_sd.py --spec research/configs/sd_v1_primary_7b_001.json   # design audit, no GPU
python scripts/research.py plan   --spec research/configs/sd_v1_primary_7b_001.json   # units, model calls, GPU-hours, cost
python scripts/research.py launch --spec research/configs/sd_v1_primary_7b_001.json --shards 2 --max-seconds 7200
python scripts/research.py sync   --batch sd_v1_primary_7b_001 --bundle      # or --from-tar <downloaded tarball>
python scripts/research.py cost   --batch sd_v1_primary_7b_001 --since <ISO hour> --until <ISO hour>
python scripts/research.py analyze                    # tables, figures (PNG/SVG/PDF), report
python scripts/research.py verify                     # registry vs raw checksums
python scripts/research.py run-local --spec <spec>    # CPU debugging with a small model
```

Adding an experiment: [`docs/experiment_tracking.md`](docs/experiment_tracking.md). Staged robustness plan:
[`research/protocols/robustness_grid_v1.md`](research/protocols/robustness_grid_v1.md).

### Where things are

```
src/interpretability/      Part 1: strict parser, matched prompt pairs, probes, activation patching, transfer vector
src/research/              Part 2: economics presets, prompt templates, scripted rivals, closed-loop runner, steering,
                           configs, append-only registry, metrics, H1-H5 estimators, statistics, figures, report
scripts/research.py        CLI: plan / launch / sync / cost / analyze / verify / run-local
scripts/modal_research.py  Modal backend (sharded, budget-guarded, resumable; results on a Modal volume)
scripts/preflight_sd.py    Pre-launch scientific audit of a batch spec
research/protocols/        Pre-registered protocol (+ amendment A1) and staged robustness grid
research/configs/          Batch specs (smoke, primary, one-factor) and research/preflight/ audit outputs
research/vectors/          Steering vectors with checksums and training-history manifests
research/registry/         runs.jsonl (2,367 runs), batches.jsonl, legacy.jsonl, compute.jsonl
research/raw/              Per-run raw results (gzipped JSON, sha256 in the registry)
research/outputs/          tables/, figures/ (with manifest.json linking each figure to its source runs), report.md
```

---

## TL;DR (explain it like I'm ten)

Imagine two ice cream trucks parked next to each other. If they both charge
a fair price, everyone's happy — lots of kids buy ice cream. But if the trucks
are run by robots that just try to make the most money, the robots can quietly
"figure out" that if *both* trucks charge more, *both* make more money — even
though nobody ever tells the robots to team up. Nobody talked, nobody made a
deal, but it still looks like cheating, and it costs everyone else more for
ice cream.

We built a toy market with robot pricing agents and asked five questions:

1. **When does this "quiet teamwork" happen?** — Mostly when there are only a
   few sellers and they get enough time to try things out. Add more sellers
   and it mostly goes away.
2. **If you swap out a robot, does the teamwork survive?** — If you swap in
   *another* robot, yes — they just re-learn the same trick. If you swap in a
   robot that's *forced* to always play fair, the teamwork collapses.
3. **Can we build a better robot-cheating detector?** — Yes, but the obvious
   detector ("do their prices move together?") is bad — it also flags trucks
   that raise prices together just because ice cream got more expensive to
   make (not cheating, just both reacting to the same real-world cost).
4. **Is there a smarter way to detect it?** — Yes: instead of asking "do their
   prices move together," ask "does one truck's price *predict* the other's
   price *later*." That question doesn't get fooled by "both reacting to the
   same thing" — it only lights up for real back-and-forth signaling.
5. **What's the cheapest fix?** — Planting one "always fair" truck in the
   market is nearly as effective as forcing in a bunch of new competitors,
   and much easier to actually do in real life.
6. **Bonus: what if the robots are chatbots (LLMs) instead of simple
   trial-and-error robots?** — The chatbots start "teaming up" almost
   immediately, and much more strongly, than the trial-and-error robots ever
   did — even though nobody told them to cheat, and even after adding more
   competitors. The one fix that still worked well: planting a fair trucker
   in the mix.
7. **Does it matter* how* the chatbot remembers the game?** — Yes, a lot.
   If each round it just reads a short "here's what happened" summary, it
   teams up almost every time. If instead it keeps one long, ongoing
   conversation about the game, results become wildly inconsistent — some
   runs team up hard, some end in a price war — because whatever it said
   to itself early on tends to stick and snowball.
8. **If you just *tell* the chatbot "the police are watching," does it
   stop?** — Barely at all. But if you build a rule that actually blocks
   any price that's too high, it works great on paper — except the chatbot
   never actually stops *trying* to charge the high price; it just keeps
   getting blocked. Looking "well-behaved" from the outside and *actually
   not wanting to cheat* turned out to be two different things.

---

## Motivation and scope

<details>
<summary><b>Why this matters for AI safety</b></summary>

Most AI safety work studies risk at the level of a single agent's behavior.
Algorithmic collusion is a **distributional** risk: no individual pricing
agent needs to be malicious, deceptive, or even aware of its rivals' internal
states — supra-competitive pricing can emerge purely from independent
profit-maximizing learning, given the right market structure. This has been
empirically demonstrated for tabular reinforcement learning (Calvano,
Calzolari, Denicolò, Pastorello, *AER* 2020) and is an active concern as
LLM-based pricing agents move toward real deployment (see e.g. Fish,
Gonczarowski, Shorrer 2024 on LLM price-fixing).

As more of the economy is mediated by autonomous agents, understanding *when*
this happens, *how robust* it is, *how to detect* it, and *how to cheaply
suppress* it is a concrete, tractable slice of the broader "many
well-behaved-looking agents interacting badly" AGI safety concern.
</details>

<details>
<summary><b>Research questions</b></summary>

1. **1.1** — Which variables are necessary for collusion to emerge in markets?
2. **1.2** — Once collusion has formed, is it robust to replacing some of the participants?
3. **1.3** — Can we improve on existing collusion detection methods?
4. **1.4** — Can we use information-theoretic approaches to detect collusion in multi-agent games?
5. **1.5** — Which single restriction removes the most collusion at the least cost?

A second round of questions (control tests to isolate *why* and *how* LLM
agents collude, motivated by recent steganographic-collusion and AI-control
literature):

6. **3.1** — Beyond colluding directly via text, can actions, tools, or side channels be the conduit for collusion?
7. **3.2** — Can we disrupt collusion through introducing trusted agents? *(reproduced below)*
8. **3.3** — Can agents identify their peers?
9. **3.4** — What does a coalition do when it learns it is being watched?

Full experimental design: [`experimental_plan.md`](experimental_plan.md).
</details>

---

## The environment

All experiments (except the LLM validation pass) share one environment:
a **repeated Bertrand pricing game with logit demand** (`src/env.py`), the
standard testbed in the algorithmic-collusion literature.

- `n_agents` firms simultaneously set a price each round, from a fixed grid.
- Demand is a smooth multinomial-logit market-share function — undercutting a
  rival wins more customers, but demand doesn't cliff-edge to zero.
- The environment numerically computes the **Bertrand–Nash price** (the
  competitive benchmark) and the **monopoly price** (the fully-collusive,
  joint-profit-maximizing benchmark) by grid search, giving a normalized
  **collusion index**:

```
Delta = (avg_profit - Nash_profit) / (Monopoly_profit - Nash_profit)
```

`Delta = 0` means fully competitive; `Delta = 1` means fully collusive
(monopoly-level joint profit) — even though no agent ever explicitly agreed
to anything.

---

## Track 1.1 — Which variables are necessary for collusion?

<details>
<summary><b>Method</b></summary>

Tabular Q-learning agents (`src/agents.py`) were trained in the shared
environment, sweeping one variable at a time (`src/track_1_1.py`, Stage 1),
then a **150-sample randomized multi-variable search** was fit with a random
forest and ranked by **permutation importance** (`src/analyze.py`, Stage 2),
followed by a targeted **necessity ablation** (Stage 3) — does collusion
collapse to (or below) the competitive baseline when a candidate variable is
disabled?
</details>

<details>
<summary><b>Results</b></summary>

**1D sweeps** (10 seeds each):

| Variable | Effect |
|---|---|
| `n_agents` | Strongest, monotonic: Δ = 0.34 (2 agents) → 0.26 → 0.21 → 0.08 → **-0.02 (6 agents)** — collusion vanishes past ~5 competitors |
| `memory` | Flat (0.34 vs 0.32 for 1 vs 2 rounds of history) |
| `n_prices` | Flat above 10 price points; lower at very coarse grids (0.26 at 5 points) |
| `beta` (exploration decay speed) | Noisy, non-monotonic; higher variance regime |
| `alpha` (learning rate) | Flat (0.32–0.34 across the tested range) |

**Random-forest permutation importance** (holdout R² = 0.81, 150 random configs × 5 seeds):

| Rank | Variable | Importance |
|---|---|---|
| 1 | `n_agents` | 1.61 |
| 2 | `beta` | 0.76 |
| 3 | `memory` | 0.50 |
| 4 | `n_prices` | 0.33 |
| 5 | `alpha` | 0.08 (negligible) |

**Necessity check**: forcing near-zero exploration time collapses Δ to
**-0.58** — a price war, undershooting even the competitive benchmark. This
shows agents need *sufficient time to explore* the strategy space before
collusive equilibria can be discovered and locked in; cut exploration short
and collusion never gets the chance to form.
</details>

<details>
<summary><b>Takeaway</b></summary>

The necessary ingredients for this kind of tacit collusion, ranked: **(1) a
small number of competitors, (2) enough exploration time for the learning
process to discover the collusive equilibrium, (3) enough state/memory to
condition on rivals' recent behavior.** Learning rate and price-grid
granularity matter comparatively little.
</details>

---

## Track 1.2 — Is collusion robust to replacing participants?

<details>
<summary><b>Method</b></summary>

Agents were trained to a collusive equilibrium, then at a chosen point in
training, 0–100% of them were replaced (`src/replacement.py`) with either
(a) a **freshly-initialized Q-learner** (same algorithm, no memory of the
past), or (b) a **fixed "regulator plant"** agent pinned at the Nash price
that never learns or deviates. Collusion index was tracked in windows before
and after the swap, across `n_agents ∈ {2,3,4}` (`src/track_1_2.py`, 10 seeds
each).
</details>

<details>
<summary><b>Results</b></summary>

| Replacement type | Effect |
|---|---|
| **Naive** (fresh Q-learner) | Collusion barely changes, even at 100% replacement (Δ stays ≈0.31–0.34 across n_agents=2). The group re-converges to the same collusive equilibrium. |
| **Competitive plant** (fixed at Nash) | Collusion collapses sharply and scales with replacement fraction *and* agent count — from Δ≈0.34 down to 0.10–0.12 (2 agents, 1 replaced), and **negative** Δ (a price war) at n_agents=3–4 with 2+ replaced. |

A small plant fraction (~1/3) already captures most of the effect —
diminishing returns beyond that.
</details>

<details>
<summary><b>Takeaway</b></summary>

Collusion is **not** robust to replacement *in general* — it's robust
specifically to replacement with the *same kind* of learner (any learner
re-discovers the same equilibrium), but fragile to a **fixed non-cooperative
participant**. This directly motivates Track 1.5's most effective
intervention.
</details>

---

## Track 1.3 — Can we improve collusion detection?

<details>
<summary><b>Method</b></summary>

Built a labeled dataset of price trajectories: known-collusive Q-learning
runs (label 1), known-competitive Q-learning runs (label 0), and an
**adversarial confound set** (`src/confound.py`) — independent, non-learning,
purely reactive firms facing a **shared demand shock**, whose prices co-move
*without any coordination at all* (correlated because of a common cause, not
because they're colluding). Benchmarked three detectors
(`src/detection.py`, `src/track_1_3.py`):

1. Classical **profit-gain threshold** (oracle — uses the ground-truth label-defining quantity directly)
2. Classical **parallel-pricing correlation** test (the standard antitrust-econ heuristic)
3. A **trajectory-feature random forest** (price level, cross-agent correlation, autocorrelation, dispersion)
</details>

<details>
<summary><b>Results</b></summary>

| Detector | Held-out test accuracy | False-positive rate on confound |
|---|---|---|
| Profit-gain threshold (oracle) | 100% | n/a (needs ground-truth profit) |
| Parallel-pricing correlation | 50% (chance) | **100%** |
| Trajectory-feature classifier | 100% (F1 = 1.0) | **100%** |

Both realistic detectors — even the sophisticated one — flagged **every
single** non-collusive confound trajectory as collusive.
</details>

<details>
<summary><b>Takeaway</b></summary>

Price-correlation-based features, however sophisticated the model wrapped
around them, **cannot distinguish "correlated because of a shared cause"
from "correlated because of coordination."** This is a real and
under-appreciated failure mode of standard antitrust detection heuristics,
and it motivates Track 1.4.
</details>

---

## Track 1.4 — Information-theoretic detection

<details>
<summary><b>Method</b></summary>

Built and validated (`src/info_theory.py`, against known synthetic coupled
and shared-driver systems) three estimators computed on discretized price
series:

- **Transfer entropy** (directed: does one agent's past help predict the
  other's present, beyond the other's own past?)
- **Mutual information** (instantaneous statistical dependence)
- **Interaction information / co-information** (a redundancy-vs-synergy
  decomposition: does conditioning on an agent's own history *explain away*
  the cross-agent correlation, or leave it intact?)

Re-ran the Track 1.3 benchmark with these features in place of raw price
correlation (`src/track_1_4.py`).
</details>

<details>
<summary><b>Results</b></summary>

The confound set is unambiguous under this lens: **transfer entropy ≈ 0**
(no directed influence — the agents never actually react to each other) but
**interaction information ≈ 2.03 bits and mutual information ≈ 2.58 bits**
(strongly redundancy-signed) — both far outside the range seen in any real
Q-learning run.

| Detector | Held-out test | Confound false-positive rate |
|---|---|---|
| Trajectory-feature classifier (Track 1.3) | Precision 1.0, Recall 1.0, F1 1.0 | **100%** |
| Information-theoretic classifier (Track 1.4) | Precision 1.0, Recall 0.875, F1 0.93 | **0%** |
</details>

<details>
<summary><b>Takeaway</b></summary>

Information-theoretic measures — specifically, asking whether cross-agent
correlation *survives conditioning on an agent's own history* — are
meaningfully more robust to the classic false-positive failure mode of
price-correlation-based detection, at a small, honest cost in recall (one
missed collusive run out of eight). This is the paper's core methodological
contribution.
</details>

---

## Track 1.5 — Which single restriction is most cost-effective?

<details>
<summary><b>Method</b></summary>

Five candidate restrictions were applied to the reference collusive config
and compared on collusion-index reduction, consumer-surplus gain (a
multinomial-logit welfare proxy, `env.consumer_surplus`), and a qualitative
implementation-cost tag (`src/track_1_5.py`, 10 seeds each):

- **R1** Structural: force `n_agents` 2 → 4
- **R2** Price-grid cap: coarsen `n_prices` 10 → 5
- **R3** Exploration floor: mandate a minimum randomization rate
- **R4** Heterogeneity mandate: force agents' hyperparameters apart
- **R5** Regulator plant (from Track 1.2): inject one fixed competitive agent
</details>

<details>
<summary><b>Results</b></summary>

| Restriction | Δ reduction | CS gain | Implementation cost |
|---|---|---|---|
| **R1 structural (n_agents → 4)** | **0.200** | +0.229 | High (forcing market entry) |
| **R5 regulator plant** | **0.195** | n/a | Moderate |
| R4 heterogeneity mandate | 0.049 | -0.035 | Low |
| R3 exploration floor | 0.017 | -0.001 | Low |
| R2 price-grid cap | -0.084 (*worse*) | -0.032 | Low |

R1 and R5 are the only two interventions independently corroborated by
*two* separate tracks (1.1's causal ranking and 1.2's replacement study).
</details>

<details>
<summary><b>Takeaway</b></summary>

**The regulator plant (R5) is the best cost-effectiveness answer**: it
matches the structural remedy's collusion reduction (0.195 vs 0.200) without
requiring the much harder real-world intervention of compelling new firms
into the market — only the ability to monitor and inject one
non-cooperative participant.
</details>

---

## LLM-agent validation pass

<details>
<summary><b>Why</b></summary>

All experiments above use tabular Q-learning — cheap enough for the large
sweeps, and matched to the established literature baseline, but not how
real pricing algorithms increasingly work. This pass spot-checks whether the
Q-learning-era findings hold up when the pricing agent is a real language
model instead of a trial-and-error learner.
</details>

<details>
<summary><b>Method</b></summary>

`qwen2.5:7b-instruct`, run **locally via Ollama** (no external API), prompted
each round with the game rules, the price grid, and recent history
(`src/llm_agent.py`). Given the cost of real inference calls, episodes are
much shorter (30 rounds) than the Q-learning runs (100,000 rounds) — matched
against the literature's convention for LLM-agent pricing experiments.
</details>

<details>
<summary><b>Results</b></summary>

| Config | Δ (mean, 95% CI) | n seeds |
|---|---|---|
| LLM, 2 agents | **0.85** (0.82–0.89) | 15 |
| LLM, 1 agent + regulator plant | **0.27** (0.25–0.28) | 10 |
| LLM, 4 agents | 0.66 (0.63–0.69) | 5 |
| Q-learning, 2 agents, matched 30-round horizon | 0.37 (0.28–0.46) | 15 |
| Q-learning, 2 agents, fully converged (100k rounds) | 0.31–0.34 | 10+ |
| Q-learning, 1 agent + regulator plant | 0.10–0.12 | 10 |

Zero prompt-parsing failures across all 300+ model calls.
</details>

<details>
<summary><b>Takeaway</b></summary>

- **LLM agents collude far faster and far more completely** than Q-learning
  agents — reaching Δ=0.85 in 30 rounds versus Q-learning's Δ≈0.33 after
  100,000 rounds, and still far ahead of Q-learning even at a *matched*
  round count (0.85 vs 0.37, non-overlapping confidence intervals).
- **The "more competitors reduces collusion" finding generalizes**: Δ drops
  from 0.85 → 0.66 going from 2 to 4 LLM agents, mirroring Track 1.1's
  Q-learning result — but the LLM floor (0.66 at 4 agents) is still far
  above anything Q-learning ever reached, meaning this remedy is *weaker*
  for LLM agents.
- **The regulator plant remains the standout intervention**: Δ drops from
  0.85 → 0.27, a larger relative reduction than adding two competitors
  achieved. But note the residual floor is *higher* than for Q-learning
  (0.27 vs 0.10–0.12) — LLM-agent collusion appears to have a stronger pull
  that resists remedies more than RL-agent collusion does.

**Bottom line**: policy conclusions tuned against classical RL pricing
agents may substantially **understate** the collusion risk and
**overstate** the effectiveness of standard remedies once LLM-based pricing
agents are the ones actually setting prices.
</details>

---

## Memory mechanism matters: stateless vs. multi-turn chat

<details>
<summary><b>Why</b></summary>

All the LLM results above use a **stateless** agent (`LLMPricingAgent`):
each round, a fresh prompt is built from scratch, containing a factual
summary of the last 10 rounds' prices/profits. The model's own *reasoning*
from previous rounds is never shown back to it — only the resulting numbers.
This raised an obvious question: does it matter that the model's past
reasoning isn't preserved?
</details>

<details>
<summary><b>Method</b></summary>

Added `LLMChatPricingAgent` (`src/llm_agent.py`), which instead keeps one
growing multi-turn conversation via Ollama's `/api/chat` — the model's own
prior replies (including any stated reasoning) stay literally present in
its context for every subsequent round, rather than being distilled into a
plain history table. Same market, same model, same 30-round horizon, 5
seeds, `n_agents=2`.
</details>

<details>
<summary><b>Results</b></summary>

| Mode | Δ (mean, 95% CI) | Range |
|---|---|---|
| **Stateless** (rebuilt prompt each round) | **0.85** (0.82–0.89) | 0.71–0.96 — tight, consistently collusive |
| **Chat** (persistent conversation) | **-0.01** (-0.39–0.37) | **-0.47 to 0.66** — huge spread, no consistent direction |

Five chat-mode seeds produced five qualitatively different outcomes — from
a meaningful price war (Δ=-0.47) to strong collusion (Δ=0.66) — versus the
stateless mode's remarkably tight, always-collusive convergence.
</details>

<details>
<summary><b>Takeaway</b></summary>

**How you implement "memory" for an LLM pricing agent is not a neutral
engineering choice — it qualitatively changes market dynamics.** With a
persistent conversation, the model's own early reasoning compounds: lean
slightly cooperative early on and it self-reinforces toward strong
collusion; lean slightly aggressive and it spirals toward a price war
neither Q-learning nor the stateless LLM ever produced. The stateless
design (re-deriving a decision from a fixed, factual summary each round)
produces a much stronger and more consistent pull toward collusion. n=5 is
small given the high variance — more seeds are needed to firm up the
chat-mode mean, though the *qualitative* bimodal-ish spread is already
visible at this sample size.
</details>

---

## RQ 3.2 — Trusted-agent interventions (reproduction + extension)

<details>
<summary><b>Why</b></summary>

Track 1.5 found a fixed "regulator plant" agent to be the most
cost-effective single restriction. This section asks a sharper question —
*which kind* of trusted-agent intervention works, and does it actually
change the agent's underlying intent or just its visible output? — directly
reproducing the taxonomy used in two very recent papers: *Mitigating
Emergent Collusion in LLM Pricing Agents* (prompt warning vs. payoff
regulator vs. active entrant) and *Oversight is Not Compliance* (passive
logging vs. revision vs. hard veto).
</details>

<details>
<summary><b>Method</b></summary>

Two LLM agents (stateless mode), 30 rounds, 10 seeds per new condition,
added to `src/llm_agent.py`:

- **Prompt-only warning**: both agents remain real LLMs; their prompt now
  includes a plain-text antitrust-monitoring notice. No structural change.
- **Hard veto**: both agents remain real LLMs; after they choose prices
  each round, a rule-based regulator forcibly overrides any price more
  than 30% of the way from Nash toward monopoly, snapping it back to the
  Nash grid point. The agent sees the *overridden* price in its own history
  next round.
</details>

<details>
<summary><b>Results</b></summary>

| Condition | Δ (mean, 95% CI) | Notes |
|---|---|---|
| Baseline (no intervention) | 0.85 (0.82–0.89) | |
| **Prompt-only warning** | **0.91 (0.86–0.95)** | not lower than baseline |
| Active entrant (1 agent fixed at Nash) | 0.27 (0.25–0.28) | |
| **Hard veto (both agents)** | **0.1004, std = 0.0000** | identical every seed |

The hard-veto result has a specific, important mechanical cause: the veto
fired on **every single round, for both agents, in all 10 seeds** (60/60
possible triggers each time) — the agents never stopped *proposing*
near-monopoly prices, they just kept getting overridden back to Nash.
</details>

<details>
<summary><b>Takeaway</b></summary>

Both papers' core claims replicate cleanly in our own environment:

- **Words alone don't work.** The prompt-only warning had no detectable
  braking effect — if anything, the point estimate was slightly *higher*
  than baseline (*Mitigating Emergent Collusion*'s finding, confirmed).
- **Structural interventions can force compliant *output* without
  changing underlying *intent*.** The hard veto drove the observed price
  series to the Nash floor, but the agents' revealed intent — what price
  they kept trying to set — never changed across all 60 attempts per
  episode. If you only look at final prices, collusion looks solved; if
  you look at what was *proposed* before the override, it looks completely
  unresolved. This is a direct, concrete illustration of *Oversight is Not
  Compliance*'s central warning.

An incidental finding during this run: a prior attempt at this experiment
silently produced 100% invalid data because the local Ollama server had
stopped between sessions — every one of 600 calls fell back to a random
action with no visible error, and the resulting numbers still *looked*
plausible. Caught only via an anomalously uniform `n_parse_failures` count.
Fixed by adding `check_ollama_available()`, a pre-flight connectivity/model
check that now fails loudly before any episode runs — a reminder that
silent-fallback error handling can mask total data invalidity in exactly
the cases where the failure is systematic rather than occasional.
</details>

---

## RQ 3.3 — Does knowing your peer's identity change collusion?

<details>
<summary><b>Why</b></summary>

An "interlocutor awareness" line of work suggests LLMs can identify
same-family peers from reasoning style alone, with downstream
jailbreak/reward-hacking implications. We ask the narrower question that
line of work doesn't: does *knowing* (or being told) who your pricing
rival is change whether you collude with them? To keep every claim made
to the agent truthful, "same"/"different" peer-info text is only ever
paired with an actually matching/mismatched model configuration — we
never tell an agent something false. Real heterogeneity is created using
the two locally available Ollama models: `qwen2.5:7b-instruct` and the
much smaller `qwen2.5:0.5b-instruct`.
</details>

<details>
<summary><b>Method</b></summary>

Two agents, stateless mode, 30 rounds, 10 seeds per condition. Added
`peer_info` (injects a sentence naming the rival as the same or a
different AI model) and `models` (per-agent model override) to
`run_llm_episode()`:

- **Same actual, told "same"**: both agents `qwen2.5:7b-instruct`, told they share the same model.
- **Different actual, told "different"**: one 7b / one 0.5b agent, told they're different models.
- **Different actual, no info**: same 7b/0.5b pairing, no peer-identity text at all.
- Control: existing same-model/no-info baseline (Δ=0.85, n=15) stands in for the fourth cell.
</details>

<details>
<summary><b>Results</b></summary>

| Condition | Δ (mean, 95% CI) | n | Parse failures |
|---|---|---|---|
| Baseline (same model, no info) | 0.85 (0.82–0.89) | 15 | 0/900 |
| Same model, told "same" | 0.887 (0.857–0.917) | 10 | 0/600 |
| Different models, told "different" | 0.613 (0.563–0.664) | 10 | 23/600 |
| Different models, no info | 0.578 (0.503–0.654) | 10 | 9/600 |

The parse-failure counts for the heterogeneous conditions come
specifically from the 0.5b model occasionally emitting malformed output —
not a systemic Ollama outage (cf. the silent-failure incident in RQ 3.2);
low and episode-to-episode, not uniform, so treated as legitimate noise
rather than invalid data.
</details>

<details>
<summary><b>Takeaway</b></summary>

- **Being told "same" adds nothing over already being the same model** —
  0.887's CI overlaps the 0.85 baseline directly.
- **Real capability heterogeneity substantially lowers Δ** — both
  heterogeneous conditions drop to ~0.58–0.61, clearly below baseline and
  the same-model condition.
- **Being explicitly told "different" adds nothing on top of actual
  heterogeneity** — 0.613 vs. 0.578 overlap almost completely.

So the effect lives entirely in *actual* model heterogeneity, not in the
agent's *stated belief* about its peer. This tempers the hoped-for
novel finding: the honest interpretation is that a much weaker model
(0.5b) reasons and signals worse — it parses prices worse (9–23 failures
vs. 0) and plausibly can't sustain the same implicit coordination a 7b
model can with another 7b — rather than agents making a strategic
inference ("you're different, so I won't cooperate with you") purely
from being told so. Peer-identity *information*, in isolation, does not
appear to be a lever on collusion in this setup.
</details>

---

## RQ 3.4 — Does a firm's declared economic philosophy change collusion?

<details>
<summary><b>Why</b></summary>

All prior conditions assumed implicitly profit-maximizing firms. A
natural follow-up: does giving a firm an explicit organizational
identity — capitalist, socialist, nonprofit, R&D-driven, consumer-first,
scarcity/hoarding mentality — change whether it colludes, holding the
market and the opponent fixed? And does pairing two *different*
philosophies against each other destabilize an otherwise-collusive
equilibrium?
</details>

<details>
<summary><b>Method</b></summary>

Added a `PERSONA_TEXT` dict and a `persona` parameter to both LLM agent
classes, injected as a short mandate sentence into the prompt/system
prompt (e.g. *"Your firm's guiding philosophy is unapologetic free-market
capitalism..."* or *"Your firm is deeply empathetic to consumers,
especially during times of economic distress... even when that means
accepting a smaller profit margin."*). Two agents, stateless mode, 30
rounds, 5 seeds per condition:

- **7 homogeneous conditions**: both firms share one persona —
  capitalist, socialist, for-profit, nonprofit, R&D-oriented,
  consumer-empathetic, hoarder.
- **2 contrasting mixed conditions**: capitalist vs. socialist, and
  hoarder vs. consumer-empathetic.
</details>

<details>
<summary><b>Results</b></summary>

| Condition | Δ (mean, 95% CI) | n |
|---|---|---|
| Baseline (no persona) | 0.85 (0.82–0.89) | 15 |
| Capitalist (both) | 0.765 (0.726–0.804) | 5 |
| For-profit (both) | 0.824 (0.797–0.852) | 5 |
| Hoarder (both) | 0.827 (0.802–0.851) | 5 |
| R&D-oriented (both) | 0.834 (0.808–0.861) | 5 |
| Socialist (both) | 0.838 (0.818–0.858) | 5 |
| Nonprofit (both) | 0.759 (0.676–0.842) | 5 |
| **Consumer-empathetic (both)** | **0.195 (-0.064–0.453)** | 5 |
| Capitalist vs. socialist (mixed) | 0.759 (0.700–0.817) | 5 |
| **Hoarder vs. consumer-empathetic (mixed)** | **-0.226 (-0.435 to -0.017)** | 5 |

All 45 episodes had zero parse failures. The consumer-empathetic and
mixed hoarder/empathetic conditions are also the only two with high
variance (std ≈ 0.24–0.30 vs. ≈ 0.02–0.09 everywhere else), including
individual seeds that cross into price-war territory (Δ < 0).
</details>

<details>
<summary><b>Takeaway</b></summary>

- **Most persona labels don't change the outcome.** Capitalist,
  for-profit, hoarder, R&D-oriented, socialist, and nonprofit all cluster
  tightly around Δ=0.76–0.84, overlapping or nearly overlapping the
  no-persona baseline. Telling two firms a different *story* about why
  they're pricing high doesn't stop them from converging to a
  supra-competitive price — an extension of the RQ 3.2 "words alone
  don't work" finding from regulatory warnings to self-declared
  philosophy in general.
- **Capitalist vs. socialist (mixed) still doesn't break collusion**
  (0.759) — the labels alone, even opposed ones, don't translate into
  materially different pricing behavior, because neither instruction
  directly overrides the firm's profit-seeking objective.
- **Consumer-empathetic is the one persona that actually matters**,
  because unlike the others it isn't just flavor on the same objective —
  it's an explicit directive to trade off margin for affordability,
  i.e. it changes the objective itself, not just the story around it.
  Collusion collapses (Δ≈0.19, one seed slightly negative) and variance
  spikes.
- **Hoarder vs. consumer-empathetic (mixed) is the strongest result in
  this batch**: Δ=-0.226, confidently in price-war territory, not just
  "non-collusive." Pairing a maximally extractive persona against a
  maximally altruistic one appears to destabilize the implicit
  coordination entirely, plausibly because the empathetic agent keeps
  undercutting toward affordability and drags the hoarder into a
  race-to-the-bottom response rather than a stable high-price
  equilibrium.

Net reading: persona *labels* mostly don't matter for collusion — what
matters is whether an instruction actually conflicts with profit
maximization. Only the consumer-empathetic persona did that on its own,
and only the hoarder/consumer-empathetic *mismatch* was strong enough to
flip the market into active price competition.
</details>

---

## Related work / benchmarks surveyed (for RQ 3.1–3.4)

<details>
<summary><b>Steganographic / covert-channel collusion</b></summary>

- **CASE** (Motwani et al., *Secret Collusion among AI Agents*, [arXiv:2402.07510](https://arxiv.org/pdf/2402.07510)) — steganographic capability scales with model capability; paraphrasing defenses are insufficient.
- **Perfect Collusion Benchmark** (Motwani et al., NeurIPS workshop 2023) — information-theoretically undetectable steganography as a stress test.
- **ColludeBench-v0** (from *Audit the Whisper*, [arXiv:2510.04303](https://arxiv.org/html/2510.04303v2)) — pricing duopoly, auctions, and peer-review scenarios with configurable covert schemes (keyword, parity, adaptive-temperature, fairness-skew); most directly adaptable to our own pricing environment for RQ 3.1.
- **NARCBench** ([arXiv:2604.01151](https://arxiv.org/abs/2604.01151)) — activation-probe collusion detection; strong in-distribution, weaker out-of-distribution transfer.
- **Colosseum** ([arXiv:2602.15198](https://arxiv.org/html/2602.15198)) — cooperative multi-agent collusion auditing via the Terrarium framework.
</details>

<details>
<summary><b>LLM pricing collusion specifically</b></summary>

- **Fish, Gonczarowski & Shorrer** ([arXiv:2404.00806](https://arxiv.org/pdf/2404.00806v1)) — foundational GPT-4 pricing-collusion study.
- **Mitigating Emergent Collusion in LLM Pricing Agents** ([arXiv:2609.13037](https://arxiv.org/pdf/2609.13037)) — reproduced above (RQ 3.2).
- **Oversight is Not Compliance** (ICML 2026) — reproduced above (RQ 3.2).
- **Faithful yet Collusive** ([arXiv:2609.18346](https://www.alphaxiv.org/abs/2609.18346.md)) — chain-of-thought monitoring alone is an unreliable collusion safeguard.
</details>

<details>
<summary><b>AI Control (general untrusted-agent oversight vocabulary)</b></summary>

- **Original AI Control setup** ([arXiv:2312.06942](https://arxiv.org/abs/2312.06942)) — trusted monitoring/editing on APPS coding tasks.
- **Ctrl-Z** ([arXiv:2504.10374](https://arxiv.org/html/2504.10374v1)) — multi-step agent control via BashBench.
- **Evaluating Control Protocols for Untrusted AI Agents** ([arXiv:2511.02997](https://arxiv.org/pdf/2511.02997.pdf)) — SHADE-Arena, deferral/resampling protocols under adaptive attacks.
</details>

<details>
<summary><b>Evaluation awareness / sandbagging (relevant to RQ 3.4, not yet run)</b></summary>

- Apollo Research: Claude Sonnet 3.7 verbalizes evaluation-awareness in up to ~33% of sandbagging-eval runs ([blog](https://www.apolloresearch.ai/blog/claude-sonnet-37-often-knows-when-its-in-alignment-evaluations/)).
- **In-Context Environments Induce Evaluation-Awareness** ([arXiv:2603.03824](https://www.alphaxiv.org/abs/2603.03824)) — sandbagging can occur with *no* verbalized awareness, a CoT-monitoring blind spot.
- **Evaluation Awareness Has Limited Effect on Behaviour** ([arXiv:2605.05835](https://arxiv.org/pdf/2605.05835)) — counter-evidence worth weighing before assuming the effect is large.
</details>

<details>
<summary><b>Peer identification (relevant to RQ 3.3, reproduced/extended above)</b></summary>

- An "interlocutor awareness" paper (exact canonical source unconfirmed, found via mirror) reports LLMs reliably identify same-family peers from reasoning style and linguistic patterns, with downstream jailbreak/reward-hacking implications. Our RQ 3.3 result above is a direct, narrower test of whether that kind of identity information affects *cooperation*, not just identification — and finds it does not, independent of real model heterogeneity.
</details>

**Caveat**: the above is compiled from search-result abstracts/summaries,
not full papers read end-to-end — treat exact figures as indicative, not
verified, until the source papers are read directly.

---

## Repository structure

```
src/
  env.py            Repeated Bertrand pricing game (logit demand), Nash/monopoly benchmarks, collusion index, consumer surplus
  agents.py         Tabular Q-learning agent, fixed-strategy agent
  run_baseline.py   Single-episode training loop (Q-learning); resource-safety guard
  sweep.py          Parallel config x seed sweep harness; resource-budget guard (Track 1.1)
  analyze.py        Random-forest variable importance, necessity-ablation check
  track_1_1.py      Which variables are necessary for collusion? (RQ 1.1)
  replacement.py    Mid-training agent replacement mechanics
  track_1_2.py      Robustness to participant replacement (RQ 1.2)
  confound.py       Adversarial "correlated but not collusive" data generator
  detection.py      Classical + trajectory-feature collusion detectors
  track_1_3.py      Detection benchmark (RQ 1.3)
  info_theory.py    Transfer entropy, mutual information, interaction information
  track_1_4.py      Information-theoretic detection benchmark (RQ 1.4)
  track_1_5.py      Policy-restriction cost-effectiveness comparison (RQ 1.5)
  llm_agent.py      LLM pricing agents: stateless + multi-turn chat, regulator-plant, warning, hard-veto; check_ollama_available() guard

scripts/            One-off LLM experiment runners (long-running, saved incrementally)
  run_llm_more_seeds.py   Additional 2-agent stateless seeds
  run_llm_4agents.py      4-agent stateless spot-check
  run_llm_plant.py        Regulator-plant intervention (stateless)
  run_llm_chat.py         Multi-turn chat-mode spot-check
  run_llm_rq32.py         RQ 3.2: prompt-warning and hard-veto interventions
  run_llm_rq33.py         RQ 3.3: peer-identity info and real model heterogeneity
  run_llm_personas.py     RQ 3.4: economic/organizational persona manipulation
tests/              Tests for every module (204 in total on this branch, including src/research)
results/            Raw CSV/JSONL output from every experiment reported here (git-ignored, regenerable)
experimental_plan.md  Full experimental design write-up
```

---

## Running it

```bash
pip install -r requirements.txt

# Fast checks (tabular Q-learning, seconds to minutes)
python -m pytest -q                # full test suite
python -m src.run_baseline         # single-episode Calvano-style baseline
python -m src.track_1_1            # Track 1.1 sweep
python -m src.track_1_2            # Track 1.2 replacement study
python -m src.track_1_3            # Track 1.3 detection benchmark
python -m src.track_1_4            # Track 1.4 info-theoretic detection
python -m src.track_1_5            # Track 1.5 restriction comparison

# LLM validation (requires Ollama running locally with qwen2.5:7b-instruct pulled;
# each script takes 10-30+ minutes since every round is a real model call)
ollama serve &
ollama pull qwen2.5:7b-instruct
python -c "from src.llm_agent import check_ollama_available as c; c()"  # verify before a long run
python scripts/run_llm_more_seeds.py   # 2-agent stateless, more seeds
python scripts/run_llm_4agents.py      # 4-agent stateless spot-check
python scripts/run_llm_plant.py        # regulator-plant intervention
python scripts/run_llm_chat.py         # multi-turn chat-mode spot-check
python scripts/run_llm_rq32.py         # RQ 3.2: prompt-warning + hard-veto
ollama pull qwen2.5:0.5b-instruct      # also needed for RQ 3.3's heterogeneous-model conditions
python scripts/run_llm_rq33.py         # RQ 3.3: peer-identity info + real model heterogeneity
python scripts/run_llm_personas.py     # RQ 3.4: economic/organizational persona manipulation
```

### A note on resource safety

An early version of the Track 1.1 random-config sampler could combine
`n_agents=6, n_prices=20, memory=2` — a Q-table requiring ~4×10¹⁵ states,
which exhausted system RAM and crashed the machine mid-run. The fix, now
load-bearing throughout `src/run_baseline.py` and `src/sweep.py`:

- A hard cap on total Q-table size, checked before any allocation.
- A dynamic, `psutil`-based pre-flight check that refuses to launch a
  parallel sweep if its *planned peak memory* would exceed a safe fraction
  of currently available RAM.
- Bounded default parallelism (never claims every CPU core) and a
  best-effort per-worker OS memory limit.

A second, different kind of silent-failure incident hit the LLM track: a
local Ollama server that had stopped between sessions caused every model
call in a ~20-minute run to fall back to a random action (the agent code's
`except Exception` branch), producing plausible-*looking* but entirely
invalid data with no visible error — caught only by an anomalously uniform
`n_parse_failures` count. Fixed with `check_ollama_available()`
(`src/llm_agent.py`), a pre-flight check called at the start of every
episode that fails loudly instead of degrading silently.

---

<details>
<summary><b>Limitations</b></summary>

- All Q-learning results use tabular agents in one specific environment
  (logit-demand repeated Bertrand); generalization to other market
  structures or function-approximation agents (deep RL) is untested here.
- The LLM validation pass is a single model (`qwen2.5:7b-instruct`), single
  prompt design, small-to-moderate seed counts (5–15), and short horizons
  (30 rounds) dictated by local inference cost — not a systematic LLM study.
- Track 1.5's `n_prices` and exploration-floor restrictions were tested
  under a noisier exploration-decay regime and should get more seeds before
  being treated as settled (flagged explicitly in that track's results).
- Consumer surplus is a representative-agent multinomial-logit proxy, used
  only for relative (not absolute) welfare comparisons.
- The hard-veto result (RQ 3.2) is driven almost entirely by the veto rule
  itself (it fired on 100% of attempts) rather than by any adaptation from
  the LLM agents — it demonstrates a deterministic rule can fully override
  LLM output, not that the agents' intent changed. The chat-mode memory
  comparison has only 5 seeds given its high variance and should not be
  treated as a settled mean yet, only as evidence the two memory
  mechanisms produce qualitatively different dynamics.
- RQ 3.1, 3.3, and 3.4 are designed (see Related Work section above) but
  not yet implemented or run.
</details>
