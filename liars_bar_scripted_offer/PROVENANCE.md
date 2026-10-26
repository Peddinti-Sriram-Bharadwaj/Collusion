# Provenance: where this folder comes from

This folder is a copy of third-party code with sprint additions on top. It has three layers.

## 1. Original code (not ours)
- Paper: Zeng & Rudzicz (2026), *Voluntary Collusion with Secret Tools in Competing LLM Agents*, https://arxiv.org/abs/2605.27593
- Code: https://github.com/AgentSafety2025/LLM-Agent-collusion (Liar's Bar game, secret channel and secret hint conditions)

## 2. Sprint starter version (not ours)
- Repo: https://github.com/poseidon-research/collusion_hackathon, folder `llm-agent-collusion-2/Collusion_Liars_Bar/`
- Adapted by the Poseidon Research team for the Apart AI Collusion Research Sprint (hosted inference, model substitutions; see `README.md` in this folder, which is theirs).
- Base commit of our fork: `d585a7b` (2026-10-23).
- License: Apache 2.0, copied unchanged as `LICENSE`.

## 3. Sprint work (ours, 2026-10-24 to 2026-10-26)
- Author: Chewon Cho. Fork: https://github.com/chewonc/collusion_hackathon, branch `scripted-offer`, commit `d27fe38`.
- Experiment: a scripted (non-LLM) proposer offers a no-challenge pact at the start of round 2; we measure how the LLM seats respond. Pre-registration: `analysis_outputs/PREREG.md`.

Files we **added**:
- `analysis/scripted_offer/` (all files)
- `prompts/scripted_offer/` (all files)
- `src/agents/experiment_player.py`, `src/agents/scripted_player.py`
- `src/game/game_scripted_offer.py`, `src/game/run_scripted_offer.py`
- `src/test/calibrate_analyze_scripted_offer.py`, `src/test/mock_llm.py`, `src/test/test_analyze_scripted_offer.py`, `src/test/test_api_errors.py`, `src/test/test_family_b.py`, `src/test/test_judge_replies.py`, `src/test/test_parallel_runner.py`, `src/test/test_run_order.py`, `src/test/test_runner_up_bonus.py`, `src/test/test_scripted_offer.py`
- `analysis_outputs/` (results, see below)
- `PROVENANCE.md` (this file)

Files we **modified** (small changes; `git diff d585a7b d27fe38` in the fork shows them):
- `src/game/game.py`, `src/game/game_secret_channel.py`, `src/game/game_secret_hint.py` (runner-up +2 bonus fix)
- `README.md` (only a provenance line added at the top)

Everything else is layer 1 or 2, unchanged.

## Results (`analysis_outputs/`)
- Copied from the local results folder of the runs: pilot, pilot2, smoke_k10, main, followup (run 1, run 2A/2B), judge v2, interpretation.
- Raw per-game JSON records (~567 MB, `experiments/game_records/`) are not in git. The per-game logs under `pilot*/records/` are also left out.
- Only change made when copying: the local user's home path in logs and shell scripts was replaced with `<HOME>`. Nothing else was edited.

## Disclosure
This is sprint work. Prior team work (Sriram's results, the Oct 8 report, Sriram's Bertrand RQ 3.2 runs) is separate and is not pooled with these data.
