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

    def test_exclude_by_appid(self):
        from steam.shortcuts import game_appid
        aid = game_appid({"name": "A", "exe": "C:\\a.exe"})
        out = L.detect_all(exclude_appids={aid})
        epic = [g for g in out if g["key"] == "epic"][0]
        # only "A" dropped; "B" kept
        self.assertEqual(len(epic["games"]), 1)
        self.assertEqual(epic["games"][0]["name"], "B")

    def test_exclude_by_exe(self):
        from steam.shortcuts import normalize_exe
        # normalize_exe of "C:\\a.exe" -> exclude it
        skip = {normalize_exe("C:\\a.exe")}
        out = L.detect_all(exclude_exes=skip)
        epic = [g for g in out if g["key"] == "epic"][0]
        # "A" dropped by exe match; "B" kept
        self.assertEqual(len(epic["games"]), 1)
        self.assertEqual(epic["games"][0]["name"], "B")

    def test_exclude_by_exe_case_insensitive(self):
        """normalize_exe normalises case so an upper-case path still matches."""
        from steam.shortcuts import normalize_exe
        skip = {normalize_exe("C:\\A.EXE")}
        out = L.detect_all(exclude_exes=skip)
        epic = [g for g in out if g["key"] == "epic"][0]
        self.assertEqual(len(epic["games"]), 1)
        self.assertEqual(epic["games"][0]["name"], "B")
