"""Synthetic cameras for the three ShoreGuard sites.

SIMULATED — not real footage. Each camera is a deterministic scene so the
demo incident fires at the same timestamps every loop (75s).
"""
import math

import cv2
import numpy as np

W, H, FPS = 640, 480, 10
DURATION = 75.0


def _lerp(a, b, k):
    return a + (b - a) * k


def _clip(v, lo, hi):
    return max(lo, min(hi, v))


class CameraScene:
    def __init__(self, spec):
        self.spec = spec
        self.kind = spec["kind"]
        self.theme = spec["theme"]
        self.incident = spec["incident"]
        self.water = tuple(spec["water"])
        self.name = spec["name"]
        self.t = 0.0

    def in_water(self, cx, cy):
        x1, y1, x2, y2 = self.water
        return x1 < cx < x2 and y1 < cy < y2

    def figure(self, t):
        if self.incident:
            return self._incident_figure(t)
        return self._safe_figure(t)

    def _incident_figure(self, t):
        x1, y1, x2, y2 = self.water
        deck_x, deck_y = _clip(x1 - 70, 40, W - 40), _clip(y2 + 20, 40, H - 30)
        edge_x, edge_y = x1 + 8, (y1 + y2) / 2
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        still_x, still_y = mid_x, _clip(y2 - 50, y1 + 20, y2 - 20)

        if self.kind == "beach":
            deck_x, deck_y = 120, 160
            edge_x, edge_y = 220, 220
            mid_x, mid_y = 340, 320
            still_x, still_y = 360, 400

        if t < 16:
            cx = deck_x + 40 * math.sin(t * 0.55)
            return cx, deck_y, 30, 58, "deck"
        if t < 22:
            k = (t - 16) / 6
            return (_lerp(deck_x, edge_x - 20, k),
                    _lerp(deck_y, edge_y, k), 30, 58, "edge")
        if t < 24:
            k = (t - 22) / 2
            return (_lerp(edge_x - 20, edge_x + 12, k), edge_y,
                    _lerp(30, 42, k), _lerp(58, 48, k), "stumble")
        if t < 25:
            k = t - 24
            return (_lerp(edge_x + 12, mid_x - 40, k),
                    _lerp(edge_y, mid_y - 20, k),
                    _lerp(42, 58, k), _lerp(48, 36, k), "falling")
        if t < 33:
            cx = mid_x - 30 + 38 * math.sin(t * 7.0) + 14 * math.sin(t * 13.7)
            cy = mid_y - 20 + 22 * math.sin(t * 9.1 + 1.0)
            return cx, cy, 56 + 8 * math.sin(t * 11.0), 34 + 6 * math.sin(t * 9.0), "struggle"
        if t < 40:
            k = (t - 33) / 7
            amp = 1 - k
            return (still_x + 24 * amp * math.sin(t * 7.0),
                    _lerp(mid_y, still_y, k), 48, 30, "sinking")
        return still_x, still_y, 44, 26, "still"

    def _safe_figure(self, t):
        x1, y1, x2, y2 = self.water
        if self.kind == "patio":
            cx = 180 + 160 * math.sin(t * 0.35)
            return cx, 300, 28, 54, "deck"
        if self.kind == "beach":
            cx = 80 + ((t * 18) % 480)
            cy = 140 + 18 * math.sin(t * 0.8)
            return cx, cy, 26, 50, "deck"
        # walk the deck around a pool, never crossing in
        cx = x1 - 40 + 30 * math.sin(t * 0.4)
        cy = y2 + 25 + 10 * math.sin(t * 0.7)
        cx = _clip(cx, 30, W - 30)
        cy = _clip(cy, 30, H - 20)
        if self.in_water(cx, cy):
            cy = y2 + 28
        return cx, cy, 28, 52, "deck"

    def frame(self, t):
        if self.kind == "beach":
            img = self._paint_beach(t)
        elif self.kind == "patio":
            img = self._paint_patio(t)
        else:
            img = self._paint_pool(t)
        cx, cy, w, h, st = self.figure(t)
        self._draw_person(img, int(cx), int(cy), int(w), int(h), st)
        cv2.putText(img, f"T+{t:05.1f}s", (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, "SIMULATED FEED - DEMO MODE", (W - 305, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        return img

    def _paint_pool(self, t):
        img = np.zeros((H, W, 3), dtype=np.uint8)
        if self.theme == "family":
            img[:] = (60, 140, 70)  # grass BGR
            cv2.rectangle(img, (0, 0), (W, 70), (90, 110, 140), -1)  # fence/house
        elif self.theme == "kids":
            img[:] = (90, 200, 230)
        elif self.theme == "lap":
            img[:] = (150, 170, 180)
        elif self.theme == "dive":
            img[:] = (120, 130, 80)
        elif self.theme == "spa":
            img[:] = (80, 90, 100)
        else:
            img[:] = (140, 180, 210)
        x1, y1, x2, y2 = (int(v) for v in self.water)
        for yy in range(max(0, y1), min(H, y2)):
            k = (yy - y1) / max(1, y2 - y1)
            if self.theme == "spa":
                col = (int(_lerp(180, 140, k)), int(_lerp(160, 90, k)), int(_lerp(40, 20, k)))
            elif self.theme == "kids":
                col = (int(_lerp(220, 140, k)), int(_lerp(180, 90, k)), int(_lerp(60, 20, k)))
            else:
                col = (int(_lerp(200, 120, k)), int(_lerp(130, 70, k)), int(_lerp(40, 15, k)))
            img[yy, max(0, x1):min(W, x2)] = col
        if self.theme == "lap":
            for lx in range(x1 + 40, x2, 70):
                cv2.line(img, (lx, y1 + 6), (lx, y2 - 6), (230, 240, 250), 2)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 220, 220), 3)
        return img

    def _paint_beach(self, t):
        img = np.zeros((H, W, 3), dtype=np.uint8)
        # sky
        for yy in range(0, 160):
            k = yy / 160
            img[yy, :] = (int(_lerp(210, 160, k)), int(_lerp(190, 140, k)), int(_lerp(90, 40, k)))
        x1, y1, x2, y2 = (int(v) for v in self.water)
        img[160:max(240, y1), :] = (140, 190, 220)  # sand runs down to the waterline
        for yy in range(max(0, y1), min(H, y2)):
            k = (yy - y1) / max(1, y2 - y1)
            wave = int(8 * math.sin(t * 2.2 + yy * 0.08))
            img[yy, :] = (
                int(_lerp(180, 90, k)),
                int(_lerp(120, 50, k)),
                int(_lerp(30, 10, k)),
            )
            if 0 <= yy < H:
                img[yy, max(0, min(W - 1, 200 + wave))] = (240, 240, 240)
        if self.theme == "pier":
            cv2.rectangle(img, (280, 80), (360, 400), (40, 60, 80), -1)
            for py in range(100, 400, 28):
                cv2.rectangle(img, (270, py), (370, py + 8), (30, 45, 60), -1)
        if self.theme == "dunes":
            cv2.rectangle(img, (40, 40), (120, 200), (30, 40, 50), -1)  # tower
            cv2.rectangle(img, (55, 20), (105, 40), (20, 30, 40), -1)
        cv2.line(img, (0, y1), (W, y1), (0, 220, 220), 2)
        return img

    def _paint_patio(self, t):
        img = np.zeros((H, W, 3), dtype=np.uint8)
        img[:] = (70, 90, 110)
        cv2.rectangle(img, (80, 40), (560, 220), (40, 55, 80), -1)  # glass door
        cv2.rectangle(img, (100, 60), (260, 200), (180, 210, 220), -1)
        cv2.rectangle(img, (280, 60), (540, 200), (180, 210, 220), -1)
        img[240:, :] = (90, 150, 80)
        cv2.rectangle(img, (0, 220), (W, 250), (50, 70, 90), -1)
        return img

    def _draw_person(self, img, cx, cy, w, h, st):
        in_w = self.in_water(cx, cy)
        body_col = (30, 60, 200) if not in_w else (20, 40, 160)
        cv2.ellipse(img, (cx, cy), (max(4, w // 2), max(4, h // 2)), 0, 0, 360, body_col, -1)
        cv2.circle(img, (cx, cy - h // 2 - 8), 10, (60, 120, 200), -1)
        if in_w:
            for rr in (w, w + 14, w + 28):
                cv2.ellipse(img, (cx, cy), (max(4, rr), max(3, int(rr * 0.6))),
                            0, 0, 360, (255, 255, 255), 1)
            if st in ("sinking", "still"):
                overlay = img.copy()
                cv2.ellipse(overlay, (cx, cy), (w // 2 + 6, h // 2 + 6), 0, 0, 360,
                            (120, 70, 13), -1)
                cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)

    def next(self):
        if self.t >= DURATION:
            self.t = 0.0
            looped = True
        else:
            looped = False
        t = self.t
        frame = self.frame(t)
        cx, cy, w, h, st = self.figure(t)
        dets = [{
            "track_id": 1 if self.incident else 10 + abs(sum(ord(c) for c in self.spec["id"])) % 40,
            "label": "person",
            "x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h,
            "cx": cx, "cy": cy, "in_water": self.in_water(cx, cy),
            "state": st, "conf": 0.97 if self.incident else 0.91,
            "camera": self.spec["id"],
        }]
        self.t += 1.0 / FPS
        return frame, dets, t, looped


# Back-compat for older imports
class Scenario(CameraScene):
    def __init__(self):
        super().__init__({
            "id": "cam-01", "name": "POOL", "kind": "pool",
            "incident": True, "theme": "family",
            "water": (180, 110, 500, 390),
        })
