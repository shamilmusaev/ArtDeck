# -*- coding: utf-8 -*-
"""Поиск локальной картинки-иконки для строки списка игр.
Steam менял раскладку librarycache между версиями, поэтому пробуем несколько мест."""
import glob
import os

# Приоритет файлов внутри appcache/librarycache/<appid>/ (новая раскладка).
# Явного «иконочного» файла там нет — берём узнаваемую мелкую обложку/лого.
STEAM_IMAGE_PRIORITY = (
    "library_600x900.jpg",
    "library_600x900_2x.jpg",
    "logo.png",
    "header.jpg",
    "library_hero.jpg",
)


def steam_game_image(steam_path, appid):
    """Лучшая доступная картинка для Steam-игры или None.
    Порядок: legacy-плоский <appid>_icon.jpg -> файлы в подпапке <appid>/ по приоритету
    -> любой не-blur .jpg/.png в подпапке (хеш-именованные ассеты)."""
    lc = os.path.join(steam_path, "appcache", "librarycache")
    legacy = os.path.join(lc, "%d_icon.jpg" % appid)
    if os.path.isfile(legacy):
        return legacy
    sub = os.path.join(lc, str(appid))
    if os.path.isdir(sub):
        for fn in STEAM_IMAGE_PRIORITY:
            p = os.path.join(sub, fn)
            if os.path.isfile(p):
                return p
        cands = sorted(glob.glob(os.path.join(sub, "*.jpg")) +
                       glob.glob(os.path.join(sub, "*.png")))
        for p in cands:
            if "_blur" not in os.path.basename(p).lower():
                return p
    return None


def game_icon_path(steam_path, game):
    """Путь к иконке для игры (любого вида) или None.
    non-Steam -> поле icon ярлыка (если файл существует); Steam -> steam_game_image."""
    if game.get("kind") == "steam":
        return steam_game_image(steam_path, game["appid"])
    icon = game.get("icon") or ""
    return icon if (icon and os.path.isfile(icon)) else None
