# -*- coding: utf-8 -*-
"""Test helpers: build a binary shortcuts.vdf in memory."""
import os
import struct


def _cstr(s):
    return s.encode("utf-8") + b"\x00"


def build_shortcuts_vdf(games):
    """games: list of dicts {appid:int, AppName:str, Exe:str}.
    Returns bytes in the format parse_binary_vdf understands."""
    body = b""
    for i, g in enumerate(games):
        entry = b""
        entry += b"\x01" + _cstr("AppName") + _cstr(g.get("AppName", ""))
        entry += b"\x01" + _cstr("Exe") + _cstr(g.get("Exe", ""))
        if g.get("icon"):
            entry += b"\x01" + _cstr("icon") + _cstr(g["icon"])
        if "appid" in g:
            entry += b"\x02" + _cstr("appid") + struct.pack("<I", g["appid"] & 0xffffffff)
        if "int64" in g:
            fname, fval = g["int64"]
            entry += b"\x07" + _cstr(fname) + struct.pack("<q", fval)
        entry += b"\x08"  # end of nested map
        body += b"\x00" + _cstr(str(i)) + entry
    body += b"\x08"  # end of the shortcuts map
    return b"\x00" + _cstr("shortcuts") + body


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def make_library(root, apps):
    """Create steamapps/appmanifest_*.acf for apps={appid: name}."""
    sa = os.path.join(root, "steamapps")
    for appid, name in apps.items():
        write_file(os.path.join(sa, "appmanifest_%s.acf" % appid),
                   '"AppState"\n{\n  "appid" "%s"\n  "name" "%s"\n  "installdir" "%s"\n}\n'
                   % (appid, name, name.replace(" ", "_")))
    return sa


def make_account(steam_root, uid, games, persona=None):
    """Create userdata/<uid>/config/shortcuts.vdf for games (a list for build_shortcuts_vdf).
    If persona is given, write config/loginusers.vdf with that name for the uid."""
    cfg = os.path.join(steam_root, "userdata", uid, "config")
    os.makedirs(cfg, exist_ok=True)
    with open(os.path.join(cfg, "shortcuts.vdf"), "wb") as f:
        f.write(build_shortcuts_vdf(games))
    if persona is not None:
        sid = int(uid) + 0x0110000100000000
        write_file(os.path.join(steam_root, "config", "loginusers.vdf"),
                   '"users"\n{\n  "%d"\n  {\n    "PersonaName" "%s"\n  }\n}\n' % (sid, persona))
    return cfg
