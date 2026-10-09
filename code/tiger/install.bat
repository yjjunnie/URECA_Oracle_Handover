@echo off
REM TIGER Installation Script for Windows
REM This script installs all required dependencies for the TIGER project

echo ========================================
echo TIGER Dependency Installation Script
echo ========================================
echo.

REM Check Python version
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8-3.10 first
    pause
    exit /b 1
)

echo.
echo Checking Python version compatibility...
python -c "import sys; exit(0 if sys.version_info >= (3,8) and sys.version_info < (3,11) else 1)"
if errorlevel 1 (
    echo ERROR: Python version must be 3.8-3.10
    echo TensorFlow 2.11 is not compatible with Python 3.11+
    pause
    exit /b 1
)

echo Python version is compatible!
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install from requirements.txt
echo Installing dependencies from requirements.txt...
echo This may take several minutes...
echo.

pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed!
    echo.
    echo Troubleshooting steps:
    echo 1. Make sure you have internet connection
    echo 2. Try running as Administrator
    echo 3. Check the INSTALLATION_GUIDE.md for manual installation
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.

REM Verify installation
echo Verifying installation...
echo.

python -c "import numpy; print('NumPy:', numpy.__version__)"
python -c "import pandas; print('Pandas:', pandas.__version__)"
python -c "import tensorflow; print('TensorFlow:', tensorflow.__version__)"
python -c "import sklearn; print('Scikit-learn: installed')"
python -c "import matplotlib; print('Matplotlib: installed')"

echo.
echo ========================================
echo Next Steps:
echo ========================================
echo 1. Read CODE_FLOW_GUIDE.md to understand the codebase
echo 2. Check data-processed/ folder for data files
echo 3. Run: python tiger_trainer.py --retrain
echo.
echo For more details, see INSTALLATION_GUIDE.md
echo ========================================

pause
