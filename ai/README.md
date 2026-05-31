# NVR AI Surveillance Module

Adds object detection, tracking, zone restriction, loitering detection, and
object-left-behind alerts to the existing Cloud NVR. Runs as a separate
service alongside the NVR — existing infrastructure is untouched.

## What it detects

| Feature | Cameras | What triggers an alert |
|---|---|---|
| Zone violation | cam106 | Person enters upper or lower restricted area |
| Zone capacity | cam106 | More than N people in a zone |
| Loitering | all | Person stationary > 5 min |
| Object left behind | all | Bag/laptop with no person nearby > 3 min |
| Out-of-room non-break | all | Person disappears outside break hours after being present > 60s |

Re-identification (within-camera): a bag picked up and put down elsewhere
on the same camera is recognised by colour+texture fingerprint. Cross-camera
re-ID is v2.

## Files

| File | Purpose |
|---|---|
| `config.yaml` | Zones, break hours, thresholds. **You edit this.** |
| `detector.py` | Main loop. Pulls HLS frames, runs YOLO, applies rules. |
| `tracker.py` | YOLO + ByteTrack wrapper, HLS frame source. |
| `zones.py` | Polygon entry/exit detection. |
| `rules.py` | Loitering, left-behind, capacity, break-violation logic. |
| `reid.py` | Lightweight colour+texture embeddings for object re-ID. |
| `alerts.py` | SQLite writes + snapshot saving + cooldown. |
| `ai_routes.py` | Flask blueprint — `/ai` dashboard + API routes. |
| `ai_dashboard.html` | The dashboard UI. Goes in `templates/`. |
| `calibrate.py` | Grabs frames from each camera so you can read pixel coords. |
| `nvr-ai.service` | Systemd unit. |
| `install.sh` | One-shot installer. |

## Architecture

```
HLS chunks on local disk      (already being written by your nginx-rtmp)
  /var/www/recordings/hls/<cam>/index.m3u8
        │
        ▼
detector.py  ──── reads frames, round-robins 3 cams
  │
  ├─ YOLOv8n (ultralytics) ──── detects person, backpack, handbag, laptop, chair, ...
  ├─ ByteTrack ──── assigns persistent track IDs across frames
  ├─ zones.py ──── polygon intersection -> enter/exit events
  ├─ rules.py ──── loitering, left-behind, capacity, break-violation
  └─ reid.py  ──── colour+texture fingerprint for object re-ID
        │
        ▼
  alerts.py  ──── writes to SQLite + saves snapshot JPG
        │
        ▼
  /var/www/ai/alerts.db
  /var/www/ai/snapshots/*.jpg
        │
        ▼
  ai_routes.py (mounted in your existing playback_server.py)
        │
        ▼
  Browser:  http://34.93.38.200:5000/ai
```

## Install

1. SCP the `ai/` folder to the VM:
   ```bash
   gcloud compute scp --recurse ai/ cloud-server-1:/home/cloud/cloud-nvr-system/ --zone=asia-south1-c
   ```

2. SSH in and run the installer:
   ```bash
   gcloud compute ssh cloud-server-1 --zone=asia-south1-c
   cd /home/cloud/cloud-nvr-system/ai
   chmod +x install.sh calibrate.py
   ./install.sh
   ```

3. Wire the Flask blueprint into your existing server. Edit
   `/home/cloud/cloud-nvr-system/server/playback_server.py` — right after
   the `app = Flask(...)` line, add:

   ```python
   import sys
   sys.path.insert(0, '/home/cloud/cloud-nvr-system/ai')
   from ai_routes import ai_bp
   app.register_blueprint(ai_bp)
   ```

4. Calibrate zones on cam106 — get a real frame with a coordinate grid:
   ```bash
   python3 calibrate.py
   gcloud compute scp cloud-server-1:/tmp/calibrate/cam106.jpg . --zone=asia-south1-c
   ```
   Open `cam106.jpg`, read the pixel coordinates of the corners of your
   upper and lower zones, edit `config.yaml`.

5. Start everything:
   ```bash
   sudo systemctl restart nvr-playback
   sudo systemctl start nvr-ai
   tail -f /home/cloud/ai_detector.log
   ```

6. Open the dashboard: `http://34.93.38.200:5000/ai`

## Performance expectations (CPU only on a 2-vCPU VM)

- YOLOv8n inference: ~150-250ms per frame
- Effective fps per camera: **~1.5-2 fps** (round-robin across 3 cams)
- Memory: ~1.2 GB resident (model + tracker state + 3 frame buffers)
- Disk write: ~50 KB per alert (snapshot JPG)

If detection feels slow:
- Bump VM to 4 vCPU (~$30/mo extra) → ~3-4 fps per camera
- Or: convert model to ONNX (`yolo export model=yolov8n.pt format=onnx`)
  and edit `inference.model` in config.yaml. Roughly 2x faster on CPU.

## Tuning

All thresholds are in `config.yaml`. Common knobs:

- **Too many loitering alerts** → raise `loitering_seconds` to 600 (10 min)
- **Missed bag thefts** → lower `left_behind_seconds` to 60 (1 min)
- **Zone alert spam** → raise `alert_cooldown_seconds` to 120
- **False zone crossings on edges** → shrink your polygon by ~20 pixels
  on each side

## Logs & commands

```bash
# Service status
sudo systemctl status nvr-ai

# Tail the detector log
tail -f /home/cloud/ai_detector.log

# How many alerts today
sqlite3 /var/www/ai/alerts.db "SELECT COUNT(*) FROM alerts WHERE ts > strftime('%s','now','start of day');"

# Recent alerts
sqlite3 /var/www/ai/alerts.db "SELECT ts_iso, camera, alert_type, message FROM alerts ORDER BY ts DESC LIMIT 20;"

# Restart detector after config edit
sudo systemctl restart nvr-ai

# Wipe alerts (start fresh)
sudo systemctl stop nvr-ai
sudo rm /var/www/ai/alerts.db
sudo rm -rf /var/www/ai/snapshots/*
python3 -c "import sys; sys.path.insert(0,'/home/cloud/cloud-nvr-system/ai'); from alerts import init_db; init_db('/var/www/ai/alerts.db')"
sudo systemctl start nvr-ai
```

## Troubleshooting

**"no frames for N ticks" in the log**
→ HLS playlist not being written. Check that your Windows FFmpeg
`livestream` push is running and that `/var/www/recordings/hls/<cam>/index.m3u8`
exists and is being updated.

**Detector eats 100% CPU and Flask becomes slow**
→ Expected. The detector and Flask share the VM. Either give the VM more
vCPUs, or set `Nice=10` in `nvr-ai.service` to deprioritise the detector.

**YOLO download fails on first run**
→ Either the VM has no outbound internet, or pip's network is fine but
ultralytics's CDN is blocked. Manually download `yolov8n.pt` and place it
in `/home/cloud/cloud-nvr-system/ai/`.

**Zone alerts fire constantly**
→ Polygon is wrong. Re-run `calibrate.py` and re-check coordinates.

## What's NOT in v1

- Cross-camera re-identification (needs CLIP + Qdrant; planned for v2)
- Face recognition (needs enrollment UI; planned for v2)
- Per-employee zone allow-lists (depends on face rec)
- Email/WhatsApp alerts (dashboard-only as you requested)
- Live annotated video stream on the dashboard (frames are stashed in
  memory, but no MJPEG endpoint yet — easy to add)
- Heatmaps and daily PDF reports (planned for v2)
