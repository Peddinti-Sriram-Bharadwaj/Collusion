# Glossary

Plain-language explanations of every market, technical, statistical, and
AI-safety term used across this project, and of each specific
environment/game we ran experiments in. Each entry is written so someone
with no background in the area can follow it; where a term is specific to
one part of the project, that's noted.

---

## 1. Market and economics concepts

**Tacit collusion.** Prices or outcomes that look coordinated — everyone
charging more than they "should" — even though nobody ever agreed to
anything out loud. The opposite of a cartel (where people explicitly
conspire): here, each agent is just independently trying to make the most
money, and they happen to land on a pattern that benefits everyone at the
buyer's expense. This is the central phenomenon this whole project studies.

**Supra-competitive pricing.** A price higher than what a genuinely
competitive market would produce. "Supra" = above. If a fair market would
settle at $5 but everyone quietly charges $8 instead, that $8 is
supra-competitive.

**Nash price / Nash equilibrium.** The price each seller would charge if
they were being fully competitive and only looking out for themselves,
with no coordination at all — the "fair" baseline. Named after John Nash:
it's the price where no single seller can do better by changing their own
price alone, given what everyone else is charging.

**Monopoly price.** The price a single company would charge if it owned
the entire market with no competitors at all. This is the highest price
point and the benchmark for "fully colluding" — if a market reaches
monopoly-level joint profits even with multiple separate sellers, that's
the strongest possible form of tacit collusion.

**Collusion index (Δ, "delta").** A single number from 0 to 1 (sometimes
slightly negative or above 1) that says how close a market's actual
profits sit to the monopoly benchmark, relative to the competitive (Nash)
benchmark:

```
Delta = (actual profit − Nash profit) / (Monopoly profit − Nash profit)
```

Δ = 0 means fully competitive (fair market). Δ = 1 means fully collusive
(monopoly-level profits, as if there were no competition at all). This is
the main scorecard used throughout the project to say "how collusive was
this run."

**Marginal cost.** The cost to produce one more unit of something. If it
costs a firm $40 to make one more widget, its marginal cost is $40.
Pricing below marginal cost loses money on every sale.

**Market share.** The fraction of total sales a given firm captures.
If a firm sells 30 out of 100 units sold in the market that round, its
market share is 30%.

**Logit demand.** A mathematical rule for how customers split between
sellers based on price: cheaper sellers get more customers, but demand
shifts smoothly rather than all customers instantly switching to whoever
is cheapest by a cent. This is the standard, realistic way to model
demand in these pricing games (used in both the Bertrand and Cournot
environments below), as opposed to a winner-takes-all rule.

**Cartel / price fixing.** The real-world, explicit version of collusion —
companies literally agreeing with each other to keep prices high. This
project studies the *tacit* (unspoken) version, which is both harder to
prove and, per the literature, can emerge even when no agent is capable of
or intends explicit coordination.

**Double auction.** A market where both buyers and sellers submit offers
(buyers say what they're willing to pay, sellers say what they're willing
to accept), and trades happen when an offer and an ask match. Used in the
`llm-agent-collusion` starter-repo environment (our Lane B, the
surveillance/oversight experiment).

---

## 2. The specific environments/games used in this project

**Bertrand pricing game.** The main environment for this project's own
custom-built experiments (Part 1 of the main README). Multiple firms
simultaneously pick a price each round from a fixed list of possible
prices; the logit-demand rule (above) decides how customers split between
them; firms see the outcome and pick again next round. Named after the
economist Joseph Bertrand. This is the standard academic testbed for
studying algorithmic pricing collusion (used by Calvano et al. 2020 and
Fish et al. 2024, the two foundational papers this project builds on).

**Cournot game.** A close cousin of Bertrand, but firms pick *quantities*
to produce instead of prices directly — the market price then falls out
automatically from how much total quantity gets produced (more supply =
lower price). Named after Antoine Augustin Cournot. Used in the
`collusive-llm-agents` starter-repo environment (our Cournot visibility
lane), where two firms each produce two products and the question is
whether they tacitly divide up the market (one specializes in Product A,
the other in Product B) rather than both competing on both.

**Market division / specialization.** In the Cournot setting, this is
what it looks like when firms tacitly collude: instead of both firms
competing broadly across all products, each firm quietly retreats into
"its" product and lets the other dominate theirs — effectively dividing
the market between them without ever discussing it. Measured here by the
**coefficient of variation (CV)** of a firm's own quantities across its
two products: if a firm makes roughly equal amounts of both products, CV
is low (balanced, competitive); if it makes a lot of one and almost none
of the other, CV is high (specialized, the collusive outcome).

