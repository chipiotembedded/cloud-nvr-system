from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import time

app = Flask(__name__, template_folder='/home/cloud/cloud-nvr-system/templates')

ROLL_FOLDER = "/var/www/recordings/roll"
HR24_FOLDER = "/var/www/recordings/24hr"

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

# ─────────────────────────────────────────
# VIDEO FILE SERVING
# ─────────────────────────────────────────

@app.route('/video/roll/<path:filename>')
def video_roll(filename):
    return send_from_directory(ROLL_FOLDER, filename)

@app.route('/video/24hr/<path:filename>')
def video_24hr(filename):
    return send_from_directory(HR24_FOLDER, filename)

# keep old /video/<filename> route working for any existing links
@app.route('/video/<path:filename>')
def video_legacy(filename):
    if os.path.exists(os.path.join(ROLL_FOLDER, filename)):
        return send_from_directory(ROLL_FOLDER, filename)
    return send_from_directory(HR24_FOLDER, filename)

# ─────────────────────────────────────────
# ROLL: synced clips API
# ─────────────────────────────────────────

@app.route('/get_synced_clips')
def get_synced_clips():
    ts = request.args.get("ts")
    try:
        target = int(ts) if ts else int(time.time())
    except Exception:
        target = int(time.time())

    cams = ["cam104", "cam105", "cam106"]
    result = {}
    all_times = []
    now = int(time.time())
    cutoff = now - 86400

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

    for cam in cams:
        cam_files = cam_files_map[cam]
        selected = None
        closest_diff = float('inf')
        for f, t in cam_files:
            diff = abs(t - target)
            if diff < closest_diff:
                closest_diff = diff
                selected = f
        if not selected and cam_files:
            selected = cam_files[0][0]
        result[cam] = selected

    timeline = []
    seen = set()
    for cam in cams:
        for f, t in cam_files_map[cam]:
            if t not in seen:
                seen.add(t)
                timeline.append(t)
    timeline.sort()

    result["min_ts"] = min(all_times) if all_times else None
    result["max_ts"] = max(all_times) if all_times else None
    result["timeline"] = timeline

    return jsonify(result)

# ─────────────────────────────────────────
# 24HR: clip lookup API
# ─────────────────────────────────────────

@app.route('/get_24hr_clip')
def get_24hr_clip():
    time_str = request.args.get("time")
    cam = request.args.get("cam", "cam104")

    if not time_str:
        return jsonify({"error": "no time provided"})

    try:
        import datetime
        dt = datetime.datetime.fromisoformat(time_str)
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
    offset = max(0, target_ts - file1_ts)

    idx = cam_files.index(selected)
    file2 = cam_files[idx + 1][0] if idx + 1 < len(cam_files) else None

    return jsonify({
        "file1": file1,
        "file2": file2,
        "offset": offset,
        "cam": cam
    })

# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────

@app.route('/health')
def health():
    roll_count = len([f for f in os.listdir(ROLL_FOLDER) if f.endswith(".mp4")]) if os.path.exists(ROLL_FOLDER) else 0
    hr24_count = len([f for f in os.listdir(HR24_FOLDER) if f.endswith(".mp4")]) if os.path.exists(HR24_FOLDER) else 0
    return jsonify({
        "roll_clips": roll_count,
        "24hr_clips": hr24_count,
        "status": "ok"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
