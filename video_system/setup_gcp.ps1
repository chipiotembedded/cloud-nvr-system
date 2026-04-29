# Quick Start Script for GCP Video Upload
# Run: .\setup_gcp.ps1

Write-Host "`n================================" -ForegroundColor Green
Write-Host "GCP Video System - Quick Setup" -ForegroundColor Green
Write-Host "================================`n" -ForegroundColor Green

# Check if Python is available
try {
    python --version | Out-Null
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 1: Activate virtual environment
Write-Host "[1/4] Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Step 2: Install dependencies
Write-Host "[2/4] Installing dependencies..." -ForegroundColor Yellow
pip install -q google-cloud-storage 2>$null

# Step 3: Run GCP configuration test
Write-Host "[3/4] Running GCP configuration test..." -ForegroundColor Yellow
python test_gcp.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ GCP setup test failed" -ForegroundColor Red
    Write-Host "Please refer to GCP_SETUP_GUIDE.md for configuration steps`n" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "`n✓ Setup complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Update config.py with your GCP project ID and bucket name"
Write-Host "2. Set up authentication (see GCP_SETUP_GUIDE.md)"
Write-Host "3. Run: python -c `"from uploader import upload_day; upload_day('2026-01-12')`""
Write-Host ""
Read-Host "Press Enter to exit"
