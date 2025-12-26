#!/bin/bash
# DCF Stock Analyzer - Mac/Linux Installer
# This script will set up everything automatically

echo "============================================================"
echo "DCF STOCK ANALYZER - AUTOMATIC INSTALLER"
echo "============================================================"
echo ""
echo "This installer will:"
echo "1. Check if Python is installed"
echo "2. Install required libraries"
echo "3. Test the installation"
echo "4. Help you get started"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

echo ""
echo "============================================================"
echo "STEP 1: Checking Python Installation"
echo "============================================================"
echo ""

# Try python3 first (most common on Mac/Linux)
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    echo "[ERROR] Python is not installed!"
    echo ""
    echo "Please install Python first:"
    echo ""
    echo "Mac:"
    echo "  1. Go to: https://www.python.org/downloads/"
    echo "  2. Download Python 3.12 or higher"
    echo "  3. Run the installer"
    echo ""
    echo "Linux (Ubuntu/Debian):"
    echo "  sudo apt update"
    echo "  sudo apt install python3 python3-pip"
    echo ""
    echo "Then run this installer again."
    exit 1
fi

echo "[SUCCESS] Python is installed!"
$PYTHON_CMD --version
echo ""

echo "============================================================"
echo "STEP 2: Installing Required Libraries"
echo "============================================================"
echo ""
echo "This may take 1-2 minutes..."
echo ""

$PYTHON_CMD -m pip install --upgrade pip --break-system-packages 2>/dev/null || $PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install -r requirements.txt --break-system-packages 2>/dev/null || $PYTHON_CMD -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to install libraries!"
    echo "Try running this command manually:"
    echo "    $PYTHON_CMD -m pip install -r requirements.txt"
    echo ""
    exit 1
fi

echo ""
echo "[SUCCESS] Libraries installed!"
echo ""

echo "============================================================"
echo "STEP 3: Testing Installation"
echo "============================================================"
echo ""

$PYTHON_CMD test_installation.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Installation test failed!"
    echo "Please check the error messages above."
    echo ""
    exit 1
fi

echo ""
echo "============================================================"
echo "INSTALLATION COMPLETE!"
echo "============================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Get a FREE API key:"
echo "   Go to: https://financialmodelingprep.com/developer/docs/"
echo "   Sign up and copy your API key"
echo ""
echo "2. Save your API key (optional but recommended):"
echo "   echo 'YOUR_API_KEY' > api_key.txt"
echo ""
echo "3. Run your first analysis:"
echo "   ./run_analysis.sh analyze AAPL"
echo "   OR"
echo "   $PYTHON_CMD main.py --api-key YOUR_KEY analyze AAPL"
echo ""
echo "============================================================"
echo ""

# Create helper script
cat > run_analysis.sh << 'EOF'
#!/bin/bash
# Quick launcher for DCF analysis

# Detect python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

if [ -f api_key.txt ]; then
    API_KEY=$(cat api_key.txt)
    $PYTHON_CMD main.py --api-key "$API_KEY" "$@"
else
    echo "No api_key.txt found!"
    echo "Either create api_key.txt with your API key"
    echo "OR run: $PYTHON_CMD main.py --api-key YOUR_KEY analyze TICKER"
fi
EOF

chmod +x run_analysis.sh

echo "Created helper script: run_analysis.sh"
echo ""
echo "Installation complete! Press Enter to exit..."
read
