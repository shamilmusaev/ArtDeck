# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

from steam.launchers import epic


def _write(d, fn, obj):
    with open(os.path.join(d, fn), "w", encoding="utf-8") as f:
        json.dump(obj, f)


class EpicDetectTest(unittest.TestCase):
    def test_detects_valid_skips_bad(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "ok.item", {"DisplayName": "Alan Wake 2",
                                   "InstallLocation": "C:\\Games\\AW2",
                                   "LaunchExecutable": "AW2.exe",
                                   "bIsApplication": True})
            _write(d, "dlc.item", {"DisplayName": "Some DLC",
                                   "InstallLocation": "C:\\Games\\AW2",
                                   "LaunchExecutable": "AW2.exe",
                                   "bIsApplication": False})
            _write(d, "partial.item", {"DisplayName": "No Exe",
                                       "InstallLocation": "C:\\Games\\X"})
            with open(os.path.join(d, "broken.item"), "w") as f:
                f.write("{ not json")
            games = epic.detect(d)
            self.assertEqual(len(games), 1)
            g = games[0]
            self.assertEqual(g["name"], "Alan Wake 2")
            self.assertEqual(g["launcher"], "epic")
            self.assertTrue(g["exe"].endswith("AW2.exe"))

    def test_missing_dir(self):
        self.assertEqual(epic.detect("Z:\\nope"), [])
