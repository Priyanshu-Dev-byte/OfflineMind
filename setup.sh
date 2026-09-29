#!/usr/bin/env bash
# ==============================================================================
# OfflineMind - One-Click Setup Script (macOS / Linux Fallback)
# ==============================================================================

set -e

echo "================================================================="
echo "  OfflineMind - Private On-Device AI Notes Setup"
echo "================================================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required. Please install Python 3.11+."
    exit 1
fi

echo "[✓] Python version: $(python3 --version)"

# Create virtualenv
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
source venv/bin/activate

echo "[*] Upgrading pip..."
pip install --upgrade pip wheel setuptools --quiet

echo "[*] Installing dependencies..."
pip install -r requirements.txt

echo "================================================================="
echo "  Setup Completed Successfully!"
echo "  To launch OfflineMind, run:"
echo "    source venv/bin/activate && streamlit run app/main.py"
echo "================================================================="
