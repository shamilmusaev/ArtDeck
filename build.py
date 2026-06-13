# -*- coding: utf-8 -*-
"""Сборка ArtDeck в один .exe через PyInstaller.

Запуск:  python build.py   (или run_build.bat)

PyInstaller — dev-зависимость, в движок/приложение не входит. На целевой машине
нужен рантайм Edge WebView2 (на Windows 11 есть из коробки). web/ кладётся в бандл;
steam_art.key создаётся рядом с .exe при первом вводе ключа (в бандл не входит).

Если --onefile проблемный (pywebview/pythonnet) — раскомментируй ONEDIR=True ниже:
тогда соберётся папка dist/ArtDeck/ с .exe внутри (надёжнее, но не один файл)."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ONEDIR = False  # True -> сборка в папку (фолбэк, если --onefile капризничает)


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller не найден — ставлю…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    sep = ";" if os.name == "nt" else ":"
    args = [
        sys.executable, "-m", "PyInstaller",
        "steam_art_app.py",
        "--name", "ArtDeck",
        "--windowed",
        "--icon", os.path.join("assets", "artdeck.ico"),
        "--add-data", "web%sweb" % sep,
        "--collect-submodules", "webview",   # платформенные бэкенды pywebview
        "--noconfirm", "--clean",
    ]
    args.append("--onedir" if ONEDIR else "--onefile")

    print(">>", " ".join(args))
    subprocess.check_call(args, cwd=HERE)

    exe = os.path.join(HERE, "dist", "ArtDeck.exe") if not ONEDIR \
        else os.path.join(HERE, "dist", "ArtDeck", "ArtDeck.exe")
    print("\n=== Готово ===")
    print("exe:", exe if os.path.isfile(exe) else "(не найден — смотри лог PyInstaller выше)")
    print("Запусти его — окно ArtDeck откроется. steam_art.key появится рядом при вводе ключа.")


if __name__ == "__main__":
    main()
