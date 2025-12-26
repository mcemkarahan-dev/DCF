# Visual Walkthrough - First Time Setup

This guide shows you EXACTLY what you'll see on your screen at each step.

---

## Part 1: Installing Python

### Windows Users:

**STEP 1 - Download**
```
What you'll do: Go to python.org/downloads
What you'll see: A big yellow button saying "Download Python 3.12.x"
Action: Click the button
```

**STEP 2 - Run Installer**
```
What you'll see: A window that says "Install Python 3.12.x"
CRITICAL: At the bottom, there's a checkbox that says "Add Python to PATH"
Action: ✓ CHECK THIS BOX (very important!)
Action: Click "Install Now"
```

**STEP 3 - Wait**
```
What you'll see: Progress bar
Time: 2-3 minutes
Action: Wait until it says "Setup was successful"
Action: Click "Close"
```

**STEP 4 - Test It**
```
What you'll do: Press Windows Key + R
What you'll see: A small "Run" dialog box
Action: Type "cmd" and press Enter
What you'll see: A black window (Command Prompt)
Action: Type "python --version" and press Enter
What you should see: "Python 3.12.1" (or similar)
✓ Success if you see the version number!
✗ If you see "not recognized" - go back to Step 2 and check the PATH box
```

### Mac Users:

**STEP 1 - Download**
```
What you'll do: Go to python.org/downloads
What you'll see: A button saying "Download Python 3.12.x"
Action: Click the button
```

**STEP 2 - Run Installer**
```
What you'll see: A .pkg file in your Downloads
Action: Double-click it
What you'll see: Installation wizard
Action: Click "Continue" → "Continue" → "Install"
Action: Enter your Mac password
Action: Wait (2-3 minutes)
Action: Click "Close"
```

**STEP 3 - Test It**
```
What you'll do: Press Command + Space
What you'll see: Spotlight search
Action: Type "terminal" and press Enter
What you'll see: A window with white text on black background
Action: Type "python3 --version" and press Enter
What you should see: "Python 3.12.1" (or similar)
✓ Success if you see the version number!
```

---

## Part 2: Setting Up the DCF Analyzer

**STEP 1 - Find Your Downloaded Files**
```
You should have a folder called "dcf_analyzer"
Inside it you'll see files named:
- main.py
- database.py
- README.md
- requirements.txt
- etc.

If you don't see .py at the end of files:
Windows: View → File name extensions (check the box)
Mac: They might show as just "main", "database" - that's OK
```

**STEP 2 - Move to a Good Location**
```
Windows: Move dcf_analyzer folder to C:\Users\YourName\Documents\
Mac: Move dcf_analyzer folder to /Users/YourName/Documents/
Linux: Move dcf_analyzer folder to /home/yourname/Documents/

Why? These locations always have the right permissions.
```

**STEP 3 - Open Terminal/Command Prompt in the Right Place**

**Windows Method:**
```
1. Open File Explorer
2. Go to Documents\dcf_analyzer
3. You should see main.py, database.py, etc.
4. Click in the address bar (where it shows the path)
5. Type "cmd" and press Enter

What you'll see: 
Command Prompt opens with path ending in \dcf_analyzer>

To verify: Type "dir" and press Enter
You should see main.py, database.py listed
```

**Mac Method:**
```
1. Open Finder
2. Go to Documents → dcf_analyzer
3. Right-click (or Control-click) the dcf_analyzer folder
4. Hold Option key - you'll see "Copy dcf_analyzer as Pathname"
5. Click that
6. Press Command + Space, type "terminal", Enter
7. Type "cd " (with space after)
8. Press Command + V (paste)
9. Press Enter

What you'll see:
Your terminal prompt now shows dcf_analyzer

To verify: Type "ls" and press Enter
You should see main.py, database.py listed
```

---

## Part 3: Installing Required Libraries

**What You'll Type:**

Windows:
```
pip install -r requirements.txt
```

Mac/Linux:
```
pip3 install -r requirements.txt
```

**What You'll See:**
```
Collecting requests>=2.31.0
  Downloading requests-2.31.0-py3-none-any.whl (62 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 62.6/62.6 KB 2.3 MB/s
Collecting pandas>=2.0.0
  Downloading pandas-2.1.4-cp312-cp312-win_amd64.whl (11.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 11.3/11.3 MB 8.2 MB/s
... (more lines of downloading/installing)
Successfully installed pandas-2.1.4 requests-2.31.0 ...
```

Time: About 1-2 minutes

✓ **Success**: When you see "Successfully installed" and get your prompt back
✗ **Error**: If you see red text, check you're in the right folder (Part 2, Step 3)

---

## Part 4: Testing Everything Works

**What You'll Type:**

Windows:
```
python test_installation.py
```

Mac/Linux:
```
python3 test_installation.py
```

