$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $projectRoot
docker compose down
if ($LASTEXITCODE -ne 0) { throw 'Stop failed. Inspect Docker Desktop.' }
Write-Host 'Montralog stopped. Persistent volumes were preserved.'
