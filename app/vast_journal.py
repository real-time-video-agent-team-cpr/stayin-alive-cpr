"""VAST-shaped local ingest journal.

When VAST_DATASTREAM_URL is unset we still write each incident to
data/ingest/events.jsonl so the data-layer story is real and inspectable.
If the URL is set, ingest.open_source() consumes it as a camera stream.
"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "data" / "ingest" / "events.jsonl"


def log_event(site_id, camera_id, event, jpeg_b64=None):
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": time.time(),
        "site": site_id,
        "camera": camera_id,
        "event_id": event.get("id"),
        "type": event.get("type"),
        "t": event.get("t"),
        "severity": event.get("severity"),
        "caption": event.get("caption"),
        "verified": event.get("verified"),
        "frame_jpeg_b64": (jpeg_b64 or "")[:80] + "…" if jpeg_b64 else None,
    }
    with JOURNAL.open("a") as f:
        f.write(json.dumps(rec) + "\n")
