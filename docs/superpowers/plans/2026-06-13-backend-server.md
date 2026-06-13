# Backend Server Wiring (Plan 2b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the Plan 2a engine capabilities through the local HTTP API so the frontend (Plan 3) can use them: account names/avatars in `/api/state`, an installed-games tab in `/api/games`, an `animated` filter in `/api/arts`, and new `/api/avatar` + `/api/gameicon` streaming endpoints. Also fix the pre-existing `_autofill_sse` crash when Steam is missing. Add an offline API test suite.

**Architecture:** All changes are in `steam_art_app.py` (the stdlib `ThreadingHTTPServer` + `Handler`). The handler already exposes `_json`, `_err`, `_send_file`, and reads module globals `STEAM` and `engine` (= the `steam` package). New endpoints reuse `_send_file` for local images. Tests spin up the real `Server` on a free port in a thread and hit it with `urllib`, pointing `STEAM` at a tempdir fixture tree and patching `engine.load_api_key`/`engine.list_arts` where network/keys would be involved.

**Tech Stack:** Python 3 stdlib (`http.server`, `urllib`, `unittest`, `unittest.mock`).

**Current API (from Plan 1/2a):** `GET /api/state|games|search|arts|orphans|autofill(SSE)`, `GET /img`, `POST /api/apply|clean|key`. `engine` now also exposes `account_infos`, `installed_games`, `load_installed`, `account_avatar_path`, `steam_game_image`, `game_icon_path`, `load_shortcuts` (with `icon`/`kind`), and `list_arts(..., animated=)`.

---

## File structure

| File | Change |
|---|---|
| `steam_art_app.py` | `/api/state` returns account infos; `/api/games` gains `source` + per-game `kind`; `/api/arts` gains `animated`; new `/api/avatar`, `/api/gameicon`; new `_game_icon_file` helper; fix `_autofill_sse` STEAM guard |
| `tests/test_api.py` | NEW — offline API tests (server in a thread + urllib + fixtures) |
| `tests/helpers.py` | ADD `make_account` helper (writes a userdata account with shortcuts.vdf + optional loginusers/avatar) |

No engine files change in this plan.

---

### Task 1: API test harness + `/api/state` account infos + `/api/games` source/kind

**Files:** Modify `steam_art_app.py`; Modify `tests/helpers.py`; Create `tests/test_api.py`.

- [ ] **Step 1: Add a fixture helper to the END of `tests/helpers.py`**

```python
def make_account(steam_root, uid, games, persona=None):
    """Создаёт userdata/<uid>/config/shortcuts.vdf для games (list для build_shortcuts_vdf).
    Если persona задан — пишет config/loginusers.vdf с этим именем для uid."""
    import os
    cfg = os.path.join(steam_root, "userdata", uid, "config")
    os.makedirs(cfg, exist_ok=True)
    with open(os.path.join(cfg, "shortcuts.vdf"), "wb") as f:
        f.write(build_shortcuts_vdf(games))
    if persona is not None:
        sid = int(uid) + 0x0110000100000000
        write_file(os.path.join(steam_root, "config", "loginusers.vdf"),
                   '"users"\n{\n  "%d"\n  {\n    "PersonaName" "%s"\n  }\n}\n' % (sid, persona))
    return cfg
```

- [ ] **Step 2: Write failing test `tests/test_api.py`**

