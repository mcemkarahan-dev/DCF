@echo off
REM Launch the DCF Analyzer GUI

echo Starting DCF Stock Analyzer GUI...
python gui_launcher.py

if %errorlevel% neq 0 (
    echo.
    echo Error launching GUI. Make sure Python is installed.
    echo Press any key to exit...
    pause >nul
)
