from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import time
import sys
sys.path.insert(0, '/home/cloud/cloud-nvr-system/ai')
from ai_routes import ai_bp
app = Flask(
    __name__,
    template_folder='/home/cloud/cloud-nvr-system/templates'
)
app.register_blueprint(ai_bp)
ROLL_FOLDER = "/var/www/recordings/roll"
HR24_FOLDER = "/var/www/recordings/24hr"
HLS_FOLDER  = "/var/www/recordings/hls"
CLIP_DURATION = 600    # 10 minutes per roll clip
HR24_CHUNK    = 3600   # 1 hour per 24hr chunk

# ─────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────

@app.route('/')
@app.route('/roll')
def roll():
    return render_template("rollplayback.html")

@app.route('/24hr')
def hr24():
    return render_template("24hr_clip.html")

@app.route('/live')
def live():
    return render_template("livestream.html")

# ─────────────────────────────────────────
# VIDEO FILE SERVING
# ─────────────────────────────────────────

@app.route('/video/roll/<path:filename>')
def video_roll(filename):
    return send_from_directory(ROLL_FOLDER, filename)

@app.route('/video/24hr/<path:filename>')
def video_24hr(filename):
    return send_from_directory(HR24_FOLDER, filename)

@app.route('/video/<path:filename>')
def video_legacy(filename):
    if os.path.exists(os.path.join(ROLL_FOLDER, filename)):
        return send_from_directory(ROLL_FOLDER, filename)
    return send_from_directory(HR24_FOLDER, filename)

# ─────────────────────────────────────────
# ROLL: synced clips API — rolling window
# ─────────────────────────────────────────

@app.route('/get_synced_clips')
def get_synced_clips():
    ts = request.args.get("ts")
    try:
        target = int(ts) if ts else int(time.time())
    except Exception:
        target = int(time.time())

    cams      = ["cam104", "cam105", "cam106"]
    result    = {}
    all_times = []
    now       = int(time.time())
    cutoff    = now - (86400 * 30)

    try:
        files = os.listdir(ROLL_FOLDER)
    except Exception:
        return jsonify({c: None for c in cams})

    cam_files_map = {}
    for cam in cams:
        cam_files = []
        for f in files:
            if f.startswith(cam) and f.endswith(".mp4"):
                try:
                    t = int(f.split("-")[1].split(".")[0])
                    if t >= cutoff:
                        cam_files.append((f, t))
                        all_times.append(t)
                except Exception:
                    continue
        cam_files.sort(key=lambda x: x[1])
        cam_files_map[cam] = cam_files

    # Live mode: find latest common timestamp across all cams
    if not ts:
        common_times = None
        for cam in cams:
            cam_ts = set(t for f, t in cam_files_map[cam])
            if not cam_ts:
                continue
            if common_times is None:
                common_times = cam_ts
            else:
                common_times = common_times & cam_ts

        if common_times:
            target = max(common_times) + CLIP_DURATION - 1
        elif all_times:
            target = max(all_times) + CLIP_DURATION - 1

    window_start = target - CLIP_DURATION

    for cam in cams:
        cam_files = cam_files_map[cam]
        if not cam_files:
            result[cam] = None
            continue

    for cam in cams:
        cam_files = cam_files_map[cam]
        selected = None
        for f, t in cam_files:
            if t <= window_start:
                selected = (f, t)
            else:
                break

        if selected is None:
            selected = cam_files[0]

        filename, clip_start_ts = selected
        offset = max(0, min(window_start - clip_start_ts, CLIP_DURATION - 1))

        result[cam] = {
            "file":          filename,
            "offset":        offset,
            "clip_start_ts": clip_start_ts,
            "window_start":  window_start,
            "target":        target,
        }

    timeline = sorted(set(t for cam in cams for f, t in cam_files_map[cam]))

    result["min_ts"]       = min(all_times) if all_times else None
    result["max_ts"]       = max(all_times) if all_times else None
    result["timeline"]     = timeline
    result["target"]       = target
    result["window_start"] = window_start

    return jsonify(result)

