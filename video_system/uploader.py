import os
import sys
import time
from datetime import datetime, date
from google.cloud import storage
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPICallError

from video_system.config import (
    BASE_DIR,
    GCP_BUCKET,
    GCP_PROJECT_ID,
    GCP_CREDENTIALS_PATH,
)

# ---------------- CONFIG ----------------

SCAN_INTERVAL = 30  # seconds between scans for new clips
SUPPORTED_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv")

# ---------------------------------------


def initialize_gcs_client():
    """Initialize Google Cloud Storage client"""
    try:
        if GCP_CREDENTIALS_PATH and os.path.exists(GCP_CREDENTIALS_PATH):
            credentials = service_account.Credentials.from_service_account_file(
                GCP_CREDENTIALS_PATH
            )
            client = storage.Client(
                project=GCP_PROJECT_ID, credentials=credentials
            )
        else:
            # Uses Application Default Credentials (ADC)
            client = storage.Client(project=GCP_PROJECT_ID)

        print("✓ Successfully connected to Google Cloud Storage", flush=True)
        return client
    except Exception as e:
        print(f"✗ Failed to initialize GCS client: {e}", flush=True)
        sys.exit(1)


storage_client = initialize_gcs_client()
bucket = storage_client.bucket(GCP_BUCKET)


def upload_file(filepath: str) -> bool:
    """Upload a single file if not already uploaded"""
    try:
        blob_name = filepath.replace(BASE_DIR + os.sep, "").replace("\\", "/")
        blob = bucket.blob(blob_name)

        if blob.exists():
            return False  # already uploaded

        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"Uploading: {blob_name} ({file_size_mb:.2f} MB)", flush=True)

        blob.upload_from_filename(filepath)

        print(f"✓ Uploaded: {blob_name}", flush=True)
        return True

    except GoogleAPICallError as e:
        print(f"✗ GCS API error for {filepath}: {e}", flush=True)
        return False
    except Exception as e:
        print(f"✗ Upload error for {filepath}: {e}", flush=True)
        return False


def upload_day(date_str: str):
    """Upload all new clips for a specific date"""
    day_path = os.path.join(BASE_DIR, date_str)

    if not os.path.exists(day_path):
        return

    files = sorted(
        f for f in os.listdir(day_path)
        if f.endswith(SUPPORTED_EXTENSIONS)
    )

    for filename in files:
        full_path = os.path.join(day_path, filename)
        upload_file(full_path)


def main():
    print("Uploader started (watching for new clips)...\n", flush=True)

    try:
        while True:
            today = date.today().strftime("%Y-%m-%d")
            upload_day(today)
            time.sleep(SCAN_INTERVAL)

    except KeyboardInterrupt:
        print("\nUploader stopped by user (Ctrl+C).", flush=True)


if __name__ == "__main__":
    main()
