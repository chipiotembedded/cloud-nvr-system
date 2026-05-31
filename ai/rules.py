"""
rules.py — behavioural rules layered on top of tracking + zones.
Each rule looks at per-track state over time and decides if an alert fires.
"""
import time
import math
from datetime import datetime, time as dtime


# ─────────────────────────────────────────────────────────────
# Time-of-day helpers
# ─────────────────────────────────────────────────────────────

def _parse_hm(s):
    h, m = s.split(':')
    return dtime(int(h), int(m))


def is_in_window(now_dt, start_str, end_str):
    start = _parse_hm(start_str)
    end = _parse_hm(end_str)
    nowt = now_dt.time()
    if start <= end:
        return start <= nowt <= end
    # wraps midnight
    return nowt >= start or nowt <= end


def is_break_time(config, now_dt=None):
    now_dt = now_dt or datetime.now()
    for win in config.get('break_hours', []):
        if is_in_window(now_dt, win['start'], win['end']):
            return True
    return False


def is_office_hours(config, now_dt=None):
    oh = config.get('office_hours')
    if not oh:
        return True
    now_dt = now_dt or datetime.now()
    return is_in_window(now_dt, oh['start'], oh['end'])


# ─────────────────────────────────────────────────────────────
# Per-track state used by rules
# ─────────────────────────────────────────────────────────────

class TrackHistory:
    """
    Tracks per-id: first_seen, last_seen, last_position, stationary_since.
    Also tracks last-known association between objects (bag↔person) for
    'object left behind'.
    """
    def __init__(self):
        self.state = {}    # track_id -> dict
        self.last_person_near = {}   # object_track_id -> (person_track_id, ts)

    def update(self, track_id, class_name, bbox, now_ts, stationary_threshold_px=15):
        s = self.state.get(track_id)
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        if s is None:
            self.state[track_id] = {
                'class': class_name,
                'first_seen': now_ts,
                'last_seen': now_ts,
                'last_pos': (cx, cy),
                'stationary_since': now_ts,
                'last_bbox': bbox,
            }
            return self.state[track_id]
        # Movement check
        dx = cx - s['last_pos'][0]
        dy = cy - s['last_pos'][1]
        if math.hypot(dx, dy) > stationary_threshold_px:
            s['stationary_since'] = now_ts
            s['last_pos'] = (cx, cy)
        s['last_seen'] = now_ts
        s['last_bbox'] = bbox
        s['class'] = class_name
        return s

    def stale(self, track_id, now_ts, gone_after=10):
        """Has this track not been seen for `gone_after` seconds?"""
        s = self.state.get(track_id)
        if s is None:
            return True
        return (now_ts - s['last_seen']) > gone_after

    def forget(self, track_id):
        self.state.pop(track_id, None)
        self.last_person_near.pop(track_id, None)


# ─────────────────────────────────────────────────────────────
# Rules
# ─────────────────────────────────────────────────────────────

def _is_person(class_name):
    return class_name == 'person'


def _is_carriable(class_name):
    return class_name in ('backpack', 'handbag', 'suitcase', 'laptop', 'cell_phone')


def _iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0


def evaluate_loitering(history, config, alert_cb, frame):
    """If a person is stationary > N seconds, emit loitering alert."""
    thresh = config['thresholds']['loitering_seconds']
    now = time.time()
    for tid, s in list(history.state.items()):
        if not _is_person(s['class']):
            continue
        stationary_for = now - s['stationary_since']
        if stationary_for > thresh and (now - s.get('_last_loiter_alert', 0)) > thresh:
            s['_last_loiter_alert'] = now
            alert_cb(
                alert_type='loitering',
                message=f"Person (track {tid}) stationary for {int(stationary_for)}s",
                frame=frame,
                track_id=tid,
                class_name='person',
            )


