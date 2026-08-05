<#
.SYNOPSIS
    Smart Quotation System - Portable Startup Script (PowerShell)
.DESCRIPTION
    Automatically detects environment, installs dependencies,
    and starts both backend and frontend services.
    Works on any Windows 10/11 computer.
#>

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

# Set window title (overrides any garbled title from parent)
$Host.UI.RawUI.WindowTitle = "Smart Quotation System"

function Write-Step($msg) { Write-Host "`n$msg" -ForegroundColor Yellow }
function Write-OK($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "  ... $msg" -ForegroundColor Cyan }
function Write-Error($msg) { Write-Host "  [ERROR] $msg" -ForegroundColor Red }

# ---------- Helper: test if venv python is usable ----------
function Test-VenvPython($exePath) {
    if (-not (Test-Path $exePath)) { return $false }
    try {
        $ver = & $exePath --version 2>&1
        return ($LASTEXITCODE -eq 0 -and $ver -match "Python")
    }
    catch { return $false }
}

# ---------- Helper: recreate venv ----------
function New-Venv {
    param([string]$ScriptDir, [string]$pythonCmd)
    Write-Info "Creating virtual environment..."
    Push-Location $ScriptDir
    try {
        & $pythonCmd -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
    }
    finally { Pop-Location }
    Write-OK "Virtual environment created"
}

# Get project root (script directory)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "backend"
$FrontendDir = Join-Path $ScriptDir "frontend"
$VenvDir = Join-Path $ScriptDir ".venv"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Smart Quotation System - Portable Launcher" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Project: $ScriptDir`n"

# ============================================================
#  Step 1: Check Python
# ============================================================
Write-Step "[1/5] Checking Python..."

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -match "Python") {
            $pythonCmd = $cmd
            break
        }
    }
    catch {}
}

if (-not $pythonCmd) {
    Write-Error "Python 3 not found!"
    Write-Host "Please install Python 3.8+ from https://www.python.org/downloads/"
    Write-Host "Make sure to check 'Add Python to PATH' during installation.`n"
    Read-Host "Press Enter to exit"
    exit 1
}

$pythonVersion = & $pythonCmd --version 2>&1
Write-OK $pythonVersion

# ============================================================
#  Step 2: Check Node.js
# ============================================================
Write-Step "[2/5] Checking Node.js..."

