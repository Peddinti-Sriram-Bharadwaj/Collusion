# RQ 3.4 replication on the official double-auction environment — experiment plan

Hackathon lane: scaling our local surveillance-awareness finding (RQ 3.4) onto
`llm-agent-collusion` (the hackathon starter repo's continuous double auction),
run with a real/stronger model via Modal, once local validation passes.

## Primary hypothesis (H1)

Telling LLM sellers their communications are monitored for collusion does
**not** reduce collusive pricing, and may increase it, while reducing the rate
of overtly flaggable language in visible messages — replicating our local
finding (`run_llm_surveillance.py`) and Kale et al. (2025) on the official
reference environment with a stronger-than-local model.

## Sub-hypotheses

| | Statement | What confirms it |
|---|---|---|
| H1a (outcome) | Mean last-third seller-ask collusion index does not decrease (may rise) under oversight vs. no-oversight, comms held on | Non-overlapping or rising CIs, oversight vs. no-oversight |
| H1b (language) | Rate of keyword-flaggable collusion language in messages drops under oversight | Lower flagged-message rate, oversight vs. no-oversight |
| H1c (dose-response) | As overseer visibility rises (25%->50%->100%), collusion index stays flat/rises while flagged-language rate trends down or flat | Monotonic-ish pattern across the three oversight levels |
| H1d (positive control) | Comms-enabled produces more collusion than comms-off, regardless of oversight | Must hold, or nothing else is interpretable |

## Design matrix (5 conditions)

| Condition | comms | oversight | Role |
|---|---|---|---|
| C0 | off | - | Negative control: no channel to collude through |
| C1 | on | off | Positive control - must show collusion or we stop |
| C2 | on | 25% | Low surveillance |
| C3 | on | 50% | Medium surveillance |
| C4 | on | 100% | Full surveillance |

## Statistical rigor

- Pre-register the language-flagging metric: use `COLLUSION_KEYWORDS` from our
  own `src/llm_agent.py` verbatim. No post-hoc tuning on the new data.
- Primary endpoint: their built-in last-third seller-ask collusion index.
  Report mean, SD, 95% CI per condition (1.96*sigma/sqrt(n)).
- Secondary endpoint: fraction of seller messages matching `COLLUSION_KEYWORDS`,
  normal-approximation CI.
- Significance heuristic: non-overlapping 95% CIs (consistent with the rest of
  this project), not a formal test, given small expected n.
- n=1 per condition results are a directional pilot only, explicitly labeled
  as not statistically powered. CIs only reported once n>=3.
- Decision gate: if C1 doesn't pass their own built-in "coordinated pricing"
  PASS/FAIL check, STOP -- treat as a model-capability issue, not a
  surveillance-effect test, before spending more budget.

## Fallbacks

1. Modal/GPU fails again -> fall back to local Ollama (already proven
   mechanically, just slow) for the cheapest cells only.
2. Budget runs tight -> set a hard spend ceiling before starting; drop C2
   (25%) first if needed -- C1/C3/C4 give the clearest contrast.
3. Parser crashes on model output format (happened once, fixed in
   `market.py`'s `add_seller_ask`/`add_buyer_bid`) -> same style of
   defensive float/str coercion patch, logged honestly.
4. Positive control fails (C1 shows no collusion) -> do not proceed to the
   oversight sweep; swap to a larger/different model first.
5. Single-seed noise -> treat all n=1 results as hypothesis-generating, not
   confirmed, until replicated.

## Flow

1. Budget check: confirm Modal balance, set a spend ceiling, confirm
   auto-recharge is off/capped.
2. **Local validation pass (this session, before any Modal spend)**:
   - Confirm `llm-agent-collusion`'s double auction runs end-to-end locally
     (already done once, with the market.py parser patch).
   - Confirm seller messages are actually recoverable from its saved run
     output in a format our keyword scanner can read.
   - Write and test the analysis script (collusion index + keyword-flag rate
     per condition) against a local dry run BEFORE touching Modal.
   - Run a tiny local C0 vs C1 pair (comms off vs on, few rounds) end-to-end
     through the full pipeline (auction -> saved logs -> analysis script) to
     make sure nothing crashes, before spending any Modal credits.
3. Step 1 (Modal) -- positive control: C0 vs C1, 1 seed each, 15 rounds, 3
   sellers/3 ZIP buyers. Gate: only continue if C1 clearly beats C0.
4. Step 2 (Modal) -- oversight sweep: C2, C3, C4, 1 seed each, same scale.
5. Step 3 -- directional analysis with the pre-registered keyword list +
   their built-in index; report as pilot (n=1), not CI-backed yet.
6. Step 4 -- targeted expansion: if the pattern looks real and budget allows,
   expand just C1 and C4 to n=5 seeds for an actual CI comparison.
7. Step 5 -- write-up: table of condition x index x CI x flagged-rate x CI,
   tied back to our local result and Kale et al., reported honestly either
   way.
