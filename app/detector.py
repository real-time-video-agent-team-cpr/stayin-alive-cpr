"""Detector interface.

SimulatedDetector wraps a CameraScene. YoloDetector runs YOLOv8 on a real
file / webcam / VAST URL. tools.refine_with_yolo can also overlay YOLO on
simulated frames when ultralytics is installed.
"""
from .scenario import CameraScene, Scenario


class BaseDetector:
    def next(self):
        raise NotImplementedError

    def clock(self):
        raise NotImplementedError


class SimulatedDetector(BaseDetector):
    def __init__(self, spec=None):
        self.sc = CameraScene(spec) if spec else Scenario()

    def next(self):
        return self.sc.next()

    def clock(self):
        return self.sc.t


class YoloDetector(BaseDetector):
    def __init__(self, video_path=None, webcam_index=None, pool_rect=None):
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise RuntimeError(
                "ultralytics is not installed — run `pip install ultralytics` "
                "or use SOURCE=simulated"
            ) from e
        import cv2
        import time

        self._cv2 = cv2
        self._time = time
        self.model = YOLO("yolov8n.pt")
        if video_path:
            self.cap = cv2.VideoCapture(video_path)
        else:
            self.cap = cv2.VideoCapture(webcam_index if webcam_index is not None else 0)
        if not self.cap.isOpened():
            raise RuntimeError("could not open video source")
        self.pool = pool_rect or (180, 110, 500, 390)
        self.t0 = time.time()

    def next(self):
        ok, frame = self.cap.read()
        if not ok:
            raise StopIteration("video source ended")
        res = self.model.track(frame, persist=True, classes=[0], verbose=False)[0]
        dets = []
        if res.boxes is not None:
            for b in res.boxes:
                x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
                tid = int(b.id[0]) if b.id is not None else 0
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                px1, py1, px2, py2 = self.pool
                dets.append({
                    "track_id": tid, "label": "person",
                    "x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1,
                    "cx": cx, "cy": cy,
                    "in_water": px1 < cx < px2 and py1 < cy < py2,
                    "state": "tracked", "conf": float(b.conf[0]),
                })
        return frame, dets, self.clock(), False

    def clock(self):
        return self._time.time() - self.t0
