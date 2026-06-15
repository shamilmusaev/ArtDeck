# -*- coding: utf-8 -*-
"""Art logic: types, status, applying, and listing variants for the GUI."""
import os
from urllib import parse

from steam.sgdb import list_arts_raw, download

# Art types. suffix is what gets appended to <appid> in the file name.
ART_TYPES = {
    "cover":  {"endpoint": "grids",  "suffix": "p",     "params": {"dimensions": "600x900"}},
    "banner": {"endpoint": "grids",  "suffix": "",      "params": {"dimensions": "460x215,920x430"}},
    "hero":   {"endpoint": "heroes", "suffix": "_hero", "params": {}},
    "logo":   {"endpoint": "logos",  "suffix": "_logo", "params": {}},
}

ART_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def grid_index(grid_dir):
    """Set of filenames present in grid_dir (a single listdir). Lets art_status
    test presence by membership instead of ~20 isfile syscalls per game."""
    try:
        return set(os.listdir(grid_dir))
    except OSError:
        return set()


def existing_art(grid_dir, appid, suffix, names=None):
    names = grid_index(grid_dir) if names is None else names
    for ext in ART_EXTS:
        fn = "%d%s%s" % (appid, suffix, ext)
        if fn in names:
            return os.path.join(grid_dir, fn)
    return None


def art_status(grid_dir, appid, names=None):
    """{art_type: path|None} for every art type of one game."""
    names = grid_index(grid_dir) if names is None else names
    return {t: existing_art(grid_dir, appid, cfg["suffix"], names) for t, cfg in ART_TYPES.items()}


def fetch_art_url(game_id, art_cfg, api_key):
    """First matching art URL (auto mode)."""
    params = dict(art_cfg["params"])
    params.setdefault("types", "static")
    data = list_arts_raw(art_cfg["endpoint"], game_id, api_key, params)
    if not data and "dimensions" in params:
        params.pop("dimensions")
        data = list_arts_raw(art_cfg["endpoint"], game_id, api_key, params)
    if not data:
        return None
    return data[0]["url"]


def list_arts(game_id, art_type, api_key, limit=40, animated=False):
    """Variants of the given art type:
    [{url, thumb, width, height, style, animated}, ...].
    animated=True -> request animated only (types=animated)."""
    cfg = ART_TYPES[art_type]
    art_kind = "animated" if animated else "static"
    data = list_arts_raw(cfg["endpoint"], game_id, api_key, {"types": art_kind})
    items = []
    for a in data:
        items.append({
            "url": a.get("url"),
            "thumb": a.get("thumb") or a.get("url"),
            "width": a.get("width"),
            "height": a.get("height"),
            "style": a.get("style"),
            "animated": animated,
        })
    # The grids endpoint returns both vertical (covers) and horizontal (banners)
    # mixed together. Filter by orientation: cover = portrait, banner = landscape.
    def portrait(a):
        return not (a["width"] and a["height"]) or a["height"] >= a["width"]

    def landscape(a):
        return not (a["width"] and a["height"]) or a["width"] > a["height"]

    if art_type == "cover":
        items = [a for a in items if portrait(a)]
        items.sort(key=lambda a: 0 if (a["width"], a["height"]) == (600, 900) else 1)
    elif art_type == "banner":
        items = [a for a in items if landscape(a)]
    return [a for a in items if a["url"]][:limit]


def apply_art(grid_dir, appid, art_type, url):
    """Download art to <appid><suffix><ext>, removing other-extension dupes of the same slot."""
    suffix = ART_TYPES[art_type]["suffix"]
    ext = os.path.splitext(parse.urlparse(url).path)[1].lower() or ".png"
    if ext not in ART_EXTS:
        ext = ".png"
    # Steam (especially for installed games) reads the cover from .png/.jpg but
    # ignores .webp; it sniffs the format by content, so webp bytes inside a .png
    # render fine. We save webp as .png — otherwise the art "doesn't apply".
    if ext == ".webp":
        ext = ".png"
    os.makedirs(grid_dir, exist_ok=True)
    for e in ART_EXTS:
        if e == ext:
            continue
        old = os.path.join(grid_dir, "%d%s%s" % (appid, suffix, e))
        if os.path.isfile(old):
            try:
                os.remove(old)
            except OSError:
                pass
    dest = os.path.join(grid_dir, "%d%s%s" % (appid, suffix, ext))
    download(url, dest)
    return dest


def revert_art(grid_dir, appid, art_type):
    """Delete our custom art for this slot (all extensions). Afterwards Steam shows
    its own original (for installed games) or the gray placeholder (non-Steam).
    Returns the list of deleted files."""
    suffix = ART_TYPES[art_type]["suffix"]
    removed = []
    for e in ART_EXTS:
        p = os.path.join(grid_dir, "%d%s%s" % (appid, suffix, e))
        if os.path.isfile(p):
            try:
                os.remove(p)
                removed.append(os.path.basename(p))
            except OSError:
                pass
    return removed
