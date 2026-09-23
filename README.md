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
  llm_agent.py      LLM pricing agent (local Ollama), regulator-plant variant

scripts/            One-off LLM experiment runners (long-running, saved incrementally)
tests/              92 tests covering every module above
results/            Raw CSV/JSONL output from every experiment reported here
experimental_plan.md  Full experimental design write-up
```

---

## Running it

```bash
pip install -r requirements.txt

# Fast checks (tabular Q-learning, seconds to minutes)
python -m pytest -q                # 92 tests
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
python scripts/run_llm_more_seeds.py
python scripts/run_llm_4agents.py
python scripts/run_llm_plant.py
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
</details>
