#!/usr/bin/env bash
# emdash_analysis.sh - Run emdash test suite and density analysis on the testbed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo " 1. Running Test Suite (pytest)"
echo "========================================================================"
if command -v uv >/dev/null 2>&1; then
    uv run --with pytest pytest -o console_output_style=count
elif command -v pytest >/dev/null 2>&1; then
    pytest -o console_output_style=count
elif python3 -m pytest --version >/dev/null 2>&1; then
    python3 -m pytest -o console_output_style=count
else
    echo "Warning: pytest not found via uv or python3; skipping unit tests." >&2
fi

echo ""
echo "========================================================================"
echo " 2. Running Em Dash Density Analysis on Melville / 19th-Century Testbed"
echo "========================================================================"

if [ ! -d "melville" ] || [ -z "$(ls -A melville/*.txt 2>/dev/null)" ]; then
    echo "melville/ directory missing or empty. Running ./pull_melville.sh..."
    if [ -x "./pull_melville.sh" ]; then
        ./pull_melville.sh
    else
        bash ./pull_melville.sh
    fi
fi

./detect_emdash.py --density melville/*.txt

echo ""
echo "Analysis complete."

