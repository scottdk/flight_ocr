#!/bin/bash
set -e

# Create virtual environment if it doesn't exist
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

# Activate the virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    # Install core requirements for this project
    pip install pillow pytesseract
fi

echo "Virtual environment setup complete. Activate with: source .venv/bin/activate"
