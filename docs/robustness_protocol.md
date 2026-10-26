# Robustness protocol

The staged design (smoke, primary, one-factor, interactions, held-out) and its cost are in
`research/protocols/robustness_grid_v1.md`; the hypotheses, metrics, decision rules and exclusions are pre-declared
in `research/protocols/strategic_deviation_v1.md`.

Three levels of consistency are reported separately:
1. Repeatability: identical config rerun (`replicate` > 0) must give identical digit distributions under greedy
   decoding (smoke: max |dE| = 0.0).
2. Robustness: the same behaviour measured under one changed factor (template, temperature, deviation size, prefix
   length, recovery delay, economics preset, history window, steering strength).
3. Generalisation: held-out histories, template, economics preset and model sizes, analysed with the frozen
   protocol only.

The behavioural consistency grid (`research/outputs/tables/behaviour_cells.csv`, figure 14) gives each
behaviour x factor-level cell one status: supported / opposite / absent / inconclusive / insufficient, and each
behaviour one replication label: robust / mixed / not replicated / inconclusive / insufficient evidence.
