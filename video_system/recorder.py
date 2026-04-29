import os
import time
import subprocess
from datetime import datetime
import pytz
import sys

# Explicit config imports (IMPORTANT)
from video_system.config import (
    VIDEO_DEVICE,
    BASE_DIR,
    CLIP_DURATION,
    TIMEZONE,
    RECORD_START_TIME,
    RECORD_END_TIME,
)

# Ensure prints appear immediately
sys.stdout.reconfigure(line_buffering=True)

tz = pytz.timezone(TIMEZONE)


def parse_time_today(time_str: str) -> datetime:
    h, m = map(int, time_str.split(":"))
    now = datetime.now(tz)
    return now.replace(hour=h, minute=m, second=0, microsecond=0)


def next_10_min_boundary(after_time: datetime) -> datetime:
    minute = (after_time.minute // 10 + 1) * 10
    if minute >= 60:
        return after_time.replace(
            hour=after_time.hour + 1,
            minute=0,
            second=0,
            microsecond=0
        )
    return after_time.replace(
        minute=minute,
        second=0,
        microsecond=0
    )


def record_clip(start_time: datetime) -> None:
    date_dir = start_time.strftime("%Y-%m-%d")
    os.makedirs(os.path.join(BASE_DIR, date_dir), exist_ok=True)

    filename = start_time.strftime("%H-%M-%S") + ".mp4"
    filepath = os.path.join(BASE_DIR, date_dir, filename)

    print(f"Recording clip: {filepath}", flush=True)

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "dshow",
        "-rtbufsize", "256M",
        "-i", VIDEO_DEVICE,
        "-t", str(CLIP_DURATION),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        filepath
    ], check=True)

    print("Clip finished\n", flush=True)


def main() -> None:
    start_time = parse_time_today(RECORD_START_TIME)
    end_time = parse_time_today(RECORD_END_TIME)

    print(f"Recording window: {start_time} → {end_time}", flush=True)

    # Wait until recording window opens
    now = datetime.now(tz)
    if now < start_time:
        wait = (start_time - now).total_seconds()
        print(f"Waiting {int(wait)} seconds until start time…", flush=True)
        time.sleep(wait)

    # Align to next 10-minute boundary
    now = datetime.now(tz)
    if now.minute % 10 != 0:
        boundary = next_10_min_boundary(now)
        wait = (boundary - now).total_seconds()
        print(f"Aligning to boundary at {boundary}", flush=True)
        time.sleep(wait)

    print("Starting continuous recording…\n", flush=True)

    try:
        while True:
            clip_start = datetime.now(tz).replace(second=0, microsecond=0)

            if clip_start >= end_time:
                print("End time reached. Stopping recorder.", flush=True)
                break

            record_clip(clip_start)

    except KeyboardInterrupt:
        print("\nRecording stopped manually (Ctrl+C).", flush=True)


if __name__ == "__main__":
    main()
