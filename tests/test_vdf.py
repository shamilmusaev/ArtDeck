# -*- coding: utf-8 -*-
import struct
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
        self.assertEqual(get_ci(entry, "exe"), "C:\\a.exe")
        # parse_binary_vdf returns the raw signed int32; 2468090731 stored as
        # unsigned wraps to a negative when read as <i>.
        expected_appid = struct.unpack("<i", struct.pack("<I", 2468090731))[0]
        self.assertEqual(get_ci(entry, "appid"), expected_appid)

    def test_get_ci_case_insensitive(self):
        self.assertEqual(get_ci({"AppName": "X"}, "appname"), "X")
        self.assertIsNone(get_ci({"AppName": "X"}, "missing"))

    def test_parse_int64_field(self):
        data = build_shortcuts_vdf([
            {"AppName": "G", "Exe": "g.exe", "int64": ("LastPlayTime", 1700000000)},
        ])
        entry = parse_binary_vdf(data)["0"]
        self.assertEqual(get_ci(entry, "LastPlayTime"), 1700000000)


if __name__ == "__main__":
    unittest.main()
