#!/usr/bin/env python3
"""
Video Upload Utility
Command-line interface for uploading videos to GCP
"""

import sys
import os
from datetime import datetime, timedelta
from video_system.uploader import upload_file, upload_day, storage_client

def get_available_dates():
    """Get list of dates with recorded videos"""
    from video_system.config import BASE_DIR
    
    if not os.path.exists(BASE_DIR):
        return []
    
    dates = []
    for item in sorted(os.listdir(BASE_DIR), reverse=True):
        item_path = os.path.join(BASE_DIR, item)
        if os.path.isdir(item_path) and len(item) == 10:  # YYYY-MM-DD format
            dates.append(item)
    
    return dates

def list_videos(date):
    """List all videos for a specific date"""
    from video_system.config import BASE_DIR
    
    day_path = os.path.join(BASE_DIR, date)
    
    if not os.path.exists(day_path):
        print(f"No recordings found for {date}")
        return []
    
    videos = []
    for file in sorted(os.listdir(day_path)):
        if file.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            file_path = os.path.join(day_path, file)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            videos.append({'name': file, 'path': file_path, 'size': size_mb})
    
    return videos

def show_menu():
    """Display main menu"""
    print("\n" + "="*60)
    print("VIDEO UPLOAD UTILITY")
    print("="*60)
    print("\n1. Upload videos from a specific date")
    print("2. Upload a single video file")
    print("3. List available dates")
    print("4. List videos for a date")
    print("5. Check GCP connection")
    print("6. Exit")
    print("\n" + "="*60)

def check_gcp_connection():
    """Verify GCP connection"""
    try:
        print("\nChecking GCP connection...")
        from video_system.config import GCP_BUCKET
        bucket = storage_client.bucket(GCP_BUCKET)
        _ = bucket.get_blob("test")
        print("✓ Successfully connected to GCP!")
        return True
    except Exception as e:
        print(f"✗ GCP connection failed: {str(e)}")
        return False

def main():
    """Main menu loop"""
    while True:
        show_menu()
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            # Upload from date
            dates = get_available_dates()
            if not dates:
                print("\nNo recorded videos found.")
                continue
            
            print("\nAvailable dates:")
            for i, date in enumerate(dates, 1):
                print(f"  {i}. {date}")
            
            try:
                date_choice = int(input("\nSelect date number: "))
                if 1 <= date_choice <= len(dates):
                    date = dates[date_choice - 1]
                    print(f"\nUploading videos from {date}...")
                    upload_day(date)
                else:
                    print("Invalid choice")
            except ValueError:
                print("Invalid input")
        
        elif choice == "2":
            # Upload single file
            file_path = input("\nEnter file path: ").strip()
            if os.path.exists(file_path):
                upload_file(file_path)
            else:
                print(f"File not found: {file_path}")
        
        elif choice == "3":
            # List dates
            dates = get_available_dates()
            if not dates:
                print("\nNo recorded videos found.")
            else:
                print("\nAvailable dates with videos:")
                for date in dates:
                    num_files = len(os.listdir(os.path.join("recordings", date)))
                    print(f"  • {date} ({num_files} files)")
        
        elif choice == "4":
            # List videos for date
            date = input("\nEnter date (YYYY-MM-DD): ").strip()
            videos = list_videos(date)
            if videos:
                print(f"\nVideos on {date}:")
                for video in videos:
                    print(f"  • {video['name']} ({video['size']:.2f} MB)")
            else:
                print(f"No videos found for {date}")
        
        elif choice == "5":
            # Check connection
            check_gcp_connection()
        
        elif choice == "6":
            # Exit
            print("\nGoodbye!")
            sys.exit(0)
        
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
