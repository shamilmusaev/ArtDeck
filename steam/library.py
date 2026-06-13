# -*- coding: utf-8 -*-
"""Источники игр аккаунта: non-Steam ярлыки + осиротевшие арты."""
import os
import re
import zlib

from steam.vdf import parse_binary_vdf, get_ci
from steam.arts import art_status
from steam.paths import account_paths

NONSTEAM_MIN = 0x80000000  # appid non-Steam игр всегда >= этого


def compute_legacy_appid(exe, appname):
    return zlib.crc32((exe + appname).encode("utf-8")) & 0xffffffff | 0x80000000


def load_shortcuts(vdf_path):
    """Возвращает список словарей: {appid, name, exe}."""
    with open(vdf_path, "rb") as f:
        data = f.read()
    try:
        parsed = parse_binary_vdf(data)
    except Exception as e:
        print("  [!] Не удалось разобрать %s: %s" % (vdf_path, e))
        return []
    games = []
    for _, entry in parsed.items():
        if not isinstance(entry, dict):
            continue
        name = get_ci(entry, "AppName") or get_ci(entry, "appname") or ""
        exe = get_ci(entry, "Exe") or get_ci(entry, "exe") or ""
        appid = get_ci(entry, "appid")
        if not appid:
            appid = compute_legacy_appid(exe, name)
        appid &= 0xffffffff
        if name:
            games.append({"appid": appid, "name": name, "exe": exe})
    return games


def list_games(steam_path, uid):
    """Игры аккаунта со статусом артов: [{appid, name, exe, status}, ...]."""
    vdf, grid_dir = account_paths(steam_path, uid)
    if not os.path.isfile(vdf):
        return []
    games = load_shortcuts(vdf)
    for g in games:
        g["status"] = art_status(grid_dir, g["appid"])
    return games


def find_orphans(vdf_path):
    """(grid_dir, [имена_файлов]) — осиротевшие арты non-Steam игр (appid >= NONSTEAM_MIN
    и отсутствует в shortcuts.vdf). Файлы обычных Steam-игр (маленький appid) не трогает."""
    grid_dir = os.path.join(os.path.dirname(vdf_path), "grid")
    if not os.path.isdir(grid_dir):
        return grid_dir, []
    valid = {g["appid"] for g in load_shortcuts(vdf_path)}
    orphans = []
    for fn in os.listdir(grid_dir):
        if not os.path.isfile(os.path.join(grid_dir, fn)):
            continue
        m = re.match(r"^(\d+)", fn)
        if not m:
            continue
        aid = int(m.group(1))
        if aid < NONSTEAM_MIN or aid in valid:
            continue
        orphans.append(fn)
    return grid_dir, sorted(orphans)


def clean_orphans(vdf_files, dry_run):
    """Удаляет осиротевшие арты во всех переданных аккаунтах (CLI-режим)."""
    total = 0
    for vdf in sorted(vdf_files):
        uid = vdf.split(os.sep)[-3]
        grid_dir, orphans = find_orphans(vdf)
        print("\n=== Аккаунт %s: осиротевших файлов: %d ===" % (uid, len(orphans)))
        for fn in sorted(orphans):
            path = os.path.join(grid_dir, fn)
            if dry_run:
                print("   DRY  удалить -> %s" % fn)
            else:
                try:
                    os.remove(path)
                    print("   удалён -> %s" % fn)
                except OSError as e:
                    print("   FAIL %s (%s)" % (fn, e))
            total += 1
    print("\n--- Очистка: %s %d файл(ов) ---" % ("найдено бы" if dry_run else "удалено", total))
