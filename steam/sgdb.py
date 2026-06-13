# -*- coding: utf-8 -*-
"""Клиент SteamGridDB API: поиск игр и выборка артов, скачивание файлов."""
import json
import os
import time
from urllib import request, parse, error

API_BASE = "https://www.steamgriddb.com/api/v2"


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
            time.sleep(1.5 * (attempt + 1))
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


def search_games(name, api_key, limit=20):
    """Список кандидатов: [{id, name}, ...]."""
    term = clean_name(name)
    if not term:
        return []
    payload = api_get("/search/autocomplete/" + parse.quote(term), api_key)
    out = []
    for g in (payload.get("data") or [])[:limit]:
        out.append({"id": g["id"], "name": g.get("name", term)})
    return out


def list_arts_raw(endpoint, game_id, api_key, params):
    """Низкоуровневая выборка артов: возвращает сырой список dict из data."""
    payload = api_get("/%s/game/%d" % (endpoint, game_id), api_key, params)
    return payload.get("data") or []


def download(url, dest):
    tmp = dest + ".tmp"
    req = request.Request(url, headers={"User-Agent": "steam_art.py/1.0"})
    with request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as f:
        f.write(resp.read())
    os.replace(tmp, dest)
