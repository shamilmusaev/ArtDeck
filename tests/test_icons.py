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
            # cover (library_600x900) takes priority over header
            self.assertTrue(steam_game_image(tmp, 431960).endswith("library_600x900.jpg"))

    def test_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(steam_game_image(tmp, 12345))

    def test_hash_named_jpg_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "appcache", "librarycache", "526870")
            os.makedirs(d)
            # only hash-named assets, no named priority
            open(os.path.join(d, "library_hero_blur.jpg"), "wb").close()
            open(os.path.join(d, "ee3406fe5ec813b1987ad67e37e5cd6fb4f620e6.jpg"), "wb").close()
            open(os.path.join(d, "5d3f4a68968b889ffe1ebdb4cbea7a0ab1189a62"), "wb").close()  # no extension
            got = steam_game_image(tmp, 526870)
            self.assertIsNotNone(got)
            self.assertTrue(got.endswith(".jpg"))
            self.assertNotIn("_blur", got)  # the blur variant is skipped

    def test_named_priority_beats_hash_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "appcache", "librarycache", "999")
            os.makedirs(d)
            open(os.path.join(d, "aaaa1111.jpg"), "wb").close()         # hash
            open(os.path.join(d, "library_600x900.jpg"), "wb").close()  # named
            self.assertTrue(steam_game_image(tmp, 999).endswith("library_600x900.jpg"))

    def test_game_icon_path_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            # non-Steam: use the shortcut's icon file if it exists
            ico = os.path.join(tmp, "alien.ico")
            open(ico, "wb").close()
            shortcut = {"kind": "shortcut", "appid": 2468090731, "icon": ico}
            self.assertEqual(game_icon_path(tmp, shortcut), ico)
            # non-Steam with no existing file -> None
            self.assertIsNone(game_icon_path(tmp, {"kind": "shortcut", "appid": 1, "icon": "Z:\\nope.ico"}))
            # Steam: delegates to steam_game_image
            d = os.path.join(tmp, "appcache", "librarycache", "431960")
            os.makedirs(d)
            open(os.path.join(d, "logo.png"), "wb").close()
            steam_g = {"kind": "steam", "appid": 431960, "icon": ""}
            self.assertTrue(game_icon_path(tmp, steam_g).endswith("logo.png"))


if __name__ == "__main__":
    unittest.main()
