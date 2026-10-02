"""Event logic: ENTRY / STRUGGLE / STILLNESS -> FALL_DETECTED / POSSIBLE_DROWNING.

Consumes tracked person detections, keeps per-track motion history, and emits
deduplicated events with confidence scores. Pure Python, no ML here — the ML
lives in the detector (YOLO) and the verifier (Cosmos).
"""
from collections import defaultdict, deque

STRUGGLE_SPEED = 60.0   # px/s mean speed over 3s window -> struggle
STILL_SPEED = 4.0       # px/s mean speed over 8s window -> motionless
STRUGGLE_WIN = 3.0
STILL_WIN = 8.0
COOLDOWN = 90.0         # don't re-fire same (type, track) within 90s
EDGE_BAND = 45.0        # px from pool border counts as "at the edge"


class Agent:
    def __init__(self, pool=(180, 110, 500, 390)):
        self.pool = pool
        self.hist = defaultdict(deque)   # tid -> deque of (t, cx, cy)
        self.in_water = {}               # tid -> bool
        self.entered_at = {}             # tid -> t of water entry
        self.last_fired = {}             # (etype, tid) -> t
        self.events = []
        self._eid = 0

    def reset(self):
        self.hist.clear()
        self.in_water.clear()
        self.entered_at.clear()
        self.last_fired.clear()
        self.events.clear()

    def _near_edge(self, cx, cy):
        x1, y1, x2, y2 = self.pool
        return min(abs(cx - x1), abs(cx - x2), abs(cy - y1), abs(cy - y2)) < EDGE_BAND

    def _window_speed(self, h, t, win):
        pts = [(tt, x, y) for tt, x, y in h if t - win <= tt <= t]
        if len(pts) < 3:
            return None
        dist = sum(
            ((pts[i + 1][1] - pts[i][1]) ** 2 + (pts[i + 1][2] - pts[i][2]) ** 2) ** 0.5
            for i in range(len(pts) - 1)
        )
        dt = pts[-1][0] - pts[0][0]
        return dist / dt if dt > 0 else 0.0

    def _fire(self, t, tid, etype, conf, caption, severity):
        key = (etype, tid)
        if t - self.last_fired.get(key, -1e9) < COOLDOWN:
            return None
        self._eid += 1
        ev = {"id": self._eid, "type": etype, "t": round(t, 1), "track_id": tid,
              "confidence": conf, "caption": caption, "severity": severity,
              "verified": None}
        self.last_fired[key] = t
        self.events.append(ev)
        return ev

    def update(self, t, detections):
        new_events = []
        seen = set()
        for d in detections:
            tid = d["track_id"]
            seen.add(tid)
            h = self.hist[tid]
            h.append((t, d["cx"], d["cy"]))
            while h and t - h[0][0] > STILL_WIN + 2:
                h.popleft()

            prev = self.in_water.get(tid, False)
            now = d["in_water"]

            if now and not prev:
                # --- ENTRY: water crossing ---
                self.entered_at[tid] = t
                spd = self._window_speed(h, t, 1.5) or 0.0
                at_edge = self._near_edge(d["cx"], d["cy"])
                conf = 0.92 if (at_edge or spd > 80) else 0.65
                ev = self._fire(
                    t, tid, "FALL_DETECTED", conf,
                    f"Person entered the water at the pool edge (track {tid})",
                    "HIGH" if conf >= 0.8 else "MEDIUM",
                )
                if ev:
                    new_events.append(ev)

            if now:
                in_water_for = t - self.entered_at.get(tid, t)
                v3 = self._window_speed(h, t, STRUGGLE_WIN)
                if in_water_for >= 2.0 and v3 is not None and v3 > STRUGGLE_SPEED:
                    ev = self._fire(
                        t, tid, "STRUGGLE", 0.85,
                        f"Erratic movement in water — possible struggle (track {tid})",
                        "HIGH",
                    )
                    if ev:
                        new_events.append(ev)
                v8 = self._window_speed(h, t, STILL_WIN)
                if in_water_for >= STILL_WIN and v8 is not None and v8 < STILL_SPEED:
                    ev = self._fire(
                        t, tid, "POSSIBLE_DROWNING", 0.88,
                        f"Person motionless in water for {int(STILL_WIN)}+ seconds "
                        f"(track {tid})",
                        "CRITICAL",
                    )
                    if ev:
                        new_events.append(ev)

            self.in_water[tid] = now

        for tid in list(self.hist):
            if tid not in seen and self.hist[tid] and t - self.hist[tid][-1][0] > 5:
                del self.hist[tid]
                self.in_water.pop(tid, None)
                self.entered_at.pop(tid, None)
        return new_events
