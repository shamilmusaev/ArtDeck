#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
steam_art.py
============
Автоматически подтягивает арты (обложку, баннер, hero, logo, icon) для non-Steam игр
из SteamGridDB и кладёт их в Steam (userdata\\<uid>\\config\\grid).

Зачем: Hydra Launcher при добавлении игры в Steam передаёт hero/logo/баннер, но НЕ
передаёт «Основное изображение» (вертикальную обложку 600x900). Этот скрипт дозаливает
недостающее, не трогая то, что уже есть.

Запуск:
    python steam_art.py                  # все аккаунты, все недостающие арты
    python steam_art.py --dry-run        # показать, что бы сделал, ничего не качая
    python steam_art.py --account 11111111
    python steam_art.py --types cover    # только обложки
    python steam_art.py --force          # перезаписать существующие

API-ключ SteamGridDB (бесплатный, https://www.steamgriddb.com -> Preferences -> API):
    - переменная окружения STEAMGRIDDB_API_KEY, либо
    - файл steam_art.key рядом со скриптом (одна строка), либо
    - флаг --api-key <KEY>
"""

import argparse
import glob
import json
import os
import re
import struct
import sys
import time
import zlib
from urllib import request, parse, error

API_BASE = "https://www.steamgriddb.com/api/v2"

# Описание типов артов. suffix — то, что приписывается к <appid> в имени файла.
# endpoint — раздел API SteamGridDB. params — query-параметры запроса списка.
ART_TYPES = {
    "cover":  {"endpoint": "grids",  "suffix": "p",     "params": {"dimensions": "600x900"}},
    "banner": {"endpoint": "grids",  "suffix": "",      "params": {"dimensions": "460x215,920x430"}},
    "hero":   {"endpoint": "heroes", "suffix": "_hero", "params": {}},
    "logo":   {"endpoint": "logos",  "suffix": "_logo", "params": {}},
    "icon":   {"endpoint": "icons",  "suffix": "_icon", "params": {}},
}

DEFAULT_STEAM_PATHS = [
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
]


# --------------------------------------------------------------------------- #
# Конфиг / ключ / путь к Steam
# --------------------------------------------------------------------------- #
def load_api_key(cli_key):
    if cli_key:
        return cli_key.strip()
    env = os.environ.get("STEAMGRIDDB_API_KEY")
    if env:
        return env.strip()
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "steam_art.key")
    if os.path.isfile(key_file):
        with open(key_file, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    return None


def find_steam_path(cli_path):
    if cli_path:
        return cli_path
    # Реестр (только Windows)
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


# --------------------------------------------------------------------------- #
# Парсинг бинарного shortcuts.vdf
# --------------------------------------------------------------------------- #
def parse_binary_vdf(data):
    """Разбирает бинарный VDF в dict. Типы: 0x00 map, 0x01 str, 0x02 int32, 0x08 end."""
    pos = 0

    def read_cstring():
        nonlocal pos
        end = data.index(b"\x00", pos)
        s = data[pos:end].decode("utf-8", "replace")
        pos = end + 1
        return s

    def read_map():
        nonlocal pos
        result = {}
        while True:
            t = data[pos]
            pos += 1
            if t == 0x08:           # конец map
                return result
            key = read_cstring()
            if t == 0x00:           # вложенный map
                result[key] = read_map()
            elif t == 0x01:         # строка
                result[key] = read_cstring()
            elif t == 0x02:         # int32
                result[key] = struct.unpack_from("<i", data, pos)[0]
                pos += 4
            elif t == 0x07:         # int64 (на всякий случай)
                result[key] = struct.unpack_from("<q", data, pos)[0]
                pos += 8
            else:
                raise ValueError("Неизвестный тип VDF: 0x%02x на позиции %d" % (t, pos))

    # верхний уровень: ключ "shortcuts" -> map
    t = data[pos]
    pos += 1
    read_cstring()  # "shortcuts"
    return read_map()


def get_ci(d, key):
    """Достаёт значение из dict без учёта регистра ключа."""
    kl = key.lower()
    for k, v in d.items():
        if k.lower() == kl:
            return v
    return None


def compute_legacy_appid(exe, appname):
    return zlib.crc32((exe + appname).encode("utf-8")) & 0xffffffff | 0x80000000


def load_shortcuts(vdf_path):
    """Возвращает список словарей: {appid, name, exe}."""
    with open(vdf_path, "rb") as f:
        data = f.read()
    try:
        parsed = parse_binary_vdf(data)
    except Exception as e:
        print("  [!] Не удалось разобрать %s: %s" % (vdf_path, e))
        return []
    games = []
    for _, entry in parsed.items():
        if not isinstance(entry, dict):
            continue
        name = get_ci(entry, "AppName") or get_ci(entry, "appname") or ""
        exe = get_ci(entry, "Exe") or get_ci(entry, "exe") or ""
        appid = get_ci(entry, "appid")
        if not appid:  # None или 0 -> считаем legacy CRC
            appid = compute_legacy_appid(exe, name)
        appid &= 0xffffffff  # unsigned
        if name:
            games.append({"appid": appid, "name": name, "exe": exe})
    return games


# --------------------------------------------------------------------------- #
# SteamGridDB API
# --------------------------------------------------------------------------- #
class SGDBError(Exception):
    """Временная/некритичная ошибка — пропускаем арт или игру, прогон продолжается."""
    pass


class SGDBAuthError(SGDBError):
    """Фатальная ошибка — неверный ключ. Прогон прерывается."""
    pass


def api_get(path, api_key, params=None, retries=3):
    url = API_BASE + path
    if params:
        url += "?" + parse.urlencode(params)
    req = request.Request(url, headers={
        "Authorization": "Bearer " + api_key,
        "User-Agent": "steam_art.py/1.0",
    })
    last_err = None
    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as e:
            if e.code in (401, 403):
                raise SGDBAuthError("API-ключ отклонён (HTTP %d). Проверь steam_art.key / STEAMGRIDDB_API_KEY." % e.code)
            if e.code == 404:
                return {"success": False, "data": []}
            last_err = "HTTP %d" % e.code
            if e.code not in (429, 500, 502, 503, 504):
                raise SGDBError("%s при запросе %s" % (last_err, path))
        except (error.URLError, TimeoutError, OSError) as e:
            last_err = getattr(e, "reason", e)
        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))  # backoff перед повтором
    raise SGDBError("сеть/таймаут (%s) после %d попыток" % (last_err, retries))


def clean_name(name):
    for ch in ("™", "®", "©"):  # ™ ® ©
        name = name.replace(ch, "")
    return " ".join(name.split())


def search_game_id(name, api_key):
    term = clean_name(name)
    payload = api_get("/search/autocomplete/" + parse.quote(term), api_key)
    data = payload.get("data") or []
    if not data:
        return None, None
    return data[0]["id"], data[0].get("name", term)


def fetch_art_url(game_id, art_cfg, api_key):
    params = dict(art_cfg["params"])
    params.setdefault("types", "static")
    payload = api_get("/%s/game/%d" % (art_cfg["endpoint"], game_id), api_key, params)
    data = payload.get("data") or []
    if not data:
        # запасной запрос без фильтра по размеру (на случай нестандартных размеров)
        if "dimensions" in params:
            params.pop("dimensions")
            payload = api_get("/%s/game/%d" % (art_cfg["endpoint"], game_id), api_key, params)
            data = payload.get("data") or []
    if not data:
        return None
    return data[0]["url"]


def download(url, dest):
    tmp = dest + ".tmp"
    req = request.Request(url, headers={"User-Agent": "steam_art.py/1.0"})
    with request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as f:
        f.write(resp.read())
    os.replace(tmp, dest)


# --------------------------------------------------------------------------- #
# Логика по одной игре
# --------------------------------------------------------------------------- #
def existing_art(grid_dir, appid, suffix):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(grid_dir, "%d%s%s" % (appid, suffix, ext))
        if os.path.isfile(p):
            return p
    return None


ART_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def art_status(grid_dir, appid):
    """Возвращает {art_type: путь_к_файлу|None} по всем типам артов для игры."""
    return {t: existing_art(grid_dir, appid, cfg["suffix"]) for t, cfg in ART_TYPES.items()}


# --------------------------------------------------------------------------- #
# Функции для GUI: списки вариантов вместо «первого результата»
# --------------------------------------------------------------------------- #
def search_games(name, api_key, limit=20):
    """Возвращает список кандидатов с SteamGridDB: [{id, name}, ...]."""
    term = clean_name(name)
    if not term:
        return []
    payload = api_get("/search/autocomplete/" + parse.quote(term), api_key)
    out = []
    for g in (payload.get("data") or [])[:limit]:
        out.append({"id": g["id"], "name": g.get("name", term)})
    return out


def list_arts(game_id, art_type, api_key, limit=40):
    """Возвращает список вариантов арта данного типа:
    [{url, thumb, width, height, style}, ...]. Без жёсткого фильтра по размеру —
    показываем всё, что есть (для cover ставим 600x900 в начало)."""
    cfg = ART_TYPES[art_type]
    payload = api_get("/%s/game/%d" % (cfg["endpoint"], game_id), api_key,
                      {"types": "static"})
    items = []
    for a in (payload.get("data") or []):
        items.append({
            "url": a.get("url"),
            "thumb": a.get("thumb") or a.get("url"),
            "width": a.get("width"),
            "height": a.get("height"),
            "style": a.get("style"),
        })
    if art_type == "cover":
        items.sort(key=lambda a: 0 if (a["width"], a["height"]) == (600, 900) else 1)
    return [a for a in items if a["url"]][:limit]


def apply_art(grid_dir, appid, art_type, url):
    """Качает выбранный арт в <appid><suffix><ext>, удаляя дубли других расширений
    того же типа (иначе Steam берёт случайный файл). Возвращает путь."""
    suffix = ART_TYPES[art_type]["suffix"]
    ext = os.path.splitext(parse.urlparse(url).path)[1].lower() or ".png"
    if ext not in ART_EXTS:
        ext = ".png"
    os.makedirs(grid_dir, exist_ok=True)
    for e in ART_EXTS:
        if e == ext:
            continue
        old = os.path.join(grid_dir, "%d%s%s" % (appid, suffix, e))
        if os.path.isfile(old):
            try:
                os.remove(old)
            except OSError:
                pass
    dest = os.path.join(grid_dir, "%d%s%s" % (appid, suffix, ext))
    download(url, dest)
    return dest


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


def list_games(steam_path, uid):
    """Игры аккаунта со статусом артов: [{appid, name, exe, status}, ...]."""
    vdf, grid_dir = account_paths(steam_path, uid)
    if not os.path.isfile(vdf):
        return []
    games = load_shortcuts(vdf)
    for g in games:
        g["status"] = art_status(grid_dir, g["appid"])
    return games


def process_game(game, grid_dir, types, api_key, force, dry_run, stats):
    name = game["name"]
    appid = game["appid"]
    print("  - %s  (appid %d)" % (clean_name(name), appid))

    # какие типы реально надо тянуть (нет файла или --force)
    needed = []
    for t in types:
        cfg = ART_TYPES[t]
        ex = existing_art(grid_dir, appid, cfg["suffix"])
        if ex and not force:
            print("      %-7s SKIP (есть: %s)" % (t, os.path.basename(ex)))
            stats["skip"] += 1
        else:
            needed.append(t)
    if not needed:
        return

    try:
        game_id, matched = search_game_id(name, api_key)
    except SGDBAuthError:
        raise  # неверный ключ -> прерываем весь прогон
    except SGDBError as e:
        print("      -> ошибка поиска (%s), пропуск" % e)
        stats["fail"] += len(needed)
        return
    if game_id is None:
        print("      -> не найдено на SteamGridDB, пропуск всех артов")
        stats["notfound"] += len(needed)
        return
    print("      -> SteamGridDB: %s (id %d)" % (matched, game_id))

    for t in needed:
        cfg = ART_TYPES[t]
        try:
            url = fetch_art_url(game_id, cfg, api_key)
        except SGDBAuthError:
            raise  # неверный ключ -> прерываем весь прогон
        except SGDBError as e:
            print("      %-7s FAIL (%s)" % (t, e))
            stats["fail"] += 1
            continue
        if not url:
            print("      %-7s нет арта в базе" % t)
            stats["notfound"] += 1
            continue
        ext = os.path.splitext(parse.urlparse(url).path)[1].lower() or ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            ext = ".png"
        dest = os.path.join(grid_dir, "%d%s%s" % (appid, cfg["suffix"], ext))
        if dry_run:
            print("      %-7s DRY  -> %s" % (t, os.path.basename(dest)))
            stats["would"] += 1
            continue
        try:
            download(url, dest)
            print("      %-7s OK   -> %s" % (t, os.path.basename(dest)))
            stats["ok"] += 1
        except Exception as e:
            print("      %-7s FAIL (%s)" % (t, e))
            stats["fail"] += 1
        time.sleep(0.2)  # вежливость к API


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# Очистка осиротевших артов
# --------------------------------------------------------------------------- #
NONSTEAM_MIN = 0x80000000  # appid non-Steam игр всегда >= этого; обычные Steam-игры ниже


def find_orphans(vdf_path):
    """Находит осиротевшие арты для одного аккаунта.
    Возвращает (grid_dir, [имена_файлов]). Осиротевший = appid >= NONSTEAM_MIN и
    отсутствует в shortcuts.vdf. Файлы обычных Steam-игр (маленький appid) игнорирует."""
    grid_dir = os.path.join(os.path.dirname(vdf_path), "grid")
    if not os.path.isdir(grid_dir):
        return grid_dir, []
    valid = {g["appid"] for g in load_shortcuts(vdf_path)}
    orphans = []
    for fn in os.listdir(grid_dir):
        if not os.path.isfile(os.path.join(grid_dir, fn)):
            continue
        m = re.match(r"^(\d+)", fn)
        if not m:
            continue
        aid = int(m.group(1))
        if aid < NONSTEAM_MIN:   # обычная Steam-игра -> не трогаем
            continue
        if aid in valid:         # игра ещё есть -> оставляем
            continue
        orphans.append(fn)
    return grid_dir, sorted(orphans)


def clean_orphans(vdf_files, dry_run):
    """Удаляет осиротевшие арты во всех переданных аккаунтах (CLI-режим)."""
    total = 0
    for vdf in sorted(vdf_files):
        uid = vdf.split(os.sep)[-3]
        grid_dir, orphans = find_orphans(vdf)
        print("\n=== Аккаунт %s: осиротевших файлов: %d ===" % (uid, len(orphans)))
        for fn in sorted(orphans):
            path = os.path.join(grid_dir, fn)
            if dry_run:
                print("   DRY  удалить -> %s" % fn)
            else:
                try:
                    os.remove(path)
                    print("   удалён -> %s" % fn)
                except OSError as e:
                    print("   FAIL %s (%s)" % (fn, e))
            total += 1
    print("\n--- Очистка: %s %d файл(ов) ---" % ("найдено бы" if dry_run else "удалено", total))


def main():
    ap = argparse.ArgumentParser(description="Авто-загрузка артов для non-Steam игр из SteamGridDB.")
    ap.add_argument("--api-key", help="API-ключ SteamGridDB (иначе env STEAMGRIDDB_API_KEY или steam_art.key)")
    ap.add_argument("--steam-path", help="Путь к папке Steam")
    ap.add_argument("--account", help="Обработать только этот userdata-аккаунт (uid)")
    ap.add_argument("--types", default=",".join(ART_TYPES.keys()),
                    help="Через запятую: %s (по умолчанию все)" % ", ".join(ART_TYPES.keys()))
    ap.add_argument("--force", action="store_true", help="Перезаписать существующие арты")
    ap.add_argument("--dry-run", action="store_true", help="Только показать план, ничего не менять")
    ap.add_argument("--clean", action="store_true",
                    help="Удалить осиротевшие арты (игр которых больше нет в Steam) вместо скачивания")
    args = ap.parse_args()

    steam_path = find_steam_path(args.steam_path)
    if not steam_path:
        print("ОШИБКА: не нашёл Steam. Укажи путь флагом --steam-path.")
        return 2
    print("Steam: %s" % steam_path)

    userdata = os.path.join(steam_path, "userdata")
    pattern = os.path.join(userdata, args.account if args.account else "*", "config", "shortcuts.vdf")
    vdf_files = glob.glob(pattern)
    if not vdf_files:
        print("Не найдено shortcuts.vdf по пути %s" % pattern)
        return 1

    # Режим очистки: API-ключ не нужен
    if args.clean:
        print("Режим очистки осиротевших артов%s" % ("  [DRY-RUN]" if args.dry_run else ""))
        clean_orphans(vdf_files, args.dry_run)
        return 0

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    bad = [t for t in types if t not in ART_TYPES]
    if bad:
        print("Неизвестные типы артов: %s. Доступно: %s" % (", ".join(bad), ", ".join(ART_TYPES)))
        return 2

    api_key = load_api_key(args.api_key)
    if not api_key:
        print("ОШИБКА: нет API-ключа SteamGridDB.")
        print("  Создай ключ на https://www.steamgriddb.com (Preferences -> API) и:")
        print("  - положи его в файл steam_art.key рядом со скриптом, ИЛИ")
        print("  - задай переменную окружения STEAMGRIDDB_API_KEY, ИЛИ")
        print("  - передай флагом --api-key")
        return 2

    print("Типы артов: %s%s%s" % (", ".join(types),
                                  "  [FORCE]" if args.force else "",
                                  "  [DRY-RUN]" if args.dry_run else ""))

    stats = {"ok": 0, "skip": 0, "notfound": 0, "fail": 0, "would": 0}
    for vdf in sorted(vdf_files):
        uid = vdf.split(os.sep)[-3]
        grid_dir = os.path.join(os.path.dirname(vdf), "grid")
        games = load_shortcuts(vdf)
        print("\n=== Аккаунт %s: %d игр ===" % (uid, len(games)))
        if not games:
            continue
        if not args.dry_run:
            os.makedirs(grid_dir, exist_ok=True)
        for game in games:
            try:
                process_game(game, grid_dir, types, api_key, args.force, args.dry_run, stats)
            except SGDBAuthError as e:
                print("\nКРИТИЧЕСКАЯ ОШИБКА API: %s" % e)
                return 1

    print("\n--- Итог ---")
    print("  Скачано:        %d" % stats["ok"])
    print("  Пропущено(есть):%d" % stats["skip"])
    print("  Не найдено:     %d" % stats["notfound"])
    print("  Ошибки:         %d" % stats["fail"])
    if args.dry_run:
        print("  Было бы скачано:%d" % stats["would"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
        sys.exit(130)
