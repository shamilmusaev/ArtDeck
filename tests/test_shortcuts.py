# -*- coding: utf-8 -*-
import unittest

from steam.shortcuts import game_appid, build_shortcut_entry, append_shortcuts

GAME = {"name": "Game One", "exe": "C:\\g\\one.exe", "start_dir": "C:\\g",
        "launcher": "epic"}


class ShortcutsTest(unittest.TestCase):
    def test_appid_is_nonsteam_range(self):
        self.assertGreaterEqual(game_appid(GAME), 0x80000000)
        self.assertLessEqual(game_appid(GAME), 0xffffffff)

    def test_entry_fields(self):
        e = build_shortcut_entry(GAME)
        self.assertEqual(e["AppName"], "Game One")
        self.assertEqual(e["Exe"], "\"C:\\g\\one.exe\"")       # quoted
        self.assertEqual(e["StartDir"], "\"C:\\g\"")
        self.assertIn("ArtDeck", e["tags"].values())
        self.assertTrue(-2147483648 <= e["appid"] <= 2147483647)  # stored signed

    def test_launcher_tag_propagates(self):
        e = build_shortcut_entry(GAME)
        self.assertIn("epic", e["tags"].values())

    def test_append_and_dedupe(self):
        m = {}
        m, added = append_shortcuts(m, [GAME])
        self.assertEqual(added, 1)
        self.assertEqual(list(m.keys()), ["0"])
        # same game again -> skipped
        m, added = append_shortcuts(m, [GAME])
        self.assertEqual(added, 0)
        self.assertEqual(list(m.keys()), ["0"])