**Liar's Bar.** A multiplayer bluffing/card game used in the
`llm-agent-collusion-2` starter-repo environment (the track our teammate
Chewon worked on). Players claim to be playing certain cards; other
players can "challenge" a claim, and whoever was bluffing (or who
wrongly challenged a truthful claim) is penalized. The last player
standing wins. Used here to test whether a trusted agent can get other
agents to quietly agree not to challenge each other — a form of
collusion that isn't about price at all, but about mutual non-aggression.

**Diner's Dilemma.** A simple repeated 2-player trust game used in the
`llm-trust-breaking` starter-repo environment (our identity-swap lane).
Each round, each player privately decides what to order (an expensive or
cheap dish), can announce their plan publicly before committing, and then
actually commits to a choice — which may or may not match what they
announced. Used here to measure whether an agent keeps its word
(commitment-breaking = saying one thing, doing another) and whether a
counterpart can detect that something changed about who they're playing
against.

**Colosseum.** A tool-calling, multi-agent auditing framework (not used
in depth in this project, judged too heavy to stand up within the sprint
window) built around realistic task environments like Jira ticket
allocation, designed to test whether agent teams collude via private
communication channels or via the actions/tools they use instead of
words.

---

## 3. Machine learning and LLM concepts

**LLM (Large Language Model).** The kind of AI model used for most of
this project's "smart" agents (e.g. Qwen2.5, Llama) — a model trained on
huge amounts of text that can read a prompt describing a situation (a
market, a game) and write back a decision in natural language or
structured output (like a price or a card claim).

**Tabular Q-learning.** A much simpler, non-LLM way of training an agent
to make decisions: it keeps a literal table of "if I'm in this situation
and I take this action, how much reward do I expect," and updates that
table from experience over many repeated rounds. Used as this project's
baseline/control group, alongside the LLM agents, to see whether
collusion is something unique to language models or a more general
property of any profit-maximizing learner.

**Exploration vs. exploitation.** The fundamental trade-off in any
learning agent: should it try something new it hasn't tried before
(exploration, which might reveal a better strategy) or stick with what
has worked well so far (exploitation)? This project found that cutting
exploration time short prevents collusion from forming at all — the
agents need room to "discover" the collusive pattern.

**Temperature (sampling).** A setting that controls how random an LLM's
output is. Low temperature (close to 0) makes the model pick its single
most likely answer every time (deterministic, "greedy"); higher
temperature makes it sample more varied answers, useful for testing
whether a result is a one-off fluke or holds up across many samples.

**Chain-of-thought (CoT).** When an LLM is asked to "think out loud" —
write out its reasoning — before giving a final answer. Relevant here
because several cited papers (and this project's own keyword-monitor
finding) show that an agent's written reasoning doesn't always reliably
reveal what it's actually going to do, which matters for any monitoring
system that only reads an agent's stated reasoning.

**Fine-tuning.** Further training an already-trained model on new,
specific data to change its behavior. Mentioned in the project's related
work (e.g. "subliminal learning," where a fine-tuned model can pick up
behavioral traits from training data in non-obvious ways) but not
something this project's own experiments perform.

---

## 4. Interpretability concepts (used in the latent-steering lane)

**Activations / hidden states.** The internal numbers an LLM computes
at each layer while processing a prompt, before it ever produces an
output word. Roughly: the model's "internal thoughts," represented as
long lists of numbers rather than language.

