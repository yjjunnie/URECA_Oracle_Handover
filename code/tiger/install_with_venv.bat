@echo off
REM TIGER Installation Script with Virtual Environment
REM This script creates a Python 3.9 virtual environment and installs dependencies

echo ========================================
echo TIGER Installation with Virtual Environment
echo ========================================
echo.

REM Check if Python 3.9 is available
echo Checking for Python 3.9...
py -3.9 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python 3.9 is not installed!
    echo.
    echo Please install Python 3.9 from:
    echo https://www.python.org/downloads/release/python-3913/
    echo.
    echo Download: Windows installer (64-bit)
    echo During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo Found Python 3.9!
py -3.9 --version
echo.

REM Check if virtual environment already exists
if exist "tiger_env" (
    echo Virtual environment 'tiger_env' already exists.
    echo.
    choice /C YN /M "Do you want to delete it and create a new one"
    if errorlevel 2 goto skip_venv_creation
    if errorlevel 1 (
        echo Removing old virtual environment...
        rmdir /s /q tiger_env
    )
)

:skip_venv_creation

REM Create virtual environment if it doesn't exist
if not exist "tiger_env" (
    echo Creating virtual environment with Python 3.9...
    py -3.9 -m venv tiger_env

    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment!
        echo Make sure Python 3.9 is properly installed.
        pause
        exit /b 1
    )

    echo Virtual environment created successfully!
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call tiger_env\Scripts\activate.bat

if errorlevel 1 (
    echo.
    echo ERROR: Failed to activate virtual environment!
    pause
    exit /b 1
)

echo Virtual environment activated!
echo.

REM Verify Python version in virtual environment
echo Verifying Python version in virtual environment...
python --version
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install dependencies
echo Installing TIGER dependencies...
echo This may take 5-10 minutes...
echo.

pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Installation failed!
    echo ========================================
    echo.
    echo Troubleshooting:
    echo 1. Check your internet connection
    echo 2. Try running as Administrator
    echo 3. See INSTALLATION_GUIDE.md for manual installation
    echo.
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

python test_installation.py

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo The virtual environment is now active.
echo.
echo IMPORTANT: To use TIGER in the future:
echo 1. Open Command Prompt
echo 2. Navigate to: cd <PATH_TO_PROJECT>\tiger-main\tiger-main
echo 3. Activate environment: tiger_env\Scripts\activate
echo 4. Run TIGER: python tiger_trainer.py
echo.
echo To deactivate the virtual environment, type: deactivate
echo.
echo ========================================

pause
