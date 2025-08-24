# Quick Environment Setup Guide

## For New Machine Setup (Any Platform)

### Option 1: Automated Environment Setup

**Linux/macOS:**
```bash
git clone https://github.com/scottdk/flight_ocr.git
cd flight_ocr
chmod +x setup-env.sh
./setup-env.sh
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/scottdk/flight_ocr.git
cd flight_ocr
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser  # If needed
.\setup-env.ps1
```

### Option 2: Manual Setup

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/scottdk/flight_ocr.git
   cd flight_ocr
   ```

2. **Create virtual environment:**
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   
   # Linux/macOS  
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Tesseract OCR:**
   - **Windows:** Download from [Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki)
   - **Ubuntu:** `sudo apt-get install tesseract-ocr`
   - **macOS:** `brew install tesseract`

## Force Fresh Environment Setup

If you have environment issues or need a clean start:

**Windows:**
```powershell
.\setup-fresh.ps1
```

**Linux/macOS:**
```bash
chmod +x setup-fresh.sh
./setup-fresh.sh
```

> **⚠️ Warning:** Fresh setup will **forcefully delete** any existing `.venv` folder.

## Important Notes

- ⚠️ **Always delete `.venv` when moving between platforms** (Windows ↔ Linux)
- ✅ Virtual environments are platform-specific and must be recreated
- 📋 The `requirements.txt` file contains all necessary Python dependencies
- 🔧 Tesseract OCR must be installed separately on each system

## Verification

Test your setup:
```bash
python -c "import pandas, matplotlib, rich, pytesseract, PIL; print('✅ All dependencies ready!')"
python test_ocr_utils.py --help
```
