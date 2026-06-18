# -*- coding: utf-8 -*-
import os
import unittest

from steam.shortcuts import game_appid, build_shortcut_entry, append_shortcuts, normalize_exe

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


class NormalizeExeTest(unittest.TestCase):
    def test_strips_quotes(self):
        self.assertEqual(normalize_exe('"C:\\Games\\foo.exe"'),
                         os.path.normcase(os.path.normpath("C:\\Games\\foo.exe")))

    def test_empty_and_none(self):
        self.assertEqual(normalize_exe(""), "")
        self.assertEqual(normalize_exe(None), "")

    def test_case_normalised(self):
        """On Windows normcase folds to lowercase; same path different case must match."""
        a = normalize_exe("C:\\Games\\Foo.exe")
        b = normalize_exe("C:\\GAMES\\FOO.EXE")
        self.assertEqual(a, b)

    def test_separator_normalised(self):
        """Forward and backward slashes normalise to the same value."""
        a = normalize_exe("C:\\Games\\foo.exe")
        b = normalize_exe("C:/Games/foo.exe")
        self.assertEqual(a, b)

    def test_dotdot_resolved(self):
        """Redundant components are collapsed."""
        a = normalize_exe("C:\\Games\\sub\\..\\foo.exe")
        b = normalize_exe("C:\\Games\\foo.exe")
        self.assertEqual(a, b)

    def test_strips_launch_args(self):
        """A quoted Exe with trailing launch args matches the bare exe path, so a
        shortcut like '"C:\\g\\foo.exe" --launch' is seen as the same game."""
        a = normalize_exe('"C:\\Games\\foo.exe" --launch -opengl')
        b = normalize_exe("C:\\Games\\foo.exe")
        self.assertEqual(a, b)
