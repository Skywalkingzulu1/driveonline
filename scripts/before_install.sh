#!/usr/bin/env bash
set -e

echo "=== BeforeInstall Hook ==="
echo "Installing Python dependencies..."
pip install --quiet -r requirements.txt
echo "Dependencies installed."