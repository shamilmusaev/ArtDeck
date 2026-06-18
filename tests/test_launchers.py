# -*- coding: utf-8 -*-
import unittest

import steam.launchers as L


class AggregatorTest(unittest.TestCase):
    def setUp(self):
        self._orig = L.LAUNCHERS
        L.LAUNCHERS = (
            ("epic", "Epic Games",
             lambda: [{"name": "A", "exe": "C:\\a.exe", "start_dir": "C:\\", "launcher": "epic"}]),
            ("boom", "Boom", lambda: (_ for _ in ()).throw(RuntimeError("x"))),
        )

    def tearDown(self):
        L.LAUNCHERS = self._orig

    def test_attaches_appid_and_survives_errors(self):
        out = L.detect_all()
        epic = [g for g in out if g["key"] == "epic"][0]
        self.assertEqual(len(epic["games"]), 1)
        self.assertGreaterEqual(epic["games"][0]["appid"], 0x80000000)
        boom = [g for g in out if g["key"] == "boom"][0]
        self.assertEqual(boom["games"], [])  # error -> empty, not a crash

    def test_exclude(self):
        from steam.shortcuts import game_appid
        aid = game_appid({"name": "A", "exe": "C:\\a.exe"})
        out = L.detect_all(exclude_appids={aid})
        epic = [g for g in out if g["key"] == "epic"][0]
        self.assertEqual(epic["games"], [])
