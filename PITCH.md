# ShoreGuard — pitch

## Problem

Drowning is silent and fast. It doesn't look like the movies — no splashing,
no screaming. The WHO estimates ~236,000 drowning deaths per year, and a
large share happen in supervised pools and beaches: a lifeguard watching six
feeds, a crowded beach, a blind corner. Human attention is the bottleneck,
and cameras without agents are just storage.

## Solution

**ShoreGuard** is a real-time video agent that watches every camera feed
without blinking. When someone falls into the water or may be drowning, it
detects it in seconds, verifies it, and fires a beach-wide response:
lifeguard alert, tower lights, siren, PA broadcast, guard paging — with an
automatic escalation ladder if nobody acknowledges.

## Architecture

```
 camera streams (VAST AI OS)
        │
        ▼
 YOLOv8 person detection + tracking        (real-time, per frame)
        │
        ▼
 Event agent: ENTRY → STRUGGLE → STILLNESS  (motion-history logic)
        │
        ▼
 NVIDIA Cosmos clip verification            (false-positive killer)
        │
        ▼
 W&B LLM: dispatch copy + semantic search   (natural language)
        │
        ▼
 Warning system: towers / siren / PA / paging + 30s escalation
```

The pipeline is one stateless container: FastAPI + WebSocket backend,
single-file dashboard, no GPU required for the demo, GPU-ready for
production on CoreWeave.

## Sponsor tools (4 in the pipeline)

- **VAST Data** — AI OS orchestrates video ingestion; the app consumes the
  VAST camera datastream (`app/ingest.py`).
- **YOLO** — real-time person detection and multi-frame tracking.
- **NVIDIA Cosmos** — verifies every incident clip before full-volume alert.
  This is the false-positive killer and the reason the system is deployable:
  cannonballs, jump-ins, and swim-lesson chaos get filtered; real entries
  get confirmed with a rationale.
- **Weights & Biases** — hosted LLMs draft the lifeguard dispatch copy and
  power natural-language search over the footage ("when did the swimmer go
  under?").
- **CoreWeave** — serving target for the GPU-backed production deployment.

## Why it wins

1. **Real-time and agentic**, not a dashboard with a model bolted on: detect
   → reason → verify → act → escalate, in a loop, with no human in the path
   until the alert.
2. **Production-minded**: Cosmos verification kills false positives, the
   escalation ladder handles the unresponsive-guard case, every integration
   degrades gracefully.
3. **Human impact**: seconds matter in drowning; this buys them.
4. **Demo-proof**: deterministic simulated feed, one-command run, honest
   labeling of what's simulated vs. real.

## Future work

Beach-wide camera mesh with multi-camera re-identification, drone feeds for
surf zones, direct hooks for siren/light controllers and SMS paging,
per-zone risk models (crowd density, surf conditions), and incident review
tooling for lifeguard training.
