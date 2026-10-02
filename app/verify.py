"""NVIDIA Cosmos verification — the false-positive killer.

Every FALL_DETECTED / POSSIBLE_DROWNING event is sent to Cosmos for
video-understanding verification before the alert goes out at full volume:
a kid doing a cannonball should not trigger a beach-wide siren.

Set COSMOS_ENDPOINT to a real Cosmos video-understanding endpoint and
verify_clip() will POST the clip window there. Without it, a deterministic
simulated verdict is returned so the demo runs anywhere.
"""
import json
import os
import urllib.request

RATIONALES = {
    "FALL_DETECTED": "person crossed the pool edge and entered the water; "
                     "no re-emergence above deck",
    "STRUGGLE": "erratic body motion consistent with distress, not lap swimming",
    "POSSIBLE_DROWNING": "body motionless below the surface; consistent with submersion",
}


class CosmosVerifier:
    def __init__(self):
        self.endpoint = os.getenv("COSMOS_ENDPOINT")

    def verify_clip(self, event):
        verdict = {
            "by": "cosmos-simulated",
            "result": "confirmed",
            "confidence": 0.94 if event["type"] != "STRUGGLE" else 0.89,
            "rationale": RATIONALES.get(event["type"],
                                        "anomaly consistent with a water-entry incident"),
        }
        if self.endpoint:
            try:
                req = urllib.request.Request(
                    self.endpoint,
                    data=json.dumps(
                        {"event": event, "clip_window_s": [-5, 10]}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    body = json.loads(r.read().decode())
                verdict = {
                    "by": "cosmos",
                    "result": body.get("result", "confirmed"),
                    "confidence": float(body.get("confidence", 0.9)),
                    "rationale": body.get("rationale", verdict["rationale"]),
                }
            except Exception as e:  # never let verification take down the pipeline
                verdict["note"] = f"Cosmos unreachable ({e}); used simulated verdict"
        return verdict
