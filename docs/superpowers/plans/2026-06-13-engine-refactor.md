# Engine Refactor → `steam/` Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Разбить монолитный `steam_art.py` на модульный пакет `steam/` с тестовым харнессом, не меняя поведения CLI и GUI.

**Architecture:** Чистый DAG модулей без циклов: `vdf` и `paths` без зависимостей; `sgdb` (сеть) без зависимостей; `arts` → `sgdb`; `library` → `vdf`, `arts`. `steam/__init__.py` реэкспортирует публичный API, поэтому `import steam as engine` даёт тот же интерфейс, что и старый `steam_art`. `steam_art.py` становится тонкой CLI-обёрткой.

**Tech Stack:** Python 3 (stdlib-only), `unittest`, `py_compile` для проверки.

**Public API контракт (нельзя сломать — это зовёт `steam_art_app.py`):**
`find_steam_path, load_api_key, list_accounts, account_paths, list_games, clean_name, ART_TYPES, search_games, list_arts, SGDBError, SGDBAuthError, find_orphans, existing_art, load_shortcuts, art_status, search_game_id, fetch_art_url, apply_art`.

---

## Целевая структура файлов

| Файл | Содержимое (перенос из `steam_art.py`) |
|---|---|
| `steam/__init__.py` | реэкспорт всего публичного API; константа `APP_DIR` |
| `steam/vdf.py` | `parse_binary_vdf`, `get_ci` |
| `steam/paths.py` | `DEFAULT_STEAM_PATHS`, `find_steam_path`, `load_api_key`, `list_accounts`, `account_paths` |
| `steam/sgdb.py` | `API_BASE`, `SGDBError`, `SGDBAuthError`, `api_get`, `clean_name`, `search_game_id`, `search_games`, `list_arts_raw`, `download` |
| `steam/arts.py` | `ART_TYPES`, `ART_EXTS`, `existing_art`, `art_status`, `apply_art`, `list_arts`, `fetch_art_url` |
| `steam/library.py` | `NONSTEAM_MIN`, `compute_legacy_appid`, `load_shortcuts`, `list_games`, `find_orphans`, `clean_orphans` |
| `steam_art.py` | тонкая CLI-обёртка: `import steam as engine`, `process_game`, `main` (Hydra убрана из docstring) |
| `steam_art_app.py` | только меняется `import steam_art as engine` → `import steam as engine` |
| `tests/__init__.py` | пустой |
| `tests/helpers.py` | `build_shortcuts_vdf(games)` — конструктор бинарного VDF для фикстур |
| `tests/test_vdf.py`, `tests/test_paths.py`, `tests/test_sgdb.py`, `tests/test_arts.py`, `tests/test_library.py` | тесты |

**Дизайн-заметка про циклы:** `find_orphans`/`clean_orphans` живут в `library.py` (а не в `arts.py`), потому что им нужен `load_shortcuts` — так избегаем цикла `arts ↔ library`. `list_arts`/`fetch_art_url` живут в `arts.py` (им нужны `ART_TYPES`), а сетевую черновую выборку делает `sgdb.list_arts_raw`.

---

### Task 1: Пакет `steam/` + модуль `vdf.py`

**Files:**
- Create: `steam/__init__.py`
- Create: `steam/vdf.py`
- Create: `tests/__init__.py`
- Create: `tests/helpers.py`
- Test: `tests/test_vdf.py`

- [ ] **Step 1: Создать конструктор фикстур `tests/helpers.py`**

```python
# -*- coding: utf-8 -*-
"""Хелперы для тестов: сборка бинарного shortcuts.vdf в памяти."""
import struct


def _cstr(s):
    return s.encode("utf-8") + b"\x00"


def build_shortcuts_vdf(games):
    """games: список dict {appid:int, AppName:str, Exe:str}.
    Возвращает bytes в формате, который понимает parse_binary_vdf."""
    body = b""
    for i, g in enumerate(games):
        entry = b""
        entry += b"\x01" + _cstr("AppName") + _cstr(g.get("AppName", ""))
        entry += b"\x01" + _cstr("Exe") + _cstr(g.get("Exe", ""))
        if "appid" in g:
            entry += b"\x02" + _cstr("appid") + struct.pack("<I", g["appid"] & 0xffffffff)
        entry += b"\x08"  # конец вложенного map
        body += b"\x00" + _cstr(str(i)) + entry
    body += b"\x08"  # конец map shortcuts
    return b"\x00" + _cstr("shortcuts") + body
```

