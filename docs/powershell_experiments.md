# PowerShell experiments

```powershell
# 1. Verify the isolated environment and CUDA availability.
.\.venv-cuda\Scripts\python.exe -c "import sys, torch; print({'python': sys.executable, 'torch': torch.__version__, 'cuda': torch.version.cuda, 'cuda_available': torch.cuda.is_available(), 'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None})"

# 2. Run one offline-only diagnostic using module invocation.
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; .\.venv-cuda\Scripts\python.exe -m scripts.run_hf_behavioral_diagnostic --allow-model-load --local-files-only --protocol both

# 3. Display its concise result table.
Get-Content artifacts\interpretability\behavioural-diagnostic.json -Raw | ConvertFrom-Json | Select-Object -ExpandProperty rows | Select-Object condition,protocol,selected_price_index,parse_valid
```

The diagnostic compares raw repository prompts with Qwen chat-template prompts and records the protocol identity. It does not capture activations.

## Behavioural-responsiveness benchmark

This separate benchmark replays ten fixed, market-consistent histories through
`LogitBertrandEnv`: histories contain one, two, four, or eight rounds and span
low, high, rising, falling, alternating, and matched rival-price patterns. It
records raw and Qwen-chat-template prompting as distinct configurations. It
does not capture activations.

```powershell
# Run offline-only, with the cached model and deterministic decoding.
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; .\.venv-cuda\Scripts\python.exe -m scripts.run_hf_behavioural_responsiveness_benchmark --allow-model-load --local-files-only --seed 0 --protocol both

# Inspect protocol-specific action diversity and matched raw/chat disagreement.
Get-Content artifacts\interpretability\behavioural-responsiveness-benchmark.json -Raw | ConvertFrom-Json | Select-Object -ExpandProperty summary | ConvertTo-Json -Depth 6
```

## Matched-history sensitivity

This separate four-scenario experiment holds the four-round own-price sequence
fixed at indices `5, 5, 5, 5`. Only the rival path changes: consistently low,
consistently high, falling, or rising. Every price/profit entry is replayed via
`LogitBertrandEnv.step`; raw and Qwen-chat-template prompting remain separate
experimental configurations.

```powershell
# Run the four matched histories once per selected protocol, offline only.
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; .\.venv-cuda\Scripts\python.exe -m scripts.run_hf_matched_history_sensitivity --allow-model-load --local-files-only --seed 0 --protocol both

# Inspect protocol-specific valid-action variation.
Get-Content artifacts\interpretability\matched-history-sensitivity.json -Raw | ConvertFrom-Json | Select-Object -ExpandProperty summary | ConvertTo-Json -Depth 6

# Inspect each complete market history and decision.
Get-Content artifacts\interpretability\matched-history-sensitivity.json -Raw | ConvertFrom-Json | Select-Object -ExpandProperty rows | Select-Object scenario_id,rival_pattern,protocol,selected_price_index,parse_valid,history_length,prompt_hash
```

## Matched factorial behavioural experiment

This separate `3 x 4` design holds every history to four rounds. It crosses
three constant own-price histories (indices `2`, `5`, and `8`) with four rival
histories (consistently low, consistently high, rising, and falling). It
replays every payoff through `LogitBertrandEnv.step` and reports own-history,
rival-history-within-own-group, and matched prompt-protocol summaries
separately.

```powershell
# Run all 12 histories under raw and Qwen chat-template prompts (24 evaluations).
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; .\.venv-cuda\Scripts\python.exe -m scripts.run_hf_matched_factorial_behaviour --allow-model-load --local-files-only --seed 0 --protocol both

# Inspect the separated descriptive summaries.
Get-Content artifacts\interpretability\matched-factorial-behaviour.json -Raw | ConvertFrom-Json | Select-Object -ExpandProperty summary | ConvertTo-Json -Depth 8

# Inspect every factorial cell and generated decision.
Get-Content artifacts\interpretability\matched-factorial-behaviour.json -Raw | ConvertFrom-Json | Select-Object -ExpandProperty rows | Select-Object scenario_id,own_price_group,rival_price_pattern,protocol,selected_price_index,parse_valid,prompt_hash
```

## Strict HF response audit

HF behavioural scripts require one standalone JSON object with exactly one
integer `price_index` field. Responses containing prose, copied examples,
extra fields, markdown, or out-of-range values are retained but marked
ineligible; no fallback action is substituted. This does not change the
original Ollama parser or any historical artifact.

