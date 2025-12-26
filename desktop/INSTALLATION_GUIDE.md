# DCF Stock Analyzer - Complete Beginner's Installation Guide

This guide assumes you have NEVER used Python before. We'll walk through everything step-by-step.

---

## Step 1: Install Python (15 minutes)

### For Windows:

1. **Download Python:**
   - Go to: https://www.python.org/downloads/
   - Click the big yellow "Download Python 3.12.x" button
   - Save the installer file (python-3.12.x-amd64.exe)

2. **Run the Installer:**
   - Double-click the downloaded file
   - ⚠️ **IMPORTANT**: Check the box "Add Python to PATH" at the bottom
   - Click "Install Now"
   - Wait for installation to complete (2-3 minutes)
   - Click "Close"

3. **Verify Installation:**
   - Press `Windows Key + R`
   - Type `cmd` and press Enter
   - In the black window that opens, type:
   ```
   python --version
   ```
   - You should see something like: `Python 3.12.1`
   - If you see an error, restart your computer and try again

### For Mac:

1. **Download Python:**
   - Go to: https://www.python.org/downloads/
   - Click "Download Python 3.12.x"
   - Save the installer file (python-3.12.x-macos11.pkg)

2. **Run the Installer:**
   - Double-click the downloaded .pkg file
   - Click "Continue" through all the prompts
   - Click "Install"
   - Enter your Mac password when prompted
   - Wait for installation to complete
   - Click "Close"

3. **Verify Installation:**
   - Press `Command + Space`
   - Type `terminal` and press Enter
   - In the window that opens, type:
   ```
   python3 --version
   ```
   - You should see something like: `Python 3.12.1`

### For Linux (Ubuntu/Debian):

1. **Open Terminal:**
   - Press `Ctrl + Alt + T`

2. **Install Python:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   ```
   - Enter your password when prompted
   - Type `y` when asked to continue

3. **Verify Installation:**
   ```bash
   python3 --version
   ```
   - You should see something like: `Python 3.10.x` or higher

---

## Step 2: Download the DCF Analyzer (5 minutes)

You should have already downloaded the `dcf_analyzer` folder. If not, make sure you have it.

1. **Find the folder:**
   - You should see a folder named `dcf_analyzer`
   - It contains files like: main.py, database.py, README.md, etc.

2. **Move it to a good location:**
   
   **Windows:**
   - Move the `dcf_analyzer` folder to `C:\Users\YourName\Documents\`
   - (Replace YourName with your actual username)
   
   **Mac:**
   - Move the `dcf_analyzer` folder to `/Users/YourName/Documents/`
   
   **Linux:**
   - Move the `dcf_analyzer` folder to `/home/yourname/Documents/`

---

## Step 3: Open Command Line in the Right Place (5 minutes)

### Windows:

1. Open File Explorer
2. Navigate to where you put the `dcf_analyzer` folder
3. Click inside the `dcf_analyzer` folder (you should see main.py, database.py, etc.)
4. Click in the address bar at the top (where it shows the path)
5. Type `cmd` and press Enter
6. A command prompt will open already in the correct folder

**Verify you're in the right place:**
```
dir
```
You should see files like main.py, database.py, README.md

### Mac:

1. Open Finder
2. Navigate to where you put the `dcf_analyzer` folder
3. Right-click (or Control-click) on the `dcf_analyzer` folder
4. While holding the `Option` key, you'll see "Copy dcf_analyzer as Pathname"
5. Click that to copy the path
6. Press `Command + Space`, type `terminal`, press Enter
7. Type `cd ` (with a space after cd)
8. Press `Command + V` to paste the path
9. Press Enter

**Verify you're in the right place:**
```bash
ls
```
You should see files like main.py, database.py, README.md

### Linux:

1. Open File Manager
2. Navigate to where you put the `dcf_analyzer` folder
3. Right-click inside the folder
4. Click "Open in Terminal"

**Verify you're in the right place:**
```bash
ls
```
You should see files like main.py, database.py, README.md

---

## Step 4: Install Required Python Libraries (10 minutes)

Now we'll install the libraries the program needs.

### Windows:
```
pip install -r requirements.txt
```

### Mac/Linux:
```bash
pip3 install -r requirements.txt
```

**What you'll see:**
- Lots of text scrolling by
- Lines saying "Downloading..." and "Installing..."
- Should take 30 seconds to 2 minutes
- When it's done, you'll see your command prompt again

**If you get an error:**
- On Windows, try: `python -m pip install -r requirements.txt`
- On Mac/Linux, try: `python3 -m pip install -r requirements.txt`

---

## Step 5: Test the Installation (5 minutes)

Let's make sure everything is working:

### Windows:
```
python test_installation.py
```

### Mac/Linux:
```bash
python3 test_installation.py
```

**What you should see:**
```
============================================================
DCF ANALYZER - INSTALLATION TEST
============================================================
Testing imports...
✓ All imports successful

Testing database...
✓ Database operations successful

Testing DCF calculator...
✓ DCF calculation successful (EV: $75,942,750,666)

Testing screener...
✓ Screener operations successful

Testing configuration...
✓ Configuration presets loaded

============================================================
RESULTS: 5 passed, 0 failed
============================================================

