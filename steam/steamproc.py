# -*- coding: utf-8 -*-
"""Detect, gracefully stop, and relaunch the Steam client.

shortcuts.vdf must not be written while Steam runs - Steam keeps an in-memory
copy and rewrites the file on exit, which would drop our new shortcuts. So the
import flow shuts Steam down first and relaunches it after the write."""
import os
import subprocess
import time

# Suppress the console window that would flash when spawning child processes.
# subprocess.CREATE_NO_WINDOW was added in Python 3.7 but is Windows-only;
# the getattr fallback keeps the constant defined on all platforms.
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def is_running(runner=subprocess.run):
    """True if a steam.exe process is running (via tasklist)."""
    try:
        out = runner(["tasklist", "/FI", "IMAGENAME eq steam.exe", "/NH"],
                     capture_output=True, text=True, timeout=10,
                     creationflags=CREATE_NO_WINDOW)
    except Exception:
        return False
    return "steam.exe" in (getattr(out, "stdout", "") or "").lower()


def shutdown(steam_path, runner=subprocess.run, sleep=time.sleep, check=None):
    """Ask Steam to exit, then wait up to ~20s. Returns True once it has gone."""
    exe = os.path.join(steam_path, "steam.exe")
    try:
        runner([exe, "-shutdown"], timeout=10, creationflags=CREATE_NO_WINDOW)
    except Exception:
        return False
    is_up = check or is_running
    for _ in range(20):
        if not is_up():
            return True
        sleep(1)
    return not is_up()


def launch(steam_path, runner=subprocess.Popen):
    """Start Steam. Returns True if the process was spawned."""
    try:
        runner([os.path.join(steam_path, "steam.exe")],
               creationflags=CREATE_NO_WINDOW)
        return True
    except Exception:
        return False