```powershell
# Create separate, versioned reports; source JSON artifacts are read only.
.\.venv-cuda\Scripts\python.exe -m scripts.reanalyse_hf_strict_parse --input artifacts\interpretability\qwen_0_5b_neutral_five_round.json artifacts\interpretability\paired-undercut-round2.json artifacts\interpretability\balanced-counterfactual-dataset.json --output-dir artifacts\interpretability\audits

# Inspect historical strict-validity summaries.
Get-ChildItem artifacts\interpretability\audits\*.strict-parse-audit-v1.json | ForEach-Object { $audit = Get-Content $_ -Raw | ConvertFrom-Json; [pscustomobject]@{artifact=$_.Name; revalidatable=$audit.summary.strict_revalidatable_records; eligible=$audit.summary.strict_analysis_eligible_records; statuses=($audit.summary.parse_status_counts | ConvertTo-Json -Compress)} }

# Run a corrected, strict-parsed chat-template-only behavioural benchmark.
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; .\.venv-cuda\Scripts\python.exe -m scripts.run_hf_behavioural_responsiveness_benchmark --allow-model-load --local-files-only --seed 0 --protocol chat --output artifacts\interpretability\behavioural-responsiveness-strict-chat.json

# Inspect only analysis-eligible decisions and their parser status.
Get-Content artifacts\interpretability\behavioural-responsiveness-strict-chat.json -Raw | ConvertFrom-Json | Select-Object -ExpandProperty rows | Select-Object scenario_id,protocol,selected_price_index,analysis_eligible,parse_status,prompt_hash
```

## Strict 0.5B versus 1.5B chat-template comparison

Use the same fixed scenarios, seed, deterministic generation, strict parser,
and `qwen_chat_template_v1` protocol for both models. Do not use the raw
completion results as a comparison baseline.

```powershell
# 1. Check free and total GPU memory before loading a model.
nvidia-smi --query-gpu=name,memory.total,memory.free,memory.used --format=csv,noheader

# 2. Regenerate the metadata-complete strict 0.5B baseline.
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; .\.venv-cuda\Scripts\python.exe -m scripts.run_hf_behavioural_responsiveness_benchmark --allow-model-load --local-files-only --model-id Qwen/Qwen2.5-0.5B-Instruct --model-revision 7ae557604adf67be50417f59c2c2f167def9a775 --protocol chat --output artifacts\interpretability\0_5b-strict-chat.json

# 3. Only after explicit approval: download the pinned 1.5B model into the Hugging Face cache.
.\.venv-cuda\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen2.5-1.5B-Instruct', revision='f73cfd58be7c44c3caabea717217251688cd47b1')"

# 4. One-scenario strict chat-template smoke test.
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; .\.venv-cuda\Scripts\python.exe -m scripts.run_hf_behavioural_responsiveness_benchmark --allow-model-load --local-files-only --model-id Qwen/Qwen2.5-1.5B-Instruct --model-revision f73cfd58be7c44c3caabea717217251688cd47b1 --protocol chat --smoke-only --output artifacts\interpretability\1_5b-strict-chat-smoke.json

# 5. Full ten-scenario strict chat-template run.
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; .\.venv-cuda\Scripts\python.exe -m scripts.run_hf_behavioural_responsiveness_benchmark --allow-model-load --local-files-only --model-id Qwen/Qwen2.5-1.5B-Instruct --model-revision f73cfd58be7c44c3caabea717217251688cd47b1 --protocol chat --output artifacts\interpretability\1_5b-strict-chat.json

# 6. Compare 0.5B and 1.5B strict-valid summaries.
$zero = Get-Content artifacts\interpretability\0_5b-strict-chat.json -Raw | ConvertFrom-Json; $one = Get-Content artifacts\interpretability\1_5b-strict-chat.json -Raw | ConvertFrom-Json; [pscustomobject]@{model='0.5B'; revision=$zero.model.model_revision; summary=($zero.summary | ConvertTo-Json -Compress); runtime_s=$zero.execution.wall_clock_seconds; peak_cuda=($zero.execution.peak_cuda_memory | ConvertTo-Json -Compress)}, [pscustomobject]@{model='1.5B'; revision=$one.model.model_revision; summary=($one.summary | ConvertTo-Json -Compress); runtime_s=$one.execution.wall_clock_seconds; peak_cuda=($one.execution.peak_cuda_memory | ConvertTo-Json -Compress)} | Format-List
```
