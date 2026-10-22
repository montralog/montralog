$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
docker compose down
if ($LASTEXITCODE -ne 0) { throw 'Stop failed. Inspect Docker Desktop.' }
Write-Host 'Montralog stopped. Persistent volumes were preserved.'
