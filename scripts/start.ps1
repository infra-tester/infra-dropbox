# Start Infra Dropbox detached. Reuses the server's lock, token and state dir.

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

    Write-Host ('  {0,-16}' -f "${Label}:") -NoNewline -ForegroundColor DarkGray
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
$stdoutPath = Join-Path $stateDir 'server.log'
$stderrPath = Join-Path $stateDir 'server-error.log'

Write-Host ''
Write-Host 'Infra Dropbox - start' -ForegroundColor Cyan
Write-Label 'Project' $projectRoot

$portListening = Test-PortListening -Port $port
$lockHeld = Test-LockHeld -Path $lockPath
if ($portListening -or $lockHeld) {
    Write-Host '[!!] Already running; no second instance started.' -ForegroundColor Red
    if ($portListening) {
        Write-Label 'Port' "$port is listening"
    }
    if ($lockHeld) {
        Write-Label 'Lock' 'held'
    }
    Write-Label 'Next' 'idb stop'
    Write-Host ''
    exit 1
}

# setx stores user variables in HKCU\Environment; a stale terminal may not have
# them in its process environment, so copy the persisted values into this child.
foreach ($name in @('ADMIN_PASSWORD', 'SMS_WEBHOOK_SECRET')) {
    $userValue = [Environment]::GetEnvironmentVariable($name, 'User')
    if ($null -ne $userValue) {
        [Environment]::SetEnvironmentVariable($name, $userValue, 'Process')
    }
}

try {
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
} catch {
    Write-Host "[!!] Could not create the state directory ${stateDir}: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ''
    exit 1
}

$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $python = 'python'
}

Write-Host "[..] Launching $python run.py" -ForegroundColor DarkGray
try {
    $process = Start-Process -FilePath $python -ArgumentList 'run.py' `
        -WorkingDirectory $projectRoot `
        -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath `
        -WindowStyle Hidden -PassThru -ErrorAction Stop
} catch {
    Write-Host "[!!] Failed to launch ${python}: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ''
    exit 1
}

$deadline = (Get-Date).AddSeconds(15)
$listening = $false
while ((Get-Date) -lt $deadline) {
    if (Test-PortListening -Port $port) {
        $listening = $true
        break
    }
    $process.Refresh()
    if ($process.HasExited) {
        break
    }
    Start-Sleep -Milliseconds 250
}

if ($listening) {
    Write-Host "[OK] Started (PID $($process.Id)). Port $port is listening." -ForegroundColor Green
    Write-Label 'stdout' $stdoutPath
    Write-Label 'stderr' $stderrPath
    Write-Label 'Next' 'idb status'
    Write-Host ''
    exit 0
}

$process.Refresh()
if ($process.HasExited) {
    Write-Host "[!!] Launcher exited with code $($process.ExitCode) before port $port was listening." -ForegroundColor Red
} else {
    Write-Host "[!!] PID $($process.Id) is running, but port $port was not listening after 15 seconds." -ForegroundColor Red
}
Write-Label 'stderr' $stderrPath 'Red'
Write-Host ''
exit 1
