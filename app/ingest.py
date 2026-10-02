"""Video ingestion abstraction.

In the hackathon event environment this connects to the VAST AI OS camera
datastream (SOURCE=vast, VAST_DATASTREAM_URL). Locally it falls back to a
video file, a webcam, or the deterministic simulated feed (default).
"""
import os

from .detector import SimulatedDetector, YoloDetector


def open_source():
    """Return (detector, source_name)."""
    src = os.getenv("SOURCE", "simulated").lower()

    if src == "simulated":
        return SimulatedDetector(), "simulated"

    if os.getenv("DETECTOR", "yolo").lower() != "yolo":
        return SimulatedDetector(), "simulated"

    if src == "file":
        path = os.getenv("VIDEO_PATH")
        if not path:
            raise RuntimeError("SOURCE=file requires VIDEO_PATH to be set")
        return YoloDetector(video_path=path), "yolo/file"

    if src == "webcam":
        return YoloDetector(webcam_index=int(os.getenv("WEBCAM", "0"))), "yolo/webcam"

    if src == "vast":
        url = os.getenv("VAST_DATASTREAM_URL")
        if not url:
            raise RuntimeError("SOURCE=vast requires VAST_DATASTREAM_URL")
        # VAST AI OS exposes camera streams; the detector consumes it as a URL.
        return YoloDetector(video_path=url), "yolo/vast"

    raise RuntimeError(f"unknown SOURCE={src!r} (want simulated|file|webcam|vast)")
