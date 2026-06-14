# -*- coding: utf-8 -*-
"""Register custom art in the newer Steam client's cache.

On recent Steam versions, dropping a file into config\\grid is not enough — the
client also reads a "customimage" entry from userdata\\<uid>\\config\\
librarycache\\<appid>.json. Without it, animated covers render as a still image
(and sometimes the art is ignored entirely). This writes/updates that entry while
preserving the others (achievements, etc.) — exactly what Steam's own
"Set Custom Artwork" does."""
import json
import os

# Default value (logo position on the hero, matching what Steam itself writes).
_DEFAULT_DATA = {
    "nVersion": 1,
    "logoPosition": {"pinnedPosition": "BottomLeft", "nWidthPct": 50.0, "nHeightPct": 50.0},
}


def librarycache_json(steam_path, uid, appid):
    return os.path.join(steam_path, "userdata", str(uid), "config",
                        "librarycache", "%d.json" % int(appid))


def register_custom_image(steam_path, uid, appid):
    """Ensure a non-empty customimage entry exists in librarycache/<appid>.json.
    Preserves an existing customimage.data (e.g. the logo position) and any other
    entries. Returns the json path. Quietly leaves a correct entry untouched."""
    p = librarycache_json(steam_path, uid, appid)

    entries = []
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as f:
                entries = json.load(f)
            if not isinstance(entries, list):
                entries = []
        except Exception:
            entries = []

    existing_data = None
    rest = []
    for item in entries:
        if (isinstance(item, list) and len(item) == 2 and item[0] == "customimage"):
            val = item[1] if isinstance(item[1], dict) else {}
            d = val.get("data")
            if isinstance(d, dict) and d:
                existing_data = d  # keep the already-set logo position etc.
            continue  # rebuilt below
        rest.append(item)

    data = existing_data if existing_data is not None else dict(_DEFAULT_DATA)
    rest.append(["customimage", {"version": 1, "data": data}])

    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rest, f, ensure_ascii=False)
    os.replace(tmp, p)
    return p
