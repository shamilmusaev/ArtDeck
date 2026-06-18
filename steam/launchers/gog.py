# -*- coding: utf-8 -*-
"""Detect installed GOG Galaxy games from the Windows registry.

GOG records each installed game under HKLM\\SOFTWARE\\WOW6432Node\\GOG.com\\Games
\\<id> with gameName / path / exe. Registry keeps this stdlib-only (no SQLite)."""
import glob
import os

GOG_KEY = r"SOFTWARE\WOW6432Node\GOG.com\Games"


def _registry_reader():
    """Yield a value-dict per game subkey under GOG_KEY (real registry)."""
    import winreg

    def read():
        rows = []
        try:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, GOG_KEY)
        except OSError:
            return rows
        with root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(root, sub) as k:
                        vals, j = {}, 0
                        while True:
                            try:
                                n, v, _ = winreg.EnumValue(k, j)
                            except OSError:
                                break
                            vals[n] = v
                            j += 1
                        rows.append(vals)
                except OSError:
                    continue
        return rows
    return read


def detect(reader=None):
    """Return a list of game dicts (keys: name, exe, start_dir, launcher='gog'). reader() yields raw registry value dicts and is injectable for tests."""
    read = reader or _registry_reader()
    games = []
    for vals in read():
        name = vals.get("gameName") or ""
        path = vals.get("path") or ""
        exe = vals.get("exe") or vals.get("exeFile") or ""
        if not (name and path and exe):
            continue
        if not os.path.isabs(exe):
            exe = os.path.normpath(os.path.join(path, exe))
        # Genuine GOG-Galaxy installs always have a goggame-*.info marker file.
        # Registry entries without this file are phantom/non-GOG entries.
        if not os.path.isfile(exe):
            continue
        if not glob.glob(os.path.join(glob.escape(path), "goggame-*.info")):
            continue
        games.append({"name": name, "exe": exe, "start_dir": path, "launcher": "gog"})
    return games
