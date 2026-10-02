"""Video ingestion abstraction.

SOURCE=simulated (default) — deterministic CameraScene per site camera
SOURCE=file|webcam|vast — YOLOv8 on a real stream (ultralytics required)
"""
import os

from .detector import SimulatedDetector, YoloDetector
from .scenario import CameraScene


def open_simulated_cameras(site):
    """Return list of CameraScene, one per camera in the site."""
    return [CameraScene(cam) for cam in site["cameras"]]


def open_source():
    """Return (detector, source_name) for a single real source."""
    src = os.getenv("SOURCE", "simulated").lower()
    if src == "simulated":
        return SimulatedDetector(), "simulated"
    if os.getenv("DETECTOR", "yolo").lower() != "yolo":
        return SimulatedDetector(), "simulated"
    if src == "file":
        path = os.getenv("VIDEO_PATH")
        if not path:
            raise RuntimeError("SOURCE=file requires VIDEO_PATH")
        return YoloDetector(video_path=path), "yolo/file"
    if src == "webcam":
        return YoloDetector(webcam_index=int(os.getenv("WEBCAM", "0"))), "yolo/webcam"
    if src == "vast":
        url = os.getenv("VAST_DATASTREAM_URL")
        if not url:
            raise RuntimeError("SOURCE=vast requires VAST_DATASTREAM_URL")
        return YoloDetector(video_path=url), "yolo/vast"
    raise RuntimeError(f"unknown SOURCE={src!r}")
