# -*- coding: utf-8 -*-
"""Источники игр аккаунта: non-Steam ярлыки + осиротевшие арты."""
import glob
import os
import re
import zlib

from steam.vdf import parse_binary_vdf, get_ci, parse_text_vdf
from steam.arts import art_status, grid_index
from steam.paths import account_paths

NONSTEAM_MIN = 0x80000000  # appid non-Steam игр всегда >= этого

# appid'ы инструментов/рантаймов, которые НЕ являются играми.
STEAM_TOOL_APPIDS = {
    228980,   # Steamworks Common Redistributables
    1070560,  # Steam Linux Runtime 1.0 (scout)
    1391110,  # Steam Linux Runtime 2.0 (soldier)
    1628350,  # Steam Linux Runtime 3.0 (sniper)
    1493710,  # Proton Experimental
}

# Подстроки в имени, по которым считаем запись не-игрой.
_TOOL_NAME_HINTS = (
    "steamworks common redistributables",
    "steam linux runtime",
    "dedicated server",
)


def _is_tool(appid, name):
    if appid in STEAM_TOOL_APPIDS:
        return True
    low = name.lower()
    return any(h in low for h in _TOOL_NAME_HINTS)


def list_libraries(steam_path):
    """Пути всех Steam-библиотек из libraryfolders.vdf (+ сам Steam как запас)."""
    out, seen = [], set()

    def add(p):
        if p and os.path.isdir(p):
            key = os.path.normcase(os.path.normpath(p))
            if key not in seen:
                seen.add(key)
                out.append(p)

    add(steam_path)  # основная библиотека всегда есть
    for cand in (os.path.join(steam_path, "steamapps", "libraryfolders.vdf"),
                 os.path.join(steam_path, "config", "libraryfolders.vdf")):
        if not os.path.isfile(cand):
            continue
        try:
            with open(cand, encoding="utf-8", errors="replace") as f:
                data = parse_text_vdf(f.read())
        except Exception:
            continue
        folders = data.get("libraryfolders") or data.get("LibraryFolders") or {}
        for _, entry in folders.items():
            if isinstance(entry, dict) and entry.get("path"):
                add(os.path.normpath(entry["path"]))
        break  # одного валидного файла достаточно
    return out


def load_installed(steam_path):
    """Установленные Steam-игры из всех библиотек: [{appid:int, name, kind:'steam',
    installdir, library}]. Инструменты/рантаймы отфильтрованы, дубликаты убраны по appid."""
    games, seen = [], set()
    for lib in list_libraries(steam_path):
        for acf in sorted(glob.glob(os.path.join(lib, "steamapps", "appmanifest_*.acf"))):
            try:
                with open(acf, encoding="utf-8", errors="replace") as f:
                    st = parse_text_vdf(f.read()).get("AppState") or {}
            except Exception:
                continue
            try:
                appid = int(st.get("appid") or 0)
            except (ValueError, TypeError):
                continue
            name = st.get("name") or ""
            if not appid or not name or appid in seen or _is_tool(appid, name):
                continue
            seen.add(appid)
            games.append({"appid": appid, "name": name, "kind": "steam",
                          "installdir": st.get("installdir") or "", "library": lib})
    games.sort(key=lambda g: g["name"].lower())
    return games


def compute_legacy_appid(exe, appname):
    return zlib.crc32((exe + appname).encode("utf-8")) & 0xffffffff | 0x80000000


def load_shortcuts(vdf_path):
    """Возвращает список словарей: {appid, name, exe, icon, kind:'shortcut'}."""
    if not os.path.isfile(vdf_path):
        return []
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
        name = get_ci(entry, "AppName") or ""
        exe = get_ci(entry, "Exe") or ""
        icon = get_ci(entry, "icon") or ""
        appid = get_ci(entry, "appid")
        if not appid:
            appid = compute_legacy_appid(exe, name)
        appid &= 0xffffffff
        if name:
            games.append({"appid": appid, "name": name, "exe": exe,
                          "icon": icon, "kind": "shortcut"})
    return games


def list_games(steam_path, uid):
    """Игры аккаунта со статусом артов: [{appid, name, exe, icon, kind, status}, ...]."""
    vdf, grid_dir = account_paths(steam_path, uid)
    if not os.path.isfile(vdf):
        return []
    games = load_shortcuts(vdf)
    names = grid_index(grid_dir)
    for g in games:
        g["status"] = art_status(grid_dir, g["appid"], names)
    return games


def installed_games(steam_path, uid):
    """Установленные Steam-игры со статусом артов для grid указанного аккаунта."""
    _, grid_dir = account_paths(steam_path, uid)
    games = load_installed(steam_path)
    names = grid_index(grid_dir)
    for g in games:
        g["status"] = art_status(grid_dir, g["appid"], names)
    return games


def find_orphans(vdf_path):
    """(grid_dir, [имена_файлов]) — осиротевшие арты non-Steam игр (appid >= NONSTEAM_MIN
    и отсутствует в shortcuts.vdf). Файлы обычных Steam-игр (маленький appid) не трогает."""
    grid_dir = os.path.join(os.path.dirname(vdf_path), "grid")
    if not os.path.isdir(grid_dir):
        return grid_dir, []
    if not os.path.isfile(vdf_path):
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
        for fn in orphans:
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
