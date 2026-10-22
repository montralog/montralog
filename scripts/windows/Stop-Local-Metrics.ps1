$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $projectRoot '.local\metrics-agent.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host 'No local agent is registered.'; exit 0 }
$agentPid = [int](Get-Content -LiteralPath $pidFile)
$existing = Get-CimInstance Win32_Process -Filter "ProcessId=$agentPid" -ErrorAction SilentlyContinue
if ($existing -and $existing.CommandLine -like '*agents*docker*agent.py*') { Stop-Process -Id $agentPid }
Remove-Item -LiteralPath $pidFile
Write-Host 'Local collection stopped. Stored telemetry is preserved.'
