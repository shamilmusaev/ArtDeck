# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from tests.helpers import build_shortcuts_vdf
from steam.library import load_shortcuts, find_orphans, compute_legacy_appid, NONSTEAM_MIN, installed_games


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
            # orphaned non-Steam art
            open(os.path.join(grid, "%dp.png" % (NONSTEAM_MIN + 5)), "wb").close()
            # regular Steam game — left alone
            open(os.path.join(grid, "440p.png"), "wb").close()
            vdf = os.path.join(cfg, "shortcuts.vdf")
            with open(vdf, "wb") as f:
                f.write(build_shortcuts_vdf([]))
            _, orph = find_orphans(vdf)
            self.assertIn("%dp.png" % (NONSTEAM_MIN + 5), orph)
            self.assertNotIn("440p.png", orph)

    def test_find_orphans_missing_vdf_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            grid = os.path.join(tmp, "grid")
            os.makedirs(grid)
            open(os.path.join(grid, "%dp.png" % (NONSTEAM_MIN + 5)), "wb").close()
            vdf = os.path.join(tmp, "shortcuts.vdf")  # intentionally NOT created
            grid_dir, orph = find_orphans(vdf)
            self.assertEqual(orph, [])  # no vdf -> nothing treated as orphan (safety)

    def test_load_shortcuts_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "nope", "shortcuts.vdf")
            self.assertEqual(load_shortcuts(missing), [])

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


class InstalledGamesTest(unittest.TestCase):
    def test_installed_games_attaches_status(self):
        from tests.helpers import make_library, write_file
        with tempfile.TemporaryDirectory() as tmp:
            steam = os.path.join(tmp, "Steam")
            make_library(steam, {"431960": "Wallpaper Engine"})
            write_file(os.path.join(steam, "steamapps", "libraryfolders.vdf"),
                       '"libraryfolders"\n{\n  "0"\n  {\n    "path" "%s"\n  }\n}\n'
                       % steam.replace("\\", "\\\\"))
            uid = "999"
            grid = os.path.join(steam, "userdata", uid, "config", "grid")
            os.makedirs(grid)
            open(os.path.join(grid, "431960p.png"), "wb").close()
            games = installed_games(steam, uid)
            self.assertEqual(len(games), 1)
            self.assertEqual(games[0]["appid"], 431960)
            self.assertTrue(games[0]["status"]["cover"])   # 431960p.png present
            self.assertFalse(games[0]["status"]["hero"])


class FacadeTest(unittest.TestCase):
    def test_public_api_exposed(self):
        import steam
        self.assertTrue(steam.__all__, "steam.__all__ must be non-empty")
        for name in steam.__all__:
            self.assertTrue(hasattr(steam, name), "missing: " + name)

    def test_key_engine_names_present(self):
        import steam
        # names the CLI and server rely on — must exist
        for name in ("find_steam_path", "load_api_key", "list_accounts",
                     "account_paths", "list_games", "clean_name", "ART_TYPES",
                     "search_games", "list_arts", "SGDBError", "SGDBAuthError",
                     "find_orphans", "existing_art", "load_shortcuts", "art_status",
                     "search_game_id", "fetch_art_url", "apply_art", "download",
                     "clean_orphans", "compute_legacy_appid"):
            self.assertIn(name, steam.__all__, "not in __all__: " + name)
            self.assertTrue(hasattr(steam, name), "missing: " + name)

    def test_plan2_names_present(self):
        import steam
        for name in ("parse_text_vdf", "list_libraries", "load_installed",
                     "installed_games", "STEAM_TOOL_APPIDS", "account_steamid64",
                     "load_users", "account_name", "account_avatar_path",
                     "account_infos", "steam_game_image", "game_icon_path"):
            self.assertIn(name, steam.__all__, "not in __all__: " + name)
            self.assertTrue(hasattr(steam, name), "missing: " + name)


if __name__ == "__main__":
    unittest.main()
