# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from steam.official import official_art


class OfficialTest(unittest.TestCase):
    def _make(self, steam, appid, fname):
        d = os.path.join(steam, "appcache", "librarycache", str(appid))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, fname), "wb").close()

    def test_finds_official_per_type(self):
        with tempfile.TemporaryDirectory() as steam:
            self._make(steam, 431960, "library_600x900.jpg")
            self._make(steam, 431960, "library_hero.jpg")
            self._make(steam, 431960, "logo.png")
            self.assertTrue(official_art(steam, 431960, "cover").endswith("library_600x900.jpg"))
            self.assertTrue(official_art(steam, 431960, "hero").endswith("library_hero.jpg"))
            self.assertTrue(official_art(steam, 431960, "logo").endswith("logo.png"))

    def test_none_when_absent(self):
        with tempfile.TemporaryDirectory() as steam:
            self.assertIsNone(official_art(steam, 999, "cover"))
            self.assertIsNone(official_art(steam, 999, "icon"))  # icon has no reliable file


if __name__ == "__main__":
    unittest.main()
