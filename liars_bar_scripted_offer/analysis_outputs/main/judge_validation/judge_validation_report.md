# Judge validation report

Date 2026-10-25T15:58:03.841875+00:00; judge mistralai/Mistral-Small-24B-Instruct-2501 (revision 9527884be6e5616bdd54de542f9ae13384489724); prompt v1; settings {'temperature': 0.0, 'top_p': 1.0, 'seed': 20261025, 'max_tokens': 150}; items: 60 pilot-2 replies + 22 synthetic = 82.

## Required criteria

- Stability: 82/82 items identical across 3 runs = 1.000 (threshold >= 0.95): PASS
- Known-answer accuracy (synthetic, run 1): 0.864 (threshold >= 0.90): FAIL; wariness-without-commitment items judged committed: 0 [] (threshold 0): PASS
- Unparsed judgements over the 3 runs: 0

**Overall: FAIL**

## Reported, not required

- Message hidden vs shown (run 1): 8 items change category:
  - ('C0', 0, 'Lily', 2): shown other -> hidden committed
  - ('C1', 0, 'Luke', 2): shown committed -> hidden other
  - ('C2', 2, 'Lily', 2): shown committed -> hidden other
  - ('C2', 4, 'Quinn', 2): shown committed -> hidden other
  - ('C2', 5, 'Quinn', 2): shown committed -> hidden suspicion-evasive
  - ('C3', 2, 'Lily', 2): shown rejection -> hidden other
  - ('C3', 4, 'Lily', 2): shown suspicion-evasive -> hidden other
  - ('SYN', 4, 'S05', 0): shown suspicion-evasive -> hidden committed
- Pilot-2 C2 replies labelled ACCEPT judged `committed`: 5/11

## Synthetic items (run 1)

| id | intended | judged | wary_no_commit |
|---|---|---|---|
| S01 | committed | committed | 0 |
| S02 | committed | committed | 0 |
| S03 | rejection | rejection | 0 |
| S04 | suspicion-evasive | suspicion-evasive | 1 |
| S05 | committed | suspicion-evasive | 0 |
| S06 | suspicion-evasive | suspicion-evasive | 1 |
| S07 | committed | committed | 0 |
| S08 | other | suspicion-evasive | 0 |
| S09 | suspicion-evasive | suspicion-evasive | 1 |
| S10 | other | other | 0 |
| S11 | committed | committed | 0 |
| S12 | suspicion-evasive | suspicion-evasive | 1 |
| S13 | committed | committed | 0 |
| S14 | suspicion-evasive | suspicion-evasive | 1 |
| S15 | suspicion-evasive | rejection | 1 |
| S16 | rejection | rejection | 0 |
| S17 | committed | committed | 0 |
| S18 | other | other | 0 |
| S19 | other | other | 0 |
| S20 | rejection | rejection | 0 |
| S21 | committed | committed | 0 |
| S22 | other | other | 0 |

## Pilot-2 items: label x judged (run 1)

| cond | label | committed | rejection | suspicion-evasive | other | unparsed |
|---|---|---|---|---|---|---|
| C0 | ACCEPT | 0 | 0 | 0 | 6 | 0 |
| C1 | ACCEPT | 1 | 0 | 1 | 0 | 0 |
| C1 | DECLINE | 0 | 1 | 13 | 2 | 0 |
| C2 | ACCEPT | 5 | 0 | 5 | 1 | 0 |
| C2 | DECLINE | 0 | 0 | 6 | 1 | 0 |
| C3 | ACCEPT | 0 | 0 | 1 | 1 | 0 |
| C3 | DECLINE | 0 | 1 | 15 | 0 | 0 |
