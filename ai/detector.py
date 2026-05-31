#!/usr/bin/env python3
"""
detector.py — the AI service main loop.

Reads HLS frames from /var/www/recordings/hls/<cam>/index.m3u8 for each
configured camera, runs YOLO+ByteTrack, evaluates zone+behaviour rules,
and writes alerts via alerts.py.

Architecture choice (CPU constraint):
  - One detector model shared across all cameras (saves ~600MB RAM)
  - Cameras round-robin: read 1 frame from cam104, infer, then cam105, etc.
  - Each camera gets ~1.5-2 fps effective. Plenty for surveillance.
  - Skipping is acceptable — ByteTrack handles temporal gaps via Kalman
    prediction between detections.

Run:
  python3 detector.py /home/cloud/cloud-nvr-system/ai/config.yaml
"""
import os
import sys
import time
import yaml
import signal
import threading

# Local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts
import zones as zones_mod
import rules as rules_mod
import reid as reid_mod
from tracker import FrameSource, Detector, build_class_lookup


# Global so the Flask sidecar can read live snapshots if we want later
LIVE_FRAMES = {}  # camera -> latest annotated frame (kept small in memory)
LIVE_LOCK = threading.Lock()

STOP = False


def handle_sigterm(signum, frame):
    global STOP
    STOP = True
    print(f"[detector] caught signal {signum}, stopping...")


signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGTERM, handle_sigterm)


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def build_camera_states(config, id_to_name, wanted_ids):
    """One state bag per camera. Detector instance is per-camera because
    ByteTrack state lives inside the Ultralytics model object."""
    states = {}
    for cam_name, cam_cfg in config['cameras'].items():
        states[cam_name] = {
            'name': cam_name,
            'config': cam_cfg,
            'source': FrameSource(cam_cfg['hls_path']),
            'detector': Detector(
                model_path=config['inference']['model'],
                device=config['inference']['device'],
                conf=config['inference']['confidence'],
                class_lookup=id_to_name,
                wanted_ids=wanted_ids,
            ),
            'zones': zones_mod.ZoneManager(cam_cfg),
            'history': rules_mod.TrackHistory(),
            'last_frame_ts': 0,
            'frame_count': 0,
        }
    return states


def draw_annotations(frame, detections, zone_mgr):
    """Minimal annotations — thin boxes, small labels. Not messy."""
    import cv2
    # Draw zones first, faded
    if zone_mgr.has_zones():
        overlay = frame.copy()
        for zname, z in zone_mgr.zones.items():
            pts = list(z['polygon'].exterior.coords)
            import numpy as np
            poly = np.array(pts, dtype=np.int32).reshape(-1, 1, 2)
            color = (0, 0, 200) if z['restricted'] else (0, 180, 0)
            cv2.polylines(overlay, [poly], True, color, 1)
            # Label at first vertex
            x, y = pts[0]
            cv2.putText(overlay, zname, (int(x) + 4, int(y) + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

    for d in detections:
        x1, y1, x2, y2 = [int(v) for v in d['bbox']]
        color = (50, 220, 50) if d['class_name'] == 'person' else (220, 180, 50)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
        label = f"{d['class_name']}#{d['track_id']}"
        cv2.putText(frame, label, (x1, max(0, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    return frame


def process_camera(state, config, reid_store):
    """One processing tick for one camera. Returns True if a frame was processed."""
    src = state['source']
    ok, frame = src.read()
    if not ok or frame is None:
        return False

    state['frame_count'] += 1
    # Skip frames to hit target fps. detection_interval_frames controls this.
    interval = config['inference'].get('detection_interval_frames', 4)
    if state['frame_count'] % interval != 0:
        return True

    now = time.time()
    cam = state['name']

    detections = state['detector'].track(frame)

    # Update per-track history
    for d in detections:
        state['history'].update(d['track_id'], d['class_name'], d['bbox'], now)

    # Person-object proximity for left-behind rule
    rules_mod.update_person_object_proximity(state['history'], detections)

    # Zone events per track
    def alert_cb(**kw):
        alerts.emit(config, camera=cam, **kw)

    active_tracks = {d['track_id']: d['bbox'] for d in detections}
    for d in detections:
        ev = state['zones'].update(d['track_id'], d['bbox'], now)
        if ev:
            rules_mod.evaluate_zone_events(
                ev, d['track_id'], d['class_name'],
                config, alert_cb, frame, cam
            )

    # Re-ID indexing for carriable objects (within-camera)
    if config.get('reid', {}).get('enabled'):
        for d in detections:
            if d['class_name'] in ('backpack', 'handbag', 'suitcase', 'laptop'):
                crop = reid_mod.crop_from_frame(frame, d['bbox'])
                emb = reid_mod.embed(crop)
                if emb is not None:
                    reid_store.add(cam, d['class_name'], d['track_id'], emb, now)

    # Behavioural rules
    rules_mod.evaluate_loitering(state['history'], config, alert_cb, frame)
    rules_mod.evaluate_left_behind(state['history'], config, alert_cb, frame)
    rules_mod.evaluate_capacity(state['zones'], active_tracks, config,
                                alert_cb, frame, cam)
    rules_mod.evaluate_break_violation(state['history'], config,
                                        alert_cb, frame, cam)

    # Stash annotated frame for live dashboard
    annotated = draw_annotations(frame.copy(), detections, state['zones'])
    with LIVE_LOCK:
        LIVE_FRAMES[cam] = annotated

    state['last_frame_ts'] = now
    return True


def cleanup_loop(config):
    """Daily snapshot/DB cleanup in background."""
    while not STOP:
        try:
            alerts.cleanup_old(config)
        except Exception as e:
            print(f"[cleanup] {e}")
        # Sleep 1 hour, but wake on STOP
        for _ in range(3600):
            if STOP:
                return
            time.sleep(1)


def main(config_path):
    config = load_config(config_path)
    print(f"[detector] loaded config from {config_path}")
    print(f"[detector] cameras: {list(config['cameras'].keys())}")

    alerts.init_db(config['storage']['db_path'])
    os.makedirs(config['storage']['snapshot_dir'], exist_ok=True)

    id_to_name, wanted_ids = build_class_lookup(
        config['inference']['classes_of_interest']
    )
    states = build_camera_states(config, id_to_name, wanted_ids)

    reid_store = reid_mod.ReIDStore(
        history_size=config['reid']['track_history_size'],
        similarity_threshold=config['reid']['similarity_threshold'],
    )

    cleanup_thread = threading.Thread(
        target=cleanup_loop, args=(config,), daemon=True
    )
    cleanup_thread.start()

    cams = list(states.keys())
    idx = 0
    consecutive_failures = {c: 0 for c in cams}

    print("[detector] entering main loop")
    while not STOP:
        cam = cams[idx % len(cams)]
        idx += 1
        try:
            processed = process_camera(states[cam], config, reid_store)
            if not processed:
                consecutive_failures[cam] += 1
                if consecutive_failures[cam] % 50 == 0:
                    print(f"[detector] {cam}: no frames for {consecutive_failures[cam]} ticks")
                time.sleep(0.2)
            else:
                consecutive_failures[cam] = 0
        except Exception as e:
            print(f"[detector] error on {cam}: {e}")
            consecutive_failures[cam] += 1
            time.sleep(1)

    for s in states.values():
        s['source'].close()
    print("[detector] stopped cleanly")


if __name__ == '__main__':
    cfg = sys.argv[1] if len(sys.argv) > 1 else '/home/cloud/cloud-nvr-system/ai/config.yaml'
    main(cfg)
