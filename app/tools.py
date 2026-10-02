"""Sponsor-tool probes: YOLO, NVIDIA Cosmos, W&B, VAST.

Each tool is optional. Status is LIVE, READY (configured but unused this
tick), or FALLBACK (simulated). Never crash the demo if a probe fails.
"""
import json
import os
import time
import urllib.request

STATUS = {
    "yolo": {"state": "fallback", "detail": "ultralytics not loaded"},
    "cosmos": {"state": "fallback", "detail": "COSMOS_ENDPOINT unset"},
    "wandb": {"state": "fallback", "detail": "WANDB_API_KEY unset"},
    "vast": {"state": "fallback", "detail": "VAST_DATASTREAM_URL unset; writing local ingest journal"},
}

_yolo_model = None


def _set(name, state, detail):
    STATUS[name] = {"state": state, "detail": detail, "ts": time.time()}


def yolo_model():
    """Lazy-load YOLOv8n if ultralytics is installed. None otherwise."""
    global _yolo_model
    if _yolo_model is not None:
        return _yolo_model if _yolo_model is not False else None
    try:
        from ultralytics import YOLO
        _yolo_model = YOLO("yolov8n.pt")
        _set("yolo", "ready", "YOLOv8n loaded; set YOLO_ON_SIM=1 or a real SOURCE to run it")
        return _yolo_model
    except Exception as e:
        _yolo_model = False
        _set("yolo", "fallback", f"YOLO unavailable ({e.__class__.__name__})")
        return None


def refine_with_yolo(frame, fallback_dets, water_rect):
    """Run YOLO on a frame; fall back to scripted boxes if it fails."""
    model = yolo_model()
    if model is None:
        return fallback_dets, "gt"
    try:
        res = model.track(frame, persist=True, classes=[0], verbose=False)[0]
        dets = []
        x1p, y1p, x2p, y2p = water_rect
        if res.boxes is None:
            return fallback_dets, "gt"
        for b in res.boxes:
            x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
            tid = int(b.id[0]) if b.id is not None else 0
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            dets.append({
                "track_id": tid, "label": "person",
                "x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1,
                "cx": cx, "cy": cy,
                "in_water": x1p < cx < x2p and y1p < cy < y2p,
                "state": "tracked", "conf": float(b.conf[0]),
            })
        if not dets:
            return fallback_dets, "gt"
        _set("yolo", "live", f"{len(dets)} person track(s)")
        return dets, "yolo"
    except Exception as e:
        _set("yolo", "fallback", f"YOLO tick failed ({e.__class__.__name__})")
        return fallback_dets, "gt"


def probe_cosmos():
    url = os.getenv("COSMOS_ENDPOINT")
    if not url:
        _set("cosmos", "fallback", "COSMOS_ENDPOINT unset — simulated verdict")
        return
    try:
        req = urllib.request.Request(url, method="GET")
        urllib.request.urlopen(req, timeout=3)
        _set("cosmos", "live", url)
    except Exception as e:
        _set("cosmos", "ready", f"endpoint set, probe failed ({e.__class__.__name__})")


def probe_wandb():
    url = os.getenv("WANDB_INFERENCE_URL")
    key = os.getenv("WANDB_API_KEY")
    model = os.getenv("WANDB_MODEL", "llama-3.1-8b-instruct")
    if key and not url:
        url = "https://api.inference.wandb.ai/v1/chat/completions"
        os.environ["WANDB_INFERENCE_URL"] = url
    if not key:
        _set("wandb", "fallback", "WANDB_API_KEY unset — template copy + keyword search")
        return
    _set("wandb", "live" if url else "ready", f"model={model}")


def probe_vast():
    url = os.getenv("VAST_DATASTREAM_URL")
    if not url:
        _set("vast", "fallback", "local ingest journal (no VAST_DATASTREAM_URL)")
        return
    try:
        urllib.request.urlopen(url, timeout=3)
        _set("vast", "live", url)
    except Exception as e:
        _set("vast", "ready", f"URL set, stream probe failed ({e.__class__.__name__})")


def snapshot():
    return {k: dict(v) for k, v in STATUS.items()}


def probe_all():
    yolo_model()
    probe_cosmos()
    probe_wandb()
    probe_vast()
    return snapshot()
