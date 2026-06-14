# -*- coding: utf-8 -*-
"""Пакет steam: движок дозаливки артов. `import steam as engine` даёт тот же
публичный интерфейс, что и прежний модуль steam_art."""
from steam.paths import (
    APP_DIR, DEFAULT_STEAM_PATHS, find_steam_path, load_api_key, save_api_key,
    list_accounts, account_paths,
)
from steam.vdf import parse_binary_vdf, get_ci
from steam.sgdb import (
    API_BASE, SGDBError, SGDBAuthError, api_get, clean_name,
    search_game_id, search_games, list_arts_raw, download,
)
from steam.arts import (
    ART_TYPES, ART_EXTS, existing_art, art_status, apply_art,
    list_arts, fetch_art_url, revert_art,
)
from steam.library import (
    NONSTEAM_MIN, compute_legacy_appid, load_shortcuts, list_games,
    find_orphans, clean_orphans,
    STEAM_TOOL_APPIDS, list_libraries, load_installed, installed_games,
)
from steam.users import (
    account_steamid64, load_users, account_name, account_avatar_path, account_infos,
)
from steam.icons import STEAM_IMAGE_PRIORITY, steam_game_image, game_icon_path
from steam.vdf import parse_text_vdf
from steam.customimage import register_custom_image, librarycache_json
from steam.verify import verify_applied, valid_image
from steam.official import official_art

__all__ = [
    "APP_DIR", "DEFAULT_STEAM_PATHS", "find_steam_path", "load_api_key", "save_api_key",
    "list_accounts", "account_paths", "parse_binary_vdf", "get_ci",
    "API_BASE", "SGDBError", "SGDBAuthError", "api_get", "clean_name",
    "search_game_id", "search_games", "list_arts_raw", "download",
    "ART_TYPES", "ART_EXTS", "existing_art", "art_status", "apply_art",
    "list_arts", "fetch_art_url", "revert_art", "NONSTEAM_MIN", "compute_legacy_appid",
    "load_shortcuts", "list_games", "find_orphans", "clean_orphans",
    "STEAM_TOOL_APPIDS", "list_libraries", "load_installed", "installed_games",
    "account_steamid64", "load_users", "account_name", "account_avatar_path",
    "account_infos", "STEAM_IMAGE_PRIORITY", "steam_game_image", "game_icon_path",
    "parse_text_vdf", "register_custom_image", "librarycache_json",
    "verify_applied", "valid_image", "official_art",
]