def update_person_object_proximity(history, detections):
    """
    For each carriable object, remember the nearest person nearby.
    detections: list of {track_id, class_name, bbox}
    """
    persons = [d for d in detections if _is_person(d['class_name'])]
    now = time.time()
    for d in detections:
        if not _is_carriable(d['class_name']):
            continue
        ox1, oy1, ox2, oy2 = d['bbox']
        ocx, ocy = (ox1 + ox2) / 2.0, (oy1 + oy2) / 2.0
        best_pid, best_dist = None, float('inf')
        for p in persons:
            px1, py1, px2, py2 = p['bbox']
            pcx, pcy = (px1 + px2) / 2.0, (py1 + py2) / 2.0
            dist = math.hypot(ocx - pcx, ocy - pcy)
            if dist < best_dist:
                best_dist = dist
                best_pid = p['track_id']
        # Threshold: within ~120 px counts as "with" the person
        if best_pid is not None and best_dist < 120:
            history.last_person_near[d['track_id']] = (best_pid, now)


def evaluate_left_behind(history, config, alert_cb, frame):
    """
    If a carriable object has been seen but no person near it for > N seconds,
    fire alert.
    """
    thresh = config['thresholds']['left_behind_seconds']
    now = time.time()
    for tid, s in list(history.state.items()):
        if not _is_carriable(s['class']):
            continue
        last = history.last_person_near.get(tid)
        if last is None:
            continue
        last_pid, last_ts = last
        unattended = now - last_ts
        if unattended > thresh and (now - s.get('_last_lb_alert', 0)) > thresh:
            s['_last_lb_alert'] = now
            alert_cb(
                alert_type='left_behind',
                message=f"{s['class'].title()} (track {tid}) unattended for {int(unattended)}s",
                frame=frame,
                track_id=tid,
                class_name=s['class'],
            )


def evaluate_zone_events(zone_events, track_id, class_name, config,
                        alert_cb, frame, camera):
    """
    For each zone-event this frame, decide if it should alert.
    Restricted zones: any person ENTER triggers an alert (v1 — no face rec).
    """
    if not _is_person(class_name):
        return
    for ev in zone_events:
        if ev['event'] != 'enter':
            continue
        if not ev['restricted']:
            continue
        alert_cb(
            alert_type='zone_violation',
            message=f"Person (track {track_id}) entered restricted zone '{ev['zone']}' on {camera}",
            frame=frame,
            track_id=track_id,
            class_name='person',
            zone=ev['zone'],
        )


def evaluate_capacity(zone_mgr, active_tracks, config, alert_cb, frame, camera):
    """If any zone exceeds capacity, alert (cooldown via alerts.py)."""
    if not zone_mgr.has_zones():
        return
    counts = zone_mgr.occupancy(active_tracks)
    for zname, cnt in counts.items():
        cap = zone_mgr.zones[zname]['capacity']
        if cnt > cap:
            alert_cb(
                alert_type='zone_capacity',
                message=f"Zone '{zname}' on {camera} over capacity: {cnt}/{cap}",
                frame=frame,
                track_id=None,
                class_name=None,
                zone=zname,
            )


def evaluate_break_violation(history, config, alert_cb, frame, camera,
                              gone_seconds=15):
    """
    If a person was present > presence_min_seconds and now hasn't been seen
    for `gone_seconds`, and we're NOT in break hours, alert.
    """
    if is_break_time(config):
        return
    if not is_office_hours(config):
        return
    now = time.time()
    pmin = config['thresholds']['presence_min_seconds']
    for tid, s in list(history.state.items()):
        if not _is_person(s['class']):
            continue
        present_for = s['last_seen'] - s['first_seen']
        gone_for = now - s['last_seen']
        if present_for > pmin and gone_seconds < gone_for < gone_seconds + 30:
            if s.get('_break_alerted'):
                continue
            s['_break_alerted'] = True
            alert_cb(
                alert_type='out_of_room_non_break',
                message=f"Person (track {tid}) left {camera} outside break hours after {int(present_for)}s present",
                frame=frame,
                track_id=tid,
                class_name='person',
            )
