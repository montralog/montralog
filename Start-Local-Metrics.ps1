$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$state = Join-Path $PSScriptRoot '.local'
New-Item -ItemType Directory -Force -Path $state | Out-Null
$pidFile = Join-Path $state 'metrics-agent.pid'
if (Test-Path -LiteralPath $pidFile) {
    $agentPid = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId=$agentPid" -ErrorAction SilentlyContinue
    if ($existing -and $existing.CommandLine -like '*agents*docker*agent.py*') {
        Write-Host 'Local metrics agent is already running.'
        exit 0
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.env'))) { throw 'Run scripts/setup.py first.' }
docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop first.' }
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$dependencyPath = Join-Path $state 'python'
$oldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $dependencyPath
    & $pythonExe -c 'import psutil'
    if ($LASTEXITCODE -ne 0) {
        & $pythonExe -m pip install --target $dependencyPath psutil==7.0.0
        if ($LASTEXITCODE -ne 0) { throw 'Host metric dependency installation failed.' }
    }
    $agentFile = Join-Path $PSScriptRoot 'agents\docker\agent.py'
    $envFile = Join-Path $PSScriptRoot '.env'
    $logFile = Join-Path $state 'metrics-agent.log'
    $arguments = '-u "{0}" --host --env-file "{1}" --interval 15 --log-file "{2}"' -f $agentFile,$envFile,$logFile
    $process = Start-Process -FilePath $pythonExe -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $state 'metrics-agent-startup.log') -RedirectStandardError (Join-Path $state 'metrics-agent-error.log')
    Set-Content -LiteralPath $pidFile -Value $process.Id
    Write-Host 'Local Docker and Windows host collection started. Updates arrive every 15 seconds.'
    Write-Host 'Logs are in .local. Run Stop-Local-Metrics.ps1 to stop collection.'
} finally { $env:PYTHONPATH = $oldPythonPath }
