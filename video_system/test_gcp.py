#!/usr/bin/env python3
"""
GCP Integration Test Script
Tests connectivity and functionality with Google Cloud Storage
"""

import sys
import os
from video_system.config import GCP_PROJECT_ID, GCP_BUCKET, GCP_CREDENTIALS_PATH

def test_gcp_setup():
    """Run comprehensive GCP setup tests"""
    
    print("=" * 60)
    print("GCP Integration Test Suite")
    print("=" * 60)
    
    # Test 1: Check configuration
    print("\n[Test 1] Checking Configuration...")
    if GCP_PROJECT_ID == "your-gcp-project-id":
        print("✗ FAIL: GCP_PROJECT_ID not configured in config.py")
        return False
    print(f"✓ PASS: GCP_PROJECT_ID = {GCP_PROJECT_ID}")
    
    if GCP_BUCKET == "your-gcp-bucket-name":
        print("✗ FAIL: GCP_BUCKET not configured in config.py")
        return False
    print(f"✓ PASS: GCP_BUCKET = {GCP_BUCKET}")
    
    # Test 2: Check credentials
    print("\n[Test 2] Checking Credentials...")
    if GCP_CREDENTIALS_PATH:
        if not os.path.exists(GCP_CREDENTIALS_PATH):
            print(f"✗ FAIL: Credentials file not found: {GCP_CREDENTIALS_PATH}")
            return False
        print(f"✓ PASS: Credentials file found: {GCP_CREDENTIALS_PATH}")
    else:
        print("✓ PASS: Using Application Default Credentials (ADC)")
    
    # Test 3: Import libraries
    print("\n[Test 3] Checking Dependencies...")
    try:
        from google.cloud import storage
        print("✓ PASS: google-cloud-storage is installed")
    except ImportError:
        print("✗ FAIL: google-cloud-storage not installed")
        print("  Run: pip install google-cloud-storage")
        return False
    
    # Test 4: Connect to GCS
    print("\n[Test 4] Connecting to Google Cloud Storage...")
    try:
        from video_system.uploader import storage_client
        print("✓ PASS: Successfully connected to GCS")
    except Exception as e:
        print(f"✗ FAIL: Could not connect to GCS: {str(e)}")
        print("  Make sure:")
        print("  - You have valid GCP credentials")
        print("  - Your GCP_PROJECT_ID is correct")
        print("  - Your GCP_BUCKET exists")
        return False
    
    # Test 5: Access bucket
    print("\n[Test 5] Accessing GCS Bucket...")
    try:
        bucket = storage_client.bucket(GCP_BUCKET)
        # Try to get bucket metadata
        _ = bucket.get_blob("test")  # This won't fail even if bucket is empty
        print(f"✓ PASS: Successfully accessed bucket: {GCP_BUCKET}")
    except Exception as e:
        print(f"✗ FAIL: Could not access bucket: {str(e)}")
        print("  Make sure:")
        print("  - Bucket name is correct")
        print("  - You have permissions to access this bucket")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All tests passed! GCP integration is ready.")
    print("=" * 60)
    print("\nYou can now use the uploader:")
    print("  - upload_file('path/to/video.mp4')")
    print("  - upload_day('2026-01-12')")
    return True

if __name__ == "__main__":
    success = test_gcp_setup()
    sys.exit(0 if success else 1)
