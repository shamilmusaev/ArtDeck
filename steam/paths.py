# -*- coding: utf-8 -*-
"""Locating Steam, the API key, and per-account paths."""
import glob
import os
import sys

# Application directory = where artdeck_cli.py / the .exe lives (NOT inside the
# steam/ package), so artdeck.key sits next to the app. In a PyInstaller build
# this is the folder containing the .exe, not the temporary _MEIPASS dir.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_STEAM_PATHS = [
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
]


def load_api_key(cli_key):
    """API key, in priority order: cli_key -> env STEAMGRIDDB_API_KEY -> artdeck.key in APP_DIR."""
    if cli_key:
        return cli_key.strip()
    env = os.environ.get("STEAMGRIDDB_API_KEY")
    if env:
        return env.strip()
    key_file = os.path.join(APP_DIR, "artdeck.key")
    if os.path.isfile(key_file):
        with open(key_file, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    return None


def save_api_key(key):
    """Persist the SteamGridDB key to APP_DIR — the same place load_api_key reads.
    Writing elsewhere (e.g. the script dir, which is a temp dir in a frozen build)
    means the key silently fails to persist."""
    with open(os.path.join(APP_DIR, "artdeck.key"), "w", encoding="utf-8") as f:
        f.write((key or "").strip())


def find_steam_path(cli_path):
    if cli_path:
        return cli_path
    try:
        import winreg
        candidates = [
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ]
        for root, sub, val in candidates:
            try:
                with winreg.OpenKey(root, sub) as k:
                    p, _ = winreg.QueryValueEx(k, val)
                    if p and os.path.isdir(p):
                        return os.path.normpath(p)
            except OSError:
                continue
    except ImportError:
        pass
    for p in DEFAULT_STEAM_PATHS:
        if os.path.isdir(p):
            return p
    return None


def list_accounts(steam_path):
    """userdata account ids (uid) that have a shortcuts.vdf."""
    userdata = os.path.join(steam_path, "userdata")
    out = []
    for vdf in sorted(glob.glob(os.path.join(userdata, "*", "config", "shortcuts.vdf"))):
        uid = os.path.basename(os.path.dirname(os.path.dirname(vdf)))
        if uid.isdigit():  # skip stray non-account folders (int(uid) is used downstream)
            out.append(uid)
    return out


def account_paths(steam_path, uid):
    """Return (vdf_path, grid_dir) for an account."""
    base = os.path.join(steam_path, "userdata", uid, "config")
    return os.path.join(base, "shortcuts.vdf"), os.path.join(base, "grid")
