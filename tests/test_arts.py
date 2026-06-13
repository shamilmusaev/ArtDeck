# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from steam import arts
from steam.arts import existing_art, art_status, apply_art, ART_TYPES


class ArtsTest(unittest.TestCase):
    def test_existing_art_finds_file(self):
        with tempfile.TemporaryDirectory() as grid:
            open(os.path.join(grid, "100p.png"), "wb").close()
            self.assertTrue(existing_art(grid, 100, "p").endswith("100p.png"))
            self.assertIsNone(existing_art(grid, 100, "_hero"))

    def test_art_status_all_types(self):
        with tempfile.TemporaryDirectory() as grid:
            st = art_status(grid, 100)
            self.assertEqual(set(st.keys()), set(ART_TYPES.keys()))
            self.assertTrue(all(v is None for v in st.values()))

    def test_apply_art_removes_other_ext(self):
        with tempfile.TemporaryDirectory() as grid:
            open(os.path.join(grid, "100p.jpg"), "wb").close()

            def fake_download(url, dest):
                open(dest, "wb").close()
            old = arts.download
            arts.download = fake_download
            try:
                dest = apply_art(grid, 100, "cover", "http://x/y.png")
            finally:
                arts.download = old
            self.assertTrue(dest.endswith("100p.png"))
            self.assertFalse(os.path.isfile(os.path.join(grid, "100p.jpg")))


if __name__ == "__main__":
    unittest.main()
