# setup-fresh.ps1 - Create a completely fresh Flight OCR development environment
# Force removes existing environment and creates a new one from scratch

Write-Host "Creating fresh Flight OCR development environment..." -ForegroundColor Green

# Check if Python is available
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "Python not found. Please install Python 3.8+ first." -ForegroundColor Red
    exit 1
}

# Check Python version
$pythonVersion = python --version 2>&1
Write-Host "Found $pythonVersion" -ForegroundColor Cyan

# Force remove existing virtual environment if it exists
if (Test-Path ".venv") {
    Write-Host "Force removing existing virtual environment..." -ForegroundColor Yellow
    # Deactivate any conda environments first
    conda deactivate 2>$null
    # Force remove with different approaches
    try {
        Remove-Item -Recurse -Force .venv -ErrorAction Stop
    } catch {
        Write-Host "Could not remove .venv automatically. Please:" -ForegroundColor Red
        Write-Host "1. Close VS Code and all terminals" -ForegroundColor Yellow
        Write-Host "2. Manually delete the .venv folder" -ForegroundColor Yellow  
        Write-Host "3. Run this script again" -ForegroundColor Yellow
        exit 1
    }
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Cyan
python -m venv .venv

# Activate virtual environment and install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

# Verify installation
Write-Host "Verifying installation..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -c "import pandas, matplotlib, rich, pytesseract, PIL; print('All dependencies installed successfully!')"

Write-Host ""
Write-Host "Fresh environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the virtual environment:" -ForegroundColor White
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
