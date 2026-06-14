# -*- coding: utf-8 -*-
"""Steam's own art for installed games (appcache\\librarycache\\<appid>\\).

For regular Steam games, Steam puts the cover/hero/logo/banner in its librarycache,
not in our grid folder. We read it so we can:
  - show in the list that a game DOES have art (rather than "empty"),
  - show the real current art in the "Current" card instead of "none"."""
import os

# File name in librarycache\<appid>\ for each of our art types.
_OFFICIAL = {
    "cover":  ("library_600x900.jpg", "library_600x900_2x.jpg"),
    "banner": ("header.jpg", "library_header.jpg"),
    "hero":   ("library_hero.jpg",),
    "logo":   ("logo.png", "logo_2x.png"),
    "icon":   (),  # the newer layout has no reliable icon file
}


def _flat_name(appid, art_type):
    return {
        "cover": "%d_library_600x900.jpg" % appid,
        "hero": "%d_library_hero.jpg" % appid,
        "logo": "%d_logo.png" % appid,
        "banner": "%d_header.jpg" % appid,
    }.get(art_type)


def official_art(steam_path, appid, art_type):
    """Path to Steam's own file for (appid, art_type), or None."""
    sub = os.path.join(steam_path, "appcache", "librarycache", str(appid))
    for fn in _OFFICIAL.get(art_type, ()):
        p = os.path.join(sub, fn)
        if os.path.isfile(p):
            return p
    flat = _flat_name(appid, art_type)
    if flat:
        p = os.path.join(steam_path, "appcache", "librarycache", flat)
        if os.path.isfile(p):
            return p
    return None


def official_arts(steam_path, appid):
    """{art_type: path|None} for all types, one listdir of the appid's
    librarycache folder (the new per-appid layout) plus an isfile fallback to
    the old flat layout only for the types still missing."""
    legacy = os.path.join(steam_path, "appcache", "librarycache")
    sub = os.path.join(legacy, str(appid))
    try:
        present = set(os.listdir(sub))
    except OSError:
        present = set()
    out = {}
    for t, names in _OFFICIAL.items():
        hit = next((os.path.join(sub, fn) for fn in names if fn in present), None)
        if hit is None:
            flat = _flat_name(appid, t)
            if flat and os.path.isfile(os.path.join(legacy, flat)):
                hit = os.path.join(legacy, flat)
        out[t] = hit
    return out
