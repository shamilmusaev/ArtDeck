# -*- coding: utf-8 -*-
"""Per-launcher game detectors. Register a new launcher in LAUNCHERS."""
from steam.launchers import epic, gog
from steam.shortcuts import game_appid

# (key, label, detect-callable). Order = display order.
LAUNCHERS = (
    ("epic", "Epic Games", epic.detect),
    ("gog", "GOG", gog.detect),
)


def detect_all(exclude_appids=None):
    """[{"key","label","games":[...]}] for every launcher. Each game gets its
    unsigned "appid"; games whose appid is in exclude_appids are dropped. A
    detector that raises contributes an empty list, never aborts the scan."""
    skip = exclude_appids or set()
    out = []
    for key, label, fn in LAUNCHERS:
        try:
            found = fn()
        except Exception:
            found = []
        games = []
        for g in found:
            aid = game_appid(g)
            if aid in skip:
                continue
            g = dict(g)
            g["appid"] = aid
            games.append(g)
        out.append({"key": key, "label": label, "games": games})
    return out
