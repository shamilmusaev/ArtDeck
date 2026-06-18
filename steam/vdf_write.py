# -*- coding: utf-8 -*-
"""Serialize a shortcuts structure back to Steam's binary VDF (shortcuts.vdf).

The inverse of steam.vdf.parse_binary_vdf. ArtDeck reads shortcuts to enumerate
non-Steam games; importing games from other launchers needs to WRITE them back.
Always back up the existing file first - a bad write would lose every non-Steam
shortcut. Types mirror the parser: 0x00 map, 0x01 str, 0x02 int32, 0x07 int64,
0x08 end."""
import os
import shutil
import struct

from steam.vdf import parse_binary_vdf


def _cstring(s):
    return s.encode("utf-8") + b"\x00"


def _dump_value(key, value):
    k = _cstring(str(key))
    if isinstance(value, dict):
        return b"\x00" + k + _dump_map(value)
    if isinstance(value, int):
        if -2147483648 <= value <= 2147483647:
            return b"\x02" + k + struct.pack("<i", value)
        return b"\x07" + k + struct.pack("<q", value)
    if isinstance(value, str):
        return b"\x01" + k + _cstring(value)
    raise ValueError("unsupported VDF value type: %r" % type(value))


def _dump_map(m):
    out = bytearray()
    for key, value in m.items():
        out += _dump_value(key, value)
    out += b"\x08"
    return bytes(out)


def dump_binary_vdf(shortcuts):
    """Serialize a shortcuts map ({"0": {...}, "1": {...}}) to Steam VDF bytes."""
    return b"\x00" + _cstring("shortcuts") + _dump_map(shortcuts) + b"\x08"


def read_shortcuts_map(vdf_path):
    """Parsed shortcuts map, or {} if the file is missing or unreadable."""
    if not os.path.isfile(vdf_path):
        return {}
    try:
        with open(vdf_path, "rb") as f:
            return parse_binary_vdf(f.read())
    except Exception:
        return {}


def write_shortcuts(vdf_path, shortcuts):
    """Back up vdf_path (if present) then write the shortcuts map atomically.
    Returns the backup path, or None if there was nothing to back up. Raises if
    the backup fails - never risk the only copy of the user's shortcuts."""
    backup = None
    if os.path.isfile(vdf_path):
        backup = vdf_path + ".bak"
        shutil.copy2(vdf_path, backup)
    d = os.path.dirname(vdf_path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = vdf_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(dump_binary_vdf(shortcuts))
    os.replace(tmp, vdf_path)
    return backup
