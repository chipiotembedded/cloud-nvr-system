from datetime import datetime, timedelta
import pytz
from video_system.config import *

tz = pytz.timezone(TIMEZONE)

def get_required_clips(current_time):
    clips = []

    # Last 24 hours
    start_24h = current_time - timedelta(hours=24)

    t = start_24h.replace(minute=(start_24h.minute // 10) * 10, second=0)
    while t <= current_time:
        date = t.strftime("%Y-%m-%d")
        filename = t.strftime("%H-%M-%S") + ".mp4"
        path = f"{BASE_DIR}/{date}/{filename}"
        clips.append(path)
        t += timedelta(minutes=10)

    return clips

if __name__ == "__main__":
    now = datetime.now(tz)
    clips = get_required_clips(now)

    for c in clips:
        print(c)
