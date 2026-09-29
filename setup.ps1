# ==============================================================================
# OfflineMind - One-Click Setup Script for Windows (x86_64 & Windows on ARM64)
# Snapdragon AI Lab Build & Present Challenge
# ==============================================================================

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  OfflineMind - Private On-Device AI Notes Setup" -ForegroundColor Cyan
Write-Host "  Target: Snapdragon-powered HP PCs & Windows on ARM64" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Check Python
$pythonCmd = "python"
if (-not (Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
    Write-Error "Python 3.11+ is not found in PATH. Please install Python and try again."
    Exit 1
}

$pyVersion = & $pythonCmd --version
Write-Host "[✓] Detected: $pyVersion" -ForegroundColor Green

# 2. Detect System Architecture
$arch = $env:PROCESSOR_ARCHITECTURE
Write-Host "[*] Architecture: $arch" -ForegroundColor Yellow

if ($arch -eq "ARM64") {
    Write-Host "[★] Snapdragon ARM64 Architecture Detected!" -ForegroundColor Magenta
    Write-Host "    Qualcomm Hexagon NPU acceleration will be utilized via QNNExecutionProvider." -ForegroundColor Green
} else {
    Write-Host "[i] Running on x86/x64. CPUExecutionProvider will be used as automatic fallback." -ForegroundColor Gray
}

# 3. Virtual Environment Setup
$venvPath = Join-Path $PSScriptRoot "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "[*] Creating virtual environment at '$venvPath'..." -ForegroundColor Yellow
    & $pythonCmd -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment."
        Exit 1
    }
}
Write-Host "[✓] Virtual environment ready." -ForegroundColor Green

# 4. Activate Venv and Upgrade Pip
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

Write-Host "[*] Upgrading pip and wheel..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip wheel setuptools --quiet

# 5. Install Dependencies
Write-Host "[*] Installing OfflineMind dependencies from requirements.txt..." -ForegroundColor Yellow
& $venvPip install -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies."
    Exit 1
}

# 6. For ARM64 Snapdragon, notify about onnxruntime-qnn
if ($arch -eq "ARM64") {
    Write-Host "[*] Checking Qualcomm QNN Execution Provider..." -ForegroundColor Cyan
    & $venvPip install onnxruntime-qnn --extra-index-url https://aihub.qualcomm.com/wheels --quiet 2>$null
}

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "  Setup Completed Successfully!" -ForegroundColor Green
Write-Host "  To launch OfflineMind, run:" -ForegroundColor White
Write-Host "    .\run.ps1" -ForegroundColor Yellow
Write-Host "  or:" -ForegroundColor White
Write-Host "    .\venv\Scripts\streamlit run app\main.py" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Green
