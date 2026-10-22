# Windows helpers

Run these from the repository root after starting Docker Desktop:

```powershell
.\scripts\windows\Start-Montralog.ps1
.\scripts\windows\Run-Demo.ps1
.\scripts\windows\Start-Local-Metrics.ps1
.\scripts\windows\Stop-Local-Metrics.ps1
.\scripts\windows\Stop-Montralog.ps1
```

Each script resolves the repository root from its own location. Configuration, runtime state and Docker volume names remain unchanged. The demo command inserts synthetic telemetry; collection is optional.
