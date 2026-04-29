# Video System with GCP Integration

A Python-based video recording and cloud uploading system that automatically records video clips and uploads them to Google Cloud Platform (GCP).

## Features

✨ **Automatic Video Recording**
- Records video at specified intervals (10-minute clips by default)
- Scheduled recording window (13:00 - 21:00 by default)
- Timezone support (Asia/Kolkata by default)
- Organized by date in local storage

☁️ **Seamless GCP Upload**
- Automatic upload to Google Cloud Storage
- Error handling and retry logic
- Progress tracking with file size display
- Support for multiple video formats (mp4, avi, mov, mkv)

🎯 **Easy Configuration**
- Single config file for all settings
- Support for service account authentication
- Application Default Credentials support

## Quick Start

### 1. Prerequisites
- Python 3.10+
- Google Cloud Platform account
- Windows PowerShell or Command Prompt

### 2. Installation

```powershell
# Clone or navigate to the project directory
cd C:\Users\ishaa\OneDrive\Desktop\video_system

# Run the setup script
.\setup_gcp.ps1
```

Or manually:
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Edit `config.py` and update:

```python
GCP_PROJECT_ID = "your-gcp-project-id"
GCP_BUCKET = "your-gcp-bucket-name"
```

See [GCP_SETUP_GUIDE.md](GCP_SETUP_GUIDE.md) for detailed setup instructions.

## Project Structure

```
video_system/
├── config.py              # Configuration file (update with your GCP settings)
├── recorder.py            # Video recording module
├── playback.py            # Video playback module
├── uploader.py            # GCP upload module
├── requirements.txt       # Python dependencies
├── test_gcp.py            # GCP integration test script
├── setup_gcp.ps1          # PowerShell setup script
├── setup_gcp.bat          # Batch setup script
├── GCP_SETUP_GUIDE.md     # Detailed GCP configuration guide
├── recordings/            # Local video storage (auto-created)
└── venv/                  # Python virtual environment
```

## Usage

### Upload Videos from a Specific Date

```python
from uploader import upload_day

# Upload all videos from January 12, 2026
upload_day("2026-01-12")
```

### Upload a Single Video

```python
from uploader import upload_file

# Upload a specific video file
upload_file("recordings/2026-01-12/video1.mp4")
```

### Test GCP Integration

```powershell
python test_gcp.py
```

## Configuration Options

### Core Settings (config.py)

| Setting | Default | Description |
|---------|---------|-------------|
| `VIDEO_DEVICE` | `video=USB2.0 HD UVC WebCam` | Webcam device identifier |
| `BASE_DIR` | `recordings` | Local storage directory |
| `CLIP_DURATION` | `600` | Recording clip duration in seconds |
| `TIMEZONE` | `Asia/Kolkata` | Timezone for timestamps |
| `RECORD_START_TIME` | `13:00` | Recording start time (24-hour format) |
| `RECORD_END_TIME` | `21:00` | Recording end time (24-hour format) |

### GCP Settings (config.py)

| Setting | Description |
|---------|-------------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_BUCKET` | Your GCS bucket name |
| `GCP_CREDENTIALS_PATH` | Path to service account JSON (optional) |
| `GCP_STORAGE_CLASS` | Storage class (STANDARD, NEARLINE, etc.) |
| `GCP_LOCATION` | GCP region for your bucket |

## Authentication Methods

### Method 1: Service Account (Recommended)

1. Download service account JSON from GCP Console
2. Save as `service-account-key.json`
3. Update config.py:
   ```python
   GCP_CREDENTIALS_PATH = "service-account-key.json"
   ```

### Method 2: Application Default Credentials (ADC)

1. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. Run: `gcloud auth application-default login`
3. Keep `GCP_CREDENTIALS_PATH = None` in config.py

## Troubleshooting

### Can't upload to GCS
- Run `python test_gcp.py` to diagnose issues
- Check GCP project ID and bucket name are correct
- Verify credentials are properly configured

### "Permission denied" error
- Ensure service account has Storage Admin role
- Check bucket permissions in GCP Console

### "Bucket not found"
- Verify bucket name (case-sensitive)
- Ensure bucket exists in your GCP project

See [GCP_SETUP_GUIDE.md](GCP_SETUP_GUIDE.md) for more troubleshooting tips.

## Security

⚠️ **Important:**
- **Never** commit `service-account-key.json` to version control
- Use `.gitignore` (already configured)
- Restrict service account permissions to minimum needed
- Rotate credentials regularly

## Monitoring

### View Uploads in GCP Console

1. Go to Cloud Storage > Buckets
2. Click your bucket name
3. Browse uploaded videos organized by date

### Check Logs

All upload activities are logged to console with timestamps.

## Dependencies

- `google-cloud-storage>=2.10.0` - GCP Cloud Storage client
- Python 3.10+ standard libraries

See `requirements.txt` for exact versions.

## Cost Optimization Tips

1. Use **Nearline** storage for older recordings (cheaper)
2. Set up lifecycle policies to auto-delete old files
3. Monitor usage in GCP Billing dashboard
4. Use regional buckets instead of multi-region

## Support & Documentation

- [Google Cloud Storage Docs](https://cloud.google.com/storage/docs)
- [GCP Setup Guide](GCP_SETUP_GUIDE.md)
- [Python google-cloud-storage](https://cloud.google.com/python/docs/reference/storage/latest)

## License

This project is provided as-is for video recording and uploading purposes.

## Author

Created for seamless video system integration with Google Cloud Platform.
