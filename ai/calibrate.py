#!/usr/bin/env python3
"""
calibrate.py — grab one frame from each camera's HLS and save as JPG.
Open the JPGs in any image viewer to read pixel coordinates for zone
polygon corners, then paste them into config.yaml.

Run:
    python3 calibrate.py

Outputs to /tmp/calibrate/cam104.jpg, cam105.jpg, cam106.jpg
Then: scp from the VM to look at them, or `display` them via X-forwarding.
"""
import os
import cv2
import sys
import yaml

CONFIG = '/home/cloud/cloud-nvr-system/ai/config.yaml'
OUT = '/tmp/calibrate'

def main():
    with open(CONFIG) as f:
        cfg = yaml.safe_load(f)
    os.makedirs(OUT, exist_ok=True)

    for cam, c in cfg['cameras'].items():
        hls = c['hls_path']
        print(f"[{cam}] reading {hls} ...")
        cap = cv2.VideoCapture(hls)
        ok, frame = False, None
        for _ in range(30):  # skip a few frames to get past any partial init
            ok, frame = cap.read()
            if ok:
                break
        cap.release()
        if not ok or frame is None:
            print(f"[{cam}] FAILED — is the FFmpeg livestream pushing?")
            continue
        h, w = frame.shape[:2]
        # draw a coordinate grid every 50px so picking is easy
        for x in range(0, w, 50):
            cv2.line(frame, (x, 0), (x, h), (200, 200, 200), 1)
            cv2.putText(frame, str(x), (x + 2, 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
        for y in range(0, h, 50):
            cv2.line(frame, (0, y), (w, y), (200, 200, 200), 1)
            cv2.putText(frame, str(y), (2, y + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
        out_path = os.path.join(OUT, f"{cam}.jpg")
        cv2.imwrite(out_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f"[{cam}] saved {out_path} ({w}x{h})")

    print("\nNow:")
    print(f"  scp from the VM: gcloud compute scp cloud-server-1:{OUT}/cam106.jpg . --zone=asia-south1-c")
    print("  Open it. Read pixel coords for your zone polygon corners.")
    print("  Paste them into config.yaml under cameras.cam106.zones.")


if __name__ == '__main__':
    main()