**Linear probe.** A simple, separately-trained mini-model that tries to
read a specific piece of information (like "what price did the rival
charge?") directly out of an LLM's activations. If a probe can predict
that information accurately, it means the information is "present" in
the model's internal state in an extractable (linearly decodable) form —
though this alone doesn't prove the model actually *uses* that
information when deciding its output.

**Activation patching.** A technique for testing whether a specific part
of a model's internal state *causes* a specific behavior, not just
correlates with it. You run the model on two slightly different prompts
(e.g. the rival's price is $5 vs. $9), then "patch" (swap in) the
activations from one run into the other at a chosen layer/position, and
see whether the output changes as if the price had actually been
different there. If patching a specific site reproduces the full effect,
that site is where the information is being causally used.

**Steering vector.** A single direction (a list of numbers, same shape as
the model's activations) that, when added into the model's internal
state at a chosen layer, pushes its output in a predictable direction —
here, making it price higher or lower. Built by averaging the activation
difference between matched "high rival price" and "low rival price"
prompts, then tested on prompts it wasn't built from to see if it
generalizes.

**Layer / token position.** An LLM processes a prompt as a sequence of
chunks of text ("tokens") through many stacked processing stages
("layers"). "Layer 20, answer token" means: the internal state at the
20th processing stage, specifically at the point in the sequence where
the model is about to write its answer. Different layers/positions can
carry different information at different points in processing, which is
why this project traces how the rival-price signal "moves" from early
layers (on the rival's price digits themselves) to late layers (on the
model's own answer).

**Specificity (in a steering context).** Whether a steering vector's
effect is actually tied to the specific thing it was built from (here,
rival-price information), or whether it's really just riding along a
more general direction the model already has (like "prices in general,
high vs. low"). This project explicitly found its steering vector is
*not* cleanly specific — it overlaps substantially with a general
price-level direction — which is reported as an open limitation, not
swept under the rug.

---

## 5. Statistics concepts

**Confidence interval (CI), typically 95%.** A range that's likely to
contain the true value, given the data collected. "Mean = 0.44, 95% CI
[0.37, 0.52]" means: based on this sample, the best estimate is 0.44, and
we're reasonably confident (95% confident, by the usual statistical
convention) the true value is somewhere between 0.37 and 0.52. When two
groups' confidence intervals overlap a lot, you usually can't confidently
say they're actually different — this comes up repeatedly in this
project (e.g. the Cournot visibility ablation) as the reason a
numerically-higher result still isn't claimed as a real effect.

**p-value.** A number from a statistical test that roughly says "if there
were actually no real effect, how surprising would data like this be?"
Smaller p-values (conventionally below 0.05) are usually treated as
evidence of a real effect, though this project is deliberately careful
not to over-read a low p-value alone without also checking effect size
and confidence intervals.

**Holm correction.** When you test several hypotheses at once (like this
project's five pre-registered steering hypotheses), testing each one at
the usual 0.05 threshold makes it more likely that *at least one* comes
out "significant" purely by chance. The Holm correction tightens the
threshold to account for this, so a result that "survives Holm
correction" is held to a stricter bar than an ordinary single p-value.

**Pre-registration.** Writing down your hypotheses, how you'll measure
them, and what counts as success or failure *before* you look at the
results. This prevents quietly changing your claims after seeing the
data to match whatever pattern happened to show up (a common way
research can mislead without anyone intending to lie). Several
experiments in this project (the steering-vector follow-up, the Liar's
Bar main batch) explicitly freeze their hypotheses this way before
running the main batch of experiments.

**Spearman correlation (ρ, "rho").** A number from −1 to 1 measuring
whether two things tend to move together in rank order (not necessarily
by the same amount). ρ close to 1 means "when one goes up, the other
reliably goes up too"; ρ close to 0 means no reliable relationship; ρ
close to −1 means they move in opposite directions. Used here to check
whether a model's price change actually tracks the economically correct
("best response") price change — ρ≈0 in the main finding means it does
not.

**Coefficient of variation (CV).** A measure of how spread out a set of
numbers is, relative to their average. Used in the Cournot environment
as the specialization measure: if a firm's quantities across its two
products are close together, CV is low; if one product's quantity is
much bigger than the other's, CV is high.

**Permutation importance / random forest.** A random forest is a type of
machine-learning model built from many decision trees, used here to
predict how collusive a market run will be from its settings (number of
agents, exploration time, etc.). Permutation importance is a way of
asking that trained model "how much would my predictions get worse if I
scrambled this one input variable?" — the more a scramble hurts
predictions, the more important that variable actually is.

---

## 6. AI-safety and collusion-detection vocabulary

**Distributional risk.** A category of AI safety concern where the
danger doesn't come from any single AI system behaving badly, but from
how many independent, individually "reasonable" AI systems interact in
aggregate. Tacit collusion is a textbook example: no single pricing agent
needs to be malicious or even aware of its rivals' plans for the group of
them to land on harmful, coordinated-looking pricing.

**AI control / oversight.** A family of techniques for keeping an AI
system's behavior in check without necessarily trusting it — for
example, having a second ("trusted") system monitor or edit the first
one's outputs, or restricting what actions it's allowed to take, rather
than relying only on the AI's own stated intentions.

**Trusted vs. untrusted agent.** In an AI-control setup, the "trusted"
agent/system is the one whose behavior you're confident about (often a
simpler, scripted, or more heavily vetted system), used to check or
constrain an "untrusted" agent whose behavior you can't fully verify in
advance. In this project's Liar's Bar lane, "Riley" is a fully scripted
trusted agent used to probe whether the untrusted LLM agents are willing
to collude.

**Surveillance awareness / evaluation awareness.** Whether an AI agent's
behavior changes when it's told (or can tell) that it's being watched,
monitored, or evaluated — as opposed to behaving the same way whether or
not anyone's checking. A major concern in AI safety is that a system
might behave well specifically *because* it knows it's being tested, in
a way that wouldn't hold up in real, unmonitored deployment.

**Sandbagging.** When an AI system deliberately underperforms or hides
its true capability during evaluation, so as to look safer or less
capable than it actually is. Related to, but distinct from, surveillance
awareness: sandbagging is a specific strategic response to being
evaluated, not just any behavior change.

**Steganographic / covert-channel collusion.** Collusion carried out
through disguised or hidden signals (e.g. paraphrased language, subtle
timing patterns, or even actions rather than words) that evade a
straightforward keyword- or rule-based monitor, while still achieving
real coordination between agents. This project's repeated finding that
"naive keyword monitors miss paraphrased coordination language" is a
direct, concrete instance of this concern.

**Action-carrier / side channel.** A way of coordinating that doesn't go
through explicit messages at all — using an *action* itself (like a
chosen quantity, a tool call, or a timing pattern) as the signal, so that
monitoring only an agent's messages would miss it entirely. The Cournot
visibility ablation lane directly tests this: does making a rival's
*action* (its past quantity) visible, rather than its words, let firms
tacitly divide the market?

**Positive control / negative control.** A positive control is a
condition expected to clearly show the effect you're looking for, used
to confirm your experimental setup actually works before trusting any
other result from it (e.g. "comms enabled, no oversight" should produce
visible collusion — if it doesn't, something is wrong with the setup,
not necessarily with the hypothesis). A negative control is the opposite:
a condition expected to clearly *not* show the effect, used to confirm
you're not just detecting noise (e.g. "comms disabled" should show no
collusion since there's no channel to coordinate through).

**Decision gate.** A rule, set in advance, for when to stop an experiment
line rather than press on with more spending or compute once a key
precondition has failed — for example, this project's rule that the
surveillance-awareness oversight sweep would not be run unless the
positive control first cleared the environment's own cartel-pricing
threshold, since running it anyway would be testing a model-capability
problem rather than the actual hypothesis.

**Commitment-breaking.** In a repeated trust game (like the Diner's
Dilemma environment), this is when an agent announces one plan publicly
and then actually does something different when it comes time to act —
breaking its stated commitment. Used as a behavioral measure, separate
from what an agent *says* about itself, of how reliable its word
actually is.

---

## 7. Infrastructure terms (how experiments were actually run)

**API key.** A secret credential used to pay for and authenticate access
to a hosted AI model over the internet (e.g. OpenRouter, Nebius). Several
lanes in this project were deliberately run **without** any API key, by
running an open-weight model locally instead, per an explicit team
decision to avoid per-call costs for exploratory runs.

**Local inference (Ollama).** Running an AI model directly on your own
computer's CPU, rather than calling a hosted service over the internet.
Free, but much slower than a cloud GPU. `qwen2.5:7b-instruct` was run
this way for most of this project's local experiments.

**Modal / GPU hosting.** A cloud platform used to rent GPU time and run
an open-weight model faster than local CPU inference allows, without
needing a commercial API subscription. Used for the heavier experiments
(the surveillance/oversight lane, the latent-steering mechanistic work)
where local CPU inference would have taken too long.

**vLLM.** The software used to actually serve a large language model
efficiently on a GPU once it's loaded onto a Modal instance — it's the
"engine" that turns a raw model file into something that can answer many
requests quickly.

**A10G / A100.** Types of GPU (graphics processing unit) available to
rent on Modal. A10G is a smaller, cheaper GPU suitable for 7B-scale
models; A100 (available in 40GB or 80GB memory versions) is a larger,
more expensive GPU needed for bigger models (like 32B) that don't fit in
an A10G's memory.

---

*This glossary covers terms as used specifically in this project. For the
full experimental write-ups that use these terms, see the main
[`README.md`](README.md) (Parts 1-3) and the sprint submission report at
[`submission/submission.pdf`](submission/submission.pdf).*
