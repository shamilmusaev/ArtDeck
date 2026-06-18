# -*- coding: utf-8 -*-
import unittest

from steam.launchers import gog


def fake_reader():
    return [
        {"gameName": "Cyberpunk 2077", "path": "C:\\GOG\\Cyberpunk",
         "exe": "C:\\GOG\\Cyberpunk\\bin\\Cyberpunk2077.exe"},
        {"gameName": "Relative Exe", "path": "C:\\GOG\\Rel", "exeFile": "game.exe"},
        {"gameName": "No path"},  # skipped
    ]


class GogDetectTest(unittest.TestCase):
    def test_detect(self):
        games = gog.detect(reader=fake_reader)
        self.assertEqual(len(games), 2)
        self.assertEqual(games[0]["name"], "Cyberpunk 2077")
        self.assertEqual(games[0]["launcher"], "gog")
        # relative exeFile is joined onto path
        self.assertEqual(games[1]["exe"], "C:\\GOG\\Rel\\game.exe")
