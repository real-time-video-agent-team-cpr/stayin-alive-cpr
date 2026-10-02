# ShoreGuard — a real-time video agent that never blinks

Drowning is silent and fast. Lifeguards are excellent but human: they can't
stare at every camera feed without blinking. **ShoreGuard** watches pool and
beach cameras 24/7, detects when someone falls into the water or may be
drowning, and in seconds alerts the lifeguard **and** fires a beach-wide
warning system — tower lights, siren, PA broadcast, guard paging — with an
escalation ladder if nobody acknowledges.

Built for the **Real-Time Video Agents Hack** (VAST Builders Challenge, SF —
Oct 2, 2026).

## Quickstart

```bash
git clone <your-fresh-repo-url> shoreguard && cd shoreguard
./scripts/run_demo.sh
# open http://localhost:8000
```

What you'll see: a lifeguard dashboard on a **deterministic simulated feed**
(labeled on screen). All clear until ~T+23s, when a figure falls into the
pool → detection → Cosmos verification → alert → tower lights red, siren on,
PA armed. ~T+26s struggle is flagged. ~T+47s the motionless-body alarm fires
at CRITICAL. Hit ACKNOWLEDGE, or wait 30s to watch the escalation ladder
fire to all towers. Then ask the footage: *"when did the swimmer go under?"*

Manual run instead of the script:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional; all integrations work unconfigured
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Demo mode (read this before the demo)

The default `SOURCE=simulated` plays a **synthetic top-down pool scene**
(`app/scenario.py`) with scripted person bounding boxes. It is honest about
it: the UI badge, the video watermark, and these docs all say SIMULATED.
Why: the venue Wi-Fi, camera access, and sponsor credentials are unknowns —
the 3-minute demo must be bit-for-bit deterministic. The **real** path is
fully wired: set `SOURCE=file` + `VIDEO_PATH=...` (or `webcam`, or `vast`)
and `DETECTOR=yolo` (`pip install ultralytics`) to run YOLOv8 person
detection + tracking on real footage through the same agent, verifier, and
warning system. Judges: the architecture is the product; the simulation is
the demo harness.

## Sponsor-tool mapping

| Sponsor | Where it lives | Without credentials |
|---|---|---|
| **VAST Data** (AI OS ingestion) | `app/ingest.py` — `SOURCE=vast` consumes the VAST camera datastream (`VAST_DATASTREAM_URL`) | simulated/file/webcam sources |
| **NVIDIA Cosmos** (video understanding) | `app/verify.py` — every incident is verified before full-volume alert (`COSMOS_ENDPOINT`) | deterministic simulated verdict, labeled `cosmos-simulated` |
| **YOLO** (real-time detection) | `app/detector.py` — `YoloDetector`, person detect + track | `SimulatedDetector` emits the same schema |
| **Weights & Biases** (LLMs) | `app/llm.py` — `AlertComposer` drafts dispatch copy; `semantic_search()` answers footage questions (`WANDB_INFERENCE_URL`/`WANDB_API_KEY`/`WANDB_MODEL`) | template copy + keyword/synonym search over the event index (embeddings in production) |
| **CoreWeave** | serving target — the whole stack is a single stateless container, GPU-optional (YOLO runs on CoreWeave GPUs in production) | runs on CPU laptop |
| **Cursor / SpaceXAI** | the build toolchain | — |

That's **4 sponsor tools** in the pipeline (VAST, Cosmos, YOLO, W&B), 5 counting
the serving story.

## API

- `GET /` — dashboard
- `WS /ws` — 10 fps frame + state stream
- `GET /api/state`, `GET /api/events`
- `POST /api/ack/{alert_id}` — acknowledge (towers → amber, siren off)
- `POST /api/siren` — toggle siren
- `GET /api/search?q=...` — natural-language moment retrieval

## TEAM-SETUP (4 people, ~5 hours)

1. **Clone + run (everyone, first 15 min):** `git clone`, `./scripts/run_demo.sh`,
   open `http://localhost:8000`, watch one full 75s loop. Read `DEMO-SCRIPT.md`.
2. **Pipeline (1 person):** `app/detector.py`, `app/agent.py`, `app/scenario.py`.
   Tune thresholds, or swap in real footage (`SOURCE=file VIDEO_PATH=...`).
3. **Dashboard (1 person):** `frontend/index.html` — single file, no build.
   Polish layout, add a second camera tile, bigger alert typography.
4. **Integrations (1 person):** at the venue, plug real credentials into `.env`:
   VAST stream URL, `COSMOS_ENDPOINT`, W&B inference key. Each is a 5-line
   change; every one degrades gracefully if it fails.
5. **Demo captain (1 person):** owns `DEMO-SCRIPT.md`, records the 3-min demo
   by **4:15 PM**, handles GitHub submission by the **4:30 PM** hard cutoff.

## Hackathon rules checklist

- [x] Brand-new project — this repo is fresh, no prior code
- [x] ≥3 sponsor tools (4 in-pipeline)
- [x] 3-minute recorded demo (`DEMO-SCRIPT.md`)
- [x] GitHub repo submitted by 4:30 PM PT
- [x] Max team size 4

## What's stubbed vs. real

Real: scenario renderer, detector interface, YOLO path, tracking + event
logic, escalation ladder, dashboard, search. Stubbed (clearly marked):
Cosmos verdict, W&B LLM copy, VAST stream URL, guard webhook, physical
sirens/lights. Nothing stubbed pretends to be real.
