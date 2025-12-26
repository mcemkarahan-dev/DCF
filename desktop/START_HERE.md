# 🚀 QUICK INSTALL - START HERE

## You Only Need To Do 2 Things:

### 1️⃣ Install Python (if you don't have it)
### 2️⃣ Run the installer for your system

---

## Step 1: Do You Have Python?

### Quick Test:

**Windows:**
- Press `Windows Key + R`
- Type `cmd` and press Enter
- Type `python --version` and press Enter
- See a version number like `Python 3.12.x`? ✅ **You have Python! Skip to Step 2.**
- See an error? ❌ **Install Python below**

**Mac:**
- Press `Command + Space`
- Type `terminal` and press Enter
- Type `python3 --version` and press Enter
- See a version number? ✅ **You have Python! Skip to Step 2.**
- See an error? ❌ **Install Python below**

**Linux:**
- Open Terminal
- Type `python3 --version` and press Enter
- See a version number? ✅ **You have Python! Skip to Step 2.**
- See an error? ❌ **Install Python below**

---

## Installing Python (if needed)

### Windows:
1. Go to: https://www.python.org/downloads/
2. Click the big yellow "Download Python" button
3. Run the downloaded file
4. ⚠️ **CRITICAL:** Check the box "Add Python to PATH"
5. Click "Install Now"
6. Wait 2-3 minutes
7. Done!

### Mac:
1. Go to: https://www.python.org/downloads/
2. Click "Download Python"
3. Run the downloaded .pkg file
4. Click through all the prompts
5. Done!

### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install python3 python3-pip
```

---

## Step 2: Run The Installer

Now navigate to the `dcf_analyzer` folder and run the installer:

### Windows:
1. Open the `dcf_analyzer` folder
2. **Double-click:** `install_windows.bat`
3. Follow the on-screen instructions
4. Done! ✅

### Mac:
1. Open the `dcf_analyzer` folder in Finder
2. Right-click the folder and select "New Terminal at Folder"
3. Type: `./install_mac_linux.sh`
4. Press Enter
5. Follow the on-screen instructions
6. Done! ✅

### Linux:
1. Open Terminal
2. Navigate to dcf_analyzer folder:
   ```bash
   cd /path/to/dcf_analyzer
   ```
3. Run installer:
   ```bash
   ./install_mac_linux.sh
   ```
4. Follow the on-screen instructions
5. Done! ✅

---

## 🎨 BONUS: Graphical User Interface (GUI)

**Don't like command line? Use the GUI instead!**

After installation, you can launch a simple graphical interface:

### Windows:
**Double-click:** `launch_gui_windows.bat`

### Mac/Linux:
```bash
./launch_gui_mac_linux.sh
```

**Or run directly:**
```bash
python3 gui_launcher.py
```

The GUI lets you:
- ✅ Analyze stocks with a simple form
- ✅ Run batch analyses with dropdowns
- ✅ Screen for opportunities with sliders
- ✅ View all output in one window
- ✅ No command line needed!

**Perfect for beginners!** 🎯

---

## What The Installer Does

The installer will:
1. ✅ Check if Python is installed correctly
2. ✅ Install required libraries (requests, pandas)
3. ✅ Test that everything works
4. ✅ Create helper scripts for easy use
5. ✅ Show you next steps

**Total time: 5 minutes** ⏱️

---

## After Installation

You'll need a **FREE API key** to fetch stock data:

1. Go to: https://financialmodelingprep.com/developer/docs/
2. Click "Get Free API Key"
3. Sign up (free - 250 requests per day)
4. Copy your API key

### Save Your API Key (Recommended):

Create a file called `api_key.txt` in the dcf_analyzer folder and paste your key into it.

Then you can run analyses easily:

**Windows:**
```
run_analysis.bat analyze AAPL
```

**Mac/Linux:**
```bash
./run_analysis.sh analyze AAPL
```

---

## Your First Analysis

### Option 1: Using Helper Script (Easiest)

If you saved your API key in `api_key.txt`:

**Windows:**
```
run_analysis.bat analyze AAPL
run_analysis.bat analyze MSFT
run_analysis.bat screen --min-discount 15
```

**Mac/Linux:**
```bash
./run_analysis.sh analyze AAPL
./run_analysis.sh analyze MSFT
./run_analysis.sh screen --min-discount 15
```

### Option 2: Direct Command

**Windows:**
```
python main.py --api-key YOUR_KEY_HERE analyze AAPL
```

**Mac/Linux:**
```bash
python3 main.py --api-key YOUR_KEY_HERE analyze AAPL
```

---

## What You'll See

```
============================================================
Analyzing AAPL
============================================================
Fetching data for AAPL...

Company: Apple Inc.
Sector: Technology
Current Price: $180.50
Intrinsic Value: $225.30
Discount/Premium: +24.8%
*** UNDERVALUED - Trading 24.8% below intrinsic value ***
```

🎉 **That's it! You're analyzing stocks!**

---

## Common Commands

```bash
# Analyze stocks
run_analysis.sh analyze AAPL
run_analysis.sh analyze MSFT

# Analyze multiple stocks from an exchange
python3 main.py --api-key YOUR_KEY batch NASDAQ --limit 20

# Screen for opportunities
run_analysis.sh screen --min-discount 15 --top 20

# View trends over time
run_analysis.sh trending AAPL --periods 5

# Export results
run_analysis.sh export --output results.json
```

---

## Need Help?

- **Full Documentation:** See `README.md`
- **Visual Guide:** See `VISUAL_WALKTHROUGH.md`
- **Quick Reference:** See `CHEAT_SHEET.md`
- **Test Install:** Run `python test_installation.py`

---

## Troubleshooting

### Installer won't run (Windows)
- Right-click `install_windows.bat`
- Select "Run as administrator"

### Installer won't run (Mac/Linux)
```bash
chmod +x install_mac_linux.sh
./install_mac_linux.sh
```

### "Python not found"
- Make sure Python is installed (Step 1)
- On Windows: make sure you checked "Add to PATH" during install
- Restart your terminal/command prompt

### Still stuck?
Run the test:
```bash
python test_installation.py
```

This will show exactly what's wrong.

---

## That's All You Need! 🎯

1. ✅ Install Python (if needed)
2. ✅ Run the installer
3. ✅ Get API key
4. ✅ Start analyzing stocks!

**Total setup time: 15 minutes**

Happy investing! 📊💰
