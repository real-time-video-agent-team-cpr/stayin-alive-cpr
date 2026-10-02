"""Weights & Biases LLM integration: alert copy + natural-language search.

Set WANDB_INFERENCE_URL (an OpenAI-compatible /chat/completions endpoint),
WANDB_API_KEY and WANDB_MODEL to use a real hosted model. Without them the
template fallback drafts the alert copy and search runs over the local event
index — in production this index is backed by video embeddings so queries
like "when did the swimmer go under" retrieve the exact clip.
"""
import json
import os
import re
import urllib.request

SYNONYMS = {
    "fall": ["fall", "fell", "enter", "entered", "drop", "plunge"],
    "under": ["under", "submerg", "sink", "sinking", "drown", "below", "motionless"],
    "swimmer": ["swimmer", "person", "victim", "track"],
    "struggle": ["struggle", "thrash", "distress", "panic", "erratic"],
    "when": ["when", "time", "moment"],
    "pool": ["pool", "water"],
    "edge": ["edge", "side", "deck"],
}


def _tokens(q):
    return re.findall(r"[a-z]+", q.lower())


def semantic_search(query, events, top_k=5):
    """Keyword + synonym retrieval over timestamped event captions."""
    toks = _tokens(query)
    scored = []
    for ev in events:
        text = (ev["caption"] + " " + ev["type"]).lower()
        score = 0
        for tk in toks:
            if tk in text:
                score += 2
            else:
                for syns in SYNONYMS.values():
                    if tk in syns and any(s in text for s in syns):
                        score += 1
                        break
        if score:
            scored.append((score, ev))
    scored.sort(key=lambda x: -x[0])
    return [ev for _, ev in scored[:top_k]]


class AlertComposer:
    def __init__(self):
        self.url = os.getenv("WANDB_INFERENCE_URL")
        self.key = os.getenv("WANDB_API_KEY")
        self.model = os.getenv("WANDB_MODEL", "llama-3.1-8b-instruct")

    def _call(self, messages):
        if not (self.url and self.key):
            raise RuntimeError("LLM not configured")
        body = json.dumps(
            {"model": self.model, "messages": messages, "max_tokens": 120}
        ).encode()
        req = urllib.request.Request(
            self.url, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"].strip()

    def compose(self, event, where="Pool Deck Camera 1"):
        fallback = (
            f"[{event['severity']}] {event['type'].replace('_', ' ')} — "
            f"{event['caption']} at T+{event['t']:.1f}s on {where}. "
            f"Immediate response required."
        )
        try:
            text = self._call([
                {"role": "system",
                 "content": "You write terse lifeguard/parent dispatch alerts. "
                            "One or two sentences, urgent, no fluff."},
                {"role": "user",
                 "content": f"Write a dispatch alert: {event['type']}, "
                            f"{event['caption']}, severity {event['severity']}, "
                            f"camera {where}."},
            ])
            from . import tools
            tools._set("wandb", "live", "composed dispatch copy")
            return text
        except Exception:
            return fallback

    def answer(self, query, events):
        hits = semantic_search(query, events)
        if not hits:
            local = "No matching moments in the event index."
        else:
            lines = [f"T+{e['t']:.1f}s — {e['caption']}" for e in hits]
            local = "Matching moments:\n" + "\n".join(lines)
        try:
            catalog = "\n".join(
                f"T+{e['t']:.1f}s {e['type']} {e.get('camera','')} {e['caption']}"
                for e in events[-30:]
            )
            text = self._call([
                {"role": "system",
                 "content": "You retrieve moments from a lifeguard event log. "
                            "Answer with timestamps. If unknown, say so."},
                {"role": "user", "content": f"Query: {query}\nLog:\n{catalog}"},
            ])
            from . import tools
            tools._set("wandb", "live", "answered footage query")
            return text
        except Exception:
            return local