- [ ] **Step 2: Написать падающий тест `tests/test_vdf.py`**

```python
# -*- coding: utf-8 -*-
import unittest
from tests.helpers import build_shortcuts_vdf
from steam.vdf import parse_binary_vdf, get_ci


class VdfTest(unittest.TestCase):
    def test_parse_single_game(self):
        data = build_shortcuts_vdf([
            {"appid": 2468090731, "AppName": "Alien Isolation", "Exe": "C:\\a.exe"},
        ])
        parsed = parse_binary_vdf(data)
        entry = parsed["0"]
        self.assertEqual(get_ci(entry, "appname"), "Alien Isolation")
        self.assertEqual(get_ci(entry, "appid"), 2468090731 & 0xffffffff
                         if 2468090731 < 0x80000000 else -1826876565)

    def test_get_ci_case_insensitive(self):
        self.assertEqual(get_ci({"AppName": "X"}, "appname"), "X")
        self.assertIsNone(get_ci({"AppName": "X"}, "missing"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Запустить — убедиться, что падает**

Run: `python -m unittest tests.test_vdf -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steam.vdf'`.

- [ ] **Step 4: Создать `steam/vdf.py` (перенос из `steam_art.py:101-147`)**

```python
# -*- coding: utf-8 -*-
"""Парсинг бинарного VDF (shortcuts.vdf) + регистронезависимый доступ к dict."""
import struct


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
            if t == 0x08:
                return result
            key = read_cstring()
            if t == 0x00:
                result[key] = read_map()
            elif t == 0x01:
                result[key] = read_cstring()
            elif t == 0x02:
                result[key] = struct.unpack_from("<i", data, pos)[0]
                pos += 4
            elif t == 0x07:
                result[key] = struct.unpack_from("<q", data, pos)[0]
                pos += 8
            else:
                raise ValueError("Неизвестный тип VDF: 0x%02x на позиции %d" % (t, pos))

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
```

Создать пустые `steam/__init__.py` и `tests/__init__.py` (одна строка комментария в каждом).

- [ ] **Step 5: Запустить — убедиться, что проходит**

Run: `python -m unittest tests.test_vdf -v`
Expected: PASS (2 теста).

- [ ] **Step 6: Коммит**

```bash
git add steam/__init__.py steam/vdf.py tests/__init__.py tests/helpers.py tests/test_vdf.py
git commit -m "refactor: extract VDF parsing into steam.vdf with tests"
```

---

### Task 2: Модуль `paths.py`

**Files:**
- Create: `steam/paths.py`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Написать падающий тест `tests/test_paths.py`**

```python
# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from steam.paths import account_paths, list_accounts, load_api_key


class PathsTest(unittest.TestCase):
    def test_account_paths(self):
        vdf, grid = account_paths("C:\\Steam", "123")
        self.assertTrue(vdf.endswith(os.path.join("userdata", "123", "config", "shortcuts.vdf")))
        self.assertTrue(grid.endswith(os.path.join("userdata", "123", "config", "grid")))

    def test_list_accounts_finds_vdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = os.path.join(tmp, "userdata", "999", "config")
            os.makedirs(cfg)
            open(os.path.join(cfg, "shortcuts.vdf"), "wb").close()
            self.assertEqual(list_accounts(tmp), ["999"])

    def test_load_api_key_from_env(self):
        os.environ["STEAMGRIDDB_API_KEY"] = "  abc123  "
        try:
            self.assertEqual(load_api_key(None), "abc123")
        finally:
            del os.environ["STEAMGRIDDB_API_KEY"]


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m unittest tests.test_paths -v`
Expected: FAIL — `No module named 'steam.paths'`.

- [ ] **Step 3: Создать `steam/paths.py` (перенос из `steam_art.py:49-95, 58-68, 335-347`)**

