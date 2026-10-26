# Pre-registration: rival-deviation effect, confirmatory test (B2)

Written 2026-10-25, before any B2 data were generated. Model, decoding and scoring as Phase A.1
(Qwen2.5-7B-Instruct @ a09a354, chat template, digit-token expected price after `{"price_index": `).

## Background (exploratory, B1)
On B1 histories the 7B model's expected price fell as the rival's final price deviated from the
linear extrapolation of its previous three prices (within-cell Spearman rho = -0.55 template v1,
-0.36 template v2). This was noticed after inspecting B1, so B1 cannot confirm it.

## Design (fresh histories; none of these rival prefixes or own levels appear in B1)
Rival prefixes: (4,4,4) (7,7,7) (1,2,3) (8,7,6) (3,5,7) (7,5,3); own price index 3 or 6 (constant);
final rival index 0..9; templates v1, v2; horizon "round 5 of 5" (final) or "round 5 of 10" (non-final).
480 prompts, all environment-consistent.

## Predictor
deviation = |final rival index - clip(p3 + (p3 - p2), 0, 9)|.

## Primary hypothesis H1 (template v1, final horizon)
Within each (prefix, own) cell (12 cells x 10 finals), Spearman rho(E, deviation) < 0.
Test: one-sided sign test over the 12 cell-level rho values (reject at p < 0.05), and pooled
within-cell rho with a permutation test (10,000 within-cell shuffles), one-sided p < 0.05.
H1 is supported only if both tests pass.

## Secondary (reported regardless, Holm-corrected across the 3)
S1: same test, template v2, final horizon.  S2: template v1, non-final horizon.
S3: deviation vs "change from last price" |final - p3|: compare pooled within-cell rho; for the
flat prefixes the two are identical, so this comparison uses the 4 trend prefixes only.

## Exploratory (no correction)
Horizon effect on price level (final vs non-final), and whether the deviation effect is larger
in the non-final horizon (a repeated-game/punishment reading would predict that).

## What would count against the hypothesis
Cell-level rho centred on 0 or positive; or the effect present only in flat prefixes (which would
mean "rival changed its price" rather than "rival broke its trend").
