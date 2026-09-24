# Kill-switch pilot: T4 (CEA, evidence) then T0 (label-only control), seed 0, CEM views for both.
# Resumable: each arm resumes from results\pilot\<arm>\last.pt and is skipped once it has DONE.
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File code\run_pilot.ps1
$ErrorActionPreference = "Continue"; $env:PYTHONUTF8 = "1"
Set-Location -Path (Split-Path $PSScriptRoot -Parent)
$PY = "..\torch_env\Scripts\python.exe"
New-Item -ItemType Directory -Force -Path "results\pilot", "logs" | Out-Null
$LOCK = "results\pilot\pilot.lock"
if (Test-Path $LOCK) { $old = (Get-Content $LOCK -Raw).Trim()
  if (Get-Process -Id $old -ErrorAction SilentlyContinue) { "pilot already running (PID $old)"; exit 0 } }
Set-Content -Path $LOCK -Value $PID
try {
  foreach ($arm in @(@{name="T4_s0"; arm="cea"}, @{name="T0_s0"; arm="label"})) {
    $out = "results\pilot\$($arm.name)"
    if (Test-Path "$out\DONE") { "$($arm.name) already DONE"; continue }
    & $PY code\train.py --arm $arm.arm --seed 0 --out $out --device cuda 2>&1 |
      Where-Object { $_ -notmatch "UNEXPECTED|Loading weights|LOAD REPORT|can be ignored" } |
      ForEach-Object { $_; Add-Content -Path "logs\pilot_$($arm.name).log" -Value $_ -Encoding UTF8 }
  }
} finally { Remove-Item $LOCK -ErrorAction SilentlyContinue }
