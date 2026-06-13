# -*- coding: utf-8 -*-
"""Имена аккаунтов (loginusers.vdf) и аватары (avatarcache). uid <-> SteamID64."""
import os

from steam.vdf import parse_text_vdf

# База SteamID64 для индивидуальных аккаунтов: account_id + это число.
STEAMID64_BASE = 0x0110000100000000  # = 76561197960265728


def account_steamid64(uid):
    """uid (32-битный account id из userdata) -> SteamID64."""
    return int(uid) + STEAMID64_BASE


def load_users(steam_path):
    """{steamid64_str: {AccountName, PersonaName, ...}} из config/loginusers.vdf."""
    p = os.path.join(steam_path, "config", "loginusers.vdf")
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            data = parse_text_vdf(f.read())
    except Exception:
        return {}
    users = data.get("users") or data.get("Users") or {}
    return {k: v for k, v in users.items() if isinstance(v, dict)}


def account_name(steam_path, uid):
    """PersonaName аккаунта или None, если не нашли."""
    sid = str(account_steamid64(uid))
    info = load_users(steam_path).get(sid)
    if info:
        return info.get("PersonaName") or info.get("AccountName") or None
    return None


def account_avatar_path(steam_path, uid):
    """Путь к локальному аватару <steamid64>.png или None."""
    sid = str(account_steamid64(uid))
    p = os.path.join(steam_path, "config", "avatarcache", sid + ".png")
    return p if os.path.isfile(p) else None


def account_infos(steam_path, uids):
    """[{uid, name, has_avatar}] для списка uid (один проход по loginusers)."""
    users = load_users(steam_path)
    out = []
    for uid in uids:
        sid = str(account_steamid64(uid))
        info = users.get(sid) or {}
        name = info.get("PersonaName") or info.get("AccountName") or None
        avatar = os.path.join(steam_path, "config", "avatarcache", sid + ".png")
        out.append({"uid": uid, "name": name, "has_avatar": os.path.isfile(avatar)})
    return out
