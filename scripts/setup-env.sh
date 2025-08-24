#!/bin/bash
# setup-env.sh - Universal environment setup script for Flight OCR project
# Creates virtual environment and installs dependencies on Linux, macOS, and Windows (Git Bash)

set -e  # Exit on any error

echo "🚀 Setting up Flight OCR development environment..."

# Detect operating system and find compatible Python
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
    PYTHON_CANDIDATES=("python" "python3" "py")
    VENV_ACTIVATE=".venv/Scripts/activate"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    PYTHON_CANDIDATES=("python3" "python" "python3.8" "python3.9" "python3.10" "python3.11" "python3.12" "python3.13")
    VENV_ACTIVATE=".venv/bin/activate"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    PYTHON_CANDIDATES=("python3" "python" "python3.8" "python3.9" "python3.10" "python3.11" "python3.12" "python3.13")
    VENV_ACTIVATE=".venv/bin/activate"
else
    echo "❌ Unsupported operating system: $OSTYPE"
    exit 1
fi

echo "📋 Detected OS: $OS"

# Find compatible Python version (3.8+)
PYTHON_CMD=""
for cmd in "${PYTHON_CANDIDATES[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        VERSION_OUTPUT=$($cmd --version 2>&1)
        if [[ $VERSION_OUTPUT =~ Python\ ([0-9]+)\.([0-9]+) ]]; then
            MAJOR=${BASH_REMATCH[1]}
            MINOR=${BASH_REMATCH[2]}
            if [[ $MAJOR -gt 3 || ($MAJOR -eq 3 && $MINOR -ge 8) ]]; then
                PYTHON_CMD=$cmd
                PYTHON_VERSION=$VERSION_OUTPUT
                break
            else
                echo "⚠️  Found $VERSION_OUTPUT but requires Python 3.8+"
            fi
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo "❌ Compatible Python version (3.8+) not found."
    echo "Please install Python 3.8+ first."
    exit 1
fi

echo "🐍 Found $PYTHON_VERSION using: $PYTHON_CMD"

# Remove existing virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🧹 Removing existing virtual environment..."
    rm -rf .venv
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
$PYTHON_CMD -m venv .venv

# Activate virtual environment and install dependencies
echo "⚡ Activating virtual environment and installing dependencies..."
source $VENV_ACTIVATE
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
echo "✅ Verifying installation..."
python -c "import pandas, matplotlib, rich, pytesseract, PIL; print('All Python dependencies installed successfully!')"

echo ""
echo "🎉 Environment setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Activate the virtual environment:"
if [[ "$OS" == "windows" ]]; then
    echo "   .venv\\Scripts\\activate.bat        (Command Prompt)"
    echo "   .venv\\Scripts\\Activate.ps1        (PowerShell)"
else
    echo "   source .venv/bin/activate"
fi
echo ""
echo "2. Install Tesseract OCR engine:"
if [[ "$OS" == "windows" ]]; then
    echo "   Download from: https://github.com/UB-Mannheim/tesseract/wiki"
elif [[ "$OS" == "linux" ]]; then
    echo "   sudo apt-get install tesseract-ocr"
elif [[ "$OS" == "macos" ]]; then
    echo "   brew install tesseract"
fi
echo ""
echo "3. Test the installation:"
echo "   python test_ocr_utils.py --help"
echo ""
echo "📚 See README.md for detailed usage instructions."
