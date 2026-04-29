@echo off
REM Quick Start Script for GCP Video Upload

echo.
echo ================================
echo GCP Video System - Quick Setup
echo ================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/4] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
pip install -q google-cloud-storage

echo [3/4] Running GCP configuration test...
python test_gcp.py

if errorlevel 1 (
    echo.
    echo ✗ GCP setup test failed
    echo Please refer to GCP_SETUP_GUIDE.md for configuration steps
    pause
    exit /b 1
)

echo.
echo ✓ Setup complete! 
echo.
echo Next steps:
echo 1. Update config.py with your GCP project ID and bucket name
echo 2. Set up authentication (see GCP_SETUP_GUIDE.md)
echo 3. Run: python -c "from uploader import upload_day; upload_day('2026-01-12')"
echo.
pause
