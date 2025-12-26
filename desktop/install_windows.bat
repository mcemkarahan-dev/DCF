@echo off
REM DCF Stock Analyzer - Windows Installer
REM This script will set up everything automatically

echo ============================================================
echo DCF STOCK ANALYZER - AUTOMATIC INSTALLER
echo ============================================================
echo.
echo This installer will:
echo 1. Check if Python is installed
echo 2. Install required libraries
echo 3. Test the installation
echo 4. Help you get started
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul

echo.
echo ============================================================
echo STEP 1: Checking Python Installation
echo ============================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python first:
    echo 1. Go to: https://www.python.org/downloads/
    echo 2. Download Python 3.12 or higher
    echo 3. Run installer and CHECK "Add Python to PATH"
    echo 4. Run this installer again
    echo.
    pause
    exit /b 1
)

echo [SUCCESS] Python is installed!
python --version
echo.

echo ============================================================
echo STEP 2: Installing Required Libraries
echo ============================================================
echo.
echo This may take 1-2 minutes...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install libraries!
    echo Try running this command manually:
    echo     python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Libraries installed!
echo.

echo ============================================================
echo STEP 3: Testing Installation
echo ============================================================
echo.

python test_installation.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation test failed!
    echo Please check the error messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo INSTALLATION COMPLETE!
echo ============================================================
echo.
echo GOOD NEWS: This app now uses Yahoo Finance!
echo - No API key required
echo - Completely free
echo - No daily limits
echo.
echo Next steps:
echo.
echo 1. Launch the app:
echo    Double-click: launch_gui_windows.bat
echo    OR
echo    Type: run_analysis.bat analyze AAPL
echo.
echo 2. In the GUI, you can leave the API key field empty
echo    (or put anything - it's not used with Yahoo Finance)
echo.
echo ============================================================
echo.

REM Create a helper script for running analyses
echo @echo off > run_analysis.bat
echo REM Quick launcher for DCF analysis >> run_analysis.bat
echo. >> run_analysis.bat
echo if exist api_key.txt ( >> run_analysis.bat
echo     set /p API_KEY=^<api_key.txt >> run_analysis.bat
echo     python main.py --api-key %%API_KEY%% %%* >> run_analysis.bat
echo ) else ( >> run_analysis.bat
echo     echo No api_key.txt found! >> run_analysis.bat
echo     echo Either create api_key.txt with your API key >> run_analysis.bat
echo     echo OR run: python main.py --api-key YOUR_KEY analyze TICKER >> run_analysis.bat
echo ) >> run_analysis.bat

echo Created helper script: run_analysis.bat
echo.
echo Would you like to open the installation guide? (Y/N)
set /p OPEN_GUIDE=
if /i "%OPEN_GUIDE%"=="Y" (
    start INSTALLATION_GUIDE.md
)

echo.
echo Press any key to exit...
pause >nul
