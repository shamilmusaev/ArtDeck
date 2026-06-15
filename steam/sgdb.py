# -*- coding: utf-8 -*-
"""SteamGridDB API client: game search, art listing, file download."""
import json
import os
import time
from urllib import request, parse, error

API_BASE = "https://www.steamgriddb.com/api/v2"


class SGDBError(Exception):
    """Transient/non-fatal error — skip the art or game and keep going."""
    pass


class SGDBAuthError(SGDBError):
    """Fatal error — the key is wrong. Abort the run."""
    pass


def api_get(path, api_key, params=None, retries=3):
    url = API_BASE + path
    if params:
        url += "?" + parse.urlencode(params)
    req = request.Request(url, headers={
        "Authorization": "Bearer " + api_key,
        "User-Agent": "ArtDeck/1.0",
    })
    last_err = None
    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
            try:
                return json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise SGDBError("invalid response from SteamGridDB for %s" % path)
        except error.HTTPError as e:
            if e.code in (401, 403):
                raise SGDBAuthError("API key rejected (HTTP %d). Check artdeck.key / STEAMGRIDDB_API_KEY." % e.code)
            if e.code == 404:
                return {"success": False, "data": []}
            last_err = "HTTP %d" % e.code
            if e.code not in (429, 500, 502, 503, 504):
                raise SGDBError("%s requesting %s" % (last_err, path))
        except (error.URLError, TimeoutError, OSError) as e:
            last_err = getattr(e, "reason", e)
        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
    raise SGDBError("network/timeout (%s) after %d attempts" % (last_err, retries))


def clean_name(name):
    for ch in ("™", "®", "©"):
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
    """Candidate list: [{id, name}, ...]."""
    term = clean_name(name)
    if not term:
        return []
    payload = api_get("/search/autocomplete/" + parse.quote(term), api_key)
    out = []
    for g in (payload.get("data") or [])[:limit]:
        out.append({"id": g["id"], "name": g.get("name", term)})
    return out


def list_arts_raw(endpoint, game_id, api_key, params):
    """Low-level art fetch: returns the raw list of dicts from data."""
    payload = api_get("/%s/game/%d" % (endpoint, game_id), api_key, params)
    return payload.get("data") or []


MAX_DOWNLOAD = 64 * 1024 * 1024   # hard cap so a hostile/huge URL can't fill RAM/disk


def download(url, dest):
    # Only fetch http(s). Without this, urllib would happily open file:// (copy a
    # local file into the grid folder) or an internal http:// address (SSRF) when
    # the URL is attacker-influenced via the API.
    scheme = parse.urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise SGDBError("refused URL scheme: %s" % (scheme or "(none)"))
    tmp = dest + ".tmp"
    req = request.Request(url, headers={"User-Agent": "ArtDeck/1.0"})
    try:
        with request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as f:
            total = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD:
                    raise SGDBError("download exceeds %d bytes" % MAX_DOWNLOAD)
                f.write(chunk)
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
