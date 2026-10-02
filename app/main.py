"""ShoreGuard backend: FastAPI + WebSocket, simulated-first pipeline."""
import asyncio
import base64
import threading
import time
from pathlib import Path

import cv2
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse

from . import agent as agent_mod
from . import alerts as alerts_mod
from . import ingest
from . import llm as llm_mod
from . import verify as verify_mod

FPS = 10
ROOT = Path(__file__).resolve().parent.parent


class Pipeline:
    def __init__(self):
        self.detector, self.source_name = ingest.open_source()
        self.agent = agent_mod.Agent()
        self.verifier = verify_mod.CosmosVerifier()
        self.composer = llm_mod.AlertComposer()
        self.warn = alerts_mod.WarningSystem()
        self.lock = threading.Lock()
        self.latest = {"frame": "", "t": 0.0, "detections": 0}
        self.running = True
        self.where = "Pool Deck Camera 1"

    def handle_event(self, ev):
        if ev["type"] == "FALL_DETECTED":
            ev["verified"] = self.verifier.verify_clip(ev)
            msg = self.composer.compose(ev, self.where)
            self.warn.raise_alert(ev, msg)
        elif ev["type"] == "STRUGGLE":
            print(f"[pipeline] update: {ev['caption']}", flush=True)
            act = self.warn.active()
            if act:
                act[-1]["message"] += " | " + ev["caption"]
        elif ev["type"] == "POSSIBLE_DROWNING":
            ev["verified"] = self.verifier.verify_clip(ev)
            act = self.warn.active()
            if act:
                self.warn.raise_severity(act[-1]["id"], "CRITICAL")
                act[-1]["message"] += " | " + ev["caption"]
            else:
                msg = self.composer.compose(ev, self.where)
                self.warn.raise_alert(ev, msg)

    def tick(self):
        frame, dets, t, looped = self.detector.next()
        if looped:  # scenario restarted -> fresh incident state
            self.agent.reset()
            self.warn = alerts_mod.WarningSystem()
        for ev in self.agent.update(t, dets):
            self.handle_event(ev)
        self.warn.check_escalation()
        for d in dets:
            x, y, w, h = int(d["x"]), int(d["y"]), int(d["w"]), int(d["h"])
            col = (0, 0, 255) if d["in_water"] else (0, 255, 0)
            cv2.rectangle(frame, (x, y), (x + w, y + h), col, 2)
            cv2.putText(frame, f"{d['label']} {d['conf']:.2f}", (x, max(12, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        with self.lock:
            self.latest = {"frame": base64.b64encode(buf.tobytes()).decode(),
                           "t": t, "detections": len(dets)}

    def run(self):
        while self.running:
            t0 = time.time()
            try:
                self.tick()
            except StopIteration:
                break
            except Exception as e:  # never let one bad frame kill the demo
                print(f"[pipeline] tick error: {e}", flush=True)
            dt = 1.0 / FPS - (time.time() - t0)
            if dt > 0:
                time.sleep(dt)


pipe = Pipeline()
app = FastAPI(title="ShoreGuard")


@app.on_event("startup")
def _startup():
    threading.Thread(target=pipe.run, daemon=True).start()


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")


@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            with pipe.lock:
                snap = dict(pipe.latest)
            snap["warning"] = pipe.warn.to_dict()
            snap["events"] = pipe.agent.events[-8:]
            await ws.send_json(snap)
            await asyncio.sleep(0.1)
    except Exception:
        pass  # client disconnected


@app.get("/api/state")
def state():
    return {"warning": pipe.warn.to_dict(),
            "events": pipe.agent.events[-20:],
            "source": pipe.source_name}


@app.get("/api/events")
def events():
    return {"events": pipe.agent.events}


@app.post("/api/ack/{alert_id}")
def ack(alert_id: int):
    a = pipe.warn.ack(alert_id)
    return {"ok": a is not None, "alert": a}


@app.post("/api/siren")
def siren(body: dict):
    pipe.warn.siren = bool(body.get("on", not pipe.warn.siren))
    return {"siren": pipe.warn.siren}


@app.get("/api/search")
def search(q: str = ""):
    hits = llm_mod.semantic_search(q, pipe.agent.events)
    return {"query": q, "results": hits,
            "answer": pipe.composer.answer(q, pipe.agent.events)}
