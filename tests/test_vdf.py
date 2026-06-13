# -*- coding: utf-8 -*-
import unittest
from tests.helpers import build_shortcuts_vdf
from steam.vdf import parse_binary_vdf, get_ci


class VdfTest(unittest.TestCase):
    def test_parse_single_game(self):
        data = build_shortcuts_vdf([
            {"appid": 2468090731, "AppName": "Alien Isolation", "Exe": "C:\\a.exe"},
        ])
        parsed = parse_binary_vdf(data)
        entry = parsed["0"]
        self.assertEqual(get_ci(entry, "appname"), "Alien Isolation")
        # parse_binary_vdf returns the raw signed int32; 2468090731 stored as
        # unsigned wraps to a negative when read as <i>.
        self.assertEqual(get_ci(entry, "appid"), 2468090731 - 0x100000000)

    def test_get_ci_case_insensitive(self):
        self.assertEqual(get_ci({"AppName": "X"}, "appname"), "X")
        self.assertIsNone(get_ci({"AppName": "X"}, "missing"))


if __name__ == "__main__":
    unittest.main()