```python
# -*- coding: utf-8 -*-
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import patch

import steam_art_app as app
from tests.helpers import make_account, make_library, write_file


def _get(srv, path):
    port = srv.server_address[1]
    req = urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=5)
    body = req.read().decode("utf-8")
    return req.status, body


class ApiBase(unittest.TestCase):
    def start(self, steam_path):
        app.STEAM = steam_path
        srv = app.Server(("127.0.0.1", app.free_port()), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        return srv


class StateGamesTest(ApiBase):
    def test_state_returns_account_infos(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_account(tmp, "11111111",
                         [{"appid": 2468090731, "AppName": "Alien", "Exe": "a.exe"}],
                         persona="Sam")
            srv = self.start(tmp)
            with patch.object(app.engine, "load_api_key", lambda *_: "k"):
                code, body = _get(srv, "/api/state")
            d = json.loads(body)
            self.assertEqual(code, 200)
            self.assertTrue(d["key_ok"])
            accts = d["accounts"]
            self.assertEqual(accts[0]["uid"], "11111111")
            self.assertEqual(accts[0]["name"], "Sam")
            self.assertIn("has_avatar", accts[0])

    def test_games_shortcut_source_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_account(tmp, "999",
                         [{"appid": 2468090731, "AppName": "Alien", "Exe": "a.exe"}])
            srv = self.start(tmp)
            code, body = _get(srv, "/api/games?account=999")
            d = json.loads(body)
            self.assertEqual(code, 200)
            self.assertEqual(len(d["games"]), 1)
            self.assertEqual(d["games"][0]["kind"], "shortcut")
            self.assertEqual(d["games"][0]["name"], "Alien")
            self.assertIn("cover", d["games"][0]["status"])

    def test_games_installed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            steam = tmp
            make_library(steam, {"431960": "Wallpaper Engine"})
            write_file(os.path.join(steam, "steamapps", "libraryfolders.vdf"),
                       '"libraryfolders"\n{\n  "0"\n  {\n    "path" "%s"\n  }\n}\n'
                       % steam.replace("\\", "\\\\"))
            os.makedirs(os.path.join(steam, "userdata", "999", "config", "grid"))
            srv = self.start(steam)
            code, body = _get(srv, "/api/games?account=999&source=installed")
            d = json.loads(body)
            self.assertEqual(code, 200)
            self.assertEqual(d["source"], "installed")
            self.assertEqual([g["name"] for g in d["games"]], ["Wallpaper Engine"])
            self.assertEqual(d["games"][0]["kind"], "steam")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run, confirm FAIL**

Run: `python -m unittest tests.test_api -v`
Expected: FAIL (state returns bare uid list, not infos; `/api/games` has no `source`/`kind`).

- [ ] **Step 4: Modify `_api_get` in `steam_art_app.py`**

Replace the `/api/state` block:
```python
        if path == "/api/state":
            return self._json({
                "steam_path": STEAM,
                "accounts": engine.list_accounts(STEAM) if STEAM else [],
                "key_ok": bool(key),
            })
```
with:
```python
        if path == "/api/state":
            accounts = engine.list_accounts(STEAM) if STEAM else []
            return self._json({
                "steam_path": STEAM,
                "accounts": engine.account_infos(STEAM, accounts) if STEAM else [],
                "key_ok": bool(key),
            })
```

Replace the `/api/games` block:
```python
        if path == "/api/games":
            acc = q.get("account", [None])[0]
            games = engine.list_games(STEAM, acc) if (acc and STEAM) else []
            out = [{
                "appid": g["appid"],
                "name": engine.clean_name(g["name"]),
                "status": {t: bool(g["status"][t]) for t in engine.ART_TYPES},
            } for g in games]
            out.sort(key=lambda g: g["name"].lower())
            return self._json({"games": out})
```
with:
```python
        if path == "/api/games":
            acc = q.get("account", [None])[0]
            source = q.get("source", ["shortcut"])[0]
            if acc and STEAM:
                games = (engine.installed_games(STEAM, acc) if source == "installed"
                         else engine.list_games(STEAM, acc))
            else:
                games = []
            out = [{
                "appid": g["appid"],
                "name": engine.clean_name(g["name"]),
                "kind": g.get("kind", "shortcut"),
                "status": {t: bool(g["status"][t]) for t in engine.ART_TYPES},
            } for g in games]
            out.sort(key=lambda g: g["name"].lower())
            return self._json({"games": out, "source": source})
```

- [ ] **Step 5: Run, confirm PASS**

Run: `python -m unittest tests.test_api -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Regression + commit**

Run: `python -m unittest discover -t . -s tests -v` (expect all green)
```bash
git add steam_art_app.py tests/helpers.py tests/test_api.py
git commit -m "feat(api): account infos in /api/state; installed source + kind in /api/games"
```

---

### Task 2: `/api/arts` animated + `/api/avatar` + `/api/gameicon`

**Files:** Modify `steam_art_app.py`; Modify `tests/test_api.py`.

- [ ] **Step 1: Add failing tests to `tests/test_api.py`**

