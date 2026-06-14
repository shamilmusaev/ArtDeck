#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
steam_art.py — CLI для движка steam.
Подтягивает арты (обложку, баннер, hero, logo, icon) для non-Steam игр из
SteamGridDB и кладёт их в Steam (userdata\\<uid>\\config\\grid).

Зачем: при добавлении любой игры в Steam как non-Steam ярлыка (ручное добавление,
эмуляторы, сторонние лаунчеры) Steam часто не получает вертикальную обложку
600x900 — в библиотеке остаётся серая заглушка. Этот инструмент дозаливает
недостающие изображения, не трогая то, что уже есть.

Не аффилировано с Valve или SteamGridDB.

Запуск:
    python steam_art.py                  # все аккаунты, все недостающие арты
    python steam_art.py --dry-run        # показать план, ничего не качая
    python steam_art.py --account 11111111
    python steam_art.py --types cover    # только обложки
    python steam_art.py --force          # перезаписать существующие
    python steam_art.py --clean          # удалить осиротевшие арты

API-ключ SteamGridDB: env STEAMGRIDDB_API_KEY, файл steam_art.key рядом со
скриптом, либо флаг --api-key.
"""
import argparse
import glob
import os
import sys
import time

import steam as engine


def process_game(game, grid_dir, types, api_key, force, dry_run, stats):
    name = game["name"]
    appid = game["appid"]
    print("  - %s  (appid %d)" % (engine.clean_name(name), appid))

    needed = []
    for t in types:
        cfg = engine.ART_TYPES[t]
        ex = engine.existing_art(grid_dir, appid, cfg["suffix"])
        if ex and not force:
            print("      %-7s SKIP (есть: %s)" % (t, os.path.basename(ex)))
            stats["skip"] += 1
        else:
            needed.append(t)
    if not needed:
        return

    try:
        game_id, matched = engine.search_game_id(name, api_key)
    except engine.SGDBAuthError:
        raise
    except engine.SGDBError as e:
        print("      -> ошибка поиска (%s), пропуск" % e)
        stats["fail"] += len(needed)
        return
    if game_id is None:
        print("      -> не найдено на SteamGridDB, пропуск")
        stats["notfound"] += len(needed)
        return
    print("      -> SteamGridDB: %s (id %d)" % (matched, game_id))

    for t in needed:
        cfg = engine.ART_TYPES[t]
        try:
            url = engine.fetch_art_url(game_id, cfg, api_key)
        except engine.SGDBAuthError:
            raise
        except engine.SGDBError as e:
            print("      %-7s FAIL (%s)" % (t, e))
            stats["fail"] += 1
            continue
        if not url:
            print("      %-7s нет арта в базе" % t)
            stats["notfound"] += 1
            continue
        if dry_run:
            print("      %-7s DRY  -> appid %d, %s" % (t, appid, t))
            stats["would"] += 1
            continue
        try:
            dest = engine.apply_art(grid_dir, appid, t, url)
            print("      %-7s OK   -> %s" % (t, os.path.basename(dest)))
            stats["ok"] += 1
        except Exception as e:
            print("      %-7s FAIL (%s)" % (t, e))
            stats["fail"] += 1
        time.sleep(0.2)


def main():
    ap = argparse.ArgumentParser(description="Авто-загрузка артов для non-Steam игр из SteamGridDB.")
    ap.add_argument("--api-key", help="API-ключ SteamGridDB")
    ap.add_argument("--steam-path", help="Путь к папке Steam")
    ap.add_argument("--account", help="Только этот userdata-аккаунт (uid)")
    ap.add_argument("--types", default=",".join(engine.ART_TYPES.keys()),
                    help="Через запятую: %s" % ", ".join(engine.ART_TYPES.keys()))
    ap.add_argument("--force", action="store_true", help="Перезаписать существующие арты")
    ap.add_argument("--dry-run", action="store_true", help="Только показать план")
    ap.add_argument("--clean", action="store_true", help="Удалить осиротевшие арты")
    args = ap.parse_args()

    steam_path = engine.find_steam_path(args.steam_path)
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

    if args.clean:
        print("Режим очистки осиротевших артов%s" % ("  [DRY-RUN]" if args.dry_run else ""))
        engine.clean_orphans(vdf_files, args.dry_run)
        return 0

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    bad = [t for t in types if t not in engine.ART_TYPES]
    if bad:
        print("Неизвестные типы артов: %s. Доступно: %s" % (", ".join(bad), ", ".join(engine.ART_TYPES)))
        return 2

    api_key = engine.load_api_key(args.api_key)
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
        games = engine.load_shortcuts(vdf)
        print("\n=== Аккаунт %s: %d игр ===" % (uid, len(games)))
        if not games:
            continue
        if not args.dry_run:
            os.makedirs(grid_dir, exist_ok=True)
        for game in games:
            try:
                process_game(game, grid_dir, types, api_key, args.force, args.dry_run, stats)
            except engine.SGDBAuthError as e:
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
