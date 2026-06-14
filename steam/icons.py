# -*- coding: utf-8 -*-
"""Find a local icon image for a game-list row. Steam changed the librarycache
layout between versions, so we try several locations."""
import glob
import os

# File priority inside appcache/librarycache/<appid>/ (the newer layout). There's
# no explicit "icon" file there, so we take a recognizable small cover/logo.
STEAM_IMAGE_PRIORITY = (
    "library_600x900.jpg",
    "library_600x900_2x.jpg",
    "logo.png",
    "header.jpg",
    "library_hero.jpg",
)


def steam_game_image(steam_path, appid):
    """Best available image for a Steam game, or None. Order: legacy flat
    <appid>_icon.jpg -> files in the <appid>/ subfolder by priority -> any
    non-blur .jpg/.png in the subfolder (hash-named assets)."""
    lc = os.path.join(steam_path, "appcache", "librarycache")
    legacy = os.path.join(lc, "%d_icon.jpg" % appid)
    if os.path.isfile(legacy):
        return legacy
    sub = os.path.join(lc, str(appid))
    if os.path.isdir(sub):
        for fn in STEAM_IMAGE_PRIORITY:
            p = os.path.join(sub, fn)
            if os.path.isfile(p):
                return p
        cands = sorted(glob.glob(os.path.join(sub, "*.jpg")) +
                       glob.glob(os.path.join(sub, "*.png")))
        for p in cands:
            if "_blur" not in os.path.basename(p).lower():
                return p
    return None


def game_icon_path(steam_path, game):
    """Icon path for a game of any kind, or None. non-Steam -> the shortcut's
    icon field (if the file exists); Steam -> steam_game_image."""
    if game.get("kind") == "steam":
        return steam_game_image(steam_path, game["appid"])
    icon = game.get("icon") or ""
    return icon if (icon and os.path.isfile(icon)) else None
