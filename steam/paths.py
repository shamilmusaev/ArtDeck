# -*- coding: utf-8 -*-
"""Поиск Steam, API-ключа и путей аккаунтов."""
import glob
import os
import sys

# Каталог приложения = там, где лежит steam_art.py / .exe (НЕ внутри пакета steam/),
# чтобы steam_art.key читался рядом с приложением. В собранном exe (PyInstaller)
# это папка с самим .exe, а не временная _MEIPASS.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_STEAM_PATHS = [
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
]


def load_api_key(cli_key):
    """API-ключ: приоритет cli_key -> env STEAMGRIDDB_API_KEY -> файл steam_art.key (в APP_DIR)."""
    if cli_key:
        return cli_key.strip()
    env = os.environ.get("STEAMGRIDDB_API_KEY")
    if env:
        return env.strip()
    key_file = os.path.join(APP_DIR, "steam_art.key")  # APP_DIR = корень проекта, рядом со steam_art.py
    if os.path.isfile(key_file):
        with open(key_file, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    return None


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
    """Список userdata-аккаунтов (uid) с shortcuts.vdf."""
    userdata = os.path.join(steam_path, "userdata")
    out = []
    for vdf in sorted(glob.glob(os.path.join(userdata, "*", "config", "shortcuts.vdf"))):
        out.append(vdf.split(os.sep)[-3])
    return out


def account_paths(steam_path, uid):
    """Возвращает (vdf_path, grid_dir) для аккаунта."""
    base = os.path.join(steam_path, "userdata", uid, "config")
    return os.path.join(base, "shortcuts.vdf"), os.path.join(base, "grid")
