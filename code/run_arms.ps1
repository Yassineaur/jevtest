# Generic resumable launcher: trains then evaluates a list of arms, skipping finished ones.
# Each arm: name:arm:cem|nocem:seed[:extra train args separated by ';']
# Example:
#   powershell -ExecutionPolicy Bypass -File code\run_arms.ps1 -Group ablation -Arms "T4nc_s0:cea:nocem:0,T0nc_s0:label:nocem:0"
param([string]$Group = "pilot", [string]$Arms)
$ErrorActionPreference = "Continue"; $env:PYTHONUTF8 = "1"
Set-Location -Path (Split-Path $PSScriptRoot -Parent)
$PY = "..\torch_env\Scripts\python.exe"
New-Item -ItemType Directory -Force -Path "results\$Group", "logs" | Out-Null
$LOCK = "results\$Group\run.lock"
if (Test-Path $LOCK) { $old = (Get-Content $LOCK -Raw).Trim()
  if (Get-Process -Id $old -ErrorAction SilentlyContinue) { "already running (PID $old)"; exit 0 } }
Set-Content -Path $LOCK -Value $PID
function Log($name, $line) { $line; Add-Content -Path "logs\$($Group)_$name.log" -Value $line -Encoding UTF8 }
try {
  foreach ($spec in $Arms.Split(",")) {
    $p = $spec.Trim().Split(":")
    $name, $arm, $cem, $seed = $p[0], $p[1], $p[2], $p[3]
    $extra = @(); if ($p.Length -gt 4) { $extra = $p[4].Split(";") | Where-Object { $_ -ne "" } }
    $out = "results\$Group\$name"
    $targs = @("code\train.py", "--arm", $arm, "--seed", $seed, "--out", $out, "--device", "cuda") + $extra
    if ($cem -eq "nocem") { $targs += "--no-cem" }
    if (-not (Test-Path "$out\DONE")) {
      & $PY @targs 2>&1 | Where-Object { $_ -notmatch "UNEXPECTED|Loading weights|LOAD REPORT|can be ignored" } |
        ForEach-Object { Log $name $_ }
    }
    if ((Test-Path "$out\DONE") -and -not (Test-Path "$out\eval\metrics.json")) {
      & $PY code\evaluate.py --ckpt "$out\best.pt" --device cuda 2>&1 |
        Where-Object { $_ -notmatch "UNEXPECTED|Loading weights|LOAD REPORT|can be ignored" } |
        ForEach-Object { Add-Content -Path "logs\$($Group)_$($name)_eval.log" -Value $_ -Encoding UTF8 }
      Log $name "EVAL DONE $name"
    }
  }
} finally { Remove-Item $LOCK -ErrorAction SilentlyContinue }
