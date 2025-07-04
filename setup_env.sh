#!/bin/bash
set -e

VENV_DIR="${HOME}/busdisplay/venv"

echo "Setting up Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "${HOME}/busdisplay/requirements.txt"
echo "Virtual environment setup complete."