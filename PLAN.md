# ShoreGuard — afternoon build plan (Oct 2, submission 4:30 PM PT)

Four improvements, in build order. Each one must keep the demo deterministic
and keep working with no sponsor credentials.

## A. False-positive demo — Cosmos rejects a cannonball

Goal: show *why* verification exists. A kid cannonballs in, the agent flags
the water entry, Cosmos rejects it, and nothing goes off. Minutes later the
real fall is confirmed and the full alarm fires.

- `app/scenario.py`: a second "decoy" figure on cameras with `decoy: True`
  (family backyard pool, aquatic-center kids pool). Walks to the edge, jumps
  in at ~T+6s, swims horizontally, climbs out at ~T+16s.
- `app/main.py`: verification becomes deferred. On `FALL_DETECTED` the event
  waits ~2.5s in a pending queue (stepper shows **VERIFYING**), then goes to
  Cosmos with the frame and the track's recent posture and motion.
- `app/verify.py`: simulated verdict reads that motion summary. Horizontal
  swimming, quick surfacing → `rejected`. Vertical or no progress →
  `confirmed`. A real `COSMOS_ENDPOINT` gets the same evidence in the request.
- Rejected events are logged and shown in the timeline as **✗ REJECTED — no
  alert**; no siren, towers stay green.
- Real fall now alerts at ~T+25.5s instead of ~T+23s. Update `DEMO-SCRIPT.md`.

## B. Audible siren + spoken PA

- `frontend/index.html`: **SOUND** toggle in the status bar (off until clicked,
  because browsers block autoplay).
- Web Audio two-tone wail while the viewed site's siren is on.
- `speechSynthesis` reads the PA message once per new alert and again on
  escalation ("Attention beachgoers…").
- Muting stops both immediately.

## D. Posture heuristic — vertical = distress, horizontal = swimming

From the Drowning-Detector reference: a drowning person is upright with no
forward progress (instinctive drowning response); a swimmer is horizontal.

- `app/agent.py`: per-track box aspect ratio (h / w) over a 3s window. In
  water ≥2s, mostly vertical, net displacement < 40px → `STRUGGLE` with caption
  "Vertical in water, no forward progress". Speed-based struggle stays.
- Events carry `posture` so Cosmos and the UI can use it.
- `app/scenario.py`: victim's struggle box becomes vertical; decoy swims
  horizontally.
- Box labels on video: **SWIMMING** (horizontal), **DISTRESS** (vertical),
  **DROWNING** (motionless).

## E. Phone view for the guard / parent

- New `frontend/guard.html` at `GET /guard?site=family|multipool|beach`.
- Mobile-first: full-screen calm green or flashing red, the incident camera
  thumbnail, alert message, 30s escalation countdown, one huge **ACKNOWLEDGE**
  button. Vibrates and sounds on a new alert.
- `WS /ws?site=` and `POST /api/ack/{id}?site=` so a phone can watch and ack
  one site while the dashboard watches another.
- Incident camera of every site is always encoded so the phone thumbnail
  works whichever tab the dashboard is on.
- Dashboard gets a **GUARD VIEW** link for the current site. The server
  binds `0.0.0.0`, so a phone on the same Wi-Fi uses
  `http://<laptop-ip>:8000/guard?site=beach`.
- Demo beat: ack on the phone → dashboard towers go amber.

## Out of scope today

Running a real hackathon clip through YOLO in its own tab (option C) and
wiring real Cosmos / W&B credentials (option F). Both work through the
existing env vars if there's time at the end.

## Done when

- All three tabs still loop cleanly with no credentials.
- Family and aquatic-center tabs show a rejected cannonball, then a confirmed
  fall.
- Sound toggle works; muting is instant.
- `/guard?site=beach` on a phone can ack and the dashboard reflects it.
- `DEMO-SCRIPT.md` timings match the new incident timeline.
