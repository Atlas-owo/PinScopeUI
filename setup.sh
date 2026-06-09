#!/bin/bash
set -e

cd "$(dirname "$0")/pinscope"

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Upgrading pip..."
.venv/bin/pip install --upgrade pip -q

echo "Installing dependencies..."
.venv/bin/pip install PySide6 pyqtgraph numpy PyOpenGL -q

echo ""
echo "Done. Run the app with:"
echo "  ./run.sh          — design mode"
echo "  ./run_touch.sh    — touchscreen mode"
