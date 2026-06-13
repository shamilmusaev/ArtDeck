# -*- coding: utf-8 -*-
"""Хелперы для тестов: сборка бинарного shortcuts.vdf в памяти."""
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
        if "appid" in g:
            entry += b"\x02" + _cstr("appid") + struct.pack("<I", g["appid"] & 0xffffffff)
        if "int64" in g:
            fname, fval = g["int64"]
            entry += b"\x07" + _cstr(fname) + struct.pack("<q", fval)
        entry += b"\x08"  # конец вложенного map
        body += b"\x00" + _cstr(str(i)) + entry
    body += b"\x08"  # конец map shortcuts
    return b"\x00" + _cstr("shortcuts") + body