✓ All tests passed! Installation is successful.
```

✅ **If you see "5 passed, 0 failed" - YOU'RE DONE WITH INSTALLATION!**

❌ **If you see errors:**
- Make sure you're in the dcf_analyzer folder (step 3)
- Make sure you ran the pip install command (step 4)
- Restart your terminal and try again

---

## Step 6: Get Your Free API Key (10 minutes)

The program needs to get stock data from somewhere. We'll use Financial Modeling Prep's free API.

1. **Go to the website:**
   - Open your browser
   - Go to: https://financialmodelingprep.com/developer/docs/

2. **Sign up:**
   - Click "Get Free API Key" or "Sign Up"
   - Enter your email and create a password
   - Click "Sign Up"
   - Check your email for a confirmation link
   - Click the confirmation link

3. **Get your API key:**
   - Log in to the website
   - Go to your Dashboard
   - You'll see "Your API Key" - it's a long string of letters and numbers
   - Copy this key - you'll need it!

**Example API key looks like:** `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

⚠️ **Keep this key private!** Don't share it with anyone.

---

## Step 7: Run Your First Analysis! (5 minutes)

Now let's analyze a stock!

### Windows:
```
python main.py --api-key YOUR_API_KEY_HERE analyze AAPL
```

### Mac/Linux:
```bash
python3 main.py --api-key YOUR_API_KEY_HERE analyze AAPL
```

⚠️ **Replace `YOUR_API_KEY_HERE` with your actual API key from Step 6**

**Example:**
```
python main.py --api-key a1b2c3d4e5f6g7h8i9j0 analyze AAPL
```

**What you'll see:**
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

🎉 **CONGRATULATIONS!** You just ran your first DCF analysis!

---

## Quick Reference: Common Commands

Once you're set up, here are the main commands you'll use:

### Analyze a Single Stock
**Windows:**
```
python main.py --api-key YOUR_KEY analyze MSFT
```
**Mac/Linux:**
```bash
python3 main.py --api-key YOUR_KEY analyze MSFT
```

### Analyze Multiple Stocks
**Windows:**
```
python main.py --api-key YOUR_KEY batch NASDAQ --limit 20
```
**Mac/Linux:**
```bash
python3 main.py --api-key YOUR_KEY batch NASDAQ --limit 20
```

### Screen for Opportunities
**Windows:**
```
python main.py screen --min-discount 15 --top 20
```
**Mac/Linux:**
```bash
python3 main.py screen --min-discount 15 --top 20
```

### View Trending Analysis
**Windows:**
```
python main.py trending AAPL --periods 5
```
**Mac/Linux:**
```bash
python3 main.py trending AAPL --periods 5
```

---

## Troubleshooting Common Issues

### Issue 1: "python is not recognized" (Windows)
**Problem:** You didn't check "Add Python to PATH" during installation.

**Solution:**
1. Uninstall Python (Control Panel → Programs → Uninstall)
2. Download and install again
3. Make sure to check "Add Python to PATH" this time

### Issue 2: "command not found: python3" (Mac/Linux)
**Problem:** Python not installed or wrong command.

**Solution:**
- Try `python` instead of `python3`
- Or reinstall Python following Step 1

### Issue 3: "No module named 'requests'"
**Problem:** You didn't install the required libraries.

**Solution:**
- Go back to Step 4 and run the pip install command

### Issue 4: "Could not fetch data for AAPL"
**Problem:** API key is wrong or you've hit the rate limit.

**Solutions:**
- Double-check your API key (copy-paste it carefully)
- Make sure there are no extra spaces
- Free tier limits: 250 requests/day - wait until tomorrow if you hit the limit

### Issue 5: "Access denied" or "Permission error"
**Problem:** You don't have permission to write files in that folder.

**Solution:**
- Move the dcf_analyzer folder to your Documents folder
- On Windows, avoid putting it in C:\Program Files

---

## Tips for Beginners

### Saving Your API Key
Instead of typing your API key every time, you can save it:

1. **Create a text file in the dcf_analyzer folder called `api_key.txt`**
2. **Paste your API key into this file and save it**
3. **Now you can use it like this:**

**Windows:**
```
python main.py --api-key $(type api_key.txt) analyze AAPL
```

**Mac/Linux:**
```bash
python3 main.py --api-key $(cat api_key.txt) analyze AAPL
```

### Understanding the Command Structure

Every command has this format:
```
python main.py --api-key YOUR_KEY [command] [arguments]
```

- `python main.py` - runs the program
- `--api-key YOUR_KEY` - tells it your API key
- `[command]` - what you want to do (analyze, batch, screen, etc.)
- `[arguments]` - details for that command (ticker symbol, filters, etc.)

### Getting Help

To see all available commands:
```
python main.py --help
```

To see help for a specific command:
```
python main.py analyze --help
```

---

## What to Do Next

1. **Analyze a few stocks you know:**
   ```
   python main.py --api-key YOUR_KEY analyze AAPL
   python main.py --api-key YOUR_KEY analyze MSFT
   python main.py --api-key YOUR_KEY analyze GOOGL
   ```

2. **Screen for opportunities:**
   ```
   python main.py screen --min-discount 15 --top 20
   ```

3. **Read the full documentation:**
   - Open `README.md` in any text editor
   - Open `QUICK_START.md` for more advanced examples

4. **Run the interactive demo:**
   ```
   python examples.py
   ```

---

## Need More Help?

1. **Check the README.md file** - has detailed examples
2. **Check the QUICK_START.md file** - has workflow examples
3. **Run the test:** `python test_installation.py`
4. **Read the error messages** - they usually tell you what's wrong

---

## You're All Set! 🎉

You now have:
- ✅ Python installed
- ✅ DCF Analyzer installed
- ✅ API key configured
- ✅ First analysis completed

Start analyzing stocks and finding opportunities! Remember:
- Free tier gives you 250 API requests per day
- Each stock analysis uses about 5-7 requests
- You can analyze about 35-50 stocks per day
- Run weekly analyses to build up historical data
- The real power comes from tracking trends over time

Happy investing! 📊💰