```python
# -*- coding: utf-8 -*-
"""Поиск Steam, API-ключа и путей аккаунтов."""
import glob
import os

# Каталог приложения = там, где лежит steam_art.py / exe (НЕ внутри пакета steam/),
# чтобы steam_art.key читался рядом со скриптом как раньше.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_STEAM_PATHS = [
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
]


def load_api_key(cli_key):
    if cli_key:
        return cli_key.strip()
    env = os.environ.get("STEAMGRIDDB_API_KEY")
    if env:
        return env.strip()
    key_file = os.path.join(APP_DIR, "steam_art.key")
    if os.path.isfile(key_file):
        with open(key_file, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    return None


def find_steam_path(cli_path):
    if cli_path:
        return cli_path
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
```

**Важно:** `APP_DIR` поднимается на уровень выше пакета (`dirname(dirname(__file__))`), поэтому `steam_art.key` ищется рядом со `steam_art.py`, а не внутри `steam/`.

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `python -m unittest tests.test_paths -v`
Expected: PASS (3 теста).

- [ ] **Step 5: Коммит**

```bash
git add steam/paths.py tests/test_paths.py
git commit -m "refactor: extract Steam path/key discovery into steam.paths"
```

---

### Task 3: Модуль `sgdb.py`

**Files:**
- Create: `steam/sgdb.py`
- Test: `tests/test_sgdb.py`

- [ ] **Step 1: Написать падающий тест `tests/test_sgdb.py`**

```python
# -*- coding: utf-8 -*-
import unittest
from urllib import error
import io
from steam import sgdb
from steam.sgdb import clean_name, api_get, SGDBError, SGDBAuthError


class CleanNameTest(unittest.TestCase):
    def test_strips_trademark_and_spaces(self):
        self.assertEqual(clean_name("Game™   II  "), "Game II")


class ApiGetTest(unittest.TestCase):
    def test_auth_error_raises(self):
        def fake_urlopen(req, timeout=0):
            raise error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b""))
        old = sgdb.request.urlopen
        sgdb.request.urlopen = fake_urlopen
        try:
            with self.assertRaises(SGDBAuthError):
                api_get("/x", "key")
        finally:
            sgdb.request.urlopen = old

    def test_404_returns_empty(self):
        def fake_urlopen(req, timeout=0):
            raise error.HTTPError(req.full_url, 404, "Not Found", {}, io.BytesIO(b""))
        old = sgdb.request.urlopen
        sgdb.request.urlopen = fake_urlopen
        try:
            self.assertEqual(api_get("/x", "key"), {"success": False, "data": []})
        finally:
            sgdb.request.urlopen = old


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m unittest tests.test_sgdb -v`
Expected: FAIL — `No module named 'steam.sgdb'`.

- [ ] **Step 3: Создать `steam/sgdb.py` (перенос из `steam_art.py:37, 181-255, 280-310`)**

```python
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
    for ch in ("™", "®", "©"):  # TM R C
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
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `python -m unittest tests.test_sgdb -v`
Expected: PASS (3 теста).

- [ ] **Step 5: Коммит**

```bash
git add steam/sgdb.py tests/test_sgdb.py
git commit -m "refactor: extract SteamGridDB client into steam.sgdb"
```

---

### Task 4: Модуль `arts.py`

**Files:**
- Create: `steam/arts.py`
- Test: `tests/test_arts.py`

- [ ] **Step 1: Написать падающий тест `tests/test_arts.py`**

```python
# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from steam import arts
from steam.arts import existing_art, art_status, apply_art, ART_TYPES


class ArtsTest(unittest.TestCase):
    def test_existing_art_finds_file(self):
        with tempfile.TemporaryDirectory() as grid:
            open(os.path.join(grid, "100p.png"), "wb").close()
            self.assertTrue(existing_art(grid, 100, "p").endswith("100p.png"))
            self.assertIsNone(existing_art(grid, 100, "_hero"))

    def test_art_status_all_types(self):
        with tempfile.TemporaryDirectory() as grid:
            st = art_status(grid, 100)
            self.assertEqual(set(st.keys()), set(ART_TYPES.keys()))
            self.assertTrue(all(v is None for v in st.values()))

    def test_apply_art_removes_other_ext(self):
        with tempfile.TemporaryDirectory() as grid:
            open(os.path.join(grid, "100p.jpg"), "wb").close()

            def fake_download(url, dest):
                open(dest, "wb").close()
            old = arts.download
            arts.download = fake_download
            try:
                dest = apply_art(grid, 100, "cover", "http://x/y.png")
            finally:
                arts.download = old
            self.assertTrue(dest.endswith("100p.png"))
            self.assertFalse(os.path.isfile(os.path.join(grid, "100p.jpg")))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m unittest tests.test_arts -v`
Expected: FAIL — `No module named 'steam.arts'`.

- [ ] **Step 3: Создать `steam/arts.py` (перенос из `steam_art.py:41-47, 234-247, 261-332`)**

```python
# -*- coding: utf-8 -*-
"""Логика артов: типы, статус, применение, выборка вариантов для GUI."""
import os
from urllib import parse

