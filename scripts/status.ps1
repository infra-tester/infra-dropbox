# Report Infra Dropbox service state. Read-only: no process or file changes.
# Shared with start.ps1/stop.ps1: port 5000 and these state/log paths.

$ErrorActionPreference = 'Stop'

function Test-PortListening {
    param([int]$Port)

    $connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    return $connections.Count -gt 0
}

function Test-LockHeld {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }

    # The server keeps server.lock open (and byte-range locked) for its lifetime.
    # Requesting no sharing at all fails while that handle is open.
    try {
        $stream = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
        $stream.Dispose()
        return $false
    } catch [System.IO.IOException] {
        return $true
    }
}

function Write-Label {
    param(
        [string]$Label,
        [string]$Value,
        [string]$Color = 'Gray'
    )

    Write-Host ('  {0,-20}' -f "${Label}:") -NoNewline -ForegroundColor DarkGray
    Write-Host $Value -ForegroundColor $Color
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$port = 5000

if ([string]::IsNullOrEmpty($env:LOCALAPPDATA)) {
    Write-Host '[!!] LOCALAPPDATA is not set; cannot locate the Infra Dropbox state directory.' -ForegroundColor Red
    Write-Host ''
    exit 1
}

$stateDir = Join-Path $env:LOCALAPPDATA 'InfraDropbox'
$lockPath = Join-Path $stateDir 'server.lock'
$tokenPath = Join-Path $stateDir 'shutdown.token'
$stdoutPath = Join-Path $stateDir 'server.log'
$stderrPath = Join-Path $stateDir 'server-error.log'

$listening = Test-PortListening -Port $port
$lockHeld = Test-LockHeld -Path $lockPath
$tokenPresent = Test-Path -LiteralPath $tokenPath -PathType Leaf

if ($listening) {
    $serviceText = "RUNNING (port $port listening)"
    $serviceColor = 'Green'
} elseif ((Test-Path -LiteralPath $lockPath) -or $tokenPresent) {
    $serviceText = "STOPPED (stale control files)"
    $serviceColor = 'Yellow'
} else {
    $serviceText = "STOPPED (port $port closed)"
    $serviceColor = 'Yellow'
}

$urlText = 'not available (service stopped)'
$urlColor = 'DarkGray'
if ($listening) {
    try {
        $network = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/network" -TimeoutSec 3
        $urls = @($network.urls)
        if ($urls.Count -gt 0) {
            $urlText = $urls -join ' | '
            $urlColor = 'Cyan'
        } else {
            $urlText = 'none detected'
            $urlColor = 'Yellow'
        }
    } catch {
        $urlText = "unavailable: $($_.Exception.Message)"
        $urlColor = 'Yellow'
    }
}

$adminSet = -not [string]::IsNullOrEmpty($env:ADMIN_PASSWORD)
$webhookSet = -not [string]::IsNullOrEmpty($env:SMS_WEBHOOK_SECRET)

Write-Host ''
Write-Host 'Infra Dropbox - status' -ForegroundColor Cyan
Write-Label 'Project' $projectRoot
Write-Label 'Service' $serviceText $serviceColor
Write-Label 'Lock' $(if ($lockHeld) { 'held' } else { 'not held' }) $(if ($lockHeld) { 'Green' } else { 'DarkGray' })
Write-Label 'Token' $(if ($tokenPresent) { 'present' } else { 'absent' }) $(if ($tokenPresent) { 'Green' } else { 'DarkGray' })
Write-Label 'URLs' $urlText $urlColor
Write-Label 'State dir' $stateDir
Write-Label 'stdout' $stdoutPath
Write-Label 'stderr' $stderrPath
Write-Label 'ADMIN_PASSWORD' $(if ($adminSet) { 'set' } else { 'not set' }) $(if ($adminSet) { 'Green' } else { 'Yellow' })
Write-Label 'SMS_WEBHOOK_SECRET' $(if ($webhookSet) { 'set' } else { 'not set' }) $(if ($webhookSet) { 'Green' } else { 'Yellow' })
Write-Host ''
