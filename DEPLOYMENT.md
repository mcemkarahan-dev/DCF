# Deployment Guide 🚀

This guide will help you deploy the DCF Stock Analyzer to GitHub and Streamlit Cloud.

## Step 1: Upload to GitHub

### Using GitHub Web Interface (Easiest)

1. **Go to your repository:**
   ```
   https://github.com/mcemkarahan-dev/DCF
   ```

2. **Upload files:**
   - Click "Add file" → "Upload files"
   - Drag and drop ALL folders from your local `dcf-github-repo` folder
   - Or use the file picker to select everything
   - Make sure you get: `desktop/`, `streamlit/`, `shared/`, `README.md`, `LICENSE`, `.gitignore`

3. **Commit:**
   - Add commit message: "Initial commit - DCF Stock Analyzer"
   - Click "Commit changes"

### Using Git Command Line (Alternative)

```bash
# Navigate to the dcf-github-repo folder
cd /path/to/dcf-github-repo

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - DCF Stock Analyzer"

# Add remote (your repository)
git remote add origin https://github.com/mcemkarahan-dev/DCF.git

# Push to GitHub
git push -u origin main
```

## Step 2: Deploy Streamlit App (FREE!)

### Create Streamlit Cloud Account

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "Sign up" (use your GitHub account)
3. Authorize Streamlit to access your GitHub

### Deploy Your App

1. **Click "New app"**

2. **Configure deployment:**
   - **Repository:** `mcemkarahan-dev/DCF`
   - **Branch:** `main`
   - **Main file path:** `streamlit/streamlit_app.py`

3. **Advanced settings (click "Advanced settings"):**
   - **Python version:** 3.10 or 3.11
   - **Secrets:** Add your Roic.ai API key (if you have one)
     ```toml
     ROIC_API_KEY = "your_api_key_here"
     ```

4. **Click "Deploy"**

5. **Wait 2-3 minutes** for deployment to complete

6. **Your app is live!** 🎉
   - URL will be something like: `https://dcf-stock-analyzer.streamlit.app`
   - Share this URL with anyone!

## Step 3: Update the App

Whenever you make changes:

1. **Edit files on GitHub** (or push via git)
2. **Streamlit Cloud auto-deploys** - changes go live in ~2 minutes!

## Troubleshooting

### "Module not found" error
- Check `streamlit/requirements.txt` has all dependencies
- Click "Reboot app" in Streamlit Cloud

### "Path not found" error
- Verify the main file path is exactly: `streamlit/streamlit_app.py`
- Make sure the `shared/` folder is uploaded

### App crashes on startup
- Check Streamlit Cloud logs (click "Manage app" → "Logs")
- Make sure all shared modules are in the repository

### API key not working
- Check secrets are added in Streamlit Cloud settings
- Format must be: `ROIC_API_KEY = "key_here"` (no quotes around key if using Cloud interface)

## Local Development

### Test Streamlit locally before deploying:

```bash
cd streamlit
pip install -r requirements.txt
streamlit run streamlit_app.py
```

App opens at `http://localhost:8501`

## Desktop App Distribution

### Share the desktop app with others:

1. **Option 1: GitHub Releases**
   - Go to your GitHub repo
   - Click "Releases" → "Create a new release"
   - Upload `desktop.zip` (zip the desktop folder)
   - Others can download and run locally

2. **Option 2: Direct ZIP**
   - Zip the `desktop/` folder
   - Share via email, Dropbox, etc.
   - Recipients run: `python gui_launcher.py` or use launcher scripts

## Custom Domain (Optional)

Streamlit Cloud supports custom domains:

1. Go to app settings in Streamlit Cloud
2. Click "Custom subdomain"
3. Or set up CNAME for full custom domain

## Maintenance

### Keep dependencies updated:
```bash
pip list --outdated
pip install -U streamlit pandas numpy
```

### Monitor usage:
- Streamlit Cloud dashboard shows traffic
- GitHub Insights shows repository activity

---

**Need help?** Open an issue on [GitHub](https://github.com/mcemkarahan-dev/DCF/issues)
