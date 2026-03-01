# Vigil Startup Script - Windows PowerShell

# Prerequisites check
Write-Host "Vigil Startup Utility v2.0" -ForegroundColor Cyan
Write-Host "============================`n" -ForegroundColor Cyan

# Function to check if command exists
function Test-CommandExists {
    param($command)
    try {
        $null = & $command --version 2>&1
        return $true
    } catch {
        return $false
    }
}

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
if (Test-CommandExists python) {
    $version = python --version
    Write-Host "✓ Python installed: $version" -ForegroundColor Green
} else {
    Write-Host "✗ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js..." -ForegroundColor Yellow
if (Test-CommandExists node) {
    $version = node --version
    Write-Host "✓ Node.js installed: $version" -ForegroundColor Green
} else {
    Write-Host "✗ Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
if (Test-CommandExists docker) {
    $version = docker --version
    Write-Host "✓ Docker installed: $version" -ForegroundColor Green
} else {
    Write-Host "✗ Docker not found. Please install Docker Desktop" -ForegroundColor Red
    exit 1
}

# Virtual environment
$venvPath = "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "`nCreating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate venv
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated" -ForegroundColor Green

# Install Python dependencies
Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install Python dependencies" -ForegroundColor Red
    exit 1
}

# Install Frontend dependencies
if (-not (Test-Path "frontend/node_modules")) {
    Write-Host "`nInstalling frontend dependencies..." -ForegroundColor Yellow
    cd frontend
    npm install --silent
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Frontend dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to install frontend dependencies" -ForegroundColor Red
        cd ..
        exit 1
    }
    cd ..
}

# Start Docker
Write-Host "`nStarting Docker containers..." -ForegroundColor Yellow
docker ps > $null 2>&1
if (-not $?) {
    Write-Host "Starting Docker Desktop..." -ForegroundColor Cyan
    & "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Start-Sleep -Seconds 15
}

# Start PostgreSQL
Write-Host "Starting PostgreSQL..." -ForegroundColor Yellow
docker compose -f config/docker-compose.yml up -d postgres
Start-Sleep -Seconds 5

# Verify database connection
Write-Host "Verifying database..." -ForegroundColor Yellow
docker exec vigil_postgres pg_isready -U vigil | Out-Null
if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 3) {
    Write-Host "✓ PostgreSQL ready" -ForegroundColor Green
} else {
    Write-Host "✗ PostgreSQL connection failed" -ForegroundColor Red
    exit 1
}

# Display summary
Write-Host "`n================================" -ForegroundColor Green
Write-Host " Vigil is Ready!" -ForegroundColor Green
Write-Host "================================`n" -ForegroundColor Green

Write-Host "Next steps (run in separate terminals):`n" -ForegroundColor Cyan

Write-Host "Terminal 1 - Backend:" -ForegroundColor Yellow
Write-Host '$env:DATABASE_URL="postgresql+psycopg://vigil:vigil@localhost:5432/vigil"' -ForegroundColor White
Write-Host 'python -m backend.app' -ForegroundColor White

Write-Host "`nTerminal 2 - Frontend:" -ForegroundColor Yellow
Write-Host 'cd frontend' -ForegroundColor White
Write-Host 'npm run dev' -ForegroundColor White

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host " Access Points:" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Dashboard:    http://localhost:5173" -ForegroundColor Green
Write-Host "Backend API:  http://localhost:5000" -ForegroundColor Green
Write-Host "Health:       http://localhost:5000/api/health" -ForegroundColor Green
Write-Host "`nSet your own admin credentials before login.`n" -ForegroundColor Green
