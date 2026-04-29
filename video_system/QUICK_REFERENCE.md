# GCP Integration - Quick Reference Card

## 🚀 Installation (One-Time)

```powershell
# 1. Navigate to project
cd C:\Users\ishaa\OneDrive\Desktop\video_system

# 2. Run setup script
.\setup_gcp.ps1

# OR manually:
.\.venv\Scripts\Activate.ps1
pip install google-cloud-storage
python test_gcp.py
```

## ⚙️ Configuration (One-Time)

**File: `config.py`**

```python
GCP_PROJECT_ID = "my-gcp-project-12345"
GCP_BUCKET = "my-video-bucket"
GCP_CREDENTIALS_PATH = None  # or "service-account-key.json"
```

## 📤 Upload Commands

```powershell
# Open PowerShell and activate venv
.\.venv\Scripts\Activate.ps1

# Upload videos from specific date
python -c "from uploader import upload_day; upload_day('2026-01-12')"

# Upload single file
python -c "from uploader import upload_file; upload_file('recordings/2026-01-12/video1.mp4')"

# Use interactive menu
python upload_manager.py
```

## 🧪 Test & Debug

```powershell
# Test GCP integration
python test_gcp.py

# List available videos
python upload_manager.py  # Choose option 3
```

## 📊 Monitor in GCP Console

https://console.cloud.google.com/ → Cloud Storage → Buckets → Your Bucket

## 🔐 Security Checklist

- [ ] `service-account-key.json` NOT in version control
- [ ] Check `.gitignore` includes `*.json`
- [ ] Credentials rotated quarterly
- [ ] Service account has minimum permissions

## 🛠️ Troubleshooting

| Error | Quick Fix |
|-------|-----------|
| `ModuleNotFoundError: google.cloud` | `pip install google-cloud-storage` |
| `ProjectNotFound` | Check GCP_PROJECT_ID in config.py |
| `Forbidden: 403` | Check service account permissions |
| `NotFound: 404` | Verify bucket name (case-sensitive) |

## 📁 Project Files

| File | Purpose |
|------|---------|
| `config.py` | Configuration (YOUR EDITS HERE) |
| `uploader.py` | Upload logic |
| `test_gcp.py` | Verify setup |
| `upload_manager.py` | Interactive upload tool |
| `requirements.txt` | Dependencies |
| `GCP_SETUP_GUIDE.md` | Detailed setup |
| `README.md` | Full documentation |

## 💡 Common Tasks

### Upload all videos from a date
```python
from uploader import upload_day
upload_day("2026-01-12")
```

### Upload single video
```python
from uploader import upload_file
upload_file("recordings/2026-01-12/myvideo.mp4")
```

### Batch upload multiple dates
```python
from uploader import upload_day
for date in ["2026-01-12", "2026-01-13", "2026-01-14"]:
    upload_day(date)
```

## 📞 Support Resources

- **Setup Help:** GCP_SETUP_GUIDE.md
- **Usage:** README.md
- **Code Issues:** test_gcp.py (diagnostic tool)
- **GCP Docs:** https://cloud.google.com/storage/docs

## 📋 Setup Validation

Run this to verify everything is working:

```powershell
python test_gcp.py
```

Expected output:
```
✓ All tests passed! GCP integration is ready.
```

---

**Last Updated:** January 30, 2026
**GCP SDK Version:** google-cloud-storage 2.10.0+
**Python Version:** 3.10+
