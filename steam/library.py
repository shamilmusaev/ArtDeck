# -*- coding: utf-8 -*-
"""Account game sources: non-Steam shortcuts, installed games, and orphaned art."""
import glob
import os
import re
import zlib

from steam.vdf import parse_binary_vdf, get_ci, parse_text_vdf
from steam.arts import art_status, grid_index
from steam.paths import account_paths

NONSTEAM_MIN = 0x80000000  # a non-Steam game's appid is always >= this

# appids of tools/runtimes that are NOT games.
STEAM_TOOL_APPIDS = {
    228980,   # Steamworks Common Redistributables
    1070560,  # Steam Linux Runtime 1.0 (scout)
    1391110,  # Steam Linux Runtime 2.0 (soldier)
    1628350,  # Steam Linux Runtime 3.0 (sniper)
    1493710,  # Proton Experimental
}

# Name substrings that mark an entry as a non-game.
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
    """Paths of all Steam libraries from libraryfolders.vdf (+ Steam itself as fallback)."""
    out, seen = [], set()

    def add(p):
        if p and os.path.isdir(p):
            key = os.path.normcase(os.path.normpath(p))
            if key not in seen:
                seen.add(key)
                out.append(p)

    add(steam_path)  # the main library always exists
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
        break  # one valid file is enough
    return out


def load_installed(steam_path):
    """Installed Steam games across all libraries: [{appid:int, name, kind:'steam',
    installdir, library}]. Tools/runtimes filtered out, duplicates removed by appid."""
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
    """Return a list of dicts: {appid, name, exe, icon, kind:'shortcut'}."""
    if not os.path.isfile(vdf_path):
        return []
    with open(vdf_path, "rb") as f:
        data = f.read()
    try:
        parsed = parse_binary_vdf(data)
    except Exception as e:
        print("  [!] Could not parse %s: %s" % (vdf_path, e))
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
    """Account games with art status: [{appid, name, exe, icon, kind, status}, ...]."""
    vdf, grid_dir = account_paths(steam_path, uid)
    if not os.path.isfile(vdf):
        return []
    games = load_shortcuts(vdf)
    names = grid_index(grid_dir)
    for g in games:
        g["status"] = art_status(grid_dir, g["appid"], names)
    return games


def installed_games(steam_path, uid, _load_installed=None):
    """Installed Steam games with art status for the given account's grid.
    _load_installed is an optional override (used by the GUI server to cache
    the manifest scan; defaults to the in-process load_installed)."""
    _, grid_dir = account_paths(steam_path, uid)
    games = (_load_installed or load_installed)(steam_path)
    names = grid_index(grid_dir)
    for g in games:
        g["status"] = art_status(grid_dir, g["appid"], names)
    return games


def find_orphans(vdf_path):
    """(grid_dir, [filenames]) — orphaned non-Steam art (appid >= NONSTEAM_MIN and
    absent from shortcuts.vdf). Regular Steam games (small appid) are left alone."""
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
    """Delete orphaned art across all given accounts (CLI mode)."""
    total = 0
    for vdf in sorted(vdf_files):
        uid = vdf.split(os.sep)[-3]
        grid_dir, orphans = find_orphans(vdf)
        print("\n=== Account %s: orphaned files: %d ===" % (uid, len(orphans)))
        for fn in orphans:
            path = os.path.join(grid_dir, fn)
            if dry_run:
                print("   DRY  delete -> %s" % fn)
            else:
                try:
                    os.remove(path)
                    print("   deleted -> %s" % fn)
                except OSError as e:
                    print("   FAIL %s (%s)" % (fn, e))
            total += 1
    print("\n--- Cleanup: %s %d file(s) ---" % ("would remove" if dry_run else "removed", total))
