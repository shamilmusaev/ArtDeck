# -*- coding: utf-8 -*-
"""Detect installed GOG Galaxy games from the Windows registry, cross-checked
against the Galaxy 2.0 SQLite database so phantom registry entries are dropped."""
import glob
import os
import sqlite3

GOG_KEY = r"SOFTWARE\WOW6432Node\GOG.com\Games"

_DEFAULT_DB = os.path.join(
    os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
    "GOG.com", "Galaxy", "storage", "galaxy-2.0.db",
)


def installed_product_ids(db_path=None):
    """Return a set of int productIds from the Galaxy InstalledBaseProducts table.

    Returns None if the database file is absent or any sqlite error occurs so
    callers can fall back gracefully."""
    path = db_path if db_path is not None else _DEFAULT_DB
    if not os.path.isfile(path):
        return None
    conn = None
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        cur = conn.execute("select productId from InstalledBaseProducts")
        return {int(row[0]) for row in cur.fetchall()}
    except Exception:
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _registry_reader():
    """Yield a value-dict per game subkey under GOG_KEY (real registry).

    Each dict includes '_id' (the subkey name, which is the GOG productId)."""
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
                        vals["_id"] = sub
                        rows.append(vals)
                except OSError:
                    continue
        return rows
    return read


def detect(reader=None, installed_ids=_DEFAULT_DB):
    """Return a list of game dicts (keys: name, exe, start_dir, launcher='gog').

    reader() returns raw registry value dicts (with '_id') and is injectable for
    tests. installed_ids can be a set of int productIds, None (fall back to the
    goggame-*.info marker check), or the sentinel _DEFAULT_DB (resolve from the
    Galaxy database at the default path)."""
    read = reader or _registry_reader()

    # Resolve the default sentinel: load from the Galaxy DB.
    if installed_ids is _DEFAULT_DB:
        installed_ids = installed_product_ids()

    games = []
    for vals in read():
        name = vals.get("gameName") or ""
        path = vals.get("path") or ""
        exe = vals.get("exe") or vals.get("exeFile") or ""
        if not (name and path and exe):
            continue
        if not os.path.isabs(exe):
            exe = os.path.normpath(os.path.join(path, exe))
        if not os.path.isfile(exe):
            continue
        if installed_ids is not None:
            # Galaxy DB is available: keep only entries whose subkey id is in it.
            raw_id = vals.get("_id", "")
            try:
                pid = int(raw_id)
            except (ValueError, TypeError):
                continue
            if pid not in installed_ids:
                continue
        else:
            # No Galaxy DB: fall back to the goggame-*.info marker heuristic.
            # Genuine GOG-Galaxy installs always have a goggame-*.info marker file.
            # Registry entries without this file are phantom/non-GOG entries.
            if not glob.glob(os.path.join(glob.escape(path), "goggame-*.info")):
                continue
        games.append({"name": name, "exe": exe, "start_dir": path, "launcher": "gog"})
    return games
