# -*- coding: utf-8 -*-
"""Post-apply check of installed art. Steam doesn't report whether it showed the
cover, but we can catch the real reasons it might not appear:
  - the file is corrupt/empty (a broken download),
  - a file of another extension is left in the same slot and couldn't be deleted
    (usually Steam held it open) -> Steam shows the old one,
  - (for animation) the customimage registration didn't get written."""
import os

from steam.arts import ART_TYPES, ART_EXTS


def valid_image(path):
    """File exists, is non-empty, and starts with a PNG/JPEG/WEBP/GIF signature."""
    try:
        if os.path.getsize(path) == 0:
            return False
        with open(path, "rb") as f:
            h = f.read(12)
    except OSError:
        return False
    if h[:4] == b"\x89PNG":
        return True
    if h[:3] == b"\xff\xd8\xff":
        return True
    if h[:4] == b"RIFF" and h[8:12] == b"WEBP":
        return True
    if h[:4] in (b"GIF8",):
        return True
    return False


def competing_files(grid_dir, appid, art_type, applied_path):
    """Files in the same slot (<appid><suffix>) with a different extension —
    Steam may show one of these instead of the art we just applied."""
    suffix = ART_TYPES[art_type]["suffix"]
    applied = os.path.basename(applied_path).lower()
    out = []
    for e in ART_EXTS:
        name = "%d%s%s" % (appid, suffix, e)
        if name.lower() == applied:
            continue
        if os.path.isfile(os.path.join(grid_dir, name)):
            out.append(name)
    return out


def verify_applied(grid_dir, appid, art_type, dest):
    """Check the applied art. Returns {ok, code, files}.
    code: None (all good) | 'corrupt' (broken file) | 'competing' (dup in slot)."""
    if not dest or not os.path.isfile(dest) or not valid_image(dest):
        return {"ok": False, "code": "corrupt", "files": []}
    comp = competing_files(grid_dir, appid, art_type, dest)
    if comp:
        return {"ok": False, "code": "competing", "files": comp}
    return {"ok": True, "code": None, "files": []}
