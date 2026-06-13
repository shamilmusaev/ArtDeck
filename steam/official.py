# -*- coding: utf-8 -*-
"""Официальный арт Steam для установленных игр (appcache\\librarycache\\<appid>\\).

Для обычных Steam-игр обложку/hero/лого/баннер кладёт сам Steam — не в нашу
grid-папку, а в свой librarycache. Это нужно, чтобы:
  - в списке показывать, что у игры арт ЕСТЬ (а не «пусто»),
  - в карточке «Текущая» показывать реальный текущий арт, а не «none»."""
import os

# Имя файла в librarycache\<appid>\ для каждого нашего типа арта.
_OFFICIAL = {
    "cover":  ("library_600x900.jpg", "library_600x900_2x.jpg"),
    "banner": ("header.jpg", "library_header.jpg"),
    "hero":   ("library_hero.jpg",),
    "logo":   ("logo.png", "logo_2x.png"),
    "icon":   (),  # в новой раскладке нет надёжного иконочного файла
}


def official_art(steam_path, appid, art_type):
    """Путь к официальному файлу Steam для (appid, тип) или None."""
    sub = os.path.join(steam_path, "appcache", "librarycache", str(appid))
    legacy = os.path.join(steam_path, "appcache", "librarycache")
    for fn in _OFFICIAL.get(art_type, ()):
        p = os.path.join(sub, fn)
        if os.path.isfile(p):
            return p
    # запасной вариант — старая плоская раскладка (<appid>_library_600x900.jpg и т.п.)
    flat = {
        "cover": "%d_library_600x900.jpg" % appid,
        "hero": "%d_library_hero.jpg" % appid,
        "logo": "%d_logo.png" % appid,
        "banner": "%d_header.jpg" % appid,
    }.get(art_type)
    if flat:
        p = os.path.join(legacy, flat)
        if os.path.isfile(p):
            return p
    return None
