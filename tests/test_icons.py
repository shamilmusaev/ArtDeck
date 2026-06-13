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
