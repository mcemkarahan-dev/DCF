@echo off
REM Quick Fix - Switch to Yahoo Finance (No API Key Needed!)

echo ============================================================
echo SWITCHING TO YAHOO FINANCE DATA SOURCE
echo ============================================================
echo.
echo This will install yfinance and switch the app to use
echo Yahoo Finance instead of Financial Modeling Prep.
echo.
echo Benefits:
echo - No API key required!
echo - Completely free
echo - No daily limits
echo - Works immediately
echo.
echo Press any key to continue...
pause >nul

echo.
echo Installing yfinance...
python -m pip install yfinance

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install yfinance
    echo Try running: python -m pip install yfinance
    pause
    exit /b 1
)

echo.
echo [SUCCESS] yfinance installed!
echo.
echo ============================================================
echo SETUP COMPLETE
echo ============================================================
echo.
echo The app now uses Yahoo Finance - no API key needed!
echo.
echo You can now:
echo 1. Launch the GUI: launch_gui_windows.bat
echo 2. Or use command line: run_analysis.bat analyze AAPL
echo.
echo Note: You can leave the API key field empty or put anything.
echo It's not used with Yahoo Finance.
echo.
echo Press any key to exit...
pause >nul
