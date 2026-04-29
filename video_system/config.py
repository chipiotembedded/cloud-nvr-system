# Video source

# Windows (local testing)
# For GCP VM / Linux later, this will change to RTSP or /dev/video*

VIDEO_DEVICE = "video=USB2.0 HD UVC WebCam"

# Local storage


BASE_DIR = "recordings"

# Clip settings

CLIP_DURATION = 600# 10 minutes 


# Timezone


TIMEZONE = "Asia/Kolkata"

# Recording window

# Recorder sleeps until RECORD_START_TIME
# Records back-to-back clips
# Stops automatically at RECORD_END_TIME
# Can be stopped manually using Ctrl+C

RECORD_START_TIME = "11:00"   # HH:MM (24-hour)
RECORD_END_TIME   = "21:00"   # HH:MM (24-hour)

# Google Cloud Platform (GCP)

# Project where the VM and bucket exist
GCP_PROJECT_ID = "pro-hour-485309-b6"   # My First Project

# Cloud Storage bucket (must already exist)
# Bucket should be in asia-south1 or asia
GCP_BUCKET = "recording-bucket-0"

# Authentication
# On GCP VM → leave as None (uses Application Default Credentials)
# On local Windows → set path to service account JSON
GCP_CREDENTIALS_PATH = None

# GCS Storage settings

GCP_STORAGE_CLASS = "STANDARD"
GCP_LOCATION = "asia-south1"
