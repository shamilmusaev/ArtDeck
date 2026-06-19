# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from steam.official import official_art, _flat_name


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
            self.assertIsNone(official_art(steam, 999, "logo"))  # not created above


class FlatNameTest(unittest.TestCase):
    # Each art type must map to the exact flat file name Steam uses.
    # If a template here ever gets a typo, covers stop being found -> this test catches it.
    def test_each_type_maps_to_expected_name(self):
        self.assertEqual(_flat_name(440, "cover"), "440_library_600x900.jpg")
        self.assertEqual(_flat_name(440, "hero"), "440_library_hero.jpg")
        self.assertEqual(_flat_name(440, "logo"), "440_logo.png")
        self.assertEqual(_flat_name(440, "banner"), "440_header.jpg")

    def test_unknown_type_returns_none(self):
        # A type we don't know about must not crash, just give nothing back.
        self.assertIsNone(_flat_name(440, "something_weird"))


if __name__ == "__main__":
    unittest.main()