from steam.sgdb import list_arts_raw, download

# Описание типов артов. suffix — то, что приписывается к <appid> в имени файла.
ART_TYPES = {
    "cover":  {"endpoint": "grids",  "suffix": "p",     "params": {"dimensions": "600x900"}},
    "banner": {"endpoint": "grids",  "suffix": "",      "params": {"dimensions": "460x215,920x430"}},
    "hero":   {"endpoint": "heroes", "suffix": "_hero", "params": {}},
    "logo":   {"endpoint": "logos",  "suffix": "_logo", "params": {}},
    "icon":   {"endpoint": "icons",  "suffix": "_icon", "params": {}},
}

ART_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def existing_art(grid_dir, appid, suffix):
    for ext in ART_EXTS:
        p = os.path.join(grid_dir, "%d%s%s" % (appid, suffix, ext))
        if os.path.isfile(p):
            return p
    return None


def art_status(grid_dir, appid):
    """{art_type: путь|None} по всем типам артов для игры."""
    return {t: existing_art(grid_dir, appid, cfg["suffix"]) for t, cfg in ART_TYPES.items()}


def fetch_art_url(game_id, art_cfg, api_key):
    """Первый подходящий URL арта (авто-режим)."""
    params = dict(art_cfg["params"])
    params.setdefault("types", "static")
    data = list_arts_raw(art_cfg["endpoint"], game_id, api_key, params)
    if not data and "dimensions" in params:
        params.pop("dimensions")
        data = list_arts_raw(art_cfg["endpoint"], game_id, api_key, params)
    if not data:
        return None
    return data[0]["url"]


def list_arts(game_id, art_type, api_key, limit=40):
    """Список вариантов арта данного типа: [{url, thumb, width, height, style}, ...]."""
    cfg = ART_TYPES[art_type]
    data = list_arts_raw(cfg["endpoint"], game_id, api_key, {"types": "static"})
    items = []
    for a in data:
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
    """Качает арт в <appid><suffix><ext>, удаляя дубли других расширений того же типа."""
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
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `python -m unittest tests.test_arts -v`
Expected: PASS (3 теста).

- [ ] **Step 5: Коммит**

```bash
git add steam/arts.py tests/test_arts.py
git commit -m "refactor: extract art logic into steam.arts"
```

---

### Task 5: Модуль `library.py`

**Files:**
- Create: `steam/library.py`
- Test: `tests/test_library.py`

- [ ] **Step 1: Написать падающий тест `tests/test_library.py`**

```python
# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from tests.helpers import build_shortcuts_vdf
from steam.library import load_shortcuts, find_orphans, compute_legacy_appid, NONSTEAM_MIN


class LibraryTest(unittest.TestCase):
    def test_load_shortcuts(self):
        with tempfile.TemporaryDirectory() as tmp:
            vdf = os.path.join(tmp, "shortcuts.vdf")
            with open(vdf, "wb") as f:
                f.write(build_shortcuts_vdf([
                    {"appid": 2468090731, "AppName": "Alien", "Exe": "a.exe"},
                ]))
            games = load_shortcuts(vdf)
            self.assertEqual(len(games), 1)
            self.assertEqual(games[0]["name"], "Alien")
            self.assertEqual(games[0]["appid"], 2468090731)

    def test_legacy_appid_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            vdf = os.path.join(tmp, "shortcuts.vdf")
            with open(vdf, "wb") as f:
                f.write(build_shortcuts_vdf([{"AppName": "NoId", "Exe": "x.exe"}]))
            games = load_shortcuts(vdf)
            self.assertEqual(games[0]["appid"], compute_legacy_appid("x.exe", "NoId"))
            self.assertGreaterEqual(games[0]["appid"], NONSTEAM_MIN)

    def test_find_orphans_only_nonsteam(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = tmp
            grid = os.path.join(cfg, "grid")
            os.makedirs(grid)
            # осиротевший non-Steam арт
            open(os.path.join(grid, "%dp.png" % (NONSTEAM_MIN + 5)), "wb").close()
            # обычная Steam-игра — не трогаем
            open(os.path.join(grid, "440p.png"), "wb").close()
            vdf = os.path.join(cfg, "shortcuts.vdf")
            with open(vdf, "wb") as f:
                f.write(build_shortcuts_vdf([]))
            _, orph = find_orphans(vdf)
            self.assertIn("%dp.png" % (NONSTEAM_MIN + 5), orph)
            self.assertNotIn("440p.png", orph)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m unittest tests.test_library -v`
