"""NVIDIA Cosmos verification — the false-positive killer.

Every FALL_DETECTED / POSSIBLE_DROWNING event is sent to Cosmos for
video-understanding verification before the alert goes out at full volume.

Set COSMOS_ENDPOINT. We POST event metadata + a JPEG frame. Without it, a
deterministic simulated verdict is returned and labeled cosmos-simulated.
"""
import base64
import json
import os
import urllib.request

from . import tools

RATIONALES = {
    "FALL_DETECTED": "person crossed the water edge and entered; no re-emergence",
    "STRUGGLE": "erratic body motion consistent with distress, not lap swimming",
    "POSSIBLE_DROWNING": "body motionless below the surface; consistent with submersion",
}


class CosmosVerifier:
    def __init__(self):
        self.endpoint = os.getenv("COSMOS_ENDPOINT")

    def verify_clip(self, event, jpeg_bytes=None):
        verdict = {
            "by": "cosmos-simulated",
            "result": "confirmed",
            "confidence": 0.94 if event["type"] != "STRUGGLE" else 0.89,
            "rationale": RATIONALES.get(
                event["type"], "anomaly consistent with a water-entry incident"),
        }
        if not self.endpoint:
            return verdict
        payload = {
            "event": {k: event[k] for k in event if k != "verified"},
            "clip_window_s": [-5, 10],
            "prompt": (
                "Is this a fall into water or a possible drowning, "
                "or a benign splash/cannonball? Return JSON "
                "{result: confirmed|rejected, confidence, rationale}."
            ),
        }
        if jpeg_bytes:
            payload["frame_jpeg_b64"] = base64.b64encode(jpeg_bytes).decode()
        try:
            req = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                body = json.loads(r.read().decode())
            verdict = {
                "by": "cosmos",
                "result": body.get("result", "confirmed"),
                "confidence": float(body.get("confidence", 0.9)),
                "rationale": body.get("rationale", verdict["rationale"]),
            }
            tools._set("cosmos", "live", "verified last incident")
        except Exception as e:
            verdict["note"] = f"Cosmos unreachable ({e}); used simulated verdict"
            tools._set("cosmos", "ready", f"POST failed ({e.__class__.__name__})")
        return verdict
