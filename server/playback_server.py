from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import time

app = Flask(__name__)

RECORDING_FOLDER = "/var/www/recordings/roll"

@app.route('/roll')
def roll():
    return render_template("rollplayback.html")

@app.route('/video/<path:filename>')
def video(filename):
    return send_from_directory(RECORDING_FOLDER, filename)

@app.route('/get_synced_clips')
def get_synced_clips():
    ts = request.args.get("ts")

    try:
        target = int(ts) if ts else int(time.time())
    except:
        target = int(time.time())

    cams = ["cam104", "cam105", "cam106"]

    result = {}
    all_times = []

    try:
        files = os.listdir(RECORDING_FOLDER)
    except:
        return jsonify({"cam104": None, "cam105": None, "cam106": None})

    for cam in cams:
        cam_files = []

        for f in files:
            if f.startswith(cam) and (f.endswith(".mp4") or f.endswith(".flv")):
                try:
                    t = int(f.split("-")[1].split(".")[0])
                    cam_files.append((f, t))
                    all_times.append(t)
                except:
                    continue

        cam_files.sort(key=lambda x: x[1])

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

    if all_times:
        result["min_ts"] = min(all_times)
        result["max_ts"] = max(all_times)

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
