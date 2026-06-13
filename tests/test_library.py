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

    def test_find_orphans_missing_vdf_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            grid = os.path.join(tmp, "grid")
            os.makedirs(grid)
            open(os.path.join(grid, "%dp.png" % (NONSTEAM_MIN + 5)), "wb").close()
            vdf = os.path.join(tmp, "shortcuts.vdf")  # intentionally NOT created
            grid_dir, orph = find_orphans(vdf)
            self.assertEqual(orph, [])  # no vdf -> nothing treated as orphan (safety)


class FacadeTest(unittest.TestCase):
    def test_public_api_exposed(self):
        import steam
        for name in ("find_steam_path", "load_api_key", "list_accounts",
                     "account_paths", "list_games", "clean_name", "ART_TYPES",
                     "search_games", "list_arts", "SGDBError", "SGDBAuthError",
                     "find_orphans", "existing_art", "load_shortcuts", "art_status",
                     "search_game_id", "fetch_art_url", "apply_art"):
            self.assertTrue(hasattr(steam, name), "missing: " + name)


if __name__ == "__main__":
    unittest.main()