Add a new test class:
```python
class ArtsAvatarIconTest(ApiBase):
    def test_arts_passes_animated_flag(self):
        captured = {}
        def fake_list_arts(gid, t, key, limit=40, animated=False):
            captured["animated"] = animated
            return [{"url": "u", "thumb": "u", "width": 600, "height": 900,
                     "style": "s", "animated": animated}]
        with tempfile.TemporaryDirectory() as tmp:
            srv = self.start(tmp)
            with patch.object(app.engine, "load_api_key", lambda *_: "k"), \
                 patch.object(app.engine, "list_arts", fake_list_arts):
                code, body = _get(srv, "/api/arts?game_id=5&type=cover&animated=1")
            self.assertEqual(code, 200)
            self.assertTrue(captured["animated"])
            self.assertTrue(json.loads(body)["arts"][0]["animated"])

    def test_avatar_streams_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            sid = int("11111111") + 0x0110000100000000
            ac = os.path.join(tmp, "config", "avatarcache")
            os.makedirs(ac)
            with open(os.path.join(ac, "%d.png" % sid), "wb") as f:
                f.write(b"\x89PNG\r\n")
            srv = self.start(tmp)
            code, body = _get(srv, "/api/avatar?account=11111111")
            self.assertEqual(code, 200)
            self.assertTrue(body.startswith("\x89PNG"))

    def test_avatar_404_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            srv = self.start(tmp)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                _get(srv, "/api/avatar?account=11111111")
            self.assertEqual(cm.exception.code, 404)

    def test_gameicon_for_shortcut(self):
        with tempfile.TemporaryDirectory() as tmp:
            ico = os.path.join(tmp, "alien.ico")
            with open(ico, "wb") as f:
                f.write(b"ICON")
            make_account(tmp, "999",
                         [{"appid": 2468090731, "AppName": "Alien", "Exe": "a.exe",
                           "icon": ico}])
            srv = self.start(tmp)
            code, body = _get(srv, "/api/gameicon?account=999&appid=2468090731")
            self.assertEqual(code, 200)
            self.assertEqual(body, "ICON")
```
Add `import urllib.error` to the imports at the top of `tests/test_api.py`.

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m unittest tests.test_api -v`
Expected: FAIL (animated ignored; `/api/avatar` + `/api/gameicon` are 404 "unknown").

- [ ] **Step 3: Modify `steam_art_app.py`**

(a) In the `/api/arts` block, change the return to pass `animated`. The block currently ends with:
```python
            t = q.get("type", ["cover"])[0]
            try:
                return self._json({"arts": engine.list_arts(gid, t, key)})
            except engine.SGDBError as e:
                return self._err(e, 502)
```
Change the `list_arts` call to:
```python
            t = q.get("type", ["cover"])[0]
            animated = q.get("animated", ["0"])[0] in ("1", "true", "yes")
            try:
                return self._json({"arts": engine.list_arts(gid, t, key, animated=animated)})
            except engine.SGDBError as e:
                return self._err(e, 502)
```

(b) Add two new GET routes. In `do_GET`, right after the existing `if path == "/img": return self._serve_current(q)` line, add:
```python
            if path == "/api/avatar":
                return self._serve_avatar(q)
            if path == "/api/gameicon":
                return self._serve_gameicon(q)
```

(c) Add the two handler methods (place them next to `_serve_current`):
```python
    def _serve_avatar(self, q):
        uid = q.get("account", [None])[0]
        if not (uid and STEAM):
            return self._err("bad", 400)
        p = engine.account_avatar_path(STEAM, uid)
        if not p:
            return self._err("none", 404)
        self._send_file(p, cache=False)

    def _game_icon_file(self, uid, appid):
        """Путь к иконке игры: сперва ищем среди non-Steam ярлыков аккаунта,
        иначе считаем Steam-игрой и берём из librarycache."""
        vdf, _ = engine.account_paths(STEAM, uid)
        for g in engine.load_shortcuts(vdf):
            if g["appid"] == appid:
                return engine.game_icon_path(STEAM, g)
        return engine.steam_game_image(STEAM, appid)

    def _serve_gameicon(self, q):
        uid = q.get("account", [None])[0]
        try:
            appid = int(q.get("appid", [0])[0])
        except ValueError:
            return self._err("bad id", 400)
        if not (uid and STEAM):
            return self._err("bad", 400)
        p = self._game_icon_file(uid, appid)
        if not p or not os.path.isfile(p):
            return self._err("none", 404)
        self._send_file(p, cache=False)
