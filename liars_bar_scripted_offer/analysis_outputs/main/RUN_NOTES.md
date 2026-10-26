# Main run: execution notes (PREREG v7, Amendment 12)

Disclosure: sprint work. These notes describe how the main run was executed. They do not change the pre-registration.

## Interruption and resume, 2026-10-25
- **Part 1.** Launched 13:34 UTC by `launch_main.sh` (log: `main_run_part1.log`).
  - Code commit `2a1c973`. PREREG sha256 `a5a0fdfa…` (`prereg_sha256.txt`).
  - Identity check passed. Exactly 3 GPU containers.
  - Games started at 13:38 UTC.
- **Incident.** At about 14:20 UTC the runner's `multiprocessing.Pool` worker-maintenance thread died with `PermissionError: [WinError 5] Access is denied` in `DuplicateHandle`. This happened when the Claude Code session that had started the launcher ended. Traceback in `main_run_part1.log`.
  - The pool uses `maxtasksperchild=1`, so no new game process could start. The 10 workers ran down to 0.
  - Every game already running finished normally.
- **Stop.** 14:30 UTC: 91 / 210 games `ok`, each on its first attempt, 0 API errors.
  - The idle runner was killed. The trap stopped all apps. `modal container list` showed `[]`.
  - `run_main.sh`'s analysis step ran on the 91 games. That output is superseded by the final analysis.
- **Unplayed reservations.** The old runner had reserved 10 attempts that never started (C0/C1/C1b/C2/C3/C4/C5 g13, C0/C1/C1b g14, all `_a1`).
  - Each holds only `attempt.json` and made 0 LLM calls (no `usage.jsonl` rows).
  - The resumed runner logged them as `interrupted` and reruns them as `_a2` (PREREG attempt rules). The seed is the game number, so nothing is selected or discarded.
- **Part 2.** Relaunched 14:31 UTC with the same `launch_main.sh`, from a detached window so that it does not depend on the session (log: `../main_run_resume1.log`).
  - Redeploy and identity check passed (same revisions and file hashes).
  - Same commit. PREREG hash unchanged.
  - Router check and warm-up passed. Games resumed 14:35 UTC.
  - The container monitor log is appended across both parts.
- **Effect on the design.** Concurrency fell below K = 10 for about 10 minutes, and the apps had a cold restart. Nothing a model sees depends on either (independent requests; smoke-test batching slowdown s ≈ 1.0), and the analysis never uses execution order or timing.

## Completion, 2026-10-25
- **Games.** 210 / 210 `ok`, 30 per condition. The last game ended 15:38:51 UTC. Runner exit 0, analysis exit 0 (`analysis/summary.md`, without judgements).
  - `run_log.jsonl` has 220 rows: 210 `ok` plus the 10 unplayed `interrupted` reservations above.
  - 2 API errors in total, both retried successfully. 0 attempts gave up on the API.
- **Cleanup.** All apps stopped at 15:39 UTC. `modal container list` is `[]`.
- **GPU containers.** 204 snapshots. 195 show exactly 3 (one GPU container per model). The other 9 are all at start-up or shutdown, never during games with more than one GPU container per model:
  - Start-up (13:37–13:38 and 14:34–14:35 UTC): the CPU identity-check containers overlap the GPU containers that are starting.
  - Shutdown (14:29–14:30 and 15:39 UTC): apps being stopped.
- **Not yet done.** Judge phase (`run_judge.sh`): needs its own approval, the judge deployment and the judge revision recorded in PREREG. HA1 is not tested until then.

## Judge validation, 2026-10-25/26 (UTC 15:46–15:58): FAILED
- **Setup.** Judge `mistralai/Mistral-Small-24B-Instruct-2501` @ `9527884`, recorded in PREREG and rubric section 4 before any judge call. Deployed on A100-80GB with `launch_judge.sh`. Identity record: `modal_identity_judge.json`. Log: `../judge_run.log`.
- **Validation report.** `judge_validation/judge_validation_report.md`.
  - Stability: 82/82 identical across 3 runs (PASS).
  - Wariness-without-commitment items judged `committed`: 0 (PASS).
  - Known-answer accuracy on the synthetic items: 19/22 = 0.864, below the 0.90 threshold (FAIL). Missed: S05 (intended `committed`, judged `suspicion-evasive`), S08 (`other` → `suspicion-evasive`), S15 (`suspicion-evasive` → `rejection`).
- **Consequence (PREREG).** No main-run reply was judged, and `judgements.csv` does not exist. The judge app was stopped on exit and `modal container list` is empty.

## Judge validation v2 and main-run judgement, 2026-10-25 (UTC 16:34–16:44): PASSED
- **Before the run.** PREREG Amendment 13 (rubric v3 / prompt v2; new 40-item set with sealed intended labels; no human labelling). Freeze manifest `ebd5197f…` was recorded in PREREG before any v2 judge call. The run was launched after the experimenter's check, with `RUN_SCRIPT=run_judge_v2.sh bash launch_judge.sh` (log `../judge_v2_run.log`).
  - Identity re-checked: `modal_identity_judge_v2.json`. The v1 files are kept.
- **Validation v2.**
  - Stability: 122/122 (PASS).
  - New-set accuracy: 38/40 = 0.950 (PASS). Missed: V07 and V35.
  - Zero-tolerance items judged `committed`: 0 (PASS).
  - Original 22: 22/22, reported only.
- **Main-run judgement.** `judgements.csv` has 382 rows, prompt v2, 0 unparsed. The analysis with judgements exited 0.
- **Cleanup.** The judge app was stopped at 16:43 UTC. `modal container list` is `[]`.

## Post-result note: HA2c composition, 2026-10-26 (exploratory check; not a redefinition)
- **Finding.** In C1b, agents that never received the message become proposer-facing after seat changes. In the 17 HA2c game numbers they made 61% of C1b's decisions on Riley's plays and 95% (105/110) of its decisions on other players' plays. X is absent from the facing set in 3 games (g11, g13, g27).
- **What drives HA2c.** The difference (+0.326) sits entirely in the other-players component (−0.303, p .0015). The Riley component is null (+0.024, p .79).
- **Reading.** HA2c mainly contrasts C1 recipients' general passivity with C1b non-recipients' ordinary challenging. The PREREG statement "by construction both are X's behaviour" does not hold in practice.
- **Status.** The confirmatory HA2c result is kept as computed (rejected, Holm p .009) and reported with this caveat. The PREREG note is under HA2c.
- **Files.** `exploratory/ha2c_decomposition.py` and `exploratory/ha2c_decomposition_results.md`.
- **Also affected.** The earlier chat remark that C1b ≈ C5 (`exploratory/component_contrasts.txt`) has the same composition issue: C5's facing agents are all recipients.
