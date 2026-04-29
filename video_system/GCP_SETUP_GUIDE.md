# GCP Integration Setup Guide

This guide will help you set up Google Cloud Platform (GCP) for seamless video upload from your video system.

## Step 1: Create a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "NEW PROJECT"
4. Enter a project name (e.g., "video-system")
5. Click "CREATE"
6. Wait for the project to be created, then select it

## Step 2: Enable Required APIs

1. In the Cloud Console, go to **APIs & Services > Library**
2. Search for and enable these APIs:
   - **Cloud Storage API**
   - **Identity and Access Management (IAM) API**

## Step 3: Create a GCS Bucket

1. In Cloud Console, go to **Cloud Storage > Buckets**
2. Click **CREATE BUCKET**
3. Enter a bucket name (must be globally unique, e.g., "my-video-system-2026")
4. Choose a location (e.g., us-central1)
5. Leave other settings as default
6. Click **CREATE**

## Step 4: Set Up Authentication

### Option A: Using Service Account (Recommended for Production)

1. Go to **APIs & Services > Credentials**
2. Click **CREATE CREDENTIALS > Service Account**
3. Fill in the Service Account name and click **CREATE AND CONTINUE**
4. Grant the role: **Basic > Editor** (or more restrictive roles if needed)
5. Click **CONTINUE > DONE**
6. Go to **Keys** tab of the service account
7. Click **ADD KEY > Create new key**
8. Choose **JSON** format and click **CREATE**
9. Save the JSON file to your video_system folder as `service-account-key.json`
10. Update `config.py`:
    ```python
    GCP_CREDENTIALS_PATH = "service-account-key.json"
    ```

### Option B: Using Application Default Credentials (ADC)

1. Install Google Cloud SDK: [Download here](https://cloud.google.com/sdk/docs/install)
2. Open PowerShell and run:
   ```powershell
   gcloud init
   gcloud auth application-default login
   ```
3. Keep `GCP_CREDENTIALS_PATH = None` in config.py

## Step 5: Configure Your Video System

Edit `config.py` and update:

```python
GCP_PROJECT_ID = "your-gcp-project-id"  # Get from Cloud Console
GCP_BUCKET = "your-gcp-bucket-name"     # Your bucket name from Step 3
GCP_CREDENTIALS_PATH = None              # or "service-account-key.json" if using service account
GCP_LOCATION = "us-central1"             # Your bucket location
```

## Step 6: Test the Setup

Run this test command in PowerShell:

```powershell
cd C:\Users\ishaa\OneDrive\Desktop\video_system
python -c "from uploader import upload_file; print('✓ GCP integration is working!')"
```

You should see a success message.

## Step 7: Upload Videos

### Upload a single file:
```python
from uploader import upload_file
upload_file("recordings/2026-01-12/video1.mp4")
```

### Upload all videos from a specific date:
```python
from uploader import upload_day
upload_day("2026-01-12")
```

## Troubleshooting

### Error: "Project not found"
- Verify your `GCP_PROJECT_ID` is correct in `config.py`
- Run `gcloud config list` to see your current project

### Error: "Permission denied"
- Check that your service account has Storage Admin permissions
- Run `gcloud auth list` to verify you're logged in

### Error: "Bucket not found"
- Verify bucket name is exactly correct (case-sensitive)
- Bucket name must be globally unique

### Error: "Credentials not found"
- Ensure service account JSON file path is correct
- Or run `gcloud auth application-default login`

## Monitoring Uploads in GCP Console

1. Go to **Cloud Storage > Buckets**
2. Click on your bucket name
3. You'll see all uploaded videos organized by date
4. Click any file to view details and download

## Billing & Cost Optimization

- Storage costs vary by location and storage class
- Check [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- Consider using **Nearline** or **Coldline** storage for older videos

## Important Security Notes

⚠️ **NEVER commit `service-account-key.json` to version control**
- Add to `.gitignore`: `service-account-key.json`
- Keep credentials secure and restricted

## Additional Resources

- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Service Account Setup](https://cloud.google.com/docs/authentication/production)
- [Gsutil Command Line Tool](https://cloud.google.com/storage/docs/gsutil)
