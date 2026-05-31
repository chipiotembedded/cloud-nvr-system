"""
alerts.py — central alert sink.
Writes to SQLite + saves a snapshot JPG.
Enforces cooldown so the same (camera, track_id, alert_type) doesn't spam.
"""
import os
import sqlite3
import time
import threading
import cv2
from datetime import datetime

_lock = threading.Lock()
_cooldown_cache = {}  # (cam, track_id, alert_type) -> last_emit_ts


SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,
    ts_iso      TEXT    NOT NULL,
    camera      TEXT    NOT NULL,
    alert_type  TEXT    NOT NULL,
    track_id    INTEGER,
    class_name  TEXT,
    zone        TEXT,
    message     TEXT    NOT NULL,
    snapshot    TEXT,
    extra       TEXT,
    acked       INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts     ON alerts(ts DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_camera ON alerts(camera);
CREATE INDEX IF NOT EXISTS idx_alerts_type   ON alerts(alert_type);
"""


def init_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def _save_snapshot(frame, snapshot_dir, camera, alert_type, quality=80):
    if frame is None:
        return None
    os.makedirs(snapshot_dir, exist_ok=True)
    ts = int(time.time() * 1000)
    fname = f"{camera}_{alert_type}_{ts}.jpg"
    fpath = os.path.join(snapshot_dir, fname)
    cv2.imwrite(fpath, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return fname


def emit(config, camera, alert_type, message,
         frame=None, track_id=None, class_name=None,
         zone=None, extra=None):
    """
    Write an alert. Returns alert id or None if suppressed by cooldown.
    """
    cooldown = config['thresholds']['alert_cooldown_seconds']
    now = time.time()

    key = (camera, track_id, alert_type)
    last = _cooldown_cache.get(key, 0)
    if now - last < cooldown:
        return None
    _cooldown_cache[key] = now

    snapshot_name = _save_snapshot(
        frame,
        config['storage']['snapshot_dir'],
        camera,
        alert_type,
        config['storage'].get('snapshot_quality', 80)
    ) if frame is not None else None

    ts = int(now)
    ts_iso = datetime.fromtimestamp(ts).isoformat()

    with _lock:
        conn = sqlite3.connect(config['storage']['db_path'])
        cur = conn.execute(
            """INSERT INTO alerts
               (ts, ts_iso, camera, alert_type, track_id, class_name,
                zone, message, snapshot, extra)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (ts, ts_iso, camera, alert_type, track_id, class_name,
             zone, message, snapshot_name,
             None if extra is None else str(extra))
        )
        alert_id = cur.lastrowid
        conn.commit()
        conn.close()

    print(f"[ALERT #{alert_id}] {ts_iso} {camera} {alert_type}: {message}")
    return alert_id


def cleanup_old(config):
    """Delete snapshots + DB rows older than retention_days."""
    days = config['storage'].get('retention_days', 14)
    cutoff = int(time.time()) - (days * 86400)
    snapshot_dir = config['storage']['snapshot_dir']

    with _lock:
        conn = sqlite3.connect(config['storage']['db_path'])
        old = conn.execute(
            "SELECT snapshot FROM alerts WHERE ts < ? AND snapshot IS NOT NULL",
            (cutoff,)
        ).fetchall()
        for (snap,) in old:
            try:
                os.remove(os.path.join(snapshot_dir, snap))
            except OSError:
                pass
        conn.execute("DELETE FROM alerts WHERE ts < ?", (cutoff,))
        conn.commit()
        conn.close()
