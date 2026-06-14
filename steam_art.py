#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
steam_art.py — CLI for the steam engine.
Fetches art (cover, banner, hero, logo, icon) for non-Steam games from
SteamGridDB and installs it into Steam (userdata\\<uid>\\config\\grid).

Why: when a game is added to Steam as a non-Steam shortcut (manual add,
emulators, third-party launchers), Steam often gets no 600x900 vertical cover,
leaving a gray placeholder in the library. This tool fills the missing images
without touching what's already there.

Not affiliated with Valve or SteamGridDB.

Usage:
    python steam_art.py                  # all accounts, all missing art
    python steam_art.py --dry-run        # show the plan, download nothing
    python steam_art.py --account 11111111
    python steam_art.py --types cover    # covers only
    python steam_art.py --force          # overwrite existing art
    python steam_art.py --clean          # delete orphaned art

SteamGridDB API key: env STEAMGRIDDB_API_KEY, the steam_art.key file next to the
script, or the --api-key flag.
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
            print("      %-7s SKIP (have: %s)" % (t, os.path.basename(ex)))
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
        print("      -> search error (%s), skipping" % e)
        stats["fail"] += len(needed)
        return
    if game_id is None:
        print("      -> not found on SteamGridDB, skipping")
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
            print("      %-7s no art in the database" % t)
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
    ap = argparse.ArgumentParser(description="Auto-download art for non-Steam games from SteamGridDB.")
    ap.add_argument("--api-key", help="SteamGridDB API key")
    ap.add_argument("--steam-path", help="Path to the Steam folder")
    ap.add_argument("--account", help="Only this userdata account (uid)")
    ap.add_argument("--types", default=",".join(engine.ART_TYPES.keys()),
                    help="Comma-separated: %s" % ", ".join(engine.ART_TYPES.keys()))
    ap.add_argument("--force", action="store_true", help="Overwrite existing art")
    ap.add_argument("--dry-run", action="store_true", help="Show the plan only")
    ap.add_argument("--clean", action="store_true", help="Delete orphaned art")
    args = ap.parse_args()

    steam_path = engine.find_steam_path(args.steam_path)
    if not steam_path:
        print("ERROR: Steam not found. Pass the path with --steam-path.")
        return 2
    print("Steam: %s" % steam_path)

    userdata = os.path.join(steam_path, "userdata")
    pattern = os.path.join(userdata, args.account if args.account else "*", "config", "shortcuts.vdf")
    vdf_files = glob.glob(pattern)
    if not vdf_files:
        print("No shortcuts.vdf found at %s" % pattern)
        return 1

    if args.clean:
        print("Cleaning orphaned art%s" % ("  [DRY-RUN]" if args.dry_run else ""))
        engine.clean_orphans(vdf_files, args.dry_run)
        return 0

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    bad = [t for t in types if t not in engine.ART_TYPES]
    if bad:
        print("Unknown art types: %s. Available: %s" % (", ".join(bad), ", ".join(engine.ART_TYPES)))
        return 2

    api_key = engine.load_api_key(args.api_key)
    if not api_key:
        print("ERROR: no SteamGridDB API key.")
        print("  Create a key at https://www.steamgriddb.com (Preferences -> API) and:")
        print("  - put it in the steam_art.key file next to the script, OR")
        print("  - set the STEAMGRIDDB_API_KEY environment variable, OR")
        print("  - pass it with --api-key")
        return 2

    print("Art types: %s%s%s" % (", ".join(types),
                                  "  [FORCE]" if args.force else "",
                                  "  [DRY-RUN]" if args.dry_run else ""))

    stats = {"ok": 0, "skip": 0, "notfound": 0, "fail": 0, "would": 0}
    for vdf in sorted(vdf_files):
        uid = vdf.split(os.sep)[-3]
        grid_dir = os.path.join(os.path.dirname(vdf), "grid")
        games = engine.load_shortcuts(vdf)
        print("\n=== Account %s: %d games ===" % (uid, len(games)))
        if not games:
            continue
        if not args.dry_run:
            os.makedirs(grid_dir, exist_ok=True)
        for game in games:
            try:
                process_game(game, grid_dir, types, api_key, args.force, args.dry_run, stats)
            except engine.SGDBAuthError as e:
                print("\nFATAL API ERROR: %s" % e)
                return 1

    print("\n--- Summary ---")
    print("  Downloaded:     %d" % stats["ok"])
    print("  Skipped (have): %d" % stats["skip"])
    print("  Not found:      %d" % stats["notfound"])
    print("  Errors:         %d" % stats["fail"])
    if args.dry_run:
        print("  Would download: %d" % stats["would"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