```

- [ ] **Step 4: Run, confirm PASS**

Run: `python -m unittest tests.test_api -v`
Expected: PASS (all StateGames + ArtsAvatarIcon tests).

- [ ] **Step 5: Regression + commit**

Run: `python -m unittest discover -t . -s tests -v`
```bash
git add steam_art_app.py tests/test_api.py
git commit -m "feat(api): animated arts filter; /api/avatar and /api/gameicon streaming"
```

---

### Task 3: Fix `_autofill_sse` STEAM guard + test

**Files:** Modify `steam_art_app.py`; Modify `tests/test_api.py`.

- [ ] **Step 1: Add a failing test to `tests/test_api.py`**

```python
class AutofillGuardTest(ApiBase):
    def test_autofill_no_steam_does_not_500(self):
        # STEAM=None: должен отдать аккуратный SSE start/done, а не 500
        app.STEAM = None
        srv = app.Server(("127.0.0.1", app.free_port()), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        with patch.object(app.engine, "load_api_key", lambda *_: "k"):
            code, body = _get(srv, "/api/autofill?accounts=all")
        self.assertEqual(code, 200)
        self.assertIn('"type": "start"', body)
        self.assertIn('"type": "done"', body)
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `python -m unittest tests.test_api.AutofillGuardTest -v`
Expected: FAIL — the request returns 500 (TypeError: `os.path.join(None, ...)` because `engine.list_accounts(None)` is called without a STEAM guard).

- [ ] **Step 3: Fix `_autofill_sse` in `steam_art_app.py`**

The current line:
```python
        acc = q.get("accounts", ["all"])[0]
        accts = engine.list_accounts(STEAM) if acc == "all" else [acc]
```
Replace with:
```python
        acc = q.get("accounts", ["all"])[0]
        accts = (engine.list_accounts(STEAM) if STEAM else []) if acc == "all" else [acc]
```

- [ ] **Step 4: Run, confirm PASS**

Run: `python -m unittest tests.test_api.AutofillGuardTest -v`
Expected: PASS.

- [ ] **Step 5: Full suite + app import smoke + commit**

Run:
```bash
python -m unittest discover -t . -s tests -v
python -c "import steam_art_app; print('server import ok')"
```
Expected: all green; `server import ok`.
```bash
git add steam_art_app.py tests/test_api.py
git commit -m "fix(api): guard _autofill_sse against missing Steam (no more 500)"
```

---

## Self-Review (by plan author)

**Spec coverage (Plan 2 server portion):**
- Account names/avatars surfaced → `/api/state` returns `account_infos`; `/api/avatar` streams the file. ✅ Task 1, 2.
- Installed-games tab → `/api/games?source=installed` via `installed_games`, each game tagged `kind`. ✅ Task 1.
- Animated filter → `/api/arts?animated=1` threads to `engine.list_arts(animated=)`. ✅ Task 2.
- Game icons in list → `/api/gameicon` resolves shortcut icon or librarycache image. ✅ Task 2.
- Pre-existing `_autofill_sse` STEAM-guard bug → fixed + regression test. ✅ Task 3.
- Offline API test suite (server in a thread, fixtures, no real Steam/network) → `tests/test_api.py`. ✅ all tasks.

**Placeholder scan:** none; every step has full code.

**Consistency:** `/api/games` items now always include `kind`; `/api/state` accounts are `{uid, name, has_avatar}` dicts (frontend in Plan 3 must read `.uid`, not a bare string — Plan 3 will account for this). `/api/gameicon` resolves via `load_shortcuts` (which now returns `icon`/`kind`) then falls back to `steam_game_image`. New endpoints reuse `_send_file(..., cache=False)`.

**Note for Plan 3 (frontend):** the `/api/state` response shape changed (accounts is now a list of objects, not strings). The current `web/app.js` builds the account `<select>` from bare strings — Plan 3's redesign (custom dropdown with avatars) will consume the new shape; until Plan 3 runs, the old `app.js` would mis-render the account list. That is expected and acceptable because Plan 3 immediately follows and rewrites the frontend.

**Execution note:** Tests run from project root with `python -m unittest discover -t . -s tests`. The API tests bind to `127.0.0.1` on an OS-assigned free port and shut the server down via `addCleanup(srv.shutdown)`; they never touch the real Steam install or network (engine key/list_arts are patched where needed).
