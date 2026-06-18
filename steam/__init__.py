# -*- coding: utf-8 -*-
"""steam: the art-fetching engine. `import steam as engine` exposes the public
interface used by both the CLI and the GUI server."""
from steam.paths import (
    APP_DIR, find_steam_path, load_api_key, save_api_key,
    list_accounts, account_paths,
)
from steam.vdf import parse_binary_vdf, get_ci, parse_text_vdf
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
from steam.icons import steam_game_image, game_icon_path
from steam.customimage import register_custom_image
from steam.verify import verify_applied, valid_image
from steam.official import official_art, official_arts
from steam.vdf_write import read_shortcuts_map, write_shortcuts
from steam.shortcuts import append_shortcuts, game_appid
from steam.launchers import detect_all
from steam import steamproc

__all__ = [
    "APP_DIR", "find_steam_path", "load_api_key", "save_api_key",
    "list_accounts", "account_paths", "parse_binary_vdf", "get_ci", "parse_text_vdf",
    "API_BASE", "SGDBError", "SGDBAuthError", "api_get", "clean_name",
    "search_game_id", "search_games", "list_arts_raw", "download",
    "ART_TYPES", "ART_EXTS", "existing_art", "art_status", "apply_art",
    "list_arts", "fetch_art_url", "revert_art", "NONSTEAM_MIN", "compute_legacy_appid",
    "load_shortcuts", "list_games", "find_orphans", "clean_orphans",
    "STEAM_TOOL_APPIDS", "list_libraries", "load_installed", "installed_games",
    "account_steamid64", "load_users", "account_name", "account_avatar_path",
    "account_infos", "steam_game_image", "game_icon_path",
    "register_custom_image", "verify_applied", "valid_image",
    "official_art", "official_arts",
    "read_shortcuts_map", "write_shortcuts", "append_shortcuts", "game_appid",
    "detect_all", "steamproc",
]
