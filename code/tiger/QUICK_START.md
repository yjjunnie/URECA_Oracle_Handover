# TIGER Quick Start Guide

You have Python 3.11, but TIGER needs Python 3.9. Here's how to get started quickly.

---

## Step 1: Install Python 3.9

### Download Python 3.9.13:
1. Go to: https://www.python.org/downloads/release/python-3913/
2. Scroll to "Files" section
3. Click: **Windows installer (64-bit)**
   - File: `python-3.9.13-amd64.exe`

### Install Python 3.9:
1. Run the downloaded installer
2. ✅ **IMPORTANT:** Check "Add Python 3.9 to PATH"
3. Click "Install Now"
4. Wait for installation to complete
5. Click "Close"

---

## Step 2: Run Automated Installation

### Option A: Double-click the installer
1. Go to: `c:\Users\holly\Downloads\tiger-main\tiger-main`
2. Double-click: **`install_with_venv.bat`**

### Option B: Run from Command Prompt
```bash
cd c:\Users\holly\Downloads\tiger-main\tiger-main
install_with_venv.bat
```

**What this does:**
- ✅ Checks for Python 3.9
- ✅ Creates a virtual environment named `tiger_env`
- ✅ Installs all required packages
- ✅ Verifies installation
- ✅ Shows you next steps

**Expected time:** 5-10 minutes

---

## Step 3: Verify Everything Works

The script will automatically run verification. You should see:

```
✓ numpy                    1.23.5
✓ pandas                   1.5.2
✓ tensorflow               2.11.0
✓ All 12 packages installed successfully!
```

---

## Using TIGER After Installation

### Every time you want to use TIGER:

1. **Open Command Prompt**
2. **Navigate to project:**
   ```bash
   cd c:\Users\holly\Downloads\tiger-main\tiger-main
   ```
3. **Activate virtual environment:**
   ```bash
   tiger_env\Scripts\activate
   ```
   You'll see `(tiger_env)` appear at the start of your prompt
4. **Run TIGER:**
   ```bash
   python tiger_trainer.py --retrain
   ```

### When you're done:
```bash
deactivate
```

---

## Troubleshooting

### "Python 3.9 is not installed"
**Solution:** Install Python 3.9 following Step 1 above

### "Failed to create virtual environment"
**Solution:**
```bash
# Try manually:
py -3.9 -m pip install virtualenv
py -3.9 -m venv tiger_env
```

### "Installation failed"
**Solution 1 - Run as Administrator:**
- Right-click `install_with_venv.bat`
- Select "Run as Administrator"

**Solution 2 - Manual installation:**
```bash
cd c:\Users\holly\Downloads\tiger-main\tiger-main
py -3.9 -m venv tiger_env
tiger_env\Scripts\activate
pip install -r requirements.txt
```

---

## Quick Reference Commands

**Activate environment:**
```bash
cd c:\Users\holly\Downloads\tiger-main\tiger-main
tiger_env\Scripts\activate
```

**Check what's installed:**
```bash
pip list
```

**Verify installation:**
```bash
python test_installation.py
```

**Run TIGER trainer:**
```bash
python tiger_trainer.py --retrain
```

**Deactivate environment:**
```bash
deactivate
```

---

## What Gets Installed

The virtual environment will have:
- Python 3.9.13 (isolated from your Python 3.11)
- TensorFlow 2.11.0 (deep learning)
- NumPy 1.23.5 (numerical computing)
- Pandas 1.5.2 (data manipulation)
- All other TIGER dependencies

**Total size:** ~2-3 GB

---

## Files Created

After installation, you'll have:
```
tiger-main/
├── tiger_env/              ← Virtual environment (new)
│   ├── Scripts/
│   │   ├── activate.bat    ← Activation script
│   │   └── python.exe      ← Python 3.9
│   └── Lib/                ← Installed packages
├── requirements.txt
├── install_with_venv.bat   ← Installation script
├── test_installation.py    ← Verification script
└── ... (other TIGER files)
```

---

## Next Steps

After successful installation:

1. ✅ Read [CODE_FLOW_GUIDE.md](CODE_FLOW_GUIDE.md) - Understand how TIGER works
2. ✅ Read [REIMPLEMENTATION_GUIDE.md](REIMPLEMENTATION_GUIDE.md) - Adapt for your use case
3. ✅ Check `data-processed/` folder for data files
4. ✅ Run TIGER: `python tiger_trainer.py --retrain`

---

**Ready to start?** Run `install_with_venv.bat` now! 🚀
