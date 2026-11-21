# Generate Andes Advisory corpus (DAP Laya).
# Usage:
#   .\scripts\generate_corpus.ps1 --dry-run
#   .\scripts\generate_corpus.ps1 --seed 20261114
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsPassThrough
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Local venv not found at $Python. Create it with: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
}
$env:PYTHONPATH = Join-Path $Root "src"
Set-Location $Root
& $Python -m corpus_gen @ArgsPassThrough
exit $LASTEXITCODE
