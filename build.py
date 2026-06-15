# -*- coding: utf-8 -*-
"""Build ArtDeck into a single .exe with PyInstaller.

Run:  python build.py   (or run_build.bat)

PyInstaller is a dev dependency; it isn't part of the engine/app. The target
machine needs the Edge WebView2 runtime (built into Windows 11). web/ goes into
the bundle; artdeck.key is created next to the .exe on first key entry (not
bundled).

If --onefile is problematic (pywebview/pythonnet), set ONEDIR=True below: it
builds a dist/ArtDeck/ folder with the .exe inside (more reliable, but not a
single file)."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ONEDIR = False  # True -> build into a folder (fallback if --onefile misbehaves)


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found — installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    sep = ";" if os.name == "nt" else ":"
    args = [
        sys.executable, "-m", "PyInstaller",
        "artdeck_app.py",
        "--name", "ArtDeck",
        "--windowed",
        "--icon", os.path.join("assets", "artdeck.ico"),
        "--add-data", "web%sweb" % sep,
        "--collect-submodules", "webview",   # pywebview platform backends
        "--noconfirm", "--clean",
    ]
    args.append("--onedir" if ONEDIR else "--onefile")

    print(">>", " ".join(args))
    subprocess.check_call(args, cwd=HERE)

    exe = os.path.join(HERE, "dist", "ArtDeck.exe") if not ONEDIR \
        else os.path.join(HERE, "dist", "ArtDeck", "ArtDeck.exe")
    print("\n=== Done ===")
    print("exe:", exe if os.path.isfile(exe) else "(not found — see the PyInstaller log above)")
    print("Run it — the ArtDeck window opens. artdeck.key appears next to it on key entry.")


if __name__ == "__main__":
    main()
