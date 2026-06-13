# Backend Engine Additions (Plan 2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the engine-side data sources for the new features — installed Steam games, account names/avatars, game-icon resolution, a text-VDF parser, and an `animated` filter for art listing — all stdlib-only and unit-tested. No server/UI changes here (that's Plan 2b).

**Architecture:** Extends the `steam/` package from Plan 1. New text-VDF parser in `steam/vdf.py`; installed-game loading + unified game model in `steam/library.py`; new `steam/users.py` (uid↔SteamID64, persona names, avatars) and `steam/icons.py` (icon path resolution); `animated` param threaded through `steam/arts.py`. Facade re-exports the new public names. Dependency DAG stays acyclic.

**Tech Stack:** Python 3 (stdlib-only), `unittest`, `unittest.mock`.

**Grounded in real files on this machine (verified):**
- `libraryfolders.vdf` (text): `libraryfolders` → `<index>` → `{path, apps:{appid:size}}`. Libraries live on multiple drives; must scan all.
- `appmanifest_<appid>.acf` (text): `AppState` → `{appid, name, installdir, StateFlags}`. Tool example: appid `228980` = "Steamworks Common Redistributables".
- `config/loginusers.vdf` (text): `users` → `<steamid64>` → `{AccountName, PersonaName, ...}`.
- `config/avatarcache/<steamid64>.png` (verified: uid `11111111` → steamid64 `76561197971376839`).
- `appcache/librarycache/<appid>/` subfolder with `library_600x900.jpg`, `logo.png`, `header.jpg` (+hash files). No flat `<appid>_icon.jpg` on new clients → resolver tries legacy then subfolder, else placeholder.

**Public API added (re-exported via `import steam as engine`):**
`parse_text_vdf`, `list_libraries`, `load_installed`, `installed_games`, `STEAM_TOOL_APPIDS`, `account_steamid64`, `load_users`, `account_name`, `account_avatar_path`, `account_infos`, `game_icon_path`, `steam_game_image`. `list_arts` gains an `animated=False` kwarg. `load_shortcuts` game dicts gain an `icon` key and `kind` key; installed game dicts use `kind="steam"`.

---

## File structure

| File | Change |
|---|---|
| `steam/vdf.py` | ADD `parse_text_vdf(text)` (+ internal `_tokenize_text_vdf`) |
| `steam/library.py` | ADD `STEAM_TOOL_APPIDS`, `list_libraries`, `load_installed`, `installed_games`; extend `load_shortcuts` (add `icon`, `kind="shortcut"`); extend `list_games` to tag `kind="shortcut"` and keep `icon` |
| `steam/users.py` | NEW: `account_steamid64`, `load_users`, `account_name`, `account_avatar_path`, `account_infos` |
| `steam/icons.py` | NEW: `STEAM_IMAGE_PRIORITY`, `steam_game_image`, `game_icon_path` |
| `steam/arts.py` | extend `list_arts(..., animated=False)` |
| `steam/__init__.py` | re-export new names |
| `tests/helpers.py` | ADD `write_text_vdf_files` helper (writes fixture .acf/.vdf trees) |
| `tests/test_text_vdf.py`, `tests/test_installed.py`, `tests/test_users.py`, `tests/test_icons.py` | NEW tests |
| `tests/test_arts.py` | ADD animated-param test |
| `tests/test_library.py` | ADD facade re-export checks for new names |

**No cycles:** `users` → `vdf`, `paths`. `icons` → `paths` (only os/glob really). `library` → `vdf`, `arts`, `paths` (unchanged). `arts` unchanged deps.

---

### Task 1: Text-VDF parser in `steam/vdf.py`

**Files:** Modify `steam/vdf.py`; Create `tests/test_text_vdf.py`.

- [ ] **Step 1: Write failing test `tests/test_text_vdf.py`**

