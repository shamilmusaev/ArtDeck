# -*- coding: utf-8 -*-
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch

import artdeck_app as app
from tests.helpers import make_account, make_library, write_file


def _get(srv, path):
    port = srv.server_address[1]
    req = urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=5)
    raw = req.read()
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError:
        body = raw.decode("latin-1")
    return req.status, body


def _status(srv, path):
    try:
        return _get(srv, path)[0]
    except urllib.error.HTTPError as e:
        return e.code


def _post(srv, path, obj):
    port = srv.server_address[1]
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, path),
        data=json.dumps(obj).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=5)
    return r.status, r.read().decode("utf-8")


class ApiBase(unittest.TestCase):
    def start(self, steam_path):
        app.STEAM = steam_path
        srv = app.Server(("127.0.0.1", app.free_port()), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return srv


class StateGamesTest(ApiBase):
    def test_state_returns_account_infos(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_account(tmp, "11111111",
                         [{"appid": 2468090731, "AppName": "Alien", "Exe": "a.exe"}],
                         persona="Player")
            srv = self.start(tmp)
            with patch.object(app.engine, "load_api_key", lambda *_: "k"):
                code, body = _get(srv, "/api/state")
            d = json.loads(body)
            self.assertEqual(code, 200)
            self.assertTrue(d["key_ok"])
            accts = d["accounts"]
            self.assertEqual(accts[0]["uid"], "11111111")
            self.assertEqual(accts[0]["name"], "Player")
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


class AutofillGuardTest(ApiBase):
    def test_autofill_no_steam_does_not_500(self):
        app.STEAM = None
        srv = app.Server(("127.0.0.1", app.free_port()), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        with patch.object(app.engine, "load_api_key", lambda *_: "k"):
            code, body = _get(srv, "/api/autofill?accounts=all")
        self.assertEqual(code, 200)
        self.assertIn('"type": "done"', body)


class ImportTest(ApiBase):
    def test_import_writes_shortcut(self):
        game = {"name": "Cyber Dummy", "exe": "C:\\Games\\CyberDummy.exe",
                "start_dir": "C:\\Games", "launcher": "epic"}
        appid = app.engine.game_appid(game)
        with tempfile.TemporaryDirectory() as tmp:
            make_account(tmp, "777", [])
            srv = self.start(tmp)
            with patch.object(app.engine, "detect_all",
                              return_value=[{"key": "epic", "label": "Epic Games",
                                             "games": [dict(game, appid=appid)]}]), \
                 patch.object(app.engine.steamproc, "is_running", return_value=False):
                code, body = _post(srv, "/api/import",
                                   {"account": "777", "appids": [appid], "close_steam": False})
            self.assertEqual(code, 200)
            d = json.loads(body)
            self.assertEqual(d, {"ok": True, "added": 1, "relaunched": False})
            vdf, _ = app.engine.account_paths(tmp, "777")
            m = app.engine.read_shortcuts_map(vdf)
            names = [e["AppName"] for e in m.values() if isinstance(e, dict)]
            self.assertIn("Cyber Dummy", names)


class SecurityTest(ApiBase):
    def test_static_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            srv = self.start(tmp)
            # Drive-absolute and dot-dot escapes must never serve files outside web/.
            self.assertEqual(_status(srv, "/C:/Windows/win.ini"), 403)
            self.assertEqual(_status(srv, "/A:/Windows/win.ini"), 403)

    def test_open_rejects_lookalike_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            srv = self.start(tmp)
            for url in ("https://www.steamgriddb.com.evil.com/x",
                        "https://steamgriddb.com@evil.com/x",
                        "http://www.steamgriddb.com/x"):
                self.assertEqual(_status(srv, "/api/open?url=" + urllib.parse.quote(url, safe="")), 400)

    def test_clean_only_deletes_real_orphans(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_account(tmp, "999", [{"appid": 2468090731, "AppName": "A", "Exe": "a.exe"}])
            grid = os.path.join(tmp, "userdata", "999", "config", "grid")
            os.makedirs(grid, exist_ok=True)
            victim = os.path.join(grid, "keep.txt")
            write_file(victim, "x")
            srv = self.start(tmp)
            _, body = _post(srv, "/api/clean",
                            {"items": [{"account": "999", "file": "keep.txt"},
                                       {"account": "999", "file": "../../../boom"}]})
            self.assertEqual(json.loads(body)["removed"], 0)
            self.assertTrue(os.path.isfile(victim))

    def test_api_key_saves_and_loads_from_same_dir(self):
        import steam.paths as paths
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(paths, "APP_DIR", tmp), \
                patch.dict(os.environ):
            os.environ.pop("STEAMGRIDDB_API_KEY", None)
            app.engine.save_api_key("secret123")
            self.assertTrue(os.path.isfile(os.path.join(tmp, "artdeck.key")))
            self.assertEqual(app.engine.load_api_key(None), "secret123")


if __name__ == "__main__":
    unittest.main()
