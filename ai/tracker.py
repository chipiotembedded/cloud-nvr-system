"""
tracker.py — thin wrappers:
  - FrameSource: read frames from HLS playlist or RTSP fallback
  - Detector:   YOLO + ByteTrack via Ultralytics built-in .track()
"""
import time
import cv2
from ultralytics import YOLO


# Reverse lookup helper
def build_class_lookup(classes_of_interest):
    """{name: id} -> {id: name}, plus list of ids we care about."""
    id_to_name = {v: k for k, v in classes_of_interest.items()}
    return id_to_name, list(classes_of_interest.values())


class FrameSource:
    """
    Reads frames from an HLS m3u8 (preferred — already on local disk)
    with auto-reconnect when the playlist gets rewritten or stalls.
    """
    def __init__(self, hls_path, reconnect_delay=2):
        self.path = hls_path
        self.cap = None
        self.reconnect_delay = reconnect_delay
        self._last_open = 0

    def _open(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.path)
        # Tiny buffer — we want live, not buffered
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        self._last_open = time.time()

    def read(self):
        """Returns (ok, frame). On failure, reconnects on next call."""
        if self.cap is None or not self.cap.isOpened():
            if time.time() - self._last_open < self.reconnect_delay:
                return False, None
            self._open()
            if self.cap is None or not self.cap.isOpened():
                return False, None
        ok, frame = self.cap.read()
        if not ok:
            self.cap.release()
            self.cap = None
            return False, None
        return True, frame

    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None


class Detector:
    """
    YOLO + ByteTrack tracking. Returns normalized detection dicts.
    """
    def __init__(self, model_path, device, conf, class_lookup, wanted_ids):
        self.model = YOLO(model_path)
        self.device = device
        self.conf = conf
        self.id_to_name = class_lookup
        self.wanted = wanted_ids

    def track(self, frame, persist=True):
        """
        Returns list of {track_id, class_name, bbox=(x1,y1,x2,y2), conf}
        for objects in classes_of_interest. Returns [] if nothing or no tracker yet.
        """
        results = self.model.track(
            source=frame,
            persist=persist,
            conf=self.conf,
            device=self.device,
            classes=self.wanted,
            tracker='bytetrack.yaml',
            verbose=False,
        )
        if not results:
            return []
        r = results[0]
        if r.boxes is None or r.boxes.id is None:
            return []
        boxes = r.boxes.xyxy.cpu().numpy()
        ids = r.boxes.id.cpu().numpy().astype(int)
        clss = r.boxes.cls.cpu().numpy().astype(int)
        confs = r.boxes.conf.cpu().numpy()

        out = []
        for bbox, tid, cls, cf in zip(boxes, ids, clss, confs):
            name = self.id_to_name.get(int(cls))
            if name is None:
                continue
            x1, y1, x2, y2 = bbox.tolist()
            out.append({
                'track_id': int(tid),
                'class_name': name,
                'bbox': (x1, y1, x2, y2),
                'conf': float(cf),
            })
        return out
