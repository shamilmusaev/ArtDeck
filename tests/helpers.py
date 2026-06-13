# -*- coding: utf-8 -*-
"""Хелперы для тестов: сборка бинарного shortcuts.vdf в памяти."""
import os
import struct


def _cstr(s):
    return s.encode("utf-8") + b"\x00"


def build_shortcuts_vdf(games):
    """games: список dict {appid:int, AppName:str, Exe:str}.
    Возвращает bytes в формате, который понимает parse_binary_vdf."""
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
        entry += b"\x08"  # конец вложенного map
        body += b"\x00" + _cstr(str(i)) + entry
    body += b"\x08"  # конец map shortcuts
    return b"\x00" + _cstr("shortcuts") + body


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def make_library(root, apps):
    """Создаёт steamapps/appmanifest_*.acf для набора apps={appid: name}."""
    sa = os.path.join(root, "steamapps")
    for appid, name in apps.items():
        write_file(os.path.join(sa, "appmanifest_%s.acf" % appid),
                   '"AppState"\n{\n  "appid" "%s"\n  "name" "%s"\n  "installdir" "%s"\n}\n'
                   % (appid, name, name.replace(" ", "_")))
    return sa


def make_account(steam_root, uid, games, persona=None):
    """Создаёт userdata/<uid>/config/shortcuts.vdf для games (list для build_shortcuts_vdf).
    Если persona задан — пишет config/loginusers.vdf с этим именем для uid."""
    import os
    cfg = os.path.join(steam_root, "userdata", uid, "config")
    os.makedirs(cfg, exist_ok=True)
    with open(os.path.join(cfg, "shortcuts.vdf"), "wb") as f:
        f.write(build_shortcuts_vdf(games))
    if persona is not None:
        sid = int(uid) + 0x0110000100000000
        write_file(os.path.join(steam_root, "config", "loginusers.vdf"),
                   '"users"\n{\n  "%d"\n  {\n    "PersonaName" "%s"\n  }\n}\n' % (sid, persona))
    return cfg
