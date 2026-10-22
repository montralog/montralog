$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.env')) { throw 'Run setup/start first.' }
foreach ($line in Get-Content -LiteralPath '.env') {
    if ($line -match '^MONTRALOG_INGEST_TOKEN=(.+)$') {
        $env:MONTRALOG_INGEST_TOKEN = $Matches[1]
    }
}
python scripts/send_demo.py
if ($LASTEXITCODE -ne 0) { throw 'Demo delivery failed.' }
Write-Host 'Synthetic demo added. Select environment=demo in the dashboard.'