**What You'll See:**
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

Next steps:
1. Get an API key from https://financialmodelingprep.com/developer/docs/
2. Run: python main.py --api-key YOUR_KEY analyze AAPL
3. Check README.md for more examples
```

✓ **Perfect!** If you see "5 passed, 0 failed" - you're ready!

---

## Part 5: Getting Your API Key

**STEP 1 - Go to Website**
```
Open browser and go to:
https://financialmodelingprep.com/developer/docs/

What you'll see: A website with "Free API Key" or "Get Started" button
```

**STEP 2 - Sign Up**
```
Click "Get Free API Key" or "Sign Up"

What you'll see: A form asking for:
- Email
- Password
- Confirm Password

Fill it out and click "Sign Up"
```

**STEP 3 - Confirm Email**
```
What you'll see: "Check your email" message

Go to your email inbox
Look for email from Financial Modeling Prep
Click the confirmation link in the email
```

**STEP 4 - Get Your Key**
```
What you'll see: Your dashboard

Look for section that says "Your API Key"

What you'll see: A long string like:
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

Action: Click "Copy" or select and copy (Ctrl+C / Command+C)

⚠️ SAVE THIS KEY SOMEWHERE SAFE!
```

**Pro Tip - Save It in a File:**
```
1. In the dcf_analyzer folder, create a new text file
2. Name it: api_key.txt
3. Paste your API key into this file
4. Save and close

Now you have it saved for later!
```

---

## Part 6: Your First Stock Analysis!

**What You'll Type:**

Windows:
```
python main.py --api-key YOUR_ACTUAL_KEY_HERE analyze AAPL
```

Mac/Linux:
```
python3 main.py --api-key YOUR_ACTUAL_KEY_HERE analyze AAPL
```

**IMPORTANT**: Replace `YOUR_ACTUAL_KEY_HERE` with the key you copied!

**Example with a fake key:**
```
python main.py --api-key a1b2c3d4e5f6g7h8i9j0 analyze AAPL
```

**What You'll See:**
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

Time: About 10-15 seconds

✓ **Success!** You just ran your first DCF analysis!

---

## Part 7: What To Do Next

### Try These Commands (One at a Time)

**Analyze Microsoft:**
```
python main.py --api-key YOUR_KEY analyze MSFT
```

**Analyze Google:**
```
python main.py --api-key YOUR_KEY analyze GOOGL
```

**Screen for Opportunities:**
```
python main.py screen --min-discount 15 --top 10
```
This shows stocks trading 15%+ below intrinsic value

**View Trend for Apple:**
```
python main.py trending AAPL --periods 5
```
This shows how Apple's intrinsic value has changed

**Run Interactive Demo:**
```
python examples.py
```
This gives you a menu to explore features

---

## Common Screen Shots / What You'll See

### When Analysis Works:
```
============================================================
Analyzing MSFT
============================================================
Fetching data for MSFT...

Company: Microsoft Corporation
Sector: Technology
Current Price: $374.50
Intrinsic Value: $420.20
Discount/Premium: +12.2%
*** FAIRLY VALUED ***
```

### When Screening Works:
```
============================================================
DCF STOCK SCREENING REPORT
Generated: 2024-01-15 10:30:00
============================================================

SUMMARY STATISTICS:
  Total stocks analyzed: 3
  Undervalued: 2
  Overvalued: 1
  Fairly valued: 0
  Average discount: 10.5%

TOP 10 OPPORTUNITIES:

Ticker     Current    Intrinsic    Discount   Model          
--------------------------------------------------------------------------------
AAPL       $180.50    $225.30      +24.8%     revenue_based  
MSFT       $374.50    $420.20      +12.2%     revenue_based  
```

### When You Get an Error (and what it means):

**"python is not recognized"**
```
Means: Python not installed correctly
Fix: Go back to Part 1, make sure to check "Add to PATH"
```

**"No such file or directory"**
```
Means: You're not in the dcf_analyzer folder
Fix: Go back to Part 2, Step 3
```

**"Could not fetch data for AAPL"**
```
Means: API key is wrong or you hit the rate limit
Fix: Check your API key (copy it again carefully)
```

**"No module named 'requests'"**
```
Means: Libraries not installed
Fix: Go back to Part 3
```

---

## You Made It! 🎉

You should now:
- ✅ Have Python installed
- ✅ Have the DCF Analyzer working
- ✅ Have an API key
- ✅ Have analyzed your first stock

**Next Steps:**
1. Analyze 5-10 stocks you know
2. Wait a week and analyze them again to see trends
3. Read QUICK_START.md for advanced features
4. Build a watchlist and track it over time

**Remember:**
- Free tier: 250 API calls per day
- Each stock uses ~5-7 calls
- You can analyze ~40 stocks per day
- The power is in tracking over time!

Happy analyzing! 📊💰
