# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

from steam.launchers import gog


class GogDetectTest(unittest.TestCase):
    def setUp(self):
        # row 1: real exe + goggame marker -> KEPT
        self.dir1 = tempfile.mkdtemp()
        self.exe1 = os.path.join(self.dir1, "game.exe")
        open(self.exe1, "w").close()
        open(os.path.join(self.dir1, "goggame-123.info"), "w").close()

        # row 2: real exe but no goggame marker -> DROPPED
        self.dir2 = tempfile.mkdtemp()
        self.exe2 = os.path.join(self.dir2, "game.exe")
        open(self.exe2, "w").close()

        # row 3: path does not exist on disk (phantom) -> DROPPED
        self.dir3 = tempfile.mkdtemp()
        self.exe3 = os.path.join(self.dir3, "phantom.exe")
        # intentionally do NOT create exe3 or marker

    def _make_reader(self):
        rows = [
            {"gameName": "Real Game",   "path": self.dir1, "exe": self.exe1},
            {"gameName": "No Marker",   "path": self.dir2, "exe": self.exe2},
            {"gameName": "Phantom",     "path": self.dir3, "exe": self.exe3},
        ]
        return lambda: rows

    def test_only_genuine_installs_kept(self):
        games = gog.detect(reader=self._make_reader())
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["name"], "Real Game")
        self.assertEqual(games[0]["launcher"], "gog")

    def test_no_path_skipped(self):
        """Rows missing name/path/exe are still skipped before the new filter."""
        rows = [{"gameName": "No path"}]
        games = gog.detect(reader=lambda: rows)
        self.assertEqual(games, [])

    def test_relative_exe_resolved(self):
        """A relative exeFile is joined onto path before the existence check."""
        rows = [{"gameName": "Rel", "path": self.dir1, "exeFile": "game.exe"}]
        games = gog.detect(reader=lambda: rows)
        # dir1 has both exe and marker, so it should be kept
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["exe"], os.path.normpath(os.path.join(self.dir1, "game.exe")))
