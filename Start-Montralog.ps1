$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.env')) {
    python scripts/setup.py
    if ($LASTEXITCODE -ne 0) { throw 'Credential setup failed.' }
}
docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop with Linux containers, then retry.' }
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Invalid Compose configuration.' }
docker compose build gateway
if ($LASTEXITCODE -ne 0) { throw 'Image build failed.' }
docker compose up -d --no-build --wait --wait-timeout 180
if ($LASTEXITCODE -ne 0) { throw 'Startup failed. Inspect docker compose logs.' }
Write-Host 'Montralog is running at http://localhost:8080'
Write-Host 'Sign in with your local username and password.'
