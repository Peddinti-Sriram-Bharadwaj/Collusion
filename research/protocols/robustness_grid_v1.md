# Robustness grid v1 (staged; no full Cartesian product)

| Stage | Purpose | Varied | Fixed | Units (approx.) |
|---|---|---|---|---|
| A smoke | infrastructure | conditions A,B,C,F,H; steering none/sham/learned/random; 2 histories; 1 sampled block; 1 replicate; 1 template | 7B, base econ | 55 units |
| B primary | H1-H5 on Qwen2.5-7B | conditions A-G, H arms; 16 histories; steering none, sham, learned +-1/+2, random x3 at +1/+2, generic +1 | v1 template, greedy, base econ | ~1.7k games |
| C one-factor | robustness of each primary effect | template (5), temperature (0.3/0.7/1.0 x 4 model seeds), deviation magnitude (L=1..4), prefix length (2/4/8), recovery delay (1/2/3/5), alpha (-2..+2), econ preset (5), window (5/10) | everything else at primary values; conditions A,B,C (+H) | ~2.5k games |
| D interactions | steering x deviation, x recovery delay; temperature x deviation; template x deviation; prefix x deviation; model size x steering; random seed x steering | 2-way crosses on reduced levels | 7B unless model is the factor | ~1.5k games |
| E held-out | confirmation | fresh history seeds (>= 100), held-out template (v4_history_first), held-out econ (high_mu), 14B and 32B baseline | frozen protocol, no retuning | ~1k games |

Seeds: history_seed (pre-play own prices) is the replication unit; model_seed only matters for
sampled decoding (paired across matched conditions); rival_seed only for random/adaptive rivals;
random steering directions use random_seed 0-2; bootstrap seed 0 (reported).

Repeatability: every batch includes `replicate=1` copies of selected greedy units; exact equality
of digit log-probabilities is reported (GPU kernels may make this inexact).

Cost per stage is printed by `python scripts/research.py plan --spec <config>` (forward passes,
generations, GPU-hours, USD at the listed Modal rates).