Expected: FAIL — `No module named 'steam.library'`.

- [ ] **Step 3: Создать `steam/library.py` (перенос из `steam_art.py:150-175, 350-358, 431-476`)**

```python
# -*- coding: utf-8 -*-
"""Источники игр аккаунта: non-Steam ярлыки + осиротевшие арты."""
import os
import re
import zlib

from steam.vdf import parse_binary_vdf, get_ci
from steam.arts import art_status
from steam.paths import account_paths

NONSTEAM_MIN = 0x80000000  # appid non-Steam игр всегда >= этого


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
        if not appid:
            appid = compute_legacy_appid(exe, name)
        appid &= 0xffffffff
        if name:
            games.append({"appid": appid, "name": name, "exe": exe})
    return games


def list_games(steam_path, uid):
    """Игры аккаунта со статусом артов: [{appid, name, exe, status}, ...]."""
    vdf, grid_dir = account_paths(steam_path, uid)
    if not os.path.isfile(vdf):
        return []
    games = load_shortcuts(vdf)
    for g in games:
        g["status"] = art_status(grid_dir, g["appid"])
    return games


def find_orphans(vdf_path):
    """(grid_dir, [имена_файлов]) — осиротевшие арты non-Steam игр (appid >= NONSTEAM_MIN
    и отсутствует в shortcuts.vdf). Файлы обычных Steam-игр (маленький appid) не трогает."""
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
        if aid < NONSTEAM_MIN or aid in valid:
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
```

- [ ] **Step 4: Запустить — убедиться, что проходит**

Run: `python -m unittest tests.test_library -v`
Expected: PASS (3 теста).

- [ ] **Step 5: Коммит**

```bash
git add steam/library.py tests/test_library.py
git commit -m "refactor: extract game sources/orphans into steam.library"
```

---

### Task 6: Фасад `steam/__init__.py` + тонкий CLI `steam_art.py`

**Files:**
- Modify: `steam/__init__.py`
- Modify: `steam_art.py` (полностью переписать как CLI-обёртку)
- Modify: `steam_art_app.py:27`

- [ ] **Step 1: Заполнить `steam/__init__.py` реэкспортом публичного API**

```python
# -*- coding: utf-8 -*-
"""Пакет steam: движок дозаливки артов. `import steam as engine` даёт тот же
публичный интерфейс, что и прежний модуль steam_art."""
from steam.paths import (
    APP_DIR, DEFAULT_STEAM_PATHS, find_steam_path, load_api_key,
    list_accounts, account_paths,
)
from steam.vdf import parse_binary_vdf, get_ci
from steam.sgdb import (
    API_BASE, SGDBError, SGDBAuthError, api_get, clean_name,
    search_game_id, search_games, list_arts_raw, download,
)
from steam.arts import (
    ART_TYPES, ART_EXTS, existing_art, art_status, apply_art,
    list_arts, fetch_art_url,
)
from steam.library import (
    NONSTEAM_MIN, compute_legacy_appid, load_shortcuts, list_games,
    find_orphans, clean_orphans,
)

__all__ = [
    "APP_DIR", "DEFAULT_STEAM_PATHS", "find_steam_path", "load_api_key",
    "list_accounts", "account_paths", "parse_binary_vdf", "get_ci",
    "API_BASE", "SGDBError", "SGDBAuthError", "api_get", "clean_name",
    "search_game_id", "search_games", "list_arts_raw", "download",
    "ART_TYPES", "ART_EXTS", "existing_art", "art_status", "apply_art",
    "list_arts", "fetch_art_url", "NONSTEAM_MIN", "compute_legacy_appid",
    "load_shortcuts", "list_games", "find_orphans", "clean_orphans",
]
```

