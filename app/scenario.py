"""Synthetic pool scene for deterministic demo mode.

SIMULATED — this is not real footage. It renders a top-down pool with one
figure on a fixed timeline so the incident (and therefore the whole demo)
fires at the same timestamps on every run:

  0-16s    figure walks the deck (all clear)
  16-22s   figure approaches the pool edge
  22-24s   stumble at the edge
  ~23.2s   crosses into the water  -> FALL_DETECTED (~T+23s)
  24-25s   plunge
  25-33s   struggle                -> STRUGGLE (~T+26s)
  33-40s   sinking
  40s+     motionless below surface -> POSSIBLE_DROWNING (~T+47s)
  75s      loop restarts
"""
import math

import cv2
import numpy as np

W, H, FPS = 640, 480, 10
DURATION = 75.0
POOL = (180, 110, 500, 390)  # x1, y1, x2, y2


def _lerp(a, b, k):
    return a + (b - a) * k


class Scenario:
    def __init__(self):
        self.t = 0.0

    # ---- figure kinematics (ground truth) ----
    def figure(self, t):
        """Return (cx, cy, w, h, state)."""
        if t < 16:
            cx = 90 + 55 * math.sin(t * 0.55)
            cy, w, h, st = 425, 30, 58, "deck"
        elif t < 22:
            k = (t - 16) / 6
            cx = _lerp(90 + 55 * math.sin(16 * 0.55), 168, k)
            cy = _lerp(425, 250, k)
            w, h, st = 30, 58, "edge"
        elif t < 24:
            k = (t - 22) / 2
            cx = _lerp(168, 189, k)
            cy = 250
            w, h, st = _lerp(30, 42, k), _lerp(58, 48, k), "stumble"
        elif t < 25:
            k = t - 24
            cx = _lerp(189, 260, k)
            cy = _lerp(250, 262, k)
            w, h, st = _lerp(42, 58, k), _lerp(48, 36, k), "falling"
        elif t < 33:
            cx = 260 + 38 * math.sin(t * 7.0) + 18 * math.sin(t * 13.7)
            cy = 262 + 26 * math.sin(t * 9.1 + 1.0)
            w, h, st = 56 + 8 * math.sin(t * 11.0), 34 + 6 * math.sin(t * 9.0), "struggle"
        elif t < 40:
            k = (t - 33) / 7
            amp = 1 - k
            cx = 262 + 30 * amp * math.sin(t * 7.0)
            cy = 262 + 75 * k
            w, h, st = 48, 30, "sinking"
        else:
            cx, cy, w, h, st = 268, 340, 44, 26, "still"
        return cx, cy, w, h, st

    def in_water(self, cx, cy):
        x1, y1, x2, y2 = POOL
        return x1 < cx < x2 and y1 < cy < y2

    # ---- rendering ----
    def frame(self, t):
        img = np.zeros((H, W, 3), dtype=np.uint8)
        img[:] = (140, 180, 210)  # deck, BGR tan
        for gx in range(0, W, 80):  # deck tile seams
            cv2.line(img, (gx, 0), (gx, H), (128, 168, 198), 1)
        x1, y1, x2, y2 = POOL
        for yy in range(y1, y2):  # water gradient, shallow -> deep
            k = (yy - y1) / (y2 - y1)
            img[yy, x1:x2] = (
                int(_lerp(200, 120, k)),
                int(_lerp(130, 70, k)),
                int(_lerp(40, 15, k)),
            )
        for lx in (280, 400):  # lane lines
            cv2.line(img, (lx, y1 + 8), (lx, y2 - 8), (230, 240, 250), 2)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 220, 220), 3)  # edge zone

        cx, cy, w, h, st = self.figure(t)
        cx, cy, w, h = int(cx), int(cy), int(w), int(h)
        in_w = self.in_water(cx, cy)
        body_col = (30, 60, 200) if not in_w else (20, 40, 160)
        cv2.ellipse(img, (cx, cy), (w // 2, h // 2), 0, 0, 360, body_col, -1)
        cv2.circle(img, (cx, cy - h // 2 - 8), 10, (60, 120, 200), -1)  # head
        if in_w:
            for rr in (w, w + 14, w + 28):  # ripples
                cv2.ellipse(img, (cx, cy), (rr, int(rr * 0.6)), 0, 0, 360,
                            (255, 255, 255), 1)
            if st in ("sinking", "still"):  # depth shading
                overlay = img.copy()
                cv2.ellipse(overlay, (cx, cy), (w // 2 + 6, h // 2 + 6), 0, 0, 360,
                            (120, 70, 13), -1)
                cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)

        cv2.putText(img, f"T+{t:05.1f}s", (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, "SIMULATED FEED - DEMO MODE", (W - 305, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        return img

    def next(self):
        """Advance one frame. Returns (frame, detections, t, looped).

        The loop flag is attached to the first frame of the new loop
        (t=0.0), so consumers reset incident state before processing it —
        never on the last frame of the old loop.
        """
        if self.t >= DURATION:
            self.t = 0.0
            looped = True
        else:
            looped = False
        t = self.t
        frame = self.frame(t)
        cx, cy, w, h, st = self.figure(t)
        dets = [{
            "track_id": 1, "label": "person",
            "x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h,
            "cx": cx, "cy": cy, "in_water": self.in_water(cx, cy),
            "state": st, "conf": 0.97,
        }]
        self.t += 1.0 / FPS
        return frame, dets, t, looped
