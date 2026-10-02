# ShoreGuard — 3-minute demo script

Record by **4:15 PM**. One continuous screen recording, dashboard full-screen.
The simulated feed loops every 75s and the incident fires at the same
timestamps every run, so rehearse once, then record. Total: ~3:00.

## Setup (before you hit record)

- `./scripts/run_demo.sh`, open `http://localhost:8000`, full-screen the browser.
- Restart the loop right before recording (reload the page = T+0s).
- Have the search query typed but not submitted: `when did the swimmer go under?`

## 0:00–0:20 — The hook

> "Drowning is silent. It doesn't look like the movies — no splashing, no
> screaming. A person can slip under in under a minute, and a lifeguard
> watching six camera feeds will miss it. ShoreGuard is a real-time video
> agent that never blinks."

## 0:20–0:45 — The dashboard, all clear

Show the dashboard. Point at: live feed with the green person box, tower
lights green, event timeline saying "all clear". Note the badge:

> "We're running the deterministic demo feed so this is reproducible — the
> same pipeline runs YOLO on real camera streams; the venue details are in
> the README."

## 0:45–1:30 — The incident

Let the clock run. At ~T+23s the figure falls in:

> "There — the agent caught the water entry. Watch the timeline: YOLO
> tracked the person, the agent fired FALL_DETECTED, and before anyone gets
> paged, NVIDIA Cosmos verified the clip — confirmed, person in the water,
> no re-emergence. That's our false-positive killer: a cannonball doesn't
> trigger a beach-wide siren."

Point at: red box, alert banner, tower lights RED, siren ON, PA message,
guard page in the server log.

## 1:30–2:00 — Acknowledge + escalation story

Click ACKNOWLEDGE:

> "Guard acknowledges — towers go amber, siren off. But if nobody acks
> within 30 seconds — say the guard is mid-rescue — it escalates to ALL
> towers automatically."

(If the stillness alarm at ~T+47s fires during your take, even better:
"And now it's gone critical — motionless for 8 seconds, possible drowning.")

## 2:00–2:30 — Ask the footage

Submit the search:

> "After the rescue, the supervisor asks: *when did the swimmer go under?*
> Natural language, straight to the timestamped moment. In production this
> is embedding search over hours of footage."

## 2:30–3:00 — Architecture + close

> "The stack: VAST AI OS ingests the camera streams, YOLO detects and
> tracks in real time, Cosmos verifies every incident so we don't cry wolf,
> and a W&B-hosted LLM writes the dispatch copy and answers questions —
> served on CoreWeave. Four sponsor tools, one container, CPU-friendly.
> Next: beach-wide camera mesh, multi-camera re-identification, and direct
> siren and light-controller hooks. ShoreGuard: the watcher that never
> blinks."

Stop recording. Submit the video + GitHub link before 4:30 PM.