- [ ] **Step 2: Smoke-тест фасада — добавить в `tests/test_library.py`**

Добавить класс в конец файла (перед `if __name__`):

```python
class FacadeTest(unittest.TestCase):
    def test_public_api_exposed(self):
        import steam
        for name in ("find_steam_path", "load_api_key", "list_accounts",
                     "account_paths", "list_games", "clean_name", "ART_TYPES",
                     "search_games", "list_arts", "SGDBError", "SGDBAuthError",
                     "find_orphans", "existing_art", "load_shortcuts", "art_status",
                     "search_game_id", "fetch_art_url", "apply_art"):
            self.assertTrue(hasattr(steam, name), "missing: " + name)
```

- [ ] **Step 3: Запустить smoke-тест — убедиться, что проходит**

Run: `python -m unittest tests.test_library.FacadeTest -v`
Expected: PASS.

- [ ] **Step 4: Переписать `steam_art.py` как тонкую CLI-обёртку (Hydra убрана)**

Полностью заменить содержимое файла:

```python
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
from urllib import parse

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
        ext = os.path.splitext(parse.urlparse(url).path)[1].lower() or ".png"
        if ext not in engine.ART_EXTS:
            ext = ".png"
        dest = os.path.join(grid_dir, "%d%s%s" % (appid, cfg["suffix"], ext))
        if dry_run:
            print("      %-7s DRY  -> %s" % (t, os.path.basename(dest)))
            stats["would"] += 1
            continue
        try:
            engine.download(url, dest)
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
```

- [ ] **Step 5: Обновить импорт в `steam_art_app.py`**

Заменить строку 27:
```python
import steam_art as engine
```
на:
```python
import steam as engine
```

- [ ] **Step 6: Прогнать всю стадию проверки**

Run:
```bash
python -m unittest discover -s tests -v
python -c "import py_compile; py_compile.compile('steam_art.py', doraise=True); py_compile.compile('steam_art_app.py', doraise=True)"
python steam_art.py --help
```
Expected: все тесты PASS; компиляция без ошибок; `--help` печатает справку без Hydra.

- [ ] **Step 7: Smoke-тест сервера (без окна) — проверить, что GUI-бэкенд импортируется**

Run:
```bash
python -c "import steam_art_app; print('server import ok')"
```
Expected: `server import ok` (импорт `import steam as engine` отрабатывает).

- [ ] **Step 8: Коммит**

```bash
git add steam/__init__.py steam_art.py steam_art_app.py tests/test_library.py
git commit -m "refactor: thin CLI wrapper over steam package; drop Hydra mention from docstring"
```

---

## Self-Review (выполнено автором плана)

**Покрытие спеки (раздел «Архитектура»):**
- Пакет `steam/` с модулями vdf/paths/sgdb/arts/library — ✅ Tasks 1-5.
- `steam/__init__.py` реэкспорт, `import steam as engine` — ✅ Task 6.
- `steam_art.py` тонкая CLI-обёртка, CLI-флаги сохранены — ✅ Task 6.
- `steam_art_app.py` меняет только импорт — ✅ Task 6 Step 5.
- stdlib-only, изолированные тесты — ✅ все тесты на tmp/мок, без сети.
- `users.py`, `load_installed`, фильтр `animated` — НЕ здесь намеренно (это План 2).

**Заметка про APP_DIR:** `steam_art.key` теперь читается из `dirname(dirname(__file__))` = корень проекта, что совпадает со старым `dirname(steam_art.py)`. Поведение сохранено.

**Placeholder scan:** TODO/TBD отсутствуют; в каждом code-step полный код.

**Type consistency:** имена `list_arts_raw`, `art_status`, `apply_art`, `find_orphans`, `ART_TYPES`, `ART_EXTS` согласованы между модулями, фасадом и тестами. `download` и `list_arts_raw` живут в `sgdb`, импортируются в `arts`. Цикл `arts↔library` исключён (orphans в library).

**Краевой случай (важно для исполнителя):** запускать тесты из корня проекта (`A:\Apps\steam-art`), иначе `import steam` / `from tests.helpers` не найдутся. Команда: `python -m unittest discover -s tests`.
