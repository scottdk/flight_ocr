# setup-env.ps1 - Environment setup script for Flight OCR project
# Creates a virtual environment and installs all Python dependencies

Write-Host "Setting up Flight OCR development environment..." -ForegroundColor Green

# Ensure we're not in a virtual environment
if ($env:VIRTUAL_ENV) {
    Write-Host "Please deactivate the current virtual environment first:" -ForegroundColor Yellow
    Write-Host "Run: deactivate" -ForegroundColor Yellow
    Write-Host "Then run this script again." -ForegroundColor Yellow
    exit 1
}

# Check if Python is available
$pythonCmd = $null
$pythonVersion = $null

# First try the simple commands
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $testResult = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $testResult -match "Python (\d+\.\d+)") {
            $majorMinor = [version]$matches[1]
            if ($majorMinor -ge [version]"3.8") {
                $pythonCmd = $cmd
                $pythonVersion = $testResult
                break
            } else {
                Write-Host "Found $testResult but requires Python 3.8 or higher" -ForegroundColor Yellow
            }
        }
    } catch {
        continue
    }
}

# If not found, try to find Python installations by searching common directories
if (-not $pythonCmd) {
    Write-Host "Searching for Python installations..." -ForegroundColor Cyan
    $searchPaths = @(
        "$env:LOCALAPPDATA\Programs\Python",
        "C:\Python*",
        "C:\Program Files\Python*",
        "C:\Program Files (x86)\Python*"
    )
    
    foreach ($searchPath in $searchPaths) {
        $pythonExes = Get-ChildItem -Path $searchPath -Recurse -Name "python.exe" -ErrorAction SilentlyContinue
        foreach ($exe in $pythonExes) {
            $fullPath = Join-Path $searchPath $exe
            try {
                $testResult = & $fullPath --version 2>&1
                if ($LASTEXITCODE -eq 0 -and $testResult -match "Python (\d+\.\d+)") {
                    $majorMinor = [version]$matches[1]
                    if ($majorMinor -ge [version]"3.8") {
                        $pythonCmd = $fullPath
                        $pythonVersion = $testResult
                        break
                    }
                }
            } catch {
                continue
            }
        }
        if ($pythonCmd) { break }
    }
}

if (-not $pythonCmd) {
    Write-Host "Compatible Python version (3.8+) not found." -ForegroundColor Red
    Write-Host "Please install Python 3.8 or higher:" -ForegroundColor Yellow
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Or use Microsoft Store: python3" -ForegroundColor Yellow
    Write-Host "  Or use Chocolatey: choco install python" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found $pythonVersion at: $pythonCmd" -ForegroundColor Cyan

# Check for existing virtual environment
if (Test-Path ".venv") {
    Write-Host "Existing virtual environment found." -ForegroundColor Yellow
    Write-Host "Please remove or rename the .venv folder first:" -ForegroundColor Yellow
    Write-Host "  Rename-Item .venv .venv_old" -ForegroundColor Cyan
    Write-Host "Then run this script again." -ForegroundColor Yellow
    exit 1
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Cyan
& $pythonCmd -m venv .venv

# Verify virtual environment was created properly
if (-not (Test-Path ".venv\pyvenv.cfg")) {
    Write-Host "Failed to create virtual environment properly." -ForegroundColor Red
    exit 1
}

# Install dependencies using the virtual environment's Python
Write-Host "Installing dependencies..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -r requirements.txt

# Verify installation
Write-Host "Verifying installation..." -ForegroundColor Cyan
$testResult = & ".\.venv\Scripts\python.exe" -c "
try:
    import pandas, matplotlib, rich, pytesseract, PIL
    print('SUCCESS: All dependencies installed!')
except ImportError as e:
    print(f'ERROR: Missing dependency: {e}')
    exit(1)
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Environment setup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "To activate the virtual environment:" -ForegroundColor White
    Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To test the installation:" -ForegroundColor White
    Write-Host "   python test_ocr_utils.py --help" -ForegroundColor Yellow
} else {
    Write-Host "Environment setup failed during dependency verification." -ForegroundColor Red
    exit 1
}
