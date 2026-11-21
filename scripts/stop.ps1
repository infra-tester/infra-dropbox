# Gracefully stop Infra Dropbox using its token-authenticated loopback endpoint.
# Never force-terminates a process.

$ErrorActionPreference = 'Stop'

function Test-PortListening {
    param([int]$Port)

    $connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    return $connections.Count -gt 0
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
$shutdownUri = "http://127.0.0.1:$port/__idb_shutdown"

if ([string]::IsNullOrEmpty($env:LOCALAPPDATA)) {
    Write-Host '[!!] LOCALAPPDATA is not set; cannot locate the Infra Dropbox shutdown token.' -ForegroundColor Red
    Write-Host ''
    exit 1
}

$stateDir = Join-Path $env:LOCALAPPDATA 'InfraDropbox'
$tokenPath = Join-Path $stateDir 'shutdown.token'
$lockPath = Join-Path $stateDir 'server.lock'
$stderrPath = Join-Path $stateDir 'server-error.log'

Write-Host ''
Write-Host 'Infra Dropbox - stop' -ForegroundColor Cyan
Write-Label 'Project' $projectRoot

if (-not (Test-PortListening -Port $port)) {
    if ((Test-Path -LiteralPath $tokenPath) -or (Test-Path -LiteralPath $lockPath)) {
        $staleFiles = @()
        if (Test-Path -LiteralPath $lockPath) { $staleFiles += 'server.lock' }
        if (Test-Path -LiteralPath $tokenPath) { $staleFiles += 'shutdown.token' }
        Write-Host "[--] Not listening on port $port. Stale: $($staleFiles -join ', '). Nothing to stop." -ForegroundColor Yellow
    } else {
        Write-Host "[--] Not running. Port $port is not listening; nothing to stop." -ForegroundColor Yellow
    }
    Write-Host ''
    exit 0
}

if (-not (Test-Path -LiteralPath $tokenPath -PathType Leaf)) {
    Write-Host "[!!] Port $port is in use but no shutdown token exists. Refusing to contact an unknown service." -ForegroundColor Red
    Write-Label 'Expected' $tokenPath 'Red'
    Write-Host ''
    exit 1
}

$token = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
if ([string]::IsNullOrEmpty($token)) {
    Write-Host "[!!] The shutdown token at $tokenPath is empty. Refusing to contact the service." -ForegroundColor Red
    Write-Host ''
    exit 1
}

# Prefer the process that actually owns the listening socket; server.pid can be stale.
$listeners = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
$serverProcessId = 0
if ($listeners.Count -gt 0 -and $listeners[0].OwningProcess -gt 0) {
    $serverProcessId = [int]$listeners[0].OwningProcess
}

$requested = $false
try {
    $response = Invoke-WebRequest -Uri $shutdownUri -Method Post `
        -Headers @{ 'X-IDB-Shutdown-Token' = $token } `
        -TimeoutSec 5 -UseBasicParsing
    $statusCode = [int]$response.StatusCode
    if ($statusCode -eq 202) {
        $requested = $true
        Write-Host "[OK] Shutdown accepted (HTTP $statusCode). Waiting for exit..." -ForegroundColor Green
    } else {
        Write-Host "[!!] Unexpected shutdown response: HTTP $statusCode." -ForegroundColor Yellow
    }
} catch [System.Net.WebException] {
    $webResponse = $_.Exception.Response
    if ($null -ne $webResponse) {
        $statusCode = [int]$webResponse.StatusCode
        switch ($statusCode) {
            403 {
                Write-Host '[!!] Shutdown token rejected (stale token or wrong service). Nothing was stopped.' -ForegroundColor Red
                Write-Host ''
                exit 1
            }
            405 {
                Write-Host "[--] Method rejected (HTTP $statusCode); the service may already be stopping." -ForegroundColor Yellow
                $requested = $true
            }
            503 {
                Write-Host "[--] Service reports it is already stopping (HTTP $statusCode)." -ForegroundColor Yellow
                $requested = $true
            }
            default {
                Write-Host "[!!] Shutdown request failed with HTTP $statusCode." -ForegroundColor Red
                Write-Host ''
                exit 1
            }
        }
    } else {
        Write-Host "[--] Server closed before acknowledging. Checking exit..." -ForegroundColor Yellow
        $requested = $true
    }
} catch {
    Write-Host "[!!] Shutdown request failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ''
    exit 1
}

if (-not $requested) {
    Write-Host ''
    exit 1
}

$deadline = (Get-Date).AddSeconds(30)
$stopped = $false
while ((Get-Date) -lt $deadline) {
    $processAlive = $false
    if ($serverProcessId -gt 0) {
        $processAlive = $null -ne (Get-Process -Id $serverProcessId -ErrorAction SilentlyContinue)
    }
    if (-not $processAlive -and -not (Test-PortListening -Port $port)) {
        $stopped = $true
        break
    }
    Start-Sleep -Milliseconds 250
}

if (-not $stopped) {
    Write-Host '[!!] Still running after 30 seconds. No force-kill was attempted.' -ForegroundColor Red
    Write-Label 'stderr' $stderrPath 'Red'
    Write-Host ''
    exit 1
}

$tokenState = if (Test-Path -LiteralPath $tokenPath) { 'still present' } else { 'removed' }
$lockState = if (Test-Path -LiteralPath $lockPath) { 'released (file remains)' } else { 'removed' }
Write-Host '[OK] Stopped.' -ForegroundColor Green
Write-Label 'Token' $tokenState
Write-Label 'Lock' $lockState