try {
    $nodeVersion = node --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "node not found" }
}
catch {
    Write-Error "Node.js not found!"
    Write-Host "Please install Node.js 18+ (LTS) from https://nodejs.org/`n"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-OK "Node.js $nodeVersion"

# ============================================================
#  Step 3: Setup Python virtual environment
# ============================================================
Write-Step "[3/5] Setting up Python environment..."

$pythonExe = Join-Path (Join-Path $VenvDir "Scripts") "python.exe"

# Check if venv exists AND is usable (survives copying to another PC)
if (Test-VenvPython $pythonExe) {
    Write-OK "Virtual environment is usable"
}
else {
    # Venv either doesn't exist or is broken (e.g. copied from another PC)
    if (Test-Path $VenvDir) {
        Write-Info "Virtual environment is broken (possibly from another computer). Recreating..."
        Remove-Item -Path $VenvDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Venv -ScriptDir $ScriptDir -pythonCmd $pythonCmd
}

# Verify the venv works after creation/repair
if (-not (Test-VenvPython $pythonExe)) {
    Write-Error "Failed to create usable virtual environment!"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if dependencies already installed (fastapi as proxy)
$depsInstalled = & $pythonExe -c "import fastapi; import uvicorn; import sqlalchemy" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-OK "Python dependencies already installed"
}
else {
    Write-Info "Installing Python dependencies (this may take a few minutes)..."
    Push-Location $ScriptDir
    try {
        & $pythonExe -m pip install --upgrade pip -q 2>&1 | Out-Host
        
        & $pythonExe -m pip install -r (Join-Path $BackendDir "requirements.txt") 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Write-Error "pip install failed!"
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
    finally { Pop-Location }
    Write-OK "Python dependencies installed"
}

# ============================================================
#  Step 4: Install frontend dependencies
# ============================================================
Write-Step "[4/5] Installing frontend dependencies..."

if (Test-Path (Join-Path $FrontendDir "node_modules")) {
    Write-OK "node_modules exists"
}
else {
    Write-Info "Running npm install (first time may take a few minutes)..."
    Push-Location $FrontendDir
    try {
        npm install 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    }
    finally { Pop-Location }
    Write-OK "npm install complete"
}
Write-OK "Frontend ready"

# ============================================================
#  Step 5: Start services
# ============================================================
Write-Step "[5/5] Starting services..."

# Kill any leftover processes
function Cleanup {
    Write-Info "Cleaning up service processes..."
    # Kill processes listening on our ports (8000 backend / 5173 frontend)
    # NOTE: use $procId instead of $pid — $PID is a read-only built-in variable in PowerShell!
    $ports = @(8000, 5173)
    $connections = netstat -ano 2>&1 | Select-String "LISTENING"
    foreach ($conn in $connections) {
        foreach ($port in $ports) {
            if ($conn -match ":$port\s+") {
                $procId = $conn -replace '.*\s+(\d+)$', '$1'
                $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Info "Stopping PID $procId ($($proc.ProcessName)) on port $port..."
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
    # Fallback: kill leftover service processes for THIS project.
    # Get-Process has no CommandLine property in Windows PowerShell 5.1,
    # so use Get-CimInstance instead (reliable cross-version).
    # Backend is launched as: python -m uvicorn app.main:app ... (matches this project only)
    Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match 'app\.main:app' } |
    ForEach-Object {
        Write-Info "Stopping leftover uvicorn PID $($_.ProcessId)..."
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    # Frontend is launched as: node .../vite.js (this project's vite dev server)
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'vite' } |
    ForEach-Object {
        Write-Info "Stopping leftover vite PID $($_.ProcessId)..."
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Cleanup

# Start backend
Write-Info "Starting backend API server..."
Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "info" -WorkingDirectory $BackendDir -WindowStyle Normal

# Wait for backend
Write-Info "Waiting for backend (this may take 10-15s)..."
$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 1
        if ($r.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    }
    catch {}
    Start-Sleep -Seconds 1
}

if (-not $backendReady) {
    Write-Error "Backend did not become ready in time"
    Write-Host "Check the backend window for errors"
    Cleanup
    Read-Host "Press Enter to exit"
    exit 1
}

Write-OK "Backend running at http://127.0.0.1:8000"

# Start frontend
Write-Info "Starting frontend dev server..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WorkingDirectory $FrontendDir -WindowStyle Normal

# Give frontend some time to start, then open browser regardless
Write-Info "Waiting for frontend to start..."
$frontendReady = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $r = Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 1
        if ($r.StatusCode -eq 200 -or $r.StatusCode -eq 304) {
            $frontendReady = $true
            break
        }
    }
    catch {}
    Start-Sleep -Seconds 1
}

if ($frontendReady) {
    Write-OK "Frontend ready at http://localhost:5173"
}
else {
    Write-Info "Frontend still starting, opening browser anyway..."
}

Write-Info "Opening browser..."
Start-Process "http://localhost:5173"

# ============================================================
#  Display status screen
# ============================================================
Clear-Host
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "   Smart Quotation System - Running" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "`n  Backend API:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  Frontend UI:  http://localhost:5173" -ForegroundColor Cyan
Write-Host "  API Docs:     http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "`n  Close this window to stop all services." -ForegroundColor Yellow
Write-Host "`n  Press any key to stop all services and exit..." -ForegroundColor Yellow
Read-Host

# Cleanup on exit
Cleanup
Write-Host "`nServices stopped. Thank you!" -ForegroundColor Green
Start-Sleep -Seconds 2
