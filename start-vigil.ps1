# VIGIL System Startup Script
# Starts backend and frontend servers in separate PowerShell windows.

$ErrorActionPreference = 'Stop'

Write-Host "Starting VIGIL Surveillance System..." -ForegroundColor Cyan
Write-Host ""

$projectRoot = "E:\Vigil"
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"

# Check Node.js
$nodeAvailable = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeAvailable) {
    Write-Host "Node.js not found in PATH" -ForegroundColor Red
    Write-Host "Adding Node.js to PATH for this session..." -ForegroundColor Yellow
    $env:Path = "$env:Path;C:\Program Files\nodejs"

    $nodeAvailable = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodeAvailable) {
        Write-Host "Failed to find Node.js after PATH update. Install Node.js and retry." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Node.js found: $(node -v)" -ForegroundColor Green
Write-Host "npm found: $(npm -v)" -ForegroundColor Green
Write-Host ""

# Choose Python executable (prefer local venv)
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonCmd = $venvPython
    Write-Host "Using project venv python: $pythonCmd" -ForegroundColor Green
} else {
    $pythonAvailable = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonAvailable) {
        Write-Host "Python not found in PATH" -ForegroundColor Red
        Write-Host "Install Python 3.10+ and retry." -ForegroundColor Yellow
        exit 1
    }
    $pythonCmd = "python"
    Write-Host "Using system python: $(python --version)" -ForegroundColor Green
}
Write-Host ""

if (-not (Test-Path $backendPath)) {
    Write-Host "Backend folder not found at: $backendPath" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $frontendPath)) {
    Write-Host "Frontend folder not found at: $frontendPath" -ForegroundColor Red
    exit 1
}

Write-Host "Backend:  $backendPath" -ForegroundColor Gray
Write-Host "Frontend: $frontendPath" -ForegroundColor Gray
Write-Host ""

# Install Python dependencies
$requirementsFile = Join-Path $projectRoot "requirements.txt"
Write-Host "Checking Python dependencies..." -ForegroundColor Cyan
if (Test-Path $requirementsFile) {
    Write-Host "Installing Python packages (this may take a while)..." -ForegroundColor Yellow
    & $pythonCmd -m pip install -q -r $requirementsFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Python dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "Some Python packages may have failed to install" -ForegroundColor Yellow
    }
} else {
    Write-Host "requirements.txt not found, skipping Python dependency install" -ForegroundColor Yellow
}
Write-Host ""

# Run Alembic migrations
Write-Host "Running database migrations..." -ForegroundColor Cyan
Push-Location $projectRoot
& $pythonCmd -m alembic upgrade head
if ($LASTEXITCODE -eq 0) {
    Write-Host "Migrations applied" -ForegroundColor Green
} else {
    Write-Host "Migrations may have failed; check output above" -ForegroundColor Yellow
}
Pop-Location
Write-Host ""

# Install frontend dependencies
Write-Host "Checking Node.js dependencies..." -ForegroundColor Cyan
Push-Location $frontendPath
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing Node.js packages..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Node.js dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "Failed to install Node.js dependencies" -ForegroundColor Red
        Pop-Location
        exit 1
    }
} else {
    Write-Host "Node.js dependencies already installed" -ForegroundColor Green
}
Pop-Location
Write-Host ""

# Start backend server in a new window
Write-Host "Starting backend server..." -ForegroundColor Cyan
$backendCmd = "Set-Location '$projectRoot'; Write-Host 'VIGIL Backend Server' -ForegroundColor Green; & '$pythonCmd' -m backend.app"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal

Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

try {
    Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health" -Method GET -UseBasicParsing -TimeoutSec 3 | Out-Null
    Write-Host "Backend is running at http://127.0.0.1:5000" -ForegroundColor Green
} catch {
    Write-Host "Backend may still be starting; check the backend window" -ForegroundColor Yellow
}
Write-Host ""

# Start frontend server in a new window
Write-Host "Starting frontend server..." -ForegroundColor Cyan
$frontendCmd = "Set-Location '$frontendPath'; Write-Host 'VIGIL Frontend Server' -ForegroundColor Green; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal

Write-Host "Waiting for frontend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
Write-Host ""

Write-Host "VIGIL system started" -ForegroundColor Green
Write-Host "Backend API:  http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "Frontend App: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop this launcher (servers keep running)." -ForegroundColor Gray
Write-Host "Close spawned PowerShell windows to stop backend/frontend." -ForegroundColor Gray
Write-Host ""

while ($true) {
    Start-Sleep -Seconds 10
}
