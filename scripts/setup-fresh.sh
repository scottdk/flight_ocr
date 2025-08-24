#!/bin/bash
# setup-fresh.sh - Create a completely fresh Flight OCR development environment
# Force removes existing environment and creates a new one from scratch

echo "🔄 Creating fresh Flight OCR development environment..."

# Detect OS for different approaches
OS=$(uname -s)
case $OS in
    Linux*)     MACHINE="Linux";;
    Darwin*)    MACHINE="macOS";;
    CYGWIN*)    MACHINE="Windows";;
    MINGW*)     MACHINE="Windows";;
    *)          MACHINE="Unknown"
esac

echo "📍 Detected: $MACHINE"

# Find suitable Python command
PYTHON_CMD=""
PYTHON_VERSION=""

# Define Python candidates based on OS
if [ "$MACHINE" = "macOS" ]; then
    PYTHON_CANDIDATES=("python3.13" "python3.12" "python3.11" "python3.10" "python3.9" "python3.8" "python3" "python")
elif [ "$MACHINE" = "Linux" ]; then
    PYTHON_CANDIDATES=("python3.13" "python3.12" "python3.11" "python3.10" "python3.9" "python3.8" "python3" "python")
else
    # Windows (Git Bash, WSL, etc.)
    PYTHON_CANDIDATES=("python" "python3" "py")
fi

# Find working Python
echo "🔍 Looking for Python 3.8+ installation..."
for cmd in "${PYTHON_CANDIDATES[@]}"; do
    if command -v "$cmd" >/dev/null 2>&1; then
        VERSION_OUTPUT=$($cmd --version 2>&1)
        if [[ $VERSION_OUTPUT =~ Python\ ([0-9]+\.[0-9]+) ]]; then
            VERSION_NUM="${BASH_REMATCH[1]}"
            # Use awk for version comparison (more portable than bash arithmetic)
            if awk "BEGIN {exit !($VERSION_NUM >= 3.8)}"; then
                PYTHON_CMD="$cmd"
                PYTHON_VERSION="$VERSION_OUTPUT"
                break
            else
                echo "⚠️  Found $VERSION_OUTPUT but requires Python 3.8 or higher"
            fi
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ No suitable Python installation found."
    echo "   Please install Python 3.8 or higher first."
    echo ""
    echo "   Installation options:"
    if [ "$MACHINE" = "macOS" ]; then
        echo "   • brew install python"
        echo "   • Download from https://www.python.org/"
    elif [ "$MACHINE" = "Linux" ]; then
        echo "   • sudo apt-get install python3 python3-venv  (Ubuntu/Debian)"
        echo "   • sudo yum install python3 python3-venv     (CentOS/RHEL)"
        echo "   • Download from https://www.python.org/"
    else
        echo "   • Download from https://www.python.org/"
        echo "   • Install via Windows Store"
    fi
    exit 1
fi

echo "✅ Found $PYTHON_VERSION at: $PYTHON_CMD"

# Force remove existing virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🗑️  Force removing existing virtual environment..."
    
    # Try to deactivate any conda environments first
    if command -v conda >/dev/null 2>&1; then
        conda deactivate 2>/dev/null || true
    fi
    
    # Deactivate current virtual environment if active
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "⚠️  Please deactivate the current virtual environment first:"
        echo "   Run: deactivate"
        echo "   Then run this script again."
        exit 1
    fi
    
    # Force remove with error handling
    if ! rm -rf .venv; then
        echo "❌ Could not remove .venv automatically. Please:"
        echo "   1. Close all terminals and editors using this environment"
        echo "   2. Manually delete the .venv folder: rm -rf .venv"
        echo "   3. Run this script again"
        exit 1
    fi
fi

# Create fresh virtual environment
echo "🔨 Creating virtual environment..."
if ! "$PYTHON_CMD" -m venv .venv; then
    echo "❌ Failed to create virtual environment"
    echo "   Make sure python3-venv is installed:"
    if [ "$MACHINE" = "Linux" ]; then
        echo "   sudo apt-get install python3-venv  (Ubuntu/Debian)"
        echo "   sudo yum install python3-venv     (CentOS/RHEL)"
    fi
    exit 1
fi

# Determine activation script path based on OS
if [ "$MACHINE" = "Windows" ]; then
    ACTIVATE_SCRIPT=".venv/Scripts/activate"
    PYTHON_VENV=".venv/Scripts/python"
else
    ACTIVATE_SCRIPT=".venv/bin/activate"
    PYTHON_VENV=".venv/bin/python"
fi

# Verify virtual environment was created properly
if [ ! -f "$ACTIVATE_SCRIPT" ]; then
    echo "❌ Virtual environment creation failed - activation script not found"
    exit 1
fi

# Install dependencies using the virtual environment's Python directly
echo "📦 Installing dependencies..."
"$PYTHON_VENV" -m pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    if ! "$PYTHON_VENV" -m pip install -r requirements.txt; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
else
    echo "⚠️  requirements.txt not found - skipping dependency installation"
fi

# Verify installation
echo "🔍 Verifying installation..."
if "$PYTHON_VENV" -c "import pandas, matplotlib, rich, pytesseract, PIL; print('✅ All dependencies installed successfully!')" 2>/dev/null; then
    echo "✅ Installation verification passed"
else
    echo "⚠️  Some optional dependencies may not be available, but core functionality should work"
fi

echo ""
echo "🎉 Fresh environment setup complete!"
echo ""
echo "📝 To activate the virtual environment:"
if [ "$MACHINE" = "Windows" ]; then
    echo "   source .venv/Scripts/activate"
else
    echo "   source .venv/bin/activate"
fi
echo ""
echo "🧪 To test your setup:"
echo "   python test_ocr_utils.py --help"