```python
# -*- coding: utf-8 -*-
import unittest
from steam.vdf import parse_text_vdf


class TextVdfTest(unittest.TestCase):
    def test_nested_and_escapes(self):
        text = '''
        "libraryfolders"
        {
            "0"
            {
                "path"  "C:\\\\Program Files (x86)\\\\Steam"
                "apps"
                {
                    "228980"  "1011723081"
                    "431960"  "829009548"
                }
            }
        }
        '''
        d = parse_text_vdf(text)
        lf = d["libraryfolders"]
        self.assertEqual(lf["0"]["path"], "C:\\Program Files (x86)\\Steam")
        self.assertEqual(set(lf["0"]["apps"].keys()), {"228980", "431960"})
        self.assertEqual(lf["0"]["apps"]["431960"], "829009548")

    def test_line_comments_ignored(self):
        text = '"AppState"\n{\n  // a comment\n  "name" "Wallpaper Engine"\n}\n'
        d = parse_text_vdf(text)
        self.assertEqual(d["AppState"]["name"], "Wallpaper Engine")

    def test_empty_block(self):
        d = parse_text_vdf('"root"\n{\n  "apps"\n  {\n  }\n}\n')
        self.assertEqual(d["root"]["apps"], {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m unittest tests.test_text_vdf -v`
Expected: FAIL — `cannot import name 'parse_text_vdf'`.

- [ ] **Step 3: Add the parser to the END of `steam/vdf.py`**

```python
def _tokenize_text_vdf(text):
    """Токенайзер текстового VDF: кавыченные строки, { и }, // комментарии."""
    tokens = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j + 1
        elif c == "{" or c == "}":
            tokens.append(c)
            i += 1
        elif c == '"':
            i += 1
            buf = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    nxt = text[i + 1]
                    buf.append({"n": "\n", "t": "\t"}.get(nxt, nxt))
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            tokens.append("".join(buf))
            i += 1  # закрывающая кавычка
        else:
            # неэкранированный токен (редко в Steam-файлах)
            j = i
            while j < n and text[j] not in ' \t\r\n"{}':
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def parse_text_vdf(text):
    """Разбирает текстовый VDF (.acf, libraryfolders.vdf, loginusers.vdf) в dict."""
    tokens = _tokenize_text_vdf(text)
    pos = 0

    def parse_obj():
        nonlocal pos
        obj = {}
        while pos < len(tokens):
            tok = tokens[pos]
            if tok == "}":
                pos += 1
                return obj
            pos += 1
            key = tok
            if pos < len(tokens) and tokens[pos] == "{":
                pos += 1
                obj[key] = parse_obj()
            else:
                obj[key] = tokens[pos] if pos < len(tokens) else ""
                pos += 1
        return obj

    return parse_obj()
```

- [ ] **Step 4: Run, confirm PASS**

Run: `python -m unittest tests.test_text_vdf -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Regression check + commit**

Run: `python -m unittest discover -t . -s tests -v` (expect all green)

```bash
git add steam/vdf.py tests/test_text_vdf.py
git commit -m "feat: add text-VDF parser (acf/libraryfolders/loginusers)"
```

---

### Task 2: Installed games in `steam/library.py`

**Files:** Modify `steam/library.py`; Modify `tests/helpers.py`; Create `tests/test_installed.py`.

- [ ] **Step 1: Add a fixture helper to `tests/helpers.py`**

Append:

```python
def write_file(path, text):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def make_library(root, apps):
    """Создаёт steamapps/appmanifest_*.acf для набора apps={appid: name}."""
    import os
    sa = os.path.join(root, "steamapps")
    for appid, name in apps.items():
        write_file(os.path.join(sa, "appmanifest_%s.acf" % appid),
                   '"AppState"\n{\n  "appid" "%s"\n  "name" "%s"\n  "installdir" "%s"\n}\n'
                   % (appid, name, name.replace(" ", "_")))
    return sa
```

- [ ] **Step 2: Write failing test `tests/test_installed.py`**

```python
# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from tests.helpers import write_file, make_library
from steam.library import list_libraries, load_installed, STEAM_TOOL_APPIDS


