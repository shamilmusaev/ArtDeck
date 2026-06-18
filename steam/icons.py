# -*- coding: utf-8 -*-
"""Find a local icon image for a game-list row. Steam changed the librarycache
layout between versions, so we try several locations."""
import glob
import os

from steam import exeicon

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


# Extensions the window's <img> can actually render. A shortcut's `icon` field
# often points at the game's .exe (Steam extracts the icon itself); we can't show
# that, so we only accept real image files.
ICON_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico")


def _image_file(path):
    """Return path if it's an existing file with a renderable image extension."""
    p = path or ""
    return p if (p and os.path.isfile(p) and p.lower().endswith(ICON_EXTS)) else None


def _exe_target(exe_field):
    """The executable path out of a shortcut's Exe field, which is usually quoted
    and may carry launch arguments: '"C:\\g\\game.exe" -arg' -> 'C:\\g\\game.exe'."""
    s = (exe_field or "").strip()
    if s.startswith('"'):
        end = s.find('"', 1)
        return s[1:end] if end != -1 else s[1:]
    return s


def shortcut_icon_path(grid_dir, appid, icon_field, exe=None):
    """Icon for a non-Steam shortcut, or None. Priority:
    1. the real icon Steam itself shows (grid/<appid>_icon.png, then -icon.ico);
    2. the shortcut's own `icon` field, if it's a renderable image;
    3. the icon extracted from the executable (what Steam shows when the `icon`
       field is empty or points at the .exe) — from the icon field if it's an
       .exe/.dll, otherwise from the Exe target;
    4. fall back to the game's cover/logo in grid so the row isn't blank."""
    if grid_dir:
        for name in ("%d_icon.png" % appid, "%d-icon.ico" % appid):
            p = os.path.join(grid_dir, name)
            if os.path.isfile(p):
                return p
    img = _image_file(icon_field)
    if img:
        return img
    field = icon_field or ""
    src = field if field.lower().endswith((".exe", ".dll")) else _exe_target(exe)
    extracted = exeicon.icon_file(src)
    if extracted:
        return extracted
    if grid_dir:
        for name in ("%dp.png" % appid, "%d.png" % appid, "%d_logo.png" % appid):
            p = os.path.join(grid_dir, name)
            if os.path.isfile(p):
                return p
    return None


def game_icon_path(steam_path, game, grid_dir=None):
    """Icon path for a game of any kind, or None. Steam -> steam_game_image;
    non-Steam -> shortcut_icon_path (grid icon, icon field, exe icon, or cover)."""
    if game.get("kind") == "steam":
        return steam_game_image(steam_path, game["appid"])
    return shortcut_icon_path(grid_dir, game["appid"], game.get("icon"), game.get("exe"))
