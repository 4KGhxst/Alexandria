# Launches Alexandria and keeps her running: loads .env, activates the
# venv, and restarts the app if it exits (crash, unhandled error, etc.).
# Meant to be the Action a Windows Task Scheduler task runs at logon —
# see docs/ARCHITECTURE.md for the one-time setup steps.
#
# To pause her without touching Task Scheduler: create an empty file named
# STOP in the repo root — she'll exit after the current run ends and won't
# restart until you delete it. To stop her for good, disable the
# Scheduled Task.

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $RepoRoot

$VenvActivate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $VenvActivate)) {
    Write-Error "No venv found at .venv — run: python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -e ."
    exit 1
}
. $VenvActivate

$EnvFile = Join-Path $RepoRoot ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        $key, $value = $line -split "=", 2
        if ($key -and $null -ne $value) {
            [System.Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
        }
    }
}

$StopFile = Join-Path $RepoRoot "STOP"

while ($true) {
    if (Test-Path $StopFile) {
        Write-Host "STOP file found — not restarting. Delete it to resume."
        break
    }

    Write-Host "$(Get-Date -Format o) Starting Alexandria..."
    python -m alexandria.main
    $exitCode = $LASTEXITCODE

    Write-Host "$(Get-Date -Format o) Alexandria exited (code $exitCode). Restarting in 5s..."
    Start-Sleep -Seconds 5
}
