# -*- coding: utf-8 -*-
"""Per-launcher game detectors. Register a new launcher in LAUNCHERS."""
from steam.launchers import epic, gog
from steam.shortcuts import game_appid, normalize_exe

# (key, label, detect-callable). Order = display order.
LAUNCHERS = (
    ("epic", "Epic Games", epic.detect),
    ("gog", "GOG", gog.detect),
)


def detect_all(imported_appids=None, exe_to_appid=None):
    """[{"key","label","games":[...]}] for every launcher. All detected games
    are returned (none dropped). Each game dict is a copy with its computed
    unsigned "appid" attached, plus an "imported" bool. When imported is True,
    "steam_appid" holds the real shortcut appid to use for deep-linking to
    Artwork (may differ from the computed appid when a game was added via a
    third-party tool). A detector that raises contributes an empty list, never
    aborts the scan."""
    imp_ids = imported_appids or set()
    exe_map = exe_to_appid or {}
    out = []
    for key, label, fn in LAUNCHERS:
        try:
            found = fn()
        except Exception:
            found = []
        games = []
        for g in found:
            g = dict(g)
            aid = game_appid(g)
            g["appid"] = aid
            ne = normalize_exe(g.get("exe", ""))
            if aid in imp_ids:
                g["imported"] = True
                g["steam_appid"] = aid
            elif ne and ne in exe_map:
                g["imported"] = True
                g["steam_appid"] = exe_map[ne]
            else:
                g["imported"] = False
                g["steam_appid"] = None
            games.append(g)
        out.append({"key": key, "label": label, "games": games})
    return out
