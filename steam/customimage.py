# -*- coding: utf-8 -*-
"""Регистрация кастомного арта в кэше нового клиента Steam.

В свежих версиях Steam мало положить файл в config\\grid — клиент смотрит в
userdata\\<uid>\\config\\librarycache\\<appid>.json, запись "customimage".
Без неё анимированные обложки показываются статикой (а иногда арт игнорируется).
Эта функция дописывает/обновляет запись, сохраняя остальные (achievements и т.п.) —
ровно то, что делает родной «Set Custom Artwork» в Steam."""
import json
import os

# Значение по умолчанию (позиция лого на hero — как пишет сам Steam).
_DEFAULT_DATA = {
    "nVersion": 1,
    "logoPosition": {"pinnedPosition": "BottomLeft", "nWidthPct": 50.0, "nHeightPct": 50.0},
}


def librarycache_json(steam_path, uid, appid):
    return os.path.join(steam_path, "userdata", str(uid), "config",
                        "librarycache", "%d.json" % int(appid))


def register_custom_image(steam_path, uid, appid):
    """Гарантирует наличие непустой записи customimage в librarycache/<appid>.json.
    Сохраняет уже существующий customimage.data (например, позицию лого) и прочие
    записи. Возвращает путь к json. Тихо игнорирует, если запись уже корректна."""
    p = librarycache_json(steam_path, uid, appid)

    entries = []
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as f:
                entries = json.load(f)
            if not isinstance(entries, list):
                entries = []
        except Exception:
            entries = []

    existing_data = None
    rest = []
    for item in entries:
        if (isinstance(item, list) and len(item) == 2 and item[0] == "customimage"):
            val = item[1] if isinstance(item[1], dict) else {}
            d = val.get("data")
            if isinstance(d, dict) and d:
                existing_data = d  # сохраняем уже выставленную позицию лого и пр.
            continue  # пересоберём запись ниже
        rest.append(item)

    data = existing_data if existing_data is not None else dict(_DEFAULT_DATA)
    rest.append(["customimage", {"version": 1, "data": data}])

    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rest, f, ensure_ascii=False)
    os.replace(tmp, p)
    return p
