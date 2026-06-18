# -*- coding: utf-8 -*-
import unittest

import steam.launchers as L


class AggregatorTest(unittest.TestCase):
    def setUp(self):
        self._orig = L.LAUNCHERS
        L.LAUNCHERS = (
            ("epic", "Epic Games",
             lambda: [{"name": "A", "exe": "C:\\a.exe", "start_dir": "C:\\", "launcher": "epic"},
                      {"name": "B", "exe": "C:\\b.exe", "start_dir": "C:\\", "launcher": "epic"}]),
            ("boom", "Boom", lambda: (_ for _ in ()).throw(RuntimeError("x"))),
        )

    def tearDown(self):
        L.LAUNCHERS = self._orig

    def test_attaches_appid_and_survives_errors(self):
        out = L.detect_all()
        epic = [g for g in out if g["key"] == "epic"][0]
        self.assertEqual(len(epic["games"]), 2)
        self.assertGreaterEqual(epic["games"][0]["appid"], 0x80000000)
        boom = [g for g in out if g["key"] == "boom"][0]
        self.assertEqual(boom["games"], [])  # error -> empty, not a crash

    def test_nothing_dropped_all_returned(self):
        """All detected games are returned regardless of imported status."""
        from steam.shortcuts import game_appid
        aid = game_appid({"name": "A", "exe": "C:\\a.exe"})
        out = L.detect_all(imported_appids={aid})
        epic = [g for g in out if g["key"] == "epic"][0]
        # both games still present
        self.assertEqual(len(epic["games"]), 2)

    def test_imported_by_appid(self):
        """Game whose computed appid is in imported_appids gets imported=True
        and steam_appid equal to that appid."""
        from steam.shortcuts import game_appid
        aid = game_appid({"name": "A", "exe": "C:\\a.exe"})
        out = L.detect_all(imported_appids={aid})
        epic = [g for g in out if g["key"] == "epic"][0]
        game_a = [g for g in epic["games"] if g["name"] == "A"][0]
        game_b = [g for g in epic["games"] if g["name"] == "B"][0]
        self.assertTrue(game_a["imported"])
        self.assertEqual(game_a["steam_appid"], aid)
        self.assertFalse(game_b["imported"])
        self.assertIsNone(game_b["steam_appid"])

    def test_imported_by_exe_different_appid(self):
        """Game whose normalized exe maps via exe_to_appid to a DIFFERENT
        appid gets imported=True and steam_appid equal to that other appid."""
        from steam.shortcuts import game_appid, normalize_exe
        computed_aid = game_appid({"name": "A", "exe": "C:\\a.exe"})
        real_steam_appid = computed_aid + 1  # simulate a different appid
        exe_map = {normalize_exe("C:\\a.exe"): real_steam_appid}
        out = L.detect_all(exe_to_appid=exe_map)
        epic = [g for g in out if g["key"] == "epic"][0]
        game_a = [g for g in epic["games"] if g["name"] == "A"][0]
        game_b = [g for g in epic["games"] if g["name"] == "B"][0]
        self.assertTrue(game_a["imported"])
        self.assertEqual(game_a["steam_appid"], real_steam_appid)
        self.assertFalse(game_b["imported"])

    def test_not_imported(self):
        """Game matching neither imported_appids nor exe_to_appid gets
        imported=False and steam_appid=None."""
        out = L.detect_all()
        epic = [g for g in out if g["key"] == "epic"][0]
        for g in epic["games"]:
            self.assertFalse(g["imported"])
            self.assertIsNone(g["steam_appid"])

    def test_appid_match_takes_precedence_over_exe_match(self):
        """When the same game matches both imported_appids and exe_to_appid,
        the appid match wins and steam_appid equals the computed appid."""
        from steam.shortcuts import game_appid, normalize_exe
        computed_aid = game_appid({"name": "A", "exe": "C:\\a.exe"})
        other_aid = computed_aid + 99
        exe_map = {normalize_exe("C:\\a.exe"): other_aid}
        out = L.detect_all(imported_appids={computed_aid}, exe_to_appid=exe_map)
        epic = [g for g in out if g["key"] == "epic"][0]
        game_a = [g for g in epic["games"] if g["name"] == "A"][0]
        self.assertTrue(game_a["imported"])
        self.assertEqual(game_a["steam_appid"], computed_aid)

    def test_exe_match_case_insensitive(self):
        """normalize_exe normalises case so an upper-case path still matches."""
        from steam.shortcuts import game_appid, normalize_exe
        computed_aid = game_appid({"name": "A", "exe": "C:\\a.exe"})
        exe_map = {normalize_exe("C:\\A.EXE"): computed_aid}
        out = L.detect_all(exe_to_appid=exe_map)
        epic = [g for g in out if g["key"] == "epic"][0]
        game_a = [g for g in epic["games"] if g["name"] == "A"][0]
        self.assertTrue(game_a["imported"])