class InstalledTest(unittest.TestCase):
    def _steam(self, tmp, libs):
        # libs: list of (relpath, {appid:name}); first is the steam root itself
        entries = []
        for i, (rel, apps) in enumerate(libs):
            root = os.path.join(tmp, rel) if rel else tmp
            make_library(root, apps)
            entries.append('  "%d"\n  {\n    "path" "%s"\n  }\n'
                           % (i, root.replace("\\", "\\\\")))
        write_file(os.path.join(tmp, "steamapps", "libraryfolders.vdf"),
                   '"libraryfolders"\n{\n%s}\n' % "".join(entries))
        return tmp

    def test_list_libraries(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._steam(tmp, [("", {"431960": "Wallpaper Engine"}),
                              ("L2", {"8870": "BioShock"})])
            libs = list_libraries(tmp)
            self.assertIn(tmp, libs)
            self.assertIn(os.path.join(tmp, "L2"), libs)

    def test_load_installed_filters_tools_and_dedups(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._steam(tmp, [
                ("", {"431960": "Wallpaper Engine", "228980": "Steamworks Common Redistributables"}),
                ("L2", {"8870": "BioShock Infinite", "1493710": "Proton 8.0"}),
            ])
            games = load_installed(tmp)
            names = sorted(g["name"] for g in games)
            self.assertEqual(names, ["BioShock Infinite", "Wallpaper Engine"])
            self.assertTrue(all(g["kind"] == "steam" for g in games))
            self.assertTrue(all(isinstance(g["appid"], int) for g in games))
            self.assertIn(228980, STEAM_TOOL_APPIDS)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run, confirm FAIL**

Run: `python -m unittest tests.test_installed -v`
Expected: FAIL — `cannot import name 'list_libraries'`.

- [ ] **Step 4: Add to `steam/library.py`**

At the top, update imports to add `glob` and `parse_text_vdf`:

```python
import glob
```
and change the vdf import line to:
```python
from steam.vdf import parse_binary_vdf, get_ci, parse_text_vdf
```

Then add these constants + functions (place after `NONSTEAM_MIN`):

```python
# appid'ы инструментов/рантаймов, которые НЕ являются играми.
STEAM_TOOL_APPIDS = {
    228980,   # Steamworks Common Redistributables
    1070560,  # Steam Linux Runtime 1.0 (scout)
    1391110,  # Steam Linux Runtime 2.0 (soldier)
    1628350,  # Steam Linux Runtime 3.0 (sniper)
    1493710,  # Proton Experimental
}

# Подстроки в имени, по которым считаем запись не-игрой.
_TOOL_NAME_HINTS = (
    "steamworks common redistributables",
    "steam linux runtime",
    "proton ",
    "proton experimental",
    "dedicated server",
)


def _is_tool(appid, name):
    if appid in STEAM_TOOL_APPIDS:
        return True
    low = name.lower()
    return any(h in low for h in _TOOL_NAME_HINTS)


def list_libraries(steam_path):
    """Пути всех Steam-библиотек из libraryfolders.vdf (+ сам Steam как запас)."""
    out, seen = [], set()

    def add(p):
        if p and os.path.isdir(p) and p not in seen:
            seen.add(p)
            out.append(p)

    add(steam_path)  # основная библиотека всегда есть
    for cand in (os.path.join(steam_path, "steamapps", "libraryfolders.vdf"),
                 os.path.join(steam_path, "config", "libraryfolders.vdf")):
        if not os.path.isfile(cand):
            continue
        try:
            with open(cand, encoding="utf-8", errors="replace") as f:
                data = parse_text_vdf(f.read())
        except Exception:
            continue
        folders = data.get("libraryfolders") or data.get("LibraryFolders") or {}
        for _, entry in folders.items():
            if isinstance(entry, dict) and entry.get("path"):
                add(os.path.normpath(entry["path"]))
        break  # одного валидного файла достаточно
    return out


def load_installed(steam_path):
    """Установленные Steam-игры из всех библиотек: [{appid:int, name, kind:'steam',
    installdir, library}]. Инструменты/рантаймы отфильтрованы, дубликаты убраны по appid."""
    games, seen = [], set()
    for lib in list_libraries(steam_path):
        for acf in sorted(glob.glob(os.path.join(lib, "steamapps", "appmanifest_*.acf"))):
            try:
                with open(acf, encoding="utf-8", errors="replace") as f:
                    st = parse_text_vdf(f.read()).get("AppState") or {}
            except Exception:
                continue
            try:
                appid = int(st.get("appid") or 0)
            except ValueError:
                continue
            name = st.get("name") or ""
            if not appid or not name or appid in seen or _is_tool(appid, name):
                continue
            seen.add(appid)
            games.append({"appid": appid, "name": name, "kind": "steam",
                          "installdir": st.get("installdir") or "", "library": lib})
    games.sort(key=lambda g: g["name"].lower())
    return games
```

- [ ] **Step 5: Run, confirm PASS**

Run: `python -m unittest tests.test_installed -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Regression + commit**

Run: `python -m unittest discover -t . -s tests -v`

```bash
git add steam/library.py tests/helpers.py tests/test_installed.py
git commit -m "feat: load installed Steam games across libraries, filter tools"
```

---

### Task 3: Unified game model — `icon`/`kind` on shortcuts + `installed_games`

**Files:** Modify `steam/library.py`; Modify `tests/test_library.py`.

- [ ] **Step 1: Add failing tests to `tests/test_library.py`**

Add these methods inside `LibraryTest` (the existing class):

```python
    def test_load_shortcuts_has_icon_and_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            vdf = os.path.join(tmp, "shortcuts.vdf")
            with open(vdf, "wb") as f:
                f.write(build_shortcuts_vdf([
                    {"appid": 2468090731, "AppName": "Alien", "Exe": "a.exe",
                     "icon": "C:\\icons\\alien.ico"},
                ]))
            g = load_shortcuts(vdf)[0]
            self.assertEqual(g["kind"], "shortcut")
            self.assertEqual(g["icon"], "C:\\icons\\alien.ico")
```

And add a new import + test for `installed_games` (status attached). Add at top of file: `from steam.library import installed_games` (extend the existing import line). Then add a new test class:

```python
class InstalledGamesTest(unittest.TestCase):
    def test_installed_games_attaches_status(self):
        import os
        from tests.helpers import make_library, write_file
        with tempfile.TemporaryDirectory() as tmp:
            steam = os.path.join(tmp, "Steam")
            make_library(steam, {"431960": "Wallpaper Engine"})
            write_file(os.path.join(steam, "steamapps", "libraryfolders.vdf"),
                       '"libraryfolders"\n{\n  "0"\n  {\n    "path" "%s"\n  }\n}\n'
                       % steam.replace("\\", "\\\\"))
            # арт-статус берётся из grid аккаунта uid
            uid = "999"
            grid = os.path.join(steam, "userdata", uid, "config", "grid")
            os.makedirs(grid)
            open(os.path.join(grid, "431960p.png"), "wb").close()
            games = installed_games(steam, uid)
            self.assertEqual(len(games), 1)
            self.assertEqual(games[0]["appid"], 431960)
            self.assertTrue(games[0]["status"]["cover"])     # 431960p.png present
            self.assertFalse(games[0]["status"]["hero"])
```

Also extend the helper import line at the top of `tests/test_library.py` if needed (the test imports `make_library, write_file` locally, which is fine).

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m unittest tests.test_library -v`
Expected: FAIL (`KeyError: 'kind'` / `cannot import name 'installed_games'`).

- [ ] **Step 3: Modify `steam/library.py`**

In `load_shortcuts`, replace the append block so each game carries `icon` and `kind`:

```python
        icon = get_ci(entry, "icon") or ""
        appid = get_ci(entry, "appid")
        if not appid:
            appid = compute_legacy_appid(exe, name)
        appid &= 0xffffffff
        if name:
            games.append({"appid": appid, "name": name, "exe": exe,
                          "icon": icon, "kind": "shortcut"})
```

Add `installed_games` after `list_games`:

```python
def installed_games(steam_path, uid):
    """Установленные Steam-игры со статусом артов для grid указанного аккаунта."""
    _, grid_dir = account_paths(steam_path, uid)
    games = load_installed(steam_path)
    for g in games:
        g["status"] = art_status(grid_dir, g["appid"])
    return games
```

(`list_games` already attaches status for shortcuts; its dicts now also include `icon`/`kind` automatically because `load_shortcuts` adds them.)

- [ ] **Step 4: Run, confirm PASS**

Run: `python -m unittest tests.test_library -v`
Expected: PASS.

- [ ] **Step 5: Regression + commit**

Run: `python -m unittest discover -t . -s tests -v`

```bash
git add steam/library.py tests/test_library.py
git commit -m "feat: unify game model (icon/kind) and add installed_games with art status"
```

---

### Task 4: Account names & avatars — `steam/users.py`

**Files:** Create `steam/users.py`; Create `tests/test_users.py`.

- [ ] **Step 1: Write failing test `tests/test_users.py`**

```python
# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from tests.helpers import write_file
from steam.users import (account_steamid64, load_users, account_name,
                         account_avatar_path, account_infos)


class UsersTest(unittest.TestCase):
    def test_steamid64_mapping(self):
        # проверенный реальный пример: uid 11111111 -> 76561197971376839
        self.assertEqual(account_steamid64("11111111"), 76561197971376839)

    def _steam_with_users(self, tmp):
        write_file(os.path.join(tmp, "config", "loginusers.vdf"),
                   '"users"\n{\n  "76561197971376839"\n  {\n'
                   '    "AccountName" "acc"\n    "PersonaName" "Sam"\n  }\n}\n')

    def test_load_and_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._steam_with_users(tmp)
            users = load_users(tmp)
            self.assertEqual(users["76561197971376839"]["PersonaName"], "Sam")
            self.assertEqual(account_name(tmp, "11111111"), "Sam")
            self.assertIsNone(account_name(tmp, "1"))  # неизвестный uid -> None

    def test_avatar_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            ac = os.path.join(tmp, "config", "avatarcache")
            os.makedirs(ac)
            open(os.path.join(ac, "76561197971376839.png"), "wb").close()
            self.assertTrue(account_avatar_path(tmp, "11111111").endswith("76561197971376839.png"))
            self.assertIsNone(account_avatar_path(tmp, "1"))  # нет файла

    def test_account_infos(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._steam_with_users(tmp)
            infos = account_infos(tmp, ["11111111", "1"])
            self.assertEqual(infos[0], {"uid": "11111111", "name": "Sam", "has_avatar": False})
            self.assertEqual(infos[1], {"uid": "1", "name": None, "has_avatar": False})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m unittest tests.test_users -v`
Expected: FAIL — `No module named 'steam.users'`.

- [ ] **Step 3: Create `steam/users.py`**

```python
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
```

- [ ] **Step 4: Run, confirm PASS**

Run: `python -m unittest tests.test_users -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Regression + commit**

Run: `python -m unittest discover -t . -s tests -v`

```bash
git add steam/users.py tests/test_users.py
git commit -m "feat: account names and avatars via loginusers/avatarcache"
```

---

### Task 5: Game-icon resolution — `steam/icons.py`

**Files:** Create `steam/icons.py`; Create `tests/test_icons.py`.

- [ ] **Step 1: Write failing test `tests/test_icons.py`**

```python
# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from steam.icons import steam_game_image, game_icon_path


class IconsTest(unittest.TestCase):
    def test_legacy_flat_icon_preferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            lc = os.path.join(tmp, "appcache", "librarycache")
            os.makedirs(lc)
            open(os.path.join(lc, "440_icon.jpg"), "wb").close()
            self.assertTrue(steam_game_image(tmp, 440).endswith("440_icon.jpg"))

    def test_subfolder_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "appcache", "librarycache", "431960")
            os.makedirs(d)
            open(os.path.join(d, "header.jpg"), "wb").close()
            open(os.path.join(d, "library_600x900.jpg"), "wb").close()
            # cover (library_600x900) приоритетнее header
            self.assertTrue(steam_game_image(tmp, 431960).endswith("library_600x900.jpg"))

    def test_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(steam_game_image(tmp, 12345))

    def test_game_icon_path_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            # non-Steam: берём icon-файл ярлыка, если он существует
            ico = os.path.join(tmp, "alien.ico")
            open(ico, "wb").close()
            shortcut = {"kind": "shortcut", "appid": 2468090731, "icon": ico}
            self.assertEqual(game_icon_path(tmp, shortcut), ico)
            # non-Steam без существующего файла -> None
            self.assertIsNone(game_icon_path(tmp, {"kind": "shortcut", "appid": 1, "icon": "Z:\\nope.ico"}))
            # Steam: делегирует steam_game_image
            d = os.path.join(tmp, "appcache", "librarycache", "431960")
            os.makedirs(d)
            open(os.path.join(d, "logo.png"), "wb").close()
            steam_g = {"kind": "steam", "appid": 431960, "icon": ""}
            self.assertTrue(game_icon_path(tmp, steam_g).endswith("logo.png"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m unittest tests.test_icons -v`
Expected: FAIL — `No module named 'steam.icons'`.

- [ ] **Step 3: Create `steam/icons.py`**

```python
# -*- coding: utf-8 -*-
"""Поиск локальной картинки-иконки для строки списка игр.
Steam менял раскладку librarycache между версиями, поэтому пробуем несколько мест."""
import os

# Приоритет файлов внутри appcache/librarycache/<appid>/ (новая раскладка).
# Явного «иконочного» файла там нет — берём узнаваемую мелкую обложку/лого.
STEAM_IMAGE_PRIORITY = (
    "library_600x900.jpg",
    "library_600x900_2x.jpg",
    "logo.png",
    "header.jpg",
)


def steam_game_image(steam_path, appid):
    """Лучшая доступная картинка для Steam-игры или None.
    Порядок: legacy-плоский <appid>_icon.jpg -> файлы в подпапке <appid>/ по приоритету."""
    lc = os.path.join(steam_path, "appcache", "librarycache")
    legacy = os.path.join(lc, "%d_icon.jpg" % appid)
    if os.path.isfile(legacy):
        return legacy
    sub = os.path.join(lc, str(appid))
    if os.path.isdir(sub):
        for fn in STEAM_IMAGE_PRIORITY:
            p = os.path.join(sub, fn)
            if os.path.isfile(p):
                return p
    return None


def game_icon_path(steam_path, game):
    """Путь к иконке для игры (любого вида) или None.
    non-Steam -> поле icon ярлыка (если файл существует); Steam -> steam_game_image."""
    if game.get("kind") == "steam":
        return steam_game_image(steam_path, game["appid"])
    icon = game.get("icon") or ""
    return icon if (icon and os.path.isfile(icon)) else None
```

- [ ] **Step 4: Run, confirm PASS**

Run: `python -m unittest tests.test_icons -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Regression + commit**

Run: `python -m unittest discover -t . -s tests -v`

```bash
git add steam/icons.py tests/test_icons.py
git commit -m "feat: resolve game-icon paths (shortcut icon / librarycache)"
```

---

### Task 6: `animated` filter in `steam/arts.py`

**Files:** Modify `steam/arts.py`; Modify `tests/test_arts.py`.

- [ ] **Step 1: Add failing test to `tests/test_arts.py`**

Add to `ArtsTest`:

```python
    def test_list_arts_animated_requests_animated_type(self):
        captured = {}
        def fake_raw(endpoint, game_id, api_key, params):
            captured["params"] = dict(params)
            return [{"url": "u", "thumb": "t", "width": 600, "height": 900, "style": "s"}]
        with patch("steam.arts.list_arts_raw", fake_raw):
            items = list_arts(1, "cover", "key", animated=True)
        self.assertEqual(captured["params"]["types"], "animated")
        self.assertTrue(items and items[0]["animated"] is True)

    def test_list_arts_static_by_default(self):
        captured = {}
        def fake_raw(endpoint, game_id, api_key, params):
            captured["params"] = dict(params)
            return [{"url": "u", "thumb": "t", "width": 600, "height": 900, "style": "s"}]
        with patch("steam.arts.list_arts_raw", fake_raw):
            items = list_arts(1, "cover", "key")
        self.assertEqual(captured["params"]["types"], "static")
        self.assertFalse(items[0]["animated"])
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m unittest tests.test_arts -v`
Expected: FAIL (unexpected `animated` kwarg / missing `animated` key).

- [ ] **Step 3: Modify `list_arts` in `steam/arts.py`**

Replace the whole `list_arts` function with:

```python
def list_arts(game_id, art_type, api_key, limit=40, animated=False):
    """Список вариантов арта данного типа:
    [{url, thumb, width, height, style, animated}, ...].
    animated=True -> запрашиваем только анимированные (types=animated)."""
    cfg = ART_TYPES[art_type]
    art_kind = "animated" if animated else "static"
    data = list_arts_raw(cfg["endpoint"], game_id, api_key, {"types": art_kind})
    items = []
    for a in data:
        items.append({
            "url": a.get("url"),
            "thumb": a.get("thumb") or a.get("url"),
            "width": a.get("width"),
            "height": a.get("height"),
            "style": a.get("style"),
            "animated": animated,
        })
    if art_type == "cover":
        items.sort(key=lambda a: 0 if (a["width"], a["height"]) == (600, 900) else 1)
    return [a for a in items if a["url"]][:limit]
```

- [ ] **Step 4: Run, confirm PASS**

Run: `python -m unittest tests.test_arts -v`
Expected: PASS (existing cover-sort/fallback tests still pass, plus the 2 new).

- [ ] **Step 5: Regression + commit**

Run: `python -m unittest discover -t . -s tests -v`

```bash
git add steam/arts.py tests/test_arts.py
git commit -m "feat: animated filter for list_arts (types=animated)"
```

---

### Task 7: Facade re-exports + smoke test

**Files:** Modify `steam/__init__.py`; Modify `tests/test_library.py`.

- [ ] **Step 1: Add the new names to `steam/__init__.py`**

Add these imports (after the existing block) and extend `__all__`:

```python
from steam.library import (
    STEAM_TOOL_APPIDS, list_libraries, load_installed, installed_games,
)
from steam.users import (
    account_steamid64, load_users, account_name, account_avatar_path, account_infos,
)
from steam.icons import STEAM_IMAGE_PRIORITY, steam_game_image, game_icon_path
from steam.vdf import parse_text_vdf
```

Extend `__all__` by appending these names:
```python
    "STEAM_TOOL_APPIDS", "list_libraries", "load_installed", "installed_games",
    "account_steamid64", "load_users", "account_name", "account_avatar_path",
    "account_infos", "STEAM_IMAGE_PRIORITY", "steam_game_image", "game_icon_path",
    "parse_text_vdf",
```

- [ ] **Step 2: Add a facade check to `tests/test_library.py` `FacadeTest`**

Add a method:

```python
    def test_plan2_names_present(self):
        import steam
        for name in ("parse_text_vdf", "list_libraries", "load_installed",
                     "installed_games", "STEAM_TOOL_APPIDS", "account_steamid64",
                     "load_users", "account_name", "account_avatar_path",
                     "account_infos", "steam_game_image", "game_icon_path"):
            self.assertIn(name, steam.__all__, "not in __all__: " + name)
            self.assertTrue(hasattr(steam, name), "missing: " + name)
```

- [ ] **Step 3: Run the facade test + whole suite**

Run: `python -m unittest tests.test_library -v`
Then: `python -m unittest discover -t . -s tests -v`
Expected: all green.

- [ ] **Step 4: Verify the engine imports cleanly and the app still imports**

Run:
```bash
python -c "import steam; print('engine ok', len(steam.__all__), 'names')"
python -c "import steam_art_app; print('server import ok')"
python -c "import py_compile; py_compile.compile('steam_art.py', doraise=True); print('cli compile ok')"
```
Expected: all three print OK.

- [ ] **Step 5: Commit**

```bash
git add steam/__init__.py tests/test_library.py
git commit -m "feat: re-export Plan 2a engine API (installed/users/icons/animated/text-vdf)"
```

---

## Self-Review (by plan author)

**Spec coverage (Plan 2 engine portion):**
- Installed games across libraries + tool filtering → Task 2 (`list_libraries`, `load_installed`, `STEAM_TOOL_APPIDS`, name hints). ✅
- Unified game model `{appid, name, kind, icon, status}` → Task 3 (shortcuts gain icon/kind; `installed_games` attaches status). ✅
- Account names + avatars + uid↔SteamID64 (`0x0110000100000000`) → Task 4. ✅
- Game icons multi-location lookup (legacy flat → `<appid>/` subfolder → none) → Task 5. ✅
- Animated filter (`types=animated`) → Task 6. ✅
- Text-VDF parser for acf/libraryfolders/loginusers → Task 1. ✅
- Server endpoints + `_autofill_sse` guard fix → NOT here; these are Plan 2b (server wiring), intentionally deferred.

**Placeholder scan:** No TODO/TBD; every code step has full code.

**Type/name consistency:** `parse_text_vdf` (vdf) used by library/users; `account_steamid64` returns int, `account_avatar_path`/`account_name` return str|None; game dicts consistently use `kind` ("shortcut"/"steam"), `icon`, `appid` (int), `status`. `list_arts(..., animated=False)` returns items with an `animated` bool. Facade `__all__` extended with exactly the names the tests assert.

**Execution note:** Run all test commands from project root `A:\Apps\steam-art` using `python -m unittest discover -t . -s tests`. Fixtures never touch the real Steam install (all use tempdirs).
