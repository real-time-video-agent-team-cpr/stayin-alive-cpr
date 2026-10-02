"""Three deployable ShoreGuard sites.

family     — one backyard pool, parent/house warning system
multipool  — aquatic center, four live pools, facility dispatch
beach      — open-water swim zone, tower/PA/siren mesh
"""

SITES = {
    "family": {
        "id": "family",
        "label": "FAMILY POOL",
        "blurb": "Single backyard pool. Fall detection + parent paging.",
        "ack_by": "parent",
        "escalate_to": "NEIGHBORS + 911",
        "warn_title": "HOUSE ALERTS",
        "pa_title": "HOME ALERT",
        "pa_prefix": "Attention household.",
        "pa_standby": "No home alert armed.",
        "entry_phrase": "the pool edge",
        "water_noun": "pool",
        "towers": ["Parent phone", "Home siren", "Neighbor watch"],
        "cameras": [
            {
                "id": "cam-01",
                "name": "BACKYARD POOL",
                "kind": "pool",
                "incident": True,
                "theme": "family",
                "water": (150, 130, 500, 400),
            },
            {
                "id": "cam-02",
                "name": "PATIO DOOR",
                "kind": "patio",
                "incident": False,
                "theme": "patio",
                "water": (900, 900, 910, 910),  # no reachable water
            },
        ],
    },
    "multipool": {
        "id": "multipool",
        "label": "AQUATIC CENTER",
        "blurb": "Four pools, one dispatch desk. Incident on the kids pool.",
        "ack_by": "deck guard",
        "escalate_to": "ALL POOL POSTS",
        "warn_title": "FACILITY POSTS",
        "pa_title": "FACILITY PA",
        "pa_prefix": "Attention aquatic center.",
        "pa_standby": "No facility message armed.",
        "entry_phrase": "the kids-pool edge",
        "water_noun": "pool",
        "towers": ["Kids pool post", "Lap pool post", "Dive well", "Front desk"],
        "cameras": [
            {
                "id": "cam-01",
                "name": "KIDS POOL",
                "kind": "pool",
                "incident": True,
                "theme": "kids",
                "water": (140, 120, 520, 400),
            },
            {
                "id": "cam-02",
                "name": "LAP POOL",
                "kind": "pool",
                "incident": False,
                "theme": "lap",
                "water": (80, 160, 560, 320),
            },
            {
                "id": "cam-03",
                "name": "DIVE WELL",
                "kind": "pool",
                "incident": False,
                "theme": "dive",
                "water": (180, 80, 460, 400),
            },
            {
                "id": "cam-04",
                "name": "SPA / HOT TUB",
                "kind": "pool",
                "incident": False,
                "theme": "spa",
                "water": (200, 180, 440, 360),
            },
        ],
    },
    "beach": {
        "id": "beach",
        "label": "OPEN BEACH",
        "blurb": "Shore-to-surf cameras. Fall into water + stillness in the swim zone.",
        "ack_by": "tower guard",
        "escalate_to": "ALL TOWERS",
        "warn_title": "TOWER LIGHTS",
        "pa_title": "PUBLIC ADDRESS",
        "pa_prefix": "Attention beachgoers.",
        "pa_standby": "No message armed.",
        "entry_phrase": "the surf line",
        "water_noun": "water",
        "towers": ["Tower 1 — North", "Tower 2 — South", "Jet ski", "Mobile unit"],
        "cameras": [
            {
                "id": "cam-01",
                "name": "SWIM ZONE",
                "kind": "beach",
                "incident": True,
                "theme": "surf",
                "water": (0, 210, 640, 480),
            },
            {
                "id": "cam-02",
                "name": "SHORE NORTH",
                "kind": "beach",
                "incident": False,
                "theme": "shore",
                "water": (0, 240, 640, 480),
            },
            {
                "id": "cam-03",
                "name": "PIER",
                "kind": "beach",
                "incident": False,
                "theme": "pier",
                "water": (0, 200, 640, 480),
            },
            {
                "id": "cam-04",
                "name": "TOWER 2 LOOKOUT",
                "kind": "beach",
                "incident": False,
                "theme": "dunes",
                "water": (0, 280, 640, 480),
            },
        ],
    },
}


def get_site(site_id=None):
    key = (site_id or "family").lower()
    if key not in SITES:
        raise KeyError(f"unknown site {site_id!r}")
    return SITES[key]


def list_sites():
    return [
        {"id": s["id"], "label": s["label"], "blurb": s["blurb"],
         "cameras": len(s["cameras"])}
        for s in SITES.values()
    ]
