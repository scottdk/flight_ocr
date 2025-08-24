# Installing Tesseract OCR

## Windows Installation

### Option 1: Download from GitHub (Recommended)
1. Go to https://github.com/UB-Mannheim/tesseract/wiki
2. Download the latest Windows installer (e.g., `tesseract-ocr-w64-setup-5.3.3.20231005.exe`)
3. Run the installer and make sure to check "Add to PATH" during installation
4. Restart your command prompt/PowerShell to refresh PATH

### Option 2: Using Chocolatey
```powershell
choco install tesseract
```

### Option 3: Using winget
```powershell
winget install --id UB-Mannheim.TesseractOCR
```

## Verification
After installation, verify tesseract is working:

```bash
tesseract --version
```

You should see output like:
```
tesseract 5.3.3
 leptonica-1.84.1
```

## Troubleshooting

### Tesseract not found in PATH
If you get "tesseract is not installed or it's not in your PATH", try:

1. **Find tesseract.exe**: Usually installed at:
   - `C:\Program Files\Tesseract-OCR\tesseract.exe`
   - `C:\Users\{username}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe`

2. **Add to PATH manually**:
   - Open Windows Settings → System → About → Advanced system settings
   - Click "Environment Variables"
   - Edit the "Path" variable for your user or system
   - Add the Tesseract installation directory (e.g., `C:\Program Files\Tesseract-OCR`)
   - Restart your terminal

3. **Set TESSDATA_PREFIX** (if needed):
   - Add environment variable: `TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata`

### Test with Sample Image
```bash
# Navigate to your project
cd c:\Users\scott\OneDrive\repos\flight_ocr

# Run the CLI tool
python -m flight_ocr.cli.main --img-dir data\input\raw --output-csv test_results.csv --debug
```

## Alternative: Using with Docker
If you prefer not to install tesseract locally:

```dockerfile
# Dockerfile
FROM python:3.11
RUN apt-get update && apt-get install -y tesseract-ocr
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "flight_ocr.cli.main"]
```
