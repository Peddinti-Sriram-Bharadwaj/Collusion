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