# ─────────────────────────────────────────
# 24HR: clip lookup API (1hr chunks)
# ─────────────────────────────────────────

@app.route('/get_24hr_clip')
def get_24hr_clip():
    time_str = request.args.get("time")
    cam      = request.args.get("cam", "cam104")

    if not time_str:
        return jsonify({"error": "no time provided"})

    try:
        import datetime
        dt        = datetime.datetime.fromisoformat(time_str)
        target_ts = int(dt.timestamp())
    except Exception as e:
        return jsonify({"error": str(e)})

    try:
        files = os.listdir(HR24_FOLDER)
    except Exception:
        return jsonify({"error": "cannot read 24hr folder"})

    cam_files = []
    for f in files:
        if f.startswith(cam) and f.endswith(".mp4"):
            try:
                t = int(f.split("-")[1].split(".")[0])
                cam_files.append((f, t))
            except Exception:
                continue

    cam_files.sort(key=lambda x: x[1])

    if not cam_files:
        return jsonify({"error": f"no 24hr clips found for {cam}"})

    selected = None
    for f, t in cam_files:
        if t <= target_ts:
            selected = (f, t)
        else:
            break

    if not selected:
        selected = cam_files[0]

    file1, file1_ts = selected
    offset = max(0, min(target_ts - file1_ts, HR24_CHUNK - 1))
    idx    = cam_files.index(selected)
    file2  = cam_files[idx + 1][0] if idx + 1 < len(cam_files) else None

    import datetime
    timeline = []
    for f, t in cam_files:
        dt_local = datetime.datetime.fromtimestamp(t)
        timeline.append({
            "ts":       t,
            "file":     f,
            "label":    dt_local.strftime("%d %b %H:%M"),
            "duration": HR24_CHUNK,
        })

    return jsonify({
        "file1":          file1,
        "file2":          file2,
        "offset":         offset,
        "cam":            cam,
        "file1_ts":       file1_ts,
        "timeline":       timeline,
        "chunk_duration": HR24_CHUNK,
    })

# ─────────────────────────────────────────
# 24HR: available dates/chunks per camera
# ─────────────────────────────────────────

@app.route('/get_24hr_dates')
def get_24hr_dates():
    cam = request.args.get("cam", "cam104")

    try:
        files = os.listdir(HR24_FOLDER)
    except Exception:
        return jsonify({"dates": [], "error": "cannot read 24hr folder"})

    import datetime
    dates  = set()
    chunks = []

    for f in files:
        if f.startswith(cam) and f.endswith(".mp4"):
            try:
                t        = int(f.split("-")[1].split(".")[0])
                dt_local = datetime.datetime.fromtimestamp(t)
                dates.add(dt_local.strftime("%Y-%m-%d"))
                chunks.append({"ts": t, "file": f, "label": dt_local.strftime("%d %b %H:%M")})
            except Exception:
                continue

    chunks.sort(key=lambda x: x["ts"])

    return jsonify({
        "cam":            cam,
        "dates":          sorted(list(dates)),
        "chunks":         chunks,
        "chunk_duration": HR24_CHUNK,
    })

# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────

@app.route('/health')
def health():
    roll_count = len([f for f in os.listdir(ROLL_FOLDER) if f.endswith(".mp4")]) \
        if os.path.exists(ROLL_FOLDER) else 0
    hr24_count = len([f for f in os.listdir(HR24_FOLDER) if f.endswith(".mp4")]) \
        if os.path.exists(HR24_FOLDER) else 0
    hls_active = []
    if os.path.exists(HLS_FOLDER):
        for cam in ["cam104", "cam105", "cam106"]:
            if os.path.exists(os.path.join(HLS_FOLDER, cam, "index.m3u8")):
                hls_active.append(cam)
    return jsonify({
        "roll_clips": roll_count, "24hr_clips": hr24_count,
        "live_streams": hls_active, "chunk_duration": HR24_CHUNK, "status": "ok"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
