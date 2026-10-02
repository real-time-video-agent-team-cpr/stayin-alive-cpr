"""Warning-system state + guard notification + escalation ladder.

Raising an alert flips the whole beach into incident mode: tower lights go
red, the siren sounds, the PA message is armed, and the on-duty guards get
paged. If nobody acknowledges within ESCALATION_S seconds, the alert
escalates to ALL towers. All physical outputs are stubbed (log + optional
GUARD_WEBHOOK_URL) — wire them to real sirens/lights at deployment.
"""
import json
import os
import time
import urllib.request

ESCALATION_S = 30


class WarningSystem:
    def __init__(self, towers=None, escalate_to="ALL TOWERS", ack_by="lifeguard"):
        names = towers or ["Tower 1 — North", "Tower 2 — South", "Pool Deck Post"]
        self.towers = [{"id": n, "light": "green"} for n in names]
        self.escalate_to = escalate_to
        self.ack_by = ack_by
        self.siren = False
        self.pa_message = ""
        self.pa_active = False
        self.alerts = []
        self._aid = 0
        self.log = []

    def _say(self, msg):
        line = f"[warning-system] {msg}"
        self.log.append(line)
        print(line, flush=True)

    def notify_guards(self, message):
        self._say(f"GUARD PAGE: {message}")
        url = os.getenv("GUARD_WEBHOOK_URL")
        if url:
            try:
                req = urllib.request.Request(
                    url, data=json.dumps({"text": message}).encode(),
                    headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=5).read()
            except Exception as e:
                self._say(f"webhook failed ({e}); page logged locally")

    def raise_alert(self, event, message):
        self._aid += 1
        alert = {
            "id": self._aid, "event_id": event["id"], "type": event["type"],
            "severity": event["severity"], "message": message,
            "created_t": event["t"], "created_wall": time.time(),
            "acked": False, "acked_t": None, "escalated": False,
        }
        self.alerts.append(alert)
        for tw in self.towers:
            tw["light"] = "red"
        self.siren = True
        self.pa_message = message
        self.pa_active = True
        self._say(f"ALERT #{alert['id']} [{alert['severity']}] {message}")
        self._say(f"Posts -> RED, siren ON, broadcast armed ({self.escalate_to})")
        self.notify_guards(message)
        return alert

    def raise_severity(self, alert_id, severity):
        for a in self.alerts:
            if a["id"] == alert_id:
                a["severity"] = severity
                self._say(f"ALERT #{alert_id} severity -> {severity}")
                self.pa_message = a["message"] + f" ESCALATED TO {severity}."
                return a
        return None

    def ack(self, alert_id, by=None):
        by = by or self.ack_by
        for a in self.alerts:
            if a["id"] == alert_id and not a["acked"]:
                a["acked"] = True
                a["acked_t"] = time.time()
                for tw in self.towers:
                    tw["light"] = "amber"
                self.siren = False
                self.pa_active = False
                self._say(f"ALERT #{alert_id} acknowledged by {by}; "
                          "towers AMBER, siren OFF")
                return a
        return None

    def check_escalation(self):
        now = time.time()
        for a in self.alerts:
            if (not a["acked"] and not a["escalated"]
                    and now - a["created_wall"] >= ESCALATION_S):
                a["escalated"] = True
                for tw in self.towers:
                    tw["light"] = "red-strobe"
                self.pa_message = a["message"] + f" NO ACK — ESCALATING TO {self.escalate_to}."
                self.pa_active = True
                self._say(f"ALERT #{a['id']} unacked for {ESCALATION_S}s "
                          f"-> ESCALATED to {self.escalate_to}")
                self.notify_guards("ESCALATION: " + a["message"])

    def active(self):
        return [a for a in self.alerts if not a["acked"]]

    def to_dict(self):
        return {
            "towers": self.towers,
            "siren": self.siren,
            "pa_message": self.pa_message,
            "pa_active": self.pa_active,
            "alerts": self.alerts[-10:],
            "escalate_to": self.escalate_to,
        }
