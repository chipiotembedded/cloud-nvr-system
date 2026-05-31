"""
reid.py — within-camera re-identification of objects (mainly bags).

v1 design choice: we use a LIGHT embedding (color histogram + texture
descriptor concatenated) instead of CLIP. Why:
  - CPU-only VM. CLIP ViT-B/32 is ~150ms per crop. With 5-10 crops/frame
    × 3 cams it would dominate the inference budget.
  - For "is this the same bag I saw before in this camera" within minutes,
    a 192-dim color+texture vector at < 5ms/crop is plenty.
  - Cross-camera (v2) WILL need CLIP. The interface is the same; swap in
    CLIPEmbedder when you upgrade.

The store is in-memory per (camera, class_name). Trades off restartability
for speed; alerts.db is what persists.
"""
import cv2
import numpy as np
from collections import deque


def _color_hist(crop):
    """3-channel HSV histogram, normalized."""
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 4], [0, 180, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten()  # 8*8*4 = 256


def _texture_desc(crop):
    """Small grayscale gradient signature."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (16, 16))
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    mag = np.hypot(gx, gy)
    mag /= (mag.max() + 1e-6)
    return mag.flatten()  # 256


def embed(crop_bgr):
    """Return a unit-norm feature vector for the crop. Returns None if invalid."""
    if crop_bgr is None or crop_bgr.size == 0:
        return None
    h, w = crop_bgr.shape[:2]
    if h < 8 or w < 8:
        return None
    v = np.concatenate([_color_hist(crop_bgr), _texture_desc(crop_bgr)])
    n = np.linalg.norm(v)
    if n < 1e-6:
        return None
    return v / n


def cosine(a, b):
    return float(np.dot(a, b))


class ReIDStore:
    """
    Per (camera, class_name) ring buffer of recent embeddings.
    Used for: 'did this newly-seen bag match one we saw 30 min ago?'
    """
    def __init__(self, history_size=200, similarity_threshold=0.75):
        self.size = history_size
        self.thresh = similarity_threshold
        self.buckets = {}  # (camera, class_name) -> deque of (track_id, embedding, ts)

    def add(self, camera, class_name, track_id, embedding, ts):
        key = (camera, class_name)
        if key not in self.buckets:
            self.buckets[key] = deque(maxlen=self.size)
        self.buckets[key].append((track_id, embedding, ts))

    def match(self, camera, class_name, embedding):
        """Return (best_track_id, similarity) or (None, 0) if no match above threshold."""
        key = (camera, class_name)
        if key not in self.buckets or embedding is None:
            return None, 0.0
        best_tid, best_sim = None, 0.0
        for tid, emb, _ts in self.buckets[key]:
            sim = cosine(embedding, emb)
            if sim > best_sim:
                best_sim = sim
                best_tid = tid
        if best_sim >= self.thresh:
            return best_tid, best_sim
        return None, best_sim


def crop_from_frame(frame, bbox, pad=4):
    """Return crop given bbox=(x1,y1,x2,y2), with safe padding."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    x1 = max(0, int(x1) - pad)
    y1 = max(0, int(y1) - pad)
    x2 = min(w, int(x2) + pad)
    y2 = min(h, int(y2) + pad)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2].copy()
