"""ShoreGuard backend: FastAPI + WebSocket, multi-site simulated-first pipeline."""
import asyncio
import base64
import os
import threading
import time
from pathlib import Path

import cv2
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import agent as agent_mod
from . import alerts as alerts_mod
from . import envload
from . import llm as llm_mod
from . import tools
from . import vast_journal
from . import verify as verify_mod
from .scenario import CameraScene
from .sites import get_site, list_sites

envload.load_dotenv()

FPS = 10
ROOT = Path(__file__).resolve().parent.parent
YOLO_ON_SIM = os.getenv("YOLO_ON_SIM", "0") == "1"


class Cam:
    def __init__(self, spec, site):
        self.spec = spec
        self.scene = CameraScene(spec)
        self.agent = agent_mod.Agent(
            pool=tuple(spec["water"]),
            camera=spec["id"],
            entry_phrase=site["entry_phrase"],
            water_noun=site["water_noun"],
        )
        self.frame = None
        self.jpeg = ""
        self.dets = []
        self.detector_name = "gt"

    def reset(self):
        self.scene.t = 0.0
        self.agent.reset()


class Pipeline:
    def __init__(self, site_id=None):
        self.lock = threading.Lock()
        self.running = True
        self.tick_i = 0
        self.verifier = verify_mod.CosmosVerifier()
        self.composer = llm_mod.AlertComposer()
        self.latest = {"t": 0.0, "cameras": [], "events": [], "site": {}, "tools": {}}
        self.encode = True
        self._configure(site_id or os.getenv("SITE", "family"))

    def configure(self, site_id):
        self._configure(site_id)

    def _configure(self, site_id):
        site = get_site(site_id)
        self.site = site
        self.cams = [Cam(spec, site) for spec in site["cameras"]]
        self.warn = alerts_mod.WarningSystem(
            towers=site["towers"],
            escalate_to=site["escalate_to"],
            ack_by=site["ack_by"],
        )
        self.source_name = os.getenv("SOURCE", "simulated")

    def all_events(self):
        evs = []
        for cam in self.cams:
            evs.extend(cam.agent.events)
        evs.sort(key=lambda e: e["t"])
        return evs

    def handle_event(self, ev, cam):
        jpeg = None
        if cam.frame is not None:
            ok, buf = cv2.imencode(".jpg", cam.frame, [int(cv2.IMWRITE_JPEG_QUALITY), 55])
            if ok:
                jpeg = buf.tobytes()
        if ev["type"] == "FALL_DETECTED":
            ev["verified"] = self.verifier.verify_clip(ev, jpeg)
            where = cam.spec["name"]
            msg = self.composer.compose(ev, where)
            self.warn.raise_alert(ev, msg)
            vast_journal.log_event(self.site["id"], cam.spec["id"], ev,
                                   base64.b64encode(jpeg).decode() if jpeg else None)
        elif ev["type"] == "STRUGGLE":
            print(f"[pipeline] update: {ev['caption']}", flush=True)
            act = self.warn.active()
            if act:
                act[-1]["message"] += " | " + ev["caption"]
        elif ev["type"] == "POSSIBLE_DROWNING":
            ev["verified"] = self.verifier.verify_clip(ev, jpeg)
            act = self.warn.active()
            if act:
                self.warn.raise_severity(act[-1]["id"], "CRITICAL")
                act[-1]["message"] += " | " + ev["caption"]
            else:
                msg = self.composer.compose(ev, cam.spec["name"])
                self.warn.raise_alert(ev, msg)
            vast_journal.log_event(self.site["id"], cam.spec["id"], ev)

    def _encode(self, frame, quality=70):
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        return base64.b64encode(buf.tobytes()).decode() if ok else ""

    def tick(self):
        self.tick_i += 1
        cam_payload = []
        t = 0.0
        for cam in self.cams:
            frame, dets, t, looped = cam.scene.next()
            if looped:
                cam.agent.reset()
                if cam.spec["incident"]:
                    self.warn = alerts_mod.WarningSystem(
                        towers=self.site["towers"],
                        escalate_to=self.site["escalate_to"],
                        ack_by=self.site["ack_by"],
                    )
            if YOLO_ON_SIM and cam.spec["incident"] and self.tick_i % 5 == 0:
                dets, name = tools.refine_with_yolo(frame, dets, cam.spec["water"])
                cam.detector_name = name
            for d in dets:
                x, y, w, h = int(d["x"]), int(d["y"]), int(d["w"]), int(d["h"])
                col = (0, 0, 255) if d["in_water"] else (0, 255, 0)
                cv2.rectangle(frame, (x, y), (x + w, y + h), col, 2)
                tag = "DROWNING" if d.get("state") in ("still", "sinking") else d["label"]
                cv2.putText(frame, f"{tag} {d['conf']:.2f}", (x, max(12, y - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
            cam.frame = frame
            cam.dets = dets
            jpeg = ""
            if self.encode:
                q = 72 if cam.spec["incident"] else 48
                jpeg = self._encode(frame, q)
                cam.jpeg = jpeg
            for ev in cam.agent.update(t, dets):
                self.handle_event(ev, cam)
            cam_payload.append({
                "id": cam.spec["id"],
                "name": cam.spec["name"],
                "incident": cam.spec["incident"],
                "frame": jpeg,
                "detections": len(dets),
                "detector": cam.detector_name,
            })
        self.warn.check_escalation()
        with self.lock:
            self.latest = {
                "t": t,
                "cameras": cam_payload,
                "events": self.all_events()[-12:],
                "site": {
                    "id": self.site["id"],
                    "label": self.site["label"],
                    "warn_title": self.site["warn_title"],
                    "pa_title": self.site["pa_title"],
                    "pa_prefix": self.site["pa_prefix"],
                    "pa_standby": self.site["pa_standby"],
                    "escalate_to": self.site["escalate_to"],
                    "cameras": len(self.cams),
                },
                "tools": tools.snapshot(),
                "source": self.source_name,
            }

    def run(self):
        while self.running:
            t0 = time.time()
            try:
                self.tick()
            except StopIteration:
                break
            except Exception as e:
                print(f"[pipeline] tick error: {e}", flush=True)
            dt = 1.0 / FPS - (time.time() - t0)
            if dt > 0:
                time.sleep(dt)


PHASE = {"family": 0.0, "multipool": 20.0, "beach": 40.0}


class Hub:
    """All three sites keep running; tabs only change which one you watch."""

    def __init__(self):
        self.sites = {}
        for sid in ("family", "multipool", "beach"):
            p = Pipeline(sid)
            off = PHASE.get(sid, 0.0)
            for cam in p.cams:
                cam.scene.t = off
            self.sites[sid] = p
        self.current = os.getenv("SITE", "family")
        if self.current not in self.sites:
            self.current = "family"
        self.running = True

    def view(self):
        return self.sites[self.current]

    def tabs(self):
        out = []
        for sid, p in self.sites.items():
            unacked = p.warn.active()
            out.append({
                "id": sid,
                "label": p.site["label"],
                "cameras": len(p.cams),
                "incident": len(unacked) > 0,
                "severity": unacked[-1]["severity"] if unacked else None,
                "t": p.latest.get("t", 0.0),
            })
        return out

    def run(self):
        while self.running:
            t0 = time.time()
            for sid, p in self.sites.items():
                p.encode = (sid == self.current)
                try:
                    p.tick()
                except Exception as e:
                    print(f"[hub {sid}] tick error: {e}", flush=True)
            dt = 1.0 / FPS - (time.time() - t0)
            if dt > 0:
                time.sleep(dt)


hub = Hub()
app = FastAPI(title="ShoreGuard")


class SiteIn(BaseModel):
    id: str


@app.on_event("startup")
def _startup():
    threading.Thread(target=tools.probe_all, daemon=True).start()
    threading.Thread(target=hub.run, daemon=True).start()


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")


@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            p = hub.view()
            with p.lock:
                snap = dict(p.latest)
            snap["warning"] = p.warn.to_dict()
            snap["tabs"] = hub.tabs()
            snap["view"] = hub.current
            await ws.send_json(snap)
            await asyncio.sleep(0.1)
    except Exception:
        pass


@app.get("/api/state")
def state():
    p = hub.view()
    with p.lock:
        latest = dict(p.latest)
    return {"warning": p.warn.to_dict(),
            "events": p.all_events()[-20:],
            "source": p.source_name,
            "site": latest.get("site"),
            "tools": tools.snapshot(),
            "tabs": hub.tabs(),
            "view": hub.current}


@app.get("/api/sites")
def sites():
    return {"sites": list_sites(), "current": hub.current, "tabs": hub.tabs()}


@app.post("/api/site")
def set_site(body: SiteIn):
    if body.id not in hub.sites:
        return {"ok": False, "error": "unknown site"}
    hub.current = body.id
    return {"ok": True, "site": hub.current}


@app.get("/api/tools")
def tool_status():
    return tools.snapshot()


@app.get("/api/events")
def events():
    return {"events": hub.view().all_events()}


@app.post("/api/ack/{alert_id}")
def ack(alert_id: int):
    a = hub.view().warn.ack(alert_id)
    return {"ok": a is not None, "alert": a}


@app.post("/api/siren")
def siren():
    p = hub.view()
    p.warn.siren = not p.warn.siren
    return {"siren": p.warn.siren}


@app.get("/api/search")
def search(q: str = ""):
    p = hub.view()
    evs = p.all_events()
    hits = llm_mod.semantic_search(q, evs)
    return {"query": q, "results": hits, "answer": p.composer.answer(q, evs)}
