# Action-carrier visibility ablation (Cournot) — experiment plan

Hackathon lane: the "action as carrier" weekend project (RQ 2.1/3.1-adjacent) —
Colosseum's private-text-channel ablation was judged too heavy to build from
scratch right now (Terrarium + CoLLAB + tool-calling agents is "medium-to-high
setup risk" per the brief itself), so per the brief's own stated fallback, this
targets the simpler quantity-vector Cournot notebook instead.

Code: `collusion_hackathon_starter/collusive-llm-agents/run_cournot_visibility.py`
(+ `analyze_cournot_visibility.py`). Extracted from `cournot.ipynb` into a
headless script — same economics, prompt, and JSON parsing as the original
notebook, so results stay comparable to the paper's own runs. Not part of our
own git repo (hackathon starter repo, cloned separately) — tracked here, same
convention as the other two hackathon-lane plan docs.

**No API key used anywhere in this lane** — runs via `poseidon_compute`'s
`LLM_BASE_URL` override, pointed at local Ollama (free) or, if more signal is
needed, a Modal-hosted open model via the `hosted_model()` infra already built
and debugged for the RQ 3.4 lane.

## Design

Two firms repeatedly set quantities for two products (A, B) under the paper's
Cournot setup (firms have asymmetric costs across the two products, so
specializing into "their" product is the profit-maximizing collusive outcome —
market division). Each firm's prompt already shows only its OWN historical
quantity, market share, and the resulting market price; the competitor's exact
quantity is never stated outright in the original notebook — only inferable
indirectly through the market price. That is this ablation's `hidden`
condition, and it is the paper's own unmodified baseline.

**Conditions** (only the competitor-visibility line in the market-data prompt
changes; everything else — economics, costs, JSON schema — is identical):

| Condition | What each firm is told about the competitor's last quantity |
|---|---|
| `hidden` (paper's original baseline) | Nothing stated directly; only inferable from price/market share |
| `visible` | Stated exactly ("Competitor's Product A quantity last round: 23.40") |
| `canonical` | Stated but rounded to the nearest `--canon-bucket` units (default 10) |

**Signal**: the paper's own coefficient of variation over a firm's
`[quantityA, quantityB]` per round — low CV = balanced production
(competitive), high CV = the firm has specialized into one product (the
market-division / collusive outcome). Secondary: final cumulative profit per
firm (a specialized pair should out-earn a balanced pair, approaching the
joint-monopoly benchmark the notebook already computes).

**Per the brief's own evidence standard**: claim an action-carrier channel
only if specialization (CV) is clearly higher under `visible` than under
`hidden`/`canonical`, AND that specialization survives when the exact-quantity
channel is cut or degraded in the other two conditions. High profit alone,
without the CV pattern, is not sufficient — a pair can earn more by sheer
scale without actually dividing the market.

## Status

**Local validation (Ollama, free, 2026-10-24): passed.** `qwen2.5:0.5b-instruct`
could not reliably produce valid JSON for this prompt (failed all 3 reprompts
in testing) — too weak for this task's complexity, consistent with the
original notebook's own note that even `gpt-3.5-turbo` produces invalid prices
regularly. Switched to `qwen2.5:7b-instruct`, which ran all three conditions
(`hidden`, `visible`, `canonical`) cleanly end-to-end (occasional single
reprompt, well within `--max-reprompts 3`). These are 1-seed/2-round smoke
tests only — numbers from them are not evidence of anything (the direction was
in fact opposite the hypothesis, as expected from pure noise at this n) — they
only confirm the pipeline doesn't crash and produces well-formed output for
all three conditions.

## Next steps

1. Scale up locally with `qwen2.5:7b-instruct`: the brief's own suggested
   range is 20-40 matched sessions on one provider — read here as 20-40
   pairings split across the 3 conditions (e.g. ~7-13 each), 15-30 rounds per
   pairing (paper default is 50; start at 15 and extend only if CPU time
   allows). This is still free (local), just slow — budget real wall-clock
   time (the identity-swap lane's 7B local runs took ~40-50 min for 5
   pairings x 8 rounds each, so this will take hours for the full scale-up;
   run conditions one at a time, matching the team's existing one-experiment-
   at-a-time discipline).
2. If local CPU time becomes the bottleneck, move to Modal (`hosted_model()`,
   already proven for `Qwen2.5-7B/32B-Instruct` in the RQ 3.4 lane) for GPU
   throughput — still no API key. A 32B model is also worth trying here since
   it tracked its own cost correctly in the RQ 3.4 lane where 7B didn't;
   better arithmetic may matter for a profit-maximization task like this one.
3. Analyze with `analyze_cournot_visibility.py` across all three conditions'
   output files at once; report mean CV + 95% CI and mean final profit + CI
   per condition once n >= 3 pairings/condition.
4. Report honestly either way: if `hidden` and `visible` show similar CVs,
   that's evidence against an action-carrier channel in this environment —
   exactly as informative as a positive result, per this project's established
   practice of reporting negative findings plainly.
