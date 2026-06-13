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
