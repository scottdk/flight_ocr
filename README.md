# Flight OCR Project

A Python project for OCR (Optical Character Recognition) preprocessing and text extraction from flight-related images using Tesseract.

## Features

- 🖼️ **Advanced Image Preprocessing**: Configurable threshold optimization for optimal OCR results
- 🔍 **Robust OCR Text Extraction**: Tesseract integration with smart preprocessing pipelines
- 🧹 **Intelligent Text Cleaning**: Automated OCR output cleaning and validation
- ⚡ **High-Performance Batch Processing**: Multiprocessing support for efficient bulk operations
- 🎯 **Threshold Optimization Analysis**: Automated analysis to find optimal preprocessing parameters
- 💾 **Smart Caching System**: Intelligent caching to avoid reprocessing with configurable refresh
- 📊 **Rich Visualization & Reporting**: Detailed analysis reports with charts and tables
- 📁 **Flexible Export Options**: CSV export with customizable output directories
- 🖥️ **Dual-Mode CLI**: Modern subcommand interface with full backward compatibility
- 🧪 **Mock Testing Mode**: Test workflows without requiring Tesseract installation

## Requirements

- **Python 3.8 or higher** (automatically detected during setup)
  - Supports Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13+
  - Works with system Python, Microsoft Store Python, or Anaconda Python
- **Tesseract OCR engine** (must be installed separately)

## Setup Instructions

### Option 1: Automated Environment Setup (Recommended)

**Linux/macOS:**
```bash
git clone https://github.com/scottdk/flight_ocr.git
cd flight_ocr
chmod +x scripts/setup-env.sh
./scripts/setup-env.sh
```

**Windows:**
```powershell
git clone https://github.com/scottdk/flight_ocr.git
cd flight_ocr
.\scripts\setup-env.ps1
```

### Force Fresh Environment Setup

If you have environment issues or need a completely clean start (e.g., corrupted dependencies, platform switching), use the fresh setup scripts:

**Linux/macOS:**
```bash
chmod +x scripts/setup-fresh.sh
./scripts/setup-fresh.sh
```

**Windows:**
```powershell
.\scripts\setup-fresh.ps1
```

> **Note:** Fresh setup will **forcefully delete** any existing `.venv` folder and create a completely new environment from scratch.

### Option 2: Manual Setup

### 1. Clone the Repository
```bash
git clone https://github.com/scottdk/flight_ocr.git
cd flight_ocr
```

### 2. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR Engine

