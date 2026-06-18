# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

from steam.launchers import gog


class GogDetectTest(unittest.TestCase):
    def setUp(self):
        # row 1: real exe + goggame marker -> KEPT (fallback path)
        self.dir1 = tempfile.mkdtemp()
        self.exe1 = os.path.join(self.dir1, "game.exe")
        open(self.exe1, "w").close()
        open(os.path.join(self.dir1, "goggame-123.info"), "w").close()

        # row 2: real exe but no goggame marker -> DROPPED (fallback path)
        self.dir2 = tempfile.mkdtemp()
        self.exe2 = os.path.join(self.dir2, "game.exe")
        open(self.exe2, "w").close()

        # row 3: path does not exist on disk (phantom) -> DROPPED
        self.dir3 = tempfile.mkdtemp()
        self.exe3 = os.path.join(self.dir3, "phantom.exe")
        # intentionally do NOT create exe3 or marker

    def _make_reader(self, id1="1001", id2="1002", id3="1003"):
        rows = [
            {"gameName": "Real Game",   "path": self.dir1, "exe": self.exe1,  "_id": id1},
            {"gameName": "No Marker",   "path": self.dir2, "exe": self.exe2,  "_id": id2},
            {"gameName": "Phantom",     "path": self.dir3, "exe": self.exe3,  "_id": id3},
        ]
        return lambda: rows

    # --- fallback (no Galaxy DB) ---

    def test_only_genuine_installs_kept(self):
        """installed_ids=None -> fall back to goggame marker heuristic."""
        games = gog.detect(reader=self._make_reader(), installed_ids=None)
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["name"], "Real Game")
        self.assertEqual(games[0]["launcher"], "gog")

    def test_no_path_skipped(self):
        """Rows missing name/path/exe are still skipped before the new filter."""
        rows = [{"gameName": "No path"}]
        games = gog.detect(reader=lambda: rows, installed_ids=None)
        self.assertEqual(games, [])

    def test_relative_exe_resolved(self):
        """A relative exeFile is joined onto path before the existence check."""
        rows = [{"gameName": "Rel", "path": self.dir1, "exeFile": "game.exe", "_id": "1001"}]
        games = gog.detect(reader=lambda: rows, installed_ids=None)
        # dir1 has both exe and marker, so it should be kept
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["exe"], os.path.normpath(os.path.join(self.dir1, "game.exe")))

    # --- Galaxy DB path ---

    def test_galaxy_db_keeps_matching_id(self):
        """Row whose _id is in installed_ids is kept even without a marker file."""
        # dir2 has no goggame marker but we pass its id in the set
        rows = [{"gameName": "DB Game", "path": self.dir2, "exe": self.exe2, "_id": "9999"}]
        games = gog.detect(reader=lambda: rows, installed_ids={9999})
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["name"], "DB Game")

    def test_galaxy_db_drops_unmatched_id(self):
        """Row whose _id is NOT in installed_ids is dropped (even if exe exists)."""
        rows = [{"gameName": "Phantom DB", "path": self.dir2, "exe": self.exe2, "_id": "5555"}]
        games = gog.detect(reader=lambda: rows, installed_ids={9999})
        self.assertEqual(games, [])

    def test_galaxy_db_drops_non_numeric_id(self):
        """Row with a non-numeric _id is always dropped when installed_ids is set."""
        rows = [{"gameName": "Bad ID", "path": self.dir2, "exe": self.exe2, "_id": "notanumber"}]
        games = gog.detect(reader=lambda: rows, installed_ids={1234})
        self.assertEqual(games, [])

    def test_galaxy_db_drops_missing_id(self):
        """Row with no _id key is dropped when installed_ids is set."""
        rows = [{"gameName": "No ID", "path": self.dir2, "exe": self.exe2}]
        games = gog.detect(reader=lambda: rows, installed_ids={1234})
        self.assertEqual(games, [])

    # --- installed_product_ids helper ---

    def test_installed_product_ids_missing_db(self):
        """Returns None when the DB file does not exist."""
        result = gog.installed_product_ids(db_path="/nonexistent/path/galaxy.db")
        self.assertIsNone(result)

    def test_installed_product_ids_reads_real_db(self):
        """Reads productIds from a minimal SQLite file."""
        import sqlite3
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("create table InstalledBaseProducts (productId integer)")
            conn.execute("insert into InstalledBaseProducts values (1111)")
            conn.execute("insert into InstalledBaseProducts values (2222)")
            conn.commit()
            conn.close()
            ids = gog.installed_product_ids(db_path=db_path)
            self.assertEqual(ids, {1111, 2222})
        finally:
            os.unlink(db_path)
