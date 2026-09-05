$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv-2\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'C:/Users/Aniket/AppData/Local/Programs/Python/Python313/python.exe' }
& $python -m uvicorn backend.main:app --reload --port 8000
