# -*- coding: utf-8 -*-
"""Build non-Steam shortcut entries for shortcuts.vdf from detected launcher
games. The appid is computed the same way Steam (and load_shortcuts) does, from
the quoted Exe + AppName, so art keyed on it lines up."""
from steam.library import compute_legacy_appid
from steam.vdf import get_ci


def _quote(p):
    return "\"%s\"" % (p or "")


def game_appid(game):
    """Unsigned non-Steam appid for a detected game."""
    return compute_legacy_appid(_quote(game["exe"]), game["name"])


def build_shortcut_entry(game):
    """A full shortcuts.vdf entry. appid is stored signed (int32), matching how
    parse_binary_vdf reads it back."""
    appid = game_appid(game)
    signed = appid - 0x100000000 if appid >= 0x80000000 else appid
    tags = {"0": "ArtDeck"}
    if game.get("launcher"):
        tags["1"] = game["launcher"]
    return {
        "appid": signed,
        "AppName": game["name"],
        "Exe": _quote(game["exe"]),
        "StartDir": _quote(game.get("start_dir", "")),
        "icon": game.get("icon", ""),
        "ShortcutPath": "",
        "LaunchOptions": "",
        "IsHidden": 0,
        "AllowDesktopConfig": 1,
        "AllowOverlay": 1,
        "OpenVR": 0,
        "Devkit": 0,
        "DevkitGameID": "",
        "DevkitOverrideAppID": 0,
        "LastPlayTime": 0,
        "FlatpakAppID": "",
        "tags": tags,
    }


def append_shortcuts(shortcuts_map, new_games):
    """Append entries for new_games, skipping any whose appid already exists.
    Returns (shortcuts_map, added_count). Keys are stringified indices."""
    existing = set()
    for entry in shortcuts_map.values():
        if isinstance(entry, dict):
            aid = get_ci(entry, "appid")
            if aid is not None:
                existing.add(aid & 0xffffffff)
    idx = len(shortcuts_map)
    added = 0
    for g in new_games:
        aid = game_appid(g)
        if aid in existing:
            continue
        shortcuts_map[str(idx)] = build_shortcut_entry(g)
        existing.add(aid)
        idx += 1
        added += 1
    return shortcuts_map, added