**Windows:**
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location (usually `C:\Program Files\Tesseract-OCR\`)
3. Add to PATH or update `pytesseract.pytesseract.tesseract_cmd` in code

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS (Homebrew):**
```bash
brew install tesseract
```

### 5. Verify Installation
```bash
python -c "import pandas, matplotlib, rich, pytesseract, PIL; print('✅ All dependencies installed successfully!')"
tesseract --version
```

## Project Structure

```
flight_ocr/
├── flight_ocr/                    # Main package
│   ├── __init__.py
│   ├── core/                      # Core business logic
│   │   ├── __init__.py
│   │   ├── ocr_engine.py         # Main OCR processing engine
│   │   ├── image_processor.py    # Image preprocessing utilities
│   │   └── data_extractor.py     # Data extraction and logging
│   ├── utils/                     # Utility modules
│   │   ├── __init__.py
│   │   ├── cache.py              # Smart caching system
│   │   ├── cleaning.py           # OCR text cleaning utilities
│   │   ├── file_io.py            # File I/O operations
│   │   └── mock_ocr.py           # Mock OCR for testing
│   ├── analysis/                  # Analysis tools
│   │   ├── __init__.py
│   │   └── threshold_optimizer.py # OCR threshold optimization
│   └── cli/                       # Command-line interface
│       ├── __init__.py
│       ├── main.py               # Main CLI with dual-mode support
│       └── threshold.py          # Threshold optimization CLI
├── data/                          # Data directories (created during setup)
│   ├── input/raw/                # Input images
│   ├── cache/                    # Cache files
│   └── output/                   # Output files
│       ├── csv/                  # CSV results
│       ├── processed_images/     # Debug images
│       └── reports/              # Threshold analysis reports
├── config/                        # Configuration files
│   ├── default.yaml              # Default configuration
│   ├── development.yaml          # Development settings
│   └── production.yaml           # Production settings
├── scripts/                       # Setup and utility scripts
│   ├── setup-env.sh/.ps1         # Environment setup
│   └── setup-fresh.sh/.ps1       # Fresh environment creation
├── docs/                          # Documentation
│   ├── README.md                 # Detailed documentation
│   ├── QUICKSTART.md             # Quick start guide
│   └── TESSERACT_INSTALL.md      # Tesseract installation guide
├── images/                        # Sample images for testing
├── pyproject.toml                # Modern Python project configuration
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
└── README.md                     # This file
```

## Usage

### Modern CLI with Subcommands (Recommended)

```bash
# OCR Processing
python -m flight_ocr.cli.main process --img-dir data/input/raw --output-csv results.csv
python -m flight_ocr.cli.main process --mock --debug  # Test with mock data

# Threshold Optimization Analysis
python -m flight_ocr.cli.main optimize-thresholds --max-workers 8
python -m flight_ocr.cli.main optimize-thresholds --no-refresh-cache

# Get help for any command
python -m flight_ocr.cli.main --help
python -m flight_ocr.cli.main process --help
python -m flight_ocr.cli.main optimize-thresholds --help
```

### Legacy CLI (Backward Compatible)

```bash
# Old syntax still works for existing scripts
python -m flight_ocr.cli.main --debug --img-dir data/input/raw --output-csv results.csv
python -m flight_ocr.cli.main --mock --debug
```

### Advanced: Threshold Optimization Analysis

The Flight OCR project includes a sophisticated threshold optimization tool that automatically finds the best OCR preprocessing parameters:

```bash
# Run threshold optimization with default settings
python -m flight_ocr.cli.main optimize-thresholds

# Use more workers for faster processing
python -m flight_ocr.cli.main optimize-thresholds --max-workers 8

# Skip cache refresh to use existing analysis
python -m flight_ocr.cli.main optimize-thresholds --no-refresh-cache
```

This analysis:
- 🔍 Tests multiple threshold combinations on your image set
- 📊 Generates detailed reports showing OCR quality metrics
- 🎯 Identifies optimal parameters for your specific image types
- 💾 Caches results for efficient re-analysis
- ⚡ Uses multiprocessing for fast batch analysis

### Custom Image Processing

```bash
# Use the package programmatically
python -c "
from flight_ocr.core.ocr_engine import FlightGridOCR
from flight_ocr.core.data_extractor import configure_logging

configure_logging(debug=True)  
ocr = FlightGridOCR('data/input/raw', debug=True)
ocr.process_images()
ocr.write_csv('my_results.csv')
"
```

## Dependencies

### Required
- `pillow` - Image processing
- `pytesseract` - Tesseract OCR wrapper

### Optional (Enhanced Features)
- `pandas` - Data manipulation and CSV export
- `matplotlib` - Chart generation
- `rich` - Enhanced terminal output with colors and tables

## Development

### Code Style
This project follows PEP 8 style guidelines with:
- All imports at the top level
- Comprehensive docstrings
- Type hints where appropriate
- Error handling for optional dependencies

### Testing
```bash
python test_ocr_utils.py
```

## Troubleshooting

### Common Issues

1. **Tesseract not found**
   ```python
   # Add to your Python code if Tesseract is not in PATH
   import pytesseract
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows
   ```

2. **Import errors after switching platforms**
   - Delete `.venv` folder
   - Recreate virtual environment using steps above
   - Reinstall dependencies

3. **Permission errors on Windows**
   - Run PowerShell as Administrator
   - Or use: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure code follows PEP 8
5. Test your changes
6. Submit a pull request

## License

This project is licensed under the MIT License.
