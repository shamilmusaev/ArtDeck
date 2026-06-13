# -*- coding: utf-8 -*-
import os
import struct
import tempfile
import unittest
from steam.verify import valid_image, verify_applied


def _png(path):
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)


class VerifyTest(unittest.TestCase):
    def test_valid_image_detects_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "a.png"); _png(p)
            self.assertTrue(valid_image(p))
            empty = os.path.join(tmp, "e.png"); open(empty, "wb").close()
            self.assertFalse(valid_image(empty))          # пустой
            txt = os.path.join(tmp, "t.png")
            with open(txt, "wb") as f: f.write(b"<html>nope")
            self.assertFalse(valid_image(txt))            # не картинка

    def test_ok_when_single_valid_file(self):
        with tempfile.TemporaryDirectory() as grid:
            dest = os.path.join(grid, "100p.png"); _png(dest)
            v = verify_applied(grid, 100, "cover", dest)
            self.assertTrue(v["ok"]); self.assertIsNone(v["code"])

    def test_competing_file_detected(self):
        with tempfile.TemporaryDirectory() as grid:
            dest = os.path.join(grid, "100p.png"); _png(dest)
            _png(os.path.join(grid, "100p.jpg"))         # старый дубль в слоте
            v = verify_applied(grid, 100, "cover", dest)
            self.assertFalse(v["ok"]); self.assertEqual(v["code"], "competing")
            self.assertIn("100p.jpg", v["files"])

    def test_corrupt_file(self):
        with tempfile.TemporaryDirectory() as grid:
            dest = os.path.join(grid, "100p.png")
            with open(dest, "wb") as f: f.write(b"oops")
            v = verify_applied(grid, 100, "cover", dest)
            self.assertEqual(v["code"], "corrupt")


if __name__ == "__main__":
    unittest.main()
