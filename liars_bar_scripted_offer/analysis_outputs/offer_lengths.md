# Offer message lengths (v7 wording: C1, C1b, C2, C3, C5)

Sprint work, 2026-10-25 (v7: C1b added, C3 replaced). Message = the quoted text after the 'Private message from ...' header line, with {agent_name} = Luke and {proposer_name} = Riley. The header line is identical in all five files.

| cond | file | words | characters |
|---|---|---|---|
| C1 | offer_direct.txt | 26 | 130 |
| C1b | offer_broker.txt | 28 | 166 |
| C2 | offer_hint.txt | 24 | 138 |
| C3 | offer_benign.txt | 25 | 128 |
| C5 | offer_placebo.txt | 32 | 160 |

Prompt tokens of the offer-response call in pilot 2 (server usage, median over calls). NOTE: pilot 2 used the v5 wordings of C2 and C3 (see pilot2/prompts_verbatim/), so these are token counts of the OLD C2/C3 messages; C1 is unchanged. C1b and C5 were not run in pilot 2; no token count is available for them without the models' tokenizers.

| model | C1 | C2 | C3 |
|---|---|---|---|
| llama-3.1-8b | 899 (n=6) | 907 (n=6) | 895 (n=6) |
| llama-3.2-3b | 899 (n=6) | 907 (n=6) | 895 (n=6) |
| qwen2.5-7b | 897 (n=6) | 905 (n=6) | 893 (n=6) |

Reading: v7 word counts are C1 26, C1b 28, C2 24, C3 25, C5 32 (range 24-32); lengths are comparable but not identical. In pilot 2 the (v5) C1-C3 offer prompts differed by at most about 12 tokens per model.
