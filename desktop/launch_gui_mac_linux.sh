#!/bin/bash
# Launch the DCF Analyzer GUI

echo "Starting DCF Stock Analyzer GUI..."

# Detect python command
if command -v python3 &> /dev/null; then
    python3 gui_launcher.py
elif command -v python &> /dev/null; then
    python gui_launcher.py
else
    echo "Error: Python not found. Please install Python first."
    exit 1
fi
